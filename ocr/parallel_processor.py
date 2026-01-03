"""Parallel OCR processing with ProcessPoolExecutor.

Provides faster OCR processing by utilizing multiple CPU cores.
Falls back to sequential processing if parallelization fails.
"""

from __future__ import annotations

import logging
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

try:
    from config import settings
except ImportError:
    class _FallbackSettings:
        OCR_BATCH_SIZE = 4
    settings = _FallbackSettings()

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result of OCR processing for a single image."""
    image_path: str
    success: bool
    extracted_text: str = ""
    processed_data: dict = None
    error: str = ""
    processing_time: float = 0.0
    
    def __post_init__(self):
        if self.processed_data is None:
            self.processed_data = {}


def _process_single_image(
    image_path: str,
    ocr_func: Callable,
    **kwargs
) -> OCRResult:
    """
    Process a single image with OCR.
    This function runs in a separate process.
    """
    start_time = time.time()
    
    try:
        # Import EasyOCR here to avoid pickling issues
        import easyocr
        
        # Initialize reader in the worker process
        reader = easyocr.Reader(
            ['en'],
            gpu=kwargs.get('use_gpu', False),
            verbose=False
        )
        
        # Read and process image
        result = reader.readtext(image_path)
        extracted_text = " ".join([r[1] for r in result])
        
        processing_time = time.time() - start_time
        
        return OCRResult(
            image_path=image_path,
            success=True,
            extracted_text=extracted_text,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        return OCRResult(
            image_path=image_path,
            success=False,
            error=str(e),
            processing_time=processing_time
        )


class ParallelOCRProcessor:
    """
    Parallel OCR processor using ProcessPoolExecutor.
    
    Usage:
        processor = ParallelOCRProcessor(max_workers=4)
        results = processor.process_folder("/path/to/images")
    """
    
    def __init__(
        self,
        max_workers: int = None,
        use_gpu: bool = False,
        batch_size: int = None
    ):
        """
        Initialize parallel OCR processor.
        
        Args:
            max_workers: Number of worker processes. Default: CPU count - 1
            use_gpu: Enable GPU acceleration (one worker per GPU)
            batch_size: Number of images per batch. Default from settings.
        """
        import multiprocessing
        
        if max_workers is None:
            # Leave 1 CPU for the main process
            max_workers = max(1, multiprocessing.cpu_count() - 1)
        
        self.max_workers = max_workers
        self.use_gpu = use_gpu
        self.batch_size = batch_size or getattr(settings, 'OCR_BATCH_SIZE', 4)
        
        logger.info(
            "Initialized ParallelOCRProcessor with %d workers, GPU=%s",
            self.max_workers, self.use_gpu
        )
    
    def process_images(
        self,
        image_paths: list[str],
        progress_callback: Callable[[int, int, str], None] = None
    ) -> list[OCRResult]:
        """
        Process multiple images in parallel.
        
        Args:
            image_paths: List of image file paths
            progress_callback: Optional callback(current, total, filename) for progress
        
        Returns:
            List of OCRResult objects
        """
        if not image_paths:
            return []
        
        total = len(image_paths)
        results: list[OCRResult] = []
        completed = 0
        
        logger.info("Starting parallel OCR for %d images with %d workers", total, self.max_workers)
        start_time = time.time()
        
        try:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_path = {
                    executor.submit(
                        _process_single_image,
                        path,
                        None,  # ocr_func not used in process
                        use_gpu=self.use_gpu
                    ): path
                    for path in image_paths
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_path):
                    path = future_to_path[future]
                    completed += 1
                    
                    try:
                        result = future.result(timeout=120)  # 2 min timeout per image
                        results.append(result)
                        
                        if result.success:
                            logger.debug("OCR completed: %s (%.2fs)", path, result.processing_time)
                        else:
                            logger.warning("OCR failed: %s - %s", path, result.error)
                            
                    except Exception as e:
                        logger.error("OCR task failed for %s: %s", path, e)
                        results.append(OCRResult(
                            image_path=path,
                            success=False,
                            error=str(e)
                        ))
                    
                    # Progress callback
                    if progress_callback:
                        try:
                            progress_callback(completed, total, os.path.basename(path))
                        except Exception:
                            pass
        
        except Exception as e:
            logger.error("Parallel OCR processing failed: %s. Falling back to sequential.", e)
            # Fallback to sequential processing
            return self._process_sequential(image_paths, progress_callback)
        
        elapsed = time.time() - start_time
        success_count = sum(1 for r in results if r.success)
        
        logger.info(
            "Parallel OCR complete: %d/%d successful in %.2fs (%.2f img/s)",
            success_count, total, elapsed, total / elapsed if elapsed > 0 else 0
        )
        
        return results
    
    def _process_sequential(
        self,
        image_paths: list[str],
        progress_callback: Callable = None
    ) -> list[OCRResult]:
        """Fallback sequential processing."""
        logger.info("Using sequential OCR processing")
        results = []
        
        for i, path in enumerate(image_paths):
            result = _process_single_image(path, None, use_gpu=self.use_gpu)
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, len(image_paths), os.path.basename(path))
        
        return results
    
    def process_folder(
        self,
        folder_path: str,
        extensions: tuple = ('.png', '.jpg', '.jpeg'),
        progress_callback: Callable = None
    ) -> list[OCRResult]:
        """
        Process all images in a folder.
        
        Args:
            folder_path: Path to folder containing images
            extensions: File extensions to process
            progress_callback: Optional progress callback
        
        Returns:
            List of OCRResult objects
        """
        folder = Path(folder_path)
        if not folder.exists():
            logger.error("Folder not found: %s", folder_path)
            return []
        
        # Find all images
        image_paths = []
        for ext in extensions:
            image_paths.extend(str(p) for p in folder.glob(f"*{ext}"))
            image_paths.extend(str(p) for p in folder.glob(f"*{ext.upper()}"))
        
        # Remove duplicates and sort
        image_paths = sorted(set(image_paths))
        
        if not image_paths:
            logger.warning("No images found in %s", folder_path)
            return []
        
        logger.info("Found %d images in %s", len(image_paths), folder_path)
        return self.process_images(image_paths, progress_callback)


# ==========================================================================
# Convenience function
# ==========================================================================
def process_images_parallel(
    folder_path: str,
    max_workers: int = None,
    use_gpu: bool = False,
    progress_callback: Callable = None
) -> list[OCRResult]:
    """
    Convenience function for parallel OCR processing.
    
    Args:
        folder_path: Path to folder containing images
        max_workers: Number of worker processes
        use_gpu: Enable GPU acceleration
        progress_callback: Optional progress callback
    
    Returns:
        List of OCRResult objects
    """
    processor = ParallelOCRProcessor(
        max_workers=max_workers,
        use_gpu=use_gpu
    )
    return processor.process_folder(folder_path, progress_callback=progress_callback)
