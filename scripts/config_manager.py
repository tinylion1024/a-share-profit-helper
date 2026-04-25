#!/usr/bin/env python3
"""
配置管理器
首次运行时询问用户偏好，生成 config.json
后续直接加载使用
"""

import json
import os
from pathlib import Path


# 投资风格预设
STYLE_PRESETS = {
    "conservative": {
        "name": "保守型",
        "max_position_per_stock": 0.2,
        "max_total_position": 0.3,
        "stop_loss_rate": 0.05,
        "profit_target_multiplier": 2.5
    },
    "balanced": {
        "name": "平衡型",
        "max_position_per_stock": 0.3,
        "max_total_position": 0.5,
        "stop_loss_rate": 0.07,
        "profit_target_multiplier": 3
    },
    "aggressive": {
        "name": "激进型",
        "max_position_per_stock": 0.4,
        "max_total_position": 0.7,
        "stop_loss_rate": 0.10,
        "profit_target_multiplier": 4
    }
}


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_path: str = None):
        if config_path is None:
            self.config_path = Path(__file__).parent.parent / "config.json"
        else:
            self.config_path = Path(config_path)

        self.config = None
        self._load_or_create()

    def _load_or_create(self):
        """加载现有配置或创建新配置"""
        if self.config_path.exists():
            self._load()
        else:
            self._create_with_prompt()

    def _load(self):
        """加载配置"""
        with open(self.config_path, "r", encoding="utf-8") as f:
            self.config = json.load(f)
        print(f"✓ 配置已加载: {self.config_path}")

    def _create_with_prompt(self):
        """交互式创建配置"""
        print("\n" + "=" * 50)
        print("首次运行配置向导")
        print("=" * 50)

        config = {
            "_version": "1.0",
            "env": {},
            "user": {},
            "trading": {},
            "filters": {},
            "display": {}
        }

        # 环境配置
        print("\n【环境配置】")
        mx_key = input("  MX API 密钥 (可稍后配置): ").strip()
        config["env"]["mx_apikey"] = mx_key

        em_key = input("  东方财富 API 密钥 (可稍后配置): ").strip()
        config["env"]["em_apikey"] = em_key

        cache_dir = input("  数据缓存目录 (默认: /tmp/a_shares_cache): ").strip()
        config["env"]["data_cache_dir"] = cache_dir or "/tmp/a_shares_cache"

        # 用户信息
        print("\n【用户偏好】")
        name = input("  昵称 (默认: 散户): ").strip() or "散户"
        config["user"]["name"] = name

        print("\n  投资风格:")
        print("    1. 保守型 - 仓位低(30%)、止损严(5%)、收益稳")
        print("    2. 平衡型 - 仓位中(50%)、止损中(7%)、收益均衡")
        print("    3. 激进型 - 仓位高(70%)、止损宽(10%)、收益高")
        style = input("  选择风格 [1/2/3, 默认: 2]: ").strip() or "2"

        styles = {"1": "conservative", "2": "balanced", "3": "aggressive"}
        style_key = styles.get(style, "balanced")
        config["user"]["style"] = style_key

        # 应用风格预设
        preset = STYLE_PRESETS[style_key]
        config["trading"]["max_position_per_stock"] = preset["max_position_per_stock"]
        config["trading"]["max_total_position"] = preset["max_total_position"]
        config["trading"]["stop_loss_rate"] = preset["stop_loss_rate"]
        config["trading"]["profit_target_multiplier"] = preset["profit_target_multiplier"]

        # 筛选设置
        print("\n【筛选偏好】")
        min_vol = input("  最小日成交额 (默认: 5000万): ").strip() or "50000000"
        config["filters"]["min_daily_volume"] = int(min_vol)

        min_price = input("  最低股价 (默认: 1元): ").strip() or "1"
        config["filters"]["min_price"] = float(min_price)

        max_price = input("  最高股价 (默认: 500元): ").strip() or "500"
        config["filters"]["max_price"] = float(max_price)

        # 展示设置
        print("\n【展示偏好】")
        show_prob = input("  显示概率预测? [y/n, 默认: y]: ").strip() or "y"
        config["display"]["show_probability"] = show_prob.lower() == "y"

        show_risk = input("  显示风险分析? [y/n, 默认: y]: ").strip() or "y"
        config["display"]["show_risk_analysis"] = show_risk.lower() == "y"

        show_reason = input("  显示详细推理? [y/n, 默认: y]: ").strip() or "y"
        config["display"]["show_detailed_reasoning"] = show_reason.lower() == "y"

        # 确认保存
        print("\n" + "=" * 50)
        print("配置预览:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
        print("=" * 50)

        confirm = input("\n确认保存? [y/n, 默认: y]: ").strip() or "y"
        if confirm.lower() == "y":
            self._save(config)
            self.config = config
            print("✓ 配置已保存!")
        else:
            print("✗ 已取消，程序将使用默认配置")
            self._use_defaults()

    def _save(self, config: dict):
        """保存配置"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    def _use_defaults(self):
        """使用默认配置"""
        self.config = {
            "_version": "1.0",
            "env": {
                "mx_apikey": "",
                "em_apikey": "",
                "data_cache_dir": "/tmp/a_shares_cache",
                "log_level": "INFO"
            },
            "user": {"name": "散户", "style": "balanced"},
            "trading": {
                "max_position_per_stock": 0.3,
                "max_total_position": 0.5,
                "stop_loss_rate": 0.07,
                "profit_target_multiplier": 3
            },
            "filters": {
                "min_daily_volume": 50000000,
                "min_price": 1,
                "max_price": 500
            },
            "display": {
                "show_probability": True,
                "show_risk_analysis": True,
                "show_detailed_reasoning": True
            }
        }

    def get(self, key_path: str, default=None):
        """获取配置值，支持点号路径"""
        keys = key_path.split(".")
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_mx_apikey(self) -> str:
        """获取 MX API 密钥"""
        return self.get("env.mx_apikey", "")

    def get_em_apikey(self) -> str:
        """获取东方财富 API 密钥"""
        return self.get("env.em_apikey", "")

    def get_cache_dir(self) -> str:
        """获取缓存目录"""
        return self.get("env.data_cache_dir", "/tmp/a_shares_cache")

    def get_user_name(self) -> str:
        """获取用户昵称"""
        return self.get("user.name", "散户")

    def get_user_style(self) -> str:
        """获取投资风格"""
        return self.get("user.style", "balanced")

    def get_style_preset(self) -> dict:
        """获取风格预设"""
        style = self.get_user_style()
        return STYLE_PRESETS.get(style, STYLE_PRESETS["balanced"])

    def get_max_position_per_stock(self) -> float:
        """获取单只最大仓位比例"""
        return self.get("trading.max_position_per_stock", 0.3)

    def get_max_total_position(self) -> float:
        """获取总仓位最大比例"""
        return self.get("trading.max_total_position", 0.5)

    def get_stop_loss_rate(self) -> float:
        """获取止损比例"""
        return self.get("trading.stop_loss_rate", 0.07)

    def get_profit_target_multiplier(self) -> float:
        """获取止盈倍数"""
        return self.get("trading.profit_target_multiplier", 3)

    def get_min_volume(self) -> int:
        """获取最小成交额"""
        return self.get("filters.min_daily_volume", 50000000)

    def is_display(self, key: str) -> bool:
        """检查展示设置"""
        return self.get(f"display.show_{key}", True)

    def reload(self):
        """重新加载配置"""
        self._load_or_create()


def get_config() -> ConfigManager:
    """获取配置管理器单例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance


_config_instance = None


if __name__ == "__main__":
    # 测试配置管理器
    config = get_config()
    style = config.get_style_preset()

    print(f"\n当前配置:")
    print(f"  用户: {config.get_user_name()}")
    print(f"  风格: {config.get_user_style()} ({style['name']})")
    print(f"  单只仓位: {config.get_max_position_per_stock()*100}%")
    print(f"  总仓位: {config.get_max_total_position()*100}%")
    print(f"  止损: {config.get_stop_loss_rate()*100}%")
    print(f"  止盈倍数: {config.get_profit_target_multiplier()}x")
