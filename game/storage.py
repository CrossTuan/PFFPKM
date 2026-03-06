from __future__ import annotations

import json
import os
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


class MongoPlayerStore:
    def __init__(self, uri: str, db_name: str, collection_name: str):
        from pymongo import MongoClient

        self.client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        self.collection = self.client[db_name][collection_name]
        self.client.admin.command("ping")

    def load_all(self) -> dict[int, PlayerProfile]:
        players: dict[int, PlayerProfile] = {}
        for doc in self.collection.find({}):
            payload = dict(doc)
            uid_raw = payload.get("user_id", payload.get("_id"))
            if uid_raw is None:
                continue
            try:
                uid = int(uid_raw)
            except (TypeError, ValueError):
                continue

            payload.pop("_id", None)
            payload["user_id"] = uid
            players[uid] = PlayerProfile.from_dict(payload)
        return players

    def save_all(self, players: dict[int, PlayerProfile]) -> None:
        for uid, profile in players.items():
            payload = profile.to_dict()
            payload["user_id"] = int(uid)
            self.collection.replace_one(
                {"_id": int(uid)},
                {"_id": int(uid), **payload},
                upsert=True,
            )

    def save_player(self, profile: PlayerProfile) -> None:
        uid = int(profile.user_id)
        payload = profile.to_dict()
        payload["user_id"] = uid
        self.collection.replace_one(
            {"_id": uid},
            {"_id": uid, **payload},
            upsert=True,
        )


def create_player_store(file_path: Path):
    mongo_enabled = os.getenv("MONGODB_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
    if not mongo_enabled:
        print(f"[storage] MONGODB_ENABLED=false, using local JSON store at {file_path}.")
        return PlayerStore(file_path)

    mongo_uri = os.getenv("MONGODB_URI", "").strip()
    if mongo_uri:
        db_name = os.getenv("MONGODB_DB", "pffpkm").strip() or "pffpkm"
        collection_name = os.getenv("MONGODB_COLLECTION", "players").strip() or "players"
        try:
            store = MongoPlayerStore(mongo_uri, db_name=db_name, collection_name=collection_name)
            print(f"[storage] Connected to MongoDB: db={db_name}, collection={collection_name}.")
            return store
        except Exception as exc:
            print(
                "[storage] Failed to connect to MongoDB "
                f"({exc.__class__.__name__}: {exc}). "
                f"Falling back to local JSON store at {file_path}."
            )
    else:
        print(f"[storage] MONGODB_URI is empty, using local JSON store at {file_path}.")
    return PlayerStore(file_path)
