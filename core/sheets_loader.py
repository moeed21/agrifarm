"""
AgriBazaar — sheets_loader.py
==============================
Optional data loader for Google Sheets or remote CSV sources.
Falls back gracefully when credentials or network are unavailable.

This module is used when data needs to be refreshed from a remote
Google Sheet instead of the local clean_crop_prices.csv file.
"""
import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Optional Google Sheets credentials from environment
SHEETS_CREDENTIALS = os.environ.get('GOOGLE_SHEETS_CREDENTIALS', '')
SHEETS_SPREADSHEET_ID = os.environ.get('SHEETS_SPREADSHEET_ID', '')
SHEETS_RANGE = os.environ.get('SHEETS_RANGE', 'Sheet1!A:Z')


def is_configured() -> bool:
    """Return True if Google Sheets credentials are configured."""
    return bool(SHEETS_CREDENTIALS and SHEETS_SPREADSHEET_ID)


def load_from_sheets(output_path: Path = None) -> bool:
    """
    Download data from Google Sheets and save as CSV to output_path.
    Returns True on success, False on failure.
    """
    if not is_configured():
        logger.info("Google Sheets not configured — skipping remote load.")
        return False

    try:
        import json
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        creds_dict = json.loads(SHEETS_CREDENTIALS)
        creds = Credentials.from_service_account_info(
            creds_dict,
            scopes=['https://www.googleapis.com/auth/spreadsheets.readonly']
        )
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()
        result = sheet.values().get(
            spreadsheetId=SHEETS_SPREADSHEET_ID,
            range=SHEETS_RANGE
        ).execute()

        values = result.get('values', [])
        if not values:
            logger.warning("No data returned from Google Sheets.")
            return False

        import csv
        if output_path is None:
            from django.conf import settings
            output_path = settings.CSV_PATH

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(values)

        logger.info(f"✅ Loaded {len(values)-1} rows from Google Sheets → {output_path}")
        return True

    except ImportError:
        logger.warning("google-auth / googleapiclient not installed. Skipping Sheets load.")
        return False
    except Exception as e:
        logger.error(f"Failed to load from Google Sheets: {e}")
        return False


def load_from_remote_csv(url: str, output_path: Path = None) -> bool:
    """
    Download a CSV from a public URL and save locally.
    Returns True on success, False on failure.
    """
    try:
        import requests
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()

        if output_path is None:
            from django.conf import settings
            output_path = settings.CSV_PATH

        output_path.write_bytes(resp.content)
        logger.info(f"✅ Downloaded remote CSV ({len(resp.content):,} bytes) → {output_path}")
        return True

    except Exception as e:
        logger.error(f"Failed to download remote CSV from {url}: {e}")
        return False


def refresh_data_if_stale(max_age_hours: int = 24) -> bool:
    """
    Re-download data if the local CSV is older than max_age_hours.
    Returns True if data was refreshed, False otherwise.
    """
    try:
        from django.conf import settings
        csv_path = settings.CSV_PATH
        if csv_path.exists():
            import time
            age_hours = (time.time() - csv_path.stat().st_mtime) / 3600
            if age_hours < max_age_hours:
                logger.debug(f"CSV is {age_hours:.1f}h old — no refresh needed.")
                return False
    except Exception:
        pass

    return load_from_sheets()
