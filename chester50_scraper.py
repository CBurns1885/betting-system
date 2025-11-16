"""
Chester 50 Ultramarathon Scraper
Scrapes information about the Chester 50 ultramarathon run by GB Ultras
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import os

class Chester50Scraper:
    def __init__(self, output_dir="scraped_data"):
        self.output_dir = output_dir
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        os.makedirs(output_dir, exist_ok=True)

        # GB Ultras and Chester 50 specific URLs
        self.sources = {
            'gb_ultras_main': 'https://www.gbultras.com/',
            'gb_ultras_chester': 'https://www.gbultras.com/chester50',
            'gb_ultras_races': 'https://www.gbultras.com/races',
            'chester_50_info': 'https://www.gbultras.com/chester50/info',
        }

    def scrape_page(self, url):
        """Scrape a single page and return BeautifulSoup object"""
        try:
            print(f"Scraping: {url}")
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return None

    def extract_race_info(self, soup, url):
        """Extract detailed race information"""
        race_info = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'title': '',
            'description': '',
            'date': '',
            'distance': '',
            'location': '',
            'elevation': '',
            'entry_fee': '',
            'cutoff_time': '',
            'aid_stations': [],
            'course_description': '',
            'full_content': ''
        }

        # Extract title
        title = soup.find('h1')
        if title:
            race_info['title'] = title.get_text(strip=True)

        # Extract meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            race_info['description'] = meta_desc.get('content')

        # Look for race details in various formats
        # Common patterns in race websites
        detail_keywords = {
            'date': ['date:', 'when:', 'race date'],
            'distance': ['distance:', 'miles:', 'km:'],
            'location': ['location:', 'where:', 'start:', 'venue:'],
            'elevation': ['elevation:', 'climbing:', 'ascent:', 'vertical:'],
            'entry_fee': ['entry fee:', 'cost:', 'price:', 'registration:'],
            'cutoff': ['cutoff:', 'time limit:', 'cut-off:']
        }

        # Search for race details in text
        text_content = soup.get_text()
        for key, keywords in detail_keywords.items():
            for keyword in keywords:
                if keyword in text_content.lower():
                    # Try to extract the value after the keyword
                    idx = text_content.lower().find(keyword)
                    if idx != -1:
                        snippet = text_content[idx:idx+200]
                        lines = snippet.split('\n')
                        if lines:
                            race_info[key] = lines[0].strip()
                        break

        # Extract tables (often contain race information)
        tables = soup.find_all('table')
        race_info['tables'] = []
        for table in tables:
            table_data = []
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                row_data = [cell.get_text(strip=True) for cell in cells]
                if row_data:
                    table_data.append(row_data)
            if table_data:
                race_info['tables'].append(table_data)

        # Extract all links
        links = []
        for link in soup.find_all('a', href=True):
            links.append({
                'text': link.get_text(strip=True),
                'href': link['href']
            })
        race_info['links'] = links

        # Get main content
        main_content = soup.find(['article', 'main', 'div'], class_=lambda x: x and 'content' in str(x).lower())
        if main_content:
            race_info['full_content'] = main_content.get_text(separator='\n', strip=True)
        else:
            # Fall back to body content
            body = soup.find('body')
            if body:
                race_info['full_content'] = body.get_text(separator='\n', strip=True)[:10000]

        return race_info

    def scrape_chester50(self):
        """Scrape all Chester 50 related information"""
        chester_data = {
            'event_name': 'Chester 50 Ultramarathon',
            'organizer': 'GB Ultras',
            'scraped_at': datetime.now().isoformat(),
            'pages': []
        }

        print("Scraping Chester 50 Ultramarathon information from GB Ultras...")

        for source_name, url in self.sources.items():
            print(f"\nScraping {source_name}...")
            soup = self.scrape_page(url)

            if soup:
                race_info = self.extract_race_info(soup, url)
                race_info['source_name'] = source_name
                chester_data['pages'].append(race_info)
                time.sleep(2)  # Be respectful with request rate

        return chester_data

    def search_for_chester50_resources(self):
        """Generate search URLs for Chester 50 related content"""
        search_queries = [
            "Chester 50 ultramarathon GB Ultras",
            "Chester 50 race report",
            "Chester 50 training plan",
            "Chester 50 course profile",
            "Chester 50 ultramarathon review",
            "GB Ultras Chester 50 elevation",
            "Chester 50 ultra pacing strategy"
        ]

        search_urls = {
            'google': [f"https://www.google.com/search?q={q.replace(' ', '+')}" for q in search_queries],
            'youtube': [f"https://www.youtube.com/results?search_query={q.replace(' ', '+')}" for q in search_queries],
            'strava': ["https://www.strava.com/search#?text=Chester%2050"]
        }

        return search_urls

    def save_results(self, data):
        """Save scraped Chester 50 data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save as JSON
        json_file = os.path.join(self.output_dir, f"chester50_data_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\nSaved Chester 50 data to {json_file}")

        # Save search URLs
        search_urls = self.search_for_chester50_resources()
        urls_file = os.path.join(self.output_dir, "chester50_search_urls.txt")
        with open(urls_file, 'w') as f:
            f.write("Chester 50 Search URLs\n")
            f.write("=" * 60 + "\n\n")
            for platform, urls in search_urls.items():
                f.write(f"\n{platform.upper()}:\n")
                for url in urls:
                    f.write(f"  {url}\n")
        print(f"Saved search URLs to {urls_file}")

        # Create a summary report
        summary_file = os.path.join(self.output_dir, f"chester50_summary_{timestamp}.txt")
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("CHESTER 50 ULTRAMARATHON - SCRAPING SUMMARY\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"Event: {data['event_name']}\n")
            f.write(f"Organizer: {data['organizer']}\n")
            f.write(f"Scraped at: {data['scraped_at']}\n")
            f.write(f"\nPages scraped: {len(data['pages'])}\n\n")

            for page in data['pages']:
                f.write(f"\n{'-' * 60}\n")
                f.write(f"Source: {page.get('source_name', 'Unknown')}\n")
                f.write(f"URL: {page['url']}\n")
                if page.get('title'):
                    f.write(f"Title: {page['title']}\n")
                if page.get('description'):
                    f.write(f"Description: {page['description']}\n")
                f.write(f"Links found: {len(page.get('links', []))}\n")
                f.write(f"Tables found: {len(page.get('tables', []))}\n")

        print(f"Saved summary to {summary_file}")

def main():
    scraper = Chester50Scraper()
    chester_data = scraper.scrape_chester50()
    scraper.save_results(chester_data)

    print("\n" + "=" * 60)
    print("Chester 50 scraping complete!")
    print(f"Pages scraped: {len(chester_data['pages'])}")
    print("=" * 60)

if __name__ == "__main__":
    main()
