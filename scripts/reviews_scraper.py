#!/usr/bin/env python3
"""
Google Reviews Scraper
Scrapes reviews for competitors from Google Maps
"""

import time
import json
import re
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pandas as pd

from config_loader import load_config, get_competitor_names, get_data_dir, ensure_directories


class ReviewsScraper:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.driver = None
        self.wait = None
        self.output_dir = get_data_dir() / "reviews"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.all_reviews = []

    def connect_to_session(self):
        """Connect to existing Chrome session"""
        port = self.config.get('semrush', {}).get('chrome_debug_port', 9222)
        print(f"🔌 Connecting to Chrome on port {port}...")

        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{port}")

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.wait = WebDriverWait(self.driver, 20)
            print("✅ Connected!")
            return True
        except:
            return self.setup_new_driver()

    def setup_new_driver(self):
        """Setup new Chrome driver if session fails"""
        print("🚀 Starting new Chrome instance...")
        chrome_options = Options()
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)
        return True

    def search_google_maps(self, query):
        """Search Google Maps for a business"""
        print(f"🔍 Searching: {query}")
        search_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        self.driver.get(search_url)
        time.sleep(4)
        return True

    def click_first_result(self):
        """Click on first search result"""
        try:
            results = self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "[role='feed'] > div"))
            )
            if results:
                results[0].click()
                time.sleep(3)
                return True
        except Exception as e:
            print(f"No results: {e}")
        return False

    def open_reviews_panel(self):
        """Open reviews panel"""
        selectors = [
            "button[aria-label*='Reviews']",
            "[data-tab-index='1']",
            "button[jsaction*='reviews']",
            "[role='tab'][data-tab-index='1']"
        ]

        for selector in selectors:
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                btn.click()
                time.sleep(3)
                return True
            except:
                continue

        # Try clicking star rating area
        try:
            rating = self.driver.find_element(By.CSS_SELECTOR, "[role='img'][aria-label*='stars']")
            rating.click()
            time.sleep(3)
            return True
        except:
            pass

        return False

    def scroll_reviews(self, scroll_count=None):
        """Scroll to load more reviews"""
        if scroll_count is None:
            scroll_count = self.config.get('google_reviews', {}).get('max_scroll_count', 15)

        scrollable_selectors = [
            "[role='feed']",
            ".m6QErb.DxyBCb",
            "[class*='review-dialog-list']",
            "div[tabindex='-1']"
        ]

        scrollable = None
        for selector in scrollable_selectors:
            try:
                scrollable = self.driver.find_element(By.CSS_SELECTOR, selector)
                break
            except:
                continue

        if scrollable:
            for i in range(scroll_count):
                self.driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight",
                    scrollable
                )
                time.sleep(1.5)
                print(f"   Scrolling... {i+1}/{scroll_count}")

    def expand_reviews(self):
        """Click 'More' buttons to expand reviews"""
        try:
            more_buttons = self.driver.find_elements(By.CSS_SELECTOR,
                "button[aria-label='See more'], [class*='expand']")
            for btn in more_buttons:
                try:
                    btn.click()
                    time.sleep(0.3)
                except:
                    pass
        except:
            pass

    def extract_reviews(self, brand_name, location):
        """Extract all visible reviews"""
        reviews = []

        review_selectors = [
            "[data-review-id]",
            "[class*='review'][class*='container']",
            ".jftiEf",
            "[jsaction*='review']"
        ]

        review_elements = []
        for selector in review_selectors:
            try:
                review_elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if review_elements:
                    break
            except:
                continue

        print(f"   Found {len(review_elements)} review elements")

        for elem in review_elements:
            try:
                review_data = {
                    "brand": brand_name,
                    "location": location,
                    "scraped_at": datetime.now().isoformat()
                }

                # Extract rating
                try:
                    rating_elem = elem.find_element(By.CSS_SELECTOR,
                        "[role='img'][aria-label*='star']")
                    rating_text = rating_elem.get_attribute("aria-label")
                    if rating_text:
                        match = re.search(r'(\d+)', rating_text)
                        if match:
                            review_data["rating"] = int(match.group(1))
                except:
                    review_data["rating"] = None

                # Extract text
                try:
                    text_selectors = [".wiI7pd", "[class*='review-text']", "[data-review-text]"]
                    for sel in text_selectors:
                        try:
                            text_elem = elem.find_element(By.CSS_SELECTOR, sel)
                            review_data["text"] = text_elem.text.strip()
                            break
                        except:
                            continue
                    if "text" not in review_data:
                        review_data["text"] = elem.text[:1000]
                except:
                    review_data["text"] = ""

                # Extract reviewer name
                try:
                    name_elem = elem.find_element(By.CSS_SELECTOR, "[class*='author'], .d4r55")
                    review_data["reviewer"] = name_elem.text.strip()
                except:
                    review_data["reviewer"] = "Anonymous"

                # Extract date
                try:
                    date_elem = elem.find_element(By.CSS_SELECTOR, "[class*='date'], .rsqaWe")
                    review_data["date"] = date_elem.text.strip()
                except:
                    review_data["date"] = "Unknown"

                if review_data.get("text") and len(review_data["text"]) > 10:
                    reviews.append(review_data)

            except Exception as e:
                continue

        return reviews

    def build_search_queries(self):
        """Build search queries from config"""
        queries = []
        competitors = self.config.get('competitors', [])
        locations = self.config.get('google_reviews', {}).get('locations', ['New York', 'Los Angeles'])
        store_types = self.config.get('google_reviews', {}).get('store_types', ['store'])

        for comp in competitors:
            name = comp.get('name', comp.get('domain', '').split('.')[0])
            for location in locations:
                queries.append({
                    "brand": name,
                    "query": f"{name} store {location}"
                })
            for store_type in store_types:
                if store_type != 'store':
                    queries.append({
                        "brand": name,
                        "query": f"{name} {store_type}"
                    })

        return queries

    def scrape_reviews(self, brand, query):
        """Scrape reviews for a single query"""
        print(f"\n{'='*50}")
        print(f"🏪 {query}")
        print("=" * 50)

        reviews = []
        try:
            self.search_google_maps(query)
            time.sleep(2)

            if self.click_first_result():
                time.sleep(2)

                if self.open_reviews_panel():
                    self.scroll_reviews()
                    self.expand_reviews()

                    reviews = self.extract_reviews(brand, query)
                    print(f"   ✅ Extracted {len(reviews)} reviews")
                else:
                    print("   ⚠️ Could not open reviews panel")
            else:
                print("   ⚠️ No results found")

        except Exception as e:
            print(f"   ❌ Error: {e}")

        return reviews

    def run_full_scrape(self):
        """Run complete scrape for all competitors"""
        print("=" * 60)
        print("🚀 Google Reviews Scraper")
        print("=" * 60)

        ensure_directories()

        if not self.connect_to_session():
            return []

        queries = self.build_search_queries()
        all_reviews = []

        for q in queries:
            reviews = self.scrape_reviews(q['brand'], q['query'])
            all_reviews.extend(reviews)
            time.sleep(2)

        # Save results
        if all_reviews:
            # CSV
            df = pd.DataFrame(all_reviews)
            csv_file = self.output_dir / "all_reviews.csv"
            df.to_csv(csv_file, index=False)
            print(f"\n💾 Saved {len(all_reviews)} reviews to {csv_file}")

            # JSON
            json_file = self.output_dir / "all_reviews.json"
            with open(json_file, 'w') as f:
                json.dump(all_reviews, f, indent=2)

            # Summary
            print("\n📈 Reviews by Brand:")
            print(df.groupby("brand").size())

        print("\n" + "=" * 60)
        print("✅ SCRAPING COMPLETE!")
        print("=" * 60)

        return all_reviews


def main():
    scraper = ReviewsScraper()
    scraper.run_full_scrape()


if __name__ == "__main__":
    main()
