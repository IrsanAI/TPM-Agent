from __future__ import annotations

from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import platform


@dataclass
class RuntimePaths:
    repo_root: Path
    device_root: Path
    state_dir: Path
    data_dir: Path
    logs_dir: Path


def _parse_config(source: Path) -> dict:
    raw = source.read_text(encoding="utf-8")
    if importlib.util.find_spec("yaml") is not None:
        import yaml

        return yaml.safe_load(raw)
    return json.loads(raw)


def detect_runtime_paths(config: dict) -> RuntimePaths:
    repo_root = Path(__file__).resolve().parents[1]
    home_root = Path.home() / config.get("platform", {}).get("project_root_name", "IrsanAI-TPM")
    device_root = home_root if home_root.exists() else repo_root

    state_dir = device_root / config.get("platform", {}).get("cache_dir", "state")
    data_dir = device_root / config.get("platform", {}).get("data_dir", "data")
    logs_dir = device_root / config.get("platform", {}).get("logs_dir", "logs")
    for path in (state_dir, data_dir, logs_dir):
        path.mkdir(parents=True, exist_ok=True)

    return RuntimePaths(repo_root=repo_root, device_root=device_root, state_dir=state_dir, data_dir=data_dir, logs_dir=logs_dir)


def load_config(config_path: Path | None = None) -> tuple[dict, RuntimePaths]:
    repo_root = Path(__file__).resolve().parents[1]
    source = config_path or (repo_root / "config" / "config.yaml")
    payload = _parse_config(source)
    paths = detect_runtime_paths(payload)
    payload["runtime"] = {"os": platform.system(), "platform": platform.platform(), "device_root": str(paths.device_root)}
    return payload, paths
