import requests
from bs4 import BeautifulSoup
import datetime
import json
import os
import time
from fake_useragent import UserAgent
from tqdm import tqdm
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("scraper.log"),
    logging.StreamHandler()
])

class NewsScraper:
    def __init__(self):
        self.ua = UserAgent()
        self.articles_buffer = []
        self.articles_count = 0
        self.file_index = 1
        self.output_dir = "scraped_data"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def get_headers(self):
        return {
            'User-Agent': self.ua.random
        }

    def save_article(self, article):
        self.articles_buffer.append(article)
        self.articles_count += 1

        if len(self.articles_buffer) >= 500:
            self.flush_buffer()

    def flush_buffer(self):
        if not self.articles_buffer:
            return

        filename = os.path.join(self.output_dir, f"news_data_{self.file_index}.json")
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.articles_buffer, f, ensure_ascii=False, indent=4)
            logging.info(f"Saved {len(self.articles_buffer)} articles to {filename}")
            self.articles_buffer = []
            self.file_index += 1
        except Exception as e:
            logging.error(f"Failed to save data to {filename}: {e}")

    def get_date_range(self, start_date, end_date):
        for n in range(int((end_date - start_date).days) + 1):
            yield start_date + datetime.timedelta(n)

    def scrape_indian_express(self, start_date, end_date):
        logging.info("Starting Indian Express Scraper...")
        for date in self.get_date_range(start_date, end_date):
            base_url = f"https://indianexpress.com/archive/{date.strftime('%Y/%m/%d')}/"
            current_url = base_url
            page_num = 1

            while current_url:
                logging.info(f"Scraping Indian Express Archive: {current_url}")
                try:
                    response = requests.get(current_url, headers=self.get_headers(), timeout=15)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')

                        links = soup.find_all('a')
                        article_links = []
                        for link in links:
                            href = link.get('href')
                            if href and 'indianexpress.com/article/' in href:
                                title = link.get_text().strip()
                                if title and title not in ["Next »", "1", "2", "...", "My Express", "Premium", "UPSC", "Subscribe", "Sign In"]:
                                    article_links.append({'url': href, 'heading': title})

                        unique_links = {v['url']: v for v in article_links}.values()

                        if not unique_links:
                            break

                        for item in tqdm(unique_links, desc=f"IE {date.strftime('%Y-%m-%d')} Pg{page_num}", leave=False):
                            content = self.fetch_indian_express_content(item['url'])
                            if content:
                                article_data = {
                                    'source': 'The Indian Express',
                                    'date': date.strftime('%Y-%m-%d'),
                                    'url': item['url'],
                                    'heading': item['heading'],
                                    'content': content
                                }
                                self.save_article(article_data)
                            time.sleep(0.5)

                        # Find Next Page
                        next_link = soup.find('a', string='Next »')
                        if next_link:
                            current_url = next_link.get('href')
                            page_num += 1
                        else:
                            current_url = None
                    else:
                        logging.warning(f"Failed to fetch archive page {current_url}: {response.status_code}")
                        current_url = None
                except Exception as e:
                    logging.error(f"Error scraping {current_url}: {e}")
                    current_url = None

    def fetch_indian_express_content(self, url):
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Try standard content containers
                content_div = soup.find('div', class_='ev-meter-content')
                if not content_div:
                    content_div = soup.find('div', class_='story-details')
                if not content_div:
                    content_div = soup.find('div', id='full-details')

                if content_div:
                    paragraphs = content_div.find_all('p', recursive=False)
                    text_content = "\n".join([p.get_text().strip() for p in paragraphs])
                    return text_content
                else:
                    # Fallback: look for all paragraphs in the main body
                    # This is risky as it might catch sidebar content
                    return None
            else:
                logging.warning(f"Failed to fetch article {url}: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error fetching content from {url}: {e}")
            return None

    def scrape_the_hindu(self, start_date, end_date):
        logging.info("Starting The Hindu Scraper...")
        for date in self.get_date_range(start_date, end_date):
            # URL format: https://www.thehindu.com/archive/web/YYYY/MM/DD/
            url = f"https://www.thehindu.com/archive/web/{date.strftime('%Y/%m/%d')}/"
            logging.info(f"Scraping The Hindu Archive: {url}")

            try:
                # The Hindu has strong protection. This might fail.
                response = requests.get(url, headers=self.get_headers(), timeout=15)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

                    # Extract links
                    # The archive page usually has a list of links
                    # <ul class="archive-list"> or similar

                    # We will look for links that look like articles
                    links = soup.find_all('a')
                    article_links = []
                    for link in links:
                        href = link.get('href')
                        if href and '.ece' in href and 'thehindu.com' in href:
                             title = link.get_text().strip()
                             if title:
                                 article_links.append({'url': href, 'heading': title})

                    unique_links = {v['url']: v for v in article_links}.values()

                    for item in tqdm(unique_links, desc=f"TH {date.strftime('%Y-%m-%d')}", leave=False):
                        content = self.fetch_the_hindu_content(item['url'])
                        if content:
                            article_data = {
                                'source': 'The Hindu',
                                'date': date.strftime('%Y-%m-%d'),
                                'url': item['url'],
                                'heading': item['heading'],
                                'content': content
                            }
                            self.save_article(article_data)
                        time.sleep(1) # Be more polite with The Hindu
                elif response.status_code == 403:
                    logging.error(f"Access Forbidden (403) for {url}. Cloudflare protection likely active.")
                    # We might skip the rest of The Hindu if we get blocked
                    # But for now, let's just log and continue to next date
                else:
                     logging.warning(f"Failed to fetch archive page {url}: {response.status_code}")

            except Exception as e:
                logging.error(f"Error scraping {url}: {e}")

    def fetch_the_hindu_content(self, url):
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

                # Content is usually in div with id 'content-body-14269002-XXXX' usually starts with content-body
                # or class 'article-body'

                # Check for div with id starting with content-body
                content_div = None
                for div in soup.find_all('div'):
                    if div.get('id') and div.get('id').startswith('content-body-'):
                        content_div = div
                        break

                if not content_div:
                     content_div = soup.find('div', class_='articlebodycontent')

                if content_div:
                    paragraphs = content_div.find_all('p')
                    text_content = "\n".join([p.get_text().strip() for p in paragraphs])
                    return text_content
                return None
            else:
                logging.warning(f"Failed to fetch article {url}: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error fetching content from {url}: {e}")
            return None

    def run(self):
        print("Welcome to the News Scraper")
        try:
            start_str = input("Enter start date (YYYY-MM-DD): ")
            end_str = input("Enter end date (YYYY-MM-DD): ")

            start_date = datetime.datetime.strptime(start_str, "%Y-%m-%d").date()
            end_date = datetime.datetime.strptime(end_str, "%Y-%m-%d").date()

            if start_date > end_date:
                print("Start date must be before end date.")
                return

            self.scrape_indian_express(start_date, end_date)
            self.scrape_the_hindu(start_date, end_date)

            self.flush_buffer()
            print("Scraping completed.")

        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")
        except KeyboardInterrupt:
            print("\nScraping interrupted. Saving progress...")
            self.flush_buffer()

if __name__ == "__main__":
    scraper = NewsScraper()
    scraper.run()
