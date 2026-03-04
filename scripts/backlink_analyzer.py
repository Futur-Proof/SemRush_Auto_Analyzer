#!/usr/bin/env python3
"""
Backlink Analyzer Scraper

Extracts backlink profile data from Semrush UI via Selenium for target domain
and competitors. Scrapes Backlinks Overview, Referring Domains, Anchors, and
Top Pages using an existing logged-in Chrome session.

Output:
  data/semrush/backlink_data.json    — Full backlink profiles
  data/semrush/backlink_summary.csv  — Domain comparison table
"""

import csv
import json
import os
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


class BacklinkAnalyzer:
    """Scrapes backlink profile data from Semrush UI."""

    def __init__(self, config_path='config/config.yaml'):
        if isinstance(config_path, dict):
            self.config = config_path
        else:
            self.config = load_config(config_path)
        ensure_directories(self.config)

        self.data_dir = get_data_dir(self.config)
        self.output_dir = get_output_dir(self.config)
        self.screenshots_dir = os.path.join(self.output_dir, 'screenshots', 'backlinks')
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(os.path.join(self.data_dir, 'semrush'), exist_ok=True)

        self.driver = None
        self.results = {}

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
        """Parse a number string from Semrush."""
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

    def scrape_backlinks_overview(self, domain):
        """Scrape backlinks overview page for a domain."""
        print(f"    Backlinks Overview: {domain}")
        url = f"https://www.semrush.com/analytics/backlinks/overview/?q={domain}&searchType=domain"
        self.driver.get(url)
        time.sleep(5)
        self.close_popups()

        overview = {
            'authority_score': 0,
            'total_backlinks': 0,
            'referring_domains': 0,
            'referring_ips': 0,
            'follow_links': 0,
            'nofollow_links': 0,
            'text_links': 0,
            'image_links': 0
        }

        # Try data-test selectors first
        field_selectors = [
            ("[data-test='authority-score']", "authority_score"),
            ("[data-test='backlinks']", "total_backlinks"),
            ("[data-test='referring-domains']", "referring_domains"),
            ("[data-test='referring-ips']", "referring_ips"),
        ]

        for selector, field in field_selectors:
            try:
                el = self.driver.find_element(By.CSS_SELECTOR, selector)
                overview[field] = self.parse_number(el.text)
            except:
                pass

        # Fallback: extract from report cards
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR,
                ".srf-report-card__data, [class*='reportCard'] [class*='value'], "
                "[class*='metric-value'], [class*='overview'] [class*='value']")
            values = [c.text.strip() for c in cards if c.text.strip()]

            # Semrush overview typically shows: Authority Score, Backlinks, Ref Domains, Ref IPs
            if len(values) >= 1 and overview['authority_score'] == 0:
                overview['authority_score'] = self.parse_number(values[0])
            if len(values) >= 2 and overview['total_backlinks'] == 0:
                overview['total_backlinks'] = self.parse_number(values[1])
            if len(values) >= 3 and overview['referring_domains'] == 0:
                overview['referring_domains'] = self.parse_number(values[2])
            if len(values) >= 4 and overview['referring_ips'] == 0:
                overview['referring_ips'] = self.parse_number(values[3])
        except:
            pass

        # Try to extract follow/nofollow from link type distribution
        try:
            type_els = self.driver.find_elements(By.CSS_SELECTOR,
                "[class*='follow'], [class*='nofollow'], [class*='link-type'] [class*='value']")
            for el in type_els:
                text = el.text.strip().lower()
                parent_text = ''
                try:
                    parent_text = el.find_element(By.XPATH, '..').text.strip().lower()
                except:
                    pass
                combined = f"{parent_text} {text}"
                val = self.parse_number(el.text)
                if 'nofollow' in combined and val > 0:
                    overview['nofollow_links'] = val
                elif 'follow' in combined and val > 0 and overview['follow_links'] == 0:
                    overview['follow_links'] = val
                elif 'text' in combined and val > 0:
                    overview['text_links'] = val
                elif 'image' in combined and val > 0:
                    overview['image_links'] = val
        except:
            pass

        self.take_screenshot(f"bl_overview_{domain.replace('.', '_')}")
        return overview

    def scrape_referring_domains(self, domain, max_rows=50):
        """Scrape top referring domains page."""
        print(f"    Referring Domains: {domain}")
        url = f"https://www.semrush.com/analytics/backlinks/refdomains/?q={domain}&searchType=domain"
        self.driver.get(url)
        time.sleep(5)
        self.close_popups()

        domains = []
        table_selectors = [
            "table tbody tr",
            "[data-test='table'] tbody tr",
            ".srf-table tbody tr"
        ]

        for selector in table_selectors:
            try:
                rows = self.driver.find_elements(By.CSS_SELECTOR, selector)[:max_rows]
                if not rows:
                    continue

                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 2:
                        continue

                    # First usable cell is usually the domain
                    ref_domain = ''
                    for cell in cells[:3]:
                        text = cell.text.strip().split('\n')[0].strip()
                        if text and '.' in text and len(text) > 3:
                            ref_domain = text
                            break

                    if not ref_domain:
                        continue

                    entry = {
                        'domain': ref_domain,
                        'authority_score': 0,
                        'backlinks_count': 0,
                    }

                    # Try to extract authority score and backlink count
                    try:
                        as_els = row.find_elements(By.CSS_SELECTOR,
                            "[data-test='authority-score'], [class*='authority'], [class*='ascore']")
                        for el in as_els:
                            v = self.parse_number(el.text)
                            if 0 < v <= 100:
                                entry['authority_score'] = v
                                break
                    except:
                        pass

                    try:
                        bl_els = row.find_elements(By.CSS_SELECTOR,
                            "[data-test='backlinks'], [class*='backlink']")
                        for el in bl_els:
                            v = self.parse_number(el.text)
                            if v > 0:
                                entry['backlinks_count'] = v
                                break
                    except:
                        pass

                    domains.append(entry)

                if domains:
                    break
            except:
                continue

        self.take_screenshot(f"bl_refdomains_{domain.replace('.', '_')}")
        return domains

    def scrape_anchors(self, domain, max_rows=30):
        """Scrape top anchor texts."""
        print(f"    Anchor Texts: {domain}")
        url = f"https://www.semrush.com/analytics/backlinks/anchors/?q={domain}&searchType=domain"
        self.driver.get(url)
        time.sleep(5)
        self.close_popups()

        anchors = []
        table_selectors = [
            "table tbody tr",
            "[data-test='table'] tbody tr",
            ".srf-table tbody tr"
        ]

        for selector in table_selectors:
            try:
                rows = self.driver.find_elements(By.CSS_SELECTOR, selector)[:max_rows]
                if not rows:
                    continue

                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 2:
                        continue

                    anchor_text = ''
                    for cell in cells[:2]:
                        text = cell.text.strip().split('\n')[0].strip()
                        if text and len(text) > 0:
                            anchor_text = text
                            break

                    if not anchor_text:
                        continue

                    entry = {
                        'anchor': anchor_text,
                        'referring_domains': 0,
                        'backlinks': 0
                    }

                    # Extract counts from remaining cells
                    cell_texts = [c.text.strip() for c in cells[1:]]
                    nums = []
                    for ct in cell_texts:
                        v = self.parse_number(ct.split('\n')[0])
                        if v > 0:
                            nums.append(v)

                    if len(nums) >= 1:
                        entry['referring_domains'] = nums[0]
                    if len(nums) >= 2:
                        entry['backlinks'] = nums[1]

                    anchors.append(entry)

                if anchors:
                    break
            except:
                continue

        self.take_screenshot(f"bl_anchors_{domain.replace('.', '_')}")
        return anchors

    def scrape_top_pages(self, domain, max_rows=30):
        """Scrape top pages by backlinks."""
        print(f"    Top Pages: {domain}")
        url = f"https://www.semrush.com/analytics/backlinks/backlinks/?q={domain}&searchType=domain"
        self.driver.get(url)
        time.sleep(5)
        self.close_popups()

        # Scroll down to see more data
        self.driver.execute_script("window.scrollTo(0, 400)")
        time.sleep(1)

        pages = []
        table_selectors = [
            "table tbody tr",
            "[data-test='table'] tbody tr",
            ".srf-table tbody tr"
        ]

        for selector in table_selectors:
            try:
                rows = self.driver.find_elements(By.CSS_SELECTOR, selector)[:max_rows]
                if not rows:
                    continue

                for row in rows:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) < 2:
                        continue

                    # Look for URLs in cells
                    page_url = ''
                    try:
                        links = row.find_elements(By.TAG_NAME, "a")
                        for link in links:
                            href = link.get_attribute("href") or ''
                            text = link.text.strip()
                            if text and ('http' in text or '/' in text):
                                page_url = text
                                break
                    except:
                        pass

                    if not page_url:
                        for cell in cells[:2]:
                            text = cell.text.strip().split('\n')[0]
                            if '/' in text or 'http' in text:
                                page_url = text
                                break

                    if not page_url:
                        continue

                    entry = {
                        'url': page_url,
                        'referring_domains': 0,
                        'backlinks': 0
                    }

                    cell_texts = [c.text.strip() for c in cells]
                    nums = []
                    for ct in cell_texts:
                        v = self.parse_number(ct.split('\n')[0])
                        if v > 0:
                            nums.append(v)
                    if len(nums) >= 1:
                        entry['referring_domains'] = nums[0]
                    if len(nums) >= 2:
                        entry['backlinks'] = nums[1]

                    pages.append(entry)

                if pages:
                    break
            except:
                continue

        self.take_screenshot(f"bl_pages_{domain.replace('.', '_')}")
        return pages

    def scrape_backlink_gap(self, target, competitors):
        """Scrape backlink gap analysis."""
        print(f"    Backlink Gap: {target} vs {len(competitors)} competitors")
        comps = ','.join(competitors[:4])
        url = (f"https://www.semrush.com/analytics/backlinkgap/"
               f"?q={target}&domains={comps}&searchType=domain")
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()
        self.take_screenshot("backlink_gap")

    def run(self):
        """Run full backlink analysis."""
        print(f"\n{'='*60}")
        print(f"  BACKLINK ANALYZER (Selenium)")
        print(f"{'='*60}")

        if not self.connect_to_chrome():
            return False

        target_domain = get_target_domain(self.config)
        competitors = [c['domain'] for c in self.config.get('competitors', [])
                       if c.get('priority') == 'primary']

        print(f"\n  Target: {target_domain}")
        print(f"  Competitors: {len(competitors)}")

        self.results = {
            'generated_at': datetime.now().isoformat(),
            'target_domain': target_domain,
            'profiles': {}
        }

        all_domains = [target_domain] + competitors

        for i, domain in enumerate(all_domains, 1):
            print(f"\n  [{i}/{len(all_domains)}] Analyzing {domain}...")

            profile = {
                'overview': self.scrape_backlinks_overview(domain),
                'top_referring_domains': self.scrape_referring_domains(domain, limit=50),
                'top_anchors': self.scrape_anchors(domain, limit=30),
                'top_pages': self.scrape_top_pages(domain, limit=30)
            }
            self.results['profiles'][domain] = profile

            ov = profile['overview']
            print(f"      Auth: {ov['authority_score']} | "
                  f"Backlinks: {ov['total_backlinks']:,} | "
                  f"Ref Domains: {ov['referring_domains']:,}")
            time.sleep(2)

        # Backlink gap
        if competitors:
            self.scrape_backlink_gap(target_domain, competitors)

        # Comparison table
        print(f"\n  {'Domain':<35} {'Auth':>5} {'Backlinks':>12} {'Ref Domains':>12}")
        print(f"  {'-'*67}")
        for domain in all_domains:
            ov = self.results['profiles'][domain]['overview']
            marker = " <-- target" if domain == target_domain else ""
            print(f"  {domain:<35} {ov['authority_score']:>5} "
                  f"{ov['total_backlinks']:>12,} "
                  f"{ov['referring_domains']:>12,}{marker}")

        return True

    def save_results(self):
        """Save backlink analysis results."""
        semrush_dir = os.path.join(self.data_dir, 'semrush')

        # Full JSON
        json_path = os.path.join(semrush_dir, 'backlink_data.json')
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n  Saved: {json_path}")

        # Summary CSV
        csv_path = os.path.join(semrush_dir, 'backlink_summary.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['domain', 'authority_score', 'total_backlinks',
                             'referring_domains', 'follow_links', 'nofollow_links',
                             'text_links', 'image_links'])
            for domain, profile in self.results.get('profiles', {}).items():
                ov = profile.get('overview', {})
                writer.writerow([
                    domain, ov.get('authority_score', 0), ov.get('total_backlinks', 0),
                    ov.get('referring_domains', 0), ov.get('follow_links', 0),
                    ov.get('nofollow_links', 0), ov.get('text_links', 0),
                    ov.get('image_links', 0)
                ])
        print(f"  Saved: {csv_path}")

        return [json_path, csv_path]


def run_backlink_analysis(config):
    """Entry point for master.py integration."""
    analyzer = BacklinkAnalyzer(config)
    success = analyzer.run()
    if success:
        analyzer.save_results()
    return success


def save_results(results, output_dir):
    """Compatibility shim for master.py."""
    pass


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Backlink Analyzer')
    parser.add_argument('--config-file', default='config/config.yaml')
    args = parser.parse_args()

    config = load_config(args.config_file)
    analyzer = BacklinkAnalyzer(config)
    success = analyzer.run()
    if success:
        analyzer.save_results()
