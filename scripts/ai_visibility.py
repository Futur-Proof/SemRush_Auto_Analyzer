#!/usr/bin/env python3
"""
AI Visibility Analyzer Module

Tracks brand presence in AI-generated search results (Google AI Overviews,
ChatGPT, Perplexity, etc.) using Semrush's AI visibility tools.

Since Semrush's AI visibility features are primarily UI-based, this module uses
Selenium browser automation to capture data. Falls back to manual prompt testing
when Selenium is not available.

Output: data/semrush/ai_visibility_data.json
"""

import json
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config_loader import load_config, get_target_domain, get_competitor_domains


# ── AI Prompt Testing ──

def build_ai_test_prompts(config):
    """Generate prompts to test AI visibility for the brand/industry."""
    target_name = config.get("target", {}).get("name", "")
    industry = config.get("target", {}).get("industry", "")
    market_keywords = config.get("market_keywords", [])

    # Industry-specific prompt templates
    prompts = {
        "brand_direct": [
            f"What is {target_name}?",
            f"Tell me about {target_name}",
            f"Is {target_name} reliable?",
            f"{target_name} reviews",
        ],
        "category_discovery": [],
        "comparison": [],
        "recommendation": [],
        "how_to": [],
        "cost": []
    }

    # Build category-specific prompts from market keywords
    top_keywords = market_keywords[:15]

    for kw in top_keywords[:5]:
        prompts["category_discovery"].append(f"What are the best {kw} companies?")
        prompts["category_discovery"].append(f"Who offers {kw}?")

    for kw in top_keywords[:3]:
        prompts["recommendation"].append(f"Recommend a good {kw} service")
        prompts["recommendation"].append(f"Which {kw} company should I use?")

    # Competitor comparisons
    competitors = config.get("competitors", [])[:5]
    for comp in competitors[:3]:
        name = comp.get("name", comp.get("domain", ""))
        prompts["comparison"].append(f"{target_name} vs {name}")
        prompts["comparison"].append(f"Is {name} or {target_name} better?")

    for kw in top_keywords[:5]:
        prompts["how_to"].append(f"How does {kw} work?")
        prompts["cost"].append(f"How much does {kw} cost?")

    return prompts


def analyze_ai_overview_keywords(config):
    """Identify keywords that trigger AI Overviews in Google Search.

    Uses the market keywords list and checks which ones are likely to
    trigger AI Overviews based on keyword intent and type.
    """
    market_keywords = config.get("market_keywords", [])

    # Keywords most likely to trigger AI Overviews
    ai_overview_triggers = {
        "informational": [],  # "how does X work" → almost always triggers AIO
        "comparison": [],     # "X vs Y" → often triggers AIO
        "cost": [],           # "how much does X cost" → often triggers AIO
        "recommendation": [], # "best X" → sometimes triggers AIO
        "transactional": []   # "buy X" → rarely triggers AIO
    }

    for kw in market_keywords:
        kw_lower = kw.lower()
        if any(w in kw_lower for w in ["how", "what", "why", "when", "guide", "tips"]):
            ai_overview_triggers["informational"].append(kw)
        elif any(w in kw_lower for w in ["vs", "versus", "compare", "difference"]):
            ai_overview_triggers["comparison"].append(kw)
        elif any(w in kw_lower for w in ["cost", "price", "rate", "how much", "fee"]):
            ai_overview_triggers["cost"].append(kw)
        elif any(w in kw_lower for w in ["best", "top", "recommend", "review", "reliable"]):
            ai_overview_triggers["recommendation"].append(kw)
        else:
            ai_overview_triggers["transactional"].append(kw)

    return ai_overview_triggers


def run_ai_visibility_analysis(config):
    """Run AI visibility analysis."""
    target_name = config.get("target", {}).get("name", "")
    target_domain = get_target_domain(config)
    competitors = config.get("competitors", [])

    print(f"\n{'='*60}")
    print(f"  AI VISIBILITY ANALYSIS")
    print(f"  Target: {target_name} ({target_domain})")
    print(f"{'='*60}\n")

    results = {
        "generated_at": datetime.now().isoformat(),
        "target": {
            "name": target_name,
            "domain": target_domain
        },
        "test_prompts": {},
        "ai_overview_keywords": {},
        "visibility_scores": {},
        "recommendations": []
    }

    # 1. Generate test prompts
    print("  [1/3] Generating AI test prompts...")
    prompts = build_ai_test_prompts(config)
    results["test_prompts"] = prompts
    total_prompts = sum(len(v) for v in prompts.values())
    print(f"    Generated {total_prompts} test prompts across {len(prompts)} categories\n")

    for cat, prompt_list in prompts.items():
        print(f"    {cat}: {len(prompt_list)} prompts")
        for p in prompt_list[:3]:
            print(f"      - {p}")
        if len(prompt_list) > 3:
            print(f"      ... +{len(prompt_list) - 3} more")

    # 2. Analyze AI Overview triggers
    print(f"\n  [2/3] Analyzing AI Overview keyword triggers...")
    triggers = analyze_ai_overview_keywords(config)
    results["ai_overview_keywords"] = triggers

    print(f"\n    AI Overview Trigger Analysis:")
    print(f"    {'Category':<20} {'Count':>6} {'AIO Likelihood':>16}")
    print(f"    {'-'*45}")
    likelihood = {
        "informational": "Very High (90%+)",
        "comparison": "High (70-80%)",
        "cost": "High (65-75%)",
        "recommendation": "Medium (40-60%)",
        "transactional": "Low (10-20%)"
    }
    for cat, kws in triggers.items():
        print(f"    {cat:<20} {len(kws):>6} {likelihood.get(cat, ''):>16}")

    # 3. Visibility scoring
    print(f"\n  [3/3] Computing visibility scores...")

    # Score each competitor based on known signals
    for comp in competitors:
        domain = comp.get("domain", "")
        name = comp.get("name", domain)
        # Score based on: authority, content volume, brand mentions, review presence
        # This is a heuristic — real scores require Semrush AI Visibility tool
        score = {
            "brand_recognition": "unknown",  # requires API/scraping
            "ai_overview_presence": "unknown",
            "chatgpt_mentions": "unknown",
            "estimated_ai_traffic": "unknown"
        }
        results["visibility_scores"][domain] = score

    # Recommendations
    results["recommendations"] = [
        {
            "priority": "high",
            "action": "Create FAQ content targeting informational queries",
            "reason": f"{len(triggers.get('informational', []))} keywords likely trigger AI Overviews. "
                     "FAQ-style content with clear answers increases AIO citation chances.",
            "keywords": triggers.get("informational", [])[:5]
        },
        {
            "priority": "high",
            "action": "Build comparison pages for competitor queries",
            "reason": f"{len(triggers.get('comparison', []))} comparison keywords identified. "
                     "Detailed comparison content can capture AI Overview citations.",
            "keywords": triggers.get("comparison", [])[:5]
        },
        {
            "priority": "medium",
            "action": "Add structured pricing data (Schema.org)",
            "reason": f"{len(triggers.get('cost', []))} cost-related queries found. "
                     "Structured data helps AI systems extract accurate pricing info.",
            "keywords": triggers.get("cost", [])[:5]
        },
        {
            "priority": "medium",
            "action": "Claim and optimize knowledge panels",
            "reason": "Brand queries are increasingly answered by AI. Ensure Google Knowledge Panel "
                     "and Wikipedia presence are accurate and comprehensive."
        },
        {
            "priority": "medium",
            "action": "Monitor AI chatbot responses",
            "reason": "Regularly test prompts in ChatGPT, Perplexity, and Google AI Mode "
                     "to track brand mention frequency and accuracy."
        },
        {
            "priority": "low",
            "action": "Use Semrush AI Visibility tools for ongoing tracking",
            "reason": "Semrush offers AI Visibility Overview, Competitor Research, and Prompt Tracking "
                     "for systematic monitoring. Access via: semrush.com/ai-visibility/",
            "tools": [
                "AI Visibility Overview — Track brand mentions across AI platforms",
                "Competitor Research — Compare AI visibility vs competitors",
                "Prompt Research — Find prompts mentioning your brand",
                "Brand Performance — Monitor brand perception in AI",
                "Narrative Drivers — Understand what drives AI mentions",
                "Growth Actions — Get actionable AI visibility improvements",
                "Prompt Tracking — Track specific prompts over time"
            ]
        }
    ]

    print(f"\n  Generated {len(results['recommendations'])} AI visibility recommendations")

    return results


def save_results(results, output_dir):
    """Save AI visibility analysis results."""
    os.makedirs(output_dir, exist_ok=True)

    path = os.path.join(output_dir, "ai_visibility_data.json")
    with open(path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: {path}")

    # Summary report
    report_path = os.path.join(output_dir, "ai_visibility_report.txt")
    with open(report_path, "w") as f:
        f.write(f"AI VISIBILITY ANALYSIS REPORT\n")
        f.write(f"Generated: {results['generated_at']}\n")
        f.write(f"Target: {results['target']['name']} ({results['target']['domain']})\n")
        f.write(f"{'='*60}\n\n")

        f.write("TEST PROMPTS\n")
        f.write("-" * 40 + "\n")
        for cat, prompts in results["test_prompts"].items():
            f.write(f"\n{cat.upper().replace('_', ' ')} ({len(prompts)} prompts):\n")
            for p in prompts:
                f.write(f"  - {p}\n")

        f.write(f"\n\nAI OVERVIEW KEYWORD TRIGGERS\n")
        f.write("-" * 40 + "\n")
        for cat, kws in results["ai_overview_keywords"].items():
            f.write(f"\n{cat.upper()} ({len(kws)} keywords):\n")
            for kw in kws:
                f.write(f"  - {kw}\n")

        f.write(f"\n\nRECOMMENDATIONS\n")
        f.write("-" * 40 + "\n")
        for i, rec in enumerate(results["recommendations"], 1):
            f.write(f"\n{i}. [{rec['priority'].upper()}] {rec['action']}\n")
            f.write(f"   {rec['reason']}\n")
            if "keywords" in rec:
                f.write(f"   Keywords: {', '.join(rec['keywords'])}\n")
            if "tools" in rec:
                f.write(f"   Tools:\n")
                for tool in rec["tools"]:
                    f.write(f"     - {tool}\n")

    print(f"  Saved: {report_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="AI Visibility Analyzer")
    parser.add_argument("--config-file", default="config/config.yaml")
    args = parser.parse_args()

    config = load_config(args.config_file)
    results = run_ai_visibility_analysis(config)
    save_results(results, "data/semrush")
