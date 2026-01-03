"""Intelligent bandwidth unit detection and conversion.

Provides robust conversion between Kbps, Mbps, and Gbps based on:
1. Explicit unit suffix (k, M, G, Kbps, Mbps, Gbps)
2. Value magnitude heuristics
3. CACTI-specific patterns

Conversion Logic:
- Values with 'k' suffix or ending in Kbps → Kbps
- Values with 'M' suffix or ending in Mbps → Mbps
- Values with 'G' suffix or ending in Gbps → Gbps
- Plain numbers: Heuristics based on typical CACTI ranges:
  - < 1 → likely already Mbps (small links)
  - 1-999 → could be Kbps or Mbps (ambiguous)
  - 1000-999999 → likely Kbps
  - >= 1000000 → likely bps, convert to Mbps
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple, Any

logger = logging.getLogger(__name__)


class BandwidthUnit(Enum):
    """Bandwidth unit types."""
    BPS = "bps"
    KBPS = "Kbps"
    MBPS = "Mbps"
    GBPS = "Gbps"
    UNKNOWN = "unknown"


@dataclass
class ParsedValue:
    """Parsed bandwidth value with detected unit."""
    original: str
    value: float
    unit: BandwidthUnit
    confidence: float  # 0.0 to 1.0


# Conversion factors to base unit (bps)
UNIT_TO_BPS = {
    BandwidthUnit.BPS: 1,
    BandwidthUnit.KBPS: 1000,
    BandwidthUnit.MBPS: 1000000,
    BandwidthUnit.GBPS: 1000000000,
}


def parse_bandwidth_value(raw_value: Any) -> ParsedValue:
    """
    Parse a raw bandwidth value and detect its unit.
    
    Args:
        raw_value: String or number value (e.g., "150k", "1.5M", "1500", "2.5 Mbps")
    
    Returns:
        ParsedValue with detected unit and confidence score
    """
    if raw_value is None or raw_value == '' or raw_value == 'N/A':
        return ParsedValue(str(raw_value), 0.0, BandwidthUnit.UNKNOWN, 0.0)
    
    raw_str = str(raw_value).strip()
    original = raw_str
    
    # Pattern 1: Explicit unit suffix (highest confidence)
    # Matches: 150Kbps, 1.5Mbps, 2Gbps, 150 Kbps, etc.
    explicit_pattern = r'^([\d.]+)\s*(kbps|mbps|gbps|bps)\s*$'
    match = re.match(explicit_pattern, raw_str, re.IGNORECASE)
    if match:
        value = float(match.group(1))
        unit_str = match.group(2).lower()
        unit_map = {'bps': BandwidthUnit.BPS, 'kbps': BandwidthUnit.KBPS, 
                    'mbps': BandwidthUnit.MBPS, 'gbps': BandwidthUnit.GBPS}
        return ParsedValue(original, value, unit_map[unit_str], 1.0)
    
    # Pattern 2: Short suffix (k, M, G)
    # Matches: 150k, 1.5M, 2G
    short_pattern = r'^([\d.]+)\s*([kKmMgG])\s*$'
    match = re.match(short_pattern, raw_str)
    if match:
        value = float(match.group(1))
        suffix = match.group(2).upper()
        unit_map = {'K': BandwidthUnit.KBPS, 'M': BandwidthUnit.MBPS, 'G': BandwidthUnit.GBPS}
        return ParsedValue(original, value, unit_map[suffix], 0.95)
    
    # Pattern 3: Plain number - use heuristics
    number_pattern = r'^([\d.]+)\s*$'
    match = re.match(number_pattern, raw_str)
    if match:
        value = float(match.group(1))
        unit, confidence = _detect_unit_by_magnitude(value)
        return ParsedValue(original, value, unit, confidence)
    
    # Fallback: try to extract number from mixed content
    number_match = re.search(r'([\d.]+)', raw_str)
    if number_match:
        value = float(number_match.group(1))
        # Check for suffix after number
        after_number = raw_str[number_match.end():].strip().lower()
        if after_number.startswith('k'):
            return ParsedValue(original, value, BandwidthUnit.KBPS, 0.85)
        elif after_number.startswith('m'):
            return ParsedValue(original, value, BandwidthUnit.MBPS, 0.85)
        elif after_number.startswith('g'):
            return ParsedValue(original, value, BandwidthUnit.GBPS, 0.85)
        
        unit, confidence = _detect_unit_by_magnitude(value)
        return ParsedValue(original, value, unit, confidence * 0.8)
    
    return ParsedValue(original, 0.0, BandwidthUnit.UNKNOWN, 0.0)


def _detect_unit_by_magnitude(value: float) -> Tuple[BandwidthUnit, float]:
    """
    Detect bandwidth unit based on value magnitude.
    
    CACTI typically reports values in Kbps for most interfaces.
    Heuristic rules:
    - Very small (<1): Likely Mbps (e.g., 0.5 Mbps link)
    - Small (1-99): Ambiguous, assume Mbps (common for smaller links)
    - Medium (100-999): Likely Kbps (typical CACTI output)
    - Large (1000-999999): Almost certainly Kbps
    - Very large (>=1M): Might be bps, convert
    """
    if value < 1:
        return BandwidthUnit.MBPS, 0.7  # Small fractions are usually Mbps
    elif value < 100:
        return BandwidthUnit.MBPS, 0.6  # Ambiguous, could be either
    elif value < 1000:
        return BandwidthUnit.KBPS, 0.75  # Most likely Kbps range
    elif value < 1000000:
        return BandwidthUnit.KBPS, 0.9  # Almost certainly Kbps
    else:
        return BandwidthUnit.BPS, 0.8  # Very large, probably bps


def convert_to_unit(parsed: ParsedValue, target_unit: BandwidthUnit) -> float:
    """
    Convert parsed value to target unit.
    
    Args:
        parsed: ParsedValue with detected unit
        target_unit: Target unit for conversion
    
    Returns:
        Converted value in target unit
    """
    if parsed.unit == BandwidthUnit.UNKNOWN or target_unit == BandwidthUnit.UNKNOWN:
        return parsed.value
    
    # Convert to bps first, then to target
    bps_value = parsed.value * UNIT_TO_BPS[parsed.unit]
    result = bps_value / UNIT_TO_BPS[target_unit]
    
    return result


def convert_value_to_mbps(raw_value: Any) -> float:
    """
    Convert any bandwidth value to Mbps.
    
    Args:
        raw_value: Any bandwidth value (string or number)
    
    Returns:
        Value in Mbps (float)
    """
    parsed = parse_bandwidth_value(raw_value)
    if parsed.unit == BandwidthUnit.UNKNOWN:
        return 0.0
    return convert_to_unit(parsed, BandwidthUnit.MBPS)


def convert_value_to_kbps(raw_value: Any) -> float:
    """
    Convert any bandwidth value to Kbps.
    
    Args:
        raw_value: Any bandwidth value (string or number)
    
    Returns:
        Value in Kbps (float)
    """
    parsed = parse_bandwidth_value(raw_value)
    if parsed.unit == BandwidthUnit.UNKNOWN:
        return 0.0
    return convert_to_unit(parsed, BandwidthUnit.KBPS)


def format_bandwidth(value: float, unit: BandwidthUnit, precision: int = 2) -> str:
    """
    Format bandwidth value with unit suffix.
    
    Args:
        value: Numeric value
        unit: Unit for formatting
        precision: Decimal places
    
    Returns:
        Formatted string (e.g., "1.50 Mbps")
    """
    if value == 0:
        return "0"
    return f"{value:.{precision}f}"


# ==========================================================================
# Pandas Integration
# ==========================================================================
def convert_dataframe_to_mbps(df, columns: list[str] = None):
    """
    Convert specified columns in DataFrame to Mbps.
    
    Args:
        df: Pandas DataFrame
        columns: List of column names to convert. If None, auto-detect bandwidth columns.
    
    Returns:
        New DataFrame with converted values
    """
    import pandas as pd
    
    result = df.copy()
    
    # Auto-detect bandwidth columns if not specified
    if columns is None:
        columns = [col for col in df.columns if any(
            keyword in col.lower() for keyword in ['current', 'average', 'max', 'inbound', 'outbound']
        ) and not any(
            keyword in col.lower() for keyword in ['period', 'date', 'id', 'isp', 'vlan', 'service']
        )]
    
    for col in columns:
        if col in result.columns:
            result[col] = result[col].apply(convert_value_to_mbps)
    
    return result


def convert_dataframe_to_kbps(df, columns: list[str] = None):
    """
    Convert specified columns in DataFrame to Kbps.
    """
    import pandas as pd
    
    result = df.copy()
    
    if columns is None:
        columns = [col for col in df.columns if any(
            keyword in col.lower() for keyword in ['current', 'average', 'max', 'inbound', 'outbound']
        ) and not any(
            keyword in col.lower() for keyword in ['period', 'date', 'id', 'isp', 'vlan', 'service']
        )]
    
    for col in columns:
        if col in result.columns:
            result[col] = result[col].apply(convert_value_to_kbps)
    
    return result
