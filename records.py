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


# --- Field readers: each returns a clean value or None, never guesses ---

def get_genres(record):
    """Return the show's genres as a set of non-empty strings (may be empty)."""
    genres = record.get("genres")
    if not isinstance(genres, list):
        return set()
    return {g.strip() for g in genres if isinstance(g, str) and g.strip()}


def get_rating(record):
    """Return the show's average rating as a float, or None if it has none."""
    rating = record.get("rating")
    if not isinstance(rating, dict):
        return None
    value = rating.get("average")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def get_language(record):
    """Return the show's language, or None if missing or blank."""
    language = record.get("language")
    if isinstance(language, str) and language.strip():
        return language.strip()
    return None


def get_premiere_year(record):
    """Return the year the show premiered, or None if missing or malformed."""
    premiered = record.get("premiered")
    if not isinstance(premiered, str):
        return None
    try:
        return datetime.strptime(premiered, "%Y-%m-%d").year
    except ValueError:
        return None


def get_channel_kind(record):
    """Return "network", "web" or None depending on where the show airs."""
    for kind, key in (("network", "network"), ("web", "webChannel")):
        channel = record.get(key)
        if isinstance(channel, dict) and channel.get("name"):
            return kind
    return None


def get_name(record):
    """Return the show's name, falling back to its id if the name is missing."""
    name = record.get("name")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return f"Show #{record['id']}"


# --- Aggregations: records in, result out. No downloading, printing or writing ---

def shows_per_genre(records):
    """Count how many shows list each genre; a show counts once per genre.

    Shows with no genres are left out here and reported in data_quality.
    Returns a dict ordered from most to least common genre.
    """
    counts = {}
    for record in records:
        for genre in get_genres(record):
            counts[genre] = counts.get(genre, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def average_rating_by_language(records):
    """Average rating per language, using only shows that have a rating.

    Unrated shows are counted separately instead of being treated as zero,
    and a language with no rated shows gets an average of None.
    """
    ratings = {}
    unrated = {}
    for record in records:
        language = get_language(record)
        if language is None:
            continue
        rating = get_rating(record)
        if rating is None:
            unrated[language] = unrated.get(language, 0) + 1
        else:
            ratings.setdefault(language, []).append(rating)

    return {
        language: {
            "average_rating": (
                round(sum(ratings[language]) / len(ratings[language]), 2)
                if language in ratings else None
            ),
            "rated_shows": len(ratings.get(language, [])),
            "unrated_shows": unrated.get(language, 0),
        }
        for language in sorted(set(ratings) | set(unrated))
    }


def shows_per_decade(records):
    """Count shows by the decade they premiered, e.g. {"1990s": 12}.

    Shows with a missing or malformed premiere date are left out.
    """
    counts = {}
    for record in records:
        year = get_premiere_year(record)
        if year is None:
            continue
        decade = f"{year // 10 * 10}s"
        counts[decade] = counts.get(decade, 0) + 1
    return dict(sorted(counts.items()))


def top_rated_shows(records, limit=10):
    """Return the highest-rated shows as a list of {"name", "rating"} dicts.

    Ties are broken alphabetically so the output is stable between runs.
    """
    rated = []
    for record in records:
        rating = get_rating(record)
        if rating is not None:
            rated.append((rating, get_name(record)))
    rated.sort(key=lambda pair: (-pair[0], pair[1]))
    return [{"name": name, "rating": rating} for rating, name in rated[:limit]]


def data_quality(records):
    """Count the records with each kind of missing or malformed field."""
    channel_kinds = [get_channel_kind(record) for record in records]
    return {
        "no_genres": sum(1 for r in records if not get_genres(r)),
        "no_rating": sum(1 for r in records if get_rating(r) is None),
        "no_language": sum(1 for r in records if get_language(r) is None),
        "no_valid_premiere_date": sum(1 for r in records if get_premiere_year(r) is None),
        "web_channel_only": channel_kinds.count("web"),
        "no_network_or_web_channel": channel_kinds.count(None),
    }


def build_summary(records, source_url, records_downloaded, records_skipped):
    """Combine the aggregations into one dict ready to write."""
    return {
        "source_url": source_url,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "records_downloaded": records_downloaded,
        "records_processed": len(records),
        "records_skipped": records_skipped,
        "shows_per_genre": shows_per_genre(records),
        "average_rating_by_language": average_rating_by_language(records),
        "shows_per_decade": shows_per_decade(records),
        "top_rated_shows": top_rated_shows(records),
        "data_quality": data_quality(records),
    }


def write_summary(summary, path):
    """Write the summary to a JSON file."""
    path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main():
    """Download, summarize and save the shows, exiting cleanly on failure."""
    print(f"Downloading shows from {SOURCE_URL} ...")
    try:
        raw_records = fetch_records(SOURCE_URL)
    except DownloadError as err:
        sys.exit(f"Download failed: {err}")

    records, skipped = clean_records(raw_records)
    if not records:
        sys.exit("Download succeeded but contained no usable show records.")

    summary = build_summary(records, SOURCE_URL, len(raw_records), skipped)
    try:
        write_summary(summary, OUTPUT)
    except OSError as err:
        sys.exit(f"Could not write {OUTPUT}: {err.strerror}")

    print(f"Processed {len(records)} shows ({skipped} skipped). Summary written to {OUTPUT}.")


if __name__ == "__main__":
    main()
