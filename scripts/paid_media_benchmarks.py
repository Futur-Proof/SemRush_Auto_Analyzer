#!/usr/bin/env python3
"""
Paid Media Benchmarks Analyzer
Extracts CPC, competitor ad spend, and paid keyword data from SEMrush
for new business projection modeling.
"""

import os
import sys
import time
import json
import csv
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

try:
    from scripts.config_loader import (
        load_config, get_target_domain, get_competitor_domains,
        get_all_domains, get_output_dir, get_data_dir, ensure_directories,
        get_target_name, get_competitor_names
    )
except ImportError:
    from config_loader import (
        load_config, get_target_domain, get_competitor_domains,
        get_all_domains, get_output_dir, get_data_dir, ensure_directories,
        get_target_name, get_competitor_names
    )


class PaidMediaBenchmarks:
    """Extracts paid media benchmarks from SEMrush for projection modeling."""

    def __init__(self, config_path='config/config.yaml'):
        self.config = load_config(config_path)
        ensure_directories(self.config)

        self.output_dir = get_output_dir(self.config)
        self.data_dir = get_data_dir(self.config)
        self.screenshots_dir = os.path.join(self.output_dir, 'screenshots', 'paid_media')
        self.exports_dir = os.path.join(self.data_dir, 'paid_media')

        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.exports_dir, exist_ok=True)

        self.driver = None
        self.database = self.config.get('semrush', {}).get('database', 'us')
        self.benchmarks = {
            'competitors': {},
            'keywords': {},
            'industry_averages': {},
            'extracted_at': datetime.now().isoformat()
        }

    def connect_to_chrome(self):
        """Connect to existing Chrome session with SEMrush logged in."""
        chrome_options = Options()
        debug_port = self.config.get('semrush', {}).get('chrome_debug_port', 9222)
        chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print(f"[OK] Connected to Chrome on port {debug_port}")
            return True
        except Exception as e:
            print(f"[ERROR] Could not connect to Chrome: {e}")
            print("Make sure Chrome is running with: --remote-debugging-port=9222")
            return False

    def close_popups(self):
        """Close any SEMrush popups or modals."""
        popup_selectors = [
            "button[data-test='close-modal']",
            ".srf-modal__close",
            "[aria-label='Close']",
            ".srf-popup__close",
            "button.close-button"
        ]
        for selector in popup_selectors:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for el in elements:
                    if el.is_displayed():
                        el.click()
                        time.sleep(0.5)
            except:
                pass

    def take_screenshot(self, name):
        """Take a screenshot with timestamp."""
        filename = f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = os.path.join(self.screenshots_dir, filename)
        self.driver.save_screenshot(filepath)
        print(f"  [Screenshot] {filename}")
        return filepath

    def extract_advertising_research(self, domain):
        """Extract paid advertising data for a domain from SEMrush."""
        print(f"\n[Advertising Research] {domain}")

        competitor_data = {
            'domain': domain,
            'paid_keywords': None,
            'paid_traffic': None,
            'paid_traffic_cost': None,
            'top_paid_keywords': [],
            'estimated_ad_spend': None
        }

        # Navigate to Advertising Research
        url = f"https://www.semrush.com/analytics/adwords/positions/?db={self.database}&q={domain}"
        self.driver.get(url)
        time.sleep(4)
        self.close_popups()

        # Take screenshot
        self.take_screenshot(f"advertising_research_{domain.replace('.', '_')}")

        # Try to extract key metrics
        try:
            # Paid keywords count
            metrics_selectors = [
                "[data-test='paid-keywords'] .srf-report-card__data",
                ".srf-report-card__data",
                "[class*='overview'] [class*='value']"
            ]
            for selector in metrics_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        values = [el.text for el in elements if el.text]
                        if len(values) >= 3:
                            competitor_data['paid_keywords'] = values[0] if values else None
                            competitor_data['paid_traffic'] = values[1] if len(values) > 1 else None
                            competitor_data['paid_traffic_cost'] = values[2] if len(values) > 2 else None
                        break
                except:
                    continue
        except Exception as e:
            print(f"  [Warning] Could not extract overview metrics: {e}")

        # Navigate to paid keyword positions for detailed CPC data
        time.sleep(2)
        self.take_screenshot(f"paid_keywords_{domain.replace('.', '_')}")

        # Try to extract top paid keywords with CPCs
        try:
            # Look for the keyword table
            table_selectors = [
                "table tbody tr",
                "[data-test='positions-table'] tr",
                ".srf-table tbody tr"
            ]
            for selector in table_selectors:
                try:
                    rows = self.driver.find_elements(By.CSS_SELECTOR, selector)[:10]  # Top 10
                    for row in rows:
                        cells = row.find_elements(By.TAG_NAME, "td")
                        if len(cells) >= 5:
                            keyword_data = {
                                'keyword': cells[0].text if cells else '',
                                'position': cells[1].text if len(cells) > 1 else '',
                                'volume': cells[2].text if len(cells) > 2 else '',
                                'cpc': cells[3].text if len(cells) > 3 else '',
                                'traffic_pct': cells[4].text if len(cells) > 4 else ''
                            }
                            if keyword_data['keyword']:
                                competitor_data['top_paid_keywords'].append(keyword_data)
                    if competitor_data['top_paid_keywords']:
                        break
                except:
                    continue
        except Exception as e:
            print(f"  [Warning] Could not extract keyword table: {e}")

        return competitor_data

    def extract_keyword_cpc(self, keywords):
        """Extract CPC data for target keywords from SEMrush Keyword Overview."""
        print(f"\n[Keyword CPC Analysis] Analyzing {len(keywords)} keywords")

        keyword_data = {}

        for keyword in keywords[:20]:  # Limit to 20 keywords to avoid rate limiting
            print(f"  Analyzing: {keyword}")

            url = f"https://www.semrush.com/analytics/keywordoverview/?db={self.database}&q={keyword.replace(' ', '%20')}"
            self.driver.get(url)
            time.sleep(3)
            self.close_popups()

            kw_info = {
                'keyword': keyword,
                'volume': None,
                'cpc': None,
                'competition': None,
                'trend': None
            }

            try:
                # Try to extract keyword metrics
                metric_selectors = [
                    "[data-test='keyword-overview'] .srf-report-card__data",
                    ".srf-report-card__data",
                    "[class*='metric'] [class*='value']"
                ]
                for selector in metric_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        values = [el.text for el in elements if el.text]
                        if values:
                            kw_info['volume'] = values[0] if values else None
                            kw_info['cpc'] = values[1] if len(values) > 1 else None
                            kw_info['competition'] = values[2] if len(values) > 2 else None
                            break
                    except:
                        continue
            except Exception as e:
                print(f"    [Warning] Could not extract metrics: {e}")

            keyword_data[keyword] = kw_info
            time.sleep(1)  # Rate limiting

        # Take one screenshot of keyword overview
        self.take_screenshot("keyword_cpc_overview")

        return keyword_data

    def extract_pla_data(self, domain):
        """Extract Product Listing Ads (PLA) data for e-commerce competitors."""
        print(f"\n[PLA Research] {domain}")

        url = f"https://www.semrush.com/analytics/pla/positions/?db={self.database}&q={domain}"
        self.driver.get(url)
        time.sleep(4)
        self.close_popups()

        self.take_screenshot(f"pla_research_{domain.replace('.', '_')}")

        pla_data = {
            'domain': domain,
            'pla_keywords': None,
            'products': []
        }

        # Try to extract PLA metrics
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, ".srf-report-card__data")
            values = [el.text for el in elements if el.text]
            if values:
                pla_data['pla_keywords'] = values[0]
        except:
            pass

        return pla_data

    def calculate_industry_averages(self):
        """Calculate average CPCs and metrics across all analyzed competitors."""
        print("\n[Calculating Industry Averages]")

        all_cpcs = []
        all_volumes = []

        # Collect CPCs from competitor keyword data
        for domain, data in self.benchmarks['competitors'].items():
            for kw in data.get('top_paid_keywords', []):
                try:
                    cpc_str = kw.get('cpc', '').replace('$', '').replace(',', '')
                    if cpc_str:
                        all_cpcs.append(float(cpc_str))
                except:
                    pass

        # Collect from keyword analysis
        for kw, data in self.benchmarks['keywords'].items():
            try:
                cpc_str = str(data.get('cpc', '')).replace('$', '').replace(',', '')
                if cpc_str:
                    all_cpcs.append(float(cpc_str))
                vol_str = str(data.get('volume', '')).replace(',', '').replace('K', '000').replace('M', '000000')
                if vol_str and vol_str.replace('.', '').isdigit():
                    all_volumes.append(float(vol_str))
            except:
                pass

        self.benchmarks['industry_averages'] = {
            'avg_cpc': sum(all_cpcs) / len(all_cpcs) if all_cpcs else None,
            'min_cpc': min(all_cpcs) if all_cpcs else None,
            'max_cpc': max(all_cpcs) if all_cpcs else None,
            'median_cpc': sorted(all_cpcs)[len(all_cpcs)//2] if all_cpcs else None,
            'avg_volume': sum(all_volumes) / len(all_volumes) if all_volumes else None,
            'total_keywords_analyzed': len(self.benchmarks['keywords']),
            'total_competitors_analyzed': len(self.benchmarks['competitors'])
        }

        print(f"  Average CPC: ${self.benchmarks['industry_averages']['avg_cpc']:.2f}" if self.benchmarks['industry_averages']['avg_cpc'] else "  Average CPC: N/A")
        print(f"  CPC Range: ${self.benchmarks['industry_averages']['min_cpc']:.2f} - ${self.benchmarks['industry_averages']['max_cpc']:.2f}" if self.benchmarks['industry_averages']['min_cpc'] else "  CPC Range: N/A")

    def save_benchmarks(self):
        """Save all benchmark data to JSON and CSV."""
        # Save full JSON
        json_path = os.path.join(self.exports_dir, 'paid_media_benchmarks.json')
        with open(json_path, 'w') as f:
            json.dump(self.benchmarks, f, indent=2)
        print(f"\n[Saved] {json_path}")

        # Save keyword CPCs to CSV
        csv_path = os.path.join(self.exports_dir, 'keyword_cpcs.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Keyword', 'Volume', 'CPC', 'Competition'])
            for kw, data in self.benchmarks['keywords'].items():
                writer.writerow([
                    kw,
                    data.get('volume', ''),
                    data.get('cpc', ''),
                    data.get('competition', '')
                ])
        print(f"[Saved] {csv_path}")

        # Save competitor summary to CSV
        csv_path = os.path.join(self.exports_dir, 'competitor_paid_summary.csv')
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Domain', 'Paid Keywords', 'Paid Traffic', 'Est. Ad Spend', 'Top Keyword', 'Top CPC'])
            for domain, data in self.benchmarks['competitors'].items():
                top_kw = data.get('top_paid_keywords', [{}])[0] if data.get('top_paid_keywords') else {}
                writer.writerow([
                    domain,
                    data.get('paid_keywords', ''),
                    data.get('paid_traffic', ''),
                    data.get('paid_traffic_cost', ''),
                    top_kw.get('keyword', ''),
                    top_kw.get('cpc', '')
                ])
        print(f"[Saved] {csv_path}")

        # Save industry averages summary
        summary_path = os.path.join(self.exports_dir, 'industry_benchmarks_summary.txt')
        with open(summary_path, 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("PAID MEDIA BENCHMARK SUMMARY\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("=" * 60 + "\n\n")

            f.write("INDUSTRY AVERAGES:\n")
            f.write("-" * 40 + "\n")
            avgs = self.benchmarks['industry_averages']
            f.write(f"Average CPC: ${avgs.get('avg_cpc', 0):.2f}\n" if avgs.get('avg_cpc') else "Average CPC: N/A\n")
            f.write(f"Median CPC: ${avgs.get('median_cpc', 0):.2f}\n" if avgs.get('median_cpc') else "Median CPC: N/A\n")
            f.write(f"CPC Range: ${avgs.get('min_cpc', 0):.2f} - ${avgs.get('max_cpc', 0):.2f}\n" if avgs.get('min_cpc') else "CPC Range: N/A\n")
            f.write(f"Competitors Analyzed: {avgs.get('total_competitors_analyzed', 0)}\n")
            f.write(f"Keywords Analyzed: {avgs.get('total_keywords_analyzed', 0)}\n")

            f.write("\n\nCOMPETITOR PAID MEDIA OVERVIEW:\n")
            f.write("-" * 40 + "\n")
            for domain, data in self.benchmarks['competitors'].items():
                f.write(f"\n{domain}:\n")
                f.write(f"  Paid Keywords: {data.get('paid_keywords', 'N/A')}\n")
                f.write(f"  Paid Traffic: {data.get('paid_traffic', 'N/A')}\n")
                f.write(f"  Est. Monthly Spend: {data.get('paid_traffic_cost', 'N/A')}\n")

        print(f"[Saved] {summary_path}")

    def run(self):
        """Run the full paid media benchmark analysis."""
        print("\n" + "=" * 60)
        print("PAID MEDIA BENCHMARKS ANALYZER")
        print("=" * 60)

        if not self.connect_to_chrome():
            return False

        try:
            # Get competitor domains
            competitors = get_competitor_domains(self.config)
            print(f"\nAnalyzing {len(competitors)} competitors...")

            # Extract advertising research for each competitor
            for domain in competitors:
                data = self.extract_advertising_research(domain)
                self.benchmarks['competitors'][domain] = data

                # Also get PLA data for e-commerce
                pla_data = self.extract_pla_data(domain)
                self.benchmarks['competitors'][domain]['pla'] = pla_data

                time.sleep(2)

            # Extract CPC data for market keywords
            market_keywords = self.config.get('market_keywords', [])
            if market_keywords:
                self.benchmarks['keywords'] = self.extract_keyword_cpc(market_keywords)

            # Calculate industry averages
            self.calculate_industry_averages()

            # Save all data
            self.save_benchmarks()

            print("\n" + "=" * 60)
            print("PAID MEDIA ANALYSIS COMPLETE")
            print("=" * 60)

            return True

        except Exception as e:
            print(f"\n[ERROR] Analysis failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point."""
    import argparse
    parser = argparse.ArgumentParser(description='Extract paid media benchmarks from SEMrush')
    parser.add_argument('--config', type=str, default='config/config.yaml',
                        help='Path to configuration file')
    args = parser.parse_args()

    analyzer = PaidMediaBenchmarks(args.config)
    success = analyzer.run()

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())
