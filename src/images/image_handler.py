"""
Image handling module for downloading, validating, and optimizing images.
"""
import os
import uuid
from io import BytesIO
from pathlib import Path
from typing import Optional

import requests
from PIL import Image, UnidentifiedImageError

from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ImageHandler:
    """Download, validate, and optimize images for posting."""

    def __init__(
        self,
        max_size_mb: float = 5.0,
        min_width: int = 720,
        min_height: int = 720,
        preferred_format: str = "jpg"
    ):
        """
        Initialize image handler.

        Args:
            max_size_mb: Maximum allowed image size in MB
            min_width: Minimum image width in pixels
            min_height: Minimum image height in pixels
            preferred_format: Preferred output format
        """
        self.max_size_bytes = int(max_size_mb * 1024 * 1024)
        self.min_width = min_width
        self.min_height = min_height
        self.preferred_format = preferred_format.lower().replace("jpeg", "jpg")
        self.output_dir = Path("images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_from_url(self, url: str, save_path: Optional[str] = None) -> Optional[str]:
        """
        Download an image from a URL and save it locally.

        Args:
            url: Image URL
            save_path: Optional explicit save path

        Returns:
            Local file path if successful, None otherwise
        """
        if not url:
            logger.warning("No image URL provided")
            return None

        try:
            logger.info(f"Downloading image from: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            image = Image.open(BytesIO(response.content))
            image.load()

            final_path = self._resolve_output_path(image, save_path)
            self._save_image(image, final_path)

            if not self.validate_image(str(final_path)):
                logger.warning("Downloaded image needs optimization")
                optimized_path = self.optimize_image(str(final_path))
                if not optimized_path or not self.validate_image(optimized_path):
                    logger.error("Downloaded image is invalid after optimization")
                    self._safe_remove(final_path)
                    return None
                return optimized_path

            logger.info(f"Image downloaded successfully: {final_path}")
            return str(final_path)

        except requests.RequestException as exc:
            logger.error(f"Failed to download image: {exc}")
            return None
        except UnidentifiedImageError:
            logger.error("Downloaded file is not a valid image")
            return None
        except Exception as exc:
            logger.error(f"Unexpected error while downloading image: {exc}", exc_info=True)
            return None

    def search_unsplash(self, keywords: str, access_key: str) -> Optional[str]:
        """
        Search Unsplash and return a downloadable image URL.

        Args:
            keywords: Search terms
            access_key: Unsplash API access key

        Returns:
            Image URL if found, None otherwise
        """
        if not keywords:
            logger.warning("No keywords provided for Unsplash search")
            return None

        if not access_key:
            logger.warning("No Unsplash access key provided")
            return None

        try:
            logger.info(f"Searching Unsplash for: {keywords}")
            response = requests.get(
                "https://api.unsplash.com/search/photos",
                params={
                    "query": f"{keywords} board game tabletop",
                    "per_page": 1,
                    "orientation": "squarish",
                    "content_filter": "high"
                },
                headers={
                    "Accept-Version": "v1",
                    "Authorization": f"Client-ID {access_key}"
                },
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])

            if not results:
                logger.warning(f"No Unsplash results found for: {keywords}")
                return None

            image_url = results[0].get("urls", {}).get("regular")
            if image_url:
                logger.info("Found Unsplash image")
            else:
                logger.warning("Unsplash result missing image URL")
            return image_url

        except requests.RequestException as exc:
            logger.error(f"Unsplash search failed: {exc}")
            return None
        except Exception as exc:
            logger.error(f"Unexpected error while searching Unsplash: {exc}", exc_info=True)
            return None

    def validate_image(self, path: str) -> bool:
        """
        Validate image size, dimensions, and format.

        Args:
            path: Local image path

        Returns:
            True if valid, False otherwise
        """
        file_path = Path(path)
        if not file_path.exists():
            logger.error(f"Image file not found: {path}")
            return False

        try:
            file_size = file_path.stat().st_size
            if file_size > self.max_size_bytes:
                logger.warning(
                    f"Image too large: {file_size} bytes (max: {self.max_size_bytes})"
                )
                return False

            with Image.open(file_path) as image:
                width, height = image.size
                image_format = (image.format or "").lower().replace("jpeg", "jpg")

                if width < self.min_width or height < self.min_height:
                    logger.warning(
                        f"Image dimensions too small: {width}x{height} "
                        f"(min: {self.min_width}x{self.min_height})"
                    )
                    return False

                if image_format not in {"jpg", "png", "webp"}:
                    logger.warning(f"Unsupported image format: {image_format}")
                    return False

            return True

        except UnidentifiedImageError:
            logger.error(f"Corrupted or unsupported image file: {path}")
            return False
        except Exception as exc:
            logger.error(f"Failed to validate image: {exc}", exc_info=True)
            return False

    def optimize_image(self, path: str) -> Optional[str]:
        """
        Optimize image in place to fit posting requirements.

        Args:
            path: Local image path

        Returns:
            Final image path if successful, None otherwise
        """
        file_path = Path(path)
        if not file_path.exists():
            logger.error(f"Image file not found for optimization: {path}")
            return None

        try:
            with Image.open(file_path) as image:
                image = image.convert("RGB")

                if image.width < self.min_width or image.height < self.min_height:
                    # Upscale only to the minimum accepted dimensions.
                    image = image.resize(
                        (
                            max(image.width, self.min_width),
                            max(image.height, self.min_height)
                        ),
                        Image.Resampling.LANCZOS
                    )

                output_path = file_path.with_suffix(f".{self.preferred_format}")
                quality = 90

                while quality >= 60:
                    self._save_image(image, output_path, quality=quality)
                    if output_path.stat().st_size <= self.max_size_bytes:
                        logger.info(
                            f"Image optimized successfully: {output_path} "
                            f"(quality={quality})"
                        )
                        if output_path != file_path:
                            self._safe_remove(file_path)
                        return str(output_path)
                    quality -= 10

                logger.error("Unable to optimize image within size limit")
                return None

        except UnidentifiedImageError:
            logger.error(f"Cannot optimize invalid image file: {path}")
            return None
        except Exception as exc:
            logger.error(f"Failed to optimize image: {exc}", exc_info=True)
            return None

    def _resolve_output_path(self, image: Image.Image, save_path: Optional[str]) -> Path:
        """Build an output path for a downloaded image."""
        if save_path:
            return Path(save_path)

        image_format = (image.format or self.preferred_format).lower().replace("jpeg", "jpg")
        extension = image_format if image_format in {"jpg", "png", "webp"} else self.preferred_format
        filename = f"{uuid.uuid4().hex}.{extension}"
        return self.output_dir / filename

    def _save_image(self, image: Image.Image, path: Path, quality: int = 92) -> None:
        """Save image using a normalized output format."""
        path.parent.mkdir(parents=True, exist_ok=True)
        image_format = path.suffix.lower().lstrip(".").replace("jpg", "JPEG")
        save_kwargs = {"optimize": True}

        if image_format == "JPEG":
            save_kwargs["quality"] = quality
            save_kwargs["format"] = "JPEG"
            image = image.convert("RGB")
        elif image_format == "PNG":
            save_kwargs["format"] = "PNG"
        elif image_format == "WEBP":
            save_kwargs["quality"] = quality
            save_kwargs["format"] = "WEBP"
        else:
            path = path.with_suffix(f".{self.preferred_format}")
            save_kwargs["quality"] = quality
            save_kwargs["format"] = "JPEG"
            image = image.convert("RGB")

        image.save(path, **save_kwargs)

    def _safe_remove(self, path: Path) -> None:
        """Remove temporary files without raising cleanup errors."""
        try:
            if path.exists():
                os.remove(path)
        except OSError as exc:
            logger.warning(f"Failed to remove temporary file {path}: {exc}")
