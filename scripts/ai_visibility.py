#!/usr/bin/env python3
"""
AI Visibility Analyzer

Tracks brand presence in AI-generated search results using Semrush's AI
visibility tools via Selenium browser automation. Also generates test prompts
and classifies keywords by AI Overview trigger likelihood.

Output:
  data/semrush/ai_visibility_data.json   — AI visibility analysis
  data/semrush/ai_visibility_report.txt  — Human-readable report
"""

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


class AIVisibilityAnalyzer:
    """Scrapes AI visibility data from Semrush and generates analysis."""

    def __init__(self, config_path='config/config.yaml'):
        if isinstance(config_path, dict):
            self.config = config_path
        else:
            self.config = load_config(config_path)
        ensure_directories(self.config)

        self.data_dir = get_data_dir(self.config)
        self.output_dir = get_output_dir(self.config)
        self.screenshots_dir = os.path.join(self.output_dir, 'screenshots', 'ai_visibility')
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

    # ── Semrush AI Visibility Scraping ──

    def scrape_ai_visibility_overview(self, domain):
        """Scrape AI Visibility Overview page."""
        print(f"    AI Visibility Overview: {domain}")
        url = f"https://www.semrush.com/ai-seo/overview/?q={domain}"
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()

        data = {
            'ai_mentions': 0,
            'ai_visibility_score': 0,
            'prompts_tracked': 0,
            'platforms': [],
            'scraped': True
        }

        # Extract overview metrics
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR,
                ".srf-report-card__data, [class*='reportCard'] [class*='value'], "
                "[class*='metric-value'], [class*='overview'] [class*='value']")
            values = [c.text.strip() for c in cards if c.text.strip()]
            if len(values) >= 1:
                data['ai_visibility_score'] = self.parse_number(values[0])
            if len(values) >= 2:
                data['ai_mentions'] = self.parse_number(values[1])
            if len(values) >= 3:
                data['prompts_tracked'] = self.parse_number(values[2])
        except:
            pass

        # Try to extract platform breakdown
        try:
            platform_els = self.driver.find_elements(By.CSS_SELECTOR,
                "[class*='platform'], [class*='source'] [class*='name']")
            for el in platform_els:
                text = el.text.strip()
                if text and len(text) > 1:
                    data['platforms'].append(text)
        except:
            pass

        self.take_screenshot(f"ai_overview_{domain.replace('.', '_')}")

        # Scroll for more data
        self.driver.execute_script("window.scrollTo(0, 600)")
        time.sleep(2)
        self.take_screenshot(f"ai_overview_{domain.replace('.', '_')}_detail")

        return data

    def scrape_ai_competitor_research(self, domain):
        """Scrape AI Competitor Research page."""
        print(f"    AI Competitor Research: {domain}")
        url = f"https://www.semrush.com/ai-seo/competitor-research/?q={domain}"
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()

        competitors_data = []

        # Try to extract competitor table
        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")[:20]
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 2:
                    continue
                comp_domain = ''
                for cell in cells[:2]:
                    text = cell.text.strip().split('\n')[0]
                    if '.' in text and len(text) > 3:
                        comp_domain = text
                        break
                if comp_domain:
                    cell_texts = [c.text.strip() for c in cells]
                    competitors_data.append({
                        'domain': comp_domain,
                        'raw_data': cell_texts[:5]
                    })
        except:
            pass

        self.take_screenshot(f"ai_competitors_{domain.replace('.', '_')}")
        return competitors_data

    def scrape_ai_prompt_research(self, domain):
        """Scrape AI Prompt Research page."""
        print(f"    AI Prompt Research: {domain}")
        url = f"https://www.semrush.com/ai-seo/prompt-research/?q={domain}"
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()

        prompts = []

        # Try to extract prompt list
        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")[:30]
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 2:
                    continue
                prompt_text = cells[0].text.strip()
                if prompt_text and len(prompt_text) > 5:
                    prompts.append({
                        'prompt': prompt_text,
                        'raw_data': [c.text.strip() for c in cells[:4]]
                    })
        except:
            pass

        self.take_screenshot(f"ai_prompts_{domain.replace('.', '_')}")

        # Scroll for more
        self.driver.execute_script("window.scrollTo(0, 500)")
        time.sleep(2)
        self.take_screenshot(f"ai_prompts_{domain.replace('.', '_')}_more")

        return prompts

    def scrape_ai_brand_performance(self, domain):
        """Scrape AI Brand Performance page."""
        print(f"    AI Brand Performance: {domain}")
        url = f"https://www.semrush.com/ai-seo/brand-performance/?q={domain}"
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()

        data = {'scraped': True}

        # Extract any visible metrics
        try:
            cards = self.driver.find_elements(By.CSS_SELECTOR,
                ".srf-report-card__data, [class*='metric-value']")
            values = [c.text.strip() for c in cards if c.text.strip()]
            data['raw_metrics'] = values[:10]
        except:
            data['raw_metrics'] = []

        self.take_screenshot(f"ai_brand_{domain.replace('.', '_')}")
        return data

    def scrape_ai_growth_actions(self, domain):
        """Scrape AI Growth Actions page."""
        print(f"    AI Growth Actions: {domain}")
        url = f"https://www.semrush.com/ai-seo/growth-actions/?q={domain}"
        self.driver.get(url)
        time.sleep(6)
        self.close_popups()

        actions = []

        # Try to extract action items
        try:
            # Look for cards or list items with recommendations
            action_els = self.driver.find_elements(By.CSS_SELECTOR,
                "[class*='action'], [class*='recommendation'], "
                "[class*='card'] h3, [class*='card'] h4, [class*='task'] [class*='title']")
            for el in action_els:
                text = el.text.strip()
                if text and len(text) > 5:
                    actions.append(text)
        except:
            pass

        self.take_screenshot(f"ai_actions_{domain.replace('.', '_')}")
        return actions

    # ── Config-Based Analysis (no Chrome needed) ──

    def build_ai_test_prompts(self):
        """Generate prompts to test AI visibility for the brand/industry."""
        target_name = self.config.get('target', {}).get('name', '')
        market_keywords = self.config.get('market_keywords', [])
        competitors = self.config.get('competitors', [])

        prompts = {
            'brand_direct': [
                f"What is {target_name}?",
                f"Tell me about {target_name}",
                f"Is {target_name} reliable?",
                f"{target_name} reviews",
            ],
            'category_discovery': [],
            'comparison': [],
            'recommendation': [],
            'how_to': [],
            'cost': []
        }

        top_keywords = market_keywords[:15]

        for kw in top_keywords[:5]:
            prompts['category_discovery'].append(f"What are the best {kw} companies?")
            prompts['category_discovery'].append(f"Who offers {kw}?")

        for kw in top_keywords[:3]:
            prompts['recommendation'].append(f"Recommend a good {kw} service")
            prompts['recommendation'].append(f"Which {kw} company should I use?")

        for comp in competitors[:3]:
            name = comp.get('name', comp.get('domain', ''))
            prompts['comparison'].append(f"{target_name} vs {name}")
            prompts['comparison'].append(f"Is {name} or {target_name} better?")

        for kw in top_keywords[:5]:
            prompts['how_to'].append(f"How does {kw} work?")
            prompts['cost'].append(f"How much does {kw} cost?")

        return prompts

    def analyze_ai_overview_keywords(self):
        """Classify market keywords by AI Overview trigger likelihood."""
        market_keywords = self.config.get('market_keywords', [])

        triggers = {
            'informational': [],
            'comparison': [],
            'cost': [],
            'recommendation': [],
            'transactional': []
        }

        for kw in market_keywords:
            kw_lower = kw.lower()
            if any(w in kw_lower for w in ['how', 'what', 'why', 'when', 'guide', 'tips']):
                triggers['informational'].append(kw)
            elif any(w in kw_lower for w in ['vs', 'versus', 'compare', 'difference']):
                triggers['comparison'].append(kw)
            elif any(w in kw_lower for w in ['cost', 'price', 'rate', 'how much', 'fee']):
                triggers['cost'].append(kw)
            elif any(w in kw_lower for w in ['best', 'top', 'recommend', 'review', 'reliable']):
                triggers['recommendation'].append(kw)
            else:
                triggers['transactional'].append(kw)

        return triggers

    def generate_recommendations(self, triggers):
        """Generate actionable AI visibility recommendations."""
        return [
            {
                'priority': 'high',
                'action': 'Create FAQ content targeting informational queries',
                'reason': (f"{len(triggers.get('informational', []))} keywords likely trigger AI Overviews. "
                          "FAQ-style content with clear answers increases AIO citation chances."),
                'keywords': triggers.get('informational', [])[:5]
            },
            {
                'priority': 'high',
                'action': 'Build comparison pages for competitor queries',
                'reason': (f"{len(triggers.get('comparison', []))} comparison keywords identified. "
                          "Detailed comparison content can capture AI Overview citations."),
                'keywords': triggers.get('comparison', [])[:5]
            },
            {
                'priority': 'medium',
                'action': 'Add structured pricing data (Schema.org)',
                'reason': (f"{len(triggers.get('cost', []))} cost-related queries found. "
                          "Structured data helps AI systems extract accurate pricing info."),
                'keywords': triggers.get('cost', [])[:5]
            },
            {
                'priority': 'medium',
                'action': 'Claim and optimize knowledge panels',
                'reason': ("Brand queries are increasingly answered by AI. Ensure Google Knowledge Panel "
                          "and Wikipedia presence are accurate and comprehensive.")
            },
            {
                'priority': 'medium',
                'action': 'Monitor AI chatbot responses',
                'reason': ("Regularly test prompts in ChatGPT, Perplexity, and Google AI Mode "
                          "to track brand mention frequency and accuracy.")
            },
            {
                'priority': 'low',
                'action': 'Use Semrush AI Visibility tools for ongoing tracking',
                'reason': ("Semrush offers AI Visibility Overview, Competitor Research, and Prompt Tracking "
                          "for systematic monitoring."),
                'tools': [
                    'AI Visibility Overview - Track brand mentions across AI platforms',
                    'Competitor Research - Compare AI visibility vs competitors',
                    'Prompt Research - Find prompts mentioning your brand',
                    'Brand Performance - Monitor brand perception in AI',
                    'Growth Actions - Get actionable AI visibility improvements',
                    'Prompt Tracking - Track specific prompts over time'
                ]
            }
        ]

    def run(self):
        """Run AI visibility analysis."""
        target_name = self.config.get('target', {}).get('name', '')
        target_domain = get_target_domain(self.config)

        print(f"\n{'='*60}")
        print(f"  AI VISIBILITY ANALYSIS")
        print(f"  Target: {target_name} ({target_domain})")
        print(f"{'='*60}")

        self.results = {
            'generated_at': datetime.now().isoformat(),
            'target': {'name': target_name, 'domain': target_domain},
            'semrush_data': {},
            'test_prompts': {},
            'ai_overview_keywords': {},
            'visibility_scores': {},
            'recommendations': []
        }

        # Step 1: Scrape Semrush AI Visibility pages
        has_chrome = self.connect_to_chrome()

        if has_chrome:
            print(f"\n  [1/4] Scraping Semrush AI Visibility tools...")

            self.results['semrush_data']['overview'] = \
                self.scrape_ai_visibility_overview(target_domain)
            time.sleep(2)

            self.results['semrush_data']['competitor_research'] = \
                self.scrape_ai_competitor_research(target_domain)
            time.sleep(2)

            self.results['semrush_data']['prompt_research'] = \
                self.scrape_ai_prompt_research(target_domain)
            time.sleep(2)

            self.results['semrush_data']['brand_performance'] = \
                self.scrape_ai_brand_performance(target_domain)
            time.sleep(2)

            self.results['semrush_data']['growth_actions'] = \
                self.scrape_ai_growth_actions(target_domain)
        else:
            print(f"\n  [1/4] Chrome not available - skipping Semrush scraping")
            print(f"         Running config-based analysis only")

        # Step 2: Generate test prompts (no Chrome needed)
        print(f"\n  [2/4] Generating AI test prompts...")
        prompts = self.build_ai_test_prompts()
        self.results['test_prompts'] = prompts
        total_prompts = sum(len(v) for v in prompts.values())
        print(f"    Generated {total_prompts} test prompts across {len(prompts)} categories")

        for cat, prompt_list in prompts.items():
            print(f"    {cat}: {len(prompt_list)} prompts")
            for p in prompt_list[:2]:
                print(f"      - {p}")
            if len(prompt_list) > 2:
                print(f"      ... +{len(prompt_list) - 2} more")

        # Step 3: Analyze AI Overview triggers
        print(f"\n  [3/4] Analyzing AI Overview keyword triggers...")
        triggers = self.analyze_ai_overview_keywords()
        self.results['ai_overview_keywords'] = triggers

        likelihood = {
            'informational': 'Very High (90%+)',
            'comparison': 'High (70-80%)',
            'cost': 'High (65-75%)',
            'recommendation': 'Medium (40-60%)',
            'transactional': 'Low (10-20%)'
        }

        print(f"\n    {'Category':<20} {'Count':>6} {'AIO Likelihood':>16}")
        print(f"    {'-'*45}")
        for cat, kws in triggers.items():
            print(f"    {cat:<20} {len(kws):>6} {likelihood.get(cat, ''):>16}")

        # Step 4: Generate recommendations
        print(f"\n  [4/4] Generating recommendations...")
        self.results['recommendations'] = self.generate_recommendations(triggers)
        print(f"    Generated {len(self.results['recommendations'])} recommendations")

        return True

    def save_results(self):
        """Save AI visibility analysis results."""
        semrush_dir = os.path.join(self.data_dir, 'semrush')

        # JSON
        json_path = os.path.join(semrush_dir, 'ai_visibility_data.json')
        with open(json_path, 'w') as f:
            json.dump(self.results, f, indent=2)
        print(f"\n  Saved: {json_path}")

        # Text report
        report_path = os.path.join(semrush_dir, 'ai_visibility_report.txt')
        with open(report_path, 'w') as f:
            f.write(f"AI VISIBILITY ANALYSIS REPORT\n")
            f.write(f"Generated: {self.results['generated_at']}\n")
            f.write(f"Target: {self.results['target']['name']} ({self.results['target']['domain']})\n")
            f.write(f"{'='*60}\n\n")

            # Semrush data summary
            sd = self.results.get('semrush_data', {})
            if sd.get('overview', {}).get('scraped'):
                ov = sd['overview']
                f.write("SEMRUSH AI VISIBILITY DATA\n")
                f.write("-" * 40 + "\n")
                f.write(f"AI Visibility Score: {ov.get('ai_visibility_score', 'N/A')}\n")
                f.write(f"AI Mentions: {ov.get('ai_mentions', 'N/A')}\n")
                f.write(f"Prompts Tracked: {ov.get('prompts_tracked', 'N/A')}\n\n")

            f.write("TEST PROMPTS\n")
            f.write("-" * 40 + "\n")
            for cat, prompt_list in self.results['test_prompts'].items():
                f.write(f"\n{cat.upper().replace('_', ' ')} ({len(prompt_list)} prompts):\n")
                for p in prompt_list:
                    f.write(f"  - {p}\n")

            f.write(f"\n\nAI OVERVIEW KEYWORD TRIGGERS\n")
            f.write("-" * 40 + "\n")
            for cat, kws in self.results['ai_overview_keywords'].items():
                f.write(f"\n{cat.upper()} ({len(kws)} keywords):\n")
                for kw in kws:
                    f.write(f"  - {kw}\n")

            f.write(f"\n\nRECOMMENDATIONS\n")
            f.write("-" * 40 + "\n")
            for i, rec in enumerate(self.results['recommendations'], 1):
                f.write(f"\n{i}. [{rec['priority'].upper()}] {rec['action']}\n")
                f.write(f"   {rec['reason']}\n")
                if 'keywords' in rec:
                    f.write(f"   Keywords: {', '.join(rec['keywords'])}\n")
                if 'tools' in rec:
                    f.write(f"   Tools:\n")
                    for tool in rec['tools']:
                        f.write(f"     - {tool}\n")

        print(f"  Saved: {report_path}")
        return [json_path, report_path]


def run_ai_visibility_analysis(config):
    """Entry point for master.py integration."""
    analyzer = AIVisibilityAnalyzer(config)
    success = analyzer.run()
    if success:
        analyzer.save_results()
    return success


def save_results(results, output_dir):
    """Compatibility shim for master.py."""
    pass


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='AI Visibility Analyzer')
    parser.add_argument('--config-file', default='config/config.yaml')
    args = parser.parse_args()

    config = load_config(args.config_file)
    analyzer = AIVisibilityAnalyzer(config)
    success = analyzer.run()
    if success:
        analyzer.save_results()
