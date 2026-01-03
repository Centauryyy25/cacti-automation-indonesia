"""Cleaning package: CSV post-processing utilities.

Provides:
- unit_converter: Intelligent bandwidth unit detection and conversion
- csv_generator: Generate 3 CSV variants (original, Mbps, Kbps)
"""

from cleaning.unit_converter import (
    BandwidthUnit,
    ParsedValue,
    parse_bandwidth_value,
    convert_to_unit,
    convert_value_to_mbps,
    convert_value_to_kbps,
    convert_dataframe_to_mbps,
    convert_dataframe_to_kbps,
)

from cleaning.csv_generator import (
    generate_all_csv_variants,
    process_ocr_output_to_csv,
    process_csv,
    BANDWIDTH_COLUMNS,
)

__all__ = [
    # Unit converter
    'BandwidthUnit',
    'ParsedValue',
    'parse_bandwidth_value',
    'convert_to_unit',
    'convert_value_to_mbps',
    'convert_value_to_kbps',
    'convert_dataframe_to_mbps',
    'convert_dataframe_to_kbps',
    # CSV generator
    'generate_all_csv_variants',
    'process_ocr_output_to_csv',
    'process_csv',
    'BANDWIDTH_COLUMNS',
]
