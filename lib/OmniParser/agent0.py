from email import utils
import os
import sys
import time

current_unix_ts = int(time.time())

root = os.path.abspath(os.path.dirname(__file__) + '/../..')
sys.path.append(root + "/lib/OmniParser")
sys.path.append(root + "/lib/OmniParser/util")
sys.path.append(root)


from python.helpers import files

# create weights directories if they don't exist
prefix = files.get_abs_path(root, 'OmniParser', 'weights')
os.makedirs(f'{prefix}/easyocr', exist_ok=True)
os.makedirs(f'{prefix}/tesseract', exist_ok=True)
os.makedirs(f'{prefix}/yolo', exist_ok=True)
os.environ['EASYOCR_MODEL_PATH'] = f'{prefix}/easyocr'
os.environ['TESSDATA_PREFIX'] = f'{prefix}/tesseract/tessdata'
os.environ['YOLO_MODEL_PATH'] = f'{prefix}/yolo'

from lib.OmniParser.util.utils import (
    setup_pytesseract, get_yolo_model, get_caption_model_processor,
    get_som_labeled_img, setup_easy_ocr, streamlined_text_detection
)

from typing import Optional, Tuple

import gradio as gr
import numpy as np
import torch
from PIL import Image
import io
from typing import Any

import base64, os

# argparse only imported when script is run directly, not when imported

yolo_model: Optional[torch.nn.Module] = None
caption_model_processor: Optional[Any] = None


def setup_yolo_model():
    global yolo_model
    yolo_model = get_yolo_model(model_path=os.environ['YOLO_MODEL_PATH'] + '/weights/icon_detect/model.pt')


def setup_caption_model_processor():
    global caption_model_processor
    caption_model_processor = get_caption_model_processor(
        model_name="florence2",
        model_name_or_path=os.environ['YOLO_MODEL_PATH'] + '/weights/icon_caption_florence'
    )

# caption_model_processor = get_caption_model_processor(model_name="blip2", model_name_or_path=os.environ['YOLO_MODEL_PATH'] + '/weights/blip2')

MARKDOWN = """
# OmniParser for Pure Vision Based General GUI Agent 🔥
<div>
    <a href="https://arxiv.org/pdf/2408.00203">
        <img src="https://img.shields.io/badge/arXiv-2408.00203-b31b1b.svg" alt="Arxiv" style="display:inline-block;">
    </a>
</div>

OmniParser is a screen parsing tool to convert general GUI screen to structured elements.
"""

DEVICE = torch.device('cpu')


# @spaces.GPU
# @torch.inference_mode()
# @torch.autocast(device_type="cuda", dtype=torch.bfloat16)
def format_annotations_for_ai(parsed_content_list):
    """Format annotations in a clean, AI-readable format with ALL essential information including rich captions"""
    formatted_lines = []

    for i, annotation in enumerate(parsed_content_list):
        # Extract essential information
        element_type = annotation.get('type', 'unknown')
        bbox = annotation.get('bbox', [0, 0, 0, 0])
        interactivity = annotation.get('interactivity', False)
        content = annotation.get('content', '')

        # Calculate center coordinates for clicking (fractional 0-1)
        if len(bbox) >= 4:
            center_x = (bbox[0] + bbox[2]) / 2
            center_y = (bbox[1] + bbox[3]) / 2
            bbox_str = f"bbox[{bbox[0]:.3f},{bbox[1]:.3f},{bbox[2]:.3f},{bbox[3]:.3f}]"
        else:
            center_x, center_y = 0.5, 0.5
            bbox_str = "bbox[unknown]"

        # ✅ SIMPLIFIED: Create clean description with Type and Text only
        descriptions = []

        # Add YOLO classification
        if element_type != 'unknown':
            descriptions.append(f"Type: {element_type}")

        # Add text content if available
        if content and content.strip():
            descriptions.append(f"Text: \"{content.strip()}\"")

        # Join descriptions or provide fallback
        if descriptions:
            description_str = " | ".join(descriptions)
        else:
            description_str = f"Type: {element_type}"

        # Format clean line for AI (no AI Description noise)
        if interactivity:
            # Clickable elements
            formatted_lines.append(f"Element {i}: CLICKABLE | center=({center_x:.3f},{center_y:.3f}) | {bbox_str} | {description_str}")
        else:
            # Non-clickable text elements
            formatted_lines.append(f"Element {i}: TEXT | center=({center_x:.3f},{center_y:.3f}) | {bbox_str} | {description_str}")

    # Add comprehensive guidance for AI
    header = "SCREEN ELEMENTS (use element_id when clicking):\n"
    footer = ("\n\nCLICK GUIDANCE:\n"
             "• Use element_id parameter with the number (e.g., element_id=5 to click Element 5)\n"
             "• Use center coordinates for clicking: center=(x,y) are the exact click points\n"
             "• bbox shows the full element area: bbox[x1,y1,x2,y2] from top-left to bottom-right\n"
             "• All coordinates are fractional (0.0-1.0) relative to screen size")

    return header + '\n'.join(formatted_lines) + footer

def smart_text_grouping(detected_boxes, group_distance=20):
    """Post-process EasyOCR results to group nearby text"""

    # First: Get good detection with conservative settings
    easyocr_conservative = {
        'paragraph': False,
        'width_ths': 0.06,
        'height_ths': 0.06,
        'link_threshold': 0.05,  # Conservative for good detection
        'text_threshold': 0.2,
        'low_text': 0.1,
    }

    # Then: Group nearby boxes manually
    grouped_boxes = []
    used_indices = set()

    for i, box1 in enumerate(detected_boxes):
        if i in used_indices:
            continue

        group = [box1]
        used_indices.add(i)

        # Find nearby boxes to group
        for j, box2 in enumerate(detected_boxes):
            if j in used_indices:
                continue

            if boxes_are_nearby(box1, box2, group_distance):
                group.append(box2)
                used_indices.add(j)

        # Merge the group into single box
        if len(group) > 1:
            merged_box = merge_text_boxes(group)
            grouped_boxes.append(merged_box)
        else:
            grouped_boxes.append(box1)

    return grouped_boxes

def boxes_are_nearby(box1, box2, max_distance):
    """Check if two boxes should be grouped"""
    x1, y1, w1, h1 = box1['bbox']
    x2, y2, w2, h2 = box2['bbox']

    # Calculate distance between box centers
    center1_x, center1_y = x1 + w1/2, y1 + h1/2
    center2_x, center2_y = x2 + w2/2, y2 + h2/2

    distance = ((center1_x - center2_x)**2 + (center1_y - center2_y)**2)**0.5

    return distance < max_distance

def process(
    image_input,
    box_threshold,
    iou_threshold,
    use_pytesseract,
    imgsz,
    batch_size=4,
    use_florence_captioning=False
) -> Tuple[Image.Image, str]:

    box_overlay_ratio = image_input.size[0] / 3200
    draw_bbox_config = {
        'text_scale': 0.8 * box_overlay_ratio,
        'text_thickness': max(int(2 * box_overlay_ratio), 1),
        'text_padding': max(int(3 * box_overlay_ratio), 1),
        'thickness': max(int(3 * box_overlay_ratio), 1),
    }

    easyocr_args = {
        'paragraph': False,
        'width_ths': 0.05,          # More reasonable
        'height_ths': 0.05,         # More reasonable
        'text_threshold': 0.1,     # Higher base confidence
        'low_text': 0.005,           # Higher low confidence
        'link_threshold': 0.05,     # Minimal linking
        'canvas_size': 1280,        # Good resolution
        'mag_ratio': 1.1,           # Modest magnification
        'slope_ths': 0.03,          # Reasonable slope
        'add_margin': 0.01,         # Reasonable margin
        'min_size': 2,              # Skip tiny noise
    }

        # ✅ Use streamlined text detection with dynamic optimization (no override)
    print("🔧 [AGENT] Using streamlined text detection with dynamic theme detection...")
    text_list, ocr_bbox, success = streamlined_text_detection(
        image_input,
        use_pytesseract=use_pytesseract,
        easyocr_args=easyocr_args  # Let streamlined detection handle optimization automatically
    )

    # Convert to expected format for compatibility with existing pipeline
    text = text_list  # List of text strings

    print(f"🔧 [AGENT] OCR returned {len(ocr_bbox)} boxes in normalized format")

    # Now ocr_bbox contains normalized coordinates [0-1] that match YOLO format
    dino_labled_img, label_coordinates, parsed_content_list = get_som_labeled_img(
        image_input, yolo_model,
        BOX_TRESHOLD=box_threshold,
        output_coord_in_ratio=True,
        ocr_bbox=ocr_bbox,  # ← Now normalized coordinates
        draw_bbox_config=draw_bbox_config,
        caption_model_processor=caption_model_processor,
        ocr_text=text,
        iou_threshold=iou_threshold,
        imgsz=imgsz,
        use_local_semantics=False,
        batch_size=batch_size,
        use_florence_captioning=use_florence_captioning  # ✅ Pass the optional flag
    )

    image = Image.open(io.BytesIO(base64.b64decode(dino_labled_img)))
    print('finish processing')
    # Format annotations for better AI readability with all necessary information
    formatted_annotations = format_annotations_for_ai(parsed_content_list)
    return image, formatted_annotations


if __name__ == '__main__':
    import argparse

    setup_easy_ocr()
    setup_pytesseract()

    setup_yolo_model()
    setup_caption_model_processor()

    parser = argparse.ArgumentParser()
    parser.add_argument('--image', type=str, required=False)
    parser.add_argument('--image-output', type=str, required=False)
    parser.add_argument('--text-output', type=str, required=False)

    elapsed_time = time.time() - current_unix_ts
    print(f"Elapsed time: {elapsed_time} seconds")

    args = parser.parse_args()
    if args.image is not None:
        im = Image.open(args.image)
        # scale_ratio = 540 / min(im.width, im.height)
        # new_width, new_height = int(im.width * scale_ratio), int(im.height * scale_ratio)
        # print(f"Resizing image from {im.width}x{im.height} to {new_width}x{new_height}")
        # resized_im = im.resize((new_width, new_height))
        image_output_component, text_output_component = process(im, 0.25, 0.3, True, 1024)
        # image_output_component = image_output_component.resize((im.width, im.height))
        image_output_component.save(args.image_output)
        with open(args.text_output, "w") as f:
            f.write(text_output_component)
