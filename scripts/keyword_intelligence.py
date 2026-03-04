#!/usr/bin/env python3
"""
Keyword Intelligence Scraper

Extracts keyword data (Volume, KD, CPC, Intent) from Semrush UI via Selenium.
Scrapes Keyword Overview and Keyword Magic Tool pages using an existing
logged-in Chrome session via remote debugging.

Output:
  data/semrush/keyword_market_data.json   — Dashboard-compatible keyword data
  data/semrush/keyword_intelligence.csv   — Full keyword CSV
"""

import csv
import json
import os
import re
import sys
import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from scripts.config_loader import (
        load_config, get_target_domain, get_competitor_domains,
        get_data_dir, get_output_dir, ensure_directories
    )
except ImportError:
    from config_loader import (
        load_config, get_target_domain, get_competitor_domains,
        get_data_dir, get_output_dir, ensure_directories
    )


class KeywordIntelligence:
    """Scrapes keyword intelligence data from Semrush UI."""

    def __init__(self, config_path='config/config.yaml'):
        if isinstance(config_path, dict):
            self.config = config_path
        else:
            self.config = load_config(config_path)
        ensure_directories(self.config)

        self.data_dir = get_data_dir(self.config)
        self.output_dir = get_output_dir(self.config)
        self.screenshots_dir = os.path.join(self.output_dir, 'screenshots', 'keywords')
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, 'semrush'), exist_ok=True)

        self.driver = None
        self.database = self.config.get('semrush', {}).get('database', 'us')
        self.keywords_data = {}  # {keyword: {volume, kd, cpc, intent}}

    def connect_to_chrome(self):
        """Connect to existing Chrome session with Semrush logged in."""
        chrome_options = Options()
        port = self.config.get('semrush', {}).get('chrome_debug_port', 9222)
        chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print(f"  Connected to Chrome on port {port}")
            return True
        except Exception as e:
            print(f"  ERROR: Could not connect to Chrome: {e}")
            print("  Make sure Chrome is running with: --remote-debugging-port=9222")
            return False

    def close_popups(self):
        """Close any Semrush popups or modals."""
        selectors = [
            "button[data-test='close-modal']",
            ".srf-modal__close",
            "[aria-label='Close']",
            ".srf-popup__close",
            "button.close-button",
            "[data-test='modal-close']"
        ]
        for sel in selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, sel)
                for el in elements:
                    if el.is_displayed():
                        el.click()
                        time.sleep(0.3)
            except:
                pass

    def take_screenshot(self, name):
        """Take a screenshot."""
        filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(self.screenshots_dir, filename)
        self.driver.save_screenshot(filepath)
        print(f"    Screenshot: {filename}")
        return filepath

    def parse_number(self, text):
        """Parse a number string from Semrush (e.g., '74K', '1.2M', '$5.20', '72')."""
        if not text:
            return 0
        text = text.strip().replace(',', '').replace('$', '').replace('%', '')
        text = text.replace('\u2013', '').replace('\u2014', '').strip()
        if not text or text == '-' or text.lower() == 'n/a':
            return 0
        try:
            if text.upper().endswith('B'):
                return int(float(text[:-1]) * 1_000_000_000)
            elif text.upper().endswith('M'):
                return int(float(text[:-1]) * 1_000_000)
            elif text.upper().endswith('K'):
                return int(float(text[:-1]) * 1_000)
            else:
                return float(text) if '.' in text else int(text)
        except:
            return 0

    def extract_keyword_overview(self, keyword):
        """Navigate to Keyword Overview and extract Volume, KD, CPC, Intent."""
        encoded = keyword.replace(' ', '%20')
        url = f"https://www.semrush.com/analytics/keywordoverview/?db={self.database}&q={encoded}"
        self.driver.get(url)
        time.sleep(4)
        self.close_popups()

        kw_data = {
            'keyword': keyword,
            'volume': 0,
            'kd': 0,
            'cpc': 0,
            'intent': 'Unknown'
        }

        # Extract metrics from overview cards
        try:
            # Try data-test attributes first
            metric_selectors = [
                ("[data-test='volume']", "volume"),
                ("[data-test='keyword-overview-volume']", "volume"),
                ("[data-test='keyword-difficulty']", "kd"),
                ("[data-test='kd']", "kd"),
                ("[data-test='cpc']", "cpc"),
                ("[data-test='keyword-overview-cpc']", "cpc"),
            ]

            for selector, field in metric_selectors:
                try:
                    el = self.driver.find_element(By.CSS_SELECTOR, selector)
                    val = el.text.strip()
                    if val:
                        kw_data[field] = self.parse_number(val)
                except:
                    pass

            # Fallback: report card data elements
            if kw_data['volume'] == 0:
                try:
                    cards = self.driver.find_elements(By.CSS_SELECTOR,
                        ".srf-report-card__data, [class*='reportCard'] [class*='value'], [class*='metric-value']")
                    values = [c.text.strip() for c in cards if c.text.strip()]
                    if len(values) >= 1:
                        kw_data['volume'] = self.parse_number(values[0])
                    if len(values) >= 3:
                        kw_data['cpc'] = self.parse_number(values[2])
                except:
                    pass

            # Fallback: KD gauge/score
            if kw_data['kd'] == 0:
                try:
                    kd_els = self.driver.find_elements(By.CSS_SELECTOR,
                        "[class*='difficulty'] [class*='score'], [class*='kd-score'], "
                        "[class*='gauge'] [class*='value']")
                    for el in kd_els:
                        parsed = self.parse_number(el.text)
                        if 0 < parsed <= 100:
                            kw_data['kd'] = parsed
                            break
                except:
                    pass

            # Extract intent
            intent_map = {
                'T': 'Transactional', 'C': 'Commercial',
                'I': 'Informational', 'N': 'Navigational',
                'transactional': 'Transactional', 'commercial': 'Commercial',
                'informational': 'Informational', 'navigational': 'Navigational',
            }
            try:
                intent_els = self.driver.find_elements(By.CSS_SELECTOR,
                    "[data-test='intent'], [class*='intent'], [class*='Intent'] span, "
                    "[class*='search-intent']")
                for el in intent_els:
                    txt = el.text.strip()
                    if txt in intent_map:
                        kw_data['intent'] = intent_map[txt]
                        break
                    for key, val in intent_map.items():
                        if key.lower() in txt.lower():
                            kw_data['intent'] = val
                            break
            except:
                pass

        except Exception as e:
            print(f"    Warning: Could not extract metrics for '{keyword}': {e}")

        return kw_data

    def extract_keyword_table(self, url, max_rows=50):
        """Extract keyword data from a Semrush table page."""
        self.driver.get(url)
        time.sleep(5)
        self.close_popups()

        keywords = []
        table_selectors = [
            "table tbody tr",
            "[data-test='table'] tbody tr",
            ".srf-table tbody tr",
            "[class*='table'] tbody tr"
        ]

        for selector in table_selectors:
            try:
                rows = self.driver.find_elements(By.CSS_SELECTOR, selector)[:max_rows]
                if not rows:
                    continue

                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 3:
                        continue

                    # Find keyword text (skip checkbox/icon cells)
                    kw_text = ''
                    for cell in cells[:3]:
                        text = cell.text.strip()
                        if text and len(text) > 2 and not text.isdigit():
                            kw_text = text.split('\n')[0].strip()
                            break

                    if not kw_text:
                        continue

                    kw_entry = {
                        'keyword': kw_text,
                        'volume': 0,
                        'kd': 0,
                        'cpc': 0,
                        'intent': 'Unknown'
                    }

                    # Parse metrics from cells
                    cell_texts = [c.text.strip() for c in cells]
                    for ct in cell_texts:
                        if not ct:
                            continue
                        for line in ct.split('\n'):
                            line = line.strip()
                            if '$' in line and kw_entry['cpc'] == 0:
                                kw_entry['cpc'] = self.parse_number(line)
                            elif line in ('T', 'C', 'I', 'N', 'Transactional', 'Commercial',
                                          'Informational', 'Navigational'):
                                m = {'T': 'Transactional', 'C': 'Commercial',
                                     'I': 'Informational', 'N': 'Navigational'}
                                kw_entry['intent'] = m.get(line, line)

                    # Volume from data attributes
                    try:
                        for vel in row.find_elements(By.CSS_SELECTOR,
                                "[data-test='volume'], [class*='volume']"):
                            v = self.parse_number(vel.text)
                            if v > 0:
                                kw_entry['volume'] = v
                                break
                    except:
                        pass

                    # KD from data attributes
                    try:
                        for kel in row.find_elements(By.CSS_SELECTOR,
                                "[data-test='kd'], [class*='difficulty'], [class*='kd']"):
                            k = self.parse_number(kel.text)
                            if 0 < k <= 100:
                                kw_entry['kd'] = k
                                break
                    except:
                        pass

                    keywords.append(kw_entry)

                if keywords:
                    break

            except:
                continue

        return keywords

    def scrape_keyword_magic_tool(self, seed_keyword, max_rows=30):
        """Scrape related keywords from Keyword Magic Tool."""
        encoded = seed_keyword.replace(' ', '%20')
        url = f"https://www.semrush.com/analytics/keywordmagic/?q={encoded}&db={self.database}"
        print(f"    Keyword Magic Tool: {seed_keyword}")
        return self.extract_keyword_table(url, max_rows=max_rows)

    def scrape_domain_organic(self, domain, max_rows=50):
        """Scrape organic keyword positions for a domain."""
        url = (f"https://www.semrush.com/analytics/organic/positions/"
               f"?db={self.database}&q={domain}&searchType=domain")
        print(f"    Organic Positions: {domain}")
        return self.extract_keyword_table(url, max_rows=max_rows)

    def scrape_domain_paid(self, domain, max_rows=30):
        """Scrape paid keyword positions for a domain."""
        url = (f"https://www.semrush.com/analytics/adwords/positions/"
               f"?db={self.database}&q={domain}")
        print(f"    Paid Keywords: {domain}")
        return self.extract_keyword_table(url, max_rows=max_rows)

    def scrape_keyword_gap(self, target, competitors):
        """Scrape keyword gap analysis."""
        comps = ','.join(competitors[:4])
        url = (f"https://www.semrush.com/analytics/keywordgap/"
               f"?db={self.database}&q={target}&domains={comps}&searchType=domain")
        print(f"    Keyword Gap: {target} vs {len(competitors)} competitors")
        return self.extract_keyword_table(url, max_rows=50)

    def run(self):
        """Run the full keyword intelligence pipeline."""
        print(f"\n{'='*60}")
        print(f"  KEYWORD INTELLIGENCE SCRAPER")
        print(f"{'='*60}")

        if not self.connect_to_chrome():
            return False

        target_domain = get_target_domain(self.config)
        market_keywords = self.config.get('market_keywords', [])
        competitors = [c['domain'] for c in self.config.get('competitors', [])
                       if c.get('priority') == 'primary']

        print(f"\n  Target: {target_domain}")
        print(f"  Keywords: {len(market_keywords)}")
        print(f"  Competitors: {len(competitors)}")

        all_keywords = {}

        # Step 1: Keyword Overview for each market keyword
        print(f"\n  [1/5] Keyword Overview ({len(market_keywords)} keywords)...")
        for i, kw in enumerate(market_keywords, 1):
            print(f"    [{i}/{len(market_keywords)}] {kw}")
            data = self.extract_keyword_overview(kw)
            all_keywords[kw.lower()] = {
                'volume': data['volume'],
                'kd': data['kd'],
                'cpc': data['cpc'],
                'intent': data['intent']
            }
            time.sleep(1.5)

            if i % 10 == 0 or i == 1:
                safe = kw.replace(' ', '_')[:30]
                self.take_screenshot(f"kw_overview_{safe}")

        # Step 2: Related keywords from Keyword Magic Tool
        print(f"\n  [2/5] Discovering related keywords...")
        for seed in market_keywords[:5]:
            related = self.scrape_keyword_magic_tool(seed, max_rows=20)
            safe = seed.replace(' ', '_')[:30]
            self.take_screenshot(f"magic_{safe}")
            for r in related:
                kw_lower = r['keyword'].lower()
                if kw_lower not in all_keywords:
                    all_keywords[kw_lower] = {
                        'volume': r['volume'], 'kd': r['kd'],
                        'cpc': r['cpc'], 'intent': r['intent']
                    }
            time.sleep(2)
            print(f"      Found {len(related)} related keywords")

        # Step 3: Competitor organic keywords
        print(f"\n  [3/5] Scraping competitor organic keywords...")
        for comp in competitors[:3]:
            organic = self.scrape_domain_organic(comp, max_rows=30)
            self.take_screenshot(f"organic_{comp.replace('.', '_')}")
            for r in organic:
                kw_lower = r['keyword'].lower()
                if kw_lower not in all_keywords:
                    all_keywords[kw_lower] = {
                        'volume': r['volume'], 'kd': r['kd'],
                        'cpc': r['cpc'], 'intent': r['intent']
                    }
            time.sleep(2)
            print(f"      {comp}: {len(organic)} keywords")

        # Step 4: Competitor paid keywords
        print(f"\n  [4/5] Scraping competitor paid keywords...")
        for comp in competitors[:3]:
            paid = self.scrape_domain_paid(comp, max_rows=20)
            self.take_screenshot(f"paid_{comp.replace('.', '_')}")
            for r in paid:
                kw_lower = r['keyword'].lower()
                if kw_lower not in all_keywords:
                    all_keywords[kw_lower] = {
                        'volume': r['volume'], 'kd': r['kd'],
                        'cpc': r['cpc'], 'intent': r['intent']
                    }
            time.sleep(2)
            print(f"      {comp}: {len(paid)} paid keywords")

        # Step 5: Keyword gap
        print(f"\n  [5/5] Keyword gap analysis...")
        if competitors:
            gap = self.scrape_keyword_gap(target_domain, competitors)
            self.take_screenshot("keyword_gap")
            for r in gap:
                kw_lower = r['keyword'].lower()
                if kw_lower not in all_keywords:
                    all_keywords[kw_lower] = {
                        'volume': r['volume'], 'kd': r['kd'],
                        'cpc': r['cpc'], 'intent': r['intent']
                    }
            print(f"      Found {len(gap)} gap keywords")

        self.keywords_data = all_keywords

        # Summary
        print(f"\n  {'='*50}")
        print(f"  RESULTS: {len(all_keywords)} total keywords collected")
        with_vol = sum(1 for v in all_keywords.values() if v['volume'] > 0)
        with_kd = sum(1 for v in all_keywords.values() if v['kd'] > 0)
        with_cpc = sum(1 for v in all_keywords.values() if v['cpc'] > 0)
        with_intent = sum(1 for v in all_keywords.values() if v['intent'] != 'Unknown')
        print(f"    With Volume: {with_vol} | KD: {with_kd} | CPC: {with_cpc} | Intent: {with_intent}")
        print(f"  {'='*50}")

        return True

    def save_results(self):
        """Save keyword intelligence results."""
        semrush_dir = os.path.join(self.data_dir, 'semrush')

        dashboard_data = {
            'source': 'semrush_scraper',
            'generated_at': datetime.now().isoformat(),
            'keywords': self.keywords_data,
            'competitors': {c['domain']: {'name': c.get('name', c['domain']),
                           'priority': c.get('priority', 'secondary')}
                           for c in self.config.get('competitors', [])},
        }

        json_path = os.path.join(semrush_dir, 'keyword_market_data.json')
        with open(json_path, 'w') as f:
            json.dump(dashboard_data, f, indent=2)
        print(f"\n  Saved: {json_path}")

        csv_path = os.path.join(semrush_dir, 'keyword_intelligence.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Keyword', 'Volume', 'KD', 'CPC', 'Intent'])
            for kw, data in sorted(self.keywords_data.items(),
                                    key=lambda x: x[1].get('volume', 0), reverse=True):
                writer.writerow([kw, data['volume'], data['kd'], data['cpc'], data['intent']])
        print(f"  Saved: {csv_path}")

        return [json_path, csv_path]


def run_keyword_intelligence(config):
    """Entry point for master.py integration."""
    scraper = KeywordIntelligence(config)
    success = scraper.run()
    if success:
        scraper.save_results()
    return success


def save_results(results, output_dir):
    """Compatibility shim for master.py."""
    pass


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Keyword Intelligence Scraper')
    parser.add_argument('--config-file', default='config/config.yaml')
    args = parser.parse_args()

    config = load_config(args.config_file)
    scraper = KeywordIntelligence(config)
    success = scraper.run()
    if success:
        scraper.save_results()
