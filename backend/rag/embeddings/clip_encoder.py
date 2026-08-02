# backend/rag/embeddings/clip_encoder.py

import clip
import torch
import numpy as np
from PIL import Image
import requests
from io import BytesIO
from functools import lru_cache

from rag.config import get_settings
from rag.utils.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_model():
    """Load CLIP once and cache. Thread-safe via lru_cache."""
    logger.info(f"Loading CLIP model: {settings.CLIP_MODEL} on {settings.CLIP_DEVICE}")
    model, preprocess = clip.load(settings.CLIP_MODEL, device=settings.CLIP_DEVICE)
    model.eval()
    return model, preprocess


def encode_text(query: str) -> list[float]:
    """
    Encode a text query into a normalized CLIP embedding.
    Returns a flat list of floats (length 512 for ViT-B/32).
    """
    model, _ = _load_model()
    device = settings.CLIP_DEVICE

    with torch.no_grad():
        tokens = clip.tokenize([query], truncate=True).to(device)
        embedding = model.encode_text(tokens)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)  # L2 normalize

    logger.debug(f"Encoded text query — shape: {embedding.shape}")
    return embedding.squeeze().cpu().numpy().tolist()


def _resolve_wikimedia_url(url: str) -> str:
    """
    Resolve a Wikimedia image URL to a working download URL.

    Wikimedia recently restricted /thumb/ to specific sizes, causing 400s.
    This function tries:
      1. The original URL as-is
      2. If it's a /thumb/ URL, extract the filename and use the Wikimedia
         API to get a valid thumbnail URL at 320px width
      3. Fall back to the non-thumb original path

    Returns a URL that should be downloadable.
    """
    import re
    import urllib.parse

    # Check if it's a Wikimedia thumb URL
    thumb_match = re.search(
        r'/wikipedia/(commons|en)/thumb/[^/]+/[^/]+/([^/]+)/\d+px-',
        url
    )

    # Also check non-thumb /en/ URLs (fair-use images that get rate-limited)
    en_match = None
    if not thumb_match:
        en_match = re.search(
            r'/wikipedia/en/[^/]+/[^/]+/([^/]+)$',
            url
        )

    if not thumb_match and not en_match:
        return url  # Not a Wikimedia URL we need to fix

    if thumb_match:
        wiki_domain = thumb_match.group(1)
        filename = urllib.parse.unquote(thumb_match.group(2))
    else:
        wiki_domain = "en"
        filename = urllib.parse.unquote(en_match.group(1))

    # Use the Wikimedia API to get a valid thumbnail URL
    try:
        if wiki_domain == "commons":
            api_url = "https://commons.wikimedia.org/w/api.php"
        else:
            api_url = "https://en.wikipedia.org/w/api.php"

        resp = requests.get(
            api_url,
            params={
                "action": "query",
                "titles": f"File:{filename}",
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": 320,  # Standard allowed size
                "format": "json",
            },
            headers={"User-Agent": "RGStudioBot/1.0 (art-generation-project)"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            imageinfo = page.get("imageinfo", [{}])
            if imageinfo:
                thumb_url = imageinfo[0].get("thumburl")
                if thumb_url:
                    logger.debug(f"Resolved via API: {filename} -> {thumb_url[:80]}...")
                    return thumb_url
    except Exception as e:
        logger.warning(f"Wikimedia API fallback failed for {filename}: {e}")

    # Last resort: strip /thumb/ and size suffix to get original
    stripped = re.sub(
        r'/thumb/([^/]+/[^/]+/[^/]+)/\d+px-[^/]+$',
        r'/\1',
        url
    )
    return stripped


def encode_image_from_url(image_url: str) -> list[float]:
    """
    Encode an image from URL or local /images/ relative path.
    """
    from pathlib import Path

    if image_url.startswith("/images/"):
        relative = image_url.replace("/images/", "")
        backend_dir = Path(__file__).resolve().parent.parent.parent
        local_file = backend_dir / "art_dataset" / relative
        if local_file.exists():
            return encode_image_from_file(str(local_file))

    model, preprocess = _load_model()
    device = settings.CLIP_DEVICE

    # Resolve Wikimedia URLs to working download URLs
    resolved_url = _resolve_wikimedia_url(image_url)

    # Stream response, cap at 10MB
    response = requests.get(
        resolved_url,
        timeout=15,
        headers={"User-Agent": "RGStudioBot/1.0 (art-generation-project; contact@rgstudio.dev)"},
        stream=True
    )
    response.raise_for_status()

    # Read max 10MB
    MAX_BYTES = 10 * 1024 * 1024
    content = b""
    for chunk in response.iter_content(chunk_size=8192):
        content += chunk
        if len(content) > MAX_BYTES:
            raise ValueError(f"Image too large (>{MAX_BYTES/1e6:.0f}MB), use a smaller image URL")

    image = Image.open(BytesIO(content)).convert("RGB")
    image.thumbnail((512, 512))  # CLIP only needs 224px anyway

    tensor = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        embedding = model.encode_image(tensor)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

    logger.debug(f"Encoded image from URL — shape: {embedding.shape}")
    return embedding.squeeze().cpu().numpy().tolist()


def encode_image_from_pil(image: Image.Image) -> list[float]:
    """
    Encode an already-loaded PIL image. Useful during ingestion.
    """
    model, preprocess = _load_model()
    device = settings.CLIP_DEVICE
    image.thumbnail((1024, 1024))  # add this line

    tensor = preprocess(image).unsqueeze(0).to(device)

    with torch.no_grad():
        embedding = model.encode_image(tensor)
        embedding = embedding / embedding.norm(dim=-1, keepdim=True)

    return embedding.squeeze().cpu().numpy().tolist()


def encode_image_from_file(file_path: str) -> list[float]:
    """
    Encode a local image file into a CLIP embedding.
    This is the production path — no network requests, just disk I/O.
    """
    from pathlib import Path

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Image file not found: {file_path}")

    image = Image.open(path).convert("RGB")
    image.thumbnail((512, 512))  # CLIP only needs 224px

    logger.debug(f"Encoding local image: {path.name}")
    return encode_image_from_pil(image)