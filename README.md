# News Scraper

This is a Python script to scrape news articles from "The Indian Express" and "The Hindu" archives.
Note: "The Hindu" scraping is currently limited by Cloudflare protection (403 Forbidden). The code includes logic to scrape it, but it may fail in environments without advanced anti-bot measures.

## Requirements

*   Python 3.x
*   `requests`
*   `beautifulsoup4`
*   `fake-useragent`
*   `tqdm`

## Installation

1.  Clone the repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

Run the script:

```bash
python news_scraper.py
```

Follow the prompts to enter the start and end dates (format: YYYY-MM-DD).

The script will:
1.  Iterate through each day in the date range.
2.  Fetch the archive page for "The Indian Express".
3.  Extract article links.
4.  Fetch and store the content of each article.
5.  Attempt the same for "The Hindu" (may fail due to protection).
6.  Save the data to JSON files in the `scraped_data` directory, with a maximum of 500 articles per file.

## Output Structure

The output JSON files (`news_data_1.json`, `news_data_2.json`, etc.) contain a list of article objects:

```json
[
    {
        "source": "The Indian Express",
        "date": "2024-01-01",
        "url": "https://indianexpress.com/article/...",
        "heading": "Article Heading",
        "content": "Full article content..."
    },
    ...
]
```
