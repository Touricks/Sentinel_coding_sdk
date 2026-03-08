"""Writeback utilities for progress.yaml I/O."""

import yaml


def dump_yaml(data: dict) -> str:
    """Serialize a dict to YAML with consistent formatting."""
    return yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
