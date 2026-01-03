"""Wrapper to expose the singleton progress tracker from the package."""

from progress_tracker import progress, ProgressTracker  # re-export

__all__ = ["progress", "ProgressTracker"]

