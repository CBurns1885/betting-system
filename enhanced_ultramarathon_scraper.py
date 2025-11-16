"""
Enhanced Ultramarathon Training Plan Scraper with anti-bot measures
Scrapes 50-mile ultramarathon training plans from various sources
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
from datetime import datetime
import time
from urllib.parse import urljoin, urlparse
import os
import random

class EnhancedUltramarathonScraper:
    def __init__(self, output_dir="scraped_data", use_selenium=False):
        self.output_dir = output_dir
        self.use_selenium = use_selenium

        # Rotate through multiple user agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]

        os.makedirs(output_dir, exist_ok=True)

        # Alternative and more accessible sources for ultramarathon training
        self.training_plan_sources = [
            {
                'name': 'Fellrnr',
                'url': 'http://fellrnr.com/wiki/Training_Plans',
                'search_terms': ['ultramarathon', '50 mile']
            },
            {
                'name': 'UltraLadies',
                'url': 'https://ultraladies.com/category/training/',
                'search_terms': ['training plan', '50 mile', 'ultra']
            },
            {
                'name': 'iRunFar',
                'url': 'https://www.irunfar.com/training',
                'search_terms': ['50 mile', 'ultramarathon', 'training']
            },
            {
                'name': 'Reddit Ultramarathon',
                'url': 'https://www.reddit.com/r/ultrarunning/search/?q=50%20mile%20training%20plan&restrict_sr=1',
                'search_terms': ['training plan']
            }
        ]

    def get_headers(self):
        """Get randomized headers to avoid bot detection"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }

    def scrape_page(self, url, retries=3):
        """Scrape a single page with retry logic"""
        for attempt in range(retries):
            try:
                headers = self.get_headers()
                print(f"Attempting to scrape {url} (attempt {attempt + 1}/{retries})")

                response = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
                response.raise_for_status()

                print(f"✓ Success! Status code: {response.status_code}")
                return BeautifulSoup(response.content, 'html.parser')

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 403:
                    print(f"  403 Forbidden (attempt {attempt + 1}/{retries})")
                    if attempt < retries - 1:
                        wait_time = (attempt + 1) * 2
                        print(f"  Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                else:
                    print(f"  HTTP Error {e.response.status_code}: {str(e)}")
                    break
            except Exception as e:
                print(f"  Error: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(2)

        print(f"✗ Failed to scrape {url} after {retries} attempts")
        return None

    def scrape_with_selenium(self, url):
        """Scrape using Selenium for JavaScript-heavy pages"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait

            print(f"Using Selenium for {url}")

            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument(f'user-agent={random.choice(self.user_agents)}')

            driver = webdriver.Chrome(options=options)
            driver.get(url)
            time.sleep(3)  # Wait for JavaScript to load

            html = driver.page_source
            driver.quit()

            return BeautifulSoup(html, 'html.parser')

        except ImportError:
            print("Selenium not installed. Install with: pip install selenium")
            return None
        except Exception as e:
            print(f"Selenium error: {str(e)}")
            return None

    def extract_training_plan(self, soup, source_name, url):
        """Extract training plan information from a page"""
        plan_data = {
            'source': source_name,
            'url': url,
            'title': '',
            'description': '',
            'duration': '',
            'content': '',
            'scraped_at': datetime.now().isoformat()
        }

        # Try to extract title
        title_tags = soup.find_all(['h1', 'h2', 'h3'])
        for tag in title_tags:
            if any(keyword in tag.text.lower() for keyword in ['50 mile', '50-mile', 'ultramarathon', 'ultra']):
                plan_data['title'] = tag.text.strip()
                break

        # If no specific title found, use first h1
        if not plan_data['title']:
            h1 = soup.find('h1')
            if h1:
                plan_data['title'] = h1.text.strip()

        # Extract main content
        content_areas = soup.find_all(['article', 'main', 'div'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['content', 'article', 'post', 'training', 'entry']
        ))

        if content_areas:
            plan_data['content'] = content_areas[0].get_text(separator='\n', strip=True)[:5000]

        # Try to extract description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            plan_data['description'] = meta_desc.get('content')

        # Extract any tables (training schedules are often in tables)
        tables = soup.find_all('table')
        if tables:
            plan_data['tables_found'] = len(tables)

        return plan_data

    def find_training_plan_links(self, soup, base_url):
        """Find links that likely contain training plans"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()

            # Check if link text or href contains relevant keywords
            if any(keyword in text or keyword in href.lower()
                   for keyword in ['50 mile', '50-mile', 'ultra', 'training plan', 'training schedule']):
                full_url = urljoin(base_url, href)
                links.append({
                    'url': full_url,
                    'text': link.get_text().strip()
                })

        return links

    def scrape_all_sources(self):
        """Scrape all configured sources for training plans"""
        all_plans = []
        all_links = []

        print("Starting enhanced ultramarathon training plan scraping...")
        print(f"Using {len(self.training_plan_sources)} sources\n")

        for source in self.training_plan_sources:
            print(f"\n{'='*70}")
            print(f"Scraping {source['name']}...")
            print(f"{'='*70}")

            soup = self.scrape_page(source['url'])

            if soup:
                # Find relevant links
                links = self.find_training_plan_links(soup, source['url'])
                all_links.extend([{**link, 'source': source['name']} for link in links])
                print(f"✓ Found {len(links)} potential training plan links")

                # Extract any training plans from the main page
                plan = self.extract_training_plan(soup, source['name'], source['url'])
                if plan['title'] or plan['content']:
                    all_plans.append(plan)
                    print(f"✓ Extracted training plan content")

                time.sleep(random.uniform(2, 4))  # Random delay to appear more human

        return all_plans, all_links

    def get_recommended_resources(self):
        """Get curated list of ultramarathon resources"""
        resources = {
            'Training Plan PDFs': [
                'Search "50 mile ultramarathon training plan PDF" on Google',
                'Check TrainingPeaks.com for downloadable plans',
                'Look for plans by coaches: Jason Koop, David Roche, Ian Sharman'
            ],
            'Books': [
                'Training Essentials for Ultrarunning by Jason Koop',
                'Relentless Forward Progress by Bryon Powell',
                'The Happy Runner by David and Megan Roche'
            ],
            'Online Communities': [
                'Reddit r/ultrarunning',
                'Facebook: Ultra Running Community',
                'Strava clubs focused on ultrarunning'
            ],
            'Coaching Services': [
                'TrainingPeaks coaches',
                'McMillan Running',
                'Jason Fitzgerald (Strength Running)'
            ]
        }
        return resources

    def save_results(self, plans, links):
        """Save scraped data to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save plans as JSON
        plans_file = os.path.join(self.output_dir, f"training_plans_{timestamp}.json")
        with open(plans_file, 'w', encoding='utf-8') as f:
            json.dump(plans, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved {len(plans)} training plans to {plans_file}")

        # Save links as CSV
        if links:
            links_file = os.path.join(self.output_dir, f"training_plan_links_{timestamp}.csv")
            with open(links_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['source', 'url', 'text'])
                writer.writeheader()
                writer.writerows(links)
            print(f"✓ Saved {len(links)} links to {links_file}")

        # Save comprehensive resource guide
        resources = self.get_recommended_resources()
        resource_file = os.path.join(self.output_dir, "ultramarathon_resources.txt")
        with open(resource_file, 'w') as f:
            f.write("50-MILE ULTRAMARATHON TRAINING RESOURCES\n")
            f.write("=" * 70 + "\n\n")

            for category, items in resources.items():
                f.write(f"\n{category}:\n")
                f.write("-" * 40 + "\n")
                for item in items:
                    f.write(f"  • {item}\n")

            f.write("\n\nGoogle Search URLs:\n")
            f.write("-" * 40 + "\n")
            search_queries = [
                "50 mile ultramarathon training plan",
                "50 mile ultra training schedule PDF",
                "free 50 mile ultramarathon training plan",
                "beginner 50 mile ultra training",
                "Jason Koop 50 mile training plan",
                "TrainingPeaks 50 mile plan"
            ]
            for query in search_queries:
                google_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
                f.write(f"  {google_url}\n")

        print(f"✓ Saved comprehensive resource guide to {resource_file}")

def main():
    scraper = EnhancedUltramarathonScraper()
    plans, links = scraper.scrape_all_sources()
    scraper.save_results(plans, links)

    print("\n" + "=" * 70)
    print("SCRAPING COMPLETE!")
    print("=" * 70)
    print(f"Total training plans extracted: {len(plans)}")
    print(f"Total links found: {len(links)}")
    print("\nCheck the 'scraped_data' directory for:")
    print("  • Training plan data (JSON)")
    print("  • Training plan links (CSV)")
    print("  • Comprehensive resource guide (TXT)")
    print("=" * 70)

if __name__ == "__main__":
    main()
