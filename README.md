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

Follow the prompts to:
1.  Enter the start and end dates (format: YYYY-MM-DD).
2.  Select which news source to scrape (The Indian Express, The Hindu, or Both).

The script will:
1.  Iterate through each day in the date range.
2.  Fetch the archive pages (handling pagination for The Indian Express).
3.  Extract article links.
4.  Fetch and store the content of each article.
5.  Save the data to JSON files organized by year and month.

## Output Structure

The scraped data is stored in the `scraped_data` directory with the following structure:

```
scraped_data/
├── 2024/
│   ├── 01/
│   │   ├── indian_express.json
│   │   └── the_hindu.json
│   └── 02/
│       ├── indian_express.json
│       └── ...
└── ...
```

Each JSON file contains a list of article objects:

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
