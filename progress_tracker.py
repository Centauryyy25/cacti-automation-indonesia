"""Thread-safe progress tracking for scraping and OCR phases.

Exposes a singleton `progress` that stores two dicts: `scraping` and `ocr`.
Use `progress.update(section, updates)` to atomically update fields.
"""

from threading import Lock


class ProgressTracker:
    """Singleton progress tracker with a lock for atomic updates."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = Lock()
            cls._instance.reset()
        return cls._instance

    def reset(self):
        self.scraping = {
            'current': 0,
            'total': 1,
            'message': '',
            'status': 'idle',
            'current_file': '',
            'current_folder': ''
        }
        self.ocr = {
            'current': 0,
            'total': 1,
            'message': '',
            'status': 'idle',
            'current_file': ''
        }

    def update(self, section: str, updates: dict) -> None:
        """Thread-safe dict update on a section ('scraping' or 'ocr')."""
        with self._lock:
            getattr(self, section).update(updates)


progress = ProgressTracker()
