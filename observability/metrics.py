"""Prometheus metrics endpoint for observability.

Provides application metrics in Prometheus format for monitoring.

Usage:
    from observability.metrics import metrics_bp, track_request
    app.register_blueprint(metrics_bp)
"""

from __future__ import annotations

import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from functools import wraps
from threading import Lock
from typing import Callable, Iterator

from flask import Blueprint, Response

metrics_bp = Blueprint('metrics', __name__)


@dataclass
class Counter:
    """Simple counter metric."""
    name: str
    help: str
    labels: dict = field(default_factory=dict)
    _value: float = 0.0
    _lock: Lock = field(default_factory=Lock)
    
    def inc(self, value: float = 1.0) -> None:
        with self._lock:
            self._value += value
    
    @property
    def value(self) -> float:
        return self._value


@dataclass
class Gauge:
    """Simple gauge metric."""
    name: str
    help: str
    labels: dict = field(default_factory=dict)
    _value: float = 0.0
    _lock: Lock = field(default_factory=Lock)
    
    def set(self, value: float) -> None:
        with self._lock:
            self._value = value
    
    def inc(self, value: float = 1.0) -> None:
        with self._lock:
            self._value += value
    
    def dec(self, value: float = 1.0) -> None:
        with self._lock:
            self._value -= value
    
    @property
    def value(self) -> float:
        return self._value


@dataclass
class Histogram:
    """Simple histogram metric with buckets."""
    name: str
    help: str
    buckets: tuple = (0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf'))
    labels: dict = field(default_factory=dict)
    _sum: float = 0.0
    _count: int = 0
    _bucket_counts: dict = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock)
    
    def __post_init__(self):
        self._bucket_counts = {b: 0 for b in self.buckets}
    
    def observe(self, value: float) -> None:
        with self._lock:
            self._sum += value
            self._count += 1
            for bucket in self.buckets:
                if value <= bucket:
                    self._bucket_counts[bucket] += 1
    
    @property
    def sum(self) -> float:
        return self._sum
    
    @property
    def count(self) -> int:
        return self._count


class MetricsRegistry:
    """Registry for all metrics."""
    
    def __init__(self):
        self._metrics: dict[str, Counter | Gauge | Histogram] = {}
        self._lock = Lock()
    
    def counter(self, name: str, help: str, labels: dict = None) -> Counter:
        key = self._make_key(name, labels)
        if key not in self._metrics:
            with self._lock:
                if key not in self._metrics:
                    self._metrics[key] = Counter(name, help, labels or {})
        return self._metrics[key]
    
    def gauge(self, name: str, help: str, labels: dict = None) -> Gauge:
        key = self._make_key(name, labels)
        if key not in self._metrics:
            with self._lock:
                if key not in self._metrics:
                    self._metrics[key] = Gauge(name, help, labels or {})
        return self._metrics[key]
    
    def histogram(self, name: str, help: str, labels: dict = None, 
                  buckets: tuple = None) -> Histogram:
        key = self._make_key(name, labels)
        if key not in self._metrics:
            with self._lock:
                if key not in self._metrics:
                    self._metrics[key] = Histogram(
                        name, help, 
                        buckets=buckets or Histogram.buckets,
                        labels=labels or {}
                    )
        return self._metrics[key]
    
    def _make_key(self, name: str, labels: dict = None) -> str:
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name
    
    def format_prometheus(self) -> str:
        """Format all metrics in Prometheus text format."""
        lines = []
        seen_help = set()
        
        for key, metric in sorted(self._metrics.items()):
            name = metric.name
            
            # Add HELP and TYPE only once per metric name
            if name not in seen_help:
                lines.append(f"# HELP {name} {metric.help}")
                if isinstance(metric, Counter):
                    lines.append(f"# TYPE {name} counter")
                elif isinstance(metric, Gauge):
                    lines.append(f"# TYPE {name} gauge")
                elif isinstance(metric, Histogram):
                    lines.append(f"# TYPE {name} histogram")
                seen_help.add(name)
            
            # Format labels
            labels_str = ""
            if metric.labels:
                labels_str = "{" + ",".join(f'{k}="{v}"' for k, v in metric.labels.items()) + "}"
            
            # Format value
            if isinstance(metric, (Counter, Gauge)):
                lines.append(f"{name}{labels_str} {metric.value}")
            elif isinstance(metric, Histogram):
                for bucket, count in sorted(metric._bucket_counts.items()):
                    bucket_labels = labels_str.rstrip("}") if labels_str else "{"
                    if bucket_labels != "{":
                        bucket_labels += ","
                    bucket_labels += f'le="{bucket if bucket != float("inf") else "+Inf"}"' + "}"
                    lines.append(f"{name}_bucket{bucket_labels} {count}")
                lines.append(f"{name}_sum{labels_str} {metric.sum}")
                lines.append(f"{name}_count{labels_str} {metric.count}")
        
        return "\n".join(lines) + "\n"


# Global registry
registry = MetricsRegistry()

# ==========================================================================
# Pre-defined Metrics
# ==========================================================================
# Request metrics
http_requests_total = registry.counter(
    "http_requests_total",
    "Total number of HTTP requests"
)

http_request_duration_seconds = registry.histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds"
)

# Pipeline metrics
pipeline_runs_total = registry.counter(
    "pipeline_runs_total",
    "Total number of pipeline runs"
)

pipeline_run_duration_seconds = registry.histogram(
    "pipeline_run_duration_seconds",
    "Pipeline run duration in seconds",
    buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600, float('inf'))
)

scraping_items_total = registry.counter(
    "scraping_items_total",
    "Total number of items scraped"
)

scraping_errors_total = registry.counter(
    "scraping_errors_total",
    "Total number of scraping errors"
)

ocr_items_total = registry.counter(
    "ocr_items_total",
    "Total number of items processed by OCR"
)

ocr_duration_seconds = registry.histogram(
    "ocr_duration_seconds",
    "OCR processing duration per item in seconds"
)

# System metrics
active_workers = registry.gauge(
    "active_workers",
    "Number of active worker threads"
)

app_info = registry.gauge(
    "app_info",
    "Application information",
    labels={"version": "1.0.0", "env": "production"}
)
app_info.set(1)


# ==========================================================================
# Decorators
# ==========================================================================
def track_duration(histogram: Histogram) -> Callable:
    """Decorator to track function duration."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                histogram.observe(time.time() - start)
        return wrapper
    return decorator


@contextmanager
def track_time(histogram: Histogram) -> Iterator[None]:
    """Context manager to track duration."""
    start = time.time()
    try:
        yield
    finally:
        histogram.observe(time.time() - start)


# ==========================================================================
# Flask Endpoint
# ==========================================================================
@metrics_bp.route('/metrics')
def metrics_endpoint():
    """Prometheus metrics endpoint."""
    return Response(
        registry.format_prometheus(),
        mimetype='text/plain; version=0.0.4; charset=utf-8'
    )
