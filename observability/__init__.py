"""Observability package initialization."""

from observability.metrics import (
    metrics_bp,
    registry,
    http_requests_total,
    http_request_duration_seconds,
    pipeline_runs_total,
    pipeline_run_duration_seconds,
    scraping_items_total,
    scraping_errors_total,
    ocr_items_total,
    ocr_duration_seconds,
    active_workers,
    track_duration,
    track_time,
)

__all__ = [
    "metrics_bp",
    "registry",
    "http_requests_total",
    "http_request_duration_seconds",
    "pipeline_runs_total",
    "pipeline_run_duration_seconds",
    "scraping_items_total",
    "scraping_errors_total",
    "ocr_items_total",
    "ocr_duration_seconds",
    "active_workers",
    "track_duration",
    "track_time",
]
