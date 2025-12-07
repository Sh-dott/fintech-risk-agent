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
    def validate_transactions(transactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate transaction data quality."""
        report = {
            "total_records": len(transactions),
            "valid_records": 0,
            "invalid_records": 0,
            "missing_fields": [],
            "data_quality_score": 0.0,
            "issues": []
        }

        required_fields = [
            'transaction_id',
            'amount',
            'user_id',
            'merchant_id'
        ]

        valid_count = 0

        for i, txn in enumerate(transactions):
            missing = [f for f in required_fields if f not in txn or txn[f] is None]

            if not missing:
                valid_count += 1
            else:
                report["invalid_records"] += 1
                report["issues"].append({
                    "record": i,
                    "missing_fields": missing
                })

        report["valid_records"] = valid_count

        # Calculate quality score
        if len(transactions) > 0:
            report["data_quality_score"] = (valid_count / len(transactions)) * 100

        return report
