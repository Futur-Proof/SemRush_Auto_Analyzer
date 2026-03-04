#!/usr/bin/env python3
"""
Dashboard Exporter Module

Exports all analyzed data to the Google Ads Dashboard format.
Copies/transforms data files from the analyzer output to the dashboard's
data/{client}/semrush/ directory structure.

Expected dashboard data files:
  data/{client}/semrush/keyword_market_data.json  — Volume, KD, CPC, Intent per keyword
  data/{client}/semrush/traffic_data.json          — Traffic overview and trends
  data/{client}/semrush/backlink_data.json         — Backlink profiles and comparisons
  data/{client}/semrush/ai_visibility_data.json    — AI visibility analysis
  data/{client}/semrush/competitor_benchmarks.json  — Competitor overview metrics
"""

import json
import os
import shutil
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.config_loader import load_config


def export_to_dashboard(config, source_dir="data/semrush", auto_deploy=False):
    """Export analyzer data to dashboard format."""
    client_id = config.get("target", {}).get("dashboard_client_id", "")
    dashboard_path = config.get("dashboard", {}).get("output_path", "")
    export_formats = config.get("dashboard", {}).get("export_formats", [])

    if not client_id:
        print("  WARNING: No dashboard_client_id configured. Skipping dashboard export.")
        return

    print(f"\n{'='*60}")
    print(f"  DASHBOARD EXPORT")
    print(f"  Client: {client_id}")
    print(f"  Source: {source_dir}")
    if dashboard_path:
        print(f"  Dashboard: {dashboard_path}")
    print(f"  Formats: {', '.join(export_formats)}")
    print(f"{'='*60}\n")

    # Determine output directory
    if dashboard_path:
        output_dir = os.path.join(dashboard_path, "data", client_id, "semrush")
    else:
        output_dir = os.path.join("output", "dashboard", client_id, "semrush")

    os.makedirs(output_dir, exist_ok=True)

    files_exported = []

    # File mapping: export_format -> (source_file, transform_function)
    file_map = {
        "keyword_market_data": ("keyword_market_data.json", transform_keyword_data),
        "traffic_data": ("traffic_data.json", None),
        "backlink_data": ("backlink_data.json", transform_backlink_data),
        "ai_visibility_data": ("ai_visibility_data.json", None),
        "competitor_benchmarks": ("competitor_benchmarks.json", None),
    }

    for fmt in export_formats:
        if fmt not in file_map:
            print(f"  SKIP: Unknown format '{fmt}'")
            continue

        source_file, transform_fn = file_map[fmt]
        source_path = os.path.join(source_dir, source_file)

        if not os.path.exists(source_path):
            # Check alternate names
            alt_names = {
                "keyword_market_data.json": "keyword_intelligence_full.json",
                "competitor_benchmarks.json": "competitor_paid_summary.csv"
            }
            alt = alt_names.get(source_file)
            if alt and os.path.exists(os.path.join(source_dir, alt)):
                source_path = os.path.join(source_dir, alt)
            else:
                print(f"  SKIP: {source_file} not found (run the analysis first)")
                continue

        dest_path = os.path.join(output_dir, source_file)

        if transform_fn:
            # Apply transformation
            with open(source_path) as f:
                data = json.load(f)
            transformed = transform_fn(data)
            with open(dest_path, "w") as f:
                json.dump(transformed, f, indent=2)
            print(f"  EXPORTED: {source_file} -> {dest_path} (transformed)")
        else:
            # Direct copy
            shutil.copy2(source_path, dest_path)
            print(f"  EXPORTED: {source_file} -> {dest_path}")

        files_exported.append(dest_path)

    # Generate manifest
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "client_id": client_id,
        "source": "semrush_auto_analyzer",
        "files": files_exported
    }
    manifest_path = os.path.join(output_dir, "export_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n  Exported {len(files_exported)} files to {output_dir}")
    return files_exported


def transform_keyword_data(data):
    """Transform full keyword intelligence into dashboard-compatible format.

    Input: keyword_intelligence_full.json (from keyword_intelligence.py)
    Output: keyword_market_data.json (dashboard format)
    """
    # If already in dashboard format, return as-is
    if "keywords" in data and isinstance(data["keywords"], dict):
        # Check if already in {keyword: {volume, kd, cpc, intent}} format
        sample = next(iter(data["keywords"].values()), None) if data["keywords"] else None
        if sample and "volume" in sample:
            return {
                "source": "semrush_auto_analyzer",
                "generated_at": data.get("generated_at", datetime.now().isoformat()),
                "keywords": data["keywords"],
                "competitors": data.get("competitors", {}),
                "keyword_gap": data.get("keyword_gap", [])[:50]
            }

    # Transform from other formats
    keywords = {}
    for kw_data in data.get("related_keywords", []):
        kw = kw_data.get("keyword", "").lower()
        if kw:
            keywords[kw] = {
                "volume": kw_data.get("volume", 0),
                "kd": kw_data.get("kd", 0),
                "cpc": kw_data.get("cpc", 0),
                "intent": kw_data.get("intent", "Unknown")
            }

    return {
        "source": "semrush_auto_analyzer",
        "generated_at": data.get("generated_at", datetime.now().isoformat()),
        "keywords": keywords,
        "competitors": data.get("competitors", {}),
    }


def transform_backlink_data(data):
    """Transform backlink data for dashboard consumption.

    Simplifies the full backlink data to overview + comparison format.
    """
    profiles = data.get("profiles", {})
    target = data.get("target_domain", "")

    dashboard_data = {
        "generated_at": data.get("generated_at", datetime.now().isoformat()),
        "target_domain": target,
        "comparison": [],
        "target_top_pages": [],
        "target_top_anchors": [],
        "target_referring_domains": []
    }

    # Build comparison table
    for domain, profile in profiles.items():
        ov = profile.get("overview") or {}
        dashboard_data["comparison"].append({
            "domain": domain,
            "is_target": domain == target,
            "authority_score": ov.get("authority_score", 0),
            "total_backlinks": ov.get("total_backlinks", 0),
            "referring_domains": ov.get("referring_domains", 0),
            "follow_links": ov.get("follow_links", 0),
            "nofollow_links": ov.get("nofollow_links", 0)
        })

    # Sort by authority score descending
    dashboard_data["comparison"].sort(key=lambda x: x["authority_score"], reverse=True)

    # Target-specific data
    target_profile = profiles.get(target, {})
    dashboard_data["target_top_pages"] = target_profile.get("top_pages", [])[:20]
    dashboard_data["target_top_anchors"] = target_profile.get("top_anchors", [])[:20]
    dashboard_data["target_referring_domains"] = target_profile.get("top_referring_domains", [])[:30]

    return dashboard_data


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Dashboard Exporter")
    parser.add_argument("--config-file", default="config/config.yaml")
    parser.add_argument("--source-dir", default="data/semrush")
    parser.add_argument("--deploy", action="store_true", help="Auto-deploy to Vercel after export")
    args = parser.parse_args()

    config = load_config(args.config_file)
    export_to_dashboard(config, args.source_dir, args.deploy)
