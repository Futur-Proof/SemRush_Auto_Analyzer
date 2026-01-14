#!/usr/bin/env python3
"""
SemRush Auto Analyzer - Master Control Script
==============================================

This script orchestrates all analysis pipelines:
1. SEMrush Data Export (organic keywords, backlinks, traffic)
2. Traffic Deep Analysis
3. Paid Media Benchmarks (CPC, competitor ad spend)
4. Google Reviews Scraping
5. Sentiment Analysis
6. Growth Projections (3/6 month forecasts)

Usage:
    python master.py --all                    # Run everything
    python master.py --semrush                # SEMrush export only
    python master.py --traffic                # Traffic analysis only
    python master.py --paid                   # Paid media benchmarks
    python master.py --reviews                # Scrape reviews only
    python master.py --sentiment              # Sentiment analysis only
    python master.py --projections            # Growth projections
    python master.py --projections-interactive  # Interactive projections
    python master.py --config                 # Show current config
    python master.py --config-file config/config_luce_divina.yaml  # Use specific config
    python master.py --help                   # Show help

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

# Global config path (can be overridden by --config-file)
CONFIG_PATH = "config/config.yaml"


def set_config_path(path):
    """Set the global config path."""
    global CONFIG_PATH
    CONFIG_PATH = path


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
    print(f"  Config: {CONFIG_PATH}")
    print("=" * 70)
    print()


def show_config():
    """Display current configuration"""
    from config_loader import load_config
    config = load_config(CONFIG_PATH)

    print("\n[CONFIG] CURRENT CONFIGURATION")
    print("-" * 50)
    print(f"\n[TARGET] Target Domain:")
    print(f"   {config.get('target', {}).get('name', 'N/A')}: {config.get('target', {}).get('domain', 'N/A')}")
    print(f"   Industry: {config.get('target', {}).get('industry', 'N/A')}")
    print(f"   Launch Status: {config.get('target', {}).get('launch_status', 'N/A')}")

    print(f"\n[COMPETITORS] Competitors:")
    for comp in config.get('competitors', []):
        tier = comp.get('tier', '')
        tier_str = f" ({tier})" if tier else ""
        print(f"   - {comp.get('name', 'N/A')}: {comp.get('domain', 'N/A')}{tier_str}")

    print(f"\n[SEMRUSH] SEMrush Settings:")
    print(f"   Database: {config.get('semrush', {}).get('database', 'us')}")
    print(f"   Chrome Port: {config.get('semrush', {}).get('chrome_debug_port', 9222)}")

    print(f"\n[KEYWORDS] Market Keywords ({len(config.get('market_keywords', []))} total):")
    for kw in config.get('market_keywords', [])[:10]:
        print(f"   - {kw}")
    if len(config.get('market_keywords', [])) > 10:
        print(f"   ... and {len(config.get('market_keywords', [])) - 10} more")

    # Show projection settings if available
    proj = config.get('projections', {})
    if proj:
        print(f"\n[PROJECTIONS] Growth Projection Settings:")
        print(f"   Monthly Ad Spend: ${proj.get('monthly_ad_spend', 'N/A'):,}")
        print(f"   AOV: ${proj.get('aov', 'N/A')}")
        print(f"   Conversion Rate: {proj.get('conversion_rate', 'benchmark')}%")
        print(f"   Projection Months: {proj.get('months', 6)}")

    print("\n" + "-" * 50)


def run_semrush_export():
    """Run SEMrush data export"""
    print("\n" + "=" * 70)
    print("[SEMRUSH] RUNNING SEMRUSH DATA EXPORT")
    print("=" * 70)

    try:
        from semrush_exporter import SEMrushExporter
        exporter = SEMrushExporter(CONFIG_PATH)
        return exporter.run_full_export()
    except Exception as e:
        print(f"[ERROR] SEMrush export failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_traffic_analysis():
    """Run traffic deep analysis"""
    print("\n" + "=" * 70)
    print("[TRAFFIC] RUNNING TRAFFIC ANALYSIS")
    print("=" * 70)

    try:
        from traffic_analyzer import TrafficAnalyzer
        analyzer = TrafficAnalyzer(CONFIG_PATH)
        return analyzer.run_full_analysis()
    except Exception as e:
        print(f"[ERROR] Traffic analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_paid_media_benchmarks():
    """Run paid media benchmarks analysis"""
    print("\n" + "=" * 70)
    print("[PAID] RUNNING PAID MEDIA BENCHMARKS")
    print("=" * 70)

    try:
        from paid_media_benchmarks import PaidMediaBenchmarks
        analyzer = PaidMediaBenchmarks(CONFIG_PATH)
        return analyzer.run()
    except Exception as e:
        print(f"[ERROR] Paid media benchmarks failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_reviews_scraper():
    """Run Google Reviews scraper"""
    print("\n" + "=" * 70)
    print("[REVIEWS] RUNNING REVIEWS SCRAPER")
    print("=" * 70)

    try:
        from reviews_scraper import ReviewsScraper
        scraper = ReviewsScraper(CONFIG_PATH)
        results = scraper.run_full_scrape()
        return len(results) > 0
    except Exception as e:
        print(f"[ERROR] Reviews scraper failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_sentiment_analysis():
    """Run sentiment analysis"""
    print("\n" + "=" * 70)
    print("[SENTIMENT] RUNNING SENTIMENT ANALYSIS")
    print("=" * 70)

    try:
        from sentiment_analyzer import SentimentAnalyzer
        analyzer = SentimentAnalyzer(CONFIG_PATH)
        report = analyzer.run()
        return report is not None
    except Exception as e:
        print(f"[ERROR] Sentiment analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_growth_projections(interactive=False, spend=None, aov=None, cpc=None, cr=None, months=6):
    """Run growth projections"""
    print("\n" + "=" * 70)
    print("[PROJECTIONS] RUNNING GROWTH PROJECTIONS")
    print("=" * 70)

    try:
        from growth_projector import GrowthProjector
        projector = GrowthProjector(CONFIG_PATH)

        if interactive:
            projector.run_interactive()
            return True
        elif spend and aov:
            # Use CLI arguments
            projections = projector.generate_projections(
                monthly_ad_spend=spend,
                aov=aov,
                cpc=cpc,
                conversion_rate=cr,
                months=months
            )
            projector.print_projection_table(projections)
            projector.save_projections(projections)
            return True
        else:
            result = projector.run_from_config()
            return result is not None
    except Exception as e:
        print(f"[ERROR] Growth projections failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all():
    """Run all pipelines"""
    results = {}

    print("\n[START] Running all analysis pipelines...\n")

    results['semrush'] = run_semrush_export()
    results['traffic'] = run_traffic_analysis()
    results['paid_media'] = run_paid_media_benchmarks()
    results['reviews'] = run_reviews_scraper()
    results['sentiment'] = run_sentiment_analysis()
    results['projections'] = run_growth_projections()

    # Summary
    print("\n" + "=" * 70)
    print("[SUMMARY] EXECUTION SUMMARY")
    print("=" * 70)

    for pipeline, success in results.items():
        status = "[OK] Success" if success else "[FAILED]"
        print(f"   {pipeline.replace('_', ' ').title()}: {status}")

    print("\n" + "=" * 70)
    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    return all(results.values())


def run_new_business_analysis():
    """
    Run analysis pipeline optimized for new business projections.
    Focuses on competitor benchmarks and growth projections.
    """
    results = {}

    print("\n[NEW BUSINESS] Running new business analysis pipeline...\n")
    print("This pipeline is optimized for pre-launch or newly launched businesses.")
    print("Focus: Competitor benchmarks, paid media CPCs, growth projections\n")

    # Step 1: Get competitor paid media benchmarks (CPC, ad spend)
    print("\n[Step 1/4] Analyzing competitor paid media...")
    results['paid_media'] = run_paid_media_benchmarks()

    # Step 2: Traffic analysis for competitor benchmarks
    print("\n[Step 2/4] Analyzing competitor traffic patterns...")
    results['traffic'] = run_traffic_analysis()

    # Step 3: Competitor reviews for market insights
    print("\n[Step 3/4] Scraping competitor reviews...")
    results['reviews'] = run_reviews_scraper()

    # Step 4: Generate growth projections
    print("\n[Step 4/4] Generating growth projections...")
    results['projections'] = run_growth_projections()

    # Summary
    print("\n" + "=" * 70)
    print("[SUMMARY] NEW BUSINESS ANALYSIS COMPLETE")
    print("=" * 70)

    for pipeline, success in results.items():
        status = "[OK] Success" if success else "[FAILED]"
        print(f"   {pipeline.replace('_', ' ').title()}: {status}")

    print("\n[OUTPUT] Check these directories for results:")
    print("   - output/projections/ - Growth projection reports")
    print("   - data/paid_media/ - CPC and ad spend benchmarks")
    print("   - output/screenshots/ - Visual captures from SEMrush")
    print("   - output/analysis/ - Sentiment analysis reports")

    print("\n" + "=" * 70)
    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    return all(results.values())


def run_established_business_analysis():
    """
    Run analysis pipeline optimized for established businesses.
    Focuses on own traffic analysis, competitor comparison, and optimization opportunities.
    """
    results = {}

    print("\n[ESTABLISHED BUSINESS] Running established business analysis pipeline...\n")
    print("This pipeline is for businesses with 6+ months of traffic data.")
    print("Focus: Own traffic analysis, competitor gaps, optimization opportunities\n")

    # Step 1: Full SEMrush export (own domain + competitors)
    print("\n[Step 1/5] Exporting SEMrush data (organic keywords, backlinks)...")
    results['semrush'] = run_semrush_export()

    # Step 2: Deep traffic analysis (includes own domain)
    print("\n[Step 2/5] Deep traffic analysis...")
    results['traffic'] = run_traffic_analysis()

    # Step 3: Paid media comparison
    print("\n[Step 3/5] Analyzing paid media landscape...")
    results['paid_media'] = run_paid_media_benchmarks()

    # Step 4: Competitor reviews for market positioning
    print("\n[Step 4/5] Scraping competitor reviews...")
    results['reviews'] = run_reviews_scraper()

    # Step 5: Sentiment analysis
    print("\n[Step 5/5] Running sentiment analysis...")
    results['sentiment'] = run_sentiment_analysis()

    # Summary
    print("\n" + "=" * 70)
    print("[SUMMARY] ESTABLISHED BUSINESS ANALYSIS COMPLETE")
    print("=" * 70)

    for pipeline, success in results.items():
        status = "[OK] Success" if success else "[FAILED]"
        print(f"   {pipeline.replace('_', ' ').title()}: {status}")

    print("\n[OUTPUT] Check these directories for results:")
    print("   - output/screenshots/semrush/ - Organic keywords, backlinks, gaps")
    print("   - output/screenshots/traffic/ - Traffic trends, sources, journey")
    print("   - data/paid_media/ - CPC and competitor ad spend")
    print("   - output/analysis/ - Sentiment analysis reports")

    print("\n[NEXT STEPS]")
    print("   1. Review keyword gap analysis for SEO opportunities")
    print("   2. Compare traffic sources to identify channel gaps")
    print("   3. Analyze competitor ad spend to optimize budget allocation")
    print("   4. Use sentiment data to improve product/service")

    print("\n" + "=" * 70)
    print(f"  Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    return all(results.values())


def main():
    from config_loader import ensure_directories, load_config

    parser = argparse.ArgumentParser(
        description="SemRush Auto Analyzer - Master Control Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # For NEW businesses (pre-launch or < 6 months):
  python master.py --business-age new --config-file config/config_luce_divina.yaml

  # For ESTABLISHED businesses (6+ months with traffic data):
  python master.py --business-age established --config-file config/config.yaml

  # Run all pipelines:
  python master.py --all

  # Growth projections with variables:
  python master.py --projections --spend 5000 --aov 65 --cr 1.5 --months 6
  python master.py --projections --spend 10000 --aov 85 --cpc 2.00 --cr 2.0

  # Individual modules:
  python master.py --semrush                SEMrush export only
  python master.py --traffic                Traffic analysis only
  python master.py --paid                   Paid media benchmarks
  python master.py --reviews                Scrape reviews only
  python master.py --sentiment              Sentiment analysis only
  python master.py --projections-interactive   Interactive projection mode
  python master.py --config                 Show current config

Setup:
  1. Edit config/config.yaml (or create custom config)
  2. Start Chrome with: --remote-debugging-port=9222
  3. Log into SEMrush in that browser
  4. Run this script
        """
    )

    parser.add_argument('--all', action='store_true', help='Run all pipelines')
    parser.add_argument('--business-age', type=str, choices=['new', 'established'],
                        help='Business age: "new" (pre-launch/just launched) or "established" (6+ months)')
    parser.add_argument('--new-business', action='store_true',
                        help='[DEPRECATED] Use --business-age new instead')
    parser.add_argument('--semrush', action='store_true', help='Run SEMrush export')
    parser.add_argument('--traffic', action='store_true', help='Run traffic analysis')
    parser.add_argument('--paid', action='store_true', help='Run paid media benchmarks')
    parser.add_argument('--reviews', action='store_true', help='Run reviews scraper')
    parser.add_argument('--sentiment', action='store_true', help='Run sentiment analysis')
    parser.add_argument('--projections', action='store_true', help='Run growth projections')
    parser.add_argument('--projections-interactive', action='store_true',
                        help='Run growth projections in interactive mode')

    # Projection variables (override config values)
    parser.add_argument('--spend', type=float, help='Monthly ad spend ($)')
    parser.add_argument('--aov', type=float, help='Average order value ($)')
    parser.add_argument('--cpc', type=float, help='Cost per click ($)')
    parser.add_argument('--cr', type=float, help='Conversion rate (%%)')
    parser.add_argument('--months', type=int, default=6, help='Months to project (default: 6)')

    parser.add_argument('--config', action='store_true', help='Show current config')
    parser.add_argument('--config-file', type=str, default='config/config.yaml',
                        help='Path to configuration file (default: config/config.yaml)')

    args = parser.parse_args()

    # Set config path
    set_config_path(args.config_file)

    print_header()

    # Ensure directories exist
    config = load_config(CONFIG_PATH)
    ensure_directories(config)

    # Show config if requested
    if args.config:
        show_config()
        return

    # Run specific pipelines
    if args.business_age == 'new' or args.new_business:
        run_new_business_analysis()
    elif args.business_age == 'established':
        run_established_business_analysis()
    elif args.semrush:
        run_semrush_export()
    elif args.traffic:
        run_traffic_analysis()
    elif args.paid:
        run_paid_media_benchmarks()
    elif args.reviews:
        run_reviews_scraper()
    elif args.sentiment:
        run_sentiment_analysis()
    elif args.projections:
        run_growth_projections(
            spend=args.spend,
            aov=args.aov,
            cpc=args.cpc,
            cr=args.cr,
            months=args.months
        )
    elif args.projections_interactive:
        run_growth_projections(interactive=True)
    elif args.all:
        run_all()
    else:
        # No args - show help
        parser.print_help()
        print("\n[TIP] Quick start: python master.py --config")
        print("[TIP] For NEW business: python master.py --business-age new --config-file config/config_luce_divina.yaml")
        print("[TIP] For ESTABLISHED business: python master.py --business-age established")


if __name__ == "__main__":
    main()
