"""Utility script to convert restaurant JSON data to CSV format."""

import json
import csv
import pandas as pd
from pathlib import Path
import argparse
import os
import sys

# Add the project root to the Python path to find the config module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def flatten_json(nested_json, prefix=''):
    """
    Flatten a nested JSON structure into a flat dictionary.
    
    Args:
        nested_json: Nested JSON object
        prefix: Prefix for flattened keys
    
    Returns:
        Flattened dictionary
    """
    flat_dict = {}
    
    for key, value in nested_json.items():
        if isinstance(value, dict):
            flat_dict.update(flatten_json(value, f"{prefix}{key}_"))
        elif isinstance(value, list):
            # Handle lists by joining values with commas
            if all(isinstance(item, (str, int, float, bool)) for item in value):
                flat_dict[f"{prefix}{key}"] = ", ".join(str(item) for item in value)
            elif all(isinstance(item, dict) for item in value) and value:
                # For lists of dicts, we'll just take the first few items
                for i, item in enumerate(value[:3]):  # Limit to 3 items to avoid overly wide CSVs
                    flat_dict.update(flatten_json(item, f"{prefix}{key}_{i}_"))
        else:
            flat_dict[f"{prefix}{key}"] = value
            
    return flat_dict

def json_to_csv(input_file, output_file):
    """
    Convert JSON restaurant data to CSV format.
    
    Args:
        input_file: Path to JSON input file
        output_file: Path to CSV output file
    """
    logger.info(f"Converting {input_file} to CSV format...")
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Read JSON data
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        logger.info(f"Successfully loaded JSON data with {len(data)} restaurants")
    except Exception as e:
        logger.error(f"Error loading JSON data: {e}")
        return False
    
    if not data:
        logger.warning("No data found in JSON file")
        return False
    
    # Flatten JSON data
    flattened_data = [flatten_json(item) for item in data]
    
    # Convert to DataFrame for easier CSV handling
    df = pd.DataFrame(flattened_data)
    
    # Save to CSV
    try:
        df.to_csv(output_file, index=False)
        logger.info(f"Successfully saved CSV data to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving CSV data: {e}")
        return False

def main():
    """Main function to convert JSON to CSV."""
    # Define default paths relative to project root
    project_root = Path(__file__).resolve().parent.parent.parent
    default_input = project_root / "data" / "raw" / "restaurant_data.json"
    default_output = project_root / "data" / "processed" / "restaurant_data.csv"
    
    parser = argparse.ArgumentParser(description="Convert restaurant JSON data to CSV format")
    parser.add_argument("--input", default=str(default_input), 
                       help="Path to input JSON file")
    parser.add_argument("--output", default=str(default_output),
                       help="Path to output CSV file")
    
    args = parser.parse_args()
    
    input_file = Path(args.input)
    output_file = Path(args.output)
    
    if not input_file.exists():
        logger.error(f"Input file {input_file} does not exist")
        return
    
    success = json_to_csv(input_file, output_file)
    
    if success:
        logger.info(f"JSON to CSV conversion completed successfully. CSV saved at: {output_file}")
    else:
        logger.error("JSON to CSV conversion failed")

if __name__ == "__main__":
    main()