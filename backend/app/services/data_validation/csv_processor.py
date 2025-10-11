# services/data_validation/csv_processor.py
"""
CSV Processing Module for the Adaptive Exam Timetabling System.
Handles CSV file parsing, validation, and transformation with comprehensive error handling.
"""

import csv
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from pathlib import Path
from datetime import datetime, date, time
import re
import chardet
from decimal import Decimal, InvalidOperation
import uuid
import pandas as pd

logger = logging.getLogger(__name__)


class CSVValidationError(Exception):
    """Custom exception for CSV validation errors."""

    pass


class CSVProcessor:
    """Handles CSV file processing with validation and transformation."""

    def __init__(self):
        self.required_columns: Dict[str, List[str]] = {}
        self.column_mappings: Dict[str, Dict[str, str]] = {}
        self.data_transformers: Dict[str, Dict[str, Any]] = {}
        self.validators: Dict[str, Dict[str, Any]] = {}

    def register_schema(self, entity_type: str, schema: Dict[str, Any]) -> None:
        """
        Register a schema for a specific entity type.
        """
        self.required_columns[entity_type] = schema.get("required_columns", [])
        self.column_mappings[entity_type] = schema.get("column_mappings", {})
        self.data_transformers[entity_type] = schema.get("transformers", {})
        self.validators[entity_type] = schema.get("validators", {})
        logger.info(f"Registered schema for {entity_type}")

    def detect_entity_type(self, file_path: Path, header: List[str]) -> Optional[str]:
        """
        Detects the entity type based on filename or column structure.
        Handles temporary filenames with UUID prefixes.
        """
        # 1. Try to match by filename
        file_name_stem = file_path.stem.lower()

        parts = file_name_stem.split("_")
        # Check if the first part could be a UUID and there are other parts
        if len(parts) > 1:
            try:
                # A quick check to see if the first part resembles a UUID segment
                uuid.UUID(parts[0])
                # Reconstruct the original entity name from the remaining parts
                possible_entity_type = "_".join(parts[1:])
                if possible_entity_type in self.required_columns:
                    logger.info(
                        f"Detected entity type '{possible_entity_type}' from prefixed filename."
                    )
                    return possible_entity_type
            except ValueError:
                # The first part is not a UUID, proceed to normal matching
                pass

        # Fallback for direct filename match (e.g., 'faculties.csv')
        if file_name_stem in self.required_columns:
            logger.info(f"Detected entity type '{file_name_stem}' from filename.")
            return file_name_stem

        # 2. If filename match fails, try to match by structure (column headers)
        best_match = None
        highest_score = 0

        for entity_type, required_cols in self.required_columns.items():
            if not required_cols:
                continue

            matched_cols = sum(
                1
                for req_col in required_cols
                if self._find_mapped_column(req_col, entity_type, header) is not None
            )
            score = matched_cols / len(required_cols)

            if score > highest_score:
                highest_score = score
                best_match = entity_type

        # Require a high confidence match (e.g., > 70%) to avoid false positives
        if highest_score > 0.7:
            logger.info(
                f"Detected entity type '{best_match}' from column structure with {highest_score:.2f} score."
            )
            return best_match

        logger.warning(f"Could not detect entity type for file: {file_path.name}")
        return None

    def detect_encoding(self, file_path: Union[str, Path]) -> str:
        """
        Detect the encoding of a CSV file.
        """
        try:
            with open(file_path, "rb") as file:
                raw_data = file.read()
                result = chardet.detect(raw_data)
                encoding = result.get("encoding") or "utf-8"
                encoding = str(encoding)
                confidence = result.get("confidence", 0)
                logger.info(
                    f"Detected encoding: {encoding} (confidence: {confidence:.2f})"
                )
                return encoding
        except Exception as e:
            logger.warning(f"Failed to detect encoding: {e}. Using utf-8")
            return "utf-8"

    def validate_csv_structure(
        self,
        file_path: Union[str, Path],
        entity_type: str,
        encoding: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate the basic structure of a CSV file.
        """
        validation_result: Dict[str, Any] = {
            "is_valid": False,
            "errors": [],
            "warnings": [],
            "row_count": 0,
            "column_count": 0,
            "columns": [],
            "encoding": encoding,
        }

        try:
            path_obj = Path(file_path)
            if not path_obj.exists():
                validation_result["errors"].append(f"File not found: {file_path}")
                return validation_result

            # Detect encoding if not provided
            if encoding is None:
                encoding = self.detect_encoding(file_path)
                validation_result["encoding"] = encoding

            try:
                df_headers = pd.read_csv(file_path, encoding=encoding, nrows=0)
                columns = list(df_headers.columns)
                validation_result["columns"] = columns
                validation_result["column_count"] = len(columns)
                df_full = pd.read_csv(file_path, encoding=encoding)
                validation_result["row_count"] = len(df_full)
                logger.info(
                    f"CSV structure: {validation_result['row_count']} rows, {validation_result['column_count']} columns"
                )
            except pd.errors.EmptyDataError:
                validation_result["errors"].append("CSV file is empty")
                return validation_result
            except pd.errors.ParserError as e:
                validation_result["errors"].append(f"CSV parsing error: {e}")
                return validation_result

            # Validate required columns
            missing_cols = []
            required_cols = self.required_columns.get(entity_type, [])
            for col in required_cols:
                if col not in columns:
                    mapped_col = self._find_mapped_column(col, entity_type, columns)
                    if mapped_col is None:
                        missing_cols.append(col)
            if missing_cols:
                validation_result["errors"].append(
                    f"Missing required columns: {missing_cols}"
                )
            else:
                validation_result["is_valid"] = True

            if entity_type not in self.required_columns:
                validation_result["warnings"].append(
                    f"No schema registered for entity type: {entity_type}"
                )
                validation_result["is_valid"] = True

            if validation_result["row_count"] == 0:
                validation_result["warnings"].append("CSV file contains only headers")
            if validation_result["column_count"] == 0:
                validation_result["errors"].append("CSV file has no columns")

        except Exception as e:
            validation_result["errors"].append(
                f"Unexpected error during validation: {e}"
            )
            logger.error(f"CSV validation error: {e}")

        return validation_result

    def _find_mapped_column(
        self, required_col: str, entity_type: str, available_cols: List[str]
    ) -> Optional[str]:
        """
        Find a mapped column name for a required column.
        """
        mappings = self.column_mappings.get(entity_type, {})

        # Direct mapping
        if required_col in mappings:
            mapped_col = mappings[required_col]
            if mapped_col in available_cols:
                return mapped_col
        # Reverse mapping
        for csv_col, mapped_col in mappings.items():
            if mapped_col == required_col and csv_col in available_cols:
                return csv_col
        # Fuzzy matching
        required_normalized = self._normalize_column_name(required_col)
        for col in available_cols:
            if required_normalized == self._normalize_column_name(col):
                return col
        return None

    def _normalize_column_name(self, col_name: str) -> str:
        """Normalize column name for fuzzy matching."""
        return re.sub(r"[_\s\-]+", "", col_name.lower().strip())

    def process_csv_file(
        self,
        file_path: Union[str, Path],
        entity_type: str,
        encoding: Optional[str] = None,
        chunk_size: int = 1000,
        validate_data: bool = True,
    ) -> Dict[str, Any]:
        """
        Process a CSV file with validation and transformation.
        """
        result: Dict[str, Any] = {
            "success": False,
            "total_rows": 0,
            "processed_rows": 0,
            "errors": [],
            "warnings": [],
            "data": [],
            "validation_errors": [],
            "skipped_rows": [],
        }
        try:
            # First validate structure
            structure_validation = self.validate_csv_structure(
                file_path, entity_type, encoding
            )
            if not structure_validation["is_valid"]:
                result["errors"].extend(structure_validation["errors"])
                return result

            result["warnings"].extend(structure_validation["warnings"])
            result["total_rows"] = structure_validation["row_count"]
            encoding = structure_validation["encoding"]

            chunk_iter = pd.read_csv(
                file_path,
                encoding=encoding,
                chunksize=chunk_size,
                dtype=str,
                keep_default_na=False,
            )

            row_offset = 0
            for chunk_df in chunk_iter:
                chunk_result = self._process_chunk(
                    chunk_df, entity_type, row_offset, validate_data
                )
                result["processed_rows"] += chunk_result["processed_rows"]
                result["data"].extend(chunk_result["data"])
                result["validation_errors"].extend(chunk_result["validation_errors"])
                result["skipped_rows"].extend(chunk_result["skipped_rows"])
                row_offset += len(chunk_df)
                logger.info(
                    f"Processed chunk: {len(chunk_df)} rows, total processed: {result['processed_rows']}"
                )

            result["success"] = True
            logger.info(
                f"CSV processing complete: {result['processed_rows']}/{result['total_rows']} rows processed"
            )
            if result["validation_errors"]:
                logger.warning(
                    f"Found {len(result['validation_errors'])} validation errors"
                )

        except Exception as e:
            error_msg = f"Failed to process CSV file: {e}"
            result["errors"].append(error_msg)
            logger.error(error_msg)

        return result

    def _process_chunk(
        self,
        chunk_df: pd.DataFrame,
        entity_type: str,
        row_offset: int,
        validate_data: bool,
    ) -> Dict[str, Any]:
        """
        Process a chunk of CSV data.
        """
        result: Dict[str, Any] = {
            "processed_rows": 0,
            "data": [],
            "validation_errors": [],
            "skipped_rows": [],
        }
        mapped_df = self._apply_column_mappings(chunk_df, entity_type)
        # enumerate chunk from zero
        for local_idx, (_index_label, row) in enumerate(mapped_df.iterrows()):
            row_number = row_offset + local_idx + 2  # +2 for header
            try:
                transformed_row = self._transform_row_data(row.to_dict(), entity_type)
                if validate_data:
                    validation_result = self._validate_row_data(
                        transformed_row, entity_type, row_number
                    )
                    if validation_result["errors"]:
                        result["validation_errors"].extend(validation_result["errors"])
                        if validation_result["is_fatal"]:
                            result["skipped_rows"].append(
                                {
                                    "row_number": row_number,
                                    "data": row.to_dict(),
                                    "errors": validation_result["errors"],
                                }
                            )
                            continue
                transformed_row["_metadata"] = {
                    "row_number": row_number,
                    "entity_type": entity_type,
                    "processed_at": datetime.utcnow().isoformat(),
                }
                result["data"].append(transformed_row)
                result["processed_rows"] += 1
            except Exception as e:
                error_msg = f"Error processing row {row_number}: {e}"
                result["validation_errors"].append(
                    {
                        "row_number": row_number,
                        "field": None,
                        "error": error_msg,
                        "is_fatal": True,
                    }
                )
                result["skipped_rows"].append(
                    {
                        "row_number": row_number,
                        "data": row.to_dict(),
                        "errors": [error_msg],
                    }
                )

        return result

    def _apply_column_mappings(
        self, df: pd.DataFrame, entity_type: str
    ) -> pd.DataFrame:
        """Apply column mappings to DataFrame."""
        if entity_type not in self.column_mappings:
            return df
        mappings = self.column_mappings[entity_type]
        rename_dict = {}
        for csv_col, db_col in mappings.items():
            if csv_col in df.columns:
                rename_dict[csv_col] = db_col
        return df.rename(columns=rename_dict)

    def _transform_row_data(
        self, row_data: Dict[str, Any], entity_type: str
    ) -> Dict[str, Any]:
        """Transform row data using registered transformers."""
        transformed: Dict[str, Any] = {}
        transformers = self.data_transformers.get(entity_type, {})
        for field, value in row_data.items():
            if field in transformers:
                transformer = transformers[field]
                try:
                    transformed[field] = transformer(value)
                except Exception as e:
                    logger.warning(f"Transformation failed for {field}: {e}")
                    transformed[field] = value
            else:
                transformed[field] = self._default_transform(value)
        return transformed

    def _default_transform(self, value: Any) -> Any:
        """Apply default transformations to a value."""
        if pd.isna(value) or value == "":
            return None
        if isinstance(value, str):
            value = value.strip()
            if value == "":
                return None
            if value.lower() in ("true", "1", "yes", "y"):
                return True
            elif value.lower() in ("false", "0", "no", "n"):
                return False
        return value

    def _validate_row_data(
        self, row_data: Dict[str, Any], entity_type: str, row_number: int
    ) -> Dict[str, Any]:
        """Validate a row of data."""
        validation_result: Dict[str, Any] = {
            "errors": [],
            "warnings": [],
            "is_fatal": False,
        }
        validators = self.validators.get(entity_type, {})
        for field, validator in validators.items():
            if field in row_data:
                try:
                    result = validator(row_data[field], row_data)
                    if not result.get("is_valid", True):
                        error_info = {
                            "row_number": row_number,
                            "field": field,
                            "value": row_data[field],
                            "error": result.get("error", "Validation failed"),
                            "is_fatal": result.get("is_fatal", False),
                        }
                        validation_result["errors"].append(error_info)
                        if result.get("is_fatal", False):
                            validation_result["is_fatal"] = True
                except Exception as e:
                    validation_result["errors"].append(
                        {
                            "row_number": row_number,
                            "field": field,
                            "value": row_data[field],
                            "error": f"Validation error: {e}",
                            "is_fatal": False,
                        }
                    )
        return validation_result


# Data transformation functions
def transform_date(value: Any) -> Optional[date]:
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        date_formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"]
        for fmt in date_formats:
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    raise ValueError(f"Cannot convert '{value}' to date")


def transform_time(value: Any) -> Optional[time]:
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, str):
        time_formats = ["%H:%M:%S", "%H:%M", "%I:%M %p", "%I:%M:%S %p"]
        for fmt in time_formats:
            try:
                return datetime.strptime(value.strip(), fmt).time()
            except ValueError:
                continue
    raise ValueError(f"Cannot convert '{value}' to time")


def transform_integer(value: Any) -> Optional[int]:
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value.strip().replace(",", "")))
        except ValueError:
            pass
    raise ValueError(f"Cannot convert '{value}' to integer")


def transform_decimal(value: Any) -> Optional[Decimal]:
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return Decimal(value.strip().replace(",", ""))
        except InvalidOperation:
            pass
    raise ValueError(f"Cannot convert '{value}' to decimal")


def transform_boolean(value: Any) -> Optional[bool]:
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        value_lower = value.strip().lower()
        if value_lower in ("true", "1", "yes", "y", "on"):
            return True
        elif value_lower in ("false", "0", "no", "n", "off"):
            return False
    if isinstance(value, (int, float)):
        return bool(value)
    raise ValueError(f"Cannot convert '{value}' to boolean")


def transform_uuid(value: Any) -> Optional[uuid.UUID]:
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value.strip())
        except ValueError:
            pass
    raise ValueError(f"Cannot convert '{value}' to UUID")


def transform_string_to_array(value: Any) -> Optional[List[str]]:
    """Splits a comma-separated string into a list of strings."""
    if pd.isna(value) or value == "":
        return None
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        # Split by comma, strip whitespace from each item, and filter out empty strings
        return [item.strip() for item in value.split(",") if item.strip()]
    raise ValueError(f"Cannot convert '{value}' to a list of strings")


# Validation functions
def validate_required(value: Any, row_data: Dict[str, Any]) -> Dict[str, Any]:
    is_valid = value is not None and value != ""
    return {
        "is_valid": is_valid,
        "error": "Field is required" if not is_valid else None,
        "is_fatal": True,
    }


def validate_email(value: Any, row_data: Dict[str, Any]) -> Dict[str, Any]:
    if not value:
        return {"is_valid": True}
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    is_valid = bool(re.match(email_pattern, str(value)))
    return {
        "is_valid": is_valid,
        "error": "Invalid email format" if not is_valid else None,
        "is_fatal": False,
    }


def validate_unique(value: Any, row_data: Dict[str, Any]) -> Dict[str, Any]:
    # Implement uniqueness via database outside this function
    return {"is_valid": True}


__all__ = [
    "CSVProcessor",
    "CSVValidationError",
    "transform_date",
    "transform_time",
    "transform_integer",
    "transform_decimal",
    "transform_boolean",
    "transform_uuid",
    "transform_string_to_array",
    "validate_required",
    "validate_email",
    "validate_unique",
]
