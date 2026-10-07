"""Summarize TV shows from the TVmaze public API into a JSON report.

Downloads one page of show records, groups and summarizes them, and
writes the result to summary.json.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

SOURCE_URL = "https://api.tvmaze.com/shows?page=0"
OUTPUT = Path("summary.json")
TIMEOUT_SECONDS = 10


class DownloadError(Exception):
    """Raised when the records cannot be downloaded or decoded."""


def fetch_records(url, timeout=TIMEOUT_SECONDS):
    """Download the records and return them as a list of Python objects.

    Raises DownloadError with a readable message if the request fails,
    the server answers with an error status, or the body is not a JSON list.
    """
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise DownloadError(
            f"the server did not respond within {timeout} seconds."
        ) from None
    except requests.exceptions.ConnectionError:
        raise DownloadError(
            "could not connect to the server. Check your internet connection."
        ) from None
    except requests.exceptions.HTTPError as err:
        raise DownloadError(
            f"the server returned HTTP {err.response.status_code}."
        ) from None
    except requests.exceptions.RequestException as err:
        raise DownloadError(f"the request failed ({type(err).__name__}).") from None

    try:
        data = response.json()
    except ValueError:
        raise DownloadError("the response was not valid JSON.") from None

    if not isinstance(data, list):
        raise DownloadError(
            f"expected a JSON list of shows but got a {type(data).__name__}."
        )
    return data


def clean_records(raw_records):
    """Keep only well-formed show records and drop repeated ids.

    A usable record is a dict with an integer "id". Returns a tuple
    (records, skipped) where skipped is how many entries were dropped.
    """
    seen_ids = set()
    records = []
    skipped = 0
    for item in raw_records:
        show_id = item.get("id") if isinstance(item, dict) else None
        if not isinstance(show_id, int) or show_id in seen_ids:
            skipped += 1
            continue
        seen_ids.add(show_id)
        records.append(item)
    return records, skipped


def main():
    """Download the shows and report how many usable records arrived."""
    print(f"Downloading shows from {SOURCE_URL} ...")
    try:
        raw_records = fetch_records(SOURCE_URL)
    except DownloadError as err:
        sys.exit(f"Download failed: {err}")

    records, skipped = clean_records(raw_records)
    print(f"Downloaded {len(raw_records)} entries, {len(records)} usable, {skipped} skipped.")


if __name__ == "__main__":
    main()
