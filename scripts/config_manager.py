#!/usr/bin/env python3
"""Interactive config generator for the live-first skill."""

from __future__ import annotations

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


DEFAULT_CONFIG = {
    "_version": "2.1",
    "env": {
        "mx_apikey": "",
        "em_apikey": "",
        "iwencai_base_url": "https://openapi.iwencai.com",
        "iwencai_api_key": "",
        "data_cache_dir": "/tmp/a_shares_cache",
        "sample_data_path": "",
        "offline_mode": False,
        "live_source": "tencent",
        "source_timeout_seconds": 10,
        "live_watchlist": [
            "300750",
            "002594",
            "600519",
            "000001",
            "600036",
            "601318",
            "000333",
            "002475",
            "601899",
            "300308",
        ],
        "log_level": "INFO",
    },
    "trading": {
        "max_position_per_stock": 0.3,
        "max_total_position": 0.5,
        "stop_loss_rate": 0.07,
        "profit_target_multiplier": 3,
    },
    "filters": {
        "min_daily_volume": 50000000,
    },
}


def prompt_bool(label: str, default: bool) -> bool:
    raw = input(f"{label} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    if raw == "":
        return default
    return raw in {"y", "yes", "1", "true"}


def main() -> None:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    config_path = Path(__file__).resolve().parent.parent / "config.json"

    print("实时在线配置向导")
    config["env"]["offline_mode"] = prompt_bool("启用离线模式(仅测试/应急)", False)
    live_source = input("实时数据源(默认 tencent): ").strip()
    if live_source:
        config["env"]["live_source"] = live_source
    watchlist = input("在线选股观察池(逗号分隔，可空): ").strip()
    if watchlist:
        config["env"]["live_watchlist"] = [item.strip() for item in watchlist.split(",") if item.strip()]
    config["env"]["sample_data_path"] = input("本地样本数据路径(可空): ").strip()
    config["env"]["iwencai_api_key"] = input("IWENCAI_API_KEY(可空): ").strip()
    config["env"]["mx_apikey"] = input("MX_APIKEY(可空): ").strip()
    config["env"]["em_apikey"] = input("EM_API_KEY(可空): ").strip()

    max_single = input("单只最大仓位(默认 0.3): ").strip()
    if max_single:
        config["trading"]["max_position_per_stock"] = float(max_single)

    max_total = input("总仓位上限(默认 0.5): ").strip()
    if max_total:
        config["trading"]["max_total_position"] = float(max_total)

    stop_loss = input("止损比例(默认 0.07): ").strip()
    if stop_loss:
        config["trading"]["stop_loss_rate"] = float(stop_loss)

    print(json.dumps(config, ensure_ascii=False, indent=2))
    if prompt_bool("写入 config.json", True):
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写入 {config_path}")
    else:
        print("已取消写入")


if __name__ == "__main__":
    main()
