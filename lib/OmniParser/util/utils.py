# Core system imports
import os
import io
import time
import base64
from functools import wraps
from typing import List, Dict, Tuple, Union, Optional

# Image processing and computer vision
import cv2
import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

# OCR engines
import easyocr
import pytesseract

# Deep learning
import torch
from torchvision.ops import box_convert
from torchvision.transforms import ToPILImage
import supervision as sv

# Text processing
import re

# Global variables for OCR readers
reader: Optional[easyocr.Reader] = None
pytesseract_initialized = False


def timing_decorator(process_name):
    """Decorator to add timing information to functions"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            print(f"[TIMING] Starting {process_name}...")
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                end_time = time.time()
                elapsed = end_time - start_time
                print(f"[TIMING] {process_name} completed in {elapsed:.3f} seconds")
                return result
            except Exception as e:
                end_time = time.time()
                elapsed = end_time - start_time
                print(f"[TIMING] {process_name} failed after {elapsed:.3f} seconds: {str(e)}")
                raise
        return wrapper
    return decorator


def setup_easy_ocr():
    start_time = time.time()
    global reader
    if reader is None:
        print(f"[TIMING] PID={os.getpid()} Starting OCR setup...")
        reader = easyocr.Reader(['en'], model_storage_directory=os.environ.get('EASYOCR_MODEL_PATH', None), download_enabled=True, gpu=False)
        print(f"[TIMING] PID={os.getpid()} OCR setup completed, elapsed={time.time() - start_time:.3f} seconds")
    else:
        print(f"[TIMING] PID={os.getpid()} OCR reader already initialized, skipping setup")

def setup_pytesseract():
    """Setup pytesseract OCR engine"""
    global pytesseract_initialized
    start_time = time.time()

    if not pytesseract_initialized:
        print(f"[TIMING] PID={os.getpid()} Starting pytesseract setup...")

        # ✅ Optional: Set tesseract executable path if not in PATH
        # Uncomment and modify if tesseract is not in your system PATH:
        # pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'  # Linux
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Windows

        # ✅ Test if tesseract is working
        try:
            version = pytesseract.get_tesseract_version()
            print(f"✅ Tesseract version: {version}")
            pytesseract_initialized = True
            print(f"[TIMING] PID={os.getpid()} pytesseract setup completed, elapsed={time.time() - start_time:.3f} seconds")
        except Exception as e:
            print(f"❌ Tesseract not found or not working: {e}")
            print("Please install tesseract-ocr: sudo apt-get install tesseract-ocr (Linux) or download from GitHub")
            pytesseract_initialized = False
    else:
        print(f"[TIMING] PID={os.getpid()} pytesseract already initialized, skipping setup")

def get_caption_model_processor(model_name, model_name_or_path="Salesforce/blip2-opt-2.7b", device=None):
    if not device:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if model_name == "blip2":
        from transformers import Blip2Processor, Blip2ForConditionalGeneration
        processor = Blip2Processor.from_pretrained("Salesforce/blip2-opt-2.7b")
        if device == 'cpu':
            model = Blip2ForConditionalGeneration.from_pretrained(
                model_name_or_path, device_map=None, torch_dtype=torch.float32
            )
        else:
            model = Blip2ForConditionalGeneration.from_pretrained(
                model_name_or_path, device_map=None, torch_dtype=torch.float16
            ).to(device)
    elif model_name == "florence2":
        from transformers import AutoProcessor, AutoModelForCausalLM
        processor = AutoProcessor.from_pretrained("microsoft/Florence-2-base", trust_remote_code=True)
        if device == 'cpu':
            model = AutoModelForCausalLM.from_pretrained(model_name_or_path, torch_dtype=torch.float32, trust_remote_code=True)
        else:
            model = AutoModelForCausalLM.from_pretrained(model_name_or_path, torch_dtype=torch.float16, trust_remote_code=True).to(device)
    return {'model': model.to(device), 'processor': processor}

def get_yolo_model(model_path):
    from ultralytics import YOLO
    # Load the model.
    model = YOLO(model_path)
    return model

def filter_small_boxes(boxes, min_area=400, min_width=20, min_height=20, image_width=None, image_height=None):
    """Filter out boxes that are too small to be meaningful UI elements"""
    filtered_boxes = []

    for box in boxes:
        if isinstance(box, dict):
            bbox = box['bbox']
            element_type = box.get('type', 'unknown')
        else:
            bbox = box
            element_type = 'unknown'

        # Convert to pixel coordinates if normalized
        if image_width and image_height and all(coord <= 1.0 for coord in bbox):
            x1, y1, x2, y2 = bbox[0] * image_width, bbox[1] * image_height, bbox[2] * image_width, bbox[3] * image_height
        else:
            x1, y1, x2, y2 = bbox

        width = abs(x2 - x1)
        height = abs(y2 - y1)
        area = width * height

        # ✅ FIXED: Smarter filtering that preserves text elements
        # Text elements can be very wide (navigation bars, tabs) or very tall (sidebars)
        if element_type == 'text':
            # More lenient criteria for text elements
            aspect_ratio_ok = (
                width / height < 50 and    # Allow wide text (navigation bars, tabs)
                height / width < 20        # Allow tall text (sidebars, labels)
            )
            size_ok = (
                area >= min_area * 0.3 and    # Lower area requirement for text
                width >= min_width * 0.5 and  # Lower width requirement
                height >= max(min_height * 0.3, 8)  # Lower height but minimum 8px
            )
        else:
            # Regular criteria for UI elements (buttons, icons, etc.)
            aspect_ratio_ok = (
                width / height < 15 and   # Slightly more lenient than before
                height / width < 15       # Allow some elongated UI elements
            )
            size_ok = (
                area >= min_area and
                width >= min_width and
                height >= min_height
            )

        if size_ok and aspect_ratio_ok:
            filtered_boxes.append(box)

    return filtered_boxes

def merge_nearby_text_boxes(text_boxes, merge_threshold=30):
    """Merge text boxes that are close to each other"""
    if not text_boxes:
        return text_boxes

    merged_boxes = []
    used_indices = set()

    for i, box1 in enumerate(text_boxes):
        if i in used_indices:
            continue

        bbox1 = box1['bbox']
        content1 = box1['content']
        merged_content = content1
        merged_bbox = bbox1.copy()
        group_indices = {i}

        # Find nearby boxes to merge
        for j, box2 in enumerate(text_boxes):
            if j == i or j in used_indices:
                continue

            bbox2 = box2['bbox']

            # Check if boxes are close horizontally or vertically
            if (abs(bbox1[1] - bbox2[1]) < merge_threshold and  # Same line
                abs(bbox1[2] - bbox2[0]) < merge_threshold) or \
               (abs(bbox1[3] - bbox2[1]) < merge_threshold and  # Vertically close
                abs(bbox1[0] - bbox2[0]) < merge_threshold):

                merged_content += " " + box2['content']
                merged_bbox[0] = min(merged_bbox[0], bbox2[0])  # min x
                merged_bbox[1] = min(merged_bbox[1], bbox2[1])  # min y
                merged_bbox[2] = max(merged_bbox[2], bbox2[2])  # max x
                merged_bbox[3] = max(merged_bbox[3], bbox2[3])  # max y
                group_indices.add(j)

        used_indices.update(group_indices)
        box1['content'] = merged_content.strip()
        box1['bbox'] = merged_bbox
        merged_boxes.append(box1)

    return merged_boxes

def get_optimal_florence_prompt(image_source, boxes):
    """
    Intelligently select the best Florence-2 prompt based on UI context and element characteristics

    Florence-2 Prompt Options:
    - <CAPTION>: Basic image caption
    - <DETAILED_CAPTION>: Detailed image description
    - <MORE_DETAILED_CAPTION>: Very detailed analysis
    - <REGION_TO_CATEGORY>: Classify element type (button, input, menu, etc.)
    - <REGION_TO_DESCRIPTION>: Detailed element description
    - <DENSE_REGION_CAPTION>: Dense captioning for complex areas
    - <OD>: Object detection within region
    """

    # Analyze image characteristics
    h, w = image_source.shape[:2]
    avg_brightness = np.mean(image_source)
    is_dark_theme = avg_brightness < 100

    # Analyze box characteristics
    if boxes and len(boxes) > 0:
        # Calculate average box size
        box_areas = []
        for box in boxes[:10]:  # Sample first 10 boxes
            if len(box) >= 4:
                box_w = abs(box[2] - box[0]) * w
                box_h = abs(box[3] - box[1]) * h
                box_areas.append(box_w * box_h)

        avg_box_area = np.mean(box_areas) if box_areas else 1000

        # Context-aware prompt selection
        if is_dark_theme and avg_box_area < 1000:
            # Dark theme small elements need detailed classification
            return "<MORE_DETAILED_CAPTION>"
        elif avg_box_area < 800:  # Small UI elements
            return "<REGION_TO_CATEGORY>"  # Focus on classification
        elif avg_box_area > 5000:  # Large UI areas
            return "<DENSE_REGION_CAPTION>"  # Dense analysis for complex areas
        else:  # Medium-sized elements
            return "<DETAILED_CAPTION>"  # Balanced detailed description

    # Default for unclear contexts
    return "<DETAILED_CAPTION>"


@torch.inference_mode()
def get_parsed_content_icon(filtered_boxes, starting_idx, image_source, caption_model_processor, prompt=None, batch_size=128):
    # Number of samples per batch, --> 128 roughly takes 4 GB of GPU memory for florence v2 model
    print(f"[TIMING] Starting icon content parsing with batch_size={batch_size}...")
    icon_parse_start = time.time()

    to_pil = ToPILImage()
    if starting_idx:
        non_ocr_boxes = filtered_boxes[starting_idx:]
    else:
        non_ocr_boxes = filtered_boxes

    print(f"[TIMING] Processing {len(non_ocr_boxes)} icon boxes...")
    crop_start = time.time()
    croped_pil_image = []
    for i, coord in enumerate(non_ocr_boxes):
        try:
            xmin, xmax = int(coord[0]*image_source.shape[1]), int(coord[2]*image_source.shape[1])
            ymin, ymax = int(coord[1]*image_source.shape[0]), int(coord[3]*image_source.shape[0])
            cropped_image = image_source[ymin:ymax, xmin:xmax, :]
            cropped_image = cv2.resize(cropped_image, (64, 64), interpolation=cv2.INTER_CUBIC)
            croped_pil_image.append(to_pil(cropped_image))
        except:
            continue
    crop_end = time.time()
    print(f"[TIMING] Image cropping completed in {crop_end - crop_start:.3f} seconds")

    model, processor = caption_model_processor['model'], caption_model_processor['processor']

    # ✅ ENHANCED: Smart prompt selection for Florence-2 based on UI context
    if not prompt:
        if 'florence' in model.config.name_or_path:
            # Determine optimal Florence-2 prompt based on image characteristics
            prompt = get_optimal_florence_prompt(image_source, non_ocr_boxes)
            print(f"🔧 [FLORENCE-PROMPT] Selected optimal prompt: {prompt}")
            print(f"   📊 Analyzing {len(non_ocr_boxes)} UI elements for context-aware captioning")
        else:
            prompt = "The image shows"

    generated_texts = []
    device = model.device
    num_batches = (len(croped_pil_image) + batch_size - 1) // batch_size
    print(f"[TIMING] Processing {num_batches} batches with vision model...")

    for i in range(0, len(croped_pil_image), batch_size):
        batch_start = time.time()
        batch_num = i // batch_size + 1
        batch = croped_pil_image[i:i+batch_size]
        print(f"[TIMING] Processing batch {batch_num}/{num_batches} ({len(batch)} images)...")

        if model.device.type == 'cuda':
            inputs = processor(images=batch, text=[prompt]*len(batch), return_tensors="pt", do_resize=False).to(device=device, dtype=torch.float16)
        else:
            inputs = processor(images=batch, text=[prompt]*len(batch), return_tensors="pt").to(device=device)

        generation_start = time.time()
        if 'florence' in model.config.name_or_path:
            generated_ids = model.generate(input_ids=inputs["input_ids"],pixel_values=inputs["pixel_values"],max_new_tokens=5,num_beams=1, do_sample=True)
        else:
            generated_ids = model.generate(**inputs, max_new_tokens=5, num_beams=1, no_repeat_ngram_size=2, early_stopping=True, num_return_sequences=1, temperature=0.01, do_sample=True) # temperature=0.01, do_sample=True,
        generated_text = processor.batch_decode(generated_ids, skip_special_tokens=True)
        generated_text = [gen.strip() for gen in generated_text]
        generated_texts.extend(generated_text)

        generation_end = time.time()
        batch_end = time.time()
        print(f"[TIMING] Batch {batch_num} completed: generation={generation_end - generation_start:.3f}s, total={batch_end - batch_start:.3f}s")

    icon_parse_end = time.time()
    print(f"[TIMING] Icon content parsing completed in {icon_parse_end - icon_parse_start:.3f} seconds")
    return generated_texts

def get_parsed_content_icon_phi3v(filtered_boxes, ocr_bbox, image_source, caption_model_processor):
    print("[TIMING] Starting Phi3V icon content parsing...")
    phi3v_start = time.time()

    to_pil = ToPILImage()
    if ocr_bbox:
        non_ocr_boxes = filtered_boxes[len(ocr_bbox):]
    else:
        non_ocr_boxes = filtered_boxes

    print(f"[TIMING] Processing {len(non_ocr_boxes)} icon boxes with Phi3V...")
    crop_start = time.time()
    croped_pil_image = []
    for i, coord in enumerate(non_ocr_boxes):
        xmin, xmax = int(coord[0]*image_source.shape[1]), int(coord[2]*image_source.shape[1])
        ymin, ymax = int(coord[1]*image_source.shape[0]), int(coord[3]*image_source.shape[0])

        # Skip very small boxes (likely decorative elements)
        width, height = xmax - xmin, ymax - ymin
        if width < 20 or height < 20:  # Skip boxes smaller than 20x20 pixels
            continue

        cropped_image = image_source[ymin:ymax, xmin:xmax, :]
        croped_pil_image.append(to_pil(cropped_image))
    crop_end = time.time()
    print(f"[TIMING] Image cropping completed in {crop_end - crop_start:.3f} seconds")

    model, processor = caption_model_processor['model'], caption_model_processor['processor']
    device = model.device
    messages = [{"role": "user", "content": "<|image_1|>\ndescribe the icon in one sentence"}]
    prompt = processor.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

    batch_size = 5  # Number of samples per batch
    generated_texts = []
    num_batches = (len(croped_pil_image) + batch_size - 1) // batch_size
    print(f"[TIMING] Processing {num_batches} batches with Phi3V model (batch_size=5)...")

    for i in range(0, len(croped_pil_image), batch_size):
        batch_start = time.time()
        batch_num = i // batch_size + 1
        images = croped_pil_image[i:i+batch_size]
        print(f"[TIMING] Processing Phi3V batch {batch_num}/{num_batches} ({len(images)} images)...")

        prep_start = time.time()
        image_inputs = [processor.image_processor(x, return_tensors="pt") for x in images]
        inputs ={'input_ids': [], 'attention_mask': [], 'pixel_values': [], 'image_sizes': []}
        texts = [prompt] * len(images)
        for i, txt in enumerate(texts):
            input = processor._convert_images_texts_to_inputs(image_inputs[i], txt, return_tensors="pt")
            inputs['input_ids'].append(input['input_ids'])
            inputs['attention_mask'].append(input['attention_mask'])
            inputs['pixel_values'].append(input['pixel_values'])
            inputs['image_sizes'].append(input['image_sizes'])
        max_len = max([x.shape[1] for x in inputs['input_ids']])
        for i, v in enumerate(inputs['input_ids']):
            inputs['input_ids'][i] = torch.cat([processor.tokenizer.pad_token_id * torch.ones(1, max_len - v.shape[1], dtype=torch.long), v], dim=1)
            inputs['attention_mask'][i] = torch.cat([torch.zeros(1, max_len - v.shape[1], dtype=torch.long), inputs['attention_mask'][i]], dim=1)
        inputs_cat = {k: torch.concatenate(v).to(device) for k, v in inputs.items()}
        prep_end = time.time()

        generation_args = {
            "max_new_tokens": 25,
            "temperature": 0.01,
            "do_sample": False,
        }
        generation_start = time.time()
        generate_ids = model.generate(**inputs_cat, eos_token_id=processor.tokenizer.eos_token_id, **generation_args)
        # # remove input tokens
        generate_ids = generate_ids[:, inputs_cat['input_ids'].shape[1]:]
        response = processor.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
        response = [res.strip('\n').strip() for res in response]
        generated_texts.extend(response)

        generation_end = time.time()
        batch_end = time.time()
        print(f"[TIMING] Phi3V batch {batch_num} completed: prep={prep_end - prep_start:.3f}s, generation={generation_end - generation_start:.3f}s, total={batch_end - batch_start:.3f}s")

    phi3v_end = time.time()
    print(f"[TIMING] Phi3V icon content parsing completed in {phi3v_end - phi3v_start:.3f} seconds")
    return generated_texts

def remove_overlap(boxes, iou_threshold, ocr_bbox=None):
    assert ocr_bbox is None or isinstance(ocr_bbox, List)

    def box_area(box):
        return (box[2] - box[0]) * (box[3] - box[1])

    def intersection_area(box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        return max(0, x2 - x1) * max(0, y2 - y1)

    def IoU(box1, box2):
        intersection = intersection_area(box1, box2)
        union = box_area(box1) + box_area(box2) - intersection + 1e-6
        if box_area(box1) > 0 and box_area(box2) > 0:
            ratio1 = intersection / box_area(box1)
            ratio2 = intersection / box_area(box2)
        else:
            ratio1, ratio2 = 0, 0
        return max(intersection / union, ratio1, ratio2)

    def is_inside(box1, box2):
        # return box1[0] >= box2[0] and box1[1] >= box2[1] and box1[2] <= box2[2] and box1[3] <= box2[3]
        intersection = intersection_area(box1, box2)
        ratio1 = intersection / box_area(box1)
        return ratio1 > 0.95

    boxes = boxes.tolist()
    filtered_boxes = []
    if ocr_bbox:
        filtered_boxes.extend(ocr_bbox)
    # print('ocr_bbox!!!', ocr_bbox)
    for i, box1 in enumerate(boxes):
        # if not any(IoU(box1, box2) > iou_threshold and box_area(box1) > box_area(box2) for j, box2 in enumerate(boxes) if i != j):
        is_valid_box = True
        for j, box2 in enumerate(boxes):
            # keep the smaller box
            if i != j and IoU(box1, box2) > iou_threshold and box_area(box1) > box_area(box2):
                is_valid_box = False
                break
        if is_valid_box:
            # add the following 2 lines to include ocr bbox
            if ocr_bbox:
                # only add the box if it does not overlap with any ocr bbox
                if not any(IoU(box1, box3) > iou_threshold and not is_inside(box1, box3) for k, box3 in enumerate(ocr_bbox)):
                    filtered_boxes.append(box1)
            else:
                filtered_boxes.append(box1)
    return torch.tensor(filtered_boxes)

def remove_overlap_new(boxes, iou_threshold, ocr_bbox=None):
    '''
    ocr_bbox format: [{'type': 'text', 'bbox':[x,y], 'interactivity':False, 'content':str }, ...]
    boxes format: [{'type': 'icon', 'bbox':[x,y], 'interactivity':True, 'content':None }, ...]

    '''
    assert ocr_bbox is None or isinstance(ocr_bbox, List)

    def box_area(box):
        return (box[2] - box[0]) * (box[3] - box[1])

    def intersection_area(box1, box2):
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        return max(0, x2 - x1) * max(0, y2 - y1)

    def IoU(box1, box2):
        intersection = intersection_area(box1, box2)
        union = box_area(box1) + box_area(box2) - intersection + 1e-6
        if box_area(box1) > 0 and box_area(box2) > 0:
            ratio1 = intersection / box_area(box1)
            ratio2 = intersection / box_area(box2)
        else:
            ratio1, ratio2 = 0, 0
        return max(intersection / union, ratio1, ratio2)

    def is_inside(box1, box2):
        # return box1[0] >= box2[0] and box1[1] >= box2[1] and box1[2] <= box2[2] and box1[3] <= box2[3]
        intersection = intersection_area(box1, box2)
        ratio1 = intersection / box_area(box1)
        return ratio1 > 0.80

    # boxes = boxes.tolist()
    filtered_boxes = []
    if ocr_bbox:
        filtered_boxes.extend(ocr_bbox)
    # print('ocr_bbox!!!', ocr_bbox)
    for i, box1_elem in enumerate(boxes):
        box1 = box1_elem['bbox']
        is_valid_box = True
        for j, box2_elem in enumerate(boxes):
            # keep the smaller box
            box2 = box2_elem['bbox']
            if i != j and IoU(box1, box2) > iou_threshold and box_area(box1) > box_area(box2):
                is_valid_box = False
                break
        if is_valid_box:
            if ocr_bbox:
                # keep yolo boxes + prioritize ocr label
                box_added = False
                ocr_labels = ''
                for box3_elem in ocr_bbox:
                    if not box_added:
                        box3 = box3_elem['bbox']
                        if is_inside(box3, box1): # ocr inside icon
                            # box_added = True
                            # delete the box3_elem from ocr_bbox
                            try:
                                # gather all ocr labels
                                ocr_labels += box3_elem['content'] + ' '
                                filtered_boxes.remove(box3_elem)
                            except:
                                continue
                            # break
                        elif is_inside(box1, box3): # icon inside ocr, don't added this icon box, no need to check other ocr bbox bc no overlap between ocr bbox, icon can only be in one ocr box
                            box_added = True
                            break
                        else:
                            continue
                if not box_added:
                    if ocr_labels:
                        filtered_boxes.append({'type': 'icon', 'bbox': box1_elem['bbox'], 'interactivity': True, 'content': ocr_labels, 'source':'box_yolo_content_ocr'})
                    else:
                        filtered_boxes.append({'type': 'icon', 'bbox': box1_elem['bbox'], 'interactivity': True, 'content': None, 'source':'box_yolo_content_yolo'})
            else:
                filtered_boxes.append(box1)
    return filtered_boxes  # torch.tensor(filtered_boxes)

def load_image(image_path: str) -> Tuple[np.ndarray, torch.Tensor]:
    # Load image
    image_source = Image.open(image_path).convert("RGB")
    image = np.asarray(image_source)

    # Manual conversion that linter will understand
    resized = image_source.resize((800, 800))
    resized_array = np.array(resized, dtype=np.float32) / 255.0

    # Convert to tensor manually
    image_transformed = torch.from_numpy(resized_array).permute(2, 0, 1)

    # Apply normalization
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    image_transformed = (image_transformed - mean) / std

    return image, image_transformed

def annotate(image_source: np.ndarray, boxes: torch.Tensor, logits: torch.Tensor, phrases: List[str], text_scale: float,
             text_padding=5, text_thickness=2, thickness=3) -> Tuple[np.ndarray, Dict]:

    h, w, _ = image_source.shape
    print(f"\n📝 [ANNOTATE-DEBUG] Input image size: {w}x{h}")

    # Scale boxes to pixel coordinates
    boxes = boxes * torch.Tensor([w, h, w, h])

    # Convert to xyxy format for drawing
    xyxy = box_convert(boxes=boxes, in_fmt="cxcywh", out_fmt="xyxy").numpy()
    xywh_for_clicks = box_convert(torch.tensor(xyxy), in_fmt="xyxy", out_fmt="xywh").numpy()

    detections = sv.Detections(xyxy=xyxy)

    # ✅ FIX: Use standalone class (no inheritance)
    class SmartAnnotator:
        def __init__(self, text_scale, text_padding, text_thickness, thickness):
            self.text_scale = text_scale
            self.text_padding = text_padding
            self.text_thickness = text_thickness
            self.thickness = thickness

        def draw_annotations(self, scene: np.ndarray, detections: sv.Detections, labels: Optional[List[str]] = None) -> np.ndarray:
            """Enhanced annotator with smart label placement"""
            annotated_scene = scene.copy()

            for i, (xyxy_coords, label) in enumerate(zip(detections.xyxy, labels or [])):
                x1, y1, x2, y2 = xyxy_coords

                # ✅ Calculate text size for positioning
                font = cv2.FONT_HERSHEY_SIMPLEX
                # ✅ BIGGER text scale for better visibility
                bigger_text_scale = self.text_scale * 1.5  # 50% bigger
                text_thickness_bold = max(2, self.text_thickness + 1)  # Bolder text

                (text_width, text_height), baseline = cv2.getTextSize(
                    label, font, bigger_text_scale, text_thickness_bold)

                # ✅ Smart label placement logic
                label_padding = self.text_padding + 2  # Extra padding
                label_height = text_height + baseline + 2 * label_padding

                # Check if label would go above image boundary
                if y1 - label_height < 0:
                    # ✅ Place label BELOW the box instead of above
                    label_y1 = int(y2)
                    label_y2 = int(y2 + label_height)
                    text_y = int(y2 + text_height + label_padding)
                    placement = "BELOW"
                else:
                    # ✅ Normal placement ABOVE the box
                    label_y1 = int(y1 - label_height)
                    label_y2 = int(y1)
                    text_y = int(y1 - label_padding)
                    placement = "ABOVE"

                # Ensure label doesn't go outside image horizontally
                label_x1 = max(0, int(x1))
                label_x2 = min(w, int(x1 + text_width + 2 * label_padding))

                # Ensure label doesn't go outside image vertically
                label_y1 = max(0, label_y1)
                label_y2 = min(h, label_y2)
                text_y = max(text_height, min(h - baseline, text_y))

                # ✅ Draw background rectangle for label
                cv2.rectangle(
                    annotated_scene,
                    (label_x1, label_y1),
                    (label_x2, label_y2),
                    (0, 0, 0),  # Black background
                    -1  # Filled
                )

                # ✅ Draw white border around label background
                cv2.rectangle(
                    annotated_scene,
                    (label_x1, label_y1),
                    (label_x2, label_y2),
                    (255, 255, 255),  # White border
                    1
                )

                # ✅ Draw the text label
                cv2.putText(
                    annotated_scene,
                    label,
                    (label_x1 + label_padding, text_y),
                    font,
                    bigger_text_scale,  # Bigger text
                    (255, 255, 255),   # White text
                    self.text_thickness,  # Bolder text
                    cv2.LINE_AA
                )

                # ✅ Draw the bounding box
                cv2.rectangle(
                    annotated_scene,
                    (int(x1), int(y1)),
                    (int(x2), int(y2)),
                    (0, 255, 0),  # Green box
                    self.thickness
                )

                # Debug info
                print(f"📍 [LABEL-{i}] {placement}: bbox({x1:.0f},{y1:.0f},{x2:.0f},{y2:.0f}) -> label({label_x1},{label_y1},{label_x2},{label_y2})")

            return annotated_scene

    # ✅ Use the standalone annotator
    labels = [f"{i}" for i in range(boxes.shape[0])]  # Number labels 0, 1, 2, ...

    smart_annotator = SmartAnnotator(
        text_scale=text_scale,
        text_padding=text_padding,
        text_thickness=text_thickness,
        thickness=thickness
    )

    annotated_frame = smart_annotator.draw_annotations(
        scene=image_source.copy(),
        detections=detections,
        labels=labels
    )

    label_coordinates = {f"{i}": xywh_for_clicks[i] for i in range(len(phrases))}

    return annotated_frame, label_coordinates

def predict(model, image, caption, box_threshold, text_threshold):
    """ Use huggingface model to replace the original model
    """
    model, processor = model['model'], model['processor']
    device = model.device

    inputs = processor(images=image, text=caption, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model(**inputs)

    results = processor.post_process_grounded_object_detection(
        outputs,
        inputs.input_ids,
        box_threshold=box_threshold, # 0.4,
        text_threshold=text_threshold, # 0.3,
        target_sizes=[image.size[::-1]]
    )[0]
    boxes, logits, phrases = results["boxes"], results["scores"], results["labels"]
    return boxes, logits, phrases

def calculate_adaptive_yolo_params(ui_stats, base_conf=0.4, base_iou=0.3):
    """Calculate adaptive YOLO parameters"""

    # ✅ Adjust confidence based on UI characteristics
    conf_multiplier = 1.0
    ui_density = ui_stats.get('ui_density', 0.5)
    contrast = ui_stats.get('contrast', 0.5)

    # Dense UIs - lower threshold to catch more elements
    if ui_density > 0.3:
        conf_multiplier *= 0.85
    elif ui_density < 0.15:
        conf_multiplier *= 1.15

    # High contrast - more reliable detections
    if contrast > 0.6:
        conf_multiplier *= 0.9
    elif contrast < 0.3:
        conf_multiplier *= 1.1

    # ✅ Adjust IoU based on density
    iou_multiplier = 1.0
    if ui_density > 0.4:
        iou_multiplier *= 0.85  # More aggressive NMS for dense UIs
    elif ui_density < 0.2:
        iou_multiplier *= 1.2   # Less aggressive for sparse UIs

    # ✅ Apply multipliers and clamp
    adaptive_conf = max(0.1, min(0.8, base_conf * conf_multiplier))
    adaptive_iou = max(0.1, min(0.7, base_iou * iou_multiplier))

    return adaptive_conf, adaptive_iou

def analyze_ui_characteristics_simple(image_np):
    """Lightweight UI analysis for adaptive parameters"""
    h, w = image_np.shape[:2]
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

    # ✅ Calculate key metrics
    contrast = gray.std() / 255.0
    brightness = gray.mean() / 255.0

    # ✅ Edge density (UI complexity indicator)
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size

    # ✅ Color complexity
    unique_colors = len(np.unique(image_np.reshape(-1, 3), axis=0))
    color_complexity = min(unique_colors / (w * h * 0.001), 1.0)

    ui_density = edge_density * color_complexity

    return {
        'contrast': contrast,
        'brightness': brightness,
        'edge_density': edge_density,
        'ui_density': ui_density,
        'resolution': (w, h)
    }

def predict_yolo(model, image, box_threshold, imgsz, scale_img, iou_threshold=0.5):
    """UI-optimized detection with intelligent duplicate removal"""
    print("[TIMING] Starting UI-optimized YOLO prediction...")
    yolo_start_time = time.time()

    w, h = image.size

    # Step 1: Aggressive detection to catch everything
    ui_conf_threshold = 0.02
    ui_iou_threshold = 0.1  # Keep low for initial detection

    result = model.predict(
        source=image,
        conf=ui_conf_threshold,
        iou=ui_iou_threshold,
        imgsz=imgsz,
        verbose=False
    )

    if len(result[0].boxes) == 0:
        return torch.empty((0, 4)), torch.empty((0,)), []

    boxes = result[0].boxes.xyxy
    confidences = result[0].boxes.conf

    # Step 2: Intelligent UI-specific NMS
    print(f"🔄 [DEDUP] Processing {len(boxes)} raw detections...")

    # Convert to numpy for processing
    boxes_np = boxes.cpu().numpy()
    conf_np = confidences.cpu().numpy()

    # Skip individual NMS here - will be handled by unified NMS later
    phrases = [str(i) for i in range(len(boxes))]

    yolo_end_time = time.time()
    print(f"[TIMING] YOLO prediction completed: {len(boxes)} raw boxes in {yolo_end_time - yolo_start_time:.3f} seconds")
    print("   🔧 Note: NMS will be applied by unified system later")

    return boxes, confidences, phrases

def intelligent_ui_nms(boxes, scores, iou_threshold=0.3):
    """Smart NMS designed for UI elements"""
    if len(boxes) == 0:
        return []

    # Sort by confidence (highest first)
    sorted_indices = np.argsort(scores)[::-1]

    keep = []
    processed = set()

    for i in sorted_indices:
        if i in processed:
            continue

        keep.append(i)
        current_box = boxes[i]

        # Check against remaining boxes
        for j in sorted_indices:
            if j <= i or j in processed:
                continue

            other_box = boxes[j]

            # Calculate IoU
            iou = calculate_iou(current_box, other_box)

            # UI-specific logic: remove overlaps but preserve small adjacent elements
            if iou > iou_threshold:
                # Check if boxes are very different sizes (keep both if size difference is large)
                area1 = (current_box[2] - current_box[0]) * (current_box[3] - current_box[1])
                area2 = (other_box[2] - other_box[0]) * (other_box[3] - other_box[1])
                size_ratio = min(area1, area2) / max(area1, area2)

                if size_ratio < 0.3:  # Very different sizes - keep both
                    continue

                # Mark smaller confidence box for removal
                processed.add(j)

    return keep

def calculate_iou(box1, box2):
    """Calculate Intersection over Union"""
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    intersection = (x2 - x1) * (y2 - y1)
    area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
    area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0

def adaptive_box_filtering_balanced(boxes, confidences, w, h, ui_stats):
    """RESTORED: Smart filtering but more permissive"""
    if len(boxes) == 0:
        return torch.empty((0, 4)), torch.empty((0,))

    filtered_boxes = []
    filtered_conf = []

    for box, confidence in zip(boxes, confidences):
        x1, y1, x2, y2 = box.cpu().numpy()
        width = abs(x2 - x1)
        height = abs(y2 - y1)
        area = width * height

        # ✅ LESS AGGRESSIVE filtering - keep more boxes
        area_ratio = area / (w * h)

        # Only remove obviously bad boxes
        if (area_ratio > 0.6 or           # Covers more than 60% (was 8%)
            area < 50 or                  # Smaller than 50px (was 400px)
            width < 3 or height < 3 or    # Too thin (was more restrictive)
            width/height > 20 or height/width > 20):  # Extreme aspect ratios
            continue

        filtered_boxes.append(box)
        filtered_conf.append(confidence)

    return (torch.stack(filtered_boxes) if filtered_boxes else torch.empty((0, 4)),
            torch.stack(filtered_conf) if filtered_conf else torch.empty((0,)))

def int_box_area(box, w, h):
    x1, y1, x2, y2 = box
    int_box = [int(x1*w), int(y1*h), int(x2*w), int(y2*h)]
    area = (int_box[2] - int_box[0]) * (int_box[3] - int_box[1])
    return area

def remove_center_large_boxes(boxes, image_width, image_height, center_area_threshold=0.4):
    """Remove boxes that cover the center area and are too large"""
    filtered_boxes = []
    center_x, center_y = image_width/2, image_height/2

    for box in boxes:
        if isinstance(box, dict):
            bbox = box['bbox']
        else:
            bbox = box

        if all(coord <= 1.0 for coord in bbox):
            x1, y1, x2, y2 = bbox[0]*image_width, bbox[1]*image_height, bbox[2]*image_width, bbox[3]*image_height
        else:
            x1, y1, x2, y2 = bbox

        # Check if box covers center and is large
        box_center_x, box_center_y = (x1 + x2)/2, (y1 + y2)/2
        width, height = abs(x2 - x1), abs(y2 - y1)
        area_ratio = (width * height) / (image_width * image_height)

        # Remove boxes that:
        # 1. Are centered on screen
        # 2. Cover significant area
        # 3. Span most of the width or height
        is_center_box = (abs(box_center_x - center_x) < image_width * 0.2 and
                        abs(box_center_y - center_y) < image_height * 0.2)
        is_large = area_ratio > 0.08
        spans_width = width > image_width * 0.4
        spans_height = height > image_height * 0.4

        if is_center_box and is_large and (spans_width or spans_height):
            print(f"[MANUAL-FILTER] Removing center large box: {width:.0f}x{height:.0f} ({area_ratio:.1%})")
            continue

        filtered_boxes.append(box)

    return filtered_boxes

def debug_final_click_coordinates(label_coordinates, image_width, image_height, filtered_boxes_elem):
    """Debug the exact coordinates that will be used for clicking - FIXED VERSION"""
    print(f"\n🎯 [CLICK-DEBUG] Final click coordinates analysis")
    print(f"Image size: {image_width}x{image_height}")

    for i, (label, coords) in enumerate(list(label_coordinates.items())[:10]):
        # Get the corresponding element info
        if i < len(filtered_boxes_elem):
            elem = filtered_boxes_elem[i]
            box_type = elem.get('type', 'unknown')
            content = elem.get('content', 'None')
            if content and isinstance(content, str):
                content = content[:30]
        else:
            box_type = 'unknown'
            content = 'N/A'

        # coords should be in xywh format from the annotate function
        if len(coords) == 4:
            x, y, w, h = coords

            # ✅ FIX: Show actual precision values, not rounded
            print(f"\n  Label {label} ({box_type}): '{content}'")
            print(f"    Box XYWH: x={x:.6f}, y={y:.6f}, w={w:.6f}, h={h:.6f}")

            # Calculate click center (this is where the AI will click)
            click_x = x + w/2
            click_y = y + h/2

            print(f"    👆 CLICK POINT: ({click_x:.6f}, {click_y:.6f})")

            # Convert to actual pixels for verification
            if all(coord <= 1.0 for coord in coords):
                pixel_click_x = click_x * image_width
                pixel_click_y = click_y * image_height
                print(f"    📍 PIXEL CLICK: ({pixel_click_x:.1f}, {pixel_click_y:.1f})")

            # Check for coordinate issues
            if w < 0.001 or h < 0.001:
                print(f"    ⚠️  Very small box size - might cause click issues")
            if click_y < 0.01:
                print(f"    ⚠️  Click very close to top edge")

def debug_ratio_conversion(label_coordinates, output_coord_in_ratio, w, h):
    """Debug coordinate ratio conversion"""
    print(f"\n🔄 [RATIO-DEBUG] output_coord_in_ratio={output_coord_in_ratio}")

    if output_coord_in_ratio:
        print("⚠️  Coordinates are being converted to ratios (0-1 range)")
        print("This means click coordinates need to be multiplied by image size!")

        for label, coords in list(label_coordinates.items())[:3]:
            x_ratio, y_ratio, w_ratio, h_ratio = coords

            # Convert back to pixels to see actual click point
            actual_click_x = (x_ratio + w_ratio/2) * w
            actual_click_y = (y_ratio + h_ratio/2) * h

            print(f"  Label {label}:")
            print(f"    Ratio coords: ({x_ratio:.3f}, {y_ratio:.3f}, {w_ratio:.3f}, {h_ratio:.3f})")
            print(f"    👆 Actual click point: ({actual_click_x:.1f}, {actual_click_y:.1f})")
    else:
        print("✅ Coordinates are in pixel format")

def analyze_yolo_quality(boxes, w, h):
    """Simple quality analysis for YOLO results"""

    if len(boxes) == 0:
        return {'quality_score': 0.0, 'suggestions': ['No boxes detected']}

    # ✅ Calculate metrics
    areas = []
    for box in boxes:
        if isinstance(box, torch.Tensor):
            x1, y1, x2, y2 = box.cpu().numpy()
        else:
            x1, y1, x2, y2 = box
        area = abs(x2 - x1) * abs(y2 - y1)
        areas.append(area / (w * h))  # Normalize by screen area

    avg_area = np.mean(areas)
    area_std = np.std(areas)
    total_coverage = sum(areas)

    # ✅ Quality scoring
    quality_score = 0.5

    # Good number of elements (5-30)
    if 5 <= len(boxes) <= 30:
        quality_score += 0.2
    elif len(boxes) < 5:
        quality_score -= 0.2
    elif len(boxes) > 50:
        quality_score -= 0.3

    # Reasonable average size
    if 0.001 <= avg_area <= 0.05:
        quality_score += 0.2

    # Low variance in sizes (consistency)
    if area_std < 0.02:
        quality_score += 0.1

    # Reasonable total coverage
    if 0.05 <= total_coverage <= 0.3:
        quality_score += 0.1

    return {
        'quality_score': max(0, min(1, quality_score)),
        'element_count': len(boxes),
        'avg_area': avg_area,
        'total_coverage': total_coverage,
        'area_variance': area_std
    }

# ✅ FIXED - ensure consistent coordinate format:
def create_consistent_yolo_elements(boxes_tensor, w, h):
    """Create YOLO elements with consistent normalized coordinates"""
    elements = []

    for i, box in enumerate(boxes_tensor):
        # box should already be normalized (0-1 range)
        x1, y1, x2, y2 = box.cpu().numpy() if isinstance(box, torch.Tensor) else box

        # ✅ VERIFY normalization
        if any(coord > 1.1 for coord in [x1, y1, x2, y2]):
            print(f"⚠️ WARNING: Box {i} coordinates seem unnormalized: {[x1, y1, x2, y2]}")
            # Force normalization if needed
            x1, y1, x2, y2 = x1/w, y1/h, x2/w, y2/h

        # ✅ Calculate element properties for classification
        width_px = (x2 - x1) * w
        height_px = (y2 - y1) * h
        area_px = width_px * height_px

        # ✅ Simple but effective classification
        if area_px < 600:
            element_type = 'icon'
            interactivity = True
        elif area_px < 2000:
            element_type = 'button'
            interactivity = True
        elif (x2 - x1) > 0.3 or (y2 - y1) > 0.3:  # Large elements
            element_type = 'container'
            interactivity = False
        else:
            element_type = 'ui_element'
            interactivity = True

        elements.append({
            'type': element_type,
            'bbox': [x1, y1, x2, y2],  # ✅ Ensure list format
            'interactivity': interactivity,
            'content': None,
            'source': f'yolo_{element_type}'
        })

    return elements

def classify_element(x1, y1, x2, y2, width, height, area, screen_w, screen_h):
    """Simple element classification based on size and position"""

    # ✅ Position analysis
    is_top = y1 < 0.15
    is_bottom = y2 > 0.85
    is_edge = x1 < 0.05 or x2 > 0.95

    # ✅ Size analysis
    area_ratio = area / (screen_w * screen_h)
    aspect_ratio = width / height if height > 0 else 1.0

    # ✅ Classification logic
    if area < 600:  # Small elements
        if is_top or is_bottom:
            return 'toolbar_icon', True
        else:
            return 'icon', True

    elif area < 2000:  # Medium elements
        if aspect_ratio > 3.0:
            return 'button', True
        elif 0.7 <= aspect_ratio <= 1.3:
            return 'icon', True
        else:
            return 'ui_control', True

    else:  # Large elements
        if area_ratio > 0.1:
            return 'container', False
        elif aspect_ratio > 4.0:
            return 'banner', False
        elif is_top or is_bottom:
            return 'navigation', True
        else:
            return 'panel', False

def categorize_element_size(area, screen_area):
    """Categorize element by size"""
    ratio = area / screen_area
    if ratio < 0.001:
        return 'tiny'
    elif ratio < 0.01:
        return 'small'
    elif ratio < 0.05:
        return 'medium'
    else:
        return 'large'

def create_normalized_ocr_elements(ocr_bbox, ocr_text, w, h):
    """Create OCR elements with guaranteed normalized coordinates"""
    elements = []

    for box, txt in zip(ocr_bbox, ocr_text):
        # OCR boxes from check_ocr_box should already be normalized when divided by w,h
        # Verify this assumption
        if isinstance(box, (list, tuple)) and len(box) == 4:
            x1, y1, x2, y2 = box

            # Contract: ALL coordinates must be normalized here
            assert 0 <= x1 <= 1 and 0 <= y1 <= 1 and 0 <= x2 <= 1 and 0 <= y2 <= 1, f"OCR box not normalized: {box}"

            elements.append({
                'type': 'text',
                'bbox': [x1, y1, x2, y2],  # Guaranteed normalized
                'interactivity': False,
                'content': txt,
                'source': 'ocr'
            })

    return elements

def create_normalized_yolo_elements(yolo_boxes, w, h):
    """Create YOLO elements with guaranteed normalized coordinates"""
    elements = []

    for i, box in enumerate(yolo_boxes):
        if isinstance(box, torch.Tensor):
            x1, y1, x2, y2 = box.cpu().numpy()
        else:
            x1, y1, x2, y2 = box

        # Contract: Input boxes MUST already be normalized by caller
        # If not, we have a bug in the caller, not here
        if not (0 <= x1 <= 1 and 0 <= y1 <= 1 and 0 <= x2 <= 1 and 0 <= y2 <= 1):
            raise ValueError(f"YOLO box {i} not normalized: [{x1}, {y1}, {x2}, {y2}] - this is a bug in the caller!")

        # Simple classification based on size
        width = (x2 - x1) * w
        height = (y2 - y1) * h
        area = width * height

        if area < 600:
            element_type, interactivity = 'icon', True
        elif area < 2000:
            element_type, interactivity = 'button', True
        elif (x2 - x1) > 0.3 or (y2 - y1) > 0.3:
            element_type, interactivity = 'container', False
        else:
            element_type, interactivity = 'ui_element', True

        elements.append({
            'type': element_type,
            'bbox': [x1, y1, x2, y2],  # Guaranteed normalized
            'interactivity': interactivity,
            'content': None,
            'source': 'yolo'
        })

    return elements

def debug_annotation_pipeline(parsed_content_list, image_width, image_height):
    """Debug annotation accuracy and coordinate consistency"""
    print(f"\n🔍 [ANNOTATION-DEBUG] Analyzing {len(parsed_content_list)} elements")
    print(f"📐 Image size: {image_width}x{image_height}")

    issues_found = []

    for i, elem in enumerate(parsed_content_list):
        element_type = elem.get('type', 'unknown')
        bbox = elem.get('bbox', [0, 0, 0, 0])
        content = elem.get('content', '')
        source = elem.get('source', 'unknown')

        # ✅ Check coordinate format and validity
        if len(bbox) != 4:
            issues_found.append(f"Element {i}: Invalid bbox length: {len(bbox)}")
            continue

        x1, y1, x2, y2 = bbox

        # Check if coordinates are normalized (0-1) or pixel values
        coords_normalized = all(0 <= coord <= 1 for coord in bbox)

        if not coords_normalized:
            issues_found.append(f"Element {i}: Coordinates not normalized: {bbox}")

        # Check for zero/invalid coordinates
        if all(coord == 0.0 for coord in bbox):
            issues_found.append(f"Element {i}: All coordinates are zero")

        if x1 >= x2 or y1 >= y2:
            issues_found.append(f"Element {i}: Invalid bbox geometry: x1={x1}, y1={y1}, x2={x2}, y2={y2}")

        # Calculate center for verification
        center_x = (x1 + x2) / 2
        center_y = (y1 + y2) / 2

        # Check text-coordinate consistency for OCR elements
        if source == 'ocr' and content:
            # For OCR elements, verify text isn't obviously wrong for position
            if center_y < 0.1:  # Top 10% of screen
                if len(content) > 50:  # Very long text at top (suspicious)
                    issues_found.append(f"Element {i}: Suspiciously long text at top: '{content[:30]}...'")

        # Report element details
        width = (x2 - x1) * image_width if coords_normalized else (x2 - x1)
        height = (y2 - y1) * image_height if coords_normalized else (y2 - y1)

        print(f"  Element {i} ({source}): type={element_type}, size={width:.0f}x{height:.0f}")
        print(f"    📍 Center: ({center_x:.3f}, {center_y:.3f})")
        print(f"    📦 Bbox: [{x1:.3f}, {y1:.3f}, {x2:.3f}, {y2:.3f}]")
        if content:
            print(f"    📝 Text: '{content[:50]}{'...' if len(content) > 50 else ''}'")
        print()

    # ✅ Check for element ID consistency
    visual_elements = [i for i, elem in enumerate(parsed_content_list)
                      if elem.get('interactivity', False)]
    text_elements = [i for i, elem in enumerate(parsed_content_list)
                    if not elem.get('interactivity', False)]

    print(f"📊 [SUMMARY] Total: {len(parsed_content_list)}, Clickable: {len(visual_elements)}, Text: {len(text_elements)}")

    if issues_found:
        print(f"\n⚠️  [ISSUES FOUND] {len(issues_found)} potential problems:")
        for issue in issues_found[:10]:  # Show first 10 issues
            print(f"   • {issue}")
    else:
        print("✅ [VALIDATION] No obvious coordinate/text issues found")

    return issues_found

def remove_false_positives(elements, image_np, confidence_threshold=0.15):
    """Remove false positive detections using image analysis"""

    filtered_elements = []
    h, w = image_np.shape[:2]

    for i, elem in enumerate(elements):
        bbox = elem['bbox']

        # Convert normalized to pixel coordinates
        x1, y1, x2, y2 = int(bbox[0]*w), int(bbox[1]*h), int(bbox[2]*w), int(bbox[3]*h)

        # Extract region
        if x2 <= x1 or y2 <= y1:
            continue

        region = image_np[y1:y2, x1:x2]
        if region.size == 0:
            continue

        # Calculate region statistics
        region_stats = analyze_region_content(region)

        # Filter out false positives based on element source
        if elem.get('source') == 'ocr':
            # OCR-specific filtering
            text_content = elem.get('content', '')

            # Remove if text looks like OCR noise
            if (len(text_content) <= 2 and
                not text_content.isalnum() or
                region_stats['edge_density'] < 0.1 or  # No real content
                region_stats['variance'] < 100):       # Too uniform
                print(f"[FILTER] Removing OCR false positive: '{text_content}'")
                continue

        elif elem.get('source') == 'yolo':
            # YOLO-specific filtering
            if (region_stats['edge_density'] < 0.05 or    # No edges/content
                region_stats['variance'] < 50 or          # Too uniform
                region_stats['mean_intensity'] < 20):     # Too dark
                print(f"[FILTER] Removing YOLO false positive in empty area")
                continue

        filtered_elements.append(elem)

    print(f"✅ [FALSE-POSITIVE-FILTER] Kept {len(filtered_elements)}/{len(elements)} elements")
    return filtered_elements

def analyze_region_content(region):
    """Analyze if region actually contains meaningful content"""
    if region.size == 0:
        return {'edge_density': 0, 'variance': 0, 'mean_intensity': 0}

    # Convert to grayscale if needed
    if len(region.shape) == 3:
        gray = cv2.cvtColor(region, cv2.COLOR_RGB2GRAY)
    else:
        gray = region

    # Calculate content metrics
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size
    variance = np.var(gray)
    mean_intensity = np.mean(gray)

    return {
        'edge_density': edge_density,
        'variance': variance,
        'mean_intensity': mean_intensity
    }

def detect_paragraph_text(image_np, existing_detections, easyocr_args=None):
    """Specialized detection for paragraph text that normal OCR misses"""

    print("📖 [PARAGRAPH-ENHANCE] Running specialized paragraph detection...")

    # ✅ Very aggressive settings for paragraph text
    paragraph_args = {
        'paragraph': True,  # Enable paragraph mode
        'width_ths': 0.1,   # Very low - catch wide text blocks
        'height_ths': 0.1,  # Very low - catch tall text blocks
        'text_threshold': 0.05,  # Very low confidence
        'low_text': 0.01,   # Ultra low for faint text
        'link_threshold': 0.01,  # Connect distant text
        'slope_ths': 0.5,   # Allow slanted text
        'add_margin': 0.1,  # Add margin around text
        'canvas_size': 2560,  # Higher resolution processing
        'mag_ratio': 1.5,   # Magnification for small text
    }

    try:
        paragraph_result = reader.readtext(image_np, **paragraph_args)

        enhanced_detections = []
        for item in paragraph_result:
            bbox_points = item[0]
            text_content = item[1].strip()
            confidence = item[2] if len(item) >= 3 else 1.0

            # ✅ Focus on longer text blocks (paragraphs)
            if (len(text_content) > 20 and  # Substantial text
                confidence > 0.05 and  # Very low threshold
                not is_already_detected(text_content, existing_detections)):

                enhanced_detections.append((bbox_points, text_content, confidence))
                print(f"✅ [PARAGRAPH-FOUND] '{text_content[:50]}...' (conf: {confidence:.2f})")

        return enhanced_detections

    except Exception as e:
        print(f"[PARAGRAPH-ENHANCE] Error: {e}")
        return []

def is_already_detected(new_text, existing_detections):
    """Check if text is already detected to avoid duplicates"""
    new_words = set(new_text.lower().split())
    for existing_text in existing_detections:
        existing_words = set(existing_text.lower().split())
        # If 70% of words overlap, consider it duplicate
        overlap = len(new_words & existing_words) / len(new_words) if new_words else 0
        if overlap > 0.7:
            return True
    return False

def detect_numerical_data(image_np, existing_detections):
    """Specialized detection for numerical data (MB, %, etc.)"""

    print("🔢 [NUMERICAL-ENHANCE] Running specialized numerical detection...")

    # ✅ Settings optimized for numbers and units
    numerical_args = {
        'paragraph': False,
        'width_ths': 0.3,   # Conservative width
        'height_ths': 0.3,  # Conservative height
        'text_threshold': 0.1,  # Low for small numbers
        'low_text': 0.05,   # Very low for faint numbers
        'link_threshold': 0.3,  # Don't link numbers too aggressively
        'allowlist': '0123456789.,% MBGKTmbgkt',  # Only numbers and units
        'canvas_size': 1920,
        'mag_ratio': 2.0,   # High magnification for small numbers
    }

    try:
        numerical_result = reader.readtext(image_np, **numerical_args)

        enhanced_detections = []
        for item in numerical_result:
            bbox_points = item[0]
            text_content = item[1].strip()
            confidence = item[2] if len(item) >= 3 else 1.0

            # ✅ Focus on numerical patterns
            if (is_numerical_content(text_content) and
                confidence > 0.05 and
                not is_already_detected(text_content, existing_detections)):

                enhanced_detections.append((bbox_points, text_content, confidence))
                print(f"✅ [NUMERICAL-FOUND] '{text_content}' (conf: {confidence:.2f})")

        return enhanced_detections

    except Exception as e:
        print(f"[NUMERICAL-ENHANCE] Error: {e}")
        return []

def is_numerical_content(text):
    """Check if text contains numerical data patterns"""
    import re

    # Patterns for numerical data
    patterns = [
        r'\d+\.?\d*\s*(MB|GB|KB|TB|%)',  # Size units
        r'\d+\.?\d*\s*(MiB|GiB|KiB|TiB)', # Binary units
        r'\d+%',  # Percentages
        r'\d+\.\d+',  # Decimal numbers
        r'^\d+$',  # Pure numbers
    ]

    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    return False

def preserve_important_text_filtering(elements):
    """FIXED: Much more permissive text filtering - only remove obvious noise"""

    preserved = []
    for elem in elements:
        if elem['type'] == 'text':
            text_content = elem.get('content', elem.get('text', '')).strip()

            # ✅ FIXED: Only filter out obvious noise, keep everything else
            should_keep = True

            # Remove only if it's clearly noise (very restrictive removal criteria)
            if (
                len(text_content) == 0 or  # Empty text
                (len(text_content) == 1 and text_content in '.,|_-+=<>[]{}()/#\\') or  # Single noise chars
                (len(text_content) > 1 and len(set(text_content)) == 1 and text_content[0] in '.,|_-+=') or  # Repeated noise chars
                (len(text_content) > 20 and not any(c.isalpha() for c in text_content))  # Very long non-alphabetic strings
            ):
                should_keep = False
                print(f"❌ [FILTER] Removing obvious noise: '{text_content}'")
            else:
                # Keep almost everything else - product names, navigation, UI text, etc.
                should_keep = True

            if should_keep:
                preserved.append(elem)
        else:
            preserved.append(elem)  # Keep all non-text elements

    print(f"✅ [PRESERVE] Text filtering kept {len([e for e in preserved if e['type'] == 'text'])} text elements")
    return preserved

def unified_intelligent_nms(elements, iou_threshold=0.3, preserve_text=True, preserve_small_elements=True):
    """
    Unified NMS system that replaces all 5 existing NMS methods with one intelligent approach.

    This consolidates:
    - remove_overlap() and remove_overlap_new()
    - intelligent_ui_nms()
    - enhanced_nms_filtering()
    - torchvision.ops.nms

    Args:
        elements: List of detection elements with 'bbox', 'type', 'content', etc.
        iou_threshold: Base IoU threshold for overlap detection
        preserve_text: Whether to preserve text elements over UI elements
        preserve_small_elements: Whether to preserve small UI elements that might be buttons/tabs

    Returns:
        List of filtered elements with overlaps removed
    """
    if len(elements) == 0:
        return elements

    print(f"🔄 [UNIFIED-NMS] Processing {len(elements)} elements...")

    # Helper functions
    def get_bbox(element):
        return element.get('bbox', [0, 0, 0, 0])

    def calculate_area(bbox):
        return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])

    def calculate_iou(bbox1, bbox2):
        x1 = max(bbox1[0], bbox2[0])
        y1 = max(bbox1[1], bbox2[1])
        x2 = min(bbox1[2], bbox2[2])
        y2 = min(bbox1[3], bbox2[3])

        if x2 <= x1 or y2 <= y1:
            return 0.0

        intersection = (x2 - x1) * (y2 - y1)
        area1 = calculate_area(bbox1)
        area2 = calculate_area(bbox2)
        union = area1 + area2 - intersection

        return intersection / union if union > 0 else 0.0

    def get_confidence(element):
        return element.get('confidence', 0.8)

    def is_text_element(element):
        return element.get('type', '') == 'text'

    def is_small_ui_element(element, area_threshold=0.001):
        """Detect small UI elements that should be preserved (buttons, tabs, etc.)"""
        bbox = get_bbox(element)
        area = calculate_area(bbox)
        # Small area in normalized coordinates (< 0.1% of screen)
        return area < area_threshold

    # Step 1: Group elements by priority
    # Priority: Text > Small UI elements > Large UI elements
    text_elements = [e for e in elements if is_text_element(e)]
    small_ui_elements = [e for e in elements if not is_text_element(e) and is_small_ui_element(e)]
    large_ui_elements = [e for e in elements if not is_text_element(e) and not is_small_ui_element(e)]

    print(f"   📊 Text: {len(text_elements)}, Small UI: {len(small_ui_elements)}, Large UI: {len(large_ui_elements)}")

    # Step 2: Process each group with appropriate strategies
    kept_elements = []

    # Always keep text elements, but remove text-text overlaps
    if text_elements:
        kept_text = nms_for_text_elements(text_elements, iou_threshold * 0.7)  # Stricter for text
        kept_elements.extend(kept_text)
        print(f"   ✅ Text NMS: {len(text_elements)} → {len(kept_text)} elements")

    # Keep small UI elements, remove only exact duplicates
    if small_ui_elements:
        kept_small = nms_for_small_elements(small_ui_elements, iou_threshold * 1.2)  # More permissive
        kept_elements.extend(kept_small)
        print(f"   ✅ Small UI NMS: {len(small_ui_elements)} → {len(kept_small)} elements")

    # Apply standard NMS to large UI elements
    if large_ui_elements:
        kept_large = nms_for_large_elements(large_ui_elements, iou_threshold)
        kept_elements.extend(kept_large)
        print(f"   ✅ Large UI NMS: {len(large_ui_elements)} → {len(kept_large)} elements")

    # Step 3: Cross-group conflict resolution
    # Remove large UI elements that significantly overlap with text
    if preserve_text and text_elements:
        kept_elements = resolve_text_ui_conflicts(kept_elements, iou_threshold * 0.5)

    print(f"🔄 [UNIFIED-NMS] Final result: {len(elements)} → {len(kept_elements)} elements")
    return kept_elements


def nms_for_text_elements(text_elements, iou_threshold):
    """NMS specifically for text elements - merge nearby text, remove exact duplicates"""
    if len(text_elements) <= 1:
        return text_elements

    # Sort by area (keep larger text boxes when overlapping)
    text_elements.sort(key=lambda x: calculate_area(get_bbox(x)), reverse=True)

    kept = []
    for i, elem1 in enumerate(text_elements):
        bbox1 = get_bbox(elem1)
        should_keep = True

        for j, elem2 in enumerate(kept):
            bbox2 = get_bbox(elem2)
            iou = calculate_iou(bbox1, bbox2)

            if iou > iou_threshold:
                # Check if this is a mergeable case (nearby text)
                if should_merge_text_boxes(elem1, elem2):
                    # Replace kept element with merged version
                    merged = merge_text_elements(elem1, elem2)
                    kept[kept.index(elem2)] = merged
                should_keep = False
                break

        if should_keep:
            kept.append(elem1)

    return kept


def nms_for_small_elements(small_elements, iou_threshold):
    """NMS for small UI elements - very permissive, only remove exact duplicates"""
    if len(small_elements) <= 1:
        return small_elements

    # Sort by confidence
    small_elements.sort(key=lambda x: get_confidence(x), reverse=True)

    kept = []
    for elem1 in small_elements:
        bbox1 = get_bbox(elem1)
        should_keep = True

        for elem2 in kept:
            bbox2 = get_bbox(elem2)
            iou = calculate_iou(bbox1, bbox2)

            # Only remove if almost identical (likely duplicate detection)
            if iou > iou_threshold:
                should_keep = False
                break

        if should_keep:
            kept.append(elem1)

    return kept


def nms_for_large_elements(large_elements, iou_threshold):
    """Standard NMS for large UI elements"""
    if len(large_elements) <= 1:
        return large_elements

    # Sort by confidence
    large_elements.sort(key=lambda x: get_confidence(x), reverse=True)

    kept = []
    for elem1 in large_elements:
        bbox1 = get_bbox(elem1)
        should_keep = True

        for elem2 in kept:
            bbox2 = get_bbox(elem2)
            iou = calculate_iou(bbox1, bbox2)

            if iou > iou_threshold:
                should_keep = False
                break

        if should_keep:
            kept.append(elem1)

    return kept


def resolve_text_ui_conflicts(elements, iou_threshold):
    """Resolve conflicts between text and UI elements, prioritizing text"""
    text_elements = [e for e in elements if is_text_element(e)]
    ui_elements = [e for e in elements if not is_text_element(e)]

    if not text_elements or not ui_elements:
        return elements

    kept_ui = []
    conflicts_resolved = 0

    for ui_elem in ui_elements:
        ui_bbox = get_bbox(ui_elem)
        has_conflict = False

        for text_elem in text_elements:
            text_bbox = get_bbox(text_elem)
            iou = calculate_iou(ui_bbox, text_bbox)

            if iou > iou_threshold:
                has_conflict = True
                conflicts_resolved += 1
                break

        if not has_conflict:
            kept_ui.append(ui_elem)

    if conflicts_resolved > 0:
        print(f"   🔧 Resolved {conflicts_resolved} text-UI conflicts")

    return text_elements + kept_ui


def should_merge_text_boxes(elem1, elem2, distance_threshold=0.02):
    """Check if two text boxes should be merged (are they nearby text fragments?)"""
    bbox1 = get_bbox(elem1)
    bbox2 = get_bbox(elem2)

    # Calculate distance between boxes
    center1 = [(bbox1[0] + bbox1[2])/2, (bbox1[1] + bbox1[3])/2]
    center2 = [(bbox2[0] + bbox2[2])/2, (bbox2[1] + bbox2[3])/2]

    distance = ((center1[0] - center2[0])**2 + (center1[1] - center2[1])**2)**0.5

    return distance < distance_threshold


def merge_text_elements(elem1, elem2):
    """Merge two text elements into one"""
    bbox1 = get_bbox(elem1)
    bbox2 = get_bbox(elem2)

    # Create merged bounding box
    merged_bbox = [
        min(bbox1[0], bbox2[0]),  # min x
        min(bbox1[1], bbox2[1]),  # min y
        max(bbox1[2], bbox2[2]),  # max x
        max(bbox1[3], bbox2[3])   # max y
    ]

    # Merge content
    content1 = elem1.get('content', '')
    content2 = elem2.get('content', '')
    merged_content = f"{content1} {content2}".strip()

    # Create merged element
    merged = elem1.copy()
    merged['bbox'] = merged_bbox
    merged['content'] = merged_content
    merged['confidence'] = max(get_confidence(elem1), get_confidence(elem2))

    return merged


# Helper functions for the unified NMS system
def get_bbox(element):
    return element.get('bbox', [0, 0, 0, 0])


def calculate_area(bbox):
    return (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])


def calculate_iou(bbox1, bbox2):
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])

    if x2 <= x1 or y2 <= y1:
        return 0.0

    intersection = (x2 - x1) * (y2 - y1)
    area1 = calculate_area(bbox1)
    area2 = calculate_area(bbox2)
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def get_confidence(element):
    return element.get('confidence', 0.8)


def is_text_element(element):
    return element.get('type', '') == 'text'

def get_som_labeled_img(image_source: Union[str, Image.Image], model=None, BOX_TRESHOLD=0.25, output_coord_in_ratio=False, ocr_bbox=None, text_scale=0.4, text_padding=5, draw_bbox_config=None, caption_model_processor=None, ocr_text=[], use_local_semantics=False, iou_threshold=0.3,prompt=None, scale_img=False, imgsz=(1024,1024), batch_size=128, use_florence_captioning=False):
    som_start_time = time.time()
    print("[TIMING] Starting SOM labeled image processing...")

    if isinstance(image_source, str):
        image_source = Image.open(image_source)
    image_source = image_source.convert("RGB")
    w, h = image_source.size

    print(f"🔧 [COORDINATE-FLOW] Image size: {w}x{h}")

    # ✅ YOLO prediction - returns pixel coordinates
    yolo_start = time.time()
    xyxy, logits, phrases = predict_yolo(
        model=model,
        image=image_source,
        box_threshold=BOX_TRESHOLD,
        imgsz=imgsz,
        scale_img=scale_img,
        iou_threshold=iou_threshold
    )
    yolo_end = time.time()
    print(f"[TIMING] YOLO prediction completed in {yolo_end - yolo_start:.3f} seconds")

    print(f"🔧 [COORDINATE-FLOW] YOLO returned {len(xyxy)} boxes in PIXEL coordinates")

    # ✅ CRITICAL: Normalize YOLO coordinates immediately
    norm_start = time.time()
    if len(xyxy) > 0:
        # Verify YOLO returned pixel coordinates
        sample_box = xyxy[0].cpu().numpy()
        print(f"🔧 [COORDINATE-FLOW] Sample YOLO box before normalization: {sample_box}")
        print(f"🔧 [COORDINATE-FLOW] Image dimensions for normalization: {w}x{h}")

        # ✅ ENHANCED: Check for potential displacement issues
        if sample_box[0] < 0 or sample_box[1] < 0:
            print(f"⚠️  [DISPLACEMENT-WARNING] Negative coordinates detected: {sample_box}")
        if sample_box[2] > w or sample_box[3] > h:
            print(f"⚠️  [DISPLACEMENT-WARNING] Coordinates exceed image bounds: {sample_box} vs {w}x{h}")

        # Normalize to 0-1 range
        xyxy = xyxy / torch.Tensor([w, h, w, h]).to(xyxy.device)

        # Verify normalization worked
        sample_box_norm = xyxy[0].cpu().numpy()
        print(f"🔧 [COORDINATE-FLOW] Sample YOLO box after normalization: {sample_box_norm}")

        if any(coord > 1.1 for coord in sample_box_norm):
            raise ValueError(f"YOLO normalization FAILED! Box still in pixel coordinates: {sample_box_norm}")

        # ✅ DEBUG: Additional coordinate validation
        if any(coord < -0.1 for coord in sample_box_norm):
            print(f"⚠️  [DISPLACEMENT-WARNING] Negative normalized coordinates: {sample_box_norm}")

    norm_end = time.time()
    print(f"[TIMING] YOLO coordinate normalization completed in {norm_end - norm_start:.3f} seconds")

    # ✅ Convert image to numpy for annotation
    image_np = np.asarray(image_source)
    phrases = [str(i) for i in range(len(xyxy))]

    # ✅ OCR processing with timing
    ocr_processing_start = time.time()
    if ocr_bbox:
        print(f"🔧 [COORDINATE-FLOW] OCR provided {len(ocr_bbox)} boxes (expecting normalized)")

        # Verify OCR boxes are normalized (they should be now!)
        sample_ocr = ocr_bbox[0]
        print(f"🔧 [COORDINATE-FLOW] Sample OCR box: {sample_ocr}")

        if any(coord > 1.1 for coord in sample_ocr):
            raise ValueError(f"OCR returned pixel coordinates but should return normalized! Box: {sample_ocr}")
        else:
            print("✅ OCR boxes properly normalized")
    else:
        print('🔧 [COORDINATE-FLOW] No OCR boxes provided')
        ocr_bbox = []
    ocr_processing_end = time.time()
    print(f"[TIMING] OCR processing completed in {ocr_processing_end - ocr_processing_start:.3f} seconds")

    # ✅ Create elements with guaranteed normalized coordinates
    element_creation_start = time.time()
    print(f"🔧 [COORDINATE-FLOW] Creating OCR elements...")
    ocr_bbox_elem = create_normalized_ocr_elements(ocr_bbox, ocr_text, w, h)

    print(f"🔧 [COORDINATE-FLOW] Creating YOLO elements...")
    xyxy_elem = create_normalized_yolo_elements(xyxy, w, h)
    element_creation_end = time.time()
    print(f"[TIMING] Element creation completed in {element_creation_end - element_creation_start:.3f} seconds")

    # ✅ FIXED: Proper filtering order and consistent thresholds
    filtering_start = time.time()
    print("🔧 [FILTERING] Applying consistent size filtering...")

    # Detect content type once
    image_type = detect_image_type(image_np)
    print(f"🔧 [FILTERING] Detected image type: {image_type}")

    # Apply consistent size filtering - no duplicates
    xyxy_elem = filter_oversized_boxes(xyxy_elem, w, h, max_width_ratio=0.3, max_height_ratio=0.3, max_area_ratio=0.08)
    ocr_bbox_elem = filter_oversized_boxes(ocr_bbox_elem, w, h, max_width_ratio=0.7, max_height_ratio=0.2, max_area_ratio=0.12)

    # Apply specialized YOLO filtering (ONLY ONCE)
    xyxy_elem = filter_oversized_yolo_boxes(xyxy_elem, w, h, image_type)

    # Consistent minimum area thresholds
    xyxy_elem = filter_small_boxes(xyxy_elem, min_area=300, image_width=w, image_height=h)  # Slightly lower for better detection
    ocr_bbox_elem = filter_small_boxes(ocr_bbox_elem, min_area=150, image_width=w, image_height=h)  # Lower for small UI text

    print(f"🔧 [FILTERING] After filtering: {len(xyxy_elem)} YOLO + {len(ocr_bbox_elem)} OCR elements")
    filtering_end = time.time()
    print(f"[TIMING] Filtering completed in {filtering_end - filtering_start:.3f} seconds")

    # ✅ REORDERED: NMS FIRST to remove overlapping/oversized boxes, then final filtering
    combination_start = time.time()
    filtered_boxes_elem = ocr_bbox_elem + xyxy_elem

    print(f"🔧 [NMS-FIRST] Starting with {len(filtered_boxes_elem)} total elements")

    # ✅ Apply NMS FIRST to eliminate problematic overlaps and oversized boxes
    nms_start = time.time()
    try:
        filtered_boxes_elem = unified_intelligent_nms(
            filtered_boxes_elem,
            iou_threshold=iou_threshold * 0.8,  # Slightly more aggressive for better overlap removal
            preserve_text=True,
            preserve_small_elements=True
        )
        print(f"🔧 [NMS-FIRST] After unified NMS: {len(filtered_boxes_elem)} elements remaining")
    except Exception as e:
        print(f"❌ Unified NMS error: {e}")
        # Fallback - continue without NMS if there's an error

    nms_end = time.time()
    print(f"[TIMING] NMS completed in {nms_end - nms_start:.3f} seconds")

    # ✅ FINAL FILTERING: Remove any remaining problematic boxes after NMS
    final_filter_start = time.time()
    initial_count = len(filtered_boxes_elem)

    # Apply conservative final filtering to clean up any remaining issues
    filtered_boxes_elem = [elem for elem in filtered_boxes_elem
                          if elem.get('bbox') and len(elem['bbox']) == 4]  # Valid bbox

    final_count = len(filtered_boxes_elem)
    if final_count != initial_count:
        print(f"🔧 [FINAL-CLEANUP] Removed {initial_count - final_count} malformed elements")

    final_filter_end = time.time()
    print(f"[TIMING] Final filtering completed in {final_filter_end - final_filter_start:.3f} seconds")

    # ✅ VERIFY: All elements should have normalized coordinates
    print(f"🔧 [COORDINATE-VERIFICATION] Checking {len(filtered_boxes_elem)} combined elements:")
    for i, elem in enumerate(filtered_boxes_elem[:5]):  # Check first 5
        bbox = elem['bbox']
        if any(coord > 1.1 for coord in bbox):
            raise ValueError(f"Element {i} has unnormalized coordinates: {bbox} - THIS IS A BUG!")
        elif any(coord < 0 for coord in bbox):
            raise ValueError(f"Element {i} has negative coordinates: {bbox} - THIS IS A BUG!")
    print("✅ All elements have properly normalized coordinates")
    combination_end = time.time()
    print(f"[TIMING] Element combination completed in {combination_end - combination_start:.3f} seconds")

    if 'preserve_important_text_filtering' in globals():
        false_positive_start = time.time()
        try:
            filtered_boxes_elem = preserve_important_text_filtering(filtered_boxes_elem)
            print(f"✅ [CONSERVATIVE-FILTER] Kept {len(filtered_boxes_elem)} elements")
        except Exception as e:
            print(f"❌ Error in preserve_important_text_filtering: {e}")
            pass  # Use existing filtering if enhancement not available
        false_positive_end = time.time()
        print(f"[TIMING] False positive filtering completed in {false_positive_end - false_positive_start:.3f} seconds")

    # ✅ ADD: Florence-2 captioning for UI elements using intelligent prompts (optional)
    florence_start = time.time()
    if use_florence_captioning and caption_model_processor and len(filtered_boxes_elem) > 0:
        try:
            print(f"🔧 [FLORENCE-2] Starting intelligent captioning for {len(filtered_boxes_elem)} elements...")

            # Get YOLO elements that need captioning (non-text elements)
            yolo_elements = [elem for elem in filtered_boxes_elem if elem.get('source') == 'yolo']

            if yolo_elements:
                # Extract just the bounding boxes for Florence
                yolo_boxes = [elem['bbox'] for elem in yolo_elements]

                                # ✅ USE: Intelligent Florence-2 prompting system
                print(f"🔧 [FLORENCE-2] Using numpy image array format for processing...")
                parsed_content = get_parsed_content_icon(
                    yolo_boxes,
                    starting_idx=0,
                    image_source=image_np,  # ✅ FIXED: Use numpy array, not PIL Image!
                    caption_model_processor=caption_model_processor,
                    prompt=None,  # Let get_optimal_florence_prompt decide
                    batch_size=batch_size
                )

                                # Update YOLO elements with Florence captions
                # ✅ FIXED: parsed_content is a list of strings, not dictionaries
                for i, elem in enumerate([e for e in filtered_boxes_elem if e.get('source') == 'yolo']):
                    if i < len(parsed_content):
                        elem['florence_caption'] = str(parsed_content[i])  # parsed_content[i] is already a string
                        print(f"   📝 [FLORENCE] Element {i}: '{elem['florence_caption']}'")

                print(f"✅ [FLORENCE-2] Captioned {len(yolo_boxes)} UI elements")
            else:
                print("   ℹ️  [FLORENCE-2] No YOLO elements to caption")

        except Exception as e:
            print(f"❌ [FLORENCE-2] Error during captioning: {e}")
            # Continue without captioning
    elif caption_model_processor and len(filtered_boxes_elem) > 0:
        print("   ⚠️  [FLORENCE-2] Captioning disabled by use_florence_captioning=False flag")
    else:
        print("   ⚠️  [FLORENCE-2] Caption model not available or no elements to process")

    florence_end = time.time()
    print(f"[TIMING] Florence-2 captioning completed in {florence_end - florence_start:.3f} seconds")

    # ✅ Convert to tensor for annotation (expects normalized coordinates)
    tensor_conversion_start = time.time()
    filtered_boxes = torch.tensor([elem['bbox'] for elem in filtered_boxes_elem])

    # ✅ Convert from xyxy to cxcywh for annotation
    filtered_boxes = box_convert(boxes=filtered_boxes, in_fmt="xyxy", out_fmt="cxcywh")

    phrases = [i for i in range(len(filtered_boxes))]
    tensor_conversion_end = time.time()
    print(f"[TIMING] Tensor conversion completed in {tensor_conversion_end - tensor_conversion_start:.3f} seconds")

    # ✅ Rest of function unchanged...
    print("[TIMING] Starting bounding box annotation...")
    annotation_start = time.time()

    if draw_bbox_config:
        annotated_frame, label_coordinates = annotate(image_source=image_np, boxes=filtered_boxes, logits=logits[:len(filtered_boxes)], phrases=phrases, **draw_bbox_config)
    else:
        annotated_frame, label_coordinates = annotate(image_source=image_np, boxes=filtered_boxes, logits=logits[:len(filtered_boxes)], phrases=phrases, text_scale=text_scale, text_padding=text_padding)

    image_encoding_start = time.time()
    pil_img = Image.fromarray(annotated_frame)
    buffered = io.BytesIO()
    pil_img.save(buffered, format="PNG")
    encoded_image = base64.b64encode(buffered.getvalue()).decode('ascii')
    image_encoding_end = time.time()
    print(f"[TIMING] Image encoding completed in {image_encoding_end - image_encoding_start:.3f} seconds")

    coord_conversion_start = time.time()
    if output_coord_in_ratio:
        label_coordinates = {k: [v[0]/w, v[1]/h, v[2]/w, v[3]/h] for k, v in label_coordinates.items()}
    coord_conversion_end = time.time()
    print(f"[TIMING] Coordinate conversion completed in {coord_conversion_end - coord_conversion_start:.3f} seconds")

    annotation_end = time.time()
    print(f"[TIMING] Bounding box annotation completed in {annotation_end - annotation_start:.3f} seconds")

    if len(filtered_boxes_elem) > 0:
        debug_start = time.time()
        debug_annotation_pipeline(filtered_boxes_elem, w, h)
        debug_end = time.time()
        print(f"[TIMING] Debug analysis completed in {debug_end - debug_start:.3f} seconds")

    som_end_time = time.time()
    print(f"[TIMING] Total SOM processing completed in {som_end_time - som_start_time:.3f} seconds")

    return encoded_image, label_coordinates, filtered_boxes_elem

def get_xywh(input):
    x, y, w, h = input[0][0], input[0][1], input[2][0] - input[0][0], input[2][1] - input[0][1]
    x, y, w, h = int(x), int(y), int(w), int(h)
    return x, y, w, h

def get_xyxy(input):
    x, y, xp, yp = input[0][0], input[0][1], input[2][0], input[2][1]
    x, y, xp, yp = int(x), int(y), int(xp), int(yp)
    return x, y, xp, yp

def get_xywh_yolo(input):
    x, y, w, h = input[0], input[1], input[2] - input[0], input[3] - input[1]
    x, y, w, h = int(x), int(y), int(w), int(h)
    return x, y, w, h

def get_xywh_pytesseract(bbox_data, text_content):
    """Convert pytesseract bbox format to xywh"""
    try:
        if isinstance(bbox_data, list) and len(bbox_data) == 4 and isinstance(bbox_data[0], list):
            # 4-point format: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
            x_coords = [float(point[0]) for point in bbox_data]
            y_coords = [float(point[1]) for point in bbox_data]
            left = min(x_coords)
            top = min(y_coords)
            width = max(x_coords) - min(x_coords)
            height = max(y_coords) - min(y_coords)
            return int(left), int(top), int(width), int(height)
        else:
            return 0, 0, 0, 0
    except Exception as e:
        print(f"❌ Error processing pytesseract bbox {bbox_data}: {e}")
        return 0, 0, 0, 0

def get_xyxy_pytesseract(bbox_data, text_content):
    """Convert pytesseract bbox format to xyxy"""
    try:
        if isinstance(bbox_data, list) and len(bbox_data) == 4 and isinstance(bbox_data[0], list):
            # 4-point format: [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]
            x_coords = [float(point[0]) for point in bbox_data]
            y_coords = [float(point[1]) for point in bbox_data]
            x1, y1 = min(x_coords), min(y_coords)
            x2, y2 = max(x_coords), max(y_coords)
            return int(x1), int(y1), int(x2), int(y2)
        else:
            return 0, 0, 0, 0
    except Exception as e:
        print(f"❌ Error processing pytesseract bbox {bbox_data}: {e}")
        return 0, 0, 0, 0

def debug_coordinate_conversion_functions():
    """Test the coordinate conversion functions with known values"""
    print("\n🔍 [FUNCTION-DEBUG] Testing coordinate conversion functions")

    # Test case: A box at (100, 50) to (200, 100) - should be 100x50 pixels
    test_points = [[100, 50], [200, 50], [200, 100], [100, 100]]

    print(f"Test input points: {test_points}")

    # Test get_xyxy
    try:
        xyxy_result = get_xyxy(test_points)
        print(f"get_xyxy result: {xyxy_result}")
        x1, y1, x2, y2 = xyxy_result
        print(f"  Interpreted as: top-left({x1}, {y1}) to bottom-right({x2}, {y2})")
        print(f"  Size: {x2-x1} x {y2-y1}")
        print(f"  Center: ({(x1+x2)/2}, {(y1+y2)/2})")
    except Exception as e:
        print(f"get_xyxy error: {e}")

    # Test get_xywh
    try:
        xywh_result = get_xywh(test_points)
        print(f"get_xywh result: {xywh_result}")
        x, y, w, h = xywh_result
        print(f"  Interpreted as: top-left({x}, {y}), size({w}, {h})")
        print(f"  Bottom-right would be: ({x+w}, {y+h})")
        print(f"  Center: ({x+w/2}, {y+h/2})")
    except Exception as e:
        print(f"get_xywh error: {e}")


def split_large_text_boxes(text_boxes, max_width_ratio=0.8, max_height_ratio=0.8, image_width=1024, image_height=1024):
    """Split text boxes that are too large (likely merged incorrectly)"""
    split_boxes = []

    for i, (bbox, content) in enumerate(text_boxes):
        if isinstance(bbox[0], (list, tuple)):
            # Convert EasyOCR format to xyxy
            x_coords = [point[0] for point in bbox]
            y_coords = [point[1] for point in bbox]
            x1, y1, x2, y2 = min(x_coords), min(y_coords), max(x_coords), max(y_coords)
        else:
            x1, y1, x2, y2 = bbox

        width = x2 - x1
        height = y2 - y1
        width_ratio = width / image_width
        height_ratio = height / image_height

        # If box is too large, it's probably incorrectly merged
        if width_ratio > max_width_ratio or height_ratio > max_height_ratio:
            print(f"[DEBUG] Skipping oversized text box {i}: {width:.0f}x{height:.0f} "
                  f"({width_ratio:.2%}x{height_ratio:.2%}) - likely merged incorrectly")
            print(f"[DEBUG] Content preview: '{content[:100]}...'")
            # Skip this box or try to split it
            continue
        else:
            split_boxes.append((bbox, content))

    return split_boxes

def filter_oversized_boxes(boxes, image_width, image_height, max_width_ratio=0.4, max_height_ratio=0.4, max_area_ratio=0.15):
    """Remove boxes that are too large to be useful UI elements"""
    filtered_boxes = []
    total_area = image_width * image_height

    for box in boxes:
        if isinstance(box, dict):
            bbox = box['bbox']
        else:
            bbox = box

        # Convert to pixel coordinates if normalized
        if all(coord <= 1.0 for coord in bbox):
            x1, y1, x2, y2 = bbox[0]*image_width, bbox[1]*image_height, bbox[2]*image_width, bbox[3]*image_height
        else:
            x1, y1, x2, y2 = bbox

        width = abs(x2 - x1)
        height = abs(y2 - y1)
        area = width * height

        width_ratio = width / image_width
        height_ratio = height / image_height
        area_ratio = area / total_area

        # Skip boxes that are too large
        if (width_ratio > max_width_ratio or
            height_ratio > max_height_ratio or
            area_ratio > max_area_ratio):
                print(f"[FILTER] Removing oversized box: {width:.0f}x{height:.0f} "
                    f"({width_ratio:.1%}x{height_ratio:.1%}, area: {area_ratio:.1%})")
                continue

        filtered_boxes.append(box)

    print(f"[FILTER] Kept {len(filtered_boxes)} boxes after size filtering")
    return filtered_boxes

def filter_oversized_yolo_boxes(yolo_elements, w, h, image_type="desktop"):
    """Enhanced filtering specifically for oversized YOLO detections"""
    filtered_elements = []

    for elem in yolo_elements:
        bbox = elem['bbox']
        width_px = (bbox[2] - bbox[0]) * w
        height_px = (bbox[3] - bbox[1]) * h
        area_px = width_px * height_px
        aspect_ratio = width_px / height_px if height_px > 0 else 1.0

        # ✅ Desktop-specific filtering for icons
        if image_type == "desktop":
            # Desktop icons should be reasonably sized squares/rectangles
            if (width_px > 200 or height_px > 200 or  # Too large for desktop icon
                aspect_ratio > 4.0 or aspect_ratio < 0.25 or  # Wrong aspect ratio
                area_px > 40000):  # Too large area
                print(f"[DESKTOP-FILTER] Removing oversized desktop element: {width_px:.0f}x{height_px:.0f}")
                continue

        # ✅ Web-specific filtering
        elif image_type == "web":
            # More permissive for web elements but still filter extreme cases
            if (width_px > w * 0.8 or height_px > h * 0.6 or
                area_px > w * h * 0.4):
                print(f"[WEB-FILTER] Removing oversized web element: {width_px:.0f}x{height_px:.0f}")
                continue

        filtered_elements.append(elem)

    return filtered_elements

def is_likely_pattern_or_noise(text_content, bbox, image_width, image_height):
    """Detect if OCR result is likely a pattern/background rather than real text"""

    # Check text characteristics
    if len(text_content.strip()) < 2:
        return True

    # ✅ PRESERVE PRICES - Don't filter price-like patterns
    import re
    # Match prices like $16.99, s1699, €15.99, etc.
    price_pattern = r'[\$€£¥]?\d+\.?\d*\(?\$?\d*\.?\d*/?\w*\)?'
    if re.search(price_pattern, text_content, re.IGNORECASE):
        print(f"[FILTER] Preserving price-like text: '{text_content}'")
        return False

    # ✅ PRESERVE COMMON UI ELEMENTS
    ui_keywords = ['sort', 'filter', 'size', 'color', 'price', 'reviews', 'results',
                   'delivery', 'cart', 'buy', 'sponsored', 'options', 'deals']
    if any(keyword in text_content.lower() for keyword in ui_keywords):
        return False

    # Check for repetitive patterns (like maze walls)
    if len(set(text_content.replace(' ', ''))) < 3 and len(text_content) > 10:
        return True

    # Check for gibberish (too many non-alphanumeric characters)
    non_alnum = sum(1 for c in text_content if not c.isalnum() and not c.isspace())
    if non_alnum / len(text_content) > 0.7:
        return True

    # Check box size (reject very large boxes)
    if isinstance(bbox[0], (list, tuple)):
        x_coords = [point[0] for point in bbox]
        y_coords = [point[1] for point in bbox]
        width = max(x_coords) - min(x_coords)
        height = max(y_coords) - min(y_coords)
    else:
        x1, y1, x2, y2 = bbox
        width = abs(x2 - x1)
        height = abs(y2 - y1)

    width_ratio = width / image_width
    height_ratio = height / image_height

    # Reject boxes covering more than 30% of screen in either dimension
    if width_ratio > 0.3 or height_ratio > 0.3:
        return True

    return False

def boxes_should_merge_horizontally(box1: Dict, box2: Dict,
                                  max_gap: float = 5.0,
                                  vertical_tolerance: float = 3.0) -> bool:
    """
    Check if two boxes should be merged horizontally (same line) with vertical tolerance

    Args:
        box1, box2: Text box dictionaries with 'bbox'
        max_gap: Maximum horizontal gap in pixels to consider "touching"
        vertical_tolerance: Tolerance for vertical misalignment in pixels

    Returns:
        True if boxes should be merged horizontally
    """

    def extract_bbox(box):
        """Extract bbox coordinates handling different formats"""
        bbox = box['bbox']
        if len(bbox) != 4:
            return None

        # Handle normalized coordinates vs pixel coordinates
        if all(0 <= coord <= 1 for coord in bbox):
            # Normalized coordinates [x1, y1, x2, y2] - convert to pixel coordinates
            x1, y1, x2, y2 = bbox
            return x1 * 1024, y1 * 1024, x2 * 1024, y2 * 1024
        else:
            # Pixel coordinates - could be [x1,y1,x2,y2] or [x,y,w,h]
            if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
                # Looks like [x1,y1,x2,y2]
                return bbox[0], bbox[1], bbox[2], bbox[3]
            else:
                # Assume [x,y,w,h]
                x, y, w, h = bbox
                return x, y, x + w, y + h

    bbox1 = extract_bbox(box1)
    bbox2 = extract_bbox(box2)

    if bbox1 is None or bbox2 is None:
        return False

    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2

    # Calculate box properties
    height1 = y2_1 - y1_1
    height2 = y2_2 - y1_2
    center_y1 = (y1_1 + y2_1) / 2
    center_y2 = (y1_2 + y2_2) / 2

    # ✅ NEW: Multiple vertical alignment checks for robustness

    # Method 1: Check if vertical centers are close
    vertical_center_distance = abs(center_y1 - center_y2)
    max_center_distance = max(height1, height2) * 0.3 + vertical_tolerance  # 30% of height + tolerance
    centers_aligned = vertical_center_distance <= max_center_distance

    # Method 2: Check if boxes overlap vertically with tolerance
    expanded_y1_1 = y1_1 - vertical_tolerance
    expanded_y2_1 = y2_1 + vertical_tolerance
    expanded_y1_2 = y1_2 - vertical_tolerance
    expanded_y2_2 = y2_2 + vertical_tolerance

    overlap_start = max(expanded_y1_1, y1_2)
    overlap_end = min(expanded_y2_1, y2_2)
    has_tolerant_overlap = overlap_end > overlap_start

    # Alternative overlap check
    overlap_start_2 = max(y1_1, expanded_y1_2)
    overlap_end_2 = min(y2_1, expanded_y2_2)
    has_tolerant_overlap_2 = overlap_end_2 > overlap_start_2

    tolerant_overlap = has_tolerant_overlap or has_tolerant_overlap_2

    # Method 3: Check if boxes are roughly on same horizontal band
    max_y_diff = max(height1, height2) * 0.5  # 50% of larger box height
    top_difference = abs(y1_1 - y1_2)
    bottom_difference = abs(y2_1 - y2_2)
    same_horizontal_band = (top_difference <= max_y_diff) or (bottom_difference <= max_y_diff)

    # ✅ Boxes are vertically aligned if ANY method succeeds
    vertically_aligned = centers_aligned or tolerant_overlap or same_horizontal_band

    if not vertically_aligned:
        return False

    # ✅ Check horizontal proximity (boxes touching or nearly touching)
    horizontal_gap = float('inf')

    if x2_1 <= x1_2:
        # box1 is to the left of box2
        horizontal_gap = x1_2 - x2_1
    elif x2_2 <= x1_1:
        # box2 is to the left of box1
        horizontal_gap = x1_1 - x2_2
    else:
        # Boxes overlap horizontally
        horizontal_gap = 0

    # Boxes should be touching or nearly touching
    is_horizontally_adjacent = horizontal_gap <= max_gap

    return is_horizontally_adjacent

def boxes_should_merge_horizontally_advanced(box1: Dict, box2: Dict,
                                           max_gap: float = 5.0,
                                           vertical_tolerance: float = 3.0,
                                           min_overlap_ratio: float = 0.5) -> bool:
    """
    Advanced version with even more robust vertical alignment detection
    """

    def extract_bbox(box):
        bbox = box['bbox']
        if len(bbox) != 4:
            return None

        if all(0 <= coord <= 1 for coord in bbox):
            x1, y1, x2, y2 = bbox
            return x1 * 1024, y1 * 1024, x2 * 1024, y2 * 1024
        else:
            if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
                return bbox[0], bbox[1], bbox[2], bbox[3]
            else:
                x, y, w, h = bbox
                return x, y, x + w, y + h

    bbox1 = extract_bbox(box1)
    bbox2 = extract_bbox(box2)

    if bbox1 is None or bbox2 is None:
        return False

    x1_1, y1_1, x2_1, y2_1 = bbox1
    x1_2, y1_2, x2_2, y2_2 = bbox2

    height1 = y2_1 - y1_1
    height2 = y2_2 - y1_2

    # ✅ Smart vertical tolerance based on text height
    adaptive_tolerance = max(vertical_tolerance, min(height1, height2) * 0.2)  # 20% of smaller box height

    # ✅ Multiple robust alignment checks

    # 1. Vertical center alignment with adaptive tolerance
    center_y1 = (y1_1 + y2_1) / 2
    center_y2 = (y1_2 + y2_2) / 2
    center_distance = abs(center_y1 - center_y2)
    max_center_distance = (max(height1, height2) * 0.4) + adaptive_tolerance

    # 2. Overlap with tolerance buffers
    buffer1_top = y1_1 - adaptive_tolerance
    buffer1_bottom = y2_1 + adaptive_tolerance
    buffer2_top = y1_2 - adaptive_tolerance
    buffer2_bottom = y2_2 + adaptive_tolerance

    # Check overlap in both directions
    overlap1 = max(0, min(buffer1_bottom, y2_2) - max(buffer1_top, y1_2))
    overlap2 = max(0, min(y2_1, buffer2_bottom) - max(y1_1, buffer2_top))
    max_overlap = max(overlap1, overlap2)

    min_height = min(height1, height2)
    overlap_ratio = max_overlap / min_height if min_height > 0 else 0

    # 3. Baseline alignment check (bottoms roughly aligned)
    bottom_alignment = abs(y2_1 - y2_2) <= adaptive_tolerance * 1.5

    # 4. Top alignment check
    top_alignment = abs(y1_1 - y1_2) <= adaptive_tolerance * 1.5

    # ✅ Accept if any alignment method succeeds
    vertically_aligned = (
        center_distance <= max_center_distance or  # Centers close
        overlap_ratio >= min_overlap_ratio or      # Sufficient overlap
        bottom_alignment or                        # Baselines aligned
        top_alignment                             # Tops aligned
    )

    if not vertically_aligned:
        return False

    # ✅ Check horizontal proximity
    if x2_1 <= x1_2:
        horizontal_gap = x1_2 - x2_1  # box1 left of box2
    elif x2_2 <= x1_1:
        horizontal_gap = x1_1 - x2_2  # box2 left of box1
    else:
        horizontal_gap = 0  # Overlapping


    return horizontal_gap <= max_gap

def merge_horizontal_boxes(boxes: List[Dict]) -> Dict:
    """
    Merge a list of horizontally adjacent boxes into one

    Args:
        boxes: List of text boxes to merge

    Returns:
        Single merged text box
    """
    if len(boxes) == 1:
        return boxes[0]

    # Sort boxes by horizontal position (left to right)
    def get_left_x(box):
        bbox = box['bbox']
        if all(0 <= coord <= 1 for coord in bbox):
            return bbox[0] * 1024  # Normalized to pixel
        else:
            return bbox[0] if bbox[2] > bbox[0] else bbox[0]  # Handle both formats

    sorted_boxes = sorted(boxes, key=get_left_x)

    # Extract all bounding boxes and text
    all_x1, all_y1, all_x2, all_y2 = [], [], [], []
    all_text = []
    all_confidences = []

    for box in sorted_boxes:
        bbox = box['bbox']

        # Handle coordinate conversion
        if all(0 <= coord <= 1 for coord in bbox):
            # Normalized coordinates
            x1, y1, x2, y2 = bbox
        else:
            # Pixel coordinates
            if bbox[2] > bbox[0] and bbox[3] > bbox[1]:
                x1, y1, x2, y2 = bbox
            else:
                x, y, w, h = bbox
                x1, y1, x2, y2 = x, y, x + w, y + h

        all_x1.append(x1)
        all_y1.append(y1)
        all_x2.append(x2)
        all_y2.append(y2)

        # Collect text content
        text_content = ""
        if 'content' in box and box['content']:
            text_content = str(box['content']).strip()
        elif 'text' in box and box['text']:
            text_content = str(box['text']).strip()

        if text_content:
            all_text.append(text_content)

        # Collect confidence
        if 'confidence' in box:
            all_confidences.append(box['confidence'])

    # Calculate merged bounding box
    merged_x1 = min(all_x1)
    merged_y1 = min(all_y1)
    merged_x2 = max(all_x2)
    merged_y2 = max(all_y2)

    # Merge text with spaces
    merged_text = " ".join(all_text)

    # Calculate average confidence
    avg_confidence = sum(all_confidences) / len(all_confidences) if all_confidences else 0.0

    # Create merged box using first box as template
    merged_box = sorted_boxes[0].copy()
    merged_box['bbox'] = [merged_x1, merged_y1, merged_x2, merged_y2]

    # Update text content
    if 'content' in merged_box:
        merged_box['content'] = merged_text
    elif 'text' in merged_box:
        merged_box['text'] = merged_text

    # Update confidence
    if 'confidence' in merged_box:
        merged_box['confidence'] = avg_confidence

    return merged_box

def detect_browser_ui_text(image_np):
    """Specialized detection for browser UI elements"""

    print("🌐 [BROWSER-UI] Running browser-specific text detection...")

    # Very sensitive settings for UI text
    ui_args = {
        'paragraph': False,
        'width_ths': 0.1,       # Very low - catch narrow text
        'height_ths': 0.1,      # Very low - catch small text
        'text_threshold': 0.05, # Very sensitive
        'low_text': 0.01,       # Extremely sensitive
        'link_threshold': 0.9,  # Don't connect distant elements
        'canvas_size': 2560,    # High resolution
        'mag_ratio': 2.0,       # High magnification
    }

    try:
        result = reader.readtext(image_np, **ui_args)

        browser_detections = []
        for item in result:
            bbox_points = item[0]
            text_content = item[1].strip()
            confidence = item[2] if len(item) >= 3 else 1.0

            # Check if it's browser/UI-like text
            if is_browser_ui_text(text_content, bbox_points, image_np.shape):
                browser_detections.append((bbox_points, text_content, confidence))
                print(f"✅ [BROWSER-UI-FOUND] '{text_content}' (conf: {confidence:.2f})")

        return browser_detections

    except Exception as e:
        print(f"[BROWSER-UI] Error: {e}")
        return []

def is_browser_ui_text(text, bbox_points, image_shape):
    """Check if text looks like browser UI"""

    # Browser UI indicators
    browser_patterns = [
        r'amazon', r'search', r'\.com', r'www', r'http', r'results',
        r'add to cart', r'price', r'delivery', r'prime', r'$\d+',
        r'reviews?', r'rating', r'stars?', r'filter', r'sort'
    ]

    # Check position (top area for address bar, various for content)
    h, w = image_shape[:2]
    y_coords = [p[1] for p in bbox_points]
    avg_y = sum(y_coords) / len(y_coords)
    is_top_area = avg_y < h * 0.15  # Top 15% for address bar

    # Check content
    has_browser_content = any(re.search(pattern, text, re.IGNORECASE)
                             for pattern in browser_patterns)

    # Check if it's substantial enough
    is_substantial = len(text.strip()) >= 2

    return (has_browser_content or is_top_area) and is_substantial

def detect_table_structure(elements, image_width, image_height):
    """Detect if elements form a table structure and shouldn't be merged"""

    # Group elements by approximate Y position (rows)
    rows = {}
    tolerance = 10  # pixels

    for elem in elements:
        bbox = elem['bbox']
        if all(0 <= coord <= 1 for coord in bbox):
            y_center = ((bbox[1] + bbox[3]) / 2) * image_height
        else:
            y_center = (bbox[1] + bbox[3]) / 2

        # Find existing row or create new one
        found_row = False
        for row_y in rows:
            if abs(y_center - row_y) <= tolerance:
                rows[row_y].append(elem)
                found_row = True
                break

        if not found_row:
            rows[y_center] = [elem]

    # Check if this looks like a table (multiple rows with similar element counts)
    if len(rows) >= 3:  # At least 3 rows
        row_sizes = [len(row_elements) for row_elements in rows.values()]
        avg_row_size = sum(row_sizes) / len(row_sizes)

        # If most rows have similar number of elements, it's likely a table
        similar_rows = sum(1 for size in row_sizes if abs(size - avg_row_size) <= 2)
        if similar_rows / len(rows) > 0.7:  # 70% of rows are similar
            print(f"🔍 [TABLE-DETECT] Detected table structure: {len(rows)} rows, avg {avg_row_size:.1f} elements per row")
            return True

    return False

def smart_merging_with_table_awareness(text_boxes, max_gap=6.0, vertical_tolerance=3.0):
    """Enhanced merging that respects table structures"""

    # First check if this looks like a table
    if detect_table_structure(text_boxes, 1024, 1024):
        print("📊 [TABLE-AWARE] Table detected - using conservative merging")
        # Use much more conservative settings for tables
        max_gap = max_gap * 0.5  # Halve the gap
        vertical_tolerance = max(3.0, vertical_tolerance * 0.3)  # Much tighter vertical tolerance

    return smart_merging_with_table_awareness(
        text_boxes,
        max_gap=max_gap,
        vertical_tolerance=vertical_tolerance
    )

def apply_horizontal_text_merging_robust(parsed_content: List[Dict],
                                       max_gap: float = 5.0,
                                       vertical_tolerance: float = 3.0,
                                       use_advanced: bool = True,
                                       debug: bool = True) -> List[Dict]:
    """
    Apply robust horizontal text merging accounting for vertical pixel offsets

    Args:
        parsed_content: List of text detection dictionaries
        max_gap: Maximum horizontal gap in pixels for merging
        vertical_tolerance: Tolerance for vertical misalignment in pixels
        use_advanced: Use advanced alignment detection
        debug: Print debug information

    Returns:
        List of merged text detections
    """

    if not parsed_content:
        return []

    if debug:
        print(f"\n🔗 [ROBUST-HORIZONTAL-MERGE] Starting with {len(parsed_content)} text boxes")
        print(f"   📏 Max horizontal gap: {max_gap}px")
        print(f"   📐 Vertical tolerance: {vertical_tolerance}px")
        print(f"   🎯 Advanced mode: {use_advanced}")

    # Choose alignment function
    alignment_func = boxes_should_merge_horizontally_advanced if use_advanced else boxes_should_merge_horizontally

    # Find groups using robust alignment
    n_boxes = len(parsed_content)
    groups = []
    used_indices = set()

    for i in range(n_boxes):
        if i in used_indices:
            continue

        current_group = [i]
        used_indices.add(i)

        # Iteratively find boxes to merge
        group_changed = True
        while group_changed:
            group_changed = False

            for j in range(n_boxes):
                if j in used_indices:
                    continue

                # Check if box j should merge with any box in current group
                should_merge = False
                for group_idx in current_group:
                    should_merge = alignment_func(
                        parsed_content[group_idx],
                        parsed_content[j],
                        max_gap,
                        vertical_tolerance
                    )

                    if should_merge:
                        break

                if should_merge:
                    current_group.append(j)
                    used_indices.add(j)
                    group_changed = True

        groups.append(current_group)

    # Merge groups and create results
    merged_content = []
    merge_count = 0

    for group_indices in groups:
        if len(group_indices) == 1:
            merged_content.append(parsed_content[group_indices[0]])
        else:
            boxes_to_merge = [parsed_content[i] for i in group_indices]
            merged_box = merge_horizontal_boxes(boxes_to_merge)
            merged_content.append(merged_box)

            merge_count += len(group_indices) - 1

            if debug:
                # Show details of merge including vertical offsets
                original_texts = []
                y_positions = []
                for i in group_indices:
                    box = parsed_content[i]
                    text = box.get('content', box.get('text', 'N/A'))
                    bbox = box['bbox']
                    if all(0 <= coord <= 1 for coord in bbox):
                        y_center = (bbox[1] + bbox[3]) / 2 * 1024
                    else:
                        y_center = (bbox[1] + bbox[3]) / 2 if bbox[3] > bbox[1] else bbox[1] + bbox[3]/2

                    original_texts.append(f"'{text}'")
                    y_positions.append(f"y={y_center:.1f}")

                merged_text = merged_box.get('content', merged_box.get('text', 'N/A'))
                y_offsets = f"[{', '.join(y_positions)}]"
                print(f"   🔗 Merged {len(group_indices)} boxes {y_offsets}: {' + '.join(original_texts)} → '{merged_text}'")

    if debug:
        print(f"✅ [ROBUST-HORIZONTAL-MERGE] Result: {len(merged_content)} boxes ({merge_count} merges performed)")

    return merged_content

def analyze_image_characteristics(image_np):
    """Analyze image to optimize OCR parameters"""
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

    # Calculate contrast (standard deviation of pixel values)
    contrast = gray.std() / 255.0

    # Calculate brightness (mean pixel value)
    brightness = gray.mean() / 255.0

    # Estimate text density using edge detection
    edges = cv2.Canny(gray, 50, 150)
    edge_density = np.sum(edges > 0) / edges.size

    return {
        'contrast': contrast,
        'brightness': brightness,
        'edge_density': edge_density,
        'resolution': gray.shape
    }

def dynamic_confidence_threshold(image_stats, base_threshold=0.5):
    """Calculate optimal confidence threshold based on image quality"""

    adjusted_threshold = base_threshold

    # ✅ Lower threshold for high contrast images (cleaner text, easier to read)
    contrast = image_stats.get('contrast', 0.5)
    if contrast > 0.6:
        adjusted_threshold *= 0.8  # 20% lower threshold
    elif contrast < 0.3:
        adjusted_threshold *= 1.2  # 20% higher threshold (more noise expected)

    # ✅ Adjust for brightness extremes (very dark/bright images harder to read)
    brightness = image_stats.get('brightness', 0.5)
    if brightness < 0.2 or brightness > 0.8:
        adjusted_threshold *= 1.1  # 10% higher threshold

    # ✅ Adjust for edge density (more edges = more text-like content)
    edge_density = image_stats.get('edge_density', 0.1)
    if edge_density > 0.15:  # High edge density suggests lots of text
        adjusted_threshold *= 0.9  # Slightly lower threshold

    # ✅ Clamp to reasonable bounds
    return max(0.1, min(0.8, adjusted_threshold))

def get_optimized_tesseract_config(image_stats):
    """Generate optimized tesseract configuration based on image analysis"""

    # ✅ Base configuration
    config = '--oem 3 --psm 6'  # LSTM engine, uniform text block

    # ✅ Adjust based on image characteristics
    contrast = image_stats.get('contrast', 0.5)
    brightness = image_stats.get('brightness', 0.5)

    # For low contrast images, be more permissive
    if contrast < 0.4:
        config += ' -c tessedit_char_confidence_th=10'  # Lower confidence threshold

    # For very bright or dark images, adjust preprocessing
    if brightness < 0.3:
        config += ' -c textord_heavy_nr=1'  # Heavy noise reduction for dark images
    elif brightness > 0.7:
        config += ' -c textord_noise_area_ratio=0.9'  # Noise filtering for bright images

    # For high edge density (lots of text), use different segmentation
    edge_density = image_stats.get('edge_density', 0.1)
    if edge_density > 0.2:
        config = config.replace('--psm 6', '--psm 3')  # Auto page segmentation

    return config

def aggressive_text_filtering(text_content, confidence, bbox, image_width, image_height):
    """More aggressive text filtering to remove OCR noise"""

    text_len = len(text_content.strip())

    # ✅ Basic filtering
    if text_len == 0:
        return False

    # ✅ Remove obvious OCR noise patterns
    noise_patterns = [
        r'^[^\w\s]*$',          # Only special characters
        r'^[~@#$%^&*]{2,}',     # Multiple special chars at start
        r'^[0-9\s@=]{1,3}$',    # Short number/symbol combinations
        r'^[DJ]+\s',            # OCR artifact patterns
    ]

    for pattern in noise_patterns:
        if re.match(pattern, text_content):
            print(f"[FILTER] Removing noise pattern: '{text_content}'")
            return False

    # Be more permissive for text that looks like valid content
    if text_len < 3 and confidence < 0.7:
        # Allow if it looks like valid content
        if not (text_content.isalnum() or
                any(char in text_content for char in ['%', '$', '€', '£']) or
                text_content.lower() in ['ok', 'go', 'on', 'in', 'to', 'of', 'is', 'no']):
            return False

    if text_len == 1 and confidence < 0.9:
        return False

    # ✅ Character diversity check
    if text_len >= 3:
        unique_chars = len(set(text_content.replace(' ', '').lower()))
        if unique_chars / text_len < 0.4:  # Less than 40% unique characters
            return False

    # ✅ Alphanumeric ratio
    alnum_count = sum(c.isalnum() for c in text_content)
    if text_len > 2 and alnum_count / text_len < 0.5:  # Less than 50% alphanumeric
        return False

    return True

def improve_text_quality(text_content, bbox, image_stats):
    """Clean and improve OCR text output"""

    # ✅ Basic cleaning
    cleaned = text_content.strip()

    # Remove common OCR artifacts (noise characters at start/end)
    cleaned = re.sub(r'^[^\w\s]*', '', cleaned)  # Remove leading non-word chars
    cleaned = re.sub(r'[^\w\s]*$', '', cleaned)  # Remove trailing non-word chars

    # ✅ Fix spacing issues
    cleaned = re.sub(r'\s+', ' ', cleaned)  # Normalize whitespace

    # ✅ Fix common OCR character substitutions
    ocr_fixes = {
        'rn': 'm',    # Common OCR error
        'cl': 'd',    # Common OCR error
        '0': 'O',     # Context-dependent (we'd need more logic)
        '1': 'l',     # Context-dependent
    }

    # Only apply fixes for very short text or low confidence scenarios
    if len(cleaned) <= 3:
        for error, fix in ocr_fixes.items():
            if error in cleaned.lower():
                # Only fix if it makes the text more readable
                potential_fix = cleaned.lower().replace(error, fix)
                if potential_fix.isalpha() and len(potential_fix) >= len(cleaned):
                    cleaned = potential_fix

    return cleaned.strip()

def analyze_detection_results(quality_stats, final_count):
    """Analyze OCR detection quality"""

    total_detections = quality_stats.get('total_detections', 1)
    fragments = quality_stats.get('fragments', 0)

    fragment_ratio = fragments / final_count if final_count > 0 else 0
    avg_text_length = quality_stats.get('total_chars', 0) / final_count if final_count > 0 else 0
    detection_rate = final_count / total_detections if total_detections > 0 else 0

    return {
        'fragment_ratio': fragment_ratio,
        'avg_text_length': avg_text_length,
        'detection_rate': detection_rate,
        'total_kept': final_count,
        'total_raw': total_detections
    }

def suggest_parameter_adjustments(detection_quality):
    """Suggest parameter adjustments based on detection quality"""

    suggestions = []

    # High fragmentation
    if detection_quality['fragment_ratio'] > 0.4:
        suggestions.append("Lower text_threshold for less fragmentation")
        suggestions.append("Increase merging parameters")

    # Very low detection rate
    if detection_quality['detection_rate'] < 0.1:
        suggestions.append("Much lower confidence threshold needed")

    # Very short average text
    if detection_quality['avg_text_length'] < 3:
        suggestions.append("Possible over-segmentation, try PSM 3 or 11")

    # Too few detections overall
    if detection_quality['total_kept'] < 5:
        suggestions.append("Try lower confidence threshold or different PSM mode")

    return suggestions

def optimized_horizontal_merging(text_boxes,
                               adaptive_gap=True,
                               adaptive_tolerance=True,
                               min_merge_confidence=0.7):
    """Optimized merging with adaptive parameters"""

    if not text_boxes or len(text_boxes) < 2:
        return text_boxes

    # ✅ Calculate adaptive parameters based on text box statistics
    if adaptive_gap or adaptive_tolerance:
        heights = []
        widths = []
        confidences = []  # ✅ ADD: Track confidences

        for box in text_boxes:
            bbox = box['bbox']
            if all(0 <= coord <= 1 for coord in bbox):
                # Normalized coordinates - convert to pixels for calculation
                width = (bbox[2] - bbox[0]) * 1024
                height = (bbox[3] - bbox[1]) * 1024
            else:
                width = abs(bbox[2] - bbox[0])
                height = abs(bbox[3] - bbox[1])

            heights.append(height)
            widths.append(width)

            # ✅ FIX: Actually use min_merge_confidence
            confidence = box.get('confidence', 1.0)
            confidences.append(confidence)

        avg_height = np.mean(heights) if heights else 20
        avg_width = np.mean(widths) if widths else 50
        avg_confidence = np.mean(confidences) if confidences else 1.0

        # ✅ Adaptive parameters based on text statistics
        if adaptive_gap:
            # Gap should be proportional to average character width
            max_gap = max(5.0, avg_height * 0.3)  # 30% of average text height
        else:
            max_gap = 8.0

        if adaptive_tolerance:
            # Tolerance should be proportional to text height variation
            vertical_tolerance = max(2.0, np.std(heights) * 0.5) if len(heights) > 1 else 5.0
        else:
            vertical_tolerance = 5.0

        # ✅ FIX: Use min_merge_confidence to filter low-quality merges
        if avg_confidence < min_merge_confidence:
            print(f"⚠️ [MERGE-CONFIDENCE] Low average confidence {avg_confidence:.2f} < {min_merge_confidence}, using conservative merging")
            max_gap *= 0.7  # More conservative gap
            vertical_tolerance *= 0.8  # More conservative tolerance
    else:
        max_gap = 8.0
        vertical_tolerance = 5.0

    print(f"🔧 [MERGE-PARAMS] Adaptive gap: {max_gap:.1f}, tolerance: {vertical_tolerance:.1f}, min_conf: {min_merge_confidence}")

    # ✅ Use optimized merging with calculated parameters
    return apply_horizontal_text_merging_robust(
        text_boxes,
        max_gap=max_gap,
        vertical_tolerance=vertical_tolerance,
        use_advanced=True,
        debug=True
    )

def analyze_ocr_quality(text_list, coord_list, w, h):
    """Simple OCR quality analysis"""

    if not text_list:
        return {'quality_score': 0.0, 'avg_text_length': 0}

    # ✅ Text quality metrics
    total_chars = sum(len(txt) for txt in text_list)
    avg_length = total_chars / len(text_list)
    fragments = sum(1 for txt in text_list if len(txt) < 4)
    fragment_ratio = fragments / len(text_list)

    # ✅ Quality scoring
    quality_score = 0.5

    if 3 <= avg_length <= 20:
        quality_score += 0.2

    if fragment_ratio < 0.3:
        quality_score += 0.2
    elif fragment_ratio > 0.6:
        quality_score -= 0.3

    if len(text_list) >= 3:
        quality_score += 0.1

    return {
        'quality_score': max(0, min(1, quality_score)),
        'avg_text_length': avg_length,
        'fragment_ratio': fragment_ratio,
        'total_elements': len(text_list)
    }

def post_process_ocr_results(text_list, coord_list, quality_info):
    """Post-process OCR results for better quality"""

    if quality_info['fragment_ratio'] > 0.4:
        print("🔧 [OCR-FIX] High fragmentation detected, applying text cleaning...")

        # ✅ Clean text with common fixes
        cleaned_text = []
        for txt in text_list:
            cleaned = txt.strip()
            # Remove leading/trailing special characters
            cleaned = re.sub(r'^[^\w\s]+|[^\w\s]+$', '', cleaned)
            # Normalize whitespace
            cleaned = re.sub(r'\s+', ' ', cleaned)
            if cleaned:  # Only keep non-empty
                cleaned_text.append(cleaned)

        # ✅ Update coordinates to match cleaned text
        if len(cleaned_text) != len(text_list):
            # Simple approach: keep first N coordinates
            coord_list = coord_list[:len(cleaned_text)]

        return cleaned_text, coord_list

    return text_list, coord_list

def preprocess_image_for_ocr(image_np):
    """Preprocess image to improve OCR quality"""

    # Convert to grayscale
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

    # Apply denoising
    denoised = cv2.fastNlMeansDenoising(gray)

    # Enhance contrast
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced = clahe.apply(denoised)

    # Apply slight blur to smooth jagged edges
    blurred = cv2.GaussianBlur(enhanced, (1, 1), 0)

    # Convert back to RGB for pytesseract
    processed = cv2.cvtColor(blurred, cv2.COLOR_GRAY2RGB)

    return processed

def check_ocr_box(image_source: Union[str, Image.Image], display_img=True, output_bb_format='xywh', goal_filtering=None, easyocr_args=None, use_pytesseract=False):
    setup_easy_ocr()
    setup_pytesseract()

    ocr_start_time = time.time()
    print("[TIMING] Starting OCR processing...")

    if isinstance(image_source, str):
        image_source = Image.open(image_source)
    if image_source.mode == 'RGBA':
        image_source = image_source.convert('RGB')
    image_np = np.array(image_source)
    w, h = image_source.size

    if use_pytesseract:
        print("[TIMING] Starting pytesseract text detection...")
        tesseract_start = time.time()

        if not pytesseract_initialized:
            print("❌ pytesseract not initialized, falling back to EasyOCR")
            use_pytesseract = False
        else:
            try:
                # ✅ RESTORE ALL OPTIMIZATIONS WITH TIMING
                image_analysis_start = time.time()
                image_stats = analyze_image_characteristics(image_np)
                image_analysis_end = time.time()
                print(f"[TIMING] Image analysis completed in {image_analysis_end - image_analysis_start:.3f} seconds")
                print(f"🔍 [IMAGE-ANALYSIS] Contrast: {image_stats['contrast']:.2f}, Brightness: {image_stats['brightness']:.2f}")

                threshold_calc_start = time.time()
                base_threshold = easyocr_args.get('text_threshold', 0.5) if easyocr_args else 0.5
                text_threshold = dynamic_confidence_threshold(image_stats, base_threshold)
                threshold_calc_end = time.time()
                print(f"[TIMING] Threshold calculation completed in {threshold_calc_end - threshold_calc_start:.3f} seconds")
                print(f"🎯 [THRESHOLD] Base: {base_threshold:.2f} → Dynamic: {text_threshold:.2f}")

                config_start = time.time()
                optimized_config = get_optimized_tesseract_config(image_stats)
                config_end = time.time()
                print(f"[TIMING] Config optimization completed in {config_end - config_start:.3f} seconds")
                print(f"🔧 [CONFIG] Using optimized config: {optimized_config}")

                preprocess_start = time.time()
                processed_image_np = preprocess_image_for_ocr(image_np)
                pil_image = Image.fromarray(processed_image_np)
                preprocess_end = time.time()
                print(f"[TIMING] Image preprocessing completed in {preprocess_end - preprocess_start:.3f} seconds")

                tesseract_inference_start = time.time()
                result = pytesseract.image_to_data(
                    pil_image,
                    config=optimized_config,
                    output_type=pytesseract.Output.DICT
                )
                tesseract_inference_end = time.time()
                print(f"[TIMING] Tesseract inference completed in {tesseract_inference_end - tesseract_inference_start:.3f} seconds")
                print(f"🔍 [PYTESSERACT-DEBUG] Found {len(result['text'])} raw detections")

                processing_start = time.time()
                coord = []
                text = []
                filtered_count = 0
                quality_stats = {'fragments': 0, 'total_chars': 0, 'total_detections': 0}

                for i in range(len(result['text'])):
                    confidence_pct = int(result['conf'][i])
                    confidence_normalized = confidence_pct / 100.0
                    text_content = result['text'][i].strip()

                    quality_stats['total_detections'] += 1

                    if not text_content:
                        continue

                    left = result['left'][i]
                    top = result['top'][i]
                    width = result['width'][i]
                    height = result['height'][i]

                    bbox_points = [[left, top], [left + width, top],
                                [left + width, top + height], [left, top + height]]

                    if aggressive_text_filtering(text_content, confidence_normalized, bbox_points, w, h):
                        cleaned_text = improve_text_quality(text_content, bbox_points, image_stats)
                        coord.append(bbox_points)
                        text.append(cleaned_text)

                        quality_stats['total_chars'] += len(cleaned_text)
                        if len(cleaned_text) < 4:
                            quality_stats['fragments'] += 1
                    else:
                        filtered_count += 1

                processing_end = time.time()
                print(f"[TIMING] Text processing completed in {processing_end - processing_start:.3f} seconds")

                # ✅ RESTORE QUALITY ANALYSIS
                if coord and text:
                    quality_start = time.time()
                    ocr_quality = analyze_ocr_quality(text, coord, w, h)
                    text, coord = post_process_ocr_results(text, coord, ocr_quality)
                    quality_end = time.time()
                    print(f"[TIMING] Quality analysis completed in {quality_end - quality_start:.3f} seconds")
                    print(f"📊 [OCR-QUALITY] Score: {ocr_quality['quality_score']:.2f}, Avg length: {ocr_quality['avg_text_length']:.1f}")

                detection_quality = analyze_detection_results(quality_stats, len(coord))
                print(f"✅ pytesseract detected {len(coord)} text elements (threshold: {text_threshold:.2f})")
                print(f"📊 [QUALITY] Filtered out: {filtered_count}, Fragment ratio: {detection_quality['fragment_ratio']:.1%}")

            except Exception as e:
                print(f"❌ pytesseract inference failed: {e}")
                import traceback
                traceback.print_exc()
                print("🔄 Falling back to EasyOCR...")
                use_pytesseract = False
                coord, text = [], []

        tesseract_end = time.time()
        print(f"[TIMING] pytesseract processing completed in {tesseract_end - tesseract_start:.3f} seconds")

    if not use_pytesseract:
        print("[TIMING] Starting EasyOCR text detection...")
        easy_start = time.time()
        if easyocr_args is None:
            easyocr_args = {}

        is_paragraph_mode = easyocr_args.get('paragraph', False)
        print(f"[DEBUG] EasyOCR paragraph mode: {is_paragraph_mode}")

        result = reader.readtext(image_np, **easyocr_args)

        filtered_result = []
        for item in result:
            bbox_points = item[0]
            text_content = item[1]

            if is_paragraph_mode:
                confidence = 1.0
            else:
                if len(item) >= 3:
                    confidence = item[2]
                else:
                    confidence = 1.0

            if is_likely_pattern_or_noise(text_content, bbox_points, w, h):
                print(f"[FILTER] Skipping pattern/noise: '{text_content[:30]}...'")
                continue

            if not is_paragraph_mode and confidence < 0.3:
                print(f"[FILTER] Skipping low confidence: '{text_content[:30]}...' (conf: {confidence:.3f})")
                continue

            filtered_result.append(item)

        print(f"[FILTER] Kept {len(filtered_result)}/{len(result)} OCR detections after filtering")
        coord = [item[0] for item in filtered_result]
        text = [item[1] for item in filtered_result]
        easy_end = time.time()
        print(f"[TIMING] EasyOCR processing completed in {easy_end - easy_start:.3f} seconds")

    # ✅ COORDINATE PROCESSING WITH TIMING
    bbox_processing_start = time.time()
    if display_img:
        opencv_img = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
        bb = []
        for item in coord:
            try:
                if use_pytesseract:
                    x, y, a, b = get_xywh_pytesseract(item, "")
                else:
                    x, y, a, b = get_xywh(item)
                bb.append((x, y, a, b))
                cv2.rectangle(opencv_img, (x, y), (x+a, y+b), (0, 255, 0), 2)
            except Exception as e:
                print(f"⚠️ Failed to process bbox {item}: {e}")
                continue
        plt.imshow(cv2.cvtColor(opencv_img, cv2.COLOR_BGR2RGB))
    else:
        bb = []
        for item in coord:
            try:
                if use_pytesseract:
                    if isinstance(item, list) and len(item) == 4 and isinstance(item[0], list):
                        x_coords = [point[0] for point in item]
                        y_coords = [point[1] for point in item]
                        x1, y1 = min(x_coords), min(y_coords)
                        x2, y2 = max(x_coords), max(y_coords)

                        if output_bb_format == 'xywh':
                            bb.append((x1, y1, x2-x1, y2-y1))
                        elif output_bb_format == 'xyxy':
                            bb.append((x1, y1, x2, y2))
                    else:
                        print(f"❌ Invalid pytesseract bbox format: {item}")
                        continue
                else:
                    if output_bb_format == 'xywh':
                        bb.append(get_xywh(item))
                    elif output_bb_format == 'xyxy':
                        bb.append(get_xyxy(item))
            except Exception as e:
                print(f"⚠️ Failed to process bbox {item}: {e}")
                continue

    bbox_processing_end = time.time()
    print(f"[TIMING] Bbox processing completed in {bbox_processing_end - bbox_processing_start:.3f} seconds")

    ocr_end_time = time.time()
    print(f"[TIMING] Total OCR processing completed in {ocr_end_time - ocr_start_time:.3f} seconds")
    return (text, bb), goal_filtering

def detect_image_type(image_np):
    """Auto-detect if image is desktop, web, or document"""
    h, w = image_np.shape[:2]

    # Simple heuristics based on image characteristics
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

    # Check for typical desktop patterns (taskbars, desktop icons)
    bottom_region = gray[int(h*0.9):, :]
    if np.mean(bottom_region) < 50:  # Dark taskbar
        return "desktop"

    # Check for typical web patterns (white backgrounds, structured layout)
    white_pixels = np.sum(gray > 240) / gray.size
    if white_pixels > 0.3:
        return "web"

    return "document"

def detect_ui_text_elements(image_np, existing_detections):
    """Specialized detection for UI elements like search bars, titles"""

    print("🔍 [UI-TEXT-ENHANCE] Running specialized UI text detection...")

    # Settings for UI text (search bars, titles, etc.)
    ui_text_args = {
        'paragraph': False,
        'width_ths': 0.7,      # Wide elements like search bars
        'height_ths': 0.7,     # Tall enough for text
        'text_threshold': 0.1,  # Lower threshold
        'low_text': 0.05,      # Very low for faint text
        'link_threshold': 0.8,  # Higher - don't connect distant text
        'canvas_size': 2048,    # Higher resolution
        'mag_ratio': 1.8,      # High magnification
    }

    try:
        ui_result = reader.readtext(image_np, **ui_text_args)

        enhanced_detections = []
        for item in ui_result:
            bbox_points = item[0]
            text_content = item[1].strip()
            confidence = item[2] if len(item) >= 3 else 1.0

            # Focus on UI-like text patterns
            if (is_ui_text_pattern(text_content, bbox_points, image_np.shape) and
                confidence > 0.05 and
                not is_already_detected(text_content, existing_detections)):

                enhanced_detections.append((bbox_points, text_content, confidence))
                print(f"✅ [UI-TEXT-FOUND] '{text_content[:30]}...' (conf: {confidence:.2f})")

        return enhanced_detections

    except Exception as e:
        print(f"[UI-TEXT-ENHANCE] Error: {e}")
        return []

def is_ui_text_pattern(text, bbox_points, image_shape):
    """Check if text looks like UI element (search bar, title, etc.)"""

    # Calculate position
    h, w = image_shape[:2]
    y_coords = [p[1] for p in bbox_points]
    avg_y = sum(y_coords) / len(y_coords)

    # Check if it's in typical UI areas
    is_top_area = avg_y < h * 0.15      # Top 15% (browser title area)
    is_search_area = h * 0.1 < avg_y < h * 0.3  # Search bar area

    # Check text characteristics
    has_meaningful_length = 3 <= len(text) <= 200
    not_just_numbers = not text.replace(' ', '').replace('.', '').replace(',', '').isdigit()

    # UI text patterns
    ui_indicators = [
        'search', 'amazon', 'www', 'http', '.com', '.org',
        'file', 'edit', 'view', 'help', 'tools', 'window',
        'results', 'filters', 'sort', 'price', 'delivery'
    ]

    has_ui_keywords = any(keyword in text.lower() for keyword in ui_indicators)

    return (is_top_area or is_search_area or has_ui_keywords) and has_meaningful_length and not_just_numbers

def check_ocr_box_with_merging(
    image_source: Union[str, Image.Image],
    display_img=False,
    output_bb_format='xyxy',
    goal_filtering=None,
    easyocr_args=None,
    use_pytesseract=False,
    merge_gap=6.0,
    vertical_tolerance=3.0,
    enable_merging=True,
    image_type="auto"  # ✅ ADD ONLY THIS LINE
):
    """ENHANCED: OCR with intelligent merging and multi-phase detection"""

    merging_start_time = time.time()
    print(f"[TIMING] Starting enhanced OCR with merging (gap={merge_gap}, tolerance={vertical_tolerance})...")

    # ✅ Get image as numpy array early for enhancement
    if isinstance(image_source, str):
        image_source = Image.open(image_source)
    if image_source.mode == 'RGBA':
        image_source = image_source.convert('RGB')

    image_np = np.array(image_source)
    w, h = image_source.size

    # ✅ Auto-detect image type if not specified
    if image_type == "auto":
        image_type = detect_image_type(image_np)
        print(f"🔍 [AUTO-DETECT] Image type detected as: {image_type}")

    # ✅ Get original OCR results with all optimizations
    (text, bb), is_goal_filtered = check_ocr_box(
        image_source,
        display_img=False,
        output_bb_format='xyxy',
        goal_filtering=goal_filtering,
        easyocr_args=easyocr_args,
        use_pytesseract=use_pytesseract
    )

    # ✅ FIXED: Enhanced detection for small text (like bookmarks)
    if len(text) < 50:  # Only run enhancement if we didn't find much text
        print("🔍 [SMALL-TEXT-ENHANCE] Running additional detection for bookmarks/small UI text...")

        # Use more aggressive EasyOCR settings for small text
        enhanced_args = (easyocr_args or {}).copy()
        enhanced_args.update({
            'text_threshold': 0.3,
            'low_text': 0.2,
            'width_ths': 0.5,
            'height_ths': 0.3
        })

        try:
            enhanced_result = reader.readtext(image_np, **enhanced_args)

            for item in enhanced_result:
                bbox_points = item[0]
                text_content = item[1].strip()
                confidence = item[2] if len(item) >= 3 else 1.0

                # Focus on top area (bookmarks) and reasonable confidence
                y_coords = [p[1] for p in bbox_points]
                avg_y = sum(y_coords) / len(y_coords)

                if (avg_y < 100 and  # Top toolbar area
                    confidence > 0.15 and
                    len(text_content) >= 2 and
                    text_content not in text):  # Not already found

                    text.append(text_content)
                    if output_bb_format == 'xywh':
                        bb.append(get_xywh(bbox_points))
                    else:
                        bb.append(get_xyxy(bbox_points))
                    print(f"✅ [SMALL-TEXT-FOUND] '{text_content}' (conf: {confidence:.2f})")

        except Exception as e:
            print(f"[SMALL-TEXT-ENHANCE] Error: {e}")

    # ✅ NEW: Multi-phase enhanced detection
    if len(text) < 100:  # If we didn't find much text
        print("🔍 [MULTI-PHASE-ENHANCE] Running enhanced detection phases...")

        # Phase 1: Paragraph text (for websites)
        if image_type in ["web", "document"]:
            paragraph_detections = detect_paragraph_text(image_np, text, easyocr_args)
            for bbox_points, text_content, confidence in paragraph_detections:
                text.append(text_content)
                if output_bb_format == 'xywh':
                    bb.append(get_xywh(bbox_points))
                else:
                    bb.append(get_xyxy(bbox_points))

        # Phase 2: Numerical data (for all types)
        numerical_detections = detect_numerical_data(image_np, text)

        # Phase 3: UI text elements (search bars, titles, etc.)
        ui_text_detections = detect_ui_text_elements(image_np, text)
        for bbox_points, text_content, confidence in ui_text_detections:
            text.append(text_content)
            if output_bb_format == 'xywh':
                bb.append(get_xywh(bbox_points))
            else:
                bb.append(get_xyxy(bbox_points))

        # Phase 4: Browser UI text (search bars, titles, etc.)
        if 'detect_browser_ui_text' in globals():
            browser_detections = detect_browser_ui_text(image_np)
            for bbox_points, text_content, confidence in browser_detections:
                text.append(text_content)
                if output_bb_format == 'xywh':
                    bb.append(get_xywh(bbox_points))
                else:
                    bb.append(get_xyxy(bbox_points))

        for bbox_points, text_content, confidence in numerical_detections:
            text.append(text_content)
            if output_bb_format == 'xywh':
                bb.append(get_xywh(bbox_points))
            else:
                bb.append(get_xyxy(bbox_points))

    # ✅ REST OF EXISTING MERGING CODE UNCHANGED...
    if enable_merging and text and bb:
        merge_start = time.time()
        print(f"\n📊 [MERGE] Original OCR: {len(text)} text detections")

        # ✅ RESTORE SMART MERGING WITH TIMING
        conversion_start = time.time()
        ocr_elements = []
        for txt, bbox in zip(text, bb):
            if output_bb_format == 'xywh':
                x, y, width, height = bbox
                x1, y1, x2, y2 = x, y, x + width, y + height
            else:
                x1, y1, x2, y2 = bbox

            norm_bbox = [x1/w, y1/h, x2/w, y2/h]
            ocr_elements.append({
                'bbox': norm_bbox,
                'content': txt,
                'type': 'text'
            })
        conversion_end = time.time()
        print(f"[TIMING] Element conversion completed in {conversion_end - conversion_start:.3f} seconds")

        # ✅ RESTORE OPTIMIZED MERGING
        merging_algo_start = time.time()
        merged_elements = optimized_horizontal_merging(
            ocr_elements,
            adaptive_gap=True,
            adaptive_tolerance=True,
            min_merge_confidence=0.7
        )
        merging_algo_end = time.time()
        print(f"[TIMING] Merging algorithm completed in {merging_algo_end - merging_algo_start:.3f} seconds")

        # ✅ Convert back with validation
        result_conversion_start = time.time()
        merged_text = []
        merged_bb = []

        for elem in merged_elements:
            merged_text.append(elem['content'])
            norm_bbox = elem['bbox']
            x1, y1, x2, y2 = norm_bbox[0], norm_bbox[1], norm_bbox[2], norm_bbox[3]

            if output_bb_format == 'xywh':
                merged_bb.append((x1, y1, x2-x1, y2-y1))
            else:
                merged_bb.append((x1, y1, x2, y2))

        result_conversion_end = time.time()
        print(f"[TIMING] Result conversion completed in {result_conversion_end - result_conversion_start:.3f} seconds")

        # ✅ COORDINATE VALIDATION WITH TIMING
        validation_start = time.time()
        valid_boxes = []
        valid_text = []

        for i, (text_item, bbox) in enumerate(zip(merged_text, merged_bb)):
            if all(coord == 0.0 for coord in bbox):
                print(f"❌ [COORDINATE-CHECK] Box {i} has zero coordinates: {bbox} - SKIPPING")
                continue
            if any(coord < 0 for coord in bbox):
                print(f"❌ [COORDINATE-CHECK] Box {i} has negative coordinates: {bbox} - SKIPPING")
                continue

            valid_boxes.append(bbox)
            valid_text.append(text_item)

        validation_end = time.time()
        print(f"[TIMING] Coordinate validation completed in {validation_end - validation_start:.3f} seconds")
        print(f"✅ [COORDINATE-CHECK] Kept {len(valid_boxes)} valid boxes out of {len(merged_bb)}")

        merge_end = time.time()
        print(f"[TIMING] Total merging completed in {merge_end - merge_start:.3f} seconds")

        merging_end_time = time.time()
        print(f"[TIMING] Total enhanced OCR with merging completed in {merging_end_time - merging_start_time:.3f} seconds")

        return valid_text, valid_boxes

    else:
        # ✅ NORMALIZE NON-MERGED PATH WITH TIMING
        norm_start = time.time()
        normalized_bb = []
        for bbox in bb:
            if output_bb_format == 'xywh':
                x, y, width, height = bbox
                normalized_bb.append((x/w, y/h, width/w, height/h))
            else:
                x1, y1, x2, y2 = bbox
                normalized_bb.append((x1/w, y1/h, x2/w, y2/h))

        norm_end = time.time()
        print(f"[TIMING] Coordinate normalization completed in {norm_end - norm_start:.3f} seconds")

        merging_end_time = time.time()
        print(f"[TIMING] Total enhanced OCR processing completed in {merging_end_time - merging_start_time:.3f} seconds")

        return text, normalized_bb

def streamlined_text_detection(image_source: Union[str, Image.Image], use_pytesseract=False, easyocr_args=None):
    """
    Streamlined text detection that replaces the over-engineered check_ocr_box_with_merging pipeline.

    Simplified approach:
    1. Single OCR pass with optimized settings
    2. Smart filtering for UI elements (tabs, buttons, small text)
    3. Basic text merging for fragments
    4. Return normalized coordinates

    Args:
        image_source: PIL Image or path to image
        use_pytesseract: Whether to use Pytesseract instead of EasyOCR
        easyocr_args: Arguments for EasyOCR (simplified)

    Returns:
        tuple: (text_list, bbox_list_normalized, success_flag)
    """
    ocr_start = time.time()
    print("[TIMING] Starting streamlined text detection...")

    # Setup image
    if isinstance(image_source, str):
        image_source = Image.open(image_source)
    if image_source.mode == 'RGBA':
        image_source = image_source.convert('RGB')

    image_np = np.array(image_source)
    w, h = image_source.size

    text_list = []
    bbox_list = []

    # Choose OCR engine and run detection
    if use_pytesseract and pytesseract_initialized:
        print("   🔧 Using Pytesseract with optimized settings...")
        try:
            # Use optimized Pytesseract config for UI elements
            config = '--oem 3 --psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,()[]{}:;!?@#$%^&*+=<>~/|\\"-_ '

            result = pytesseract.image_to_data(
                image_source,
                config=config,
                output_type=pytesseract.Output.DICT
            )

            # Process Pytesseract results
            for i in range(len(result['text'])):
                text_content = result['text'][i].strip()
                confidence = int(result['conf'][i]) / 100.0

                # ✅ FIXED: More permissive confidence threshold for small UI text
                if (text_content and
                    len(text_content) >= 1 and
                    confidence > 0.15 and  # LOWERED from 0.3 - UI text can have lower confidence
                    not is_noise_text(text_content)):

                    # Get bounding box
                    left = result['left'][i]
                    top = result['top'][i]
                    width = result['width'][i]
                    height = result['height'][i]

                    # Convert to xyxy format and normalize
                    bbox_normalized = [
                        left / w,
                        top / h,
                        (left + width) / w,
                        (top + height) / h
                    ]

                    text_list.append(text_content)
                    bbox_list.append(bbox_normalized)

            print(f"   ✅ Pytesseract found {len(text_list)} text elements")

        except Exception as e:
            print(f"   ❌ Pytesseract failed: {e}, falling back to EasyOCR")
            use_pytesseract = False

    if not use_pytesseract:
        print("   🔧 Using EasyOCR with optimized settings...")
        setup_easy_ocr()

        # ✅ ENHANCED: OCR settings optimized for both light and dark backgrounds
        if easyocr_args is None:
            easyocr_args = {}

        # Analyze image for background optimization
        avg_brightness = np.mean(image_np)
        is_dark_theme = avg_brightness < 100  # Dark background detection

        if is_dark_theme:
            print("   🔧 Dark background detected - using optimized settings")
            ocr_settings = {
                'width_ths': 0.3,      # Lower for better dark text detection
                'height_ths': 0.2,     # Lower for small dark theme text
                'text_threshold': 0.3, # More sensitive for light-on-dark text
                'link_threshold': 0.2, # Better linking for dark themes
                'low_text': 0.15,      # Lower confidence acceptable
                'paragraph': False,    # UI mode
                'contrast_ths': 0.1,   # Better contrast detection
                'adjust_contrast': 0.5 # Enhance contrast for dark backgrounds
            }
        else:
            print("   🔧 Light background detected - using standard settings")
            ocr_settings = {
                'width_ths': 0.5,      # Standard width threshold
                'height_ths': 0.3,     # Standard height threshold
                'text_threshold': 0.4, # Standard text detection
                'link_threshold': 0.3, # Standard linking
                'low_text': 0.2,      # Standard low confidence
                'paragraph': False     # UI mode
            }

        # Update with any provided args
        ocr_settings.update(easyocr_args)

        try:
            result = reader.readtext(image_np, **ocr_settings)

            # Process EasyOCR results
            for item in result:
                bbox_points = item[0]
                text_content = item[1].strip()
                confidence = item[2] if len(item) >= 3 else 1.0

                # ✅ FIXED: Very permissive filtering for maximum text capture
                if (text_content and
                    len(text_content) >= 1 and
                    confidence > 0.1 and   # VERY LOW threshold to catch all text
                    not is_noise_text(text_content) and
                    is_valid_ui_text(text_content, bbox_points, w, h)):

                    # Convert bbox points to normalized xyxy
                    x_coords = [p[0] for p in bbox_points]
                    y_coords = [p[1] for p in bbox_points]

                    bbox_normalized = [
                        min(x_coords) / w,
                        min(y_coords) / h,
                        max(x_coords) / w,
                        max(y_coords) / h
                    ]

                    text_list.append(text_content)
                    bbox_list.append(bbox_normalized)

            print(f"   ✅ EasyOCR found {len(text_list)} text elements")

        except Exception as e:
            print(f"   ❌ EasyOCR failed: {e}")
            ocr_end = time.time()
            print(f"[TIMING] Text detection failed in {ocr_end - ocr_start:.3f} seconds")
            return [], [], False

    # ✅ FIXED: Conservative text merging - only merge obvious continuations
    if text_list and len(text_list) > 1:
        print(f"   🔗 Before merging: {len(text_list)} text fragments")

        # MUCH MORE CONSERVATIVE: Only merge very close, obviously related text
        text_list, bbox_list = merge_nearby_text_simple(text_list, bbox_list, merge_distance=0.02)
        print(f"   🔗 After conservative merge: {len(text_list)} text elements")

    ocr_end = time.time()
    print(f"[TIMING] Streamlined text detection completed in {ocr_end - ocr_start:.3f} seconds")

    return text_list, bbox_list, True


def is_noise_text(text):
    """FIXED: Very conservative noise detection - only remove obvious garbage"""
    if not text or len(text.strip()) == 0:
        return True

    text = text.strip()

    # Only remove single special characters that are clearly noise
    if len(text) == 1 and text in '.,|_-+=<>[]{}()/#\\':
        return True

    # Only remove very repetitive patterns (5+ same characters)
    if len(set(text)) == 1 and len(text) > 5:
        return True

    # Only remove text that's 90%+ special characters (very conservative)
    special_char_ratio = sum(1 for c in text if not c.isalnum() and c != ' ') / len(text) if text else 0
    if special_char_ratio > 0.9:
        return True

    # Don't filter anything else - keep all legitimate text
    return False


def is_valid_ui_text(text, bbox_points, image_width, image_height):
    """FIXED: Very permissive text validation - accept almost all text"""
    # Calculate text area
    x_coords = [p[0] for p in bbox_points]
    y_coords = [p[1] for p in bbox_points]
    width = max(x_coords) - min(x_coords)
    height = max(y_coords) - min(y_coords)
    area_ratio = (width * height) / (image_width * image_height)

    # Only reject text that covers more than 80% of screen (obvious background)
    if area_ratio > 0.8:
        return False

    # Accept almost all text - don't be picky about length
    if len(text.strip()) >= 1:  # Any non-empty text
        return True

    return False


def merge_nearby_text_simple(text_list, bbox_list, merge_distance=0.02):
    """Intelligent merging for meaningful text blocks (titles, prices, navigation)"""
    if len(text_list) <= 1:
        return text_list, bbox_list

    print(f"🔗 [MERGE-DEBUG] Starting merge with distance={merge_distance:.3f}")
    print(f"🔗 [MERGE-DEBUG] Input: {len(text_list)} text elements")

    # Debug: Show first few elements
    for i, (text, bbox) in enumerate(zip(text_list[:3], bbox_list[:3])):
        print(f"   Element {i}: '{text}' at {bbox}")

    merged_text = []
    merged_bbox = []
    used_indices = set()

    for i, (text1, bbox1) in enumerate(zip(text_list, bbox_list)):
        if i in used_indices:
            continue

        # Start with current element
        merge_group = [(text1, bbox1, i)]
        used_indices.add(i)

        # ✅ IMPROVED: Multi-pass merging for better grouping
        # Pass 1: Horizontal line elements (prices, titles)
        center1_y = (bbox1[1] + bbox1[3]) / 2
        for j, (text2, bbox2) in enumerate(zip(text_list, bbox_list)):
            if j == i or j in used_indices:
                continue

            center2_y = (bbox2[1] + bbox2[3]) / 2
            horizontal_gap = abs(bbox2[0] - bbox1[2])  # Gap between boxes
            vertical_alignment = abs(center1_y - center2_y)

            # Smart horizontal merging conditions
            should_merge_horizontal = (
                vertical_alignment < merge_distance * 0.7 and  # Same line
                horizontal_gap < merge_distance * 3 and        # Close horizontally
                (
                    # Price patterns: "$89" + "90" = "$89.90"
                    (text1.startswith('$') and text2.isdigit()) or
                    (text2.startswith('$') and text1.isdigit()) or
                    # Word continuation patterns
                    (len(text1.split()) == 1 and len(text2.split()) == 1 and
                     horizontal_gap < merge_distance * 2) or
                    # Product title fragments
                    (len(text1) > 2 and len(text2) > 2 and horizontal_gap < merge_distance * 1.5)
                )
            )

            if should_merge_horizontal:
                merge_group.append((text2, bbox2, j))
                used_indices.add(j)

        # Pass 2: Vertical grouping for product descriptions
        base_bbox = bbox1
        for j, (text2, bbox2) in enumerate(zip(text_list, bbox_list)):
            if j == i or j in used_indices:
                continue

            vertical_gap = abs(bbox2[1] - base_bbox[3])  # Gap below current element
            horizontal_overlap = min(base_bbox[2], bbox2[2]) - max(base_bbox[0], bbox2[0])
            box_width = bbox2[2] - bbox2[0]

            # Vertical grouping for related content (descriptions, details)
            should_merge_vertical = (
                vertical_gap < merge_distance * 2 and           # Close vertically
                horizontal_overlap > box_width * 0.3 and        # Good horizontal overlap
                len(text2) > 3 and                             # Meaningful text
                vertical_gap < merge_distance * 4               # Not too far apart
            )

            if should_merge_vertical:
                merge_group.append((text2, bbox2, j))
                used_indices.add(j)

        # Create final merged element
        if len(merge_group) == 1:
            merged_text.append(text1)
            merged_bbox.append(bbox1)
        else:
            # Sort elements for proper reading order
            # First by Y (top to bottom), then by X (left to right)
            merge_group.sort(key=lambda x: (x[1][1], x[1][0]))

            # Smart text joining
            texts = [item[0] for item in merge_group]
            bboxes = [item[1] for item in merge_group]

            # Check if this looks like a price
            is_price_group = any(text.startswith('$') for text in texts)
            if is_price_group:
                # Join price components tightly
                final_text = ''.join(texts) if any(t.isdigit() for t in texts) else ' '.join(texts)
            else:
                # Regular text joining
                final_text = ' '.join(texts)

            # Create merged bounding box
            merged_box = [
                min(bbox[0] for bbox in bboxes),  # min x
                min(bbox[1] for bbox in bboxes),  # min y
                max(bbox[2] for bbox in bboxes),  # max x
                max(bbox[3] for bbox in bboxes)   # max y
            ]

            merged_text.append(final_text)
            merged_bbox.append(merged_box)

            # Debug: Show successful merges
            print(f"🔗 [MERGE-SUCCESS] '{' + '.join(texts)}' → '{final_text}'")

    print(f"🔗 [MERGE-DEBUG] Result: {len(merged_text)} elements (merged from {len(text_list)})")
    return merged_text, merged_bbox
