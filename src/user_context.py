"""Persistent user preferences and memory for the skill."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.config import Config
from src.utils.time import shanghai_timestamp_iso


def _dedupe_strings(values: list[str] | tuple[str, ...] | None) -> list[str]:
    result: list[str] = []
    for raw in values or []:
        value = str(raw).strip()
        if value and value not in result:
            result.append(value)
    return result


@dataclass
class UserPreferences:
    """Explicit user-level trading and research preferences."""

    risk_preference: str = "平衡型"
    default_horizon: str = "短线"
    preferred_sectors: list[str] = field(default_factory=list)
    avoided_sectors: list[str] = field(default_factory=list)
    watchlist: list[str] = field(default_factory=list)
    focus_styles: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class UserMemory:
    """Implicit memory accumulated from usage."""

    recent_stocks: list[str] = field(default_factory=list)
    recent_workflows: list[dict[str, Any]] = field(default_factory=list)
    stock_notes: dict[str, list[str]] = field(default_factory=dict)
    stock_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)
    theme_profiles: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class UserContextStore:
    """Read and write persistent user preferences and memory."""

    def __init__(self, config: Config):
        self.config = config
        self.root = Path(config.data_cache_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.profile_path = self.root / "user_profile.json"
        self.memory_path = self.root / "user_memory.json"

    def _read_json(self, path: Path, default: dict[str, Any]) -> dict[str, Any]:
        if not path.exists():
            return default
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return default
        return payload if isinstance(payload, dict) else default

    def _write_json(self, path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_preferences(self) -> UserPreferences:
        payload = self._read_json(self.profile_path, {})
        return UserPreferences(
            risk_preference=str(payload.get("risk_preference", "平衡型") or "平衡型"),
            default_horizon=str(payload.get("default_horizon", "短线") or "短线"),
            preferred_sectors=_dedupe_strings(payload.get("preferred_sectors", [])),
            avoided_sectors=_dedupe_strings(payload.get("avoided_sectors", [])),
            watchlist=_dedupe_strings(payload.get("watchlist", [])),
            focus_styles=_dedupe_strings(payload.get("focus_styles", [])),
            notes=_dedupe_strings(payload.get("notes", [])),
        )

    def save_preferences(self, preferences: UserPreferences) -> UserPreferences:
        normalized = UserPreferences(
            risk_preference=preferences.risk_preference or "平衡型",
            default_horizon=preferences.default_horizon or "短线",
            preferred_sectors=_dedupe_strings(preferences.preferred_sectors),
            avoided_sectors=_dedupe_strings(preferences.avoided_sectors),
            watchlist=_dedupe_strings(preferences.watchlist),
            focus_styles=_dedupe_strings(preferences.focus_styles),
            notes=_dedupe_strings(preferences.notes),
        )
        self._write_json(self.profile_path, normalized.to_dict())
        return normalized

    def update_preferences(self, **changes: Any) -> UserPreferences:
        current = self.load_preferences()
        payload = current.to_dict()
        for key, value in changes.items():
            if value is None:
                continue
            if key in {"preferred_sectors", "avoided_sectors", "watchlist", "focus_styles", "notes"}:
                payload[key] = _dedupe_strings(value)
            else:
                payload[key] = value
        return self.save_preferences(UserPreferences(**payload))

    def load_memory(self) -> UserMemory:
        payload = self._read_json(self.memory_path, {})
        stock_notes = payload.get("stock_notes", {})
        return UserMemory(
            recent_stocks=_dedupe_strings(payload.get("recent_stocks", [])),
            recent_workflows=list(payload.get("recent_workflows", []))[:20],
            stock_notes={
                str(code): _dedupe_strings(notes if isinstance(notes, list) else [])
                for code, notes in (stock_notes.items() if isinstance(stock_notes, dict) else [])
            },
            stock_profiles={
                str(code): profile
                for code, profile in ((payload.get("stock_profiles") or {}).items() if isinstance(payload.get("stock_profiles"), dict) else [])
                if isinstance(profile, dict)
            },
            theme_profiles={
                str(theme): profile
                for theme, profile in ((payload.get("theme_profiles") or {}).items() if isinstance(payload.get("theme_profiles"), dict) else [])
                if isinstance(profile, dict)
            },
        )

    def save_memory(self, memory: UserMemory) -> UserMemory:
        normalized = UserMemory(
            recent_stocks=_dedupe_strings(memory.recent_stocks)[:20],
            recent_workflows=list(memory.recent_workflows)[:20],
            stock_notes={code: _dedupe_strings(notes)[:20] for code, notes in memory.stock_notes.items()},
            stock_profiles={str(code): dict(profile) for code, profile in memory.stock_profiles.items()},
            theme_profiles={str(theme): dict(profile) for theme, profile in memory.theme_profiles.items()},
        )
        self._write_json(self.memory_path, normalized.to_dict())
        return normalized

    def _bump_counter(self, profile: dict[str, Any], field: str, value: str | None) -> None:
        token = str(value or "").strip()
        if not token:
            return
        counters = profile.setdefault(field, {})
        counters[token] = int(counters.get(token, 0) or 0) + 1

    def _touch_recent_list(self, profile: dict[str, Any], field: str, values: list[str], limit: int = 12) -> None:
        current = [str(item).strip() for item in profile.get(field, []) if str(item).strip()]
        for item in values:
            token = str(item).strip()
            if token and token not in current:
                current.append(token)
        profile[field] = current[-limit:]

    def observe_stock_profile(self, stock_code: str, observation: dict[str, Any]) -> UserMemory:
        memory = self.load_memory()
        profile = memory.stock_profiles.setdefault(
            stock_code,
            {
                "stock_code": stock_code,
                "stock_name": "",
                "observation_count": 0,
                "watch_count": 0,
                "tags": [],
                "concept_tags": [],
                "catalysts": [],
                "notes": [],
                "style_counts": {},
                "setup_counts": {},
                "market_stage_counts": {},
                "community_mood_counts": {},
                "theme_links": {},
            },
        )
        profile["stock_name"] = observation.get("stock_name") or profile.get("stock_name", "")
        profile["sector"] = observation.get("sector") or profile.get("sector", "")
        profile["last_seen"] = shanghai_timestamp_iso()
        profile["last_summary"] = observation.get("summary", profile.get("last_summary", ""))
        profile["last_market_stage"] = observation.get("market_stage", profile.get("last_market_stage", ""))
        profile["last_style"] = observation.get("style", profile.get("last_style", ""))
        profile["last_setup"] = observation.get("setup", profile.get("last_setup", ""))
        profile["last_sentiment"] = observation.get("community_mood", profile.get("last_sentiment", ""))
        profile["observation_count"] = int(profile.get("observation_count", 0) or 0) + 1
        profile["watch_count"] = int(profile.get("watch_count", 0) or 0) + (1 if observation.get("watchlist_match") else 0)
        self._bump_counter(profile, "style_counts", observation.get("style"))
        self._bump_counter(profile, "setup_counts", observation.get("setup"))
        self._bump_counter(profile, "market_stage_counts", observation.get("market_stage"))
        self._bump_counter(profile, "community_mood_counts", observation.get("community_mood"))
        self._touch_recent_list(profile, "tags", _dedupe_strings(observation.get("tags", [])))
        self._touch_recent_list(profile, "concept_tags", _dedupe_strings(observation.get("concept_tags", [])))
        self._touch_recent_list(profile, "catalysts", _dedupe_strings(observation.get("catalysts", [])))
        self._touch_recent_list(profile, "notes", _dedupe_strings(observation.get("notes", [])))
        for theme in _dedupe_strings(observation.get("themes", [])):
            theme_links = profile.setdefault("theme_links", {})
            theme_links[theme] = int(theme_links.get(theme, 0) or 0) + 1
        score = observation.get("methodology_score")
        if isinstance(score, (int, float)):
            total = float(profile.get("methodology_score_total", 0.0) or 0.0) + float(score)
            profile["methodology_score_total"] = round(total, 4)
            profile["avg_methodology_score"] = round(total / max(profile["observation_count"], 1), 2)
        memory.recent_stocks = [stock_code] + [item for item in memory.recent_stocks if item != stock_code]
        return self.save_memory(memory)

    def observe_theme_profile(self, theme: str, observation: dict[str, Any]) -> UserMemory:
        theme_key = str(theme).strip()
        if not theme_key:
            return self.load_memory()
        memory = self.load_memory()
        profile = memory.theme_profiles.setdefault(
            theme_key,
            {
                "theme": theme_key,
                "observation_count": 0,
                "related_stocks": [],
                "sources": {},
                "market_stage_counts": {},
                "community_mood_counts": {},
                "recent_reasons": [],
                "linked_tags": [],
            },
        )
        profile["last_seen"] = shanghai_timestamp_iso()
        profile["last_summary"] = observation.get("summary", profile.get("last_summary", ""))
        profile["last_market_stage"] = observation.get("market_stage", profile.get("last_market_stage", ""))
        profile["observation_count"] = int(profile.get("observation_count", 0) or 0) + 1
        self._bump_counter(profile, "sources", observation.get("source"))
        self._bump_counter(profile, "market_stage_counts", observation.get("market_stage"))
        self._bump_counter(profile, "community_mood_counts", observation.get("community_mood"))
        self._touch_recent_list(profile, "related_stocks", _dedupe_strings(observation.get("related_stocks", [])), limit=20)
        self._touch_recent_list(profile, "recent_reasons", _dedupe_strings(observation.get("reasons", [])))
        self._touch_recent_list(profile, "linked_tags", _dedupe_strings(observation.get("linked_tags", [])))
        heat_score = observation.get("heat_score")
        if isinstance(heat_score, (int, float)):
            total = float(profile.get("heat_score_total", 0.0) or 0.0) + float(heat_score)
            profile["heat_score_total"] = round(total, 4)
            profile["avg_heat_score"] = round(total / max(profile["observation_count"], 1), 2)
        return self.save_memory(memory)

    def remember_workflow(
        self,
        workflow: str,
        *,
        stock_code: str | None = None,
        stock_name: str | None = None,
        summary: str | None = None,
    ) -> UserMemory:
        memory = self.load_memory()
        if stock_code:
            memory.recent_stocks = [stock_code] + [item for item in memory.recent_stocks if item != stock_code]
        entry = {
            "workflow": workflow,
            "stock_code": stock_code or "",
            "stock_name": stock_name or "",
            "summary": summary or "",
            "timestamp": shanghai_timestamp_iso(),
        }
        memory.recent_workflows = [entry] + [
            item
            for item in memory.recent_workflows
            if not (
                item.get("workflow") == entry["workflow"]
                and item.get("stock_code") == entry["stock_code"]
            )
        ]
        return self.save_memory(memory)

    def add_stock_note(self, stock_code: str, note: str) -> UserMemory:
        memory = self.load_memory()
        notes = memory.stock_notes.setdefault(stock_code, [])
        cleaned = str(note).strip()
        if cleaned and cleaned not in notes:
            notes.insert(0, cleaned)
        return self.save_memory(memory)

    def clear_memory(self, stock_code: str | None = None) -> UserMemory:
        if stock_code is None:
            memory = UserMemory()
            return self.save_memory(memory)
        memory = self.load_memory()
        memory.stock_notes.pop(stock_code, None)
        memory.stock_profiles.pop(stock_code, None)
        memory.recent_stocks = [item for item in memory.recent_stocks if item != stock_code]
        memory.recent_workflows = [item for item in memory.recent_workflows if item.get("stock_code") != stock_code]
        for theme, profile in memory.theme_profiles.items():
            related = [item for item in profile.get("related_stocks", []) if item != stock_code]
            profile["related_stocks"] = related
        return self.save_memory(memory)

    def build_context(self, stock_code: str | None = None) -> dict[str, Any]:
        preferences = self.load_preferences()
        memory = self.load_memory()
        payload = {
            "preferences": preferences.to_dict(),
            "memory": {
                "recent_stocks": list(memory.recent_stocks),
                "recent_workflows": list(memory.recent_workflows),
                "stock_notes": {},
                "stock_profiles": memory.stock_profiles,
                "theme_profiles": memory.theme_profiles,
            },
        }
        if stock_code:
            payload["memory"]["stock_notes"] = {
                stock_code: list(memory.stock_notes.get(stock_code, []))
            }
            payload["memory"]["stock_profiles"] = {
                stock_code: dict(memory.stock_profiles.get(stock_code, {}))
            }
            payload["memory"]["is_watchlist_stock"] = stock_code in preferences.watchlist
        return payload
