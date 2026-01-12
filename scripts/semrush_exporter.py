#!/usr/bin/env python3
"""
SEMrush Data Exporter
Exports organic keywords, backlinks, traffic data, and competitor analysis
Uses existing logged-in Chrome session via remote debugging
"""

import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains

from config_loader import load_config, get_all_domains, get_target_domain, get_competitor_domains, get_output_dir, ensure_directories


class SEMrushExporter:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.driver = None
        self.wait = None
        self.output_dir = get_output_dir() / "screenshots" / "semrush"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def connect_to_session(self):
        """Connect to existing Chrome session via remote debugging"""
        port = self.config.get('semrush', {}).get('chrome_debug_port', 9222)
        print(f"🔌 Connecting to Chrome on port {port}...")

        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            print(f"✅ Connected! Current URL: {self.driver.current_url}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            print(f"\n💡 Make sure Chrome is running with remote debugging:")
            print(f"   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome --remote-debugging-port={port}")
            return False

    def close_popups(self):
        """Close any modal popups"""
        try:
            close_selectors = [
                "[aria-label='Close']",
                ".modal-close",
                "button[class*='close']",
                "[data-test='modal-close']"
            ]
            for selector in close_selectors:
                try:
                    btns = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for btn in btns:
                        btn.click()
                        time.sleep(0.5)
                except:
                    pass
        except:
            pass

    def save_screenshot(self, name):
        """Save screenshot with timestamp"""
        filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = self.output_dir / filename
        self.driver.save_screenshot(str(path))
        print(f"📸 {path}")
        return path

    def export_organic_keywords(self, domain):
        """Export organic keywords for a domain"""
        print(f"\n🔑 Organic Keywords: {domain}")
        db = self.config.get('semrush', {}).get('database', 'us')

        url = f"https://www.semrush.com/analytics/organic/positions/?db={db}&q={domain}&searchType=domain"
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()

        return self.save_screenshot(f"organic_{domain.replace('.', '_')}")

    def export_backlinks(self, domain):
        """Export backlinks data"""
        print(f"\n🔗 Backlinks: {domain}")

        url = f"https://www.semrush.com/analytics/backlinks/backlinks/?q={domain}&searchType=domain"
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()

        return self.save_screenshot(f"backlinks_{domain.replace('.', '_')}")

    def export_traffic_analytics(self, domain):
        """Export traffic analytics"""
        print(f"\n📈 Traffic Analytics: {domain}")

        url = f"https://www.semrush.com/analytics/traffic/overview/?q={domain}"
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()

        # Main view
        self.save_screenshot(f"traffic_{domain.replace('.', '_')}")

        # Scroll for more data
        self.driver.execute_script("window.scrollTo(0, 600)")
        time.sleep(2)
        self.save_screenshot(f"traffic_{domain.replace('.', '_')}_channels")

        # Geographic data
        self.driver.execute_script("window.scrollTo(0, 1200)")
        time.sleep(2)
        return self.save_screenshot(f"traffic_{domain.replace('.', '_')}_geo")

    def export_top_pages(self, domain):
        """Export top pages"""
        print(f"\n📄 Top Pages: {domain}")
        db = self.config.get('semrush', {}).get('database', 'us')

        url = f"https://www.semrush.com/analytics/organic/pages/?db={db}&q={domain}&searchType=domain"
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()

        return self.save_screenshot(f"pages_{domain.replace('.', '_')}")

    def export_competitors_organic(self, domain):
        """Export organic competitors"""
        print(f"\n🏆 Organic Competitors: {domain}")
        db = self.config.get('semrush', {}).get('database', 'us')

        url = f"https://www.semrush.com/analytics/organic/competitors/?db={db}&q={domain}&searchType=domain"
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()

        return self.save_screenshot(f"competitors_{domain.replace('.', '_')}")

    def export_keyword_gap(self):
        """Export keyword gap analysis between target and competitors"""
        print(f"\n🔍 Keyword Gap Analysis...")

        target = get_target_domain(self.config)
        competitors = get_competitor_domains(self.config)[:3]
        db = self.config.get('semrush', {}).get('database', 'us')

        if not target or not competitors:
            print("⚠️ Need target and competitors for gap analysis")
            return None

        comps_param = ",".join(competitors)
        url = f"https://www.semrush.com/analytics/keywordgap/?db={db}&q={target}&domains={comps_param}&searchType=domain"
        self.driver.get(url)
        time.sleep(8)
        self.close_popups()

        return self.save_screenshot("keyword_gap")

    def export_market_explorer(self):
        """Export market explorer / industry trends"""
        print(f"\n🌍 Market Explorer...")

        category = self.config.get('industry', {}).get('category', 'beauty-and-cosmetics')
        region = self.config.get('industry', {}).get('region', 'us')

        url = f"https://www.semrush.com/trends/overview/{region}/{category}"
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()

        self.save_screenshot("market_trends")

        # Scroll for more
        self.driver.execute_script("window.scrollTo(0, 800)")
        time.sleep(2)
        return self.save_screenshot("market_trends_2")

    def export_keyword_research(self):
        """Export keyword research for market keywords"""
        print(f"\n🎯 Keyword Research...")

        keywords = self.config.get('market_keywords', [])
        db = self.config.get('semrush', {}).get('database', 'us')

        for kw in keywords:
            print(f"   Researching: {kw}")
            url = f"https://www.semrush.com/analytics/keywordmagic/?q={kw.replace(' ', '%20')}&db={db}"
            self.driver.get(url)
            time.sleep(6)
            self.close_popups()

            safe_name = kw.replace(' ', '_')
            self.save_screenshot(f"keyword_{safe_name}")

            # Scroll for more keywords
            self.driver.execute_script("window.scrollTo(0, 400)")
            time.sleep(1)
            self.save_screenshot(f"keyword_{safe_name}_list")

    def run_full_export(self):
        """Run complete export for all domains"""
        print("=" * 60)
        print("🚀 SEMrush Data Export Pipeline")
        print("=" * 60)

        ensure_directories()

        if not self.connect_to_session():
            return False

        all_domains = get_all_domains(self.config)
        target = get_target_domain(self.config)

        for domain in all_domains:
            print(f"\n{'='*60}")
            print(f"📊 Processing: {domain}")
            print("=" * 60)

            self.export_organic_keywords(domain)
            time.sleep(2)

            self.export_backlinks(domain)
            time.sleep(2)

            self.export_top_pages(domain)
            time.sleep(2)

            self.export_competitors_organic(domain)
            time.sleep(2)

            # Traffic analytics (may require paid plan)
            self.export_traffic_analytics(domain)
            time.sleep(2)

        # Gap analysis
        self.export_keyword_gap()
        time.sleep(2)

        # Market trends
        self.export_market_explorer()
        time.sleep(2)

        # Keyword research
        self.export_keyword_research()

        print("\n" + "=" * 60)
        print("✅ EXPORT COMPLETE!")
        print("=" * 60)
        print(f"📁 Data saved to: {self.output_dir}")

        # List files
        files = list(self.output_dir.glob("*.png"))
        print(f"\n📊 Exported {len(files)} screenshots")

        return True


def main():
    exporter = SEMrushExporter()
    exporter.run_full_export()


if __name__ == "__main__":
    main()
