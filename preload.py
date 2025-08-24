import asyncio
import os
import traceback
from python.helpers import runtime, whisper, settings
from python.helpers.print_style import PrintStyle
from python.helpers import kokoro_tts
import models


async def preload():
    try:
        set = settings.get_default_settings()

        # preload whisper model
        async def preload_whisper():
            try:
                return await whisper.preload(set["stt_model_size"])
            except Exception as e:
                PrintStyle().error(f"Error in preload_whisper: {e}")

        # preload embedding model
        async def preload_embedding():
            if set["embed_model_provider"].lower() == "huggingface":
                try:
                    # Use the new LiteLLM-based model system
                    emb_mod = models.get_embedding_model(
                        "huggingface", set["embed_model_name"]
                    )
                    emb_txt = await emb_mod.aembed_query("test")
                    return emb_txt
                except Exception as e:
                    PrintStyle().error(f"Error in preload_embedding: {e}")

        # preload kokoro tts model if enabled
        async def preload_kokoro():
            if set["tts_kokoro"]:
                try:
                    return await kokoro_tts.preload()
                except Exception as e:
                    PrintStyle().error(f"Error in preload_kokoro: {e}")

        # preload yolo model
        async def preload_ocr_models():
            if runtime.is_development():
                return
            # create weights directories if they don't exist
            from python.helpers import files
            prefix = files.get_abs_path('OmniParser', 'weights')
            os.makedirs(f'{prefix}/easyocr', exist_ok=True)
            os.makedirs(f'{prefix}/paddleocr', exist_ok=True)
            os.makedirs(f'{prefix}/yolo', exist_ok=True)
            os.environ['EASYOCR_MODEL_PATH'] = f'{prefix}/easyocr'
            os.environ['TESSDATA_PREFIX'] = f'{prefix}/tesseract/tessdata'
            os.environ['YOLO_MODEL_PATH'] = f'{prefix}/yolo'

            try:
                # preload the omni parser models
                from huggingface_hub import hf_hub_download

                # icon_detect/{train_args.yaml,model.pt,model.yaml} icon_caption/{config.json,generation_config.json,model.safetensors}
                files = [
                    "icon_detect/train_args.yaml",
                    "icon_detect/model.pt",
                    "icon_detect/model.yaml",
                    "icon_caption/config.json",
                    "icon_caption/generation_config.json",
                    "icon_caption/model.safetensors"
                ]

                for file in files:
                    # Just download the files - they will be loaded by OmniParser when needed
                    file_path = hf_hub_download(
                        repo_id="microsoft/OmniParser-v2.0",
                        filename=file,
                        local_dir=os.environ['YOLO_MODEL_PATH'] + "/weights/"
                    )
                    PrintStyle().print(f"Downloaded: {file_path}")

                files = [
                    "model.safetensors",
                    "config.json"
                ]
                for file in files:
                    # also download the blip2 model
                    PrintStyle().print(f"Downloading blip2 model: {file}")
                    file_path = hf_hub_download(
                        repo_id="Salesforce/blip2-itm-vit-g-coco",
                        filename=file,
                        local_dir=os.environ['YOLO_MODEL_PATH'] + "/weights/blip2"
                    )
                    PrintStyle().print(f"Downloaded: {file_path}")

                # verify the models are loaded
                import lib.OmniParser.agent0 as agent0  # noqa: F401
                import python.tools.operator as operator  # noqa: F401
            except Exception as e:
                PrintStyle().error(f"Error in preload_ocr_models: {e}")
                PrintStyle().error(traceback.format_exc())

        # async tasks to preload
        tasks = [
            preload_embedding(),
            preload_ocr_models(),
            # preload_whisper(),
            # preload_kokoro()
        ]

        await asyncio.gather(*tasks, return_exceptions=True)
        PrintStyle().print("Preload completed")
    except Exception as e:
        PrintStyle().error(f"Error in preload: {e}")


# preload transcription model
if __name__ == "__main__":
    PrintStyle().print("Running preload...")
    runtime.initialize()
    asyncio.run(preload())
