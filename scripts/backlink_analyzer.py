#!/usr/bin/env python3
"""
Backlink Analyzer Module

Extracts backlink profile data from Semrush API for target domain and competitors.
Includes: backlink counts, referring domains, authority scores, anchor text distribution,
top backlinks, and new/lost backlink trends.

Output: data/semrush/backlink_data.json
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config_loader import load_config, get_target_domain, get_competitor_domains


def semrush_api_call(params, api_key, base_url="https://api.semrush.com/analytics/v1/"):
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


def get_backlinks_overview(domain, api_key):
    """Get backlink profile overview for a domain."""
    rows = semrush_api_call({
        "type": "backlinks_overview",
        "target": domain,
        "target_type": "root_domain",
        "export_columns": "total,domains_num,urls_num,ips_num,ipclassc_num,follows_num,"
                         "nofollows_num,texts_num,images_num,forms_num,frames_num,"
                         "score"
    }, api_key)
    if rows:
        r = rows[0]
        return {
            "total_backlinks": int(r.get("total", 0) or 0),
            "referring_domains": int(r.get("domains_num", 0) or 0),
            "referring_urls": int(r.get("urls_num", 0) or 0),
            "referring_ips": int(r.get("ips_num", 0) or 0),
            "follow_links": int(r.get("follows_num", 0) or 0),
            "nofollow_links": int(r.get("nofollows_num", 0) or 0),
            "text_links": int(r.get("texts_num", 0) or 0),
            "image_links": int(r.get("images_num", 0) or 0),
            "authority_score": int(r.get("score", 0) or 0)
        }
    return None


def get_backlinks(domain, api_key, limit=100):
    """Get individual backlinks for a domain."""
    rows = semrush_api_call({
        "type": "backlinks",
        "target": domain,
        "target_type": "root_domain",
        "export_columns": "source_url,source_title,target_url,anchor,external_num,"
                         "internal_num,first_seen,last_seen,nofollow,form,frame,image",
        "display_limit": str(limit),
        "display_sort": "source_score_desc"
    }, api_key)
    results = []
    for r in rows:
        results.append({
            "source_url": r.get("source_url", ""),
            "source_title": r.get("source_title", ""),
            "target_url": r.get("target_url", ""),
            "anchor": r.get("anchor", ""),
            "external_links": int(r.get("external_num", 0) or 0),
            "internal_links": int(r.get("internal_num", 0) or 0),
            "first_seen": r.get("first_seen", ""),
            "last_seen": r.get("last_seen", ""),
            "nofollow": r.get("nofollow", "0") == "1",
            "type": "image" if r.get("image", "0") == "1" else "text"
        })
    return results


def get_referring_domains(domain, api_key, limit=100):
    """Get top referring domains."""
    rows = semrush_api_call({
        "type": "backlinks_refdomains",
        "target": domain,
        "target_type": "root_domain",
        "export_columns": "domain_ascore,domain,backlinks_num,ip,country,first_seen,last_seen",
        "display_limit": str(limit),
        "display_sort": "domain_ascore_desc"
    }, api_key)
    results = []
    for r in rows:
        results.append({
            "domain": r.get("domain", ""),
            "authority_score": int(r.get("domain_ascore", 0) or 0),
            "backlinks_count": int(r.get("backlinks_num", 0) or 0),
            "country": r.get("country", ""),
            "first_seen": r.get("first_seen", ""),
            "last_seen": r.get("last_seen", "")
        })
    return results


def get_anchors(domain, api_key, limit=50):
    """Get top anchor texts."""
    rows = semrush_api_call({
        "type": "backlinks_anchors",
        "target": domain,
        "target_type": "root_domain",
        "export_columns": "anchor,domains_num,backlinks_num,first_seen,last_seen",
        "display_limit": str(limit),
        "display_sort": "backlinks_num_desc"
    }, api_key)
    results = []
    for r in rows:
        results.append({
            "anchor": r.get("anchor", ""),
            "referring_domains": int(r.get("domains_num", 0) or 0),
            "backlinks": int(r.get("backlinks_num", 0) or 0),
            "first_seen": r.get("first_seen", ""),
            "last_seen": r.get("last_seen", "")
        })
    return results


def get_indexed_pages(domain, api_key, limit=50):
    """Get top indexed pages by backlinks."""
    rows = semrush_api_call({
        "type": "backlinks_pages",
        "target": domain,
        "target_type": "root_domain",
        "export_columns": "target_url,domains_num,backlinks_num,last_seen",
        "display_limit": str(limit),
        "display_sort": "backlinks_num_desc"
    }, api_key)
    results = []
    for r in rows:
        results.append({
            "url": r.get("target_url", ""),
            "referring_domains": int(r.get("domains_num", 0) or 0),
            "backlinks": int(r.get("backlinks_num", 0) or 0),
            "last_seen": r.get("last_seen", "")
        })
    return results


def run_backlink_analysis(config):
    """Run full backlink analysis."""
    api_key = config.get("semrush", {}).get("api_key", "")
    target_domain = get_target_domain(config)
    competitors = [c["domain"] for c in config.get("competitors", [])
                   if c.get("priority") == "primary"]

    print(f"\n{'='*60}")
    print(f"  BACKLINK ANALYSIS")
    print(f"  Target: {target_domain}")
    print(f"  Competitors: {len(competitors)}")
    print(f"{'='*60}\n")

    results = {
        "generated_at": datetime.now().isoformat(),
        "target_domain": target_domain,
        "profiles": {}
    }

    all_domains = [target_domain] + competitors

    for domain in all_domains:
        print(f"  Analyzing {domain}...")
        profile = {
            "overview": get_backlinks_overview(domain, api_key),
            "top_backlinks": get_backlinks(domain, api_key, limit=50),
            "top_referring_domains": get_referring_domains(domain, api_key, limit=50),
            "top_anchors": get_anchors(domain, api_key, limit=30),
            "top_pages": get_indexed_pages(domain, api_key, limit=30)
        }
        results["profiles"][domain] = profile

        overview = profile["overview"]
        if overview:
            print(f"    Authority: {overview['authority_score']} | "
                  f"Backlinks: {overview['total_backlinks']:,} | "
                  f"Ref Domains: {overview['referring_domains']:,}")
        else:
            print(f"    No data returned")
        time.sleep(0.5)

    # Build comparison table
    print(f"\n  {'Domain':<35} {'Auth':>5} {'Backlinks':>12} {'Ref Domains':>12} {'Follow%':>8}")
    print(f"  {'-'*75}")
    for domain in all_domains:
        ov = results["profiles"][domain].get("overview")
        if ov:
            follow_pct = (ov["follow_links"] / max(ov["total_backlinks"], 1) * 100)
            marker = " <-- target" if domain == target_domain else ""
            print(f"  {domain:<35} {ov['authority_score']:>5} {ov['total_backlinks']:>12,} "
                  f"{ov['referring_domains']:>12,} {follow_pct:>7.1f}%{marker}")

    return results


def save_results(results, output_dir):
    """Save backlink analysis results."""
    os.makedirs(output_dir, exist_ok=True)

    # Full backlink data
    full_path = os.path.join(output_dir, "backlink_data.json")
    with open(full_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Saved: {full_path}")

    # Summary CSV
    csv_path = os.path.join(output_dir, "backlink_summary.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["domain", "authority_score", "total_backlinks", "referring_domains",
                         "follow_links", "nofollow_links", "text_links", "image_links"])
        for domain, profile in results["profiles"].items():
            ov = profile.get("overview") or {}
            writer.writerow([
                domain,
                ov.get("authority_score", 0),
                ov.get("total_backlinks", 0),
                ov.get("referring_domains", 0),
                ov.get("follow_links", 0),
                ov.get("nofollow_links", 0),
                ov.get("text_links", 0),
                ov.get("image_links", 0)
            ])
    print(f"  Saved: {csv_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Backlink Analyzer")
    parser.add_argument("--config-file", default="config/config.yaml")
    args = parser.parse_args()

    config = load_config(args.config_file)
    results = run_backlink_analysis(config)
    save_results(results, "data/semrush")
