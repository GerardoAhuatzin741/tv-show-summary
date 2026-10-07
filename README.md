# TV Show Summary

Downloads a page of TV show records from the TVmaze API and summarizes them: how many shows fall in each genre, the average rating per language, how many premiered in each decade, the top-rated shows, and how much of the data is missing. It turns a few hundred raw records into a short JSON report you can read in a minute.

## Data source

`https://api.tvmaze.com/shows?page=0`

Each record is one TV show: its name, language, genres, premiere date, rating, and the network or streaming service it airs on. Page 0 covers show ids 0 to 249; shows that were deleted from TVmaze leave gaps, so slightly fewer than 250 records come back. No account or API key is needed.

## Setup

    python -m venv .venv
    source .venv/bin/activate      # Windows: .venv\Scripts\activate
    pip install -r requirements.txt

## Run

    python records.py

The program writes `summary.json` in the current folder. If the download fails (no internet, timeout, server error), it prints a one-line message and exits without a traceback.

## Example output

<!-- TODO: replace this excerpt with the real values from your summary.json -->

```json
{
  "source_url": "https://api.tvmaze.com/shows?page=0",
  "records_processed": 0,
  "shows_per_genre": { "Drama": 0, "Comedy": 0 },
  "average_rating_by_language": {
    "English": { "average_rating": 0.0, "rated_shows": 0, "unrated_shows": 0 }
  },
  "data_quality": { "no_genres": 0, "no_rating": 0, "web_channel_only": 0 }
}
```

`shows_per_genre` shows which genres dominate the catalogue. `average_rating_by_language` shows how ratings compare across languages and, through `rated_shows`, how much each average can be trusted. `data_quality` shows how many records had each kind of gap.

## Data quirks

| Quirk | What the program does |
|---|---|
| A show can have several genres, or none. | `shows_per_genre` loops over each show's genres, so one show adds to every genre it lists. Shows with no genres are not filed under a made-up genre; they are counted in `data_quality.no_genres`. |
| The same genre could appear twice in one show's list, or as a blank string. | Genres are read into a set and blank strings are dropped, so a show counts at most once per genre. |
| Some shows have no rating (`rating.average` is `null`). | Unrated shows are never treated as 0. They are left out of the averages and counted in `unrated_shows` per language and in `data_quality.no_rating`. A language with no rated shows gets `"average_rating": null`. |
| Streaming shows have `network: null` and a `webChannel` instead (for example, Hemlock Grove airs on Netflix). | `get_channel_kind` checks both fields. `data_quality` reports shows that are web-only and shows that have neither. |
| `premiered` can be missing or not a full `YYYY-MM-DD` date. | `get_premiere_year` parses the date with `strptime` and returns `None` on failure; those shows are skipped by `shows_per_decade` and counted in `data_quality.no_valid_premiere_date`. |
| `language` can be missing. | Those shows are left out of the per-language averages and counted in `data_quality.no_language`. |
| Ids have gaps where shows were deleted. | Nothing breaks; the program never assumes ids are continuous. |
| A record could be malformed (not an object, no id) or repeated. | `clean_records` drops entries without an integer `id` and duplicate ids, and reports the count as `records_skipped`. |

## Design choices

- **list** holds the cleaned records and, per language, the ratings to be averaged. Order matters for the records (they come back in id order) and a list of ratings is all `sum()` and `len()` need.
- **dict** is used for every grouping (`genre -> count`, `decade -> count`, `language -> ratings`) because it maps a key straight to its running total in one lookup. The summary itself is a dict because it becomes a JSON object.
- **set** holds the ids already seen in `clean_records`, so checking for a duplicate is a constant-time lookup rather than a scan of the list. Each show's genres are also a set so a repeated genre cannot be counted twice. The set union `set(ratings) | set(unrated)` gathers every language that appeared, rated or not.
- **tuple** pairs each rating with its show name in `top_rated_shows`. The pair is fixed once made and sorts naturally by its first item. The `(kind, field name)` pairs in `get_channel_kind` are tuples for the same reason: fixed data that is only read.

Comprehensions build the genre set in `get_genres`, the per-language result in `average_rating_by_language` (dict comprehension), and the output list in `top_rated_shows`.

Aggregation functions only take records and return results; they never download, print or write. That keeps them easy to test with a few hand-made records and easy to move into a package next week.

## Known limitations

- Only page 0 is downloaded. Fetching more pages would mean looping over `?page=N` until the API returns 404.
- A single averaged rating per language can be misleading when only a few shows in that language are rated; `rated_shows` is reported so the reader can judge this.
- Genres are taken exactly as TVmaze labels them; similar genres (for example, "Science-Fiction" and "Supernatural") are not merged.
