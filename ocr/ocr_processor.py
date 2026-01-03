"""Wrapper module to expose OCR utilities via the ocr package.

This preserves backward compatibility while providing a structured import path.
"""

from easyocr_image_to_text import (
    image_to_text,
    process_images_in_folder,
    clean_ocr_text,
    save_processed_data,
    convert_json_to_csv,
    process_images_in_folder_with_custom_output,
)

__all__ = [
    "image_to_text",
    "process_images_in_folder",
    "clean_ocr_text",
    "save_processed_data",
    "convert_json_to_csv",
    "process_images_in_folder_with_custom_output",
]

