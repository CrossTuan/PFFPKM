from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class MoveData:
    name: str
    move_type: str
    category: str
    power: int
    accuracy: int


import json as _json

def get_learnset_for_species(species_name: str, level: int, gen: str = "9") -> list[str]:
    """Trả về danh sách tên move mà species này học được ở level hiện tại (chỉ lấy level-up move, không lấy TM/egg/event)."""
    path = Path(__file__).parent / "learnsets.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        data = _json.load(f)
    species = data.get(species_name.lower())
    if not species:
        return []
    moves = []
    for entry in species.get(gen, []):
        if entry["level"] <= level:
            moves.append(entry["move"])
    if len(moves) <= 4:
        return moves
    # Nếu có nhiều hơn 4 move, chọn ngẫu nhiên 4 move từ danh sách các move đã học được
    return random.sample(moves, 4)

class GameData:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        env_data_root = os.getenv("POKEMON_DATA_ROOT", "").strip()
        if env_data_root:
            self.data_root = Path(env_data_root)
        else:
            local_candidate = project_root / "pokemon-data.json-master"
            parent_candidate = project_root.parent / "pokemon-data.json-master"
            self.data_root = local_candidate if local_candidate.exists() else parent_candidate
        self.pokedex: list[dict[str, Any]] = []
        self.moves: list[dict[str, Any]] = []
        self.items: list[dict[str, Any]] = []
        self.type_chart: dict[str, dict[str, set[str]]] = {}
        self.moves_by_type: dict[str, list[MoveData]] = {}
        self.items_by_name: dict[str, dict[str, Any]] = {}

    def load(self) -> None:
        self.pokedex = self._load_json("pokedex.json")
        self.moves = self._load_json("moves.json")
        self.items = self._load_json("items.json")
        types = self._load_json("types.json")

        self.type_chart = {
            type_info["english"]: {
                "effective": set(type_info.get("effective", [])),
                "ineffective": set(type_info.get("ineffective", [])),
                "no_effect": set(type_info.get("no_effect", [])),
            }
            for type_info in types
        }

        self.moves_by_type = {}
        for raw_move in self.moves:
            power_raw = str(raw_move.get("power", "0"))
            try:
                power = int(power_raw)
            except ValueError:
                power = 0
            if power <= 0:
                continue

            accuracy_raw = str(raw_move.get("accuracy", "100")).replace("%", "")
            try:
                accuracy = int(float(accuracy_raw))
            except ValueError:
                accuracy = 100

            move = MoveData(
                name=raw_move["name"]["english"],
                move_type=raw_move.get("type", "Normal"),
                category=raw_move.get("category", "Physical"),
                power=power,
                accuracy=max(1, min(100, accuracy)),
            )
            self.moves_by_type.setdefault(move.move_type, []).append(move)

        self.items_by_name = {
            item["name"]["english"]: item
            for item in self.items
            if item.get("name", {}).get("english")
        }

    def _load_json(self, filename: str) -> list[dict[str, Any]]:
        path = self.data_root / filename
        if not path.exists():
            raise FileNotFoundError(f"Missing data file: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def get_pokemon_by_name(self, name: str) -> dict[str, Any] | None:
        lowered = name.lower()
        for pkmn in self.pokedex:
            if pkmn["name"]["english"].lower() == lowered:
                return pkmn
        return None

    def random_wild_choices(self, count: int = 5) -> list[dict[str, Any]]:
        pool = [p for p in self.pokedex if p.get("id", 0) <= 251]
        return random.sample(pool, k=min(count, len(pool)))

    def random_moves_for_species(self, species_types: list[str], count: int = 4) -> list[MoveData]:
        selected: list[MoveData] = []
        for type_name in species_types:
            candidates = self.moves_by_type.get(type_name, [])
            if candidates:
                selected.append(random.choice(candidates))

        flat_pool = [move for moves in self.moves_by_type.values() for move in moves]
        while len(selected) < count and flat_pool:
            move = random.choice(flat_pool)
            if move.name not in {m.name for m in selected}:
                selected.append(move)

        return selected[:count]

    def type_multiplier(self, attack_type: str, defender_types: list[str]) -> float:
        chart = self.type_chart.get(attack_type)
        if not chart:
            return 1.0

        multiplier = 1.0
        for defender_type in defender_types:
            if defender_type in chart["no_effect"]:
                return 0.0
            if defender_type in chart["effective"]:
                multiplier *= 2.0
            elif defender_type in chart["ineffective"]:
                multiplier *= 0.5
        return multiplier
