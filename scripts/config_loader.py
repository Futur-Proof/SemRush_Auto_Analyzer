#!/usr/bin/env python3
"""
Configuration Loader
Loads and validates config.yaml settings
"""

import os
import yaml
from pathlib import Path


def get_config_path(config_file=None):
    """Get path to config file"""
    if config_file:
        # If absolute path, use directly
        if os.path.isabs(config_file):
            return Path(config_file)
        # If relative, resolve from script parent directory
        script_dir = Path(__file__).parent.parent
        return script_dir / config_file
    # Default config path
    script_dir = Path(__file__).parent.parent
    return script_dir / "config" / "config.yaml"


def load_config(config_file=None):
    """Load configuration from YAML file"""
    config_path = get_config_path(config_file)

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


def get_output_dir(config=None):
    """Get output directory path"""
    script_dir = Path(__file__).parent.parent
    if config and config.get('output', {}).get('base_dir'):
        return script_dir / config['output']['base_dir']
    return script_dir / "output"


def get_data_dir(config=None):
    """Get data directory path"""
    script_dir = Path(__file__).parent.parent
    if config and config.get('output', {}).get('data_dir'):
        return script_dir / config['output']['data_dir']
    return script_dir / "data"


def ensure_directories(config=None):
    """Ensure output and data directories exist"""
    output_dir = get_output_dir(config)
    data_dir = get_data_dir(config)

    output_dir.mkdir(exist_ok=True)
    data_dir.mkdir(exist_ok=True)
    (output_dir / "screenshots").mkdir(exist_ok=True)
    (output_dir / "screenshots" / "semrush").mkdir(exist_ok=True)
    (output_dir / "screenshots" / "traffic").mkdir(exist_ok=True)
    (output_dir / "screenshots" / "paid_media").mkdir(exist_ok=True)
    (output_dir / "exports").mkdir(exist_ok=True)
    (output_dir / "analysis").mkdir(exist_ok=True)
    (output_dir / "projections").mkdir(exist_ok=True)
    (data_dir / "reviews").mkdir(exist_ok=True)
    (data_dir / "semrush").mkdir(exist_ok=True)
    (data_dir / "paid_media").mkdir(exist_ok=True)


if __name__ == "__main__":
    # Test config loading
    import sys
    config_file = sys.argv[1] if len(sys.argv) > 1 else None
    config = load_config(config_file)
    print("=" * 50)
    print("Configuration Loaded Successfully")
    print("=" * 50)
    print(f"Target: {get_target_name(config)} ({get_target_domain(config)})")
    print(f"Competitors: {get_competitor_domains(config)}")
    print(f"Database: {config.get('semrush', {}).get('database', 'us')}")
    print(f"Market Keywords: {config.get('market_keywords', [])}")
