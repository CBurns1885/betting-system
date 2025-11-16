"""
Ultramarathon Training Plan Scraper
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

class UltramarathonScraper:
    def __init__(self, output_dir="scraped_data"):
        self.output_dir = output_dir
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        os.makedirs(output_dir, exist_ok=True)

        # Common sources for ultramarathon training plans
        self.training_plan_sources = [
            {
                'name': 'Runner\'s World',
                'url': 'https://www.runnersworld.com/uk/training/marathon/',
                'search_terms': ['50 mile', 'ultramarathon', 'ultra training']
            },
            {
                'name': 'TrailRunner',
                'url': 'https://www.trailrunnermag.com/training/',
                'search_terms': ['50 mile', '50-mile', 'ultramarathon']
            },
            {
                'name': 'UltraRunning Magazine',
                'url': 'https://ultrarunning.com/featured/training/',
                'search_terms': ['training plan', '50 mile']
            },
            {
                'name': 'Fellrnr',
                'url': 'https://fellrnr.com/wiki/Training_Plans',
                'search_terms': ['ultramarathon', '50 mile']
            },
            {
                'name': 'Hal Higdon',
                'url': 'https://www.halhigdon.com/training/',
                'search_terms': ['ultra', '50 mile']
            }
        ]

    def scrape_page(self, url):
        """Scrape a single page and return BeautifulSoup object"""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
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

        # Extract main content
        content_areas = soup.find_all(['article', 'main', 'div'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['content', 'article', 'post', 'training']
        ))

        if content_areas:
            plan_data['content'] = content_areas[0].get_text(separator='\n', strip=True)[:5000]

        # Try to extract description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            plan_data['description'] = meta_desc.get('content')

        return plan_data

    def find_training_plan_links(self, soup, base_url):
        """Find links that likely contain training plans"""
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()

            # Check if link text or href contains relevant keywords
            if any(keyword in text or keyword in href.lower()
                   for keyword in ['50 mile', '50-mile', 'ultra', 'training plan']):
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

        print("Starting to scrape ultramarathon training plans...")

        for source in self.training_plan_sources:
            print(f"\nScraping {source['name']}...")
            soup = self.scrape_page(source['url'])

            if soup:
                # Find relevant links
                links = self.find_training_plan_links(soup, source['url'])
                all_links.extend([{**link, 'source': source['name']} for link in links])
                print(f"Found {len(links)} potential training plan links")

                # Extract any training plans from the main page
                plan = self.extract_training_plan(soup, source['name'], source['url'])
                if plan['title'] or plan['content']:
                    all_plans.append(plan)

                time.sleep(2)  # Be respectful with request rate

        return all_plans, all_links

    def search_google_for_plans(self):
        """Generate Google search URLs for finding training plans"""
        search_queries = [
            "50 mile ultramarathon training plan",
            "50 mile ultra training schedule",
            "ultramarathon training plan 50 miles",
            "free 50 mile ultramarathon training plan",
            "beginner 50 mile ultra training",
            "advanced 50 mile ultramarathon plan"
        ]

        google_urls = []
        for query in search_queries:
            google_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            google_urls.append(google_url)

        return google_urls

    def save_results(self, plans, links):
        """Save scraped data to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save plans as JSON
        plans_file = os.path.join(self.output_dir, f"training_plans_{timestamp}.json")
        with open(plans_file, 'w', encoding='utf-8') as f:
            json.dump(plans, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(plans)} training plans to {plans_file}")

        # Save links as CSV
        links_file = os.path.join(self.output_dir, f"training_plan_links_{timestamp}.csv")
        if links:
            with open(links_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['source', 'url', 'text'])
                writer.writeheader()
                writer.writerows(links)
            print(f"Saved {len(links)} links to {links_file}")

        # Save Google search URLs
        google_urls = self.search_google_for_plans()
        google_file = os.path.join(self.output_dir, "google_search_urls.txt")
        with open(google_file, 'w') as f:
            f.write("Google Search URLs for 50-Mile Ultramarathon Training Plans\n")
            f.write("=" * 60 + "\n\n")
            for url in google_urls:
                f.write(url + "\n")
        print(f"Saved Google search URLs to {google_file}")

def main():
    scraper = UltramarathonScraper()
    plans, links = scraper.scrape_all_sources()
    scraper.save_results(plans, links)

    print("\n" + "=" * 60)
    print("Scraping complete!")
    print(f"Total training plans extracted: {len(plans)}")
    print(f"Total links found: {len(links)}")
    print("=" * 60)

if __name__ == "__main__":
    main()
