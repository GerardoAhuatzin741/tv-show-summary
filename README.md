# TV Show Summary

This program downloads a list of TV shows from the free TVmaze website and turns it into a short report. The report says how many shows belong to each genre, the average rating for each language, how many shows started in each decade, which shows have the best ratings, and how much information is missing from the data. This is useful because it turns 240 raw records into a summary you can read in a minute.

## Data source

The data comes from https://api.tvmaze.com/shows?page=0. Each record is one TV show, with its name, language, genres, premiere date, rating, and the TV network or streaming service where it airs. The page returned 240 shows on the last run. It needs no account or API key.

## Setup

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt

## Run

    python records.py

The program creates a file called summary.json with the report. If there is no internet connection or the server fails, it shows a short error message and stops, instead of crashing.

## Example output

    "records_processed": 240,
    "shows_per_genre": { "Drama": 154, "Comedy": 66, "Crime": 57 },
    "English": { "average_rating": 7.58, "rated_shows": 232, "unrated_shows": 4 }

Drama is the most common genre, appearing in 154 of the 240 shows, and most shows premiered in the 2010s. The average rating for English shows is 7.58, based on 232 rated shows. The best rated show is Breaking Bad with 9.2. The report also shows that 5 shows have no genres, 4 have no rating, and 11 are only on streaming services.

## Data quirks

Some shows have several genres and some have none. The program counts a show once in every genre it has, and shows with no genres are counted separately instead of being given a fake genre.

Some shows have no rating. The program does not count them as zero, because that would lower the average unfairly. They are left out of the average and counted separately as unrated.

Some shows are on streaming services instead of TV networks, so their network field is empty. The program checks both fields and reports how many shows are streaming only.

Dates and languages could be missing or written wrong. Page 0 had none of these problems, but the program still checks for them, so it will not crash on other data.

Some records could be broken, repeated, or missing an id. The program removes them and reports how many were skipped.

## Design choices

I used a list to keep the shows in order and to collect the ratings for each language before calculating the average.

I used a dictionary for every count, such as shows per genre or shows per decade, because it connects each name to its total and is fast to look up. The final report is also a dictionary, because it is saved as JSON.

I used a set to remember which show ids were already seen, so repeated shows are detected quickly. The genres of each show are also stored in a set, so the same genre cannot be counted twice for one show.

I used tuples to pair each rating with its show name when finding the best rated shows, because the pair never changes and is easy to sort.

The program is split into small functions, each doing one job. The functions that calculate results do not download, print or save anything, which makes them easier to test and to reuse next week.

## Known limitations

The program only downloads the first page of shows, not the whole TVmaze catalogue. The average rating for a language with very few rated shows, like Japanese with only 4, is not very reliable. Genres are used exactly as TVmaze writes them, so similar genres are not combined.
