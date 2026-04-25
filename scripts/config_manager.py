#!/usr/bin/env python3
"""
配置管理器
首次运行时询问用户偏好，生成 config.json
后续直接加载使用
"""

import json
import os
from pathlib import Path


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
            "_created_at": str(Path(__file__).parent.parent / ".git" / "HEAD"),
            "user": {},
            "account": {},
            "trading": {},
            "preferences": {},
            "filters": {},
            "display": {}
        }

        # 用户信息
        print("\n【用户信息】")
        name = input("  昵称 (默认: 散户): ").strip() or "散户"
        config["user"]["name"] = name

        level = input("  经验级别 [1=新手/2=有经验/3=高手] (默认: 1): ").strip() or "1"
        levels = {"1": "beginner", "2": "intermediate", "3": "advanced"}
        config["user"]["level"] = levels.get(level, "beginner")

        # 账户信息
        print("\n【账户信息】")
        fund = input("  总资金 (元, 默认: 100000): ").strip() or "100000"
        try:
            config["account"]["total_fund"] = int(fund)
        except ValueError:
            config["account"]["total_fund"] = 100000

        # 交易设置
        print("\n【交易设置】")

        max_pos = input("  单只最大仓位 (默认: 30%): ").strip() or "30"
        config["trading"]["max_position_per_stock"] = float(max_pos) / 100

        max_total = input("  总仓位最大比例 (默认: 50%): ").strip() or "50"
        config["trading"]["max_total_position"] = float(max_total) / 100

        stop_loss = input("  止损比例 (默认: 7%): ").strip() or "7"
        config["trading"]["stop_loss_rate"] = float(stop_loss) / 100

        target_mult = input("  止盈为目标止损距离倍数 (默认: 3): ").strip() or "3"
        config["trading"]["profit_target_multiplier"] = float(target_mult)

        # 筛选设置
        print("\n【筛选设置】")

        min_vol = input("  最小日成交额 (默认: 5000万): ").strip() or "50000000"
        config["filters"]["min_daily_volume"] = int(min_vol)

        min_price = input("  最低股价 (默认: 1元): ").strip() or "1"
        config["filters"]["min_price"] = float(min_price)

        max_price = input("  最高股价 (默认: 500元): ").strip() or "500"
        config["filters"]["max_price"] = float(max_price)

        # 展示设置
        print("\n【展示设置】")
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
            "user": {"name": "散户", "level": "beginner"},
            "account": {"total_fund": 100000},
            "trading": {
                "max_position_per_stock": 0.3,
                "max_total_position": 0.5,
                "stop_loss_rate": 0.07,
                "profit_target_multiplier": 3
            },
            "preferences": {
                "default_weight_opportunity": 0.3,
                "default_weight_safety": 0.25,
                "default_weight_certainty": 0.25,
                "default_weight_comfort": 0.2
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
        """
        获取配置值，支持点号路径
        例如: config.get("trading.max_position_per_stock")
        """
        keys = key_path.split(".")
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def get_user_fund(self) -> int:
        """获取用户总资金"""
        return self.get("account.total_fund", 100000)

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
    print(f"\n当前配置:")
    print(f"  用户: {config.get('user.name')}")
    print(f"  资金: {config.get_user_fund()} 元")
    print(f"  单只仓位: {config.get_max_position_per_stock()*100}%")
    print(f"  总仓位: {config.get_max_total_position()*100}%")
    print(f"  止损: {config.get_stop_loss_rate()*100}%")
    print(f"  止盈倍数: {config.get_profit_target_multiplier()}x")
