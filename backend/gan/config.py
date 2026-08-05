# backend/gan/config.py

from functools import lru_cache

from pydantic_settings import BaseSettings


class GANSettings(BaseSettings):
    # Style transfer
    OUTPUT_SIZE: int = 512                # Output image resolution (square)
    STYLE_WEIGHT: float = 0.8            # AdaIN alpha: 0.0 = pure content, 1.0 = pure style
    CONTENT_LAYERS: str = "relu4_1"      # VGG layer for content features
    STYLE_LAYERS: str = "relu1_1,relu2_1,relu3_1,relu4_1"  # VGG layers for style

    # Generation
    MAX_IMAGE_SIZE: int = 1024           # Max input image dimension
    JPEG_QUALITY: int = 92               # Output JPEG quality
    TEMP_DIR: str = "tmp_generated"      # Temporary directory for generated images

    # Device
    GAN_DEVICE: str = "cpu"              # "cpu" or "cuda"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_gan_settings() -> GANSettings:
    return GANSettings()
