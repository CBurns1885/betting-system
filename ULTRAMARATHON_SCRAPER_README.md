# Ultramarathon Training Plan & Chester 50 Scraper

A comprehensive web scraper for collecting 50-mile ultramarathon training plans and detailed information about the Chester 50 ultramarathon run by GB Ultras.

## Features

### 1. General Ultramarathon Training Plan Scraper (`ultramarathon_scraper.py`)
- Scrapes multiple reputable sources for 50-mile ultramarathon training plans
- Extracts training plan details, schedules, and advice
- Generates search URLs for finding additional resources
- Saves results in JSON and CSV formats

**Sources include:**
- Runner's World
- TrailRunner Magazine
- UltraRunning Magazine
- Fellrnr
- Hal Higdon
- And more...

### 2. Chester 50 Specific Scraper (`chester50_scraper.py`)
- Dedicated scraper for the Chester 50 ultramarathon by GB Ultras
- Extracts race details: date, distance, elevation, entry fees, cutoff times
- Captures course information and aid station details
- Generates comprehensive search URLs for race reports and reviews

## Installation

1. **Clone this repository:**
```bash
git clone <your-repo-url>
cd betting-system
```

2. **Install dependencies:**
```bash
pip install -r scraper_requirements.txt
```

## Usage

### Run the Ultramarathon Training Plan Scraper

```bash
python ultramarathon_scraper.py
```

This will:
- Scrape training plans from configured sources
- Save extracted plans to `scraped_data/training_plans_[timestamp].json`
- Save discovered links to `scraped_data/training_plan_links_[timestamp].csv`
- Generate Google search URLs in `scraped_data/google_search_urls.txt`

### Run the Chester 50 Scraper

```bash
python chester50_scraper.py
```

This will:
- Scrape the GB Ultras website for Chester 50 information
- Save detailed race data to `scraped_data/chester50_data_[timestamp].json`
- Create a summary report in `scraped_data/chester50_summary_[timestamp].txt`
- Generate search URLs for additional resources in `scraped_data/chester50_search_urls.txt`

### Run Both Scrapers

```bash
python run_all_scrapers.py
```

## Output Files

All scraped data is saved to the `scraped_data/` directory:

### Training Plan Scraper Output:
- `training_plans_[timestamp].json` - Full training plan data
- `training_plan_links_[timestamp].csv` - All discovered links
- `google_search_urls.txt` - Google search URLs for manual exploration

### Chester 50 Scraper Output:
- `chester50_data_[timestamp].json` - Complete Chester 50 race information
- `chester50_summary_[timestamp].txt` - Human-readable summary
- `chester50_search_urls.txt` - Search URLs for race reports and reviews

## Configuration

### Adding More Sources (ultramarathon_scraper.py)

Edit the `training_plan_sources` list in the `UltramarathonScraper` class:

```python
self.training_plan_sources.append({
    'name': 'Your Source Name',
    'url': 'https://example.com/training-plans',
    'search_terms': ['50 mile', 'ultramarathon']
})
```

### Adding More Chester 50 URLs (chester50_scraper.py)

Edit the `sources` dictionary in the `Chester50Scraper` class:

```python
self.sources['new_source'] = 'https://example.com/chester50'
```

## Rate Limiting

Both scrapers include built-in delays between requests (2 seconds) to be respectful to web servers. Adjust the `time.sleep()` values if needed.

## Legal & Ethical Considerations

- This scraper is for **personal research and educational purposes**
- Always check websites' `robots.txt` and Terms of Service
- Respect rate limits and server resources
- Don't republish scraped content without permission
- Some websites may require authentication or have anti-scraping measures

## Advanced Usage

### Using Selenium for Dynamic Content

Some websites load content via JavaScript. For these cases, consider using Selenium:

```bash
pip install selenium
```

Then modify the scraper to use Selenium WebDriver instead of requests.

### Scheduling Regular Scrapes

Set up a cron job (Linux/Mac) or Task Scheduler (Windows) to run the scrapers regularly:

```bash
# Run every Sunday at 9 AM
0 9 * * 0 cd /path/to/betting-system && python ultramarathon_scraper.py
```

## Troubleshooting

### Common Issues:

1. **403 Forbidden Errors**
   - Some websites block scrapers. Try updating the User-Agent header.
   - Consider using Selenium for these sites.

2. **Timeout Errors**
   - Increase the timeout value in the `requests.get()` calls
   - Check your internet connection

3. **Empty Results**
   - Website structure may have changed
   - Check the URL is still valid
   - Inspect the HTML to update CSS selectors

## Contributing

Feel free to add more sources, improve extraction logic, or add new features!

## Resources

### Ultramarathon Training Resources:
- [GB Ultras](https://www.gbultras.com/)
- [UltraRunning Magazine](https://ultrarunning.com/)
- [TrailRunner Magazine](https://www.trailrunnermag.com/)
- [iRunFar](https://www.irunfar.com/)

### Chester 50 Specific:
- [Official Chester 50 Page](https://www.gbultras.com/chester50)
- Search for race reports on running forums and blogs

## License

For personal use. Respect website terms of service.
