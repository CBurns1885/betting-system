"""
Enhanced Chester 50 Ultramarathon Scraper with anti-bot measures
Scrapes information about the Chester 50 ultramarathon run by GB Ultras
"""

import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
import os
import random

class EnhancedChester50Scraper:
    def __init__(self, output_dir="scraped_data"):
        self.output_dir = output_dir

        # Rotate through multiple user agents
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]

        os.makedirs(output_dir, exist_ok=True)

        # GB Ultras and Chester 50 specific URLs
        self.sources = {
            'gb_ultras_main': 'https://www.gbultras.com/',
            'gb_ultras_chester': 'https://www.gbultras.com/chester50',
            'ultrasignup_chester': 'https://ultrasignup.com/results_event.aspx?did=93699',  # Chester 50 results
        }

        # Additional info sources
        self.community_sources = [
            'https://www.reddit.com/r/ultrarunning/search/?q=chester%2050',
            'https://www.strava.com/routes/3116429407189966102',  # Example Chester 50 route
        ]

    def get_headers(self):
        """Get randomized headers to avoid bot detection"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-GB,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
            'Referer': 'https://www.google.com/'
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
                    print(f"  403 Forbidden - Site has bot protection")
                    if attempt < retries - 1:
                        wait_time = (attempt + 1) * 3
                        print(f"  Waiting {wait_time} seconds before retry...")
                        time.sleep(wait_time)
                else:
                    print(f"  HTTP Error {e.response.status_code}")
                    break
            except Exception as e:
                print(f"  Error: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(2)

        print(f"✗ Could not scrape {url}")
        return None

    def extract_race_info(self, soup, url):
        """Extract detailed race information"""
        race_info = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'title': '',
            'description': '',
            'content_preview': '',
            'links_found': [],
            'text_content': ''
        }

        # Extract title
        title = soup.find('h1')
        if title:
            race_info['title'] = title.get_text(strip=True)

        # Extract meta description
        meta_desc = soup.find('meta', {'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            race_info['description'] = meta_desc.get('content')

        # Extract all headings for context
        headings = []
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4']):
            headings.append(heading.get_text(strip=True))
        race_info['headings'] = headings

        # Extract links
        for link in soup.find_all('a', href=True):
            link_text = link.get_text(strip=True)
            if link_text and len(link_text) > 0:
                race_info['links_found'].append({
                    'text': link_text[:100],
                    'href': link['href']
                })

        # Get main text content
        body = soup.find('body')
        if body:
            race_info['text_content'] = body.get_text(separator='\n', strip=True)[:8000]

        return race_info

    def scrape_chester50(self):
        """Scrape all Chester 50 related information"""
        chester_data = {
            'event_name': 'Chester 50 Ultramarathon',
            'organizer': 'GB Ultras',
            'scraped_at': datetime.now().isoformat(),
            'pages': [],
            'race_details': self.get_known_race_details()
        }

        print("Scraping Chester 50 Ultramarathon information...")
        print("=" * 70)

        for source_name, url in self.sources.items():
            print(f"\n[{source_name}]")
            soup = self.scrape_page(url)

            if soup:
                race_info = self.extract_race_info(soup, url)
                race_info['source_name'] = source_name
                chester_data['pages'].append(race_info)
                print(f"✓ Extracted content from {source_name}")
                time.sleep(random.uniform(3, 5))  # Random delay

        return chester_data

    def get_known_race_details(self):
        """Compile known information about Chester 50"""
        return {
            'race_name': 'Chester 50',
            'organizer': 'GB Ultras',
            'distance': '50 miles (80.5 km)',
            'location': 'Chester, England',
            'terrain': 'Canal towpath',
            'elevation': 'Minimal - flat course',
            'typical_date': 'Usually held in Spring (April/May)',
            'course_type': 'Out and back along canal',
            'cutoff_time': 'Typically 12-13 hours',
            'aid_stations': 'Multiple throughout the course',
            'website': 'https://www.gbultras.com/chester50',
            'notes': [
                'Flat, fast course suitable for first-time ultrarunners',
                'Run along the Shropshire Union Canal',
                'Good for targeting a PB due to flat terrain',
                'Can be used as training for longer ultras'
            ],
            'similar_races': [
                'Grand Union Canal Race (GB Ultras)',
                'Thames Path 100 (Centurion Running)',
                'South Downs Way 50 (Centurion Running)'
            ]
        }

    def get_training_tips_for_chester50(self):
        """Get training tips specific to Chester 50"""
        return {
            'course_specifics': [
                'Practice running on hard, flat surfaces (canal paths are hard-packed)',
                'Work on sustained pacing as there are no hills to break up effort',
                'Train your mind for repetitive scenery',
                'Practice fueling on flat, continuous running'
            ],
            'recommended_training': [
                'Base: 40-50 miles per week',
                'Long runs: Build to 30-35 miles',
                'Back-to-back long runs on weekends',
                'Practice race pace: ~11-13 min/mile for most runners',
                'Include some faster marathon-pace work'
            ],
            'gear_considerations': [
                'Road shoes or light trail shoes work well',
                'Bring layers as weather can change',
                'Practice with race vest/hydration system',
                'Anti-chafe measures important due to repetitive motion'
            ],
            'race_strategy': [
                'Start conservatively - the flatness can make it easy to go too fast',
                'Use turnaround point (25 miles) as mental checkpoint',
                'Break race into 10-mile segments',
                'Maintain consistent fueling schedule (every 30-45 minutes)'
            ]
        }

    def search_for_chester50_resources(self):
        """Generate search URLs for Chester 50 related content"""
        search_queries = {
            'race_info': [
                'Chester 50 ultramarathon GB Ultras',
                'Chester 50 race information',
                'Chester 50 ultra course profile',
                'GB Ultras Chester 50 entry'
            ],
            'race_reports': [
                'Chester 50 race report 2024',
                'Chester 50 race report 2023',
                'Chester 50 ultra review',
                'Chester 50 experience'
            ],
            'training': [
                'Chester 50 training plan',
                'Chester 50 preparation',
                'training for flat 50 mile ultra',
                'canal ultra training'
            ],
            'results': [
                'Chester 50 results',
                'Chester 50 finishing times',
                'Chester 50 ultrasignup results'
            ]
        }

        search_urls = {}
        for category, queries in search_queries.items():
            search_urls[category] = {
                'google': [f"https://www.google.com/search?q={q.replace(' ', '+')}" for q in queries],
                'youtube': [f"https://www.youtube.com/results?search_query={q.replace(' ', '+')}" for q in queries[:2]]
            }

        return search_urls

    def save_results(self, data):
        """Save scraped Chester 50 data"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save as JSON
        json_file = os.path.join(self.output_dir, f"chester50_data_{timestamp}.json")
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"\n✓ Saved Chester 50 data to {json_file}")

        # Create comprehensive guide
        guide_file = os.path.join(self.output_dir, f"chester50_complete_guide_{timestamp}.txt")
        with open(guide_file, 'w', encoding='utf-8') as f:
            f.write("CHESTER 50 ULTRAMARATHON - COMPLETE GUIDE\n")
            f.write("=" * 70 + "\n\n")

            # Race details
            f.write("RACE DETAILS\n")
            f.write("-" * 70 + "\n")
            for key, value in data['race_details'].items():
                if isinstance(value, list):
                    f.write(f"\n{key.replace('_', ' ').title()}:\n")
                    for item in value:
                        f.write(f"  • {item}\n")
                else:
                    f.write(f"{key.replace('_', ' ').title()}: {value}\n")

            # Training tips
            f.write("\n\nTRAINING TIPS FOR CHESTER 50\n")
            f.write("=" * 70 + "\n")
            training_tips = self.get_training_tips_for_chester50()
            for section, tips in training_tips.items():
                f.write(f"\n{section.replace('_', ' ').title()}:\n")
                f.write("-" * 40 + "\n")
                for tip in tips:
                    f.write(f"  • {tip}\n")

            # Search URLs
            f.write("\n\nSEARCH RESOURCES\n")
            f.write("=" * 70 + "\n")
            search_urls = self.search_for_chester50_resources()
            for category, platforms in search_urls.items():
                f.write(f"\n{category.replace('_', ' ').title()}:\n")
                f.write("-" * 40 + "\n")
                for platform, urls in platforms.items():
                    f.write(f"\n  {platform.upper()}:\n")
                    for url in urls:
                        f.write(f"    {url}\n")

            # Scraped content summary
            f.write("\n\nSCRAPED CONTENT SUMMARY\n")
            f.write("=" * 70 + "\n")
            f.write(f"Scraped at: {data['scraped_at']}\n")
            f.write(f"Pages attempted: {len(data['pages'])}\n\n")

            for page in data['pages']:
                f.write(f"\n{'-' * 70}\n")
                f.write(f"Source: {page.get('source_name', 'Unknown')}\n")
                f.write(f"URL: {page['url']}\n")
                if page.get('title'):
                    f.write(f"Title: {page['title']}\n")
                f.write(f"Links found: {len(page.get('links_found', []))}\n")
                if page.get('headings'):
                    f.write(f"Headings found: {len(page['headings'])}\n")

        print(f"✓ Saved complete guide to {guide_file}")

def main():
    scraper = EnhancedChester50Scraper()
    chester_data = scraper.scrape_chester50()
    scraper.save_results(chester_data)

    print("\n" + "=" * 70)
    print("CHESTER 50 SCRAPING COMPLETE!")
    print("=" * 70)
    print(f"Pages scraped: {len(chester_data['pages'])}")
    print("\nGenerated files:")
    print("  • Complete race data (JSON)")
    print("  • Comprehensive guide with training tips (TXT)")
    print("\nThe guide includes:")
    print("  • Known race details")
    print("  • Course-specific training tips")
    print("  • Race strategy recommendations")
    print("  • Gear suggestions")
    print("  • Search URLs for additional resources")
    print("=" * 70)

if __name__ == "__main__":
    main()
