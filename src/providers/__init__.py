"""Market data providers for the skill."""

from src.config import Config

from .base import DataNotFoundError, MarketDataProvider, OnlineDataError
from .live import TencentLiveProvider
from .offline import OfflineFirstProvider


def build_provider(config: Config) -> MarketDataProvider:
    if config.offline_mode:
        return OfflineFirstProvider(config)
    return TencentLiveProvider(config)


__all__ = [
    "DataNotFoundError",
    "MarketDataProvider",
    "OnlineDataError",
    "OfflineFirstProvider",
    "TencentLiveProvider",
    "build_provider",
]
