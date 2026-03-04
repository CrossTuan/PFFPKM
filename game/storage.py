from __future__ import annotations

import json
from pathlib import Path

from .logic import PlayerProfile


class PlayerStore:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._cache: dict[str, dict] | None = None
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.write_text("{}", encoding="utf-8")

    def _read_raw(self) -> dict[str, dict]:
        try:
            content = self.file_path.read_text(encoding="utf-8").strip()
            if not content:
                return {}
            data = json.loads(content)
            if isinstance(data, dict):
                return data
            return {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_raw(self, raw: dict[str, dict]) -> None:
        self.file_path.write_text(
            json.dumps(raw, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )

    def load_all(self) -> dict[int, PlayerProfile]:
        raw = self._read_raw()
        self._cache = raw
        return {int(uid): PlayerProfile.from_dict(data) for uid, data in raw.items()}

    def save_all(self, players: dict[int, PlayerProfile]) -> None:
        serializable = {str(uid): profile.to_dict() for uid, profile in players.items()}
        self._cache = serializable
        self._write_raw(serializable)

    def save_player(self, profile: PlayerProfile) -> None:
        if self._cache is None:
            self._cache = self._read_raw()
        self._cache[str(profile.user_id)] = profile.to_dict()
        self._write_raw(self._cache)
