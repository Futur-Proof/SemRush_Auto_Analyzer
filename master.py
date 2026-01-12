#!/usr/bin/env python3
"""
SemRush Auto Analyzer - Master Control Script
==============================================

This script orchestrates all analysis pipelines:
1. SEMrush Data Export (organic keywords, backlinks, traffic)
2. Traffic Deep Analysis
3. Google Reviews Scraping
4. Sentiment Analysis

Usage:
    python master.py --all              # Run everything
    python master.py --semrush          # SEMrush export only
    python master.py --traffic          # Traffic analysis only
    python master.py --reviews          # Scrape reviews only
    python master.py --sentiment        # Sentiment analysis only
    python master.py --config           # Show current config
    python master.py --help             # Show help

Before running:
    1. Edit config/config.yaml with your target domain and competitors
    2. Start Chrome with remote debugging:
       /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port=9222
    3. Log into SEMrush in that Chrome window
"""

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# Add scripts directory to path
SCRIPT_DIR = Path(__file__).parent / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from config_loader import load_config, get_target_domain, get_competitor_domains, ensure_directories


def print_header():
    """Print welcome header"""
    print("=" * 70)
    print("  ____  _____ __  __ ____            _        ")
    print(" / ___|| ____|  \\/  |  _ \\ _   _ ___| |__     ")
    print(" \\___ \\|  _| | |\\/| | |_) | | | / __| '_ \\    ")
    print("  ___) | |___| |  | |  _ <| |_| \\__ \\ | | |   ")
    print(" |____/|_____|_|  |_|_| \\_\\\\__,_|___/_| |_|   ")
    print("                                              ")
    print("        AUTO ANALYZER - Master Script         ")
    print("=" * 70)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()


def show_config():
    """Display current configuration"""
    config = load_config()

    print("\n📋 CURRENT CONFIGURATION")
    print("-" * 50)
    print(f"\n🎯 Target Domain:")
    print(f"   {config.get('target', {}).get('name', 'N/A')}: {config.get('target', {}).get('domain', 'N/A')}")

    print(f"\n🏆 Competitors:")
    for comp in config.get('competitors', []):
        print(f"   - {comp.get('name', 'N/A')}: {comp.get('domain', 'N/A')}")

    print(f"\n🔍 SEMrush Settings:")
    print(f"   Database: {config.get('semrush', {}).get('database', 'us')}")
    print(f"   Chrome Port: {config.get('semrush', {}).get('chrome_debug_port', 9222)}")

    print(f"\n🔑 Market Keywords:")
    for kw in config.get('market_keywords', []):
        print(f"   - {kw}")

    print(f"\n🏭 Industry:")
    print(f"   Category: {config.get('industry', {}).get('category', 'N/A')}")
    print(f"   Region: {config.get('industry', {}).get('region', 'N/A')}")

    print("\n" + "-" * 50)


def run_semrush_export():
    """Run SEMrush data export"""
    print("\n" + "=" * 70)
    print("📊 RUNNING SEMRUSH DATA EXPORT")
    print("=" * 70)

    try:
        from semrush_exporter import SEMrushExporter
        exporter = SEMrushExporter()
        return exporter.run_full_export()
    except Exception as e:
        print(f"❌ SEMrush export failed: {e}")
        return False


def run_traffic_analysis():
    """Run traffic deep analysis"""
    print("\n" + "=" * 70)
    print("📈 RUNNING TRAFFIC ANALYSIS")
    print("=" * 70)

    try:
        from traffic_analyzer import TrafficAnalyzer
        analyzer = TrafficAnalyzer()
        return analyzer.run_full_analysis()
    except Exception as e:
        print(f"❌ Traffic analysis failed: {e}")
        return False


def run_reviews_scraper():
    """Run Google Reviews scraper"""
    print("\n" + "=" * 70)
    print("⭐ RUNNING REVIEWS SCRAPER")
    print("=" * 70)

    try:
        from reviews_scraper import ReviewsScraper
        scraper = ReviewsScraper()
        results = scraper.run_full_scrape()
        return len(results) > 0
    except Exception as e:
        print(f"❌ Reviews scraper failed: {e}")
        return False


def run_sentiment_analysis():
    """Run sentiment analysis"""
    print("\n" + "=" * 70)
    print("🔬 RUNNING SENTIMENT ANALYSIS")
    print("=" * 70)

    try:
        from sentiment_analyzer import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        report = analyzer.run()
        return report is not None
    except Exception as e:
        print(f"❌ Sentiment analysis failed: {e}")
        return False


def run_all():
    """Run all pipelines"""
    results = {}

    print("\n🚀 Running all analysis pipelines...\n")

    results['semrush'] = run_semrush_export()
    results['traffic'] = run_traffic_analysis()
    results['reviews'] = run_reviews_scraper()
    results['sentiment'] = run_sentiment_analysis()

    # Summary
    print("\n" + "=" * 70)
    print("📋 EXECUTION SUMMARY")
    print("=" * 70)

    for pipeline, success in results.items():
        status = "✅ Success" if success else "❌ Failed"
        print(f"   {pipeline.capitalize()}: {status}")

    print("\n" + "=" * 70)
    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    return all(results.values())


def main():
    parser = argparse.ArgumentParser(
        description="SemRush Auto Analyzer - Master Control Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python master.py --all              Run all pipelines
  python master.py --semrush          SEMrush export only
  python master.py --traffic          Traffic analysis only
  python master.py --reviews          Scrape reviews only
  python master.py --sentiment        Sentiment analysis only
  python master.py --config           Show current config

Setup:
  1. Edit config/config.yaml with your domains
  2. Start Chrome with: --remote-debugging-port=9222
  3. Log into SEMrush in that browser
  4. Run this script
        """
    )

    parser.add_argument('--all', action='store_true', help='Run all pipelines')
    parser.add_argument('--semrush', action='store_true', help='Run SEMrush export')
    parser.add_argument('--traffic', action='store_true', help='Run traffic analysis')
    parser.add_argument('--reviews', action='store_true', help='Run reviews scraper')
    parser.add_argument('--sentiment', action='store_true', help='Run sentiment analysis')
    parser.add_argument('--config', action='store_true', help='Show current config')

    args = parser.parse_args()

    print_header()

    # Ensure directories exist
    ensure_directories()

    # Show config if requested
    if args.config:
        show_config()
        return

    # Run specific pipelines
    if args.semrush:
        run_semrush_export()
    elif args.traffic:
        run_traffic_analysis()
    elif args.reviews:
        run_reviews_scraper()
    elif args.sentiment:
        run_sentiment_analysis()
    elif args.all:
        run_all()
    else:
        # No args - show help
        parser.print_help()
        print("\n💡 Quick start: python master.py --config")


if __name__ == "__main__":
    main()
