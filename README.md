# SemRush Auto Analyzer

Automated SEMrush data extraction and competitor analysis toolkit. Scrape organic keywords, backlinks, traffic data, Google reviews, and run sentiment analysis - all controlled from a single config file.

## Features

- **SEMrush Data Export**: Organic keywords, backlinks, top pages, competitor analysis
- **Traffic Analytics**: Traffic sources, user journeys, historical trends
- **Google Reviews Scraper**: Scrape competitor reviews from Google Maps
- **Sentiment Analysis**: NLP-powered complaint categorization and topic modeling
- **Configurable**: Single YAML config for all settings
- **Master Script**: One command to run everything

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt

# Download NLTK data (optional, for better NLP)
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
```

### 2. Configure Your Analysis

Edit `config/config.yaml`:

```yaml
target:
  name: "Your Brand"
  domain: "yourbrand.com"

competitors:
  - domain: "competitor1.com"
    name: "Competitor 1"
  - domain: "competitor2.com"
    name: "Competitor 2"

market_keywords:
  - "your industry keyword"
  - "another keyword"
```

### 3. Start Chrome with Remote Debugging

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222
```

### 4. Log into SEMrush

Open SEMrush in the Chrome window you just launched and log in.

### 5. Run the Analysis

```bash
# Run everything
python master.py --all

# Or run specific pipelines
python master.py --semrush      # SEMrush export only
python master.py --traffic      # Traffic analysis only
python master.py --reviews      # Google reviews only
python master.py --sentiment    # Sentiment analysis only

# View current config
python master.py --config
```

## Directory Structure

```
SemRush_Auto_Analyzer/
├── master.py              # Main control script
├── config/
│   └── config.yaml        # All configuration settings
├── scripts/
│   ├── config_loader.py   # Config utilities
│   ├── semrush_exporter.py
│   ├── traffic_analyzer.py
│   ├── reviews_scraper.py
│   └── sentiment_analyzer.py
├── data/                  # Scraped data (gitignored)
│   ├── reviews/
│   └── semrush/
├── output/                # Analysis output (gitignored)
│   ├── screenshots/
│   ├── exports/
│   └── analysis/
├── requirements.txt
└── README.md
```

## Configuration Reference

### Target & Competitors

```yaml
target:
  name: "Your Brand"
  domain: "yourbrand.com"

competitors:
  - domain: "competitor1.com"
    name: "Competitor 1"
```

### SEMrush Settings

```yaml
semrush:
  database: "us"           # us, uk, de, fr, etc.
  search_type: "domain"    # domain, subdomain, url
  chrome_debug_port: 9222  # Chrome remote debugging port
```

### Market Keywords

```yaml
market_keywords:
  - "luxury candles"
  - "premium candles"
```

### Google Reviews

```yaml
google_reviews:
  locations:
    - "New York"
    - "Los Angeles"
  store_types:
    - "store"
    - "Nordstrom"
  max_scroll_count: 15
```

### Analysis Settings

```yaml
analysis:
  sentiment_threshold: -0.1    # Below = negative
  min_rating_negative: 3       # Ratings <= this = negative
  n_topics: 10                 # LDA topics
  n_key_phrases: 20            # TF-IDF phrases
```

### Industry/Market

```yaml
industry:
  category: "beauty-and-cosmetics"
  region: "us"
```

## Output

### Screenshots
Saved to `output/screenshots/` organized by type:
- `semrush/` - Organic keywords, backlinks, gap analysis
- `traffic/` - Traffic sources, journeys, trends

### Data Files
- `data/reviews/all_reviews.json` - Scraped reviews
- `data/reviews/all_reviews.csv` - CSV format

### Analysis Reports
- `output/analysis/sentiment_report.txt` - Human-readable report
- `output/analysis/analysis.json` - Full analysis data
- `output/analysis/negative_reviews.csv` - Filtered negative reviews

## Troubleshooting

### Chrome connection fails
- Make sure Chrome is running with `--remote-debugging-port=9222`
- Check no other Chrome instances are using that port
- Try closing all Chrome windows and restarting

### SEMrush pages not loading
- Ensure you're logged into SEMrush in the debugging Chrome window
- Some features require a paid SEMrush subscription

### No reviews found
- Google Maps UI changes frequently; selectors may need updating
- Try increasing `max_scroll_count` in config

## License

MIT License - Use freely for your marketing analysis needs.

---

Built by [FuturProof Labs](https://futur-proof.com) - Full-Funnel Growth Marketing
