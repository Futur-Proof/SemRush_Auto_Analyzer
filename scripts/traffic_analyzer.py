#!/usr/bin/env python3
"""
Traffic Metrics Analyzer
Captures detailed traffic metrics, keyword graphs, and channel data from SEMrush
"""

import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options

from config_loader import load_config, get_competitor_domains, get_output_dir, ensure_directories


class TrafficAnalyzer:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.driver = None
        self.wait = None
        self.output_dir = get_output_dir() / "screenshots" / "traffic"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def connect_to_session(self):
        """Connect to existing Chrome session"""
        port = self.config.get('semrush', {}).get('chrome_debug_port', 9222)
        print(f"🔌 Connecting to Chrome on port {port}...")

        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 30)
            print("✅ Connected!")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    def close_popups(self):
        """Close any modal popups"""
        try:
            close_btns = self.driver.find_elements(By.CSS_SELECTOR,
                "[aria-label='Close'], .modal-close, button[class*='close']")
            for btn in close_btns:
                try:
                    btn.click()
                    time.sleep(0.5)
                except:
                    pass
        except:
            pass

    def save_screenshot(self, name):
        """Save screenshot"""
        filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = self.output_dir / filename
        self.driver.save_screenshot(str(path))
        print(f"📸 {path}")
        return path

    def capture_traffic_overview(self, domain):
        """Capture traffic overview with historical graphs"""
        print(f"\n📈 Traffic Overview: {domain}")

        url = f"https://www.semrush.com/analytics/traffic/overview/?q={domain}"
        self.driver.get(url)
        time.sleep(7)
        self.close_popups()

        # Main overview
        self.save_screenshot(f"traffic_overview_{domain.replace('.', '_')}")

        # Channels
        self.driver.execute_script("window.scrollTo(0, 600)")
        time.sleep(2)
        self.save_screenshot(f"traffic_channels_{domain.replace('.', '_')}")

        # Geographic
        self.driver.execute_script("window.scrollTo(0, 1200)")
        time.sleep(2)
        self.save_screenshot(f"traffic_geo_{domain.replace('.', '_')}")

    def capture_traffic_sources(self, domain):
        """Capture traffic sources breakdown"""
        print(f"\n📊 Traffic Sources: {domain}")

        url = f"https://www.semrush.com/analytics/traffic/traffic-sources/?q={domain}"
        self.driver.get(url)
        time.sleep(7)
        self.close_popups()

        self.save_screenshot(f"sources_{domain.replace('.', '_')}")

        self.driver.execute_script("window.scrollTo(0, 500)")
        time.sleep(2)
        self.save_screenshot(f"sources_detail_{domain.replace('.', '_')}")

    def capture_traffic_journey(self, domain):
        """Capture traffic journey / user flow"""
        print(f"\n🔄 Traffic Journey: {domain}")

        url = f"https://www.semrush.com/analytics/traffic/traffic-journey/?q={domain}"
        self.driver.get(url)
        time.sleep(7)
        self.close_popups()

        self.save_screenshot(f"journey_{domain.replace('.', '_')}")

    def capture_historical_data(self, domain):
        """Capture historical traffic data"""
        print(f"\n📅 Historical Data: {domain}")

        url = f"https://www.semrush.com/analytics/overview/?q={domain}&searchType=domain"
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()

        # Try to select longer time range
        try:
            time_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button")
            for btn in time_buttons:
                if btn.text in ["2Y", "All time", "All", "Max"]:
                    btn.click()
                    time.sleep(3)
                    break
        except:
            pass

        self.save_screenshot(f"historical_{domain.replace('.', '_')}")

        self.driver.execute_script("window.scrollTo(0, 400)")
        time.sleep(2)
        self.save_screenshot(f"historical_graph_{domain.replace('.', '_')}")

    def capture_top_keywords(self, domain):
        """Capture top organic keywords"""
        print(f"\n🏆 Top Keywords: {domain}")
        db = self.config.get('semrush', {}).get('database', 'us')

        url = f"https://www.semrush.com/analytics/organic/positions/?db={db}&q={domain}&searchType=domain"
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()

        # Try to sort by traffic
        try:
            traffic_header = self.driver.find_element(By.XPATH,
                "//th[contains(., 'Traffic')] | //button[contains(., 'Traffic')]")
            traffic_header.click()
            time.sleep(2)
        except:
            pass

        self.save_screenshot(f"top_keywords_{domain.replace('.', '_')}")

        self.driver.execute_script("window.scrollTo(0, 400)")
        time.sleep(1)
        self.save_screenshot(f"top_keywords_more_{domain.replace('.', '_')}")

    def capture_market_keywords(self):
        """Capture market keyword research"""
        print(f"\n🎯 Market Keywords...")

        keywords = self.config.get('market_keywords', [])
        db = self.config.get('semrush', {}).get('database', 'us')

        for kw in keywords:
            url = f"https://www.semrush.com/analytics/keywordmagic/?q={kw.replace(' ', '%20')}&db={db}"
            self.driver.get(url)
            time.sleep(6)
            self.close_popups()

            safe_name = kw.replace(' ', '_')
            self.save_screenshot(f"market_kw_{safe_name}")

            self.driver.execute_script("window.scrollTo(0, 400)")
            time.sleep(1)
            self.save_screenshot(f"market_kw_{safe_name}_list")

    def run_full_analysis(self):
        """Run complete traffic analysis"""
        print("=" * 60)
        print("🚀 Traffic Metrics Analysis")
        print("=" * 60)

        ensure_directories()

        if not self.connect_to_session():
            return False

        competitors = get_competitor_domains(self.config)

        for domain in competitors:
            print(f"\n{'#'*60}")
            print(f"# {domain}")
            print("#" * 60)

            self.capture_traffic_overview(domain)
            time.sleep(2)

            self.capture_traffic_sources(domain)
            time.sleep(2)

            self.capture_traffic_journey(domain)
            time.sleep(2)

            self.capture_top_keywords(domain)
            time.sleep(2)

            self.capture_historical_data(domain)
            time.sleep(3)

        # Market analysis
        print(f"\n{'#'*60}")
        print("# MARKET ANALYSIS")
        print("#" * 60)

        self.capture_market_keywords()

        # Count files
        files = list(self.output_dir.glob("*.png"))
        print("\n" + "=" * 60)
        print(f"✅ ANALYSIS COMPLETE! {len(files)} screenshots saved")
        print("=" * 60)
        print(f"📁 Output: {self.output_dir}")

        return True


def main():
    analyzer = TrafficAnalyzer()
    analyzer.run_full_analysis()


if __name__ == "__main__":
    main()
