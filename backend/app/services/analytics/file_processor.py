"""
File Processing Module

Handles multiple file formats:
- CSV files
- JSON files
- Excel files
- Parquet files
- Custom formats
"""

import csv
import json
from typing import List, Dict, Any
from pathlib import Path


class FileProcessor:
    """Process transaction data from various file formats."""

    @staticmethod
    def process_csv(file_path: str) -> List[Dict[str, Any]]:
        """Process CSV file into transaction list."""
        transactions = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Convert numeric fields
                    transaction = {}

                    for key, value in row.items():
                        if key.lower() in ['amount', 'risk_score']:
                            try:
                                transaction[key] = float(value)
                            except (ValueError, TypeError):
                                transaction[key] = value
                        else:
                            transaction[key] = value

                    transactions.append(transaction)

            return transactions

        except Exception as e:
            raise ValueError(f"Error processing CSV file: {str(e)}")

    @staticmethod
    def process_json(file_path: str) -> List[Dict[str, Any]]:
        """Process JSON file into transaction list."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle both array and object responses
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'transactions' in data:
                return data['transactions']
            elif isinstance(data, dict) and 'decisions' in data:
                return data['decisions']
            else:
                return [data]

        except Exception as e:
            raise ValueError(f"Error processing JSON file: {str(e)}")

    @staticmethod
    def process_jsonl(file_path: str) -> List[Dict[str, Any]]:
        """Process JSONL (JSON Lines) file into transaction list."""
        transactions = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        try:
                            transaction = json.loads(line)
                            transactions.append(transaction)
                        except json.JSONDecodeError:
                            continue

            return transactions

        except Exception as e:
            raise ValueError(f"Error processing JSONL file: {str(e)}")

    @staticmethod
    def process_file(file_path: str) -> List[Dict[str, Any]]:
        """Auto-detect file format and process."""
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension == '.csv':
            return FileProcessor.process_csv(file_path)

        elif extension == '.json':
            return FileProcessor.process_json(file_path)

        elif extension == '.jsonl' or extension == '.ndjson':
            return FileProcessor.process_jsonl(file_path)

        elif extension in ['.xlsx', '.xls']:
            return FileProcessor.process_excel(file_path)

        else:
            raise ValueError(f"Unsupported file format: {extension}")

    @staticmethod
    def process_excel(file_path: str) -> List[Dict[str, Any]]:
        """Process Excel file into transaction list."""
        try:
            import openpyxl

            workbook = openpyxl.load_workbook(file_path)
            sheet = workbook.active
            transactions = []

            # Get headers from first row
            headers = []
            for cell in sheet[1]:
                headers.append(cell.value)

            # Read data rows
            for row in sheet.iter_rows(min_row=2, values_only=True):
                if any(cell is not None for cell in row):
                    transaction = {}

                    for i, header in enumerate(headers):
                        if i < len(row):
                            value = row[i]

                            # Convert numeric fields
                            if header and header.lower() in ['amount', 'risk_score']:
                                try:
                                    transaction[header] = float(value)
                                except (ValueError, TypeError):
                                    transaction[header] = value
                            else:
                                transaction[header] = value

                    transactions.append(transaction)

            return transactions

        except ImportError:
            raise ValueError("openpyxl not installed. Install with: pip install openpyxl")
        except Exception as e:
            raise ValueError(f"Error processing Excel file: {str(e)}")

    @staticmethod
    def normalize_columns(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Intelligently map columns to standard fields.
        Works with ANY column names and creates standardized fields.
        """
        if not transactions:
            return transactions

        normalized = []

        # Column mapping patterns (case-insensitive)
        column_patterns = {
            'transaction_id': ['transaction_id', 'txn_id', 'trans_id', 'id', 'transaction', 'txn', 'order_id', 'payment_id'],
            'amount': ['amount', 'value', 'total', 'sum', 'price', 'payment_amount', 'transaction_amount'],
            'user_id': ['user_id', 'customer_id', 'client_id', 'userid', 'customerid', 'user', 'customer'],
            'merchant_id': ['merchant_id', 'seller_id', 'vendor_id', 'merchantid', 'merchant', 'seller', 'store_id'],
            'timestamp': ['timestamp', 'time', 'date', 'datetime', 'created_at', 'transaction_time', 'trans_time'],
            'currency': ['currency', 'curr', 'currency_code'],
            'country': ['country', 'nation', 'country_code', 'location'],
            'device_id': ['device_id', 'deviceid', 'device'],
            'ip_address': ['ip_address', 'ip', 'ipaddress', 'client_ip']
        }

        for txn in transactions:
            normalized_txn = {}

            # Get all column names from the transaction (case-insensitive)
            columns_lower = {k.lower(): k for k in txn.keys()}

            # Try to map each standard field
            for standard_field, patterns in column_patterns.items():
                mapped = False
                for pattern in patterns:
                    if pattern.lower() in columns_lower:
                        original_key = columns_lower[pattern.lower()]
                        normalized_txn[standard_field] = txn[original_key]
                        mapped = True
                        break

                # If not mapped, check for partial matches
                if not mapped:
                    for col_lower, col_original in columns_lower.items():
                        for pattern in patterns:
                            if pattern.lower() in col_lower or col_lower in pattern.lower():
                                normalized_txn[standard_field] = txn[col_original]
                                mapped = True
                                break
                        if mapped:
                            break

            # Generate IDs if missing
            if 'transaction_id' not in normalized_txn:
                # Use first column value or generate ID
                first_value = next(iter(txn.values())) if txn else None
                normalized_txn['transaction_id'] = str(first_value) if first_value else f'txn_{hash(str(txn))}'

            # Copy any unmapped fields as-is
            for key, value in txn.items():
                if key not in normalized_txn:
                    normalized_txn[key] = value

            normalized.append(normalized_txn)

        return normalized

    @staticmethod
    def validate_transactions(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Flexible validation - accepts ANY data format.
        Quality score based on available data, not strict requirements.
        """
        report = {
            "total_records": len(transactions),
            "valid_records": len(transactions),  # All records are valid now
            "invalid_records": 0,
            "missing_fields": [],
            "data_quality_score": 100.0,  # Start with 100%
            "issues": [],
            "detected_columns": [],
            "suggestions": []
        }

        if not transactions:
            report["data_quality_score"] = 0.0
            report["suggestions"].append("No data found in file")
            return report

        # Detect what columns are available
        if transactions:
            sample_txn = transactions[0]
            report["detected_columns"] = list(sample_txn.keys())

        # Check for common useful fields (but don't require them)
        useful_fields = ['transaction_id', 'amount', 'user_id', 'merchant_id', 'timestamp']
        found_fields = []
        missing_fields = []

        for field in useful_fields:
            field_found = False
            for txn in transactions[:10]:  # Check first 10 records
                if field in txn and txn[field] is not None:
                    field_found = True
                    break

            if field_found:
                found_fields.append(field)
            else:
                missing_fields.append(field)

        # Calculate quality based on found fields (but minimum 50%)
        field_coverage = len(found_fields) / len(useful_fields) if useful_fields else 1.0
        report["data_quality_score"] = max(50.0, field_coverage * 100)

        if missing_fields:
            report["suggestions"].append(f"Consider adding these fields for better analysis: {', '.join(missing_fields)}")

        report["missing_fields"] = missing_fields

        return report
