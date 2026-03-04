#!/usr/bin/env python3
"""
Keyword Intelligence Module

Extracts keyword metrics (Volume, KD, CPC, Intent, Trend) from Semrush API
and competitor keyword gap analysis. Outputs structured JSON for dashboard integration.

Supports both:
  - Semrush API (api.semrush.com) for programmatic keyword data
  - Selenium browser automation for data not available via API

Output: data/semrush/keyword_market_data.json
"""

import csv
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime

# Add parent directory for config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config_loader import load_config, get_target_domain, get_competitor_domains


# ── Semrush API helpers ──

def semrush_api_call(params, api_key, base_url="https://api.semrush.com/"):
    """Make a Semrush API call and return parsed CSV rows."""
    params["key"] = api_key
    url = base_url + "?" + urllib.parse.urlencode(params)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SemrushAutoAnalyzer/2.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(text), delimiter=";")
        return list(reader)
    except Exception as e:
        print(f"    API error ({params.get('type', '?')}): {e}")
        return []


def get_keyword_overview(keyword, database, api_key):
    """Get keyword metrics: volume, KD, CPC, competition, intent."""
    rows = semrush_api_call({
        "type": "phrase_this",
        "phrase": keyword,
        "database": database,
        "export_columns": "Ph,Nq,Kd,Cp,Co,Nr,In,Td"
    }, api_key)
    if rows:
        r = rows[0]
        return {
            "keyword": r.get("Keyword", keyword),
            "volume": int(r.get("Search Volume", 0) or 0),
            "kd": int(r.get("Keyword Difficulty Index", 0) or 0),
            "cpc": round(float(r.get("CPC", 0) or 0), 2),
            "competition": round(float(r.get("Competition", 0) or 0), 4),
            "results": int(r.get("Number of Results", 0) or 0),
            "intent": map_intent(r.get("Intent", "")),
            "trend": r.get("Trends", "")
        }
    return None


def get_keyword_related(keyword, database, api_key, limit=50):
    """Get related keywords with metrics."""
    rows = semrush_api_call({
        "type": "phrase_related",
        "phrase": keyword,
        "database": database,
        "export_columns": "Ph,Nq,Kd,Cp,Co,Nr,In",
        "display_limit": str(limit)
    }, api_key)
    results = []
    for r in rows:
        results.append({
            "keyword": r.get("Keyword", ""),
            "volume": int(r.get("Search Volume", 0) or 0),
            "kd": int(r.get("Keyword Difficulty Index", 0) or 0),
            "cpc": round(float(r.get("CPC", 0) or 0), 2),
            "competition": round(float(r.get("Competition", 0) or 0), 4),
            "intent": map_intent(r.get("Intent", ""))
        })
    return results


def get_domain_organic_keywords(domain, database, api_key, limit=500):
    """Get a domain's top organic keywords."""
    rows = semrush_api_call({
        "type": "domain_organic",
        "domain": domain,
        "database": database,
        "export_columns": "Ph,Po,Nq,Kd,Cp,Ur,Tr,Tc",
        "display_limit": str(limit),
        "display_sort": "tr_desc"
    }, api_key)
    results = []
    for r in rows:
        results.append({
            "keyword": r.get("Keyword", ""),
            "position": int(r.get("Position", 0) or 0),
            "volume": int(r.get("Search Volume", 0) or 0),
            "kd": int(r.get("Keyword Difficulty Index", 0) or 0),
            "cpc": round(float(r.get("CPC", 0) or 0), 2),
            "url": r.get("Url", ""),
            "traffic": round(float(r.get("Traffic", 0) or 0), 1),
            "traffic_cost": round(float(r.get("Traffic Cost", 0) or 0), 2)
        })
    return results


def get_domain_paid_keywords(domain, database, api_key, limit=500):
    """Get a domain's paid (PPC) keywords."""
    rows = semrush_api_call({
        "type": "domain_adwords",
        "domain": domain,
        "database": database,
        "export_columns": "Ph,Po,Nq,Cp,Ur,Tr,Tc,Co",
        "display_limit": str(limit),
        "display_sort": "tr_desc"
    }, api_key)
    results = []
    for r in rows:
        results.append({
            "keyword": r.get("Keyword", ""),
            "position": int(r.get("Position", 0) or 0),
            "volume": int(r.get("Search Volume", 0) or 0),
            "cpc": round(float(r.get("CPC", 0) or 0), 2),
            "url": r.get("Url", ""),
            "traffic": round(float(r.get("Traffic", 0) or 0), 1),
            "traffic_cost": round(float(r.get("Traffic Cost", 0) or 0), 2),
            "competition": round(float(r.get("Competition", 0) or 0), 4)
        })
    return results


def get_keyword_gap(target, competitors, database, api_key, limit=200):
    """Find keywords competitors rank for that target doesn't."""
    # Semrush keyword gap API: domain_domains
    domains_param = "|".join([f"{d}|organic" for d in [target] + competitors[:4]])
    rows = semrush_api_call({
        "type": "domain_domains",
        "domains": domains_param,
        "database": database,
        "export_columns": "Ph,Nq,Kd,Cp,Co",
        "display_limit": str(limit),
        "display_sort": "nq_desc",
        "display_filter": "+|Ph|Co|Lt|1"  # filter: competition < 1 (has room)
    }, api_key)
    results = []
    for r in rows:
        results.append({
            "keyword": r.get("Keyword", ""),
            "volume": int(r.get("Search Volume", 0) or 0),
            "kd": int(r.get("Keyword Difficulty Index", 0) or 0),
            "cpc": round(float(r.get("CPC", 0) or 0), 2),
            "competition": round(float(r.get("Competition", 0) or 0), 4),
            "source": "keyword_gap"
        })
    return results


def map_intent(raw):
    """Map Semrush intent codes to readable labels."""
    mapping = {
        "0": "Informational",
        "1": "Navigational",
        "2": "Commercial",
        "3": "Transactional",
        "informational": "Informational",
        "navigational": "Navigational",
        "commercial": "Commercial",
        "transactional": "Transactional",
    }
    if not raw:
        return "Unknown"
    # Semrush returns comma-separated intent codes sometimes
    parts = str(raw).strip().lower().split(",")
    for p in parts:
        p = p.strip()
        if p in mapping:
            return mapping[p]
    return raw.capitalize() if raw else "Unknown"


# ── Main analysis ──

def run_keyword_intelligence(config):
    """Run full keyword intelligence analysis."""
    api_key = config.get("semrush", {}).get("api_key", "")
    database = config.get("semrush", {}).get("database", "us")
    target_domain = get_target_domain(config)
    competitors = get_competitor_domains(config)
    market_keywords = config.get("market_keywords", [])

    print(f"\n{'='*60}")
    print(f"  KEYWORD INTELLIGENCE")
    print(f"  Target: {target_domain}")
    print(f"  Competitors: {len(competitors)}")
    print(f"  Market keywords: {len(market_keywords)}")
    print(f"{'='*60}\n")

    results = {
        "generated_at": datetime.now().isoformat(),
        "source": "semrush_api",
        "target_domain": target_domain,
        "database": database,
        "keywords": {},           # keyword -> {volume, kd, cpc, intent}
        "competitor_keywords": {},  # domain -> [{keyword, volume, ...}]
        "keyword_gap": [],         # keywords competitors have, target doesn't
        "related_keywords": [],    # discovered related keywords
        "competitors": {}          # domain -> {organic_count, paid_count, ...}
    }

    # 1. Enrich market keywords
    print("  [1/5] Enriching market keywords...")
    enriched = 0
    for i, kw in enumerate(market_keywords):
        data = get_keyword_overview(kw, database, api_key)
        if data:
            results["keywords"][kw.lower()] = {
                "volume": data["volume"],
                "kd": data["kd"],
                "cpc": data["cpc"],
                "intent": data["intent"],
                "competition": data["competition"],
                "results": data["results"],
                "trend": data["trend"]
            }
            enriched += 1
        if (i + 1) % 10 == 0:
            print(f"    {i+1}/{len(market_keywords)} done ({enriched} enriched)")
        time.sleep(0.3)
    print(f"    Enriched {enriched}/{len(market_keywords)} market keywords\n")

    # 2. Get related keywords from top seeds
    print("  [2/5] Discovering related keywords...")
    seeds = market_keywords[:10]  # top 10 seeds for discovery
    seen = set(kw.lower() for kw in market_keywords)
    for seed in seeds:
        related = get_keyword_related(seed, database, api_key, limit=30)
        for r in related:
            kw_lower = r["keyword"].lower()
            if kw_lower not in seen:
                seen.add(kw_lower)
                results["related_keywords"].append(r)
                # Also add to main keywords dict
                results["keywords"][kw_lower] = {
                    "volume": r["volume"],
                    "kd": r["kd"],
                    "cpc": r["cpc"],
                    "intent": r["intent"],
                    "competition": r["competition"]
                }
        time.sleep(0.3)
    print(f"    Discovered {len(results['related_keywords'])} related keywords\n")

    # 3. Competitor paid keywords
    print("  [3/5] Analyzing competitor paid keywords...")
    primary_competitors = [c["domain"] for c in config.get("competitors", [])
                          if c.get("priority") == "primary"]
    for domain in primary_competitors:
        print(f"    {domain}...")
        paid = get_domain_paid_keywords(domain, database, api_key, limit=500)
        organic = get_domain_organic_keywords(domain, database, api_key, limit=200)
        results["competitor_keywords"][domain] = {
            "paid": paid,
            "organic": organic[:100]  # cap organic to avoid huge output
        }
        results["competitors"][domain] = {
            "paid_keyword_count": len(paid),
            "organic_keyword_count": len(organic),
            "top_paid_traffic": sum(k["traffic"] for k in paid[:50]),
            "top_paid_cost": sum(k["traffic_cost"] for k in paid[:50])
        }
        # Add competitor keywords to main lookup
        for k in paid + organic:
            kw_lower = k["keyword"].lower()
            if kw_lower not in results["keywords"]:
                results["keywords"][kw_lower] = {
                    "volume": k["volume"],
                    "kd": k.get("kd", 0),
                    "cpc": k["cpc"],
                    "intent": "Unknown",
                    "competition": k.get("competition", 0)
                }
        time.sleep(0.5)
    print()

    # 4. Keyword gap analysis
    print("  [4/5] Running keyword gap analysis...")
    gap_keywords = get_keyword_gap(target_domain, primary_competitors, database, api_key, limit=200)
    results["keyword_gap"] = gap_keywords
    for k in gap_keywords:
        kw_lower = k["keyword"].lower()
        if kw_lower not in results["keywords"]:
            results["keywords"][kw_lower] = {
                "volume": k["volume"],
                "kd": k["kd"],
                "cpc": k["cpc"],
                "intent": "Unknown",
                "competition": k["competition"]
            }
    print(f"    Found {len(gap_keywords)} keyword gap opportunities\n")

    # 5. Target domain keywords
    print("  [5/5] Analyzing target domain keywords...")
    target_organic = get_domain_organic_keywords(target_domain, database, api_key, limit=200)
    target_paid = get_domain_paid_keywords(target_domain, database, api_key, limit=200)
    results["target_keywords"] = {
        "organic": target_organic,
        "paid": target_paid
    }
    for k in target_organic + target_paid:
        kw_lower = k["keyword"].lower()
        if kw_lower not in results["keywords"]:
            results["keywords"][kw_lower] = {
                "volume": k["volume"],
                "kd": k.get("kd", 0),
                "cpc": k["cpc"],
                "intent": "Unknown",
                "competition": k.get("competition", 0)
            }
    print(f"    Target organic: {len(target_organic)}, paid: {len(target_paid)}\n")

    # Summary
    print(f"  Total keywords in intelligence database: {len(results['keywords'])}")
    print(f"  Competitor keyword gaps: {len(results['keyword_gap'])}")
    print(f"  Related keywords discovered: {len(results['related_keywords'])}")

    return results


def save_results(results, output_dir):
    """Save keyword intelligence to files."""
    os.makedirs(output_dir, exist_ok=True)

    # Full intelligence JSON
    full_path = os.path.join(output_dir, "keyword_intelligence_full.json")
    with open(full_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"  Saved: {full_path}")

    # Dashboard-compatible keyword_market_data.json
    dashboard_data = {
        "source": "semrush_auto_analyzer",
        "generated_at": results["generated_at"],
        "keywords": results["keywords"],
        "competitors": results.get("competitors", {}),
        "keyword_gap": results.get("keyword_gap", [])[:50]
    }
    dash_path = os.path.join(output_dir, "keyword_market_data.json")
    with open(dash_path, "w") as f:
        json.dump(dashboard_data, f, indent=2)
    print(f"  Saved: {dash_path}")

    # CSV export
    csv_path = os.path.join(output_dir, "keyword_intelligence.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["keyword", "volume", "kd", "cpc", "intent", "competition"])
        for kw, data in sorted(results["keywords"].items(), key=lambda x: x[1].get("volume", 0), reverse=True):
            writer.writerow([kw, data.get("volume", 0), data.get("kd", 0),
                           data.get("cpc", 0), data.get("intent", ""), data.get("competition", 0)])
    print(f"  Saved: {csv_path}")

    return dashboard_data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Keyword Intelligence Module")
    parser.add_argument("--config-file", default="config/config.yaml")
    args = parser.parse_args()

    config = load_config(args.config_file)
    results = run_keyword_intelligence(config)
    save_results(results, "data/semrush")
