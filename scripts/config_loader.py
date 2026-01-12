#!/usr/bin/env python3
"""
Configuration Loader
Loads and validates config.yaml settings
"""

import os
import yaml
from pathlib import Path


def get_config_path():
    """Get path to config file"""
    script_dir = Path(__file__).parent.parent
    return script_dir / "config" / "config.yaml"


def load_config():
    """Load configuration from YAML file"""
    config_path = get_config_path()

    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config


def get_target_domain(config):
    """Get target domain from config"""
    return config.get('target', {}).get('domain', '')


def get_target_name(config):
    """Get target name from config"""
    return config.get('target', {}).get('name', '')


def get_competitor_domains(config):
    """Get list of competitor domains"""
    competitors = config.get('competitors', [])
    return [c.get('domain') for c in competitors if c.get('domain')]


def get_competitor_names(config):
    """Get dict mapping domain to name"""
    competitors = config.get('competitors', [])
    return {c.get('domain'): c.get('name') for c in competitors}


def get_all_domains(config):
    """Get target + all competitor domains"""
    domains = []
    target = get_target_domain(config)
    if target:
        domains.append(target)
    domains.extend(get_competitor_domains(config))
    return domains


def get_output_dir():
    """Get output directory path"""
    script_dir = Path(__file__).parent.parent
    return script_dir / "output"


def get_data_dir():
    """Get data directory path"""
    script_dir = Path(__file__).parent.parent
    return script_dir / "data"


def ensure_directories():
    """Ensure output and data directories exist"""
    get_output_dir().mkdir(exist_ok=True)
    get_data_dir().mkdir(exist_ok=True)
    (get_output_dir() / "screenshots").mkdir(exist_ok=True)
    (get_output_dir() / "exports").mkdir(exist_ok=True)
    (get_data_dir() / "reviews").mkdir(exist_ok=True)
    (get_data_dir() / "semrush").mkdir(exist_ok=True)


if __name__ == "__main__":
    # Test config loading
    config = load_config()
    print("=" * 50)
    print("Configuration Loaded Successfully")
    print("=" * 50)
    print(f"Target: {get_target_name(config)} ({get_target_domain(config)})")
    print(f"Competitors: {get_competitor_domains(config)}")
    print(f"Database: {config.get('semrush', {}).get('database', 'us')}")
    print(f"Market Keywords: {config.get('market_keywords', [])}")
