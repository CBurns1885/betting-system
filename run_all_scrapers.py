"""
Master script to run both ultramarathon scrapers
"""

import sys
from ultramarathon_scraper import UltramarathonScraper
from chester50_scraper import Chester50Scraper

def main():
    print("=" * 70)
    print("ULTRAMARATHON DATA COLLECTION SUITE")
    print("=" * 70)
    print("\nThis will scrape:")
    print("1. 50-mile ultramarathon training plans from multiple sources")
    print("2. Chester 50 race information from GB Ultras")
    print("\n" + "=" * 70 + "\n")

    # Run ultramarathon training plan scraper
    print("\n[1/2] SCRAPING ULTRAMARATHON TRAINING PLANS")
    print("-" * 70)
    try:
        ultra_scraper = UltramarathonScraper()
        plans, links = ultra_scraper.scrape_all_sources()
        ultra_scraper.save_results(plans, links)
        print(f"\n✓ Training plan scraper completed!")
        print(f"  - Plans found: {len(plans)}")
        print(f"  - Links found: {len(links)}")
    except Exception as e:
        print(f"\n✗ Error in training plan scraper: {str(e)}")

    print("\n" + "=" * 70 + "\n")

    # Run Chester 50 scraper
    print("[2/2] SCRAPING CHESTER 50 INFORMATION")
    print("-" * 70)
    try:
        chester_scraper = Chester50Scraper()
        chester_data = chester_scraper.scrape_chester50()
        chester_scraper.save_results(chester_data)
        print(f"\n✓ Chester 50 scraper completed!")
        print(f"  - Pages scraped: {len(chester_data['pages'])}")
    except Exception as e:
        print(f"\n✗ Error in Chester 50 scraper: {str(e)}")

    print("\n" + "=" * 70)
    print("ALL SCRAPING COMPLETE!")
    print("=" * 70)
    print("\nCheck the 'scraped_data' directory for all results.")
    print("\nFiles created:")
    print("  - training_plans_[timestamp].json")
    print("  - training_plan_links_[timestamp].csv")
    print("  - google_search_urls.txt")
    print("  - chester50_data_[timestamp].json")
    print("  - chester50_summary_[timestamp].txt")
    print("  - chester50_search_urls.txt")
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    main()
