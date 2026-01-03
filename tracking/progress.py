"""Wrapper to expose the singleton progress tracker from the package."""

from progress_tracker import ProgressTracker, progress  # re-export

__all__ = ["progress", "ProgressTracker"]

