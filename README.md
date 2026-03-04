# SemRush Auto Analyzer

Automated SEMrush data extraction, competitor analysis, and Google Ads dashboard integration toolkit. Extracts keyword intelligence, backlink profiles, traffic data, AI visibility metrics, reviews, and sentiment — all from a single config file.

## Features

- **Keyword Intelligence**: Volume, KD, CPC, Intent for 200+ keywords via Semrush API
- **Backlink Analysis**: Authority scores, referring domains, anchor text, top pages
- **AI Visibility**: AI Overview keyword triggers, test prompts, visibility recommendations
- **SEMrush Data Export**: Organic keywords, backlinks, top pages, competitor analysis (Selenium)
- **Traffic Analytics**: Traffic sources, user journeys, historical trends (Selenium)
- **Paid Media Benchmarks**: CPC extraction, competitor ad spend modeling
- **Google Reviews Scraper**: Scrape competitor reviews from Google Maps
- **Sentiment Analysis**: NLP-powered complaint categorization and topic modeling
- **Growth Projections**: 3/6 month financial forecasts with ROAS modeling
- **Dashboard Export**: Push all data to Google Ads Dashboard (keyword_market_data.json, backlinks, AI visibility)
- **Configurable**: Single YAML config per client
- **Master Script**: One command to run everything

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt

# Download NLTK data (optional, for better NLP)
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords'); nltk.download('wordnet')"
```

### 2. Configure Your Analysis

Configs are in `config/`. Use an existing one or create your own:

```bash
# Auto transport (Snowbird Ship Co)
python master.py --config-file config/config_embenauto.yaml --keywords

# Luxury candles (Luce Divina)
python master.py --config-file config/config_luce_divina.yaml --business-age new

# Jewelry (CaratTrade)
python master.py --config-file config/config_carattrade.yaml --business-age established
```

### 3. Run Analysis

```bash
# ── API-based analysis (no Chrome needed) ──
python master.py --keywords --config-file config/config_embenauto.yaml      # Keyword Volume/KD/CPC/Intent
python master.py --backlinks --config-file config/config_embenauto.yaml     # Backlink profiles
python master.py --ai-visibility --config-file config/config_embenauto.yaml # AI visibility analysis
python master.py --dashboard --config-file config/config_embenauto.yaml     # Export to dashboard

# ── Selenium-based analysis (requires Chrome + Semrush login) ──
python master.py --semrush --config-file config/config_embenauto.yaml       # Full Semrush UI export
python master.py --traffic --config-file config/config_embenauto.yaml       # Traffic deep dive
python master.py --paid --config-file config/config_embenauto.yaml          # Paid media benchmarks

# ── Other modules ──
python master.py --reviews --config-file config/config_embenauto.yaml       # Google reviews
python master.py --sentiment --config-file config/config_embenauto.yaml     # Sentiment analysis
python master.py --projections --config-file config/config_embenauto.yaml   # Growth projections

# ── Run everything ──
python master.py --all --config-file config/config_embenauto.yaml
python master.py --business-age established --config-file config/config_embenauto.yaml

# ── Projection overrides ──
python master.py --projections --spend 5000 --aov 1100 --cr 4.5 --months 6
```

### 4. Chrome Setup (for Selenium modules only)

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Log into SEMrush in the Chrome window, then run Selenium modules
```

## Module Overview

| Module | Method | Chrome? | Output |
|--------|--------|---------|--------|
| `--keywords` | Semrush API | No | `data/semrush/keyword_market_data.json` |
| `--backlinks` | Semrush API | No | `data/semrush/backlink_data.json` |
| `--ai-visibility` | Config analysis | No | `data/semrush/ai_visibility_data.json` |
| `--dashboard` | File export | No | `output/dashboard/{client}/semrush/` |
| `--semrush` | Selenium | Yes | `output/screenshots/semrush/` |
| `--traffic` | Selenium | Yes | `output/screenshots/traffic/` |
| `--paid` | Selenium + parsing | Yes | `data/paid_media/` |
| `--reviews` | Selenium | Yes | `data/reviews/` |
| `--sentiment` | NLP | No | `output/analysis/` |
| `--projections` | Math model | No | `output/projections/` |

## Directory Structure

```
SemRush_Auto_Analyzer/
├── master.py                   # Main orchestrator (10 pipelines)
├── config/
│   ├── config.yaml             # Default template
│   ├── config_embenauto.yaml   # Auto transport (Snowbird Ship Co)
│   ├── config_luce_divina.yaml # Luxury candles
│   └── config_carattrade.yaml  # Jewelry
├── scripts/
│   ├── config_loader.py        # Config utilities
│   ├── keyword_intelligence.py # Volume/KD/CPC/Intent via API
│   ├── backlink_analyzer.py    # Backlink profiles via API
│   ├── ai_visibility.py        # AI Overview analysis
│   ├── dashboard_exporter.py   # Export to Google Ads Dashboard
│   ├── semrush_exporter.py     # Selenium UI export
│   ├── traffic_analyzer.py     # Selenium traffic analysis
│   ├── paid_media_benchmarks.py# CPC + ad spend extraction
│   ├── reviews_scraper.py      # Google Maps reviews
│   ├── sentiment_analyzer.py   # NLP complaint analysis
│   └── growth_projector.py     # Financial projections
├── data/                       # Analysis output (gitignored)
│   ├── semrush/
│   │   ├── keyword_market_data.json    # Dashboard-ready keyword data
│   │   ├── keyword_intelligence.csv    # Full keyword CSV
│   │   ├── backlink_data.json          # Backlink profiles
│   │   ├── backlink_summary.csv        # Backlink comparison
│   │   └── ai_visibility_data.json     # AI visibility analysis
│   ├── reviews/
│   └── paid_media/
├── output/
│   ├── dashboard/{client}/semrush/     # Dashboard export target
│   ├── screenshots/
│   ├── analysis/
│   └── projections/
├── requirements.txt
└── README.md
```

## Dashboard Integration

The analyzer exports data to the Google Ads Dashboard at `/Users/alpharank/Google-Ads-Automation/`.

### Exported Files

| File | Dashboard View | Content |
|------|---------------|---------|
| `keyword_market_data.json` | Keywords, Search Terms, QS, Recommendations | Volume, KD, CPC, Intent per keyword |
| `backlink_data.json` | Backlinks view (new) | Authority, referring domains, anchors |
| `ai_visibility_data.json` | AI Analysis view | Test prompts, AIO triggers, recommendations |
| `competitor_benchmarks.json` | Competitors view | Traffic, ad spend, authority scores |

### Auto-Export

Set `dashboard.output_path` in your config to auto-push data:

```yaml
dashboard:
  output_path: "/Users/alpharank/Google-Ads-Automation"
  export_formats:
    - keyword_market_data
    - backlink_data
    - ai_visibility_data
    - competitor_benchmarks
```

Then run:
```bash
python master.py --dashboard --config-file config/config_embenauto.yaml
```

## Configuration Reference

### Required Fields

```yaml
target:
  name: "Your Brand"
  domain: "yourbrand.com"
  industry: "auto_transport"
  dashboard_client_id: "embenauto"  # maps to data/{id}/ in dashboard

competitors:
  - domain: "competitor.com"
    name: "Competitor Name"
    priority: "primary"  # primary or secondary

semrush:
  api_key: "your-semrush-api-key"
  database: "us"

market_keywords:
  - "your main keyword"
  - "another keyword"
```

### Optional Fields

```yaml
projections:
  monthly_ad_spend: 5000
  aov: 1100
  conversion_rate: 4.5
  months: 6

reviews:
  search_queries:
    - "brand name reviews"
  scroll_count: 10

dashboard:
  output_path: "/path/to/Google-Ads-Automation"
  export_formats:
    - keyword_market_data
    - backlink_data
    - ai_visibility_data
```

## Troubleshooting

### Semrush API returns 403
- API key may have expired or hit rate limits
- Check your Semrush subscription plan (API access requires Guru+ plan)
- Verify the API key in your config YAML

### Chrome connection fails (Selenium modules)
- Make sure Chrome is running with `--remote-debugging-port=9222`
- Check no other Chrome instances are using that port

### No reviews found
- Google Maps UI changes frequently; selectors may need updating
- Try increasing `scroll_count` in config

## License

MIT License

---

Built by [FuturProof Labs](https://futur-proof.com)
