# backend/rag/ingestion/captioner.py

import requests
from io import BytesIO
from PIL import Image
from functools import lru_cache
from transformers import Blip2Processor, Blip2ForConditionalGeneration
import torch

from rag.config import get_settings
from rag.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_blip2():
    logger.info(f"Loading BLIP-2 model: {settings.BLIP_MODEL} on {settings.BLIP_DEVICE}")
    processor = Blip2Processor.from_pretrained(settings.BLIP_MODEL)
    model = Blip2ForConditionalGeneration.from_pretrained(
        settings.BLIP_MODEL,
        torch_dtype=torch.float16 if settings.BLIP_DEVICE == "cuda" else torch.float32,
    ).to(settings.BLIP_DEVICE)
    model.eval()
    return processor, model


def caption_from_url(image_url: str) -> str:
    """
    Download image from URL and generate a descriptive caption using BLIP-2.
    Returns a single caption string.
    """
    response = requests.get(image_url, timeout=10)
    response.raise_for_status()
    image = Image.open(BytesIO(response.content)).convert("RGB")

    return caption_from_pil(image)


def caption_from_pil(image: Image.Image) -> str:
    """
    Generate caption from an already-loaded PIL Image.
    """
    processor, model = _load_blip2()
    device = settings.BLIP_DEVICE

    inputs = processor(images=image, return_tensors="pt").to(
        device,
        torch.float16 if device == "cuda" else torch.float32,
    )

    with torch.no_grad():
        output = model.generate(**inputs, max_new_tokens=80)

    caption = processor.decode(output[0], skip_special_tokens=True).strip()
    logger.debug(f"BLIP-2 caption: {caption}")
    return caption