import time
import json
import os
import datetime
import logging
from bs4 import BeautifulSoup
from tqdm import tqdm
from curl_cffi import requests

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[
    logging.FileHandler("scraper.log"),
    logging.StreamHandler()
])

class NewsScraper:
    def __init__(self):
        self.output_dir = "scraped_data"
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Initialize session
        self.session = requests.Session(impersonate="chrome")
        self.manual_cookies_set = False

    def get_headers(self):
        # We rely on curl_cffi impersonate, but can add others if needed
        # Return empty dict as headers are managed by session
        return {}

    def make_request(self, url, retries=3):
        try:
            # We don't use self.get_headers() here because session maintains headers
            # However, if we needed to add specific headers per request, we could.
            response = self.session.get(url, timeout=30)

            if response.status_code == 403 and "thehindu.com" in url:
                logging.warning("Got 403 Forbidden. Cloudflare protection active.")

                # Check if we should prompt user
                if not self.manual_cookies_set:
                     print("\n" + "!"*50)
                     print("CLOUDFLARE BLOCK DETECTED")
                     print("The script cannot bypass the Cloudflare protection automatically.")
                     print("Please open the URL in your browser: ", url)
                     print("Then copy the 'Cookie' header from your browser's developer tools (Network tab).")
                     print("!"*50 + "\n")

                     cookie_input = input("Enter Cookie string (or press Enter to skip/abort): ").strip()
                     ua_input = input("Enter User-Agent string (optional, press Enter to use default): ").strip()

                     if cookie_input:
                         # Update session headers
                         self.session.headers["Cookie"] = cookie_input
                         if ua_input:
                             self.session.headers["User-Agent"] = ua_input

                         self.manual_cookies_set = True
                         logging.info("Updated session with manual cookies. Retrying...")
                         return self.make_request(url, retries=retries-1)
                     else:
                         logging.error("No cookies provided. Skipping this URL.")
                         return None
                elif retries > 0:
                     # If cookies are already set but we still get 403, maybe wait and retry?
                     # Or maybe cookies expired.
                     logging.warning(f"403 Forbidden with manual cookies. Retrying {retries} more times...")
                     time.sleep(2)
                     return self.make_request(url, retries=retries-1)
                else:
                    logging.error("403 Forbidden even with manual cookies. They might be expired or invalid.")
                    return None

            return response

        except Exception as e:
            logging.error(f"Request failed for {url}: {e}")
            return None

    def save_article(self, article):
        date_obj = datetime.datetime.strptime(article['date'], '%Y-%m-%d')
        year = date_obj.strftime('%Y')
        month = date_obj.strftime('%m')
        source_slug = article['source'].lower().replace(" ", "_").replace("the_", "")

        target_dir = os.path.join(self.output_dir, year, month)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        filename = os.path.join(target_dir, f"{source_slug}.json")

        # Load existing data if file exists
        data = []
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content:
                        data = json.loads(content)
            except json.JSONDecodeError:
                logging.warning(f"Could not decode JSON from {filename}. Starting fresh.")
                data = []

        data.append(article)

        # Write back
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"Failed to save article to {filename}: {e}")

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
                    response = self.make_request(current_url)
                    if response and response.status_code == 200:
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
                        logging.warning(f"Failed to fetch archive page {current_url} or blocked")
                        current_url = None
                except Exception as e:
                    logging.error(f"Error scraping {current_url}: {e}")
                    current_url = None

    def fetch_indian_express_content(self, url):
        try:
            response = self.make_request(url)
            if response and response.status_code == 200:
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
                    return None
            else:
                logging.warning(f"Failed to fetch article {url}")
                return None
        except Exception as e:
            logging.error(f"Error fetching content from {url}: {e}")
            return None

    def scrape_the_hindu(self, start_date, end_date):
        logging.info("Starting The Hindu Scraper...")
        for date in self.get_date_range(start_date, end_date):
            url = f"https://www.thehindu.com/archive/web/{date.strftime('%Y/%m/%d')}/"
            logging.info(f"Scraping The Hindu Archive: {url}")

            try:
                response = self.make_request(url)

                if response and response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')

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
                        time.sleep(1)
                elif response and response.status_code == 403:
                    logging.error(f"Access Forbidden (403) for {url}. Cloudflare protection active/failed bypass.")
                else:
                    code = response.status_code if response else "Unknown"
                    logging.warning(f"Failed to fetch archive page {url}: {code}")

            except Exception as e:
                logging.error(f"Error scraping {url}: {e}")

    def fetch_the_hindu_content(self, url):
        try:
            response = self.make_request(url)
            if response and response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')

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
                code = response.status_code if response else "Unknown"
                logging.warning(f"Failed to fetch article {url}: {code}")
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

            print("\nSelect News Source:")
            print("1. The Indian Express")
            print("2. The Hindu")
            print("3. Both")
            choice = input("Enter your choice (1/2/3): ")

            if choice == '1':
                self.scrape_indian_express(start_date, end_date)
            elif choice == '2':
                self.scrape_the_hindu(start_date, end_date)
            elif choice == '3':
                self.scrape_indian_express(start_date, end_date)
                self.scrape_the_hindu(start_date, end_date)
            else:
                print("Invalid choice. Exiting.")
                return

            print("Scraping completed.")

        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")
        except KeyboardInterrupt:
            print("\nScraping interrupted.")

if __name__ == "__main__":
    scraper = NewsScraper()
    scraper.run()
