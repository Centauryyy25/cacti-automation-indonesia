"""Wrapper to expose CSV cleaning utilities as a package module."""

from data_cleaner import process_csv  # re-export for package import paths

__all__ = ["process_csv"]

