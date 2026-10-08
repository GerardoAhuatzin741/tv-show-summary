## Example output

An excerpt of `summary.json` from a run on page 0:

```json
{
  "source_url": "https://api.tvmaze.com/shows?page=0",
  "records_downloaded": 240,
  "records_processed": 240,
  "records_skipped": 0,
  "shows_per_genre": { "Drama": 154, "Comedy": 66, "Crime": 57, "Action": 55 },
  "average_rating_by_language": {
    "English": { "average_rating": 7.58, "rated_shows": 232, "unrated_shows": 4 },
    "Japanese": { "average_rating": 7.88, "rated_shows": 4, "unrated_shows": 0 }
  },
  "shows_per_decade": { "1980s": 2, "1990s": 8, "2000s": 51, "2010s": 179 },
  "top_rated_shows": [
    { "name": "Breaking Bad", "rating": 9.2 },
    { "name": "Firefly", "rating": 9.0 }
  ],
  "data_quality": { "no_genres": 5, "no_rating": 4, "web_channel_only": 11 }
}
```

Drama is by far the most common genre, appearing in 154 of the 240 shows. Most shows on this page premiered in the 2010s. The English average of 7.58 rests on 232 rated shows, while the Japanese average of 7.88 rests on only 4, so it says much less. `data_quality` shows the gaps the program handled: 5 shows with no genres, 4 with no rating, and 11 that stream on a web channel instead of a TV network.
