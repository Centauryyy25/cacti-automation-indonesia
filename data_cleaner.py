"""CSV utilities for converting Kbps values to Mbps.

Converts numeric values in the 100..999 range (assumed to be Kbps) to Mbps
by dividing by 1000. Non-numeric values or values outside the range are left
untouched. Intended for post-OCR CSV normalization.
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


def _convert_kbps_to_mbps(value: Any) -> Any:
    """Convert 3-digit Kbps values (100..999) into Mbps.

    Returns the original value if it's not a number or out of range.
    """
    try:
        if isinstance(value, (int, float)) and 100 <= value <= 999:
            return value / 1000.0
        return value
    except Exception:  # keep robust against unexpected cell types
        return value


def process_csv(input_file: str, output_file: str) -> None:
    """Load CSV, convert qualifying numeric cells from Kbps to Mbps, and save.

    - Reads numeric columns only
    - Applies 100..999 -> value/1000
    - Writes to `output_file`
    """
    logger.info("Loading CSV: %s", input_file)
    df = pd.read_csv(input_file)

    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    for col in numeric_cols:
        df[col] = df[col].apply(_convert_kbps_to_mbps)

    df.to_csv(output_file, index=False)
    logger.info("Saved cleaned CSV: %s", output_file)


__all__ = ["process_csv"]

