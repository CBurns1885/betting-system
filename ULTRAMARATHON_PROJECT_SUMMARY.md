# 🏃 Ultramarathon Training & Chester 50 Research Project

## 📋 Project Overview

This repository contains web scrapers and comprehensive resource guides for:
1. **50-mile ultramarathon training plans**
2. **Chester 50 ultramarathon (GB Ultras)** specific information

Even though many websites have anti-bot protection, the scrapers generate valuable resource guides with curated information, training tips, and search URLs to help you find the best ultramarathon resources.

## 📁 Files Created

### Main Scrapers
- `ultramarathon_scraper.py` - Basic training plan scraper
- `chester50_scraper.py` - Basic Chester 50 scraper
- `enhanced_ultramarathon_scraper.py` - **Enhanced** version with anti-bot measures
- `enhanced_chester50_scraper.py` - **Enhanced** Chester 50 scraper
- `run_all_scrapers.py` - Run both basic scrapers together

### Documentation
- `ULTRAMARATHON_SCRAPER_README.md` - Detailed usage instructions
- `scraper_requirements.txt` - Python dependencies
- `ULTRAMARATHON_PROJECT_SUMMARY.md` - This file!

### Generated Resources (in `scraped_data/`)
- `ultramarathon_resources.txt` - **Curated training resources**
- `chester50_complete_guide_[timestamp].txt` - **Complete Chester 50 guide**
- `google_search_urls.txt` - Search URLs for training plans
- `chester50_search_urls.txt` - Search URLs for race info
- Various JSON/CSV files with scraped data

## 🎯 What You Got

### 1. Ultramarathon Training Resources

The scraper generated a comprehensive guide including:

**Training Plan Sources:**
- Jason Koop (Training Essentials for Ultrarunning)
- David Roche (The Happy Runner)
- TrainingPeaks downloadable plans
- Ian Sharman training methods

**Books:**
- Training Essentials for Ultrarunning by Jason Koop
- Relentless Forward Progress by Bryon Powell
- The Happy Runner by David and Megan Roche

**Communities:**
- Reddit r/ultrarunning
- Facebook Ultra Running groups
- Strava ultrarunning clubs

**Ready-to-use Google searches** for finding free training plans!

### 2. Chester 50 Complete Guide

**Race Details:**
- **Distance:** 50 miles (80.5 km)
- **Location:** Chester, England
- **Terrain:** Canal towpath (FLAT!)
- **Course:** Out and back along Shropshire Union Canal
- **Cutoff:** 12-13 hours
- **Best for:** First-time 50-milers, flat course PBs

**Training Tips Specific to Chester 50:**
- Base building: 40-50 miles/week
- Long runs: Build to 30-35 miles
- Practice on hard, flat surfaces
- Mental training for repetitive scenery
- Race pace: ~11-13 min/mile for most runners

**Race Strategy:**
- Start conservatively (flat = easy to go too fast!)
- Use 25-mile turnaround as mental checkpoint
- Break into 10-mile segments
- Fuel every 30-45 minutes

**Gear:**
- Road shoes or light trail shoes
- Layers for weather changes
- Anti-chafe products (repetitive motion!)

## 🚀 Quick Start

### Install Dependencies
```bash
pip install -r scraper_requirements.txt
```

### Run Enhanced Scrapers
```bash
# Training plans
python enhanced_ultramarathon_scraper.py

# Chester 50
python enhanced_chester50_scraper.py
```

### Check Your Resources
```bash
cat scraped_data/ultramarathon_resources.txt
cat scraped_data/chester50_complete_guide_*.txt
```

## 💡 Next Steps - How to Use This

### For Training Plan Research:

1. **Check the resource guide:**
   ```bash
   cat scraped_data/ultramarathon_resources.txt
   ```

2. **Use the Google search URLs** provided to find free plans

3. **Try these specific searches:**
   - "Jason Koop 50 mile training plan PDF"
   - "free 50 mile ultramarathon training schedule"
   - Check TrainingPeaks.com for paid plans ($30-50)

4. **Join communities:**
   - r/ultrarunning on Reddit
   - Ask for recommendations there!

### For Chester 50 Specific Info:

1. **Read the complete guide:**
   ```bash
   cat scraped_data/chester50_complete_guide_*.txt
   ```

2. **Visit official site:**
   - https://www.gbultras.com/chester50
   - Check entry dates and pricing

3. **Watch race videos** using the YouTube search URLs provided

4. **Read race reports** using the Google search URLs

5. **Similar races to consider:**
   - Grand Union Canal Race (GB Ultras)
   - Thames Path 100 (Centurion Running)
   - South Downs Way 50 (Centurion Running)

## 🔧 Overcoming Bot Protection (Advanced)

Many sites use Cloudflare or similar protection. To scrape them:

### Option 1: Use Selenium (Included in enhanced scrapers)
```bash
pip install selenium
# Download ChromeDriver
# Uncomment Selenium code in enhanced scrapers
```

### Option 2: Manual Collection
Use the search URLs provided and manually save content you find

### Option 3: Browser Extensions
- Use "Web Scraper" Chrome extension
- Save pages manually and parse locally

## 📊 What the Scrapers Do

1. **Attempt to scrape** multiple sources for training plans and race info
2. **Generate curated resource lists** with books, coaches, communities
3. **Create search URLs** for easy manual research
4. **Save all data** in organized JSON/CSV/TXT files
5. **Include built-in race knowledge** (Chester 50 details, training tips, etc.)

## 🎓 Training Philosophy for 50-Mile Ultras

Based on the compiled resources:

1. **Base Building (12-16 weeks)**
   - Build to 40-50 mpw
   - Focus on time on feet
   - Include back-to-back long runs

2. **Specific Prep (8-12 weeks)**
   - Long runs: 25-35 miles
   - Practice race pace
   - Nail your fueling strategy
   - Mental training

3. **Taper (2-3 weeks)**
   - Reduce volume 30-50%
   - Maintain intensity
   - Focus on recovery

4. **For Chester 50 Specifically:**
   - More road running in training
   - Practice sustained flat running
   - Less focus on hill work
   - Mental preparation for repetitive scenery

## 📚 Recommended Resources Found

**Top Coaches:**
- Jason Koop (CTS, science-based)
- David Roche (SWAP, fast finishing)
- Ian Sharman (100-mile specialist)
- Hal Koerner (Western States expert)

**Must-Read Books:**
- Training Essentials for Ultrarunning (Koop)
- Relentless Forward Progress (Powell)
- The Happy Runner (Roche & Roche)

**Best Online Communities:**
- r/ultrarunning (very active, helpful)
- UltraRunning Magazine forums
- Trail Runner Magazine community

## 🤝 Contributing

Want to add more sources or improve the scrapers?
- Add URLs to the `training_plan_sources` list
- Update the `get_known_race_details()` function
- Share your own Chester 50 experience!

## ⚠️ Important Notes

1. **Respect website ToS** - Use manual browsing when scraping is blocked
2. **Personal use only** - Don't republish scraped content
3. **Bot protection is normal** - That's why we include curated guides
4. **Search URLs are gold** - Use them to find what you need

## 🏁 Bottom Line

You now have:
- ✅ Comprehensive Chester 50 race guide with training tips
- ✅ Curated list of the best 50-mile training resources
- ✅ Search URLs to find free training plans
- ✅ Books, coaches, and communities to explore
- ✅ Working scrapers if/when sites allow access
- ✅ Race-specific strategy for Chester 50

**Good luck with your ultramarathon training!** 🎉

---

*Generated by Claude Code for ultramarathon research*
