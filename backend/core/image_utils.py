"""
Image processing utilities for thumbnail generation.
"""
from io import BytesIO
from typing import BinaryIO, Union
from PIL import Image
import logging

logger = logging.getLogger(__name__)

THUMBNAIL_SIZE = (256, 256)
THUMBNAIL_FORMAT = "JPEG"
THUMBNAIL_QUALITY = 85


def generate_thumbnail(
    image_data: Union[bytes, BinaryIO],
    size: tuple[int, int] = THUMBNAIL_SIZE
) -> bytes:
    """
    Generate a center-cropped thumbnail from image data.

    Uses center cropping to ensure the thumbnail fills the entire size
    without black bars. The image is first resized to ensure one dimension
    matches the target, then the excess is cropped from the center.

    Args:
        image_data: Image data as bytes or file-like object
        size: Tuple of (width, height) for thumbnail. Default is 256x256.

    Returns:
        Thumbnail image data as JPEG bytes

    Raises:
        ValueError: If image cannot be processed
        IOError: If image format is unsupported
    """
    try:
        # Open image from bytes or file-like object
        if isinstance(image_data, bytes):
            image = Image.open(BytesIO(image_data))
        else:
            image = Image.open(image_data)

        # Convert to RGB if necessary (handles RGBA, P, L modes)
        if image.mode not in ('RGB', 'L'):
            # For images with transparency, use white background
            if image.mode == 'RGBA':
                background = Image.new('RGB', image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[3])  # Use alpha channel as mask
                image = background
            else:
                image = image.convert('RGB')

        # Calculate dimensions for center crop
        target_width, target_height = size
        target_ratio = target_width / target_height
        image_ratio = image.width / image.height

        if image_ratio > target_ratio:
            # Image is wider than target - fit height, crop width
            new_height = target_height
            new_width = int(new_height * image_ratio)
        else:
            # Image is taller than target - fit width, crop height
            new_width = target_width
            new_height = int(new_width / image_ratio)

        # Resize image to ensure one dimension matches target
        image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        # Calculate crop box to center the image
        left = (new_width - target_width) // 2
        top = (new_height - target_height) // 2
        right = left + target_width
        bottom = top + target_height

        # Crop to final size
        image = image.crop((left, top, right, bottom))

        # Save to bytes as JPEG
        output = BytesIO()
        image.save(output, format=THUMBNAIL_FORMAT, quality=THUMBNAIL_QUALITY, optimize=True)
        thumbnail_bytes = output.getvalue()

        logger.info(f"Generated thumbnail: {len(thumbnail_bytes)} bytes")
        return thumbnail_bytes

    except Exception as e:
        logger.error(f"Failed to generate thumbnail: {str(e)}")
        raise ValueError(f"Unable to process image: {str(e)}")


def get_image_dimensions(image_data: Union[bytes, BinaryIO]) -> tuple[int, int]:
    """
    Get dimensions of an image without loading the entire image into memory.

    Args:
        image_data: Image data as bytes or file-like object

    Returns:
        Tuple of (width, height)
    """
    try:
        if isinstance(image_data, bytes):
            image = Image.open(BytesIO(image_data))
        else:
            image = Image.open(image_data)

        return image.size
    except Exception as e:
        logger.error(f"Failed to get image dimensions: {str(e)}")
        raise ValueError(f"Unable to read image: {str(e)}")
