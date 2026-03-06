from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any


from .data_loader import GameData, MoveData
from .ability_effects import get_ability_effect
from .battle_state_effects import (
    apply_end_of_turn_status,
    apply_leech_seed_drain,
    apply_switch_in_hazards,
    decrement_side_conditions,
    residual_status_damage,
)
from .move_effects import get_default_target, get_move_priority, resolve_status_move_effect
from .item_logic import (
    apply_pp_item_for_pokemon,
    apply_held_item_stat_modifiers,
    calculate_catch_chance,
    consume_eject_pack_for,
    consume_pending_eject_pack,
    get_healing_item_amount,
    get_pp_restore_item,
    get_revive_item,
    get_screen_duration,
    get_status_cure_item,
    get_terrain_duration,
    get_weather_duration,
    get_x_item_stat,
    is_choice_item,
    is_disliked_pinch_flavor,
    resolve_held_item_name,
    trigger_active_terrain_seeds,
    trigger_active_room_service,
    trigger_berry_effects,
    try_activate_booster_energy,
    try_activate_terrain_seed,
    try_activate_room_service,
    try_consume_mental_herb,
)


ZERO_POWER_DAMAGING_MOVES = {
    "Black Hole Eclipse",
    "Bloom Doom",
    "Breakneck Blitz",
    "Continental Crush",
    "Corkscrew Crash",
    "Catastropika",
    "Clangorous Soulblaze",
    "Devastating Drake",
    "Final Gambit",
    "G-Max Centiferno",
    "G-Max Chi Strike",
    "G-Max Cuddle",
    "G-Max Depletion",
    "G-Max Drum Solo",
    "G-Max Finale",
    "G-Max Fireball",
    "G-Max Foam Burst",
    "G-Max Gold Rush",
    "G-Max Gravitas",
    "G-Max Hydrosnipe",
    "G-Max Malodor",
    "G-Max Meltdown",
    "G-Max One Blow",
    "G-Max Rapid Flow",
    "G-Max Replenish",
    "G-Max Resonance",
    "G-Max Sandblast",
    "G-Max Smite",
    "G-Max Snooze",
    "G-Max Steelsurge",
    "G-Max Stonesurge",
    "G-Max Stun Shock",
    "G-Max Sweetness",
    "G-Max Tartness",
    "G-Max Terror",
        "Max Airstream",
        "Max Darkness",
        "Max Flare",
        "Max Flutterby",
        "Max Geyser",
        "Max Hailstorm",
        "Max Knuckle",
        "Max Lightning",
        "Max Mindstorm",
        "Max Ooze",
        "Max Overgrowth",
        "Max Phantasm",
        "Max Quake",
        "Max Rockfall",
    "G-Max Vine Lash",
    "G-Max Volcalith",
    "G-Max Volt Crash",
    "G-Max Wildfire",
    "G-Max Wind Rage",
    "Gigavolt Havoc",
    "Fissure",
    "Guillotine",
    "Guardian of Alola",
    "Flail",
    "Frustration",
    "Fling",
    "Gyro Ball",
    "Grass Knot",
    "Hard Press",
    "Heat Crash",
    "Heavy Slam",
    "Horn Drill",
    "Hydro Vortex",
    "Hold Back",
    "Hex",
    "Inferno Overdrive",
    "Nature's Madness",
    "Night Shade",
    "Never-Ending Nightmare",
    "Oceanic Operetta",
    "Psywave",
    "Punishment",
    "Pulverizing Pancake",
    "Ruination",
    "Savage Spin-Out",
    "Searing Sunraze Smash",
    "Subzero Slammer",
    "Supersonic Skystrike",
    "Spit Up",
    "Present",
}
ZERO_POWER_DAMAGE_OVERRIDES = {
    "Black Hole Eclipse": 180,
    "Bloom Doom": 180,
    "Breakneck Blitz": 180,
    "Continental Crush": 180,
    "Corkscrew Crash": 180,
    "Catastropika": 210,
    "Clangorous Soulblaze": 185,
    "Devastating Drake": 180,
    "G-Max Centiferno": 130,
    "G-Max Chi Strike": 130,
    "G-Max Cuddle": 130,
    "G-Max Depletion": 130,
    "G-Max Drum Solo": 160,
    "G-Max Finale": 130,
    "G-Max Fireball": 160,
    "G-Max Foam Burst": 130,
    "G-Max Gold Rush": 130,
    "G-Max Gravitas": 130,
    "G-Max Hydrosnipe": 160,
    "G-Max Malodor": 130,
    "G-Max Meltdown": 130,
    "G-Max One Blow": 130,
    "G-Max Rapid Flow": 130,
    "G-Max Replenish": 130,
    "G-Max Resonance": 130,
    "G-Max Sandblast": 130,
    "G-Max Smite": 130,
    "G-Max Snooze": 130,
    "G-Max Steelsurge": 130,
    "G-Max Stonesurge": 130,
    "G-Max Stun Shock": 130,
    "G-Max Sweetness": 130,
    "G-Max Tartness": 130,
    "G-Max Terror": 130,
    "G-Max Vine Lash": 130,
    "G-Max Volcalith": 130,
    "G-Max Volt Crash": 130,
    "G-Max Wildfire": 130,
    "G-Max Wind Rage": 130,
    "Gigavolt Havoc": 180,
    "Hydro Vortex": 180,
    "Inferno Overdrive": 180,
    "Never-Ending Nightmare": 180,
    "Oceanic Operetta": 195,
    "Pulverizing Pancake": 210,
    "Savage Spin-Out": 190,
    "Searing Sunraze Smash": 200,
    "Subzero Slammer": 180,
    "Supersonic Skystrike": 190,
    "Spit Up": 100,
    "Present": 40,
}


@dataclass(slots=True)
class MoveSet:
    name: str
    move_type: str
    category: str
    power: int
    accuracy: int
    base_pp: int = 1
    max_pp: int = 1
    current_pp: int = 1
    pp_up_level: int = 0
    makes_contact: bool = False
    target: str = "any"
    priority: int = 0


STAT_KEYS = ["HP", "Attack", "Defense", "Sp. Attack", "Sp. Defense", "Speed"]
EV_STAT_CAP = 252
EV_TOTAL_CAP = 510
HAPPINESS_MIN = 0
HAPPINESS_MAX = 255
HAPPINESS_START = 70
HAPPINESS_EVOLVE_THRESHOLD = 220

NATURE_EFFECTS: dict[str, tuple[str | None, str | None]] = {
    "Hardy": (None, None),
    "Lonely": ("attack", "defense"),
    "Brave": ("attack", "speed"),
    "Adamant": ("attack", "sp_attack"),
    "Naughty": ("attack", "sp_defense"),
    "Bold": ("defense", "attack"),
    "Docile": (None, None),
    "Relaxed": ("defense", "speed"),
    "Impish": ("defense", "sp_attack"),
    "Lax": ("defense", "sp_defense"),
    "Timid": ("speed", "attack"),
    "Hasty": ("speed", "defense"),
    "Serious": (None, None),
    "Jolly": ("speed", "sp_attack"),
    "Naive": ("speed", "sp_defense"),
    "Modest": ("sp_attack", "attack"),
    "Mild": ("sp_attack", "defense"),
    "Quiet": ("sp_attack", "speed"),
    "Bashful": (None, None),
    "Rash": ("sp_attack", "sp_defense"),
    "Calm": ("sp_defense", "attack"),
    "Gentle": ("sp_defense", "defense"),
    "Sassy": ("sp_defense", "speed"),
    "Careful": ("sp_defense", "sp_attack"),
    "Quirky": (None, None),
}


def _nature_multiplier(nature: str, stat_key: str) -> float:
    up, down = NATURE_EFFECTS.get(nature, (None, None))
    if up == stat_key:
        return 1.1
    if down == stat_key:
        return 0.9
    return 1.0


def _clamp_happiness(value: int) -> int:
    return max(HAPPINESS_MIN, min(HAPPINESS_MAX, int(value)))


def add_happiness(pokemon: "PokemonInstance", amount: int) -> int:
    before = _clamp_happiness(getattr(pokemon, "happiness", HAPPINESS_START))
    after = _clamp_happiness(before + int(amount))
    pokemon.happiness = after
    return after - before


def get_species_by_id(game_data: GameData, species_id: int) -> dict[str, Any] | None:
    target = int(species_id)
    for species in game_data.pokedex:
        try:
            if int(species.get("id", -1)) == target:
                return species
        except (TypeError, ValueError):
            continue
    return None


def recalculate_pokemon_stats(game_data: GameData, pokemon: "PokemonInstance", preserve_current_hp_ratio: bool = True) -> None:
    species = get_species_by_id(game_data, pokemon.species_id)
    if not species:
        return

    base = species.get("base", {})
    old_max_hp = max(1, int(getattr(pokemon, "max_hp", 1)))
    old_current_hp = max(0, int(getattr(pokemon, "current_hp", 0)))
    hp_ratio = old_current_hp / old_max_hp if old_max_hp > 0 else 0.0

    ivs = {k: int(v) for k, v in getattr(pokemon, "ivs", {}).items()} or {k: 0 for k in STAT_KEYS}
    evs = {k: int(v) for k, v in getattr(pokemon, "evs", {}).items()} or {k: 0 for k in STAT_KEYS}
    level = max(1, int(getattr(pokemon, "level", 1)))
    nature = str(getattr(pokemon, "nature", "Hardy"))

    hp = int(((2 * int(base.get("HP", 1)) + ivs.get("HP", 0) + (evs.get("HP", 0) // 4)) * level) / 100) + level + 10
    attack_base = int(((2 * int(base.get("Attack", 1)) + ivs.get("Attack", 0) + (evs.get("Attack", 0) // 4)) * level) / 100) + 5
    defense_base = int(((2 * int(base.get("Defense", 1)) + ivs.get("Defense", 0) + (evs.get("Defense", 0) // 4)) * level) / 100) + 5
    sp_attack_base = int(((2 * int(base.get("Sp. Attack", 1)) + ivs.get("Sp. Attack", 0) + (evs.get("Sp. Attack", 0) // 4)) * level) / 100) + 5
    sp_defense_base = int(((2 * int(base.get("Sp. Defense", 1)) + ivs.get("Sp. Defense", 0) + (evs.get("Sp. Defense", 0) // 4)) * level) / 100) + 5
    speed_base = int(((2 * int(base.get("Speed", 1)) + ivs.get("Speed", 0) + (evs.get("Speed", 0) // 4)) * level) / 100) + 5

    pokemon.max_hp = max(1, hp)
    pokemon.attack = max(1, int(attack_base * _nature_multiplier(nature, "attack")))
    pokemon.defense = max(1, int(defense_base * _nature_multiplier(nature, "defense")))
    pokemon.sp_attack = max(1, int(sp_attack_base * _nature_multiplier(nature, "sp_attack")))
    pokemon.sp_defense = max(1, int(sp_defense_base * _nature_multiplier(nature, "sp_defense")))
    pokemon.speed = max(1, int(speed_base * _nature_multiplier(nature, "speed")))

    if preserve_current_hp_ratio:
        if old_current_hp <= 0:
            pokemon.current_hp = 0
        else:
            pokemon.current_hp = max(1, min(pokemon.max_hp, int(round(pokemon.max_hp * hp_ratio))))
    else:
        hp_delta = pokemon.max_hp - old_max_hp
        pokemon.current_hp = max(0, min(pokemon.max_hp, old_current_hp + hp_delta))


def derive_ev_yield_from_species(species: dict[str, Any] | None) -> tuple[str, int]:
    if not species:
        return "HP", 1
    base = species.get("base", {}) or {}
    best_key = "HP"
    best_value = int(base.get("HP", 0))
    for stat_key in STAT_KEYS:
        value = int(base.get(stat_key, 0))
        if value > best_value:
            best_key = stat_key
            best_value = value
    if best_value >= 120:
        amount = 3
    elif best_value >= 80:
        amount = 2
    else:
        amount = 1
    return best_key, amount


def award_evs(pokemon: "PokemonInstance", stat_key: str, amount: int) -> int:
    if not getattr(pokemon, "evs", None):
        pokemon.evs = {k: 0 for k in STAT_KEYS}
    for key in STAT_KEYS:
        pokemon.evs[key] = max(0, int(pokemon.evs.get(key, 0)))

    amount = max(0, int(amount))
    if amount == 0:
        return 0

    total_now = sum(int(pokemon.evs.get(k, 0)) for k in STAT_KEYS)
    remaining_total = max(0, EV_TOTAL_CAP - total_now)
    current_stat = int(pokemon.evs.get(stat_key, 0))
    remaining_stat = max(0, EV_STAT_CAP - current_stat)
    gain = min(amount, remaining_total, remaining_stat)
    if gain <= 0:
        return 0

    pokemon.evs[stat_key] = current_stat + gain
    return gain


def _parse_move_numeric(raw_value: Any, default: int = 0) -> int:
    text = str(raw_value).strip()
    if not text or text == "—":
        return default
    cleaned = text.replace("%", "").replace("*", "").strip()
    try:
        return int(float(cleaned))
    except (ValueError, TypeError):
        return default


def _max_pp_from_base(base_pp: int) -> int:
    return max(1, int(base_pp * 8 / 5))


def _max_pp_from_stage(base_pp: int, pp_up_level: int) -> int:
    level = max(0, min(3, pp_up_level))
    return max(1, int(base_pp * (5 + level) / 5))


def _stage_multiplier(stage: int) -> float:
    stage = max(-6, min(6, stage))
    if stage >= 0:
        return (2 + stage) / 2
    return 2 / (2 - stage)


def get_default_ability_for_species(species: dict[str, Any]) -> str:
    abilities = species.get("profile", {}).get("ability", [])
    if not abilities:
        return ""

    for ability_entry in abilities:
        if isinstance(ability_entry, list) and len(ability_entry) >= 2:
            ability_name = str(ability_entry[0])
            hidden_flag = str(ability_entry[1]).strip().lower()
            if hidden_flag == "false":
                return ability_name

    first = abilities[0]
    if isinstance(first, list) and first:
        return str(first[0])
    if isinstance(first, str):
        return first
    return ""


@dataclass(slots=True)
class PokemonInstance:
    species_id: int
    name: str
    level: int
    types: list[str]
    max_hp: int
    attack: int
    defense: int
    sp_attack: int
    sp_defense: int
    speed: int
    current_hp: int
    moves: list[MoveSet]
    ivs: dict[str, int] = field(default_factory=dict)
    evs: dict[str, int] = field(default_factory=dict)
    nature: str = "Hardy"
    exp: int = 0
    hold_item: str | None = None
    berry_consumed: bool = False
    is_dynamaxed: bool = False
    image_url: str | None = None
    owner_id: int | None = None
    ability: str = ""
    status: str | None = None
    status_counter: int = 0
    confusion_turns: int = 0
    happiness: int = HAPPINESS_START

    @staticmethod
    def exp_for_level(level: int) -> int:
        return max(0, level**3)

    def exp_to_next_level(self) -> int:
        return max(0, self.exp_for_level(self.level + 1) - self.exp)

    def to_dict(self) -> dict[str, Any]:
        return {
            "species_id": self.species_id,
            "name": self.name,
            "level": self.level,
            "types": self.types,
            "max_hp": self.max_hp,
            "attack": self.attack,
            "defense": self.defense,
            "sp_attack": self.sp_attack,
            "sp_defense": self.sp_defense,
            "speed": self.speed,
            "current_hp": self.current_hp,
            "moves": [
                {
                    "name": move.name,
                    "move_type": move.move_type,
                    "category": move.category,
                    "power": move.power,
                    "accuracy": move.accuracy,
                    "base_pp": move.base_pp,
                    "max_pp": move.max_pp,
                    "current_pp": move.current_pp,
                    "pp_up_level": move.pp_up_level,
                    "makes_contact": move.makes_contact,
                    "target": move.target,
                    "priority": move.priority,
                }
                for move in self.moves
            ],
            "ivs": self.ivs,
            "evs": self.evs,
            "nature": self.nature,
            "exp": self.exp,
            "hold_item": self.hold_item,
            "berry_consumed": self.berry_consumed,
            "is_dynamaxed": self.is_dynamaxed,
            "image_url": self.image_url,
            "owner_id": self.owner_id,
            "ability": self.ability,
            "status": self.status,
            "status_counter": self.status_counter,
            "confusion_turns": self.confusion_turns,
            "happiness": self.happiness,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PokemonInstance":
        parsed_moves: list[MoveSet] = []
        for m in data.get("moves", []):
            base_pp = int(m.get("base_pp", 0) or 0)
            max_pp = int(m.get("max_pp", 0) or 0)
            saved_current = m.get("current_pp")
            pp_up_level_raw = int(m.get("pp_up_level", 0) or 0)
            pp_up_level = max(0, min(3, pp_up_level_raw))
            if base_pp <= 0 and max_pp > 0:
                base_pp = max(1, int(max_pp * 5 / 8))
            if base_pp <= 0:
                base_pp = 1
            if max_pp > base_pp and pp_up_level == 0:
                inferred = round((max_pp / base_pp - 1) * 5)
                if inferred in {1, 2, 3}:
                    pp_up_level = inferred
            target_max_pp = _max_pp_from_stage(base_pp, pp_up_level)
            if max_pp <= 0:
                max_pp = target_max_pp
            else:
                max_pp = target_max_pp
            if saved_current is None:
                current_pp = max_pp
            else:
                current_pp = max(0, min(max_pp, int(saved_current)))

            parsed_moves.append(
                MoveSet(
                    name=m["name"],
                    move_type=m["move_type"],
                    category=m["category"],
                    power=int(m.get("power", 0)),
                    accuracy=int(m.get("accuracy", 100)),
                    base_pp=base_pp,
                    max_pp=max_pp,
                    current_pp=current_pp,
                    pp_up_level=pp_up_level,
                    makes_contact=bool(m.get("makes_contact", False)),
                    target=str(m.get("target", "any")),
                    priority=int(m.get("priority", 0)),
                )
            )

        return cls(
            species_id=int(data["species_id"]),
            name=data["name"],
            level=int(data["level"]),
            types=list(data["types"]),
            max_hp=int(data["max_hp"]),
            attack=int(data["attack"]),
            defense=int(data["defense"]),
            sp_attack=int(data["sp_attack"]),
            sp_defense=int(data["sp_defense"]),
            speed=int(data["speed"]),
            current_hp=int(data["current_hp"]),
            moves=parsed_moves,
            ivs={k: int(v) for k, v in data.get("ivs", {}).items()} or {k: 0 for k in STAT_KEYS},
            evs={k: int(v) for k, v in data.get("evs", {}).items()} or {k: 0 for k in STAT_KEYS},
            nature=str(data.get("nature", "Hardy")),
            exp=int(data.get("exp", int(data.get("level", 1)) ** 3)),
            hold_item=data.get("hold_item"),
            berry_consumed=bool(data.get("berry_consumed", False)),
            is_dynamaxed=bool(data.get("is_dynamaxed", False)),
            image_url=data.get("image_url"),
            owner_id=data.get("owner_id"),
            ability=data.get("ability", ""),
            status=data.get("status"),
            status_counter=int(data.get("status_counter", 0)),
            confusion_turns=int(data.get("confusion_turns", 0)),
            happiness=_clamp_happiness(int(data.get("happiness", HAPPINESS_START))),
        )


@dataclass(slots=True)
class PlayerProfile:
    user_id: int
    started: bool = False
    money: int = 0
    inventory: dict[str, int] = field(default_factory=dict)
    party: list[PokemonInstance] = field(default_factory=list)
    pc: list[PokemonInstance] = field(default_factory=list)
    gym_badges: dict[str, int] = field(default_factory=dict)
    gym_run: dict[str, Any] | None = None
    last_chat_happiness_at: int = 0
    center_uses_date: str = ""
    center_uses_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "started": self.started,
            "money": self.money,
            "inventory": self.inventory,
            "party": [p.to_dict() for p in self.party],
            "pc": [p.to_dict() for p in self.pc],
            "gym_badges": self.gym_badges,
            "gym_run": self.gym_run,
            "last_chat_happiness_at": self.last_chat_happiness_at,
            "center_uses_date": self.center_uses_date,
            "center_uses_count": self.center_uses_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlayerProfile":
        return cls(
            user_id=int(data["user_id"]),
            started=bool(data.get("started", False)),
            money=int(data.get("money", 0)),
            inventory={k: int(v) for k, v in data.get("inventory", {}).items()},
            party=[PokemonInstance.from_dict(p) for p in data.get("party", [])],
            pc=[PokemonInstance.from_dict(p) for p in data.get("pc", [])],
            gym_badges={k: int(v) for k, v in data.get("gym_badges", {}).items()},
            gym_run=data.get("gym_run") if isinstance(data.get("gym_run"), dict) else None,
            last_chat_happiness_at=int(data.get("last_chat_happiness_at", 0)),
            center_uses_date=str(data.get("center_uses_date", "")),
            center_uses_count=max(0, int(data.get("center_uses_count", 0))),
        )


@dataclass(slots=True)
class TurnResult:
    text: str
    battle_over: bool = False
    caught: bool = False
    success: bool = True


class Battle:
    def switch_pokemon(self, new_index: int) -> TurnResult:
        """
        Đổi sang Pokémon khác trong party (nếu còn sống và không phải đang active)
        """
        if new_index < 0 or new_index >= len(self.player.party):
            return TurnResult("Vị trí không hợp lệ.", success=False)
        if new_index == self.player_active_index:
            return TurnResult(f"{self.player.party[new_index].name} đã ở trên sân.", success=False)
        if self.player.party[new_index].current_hp <= 0:
            return TurnResult(f"{self.player.party[new_index].name} đã gục, không thể vào sân.", success=False)
        if self.player_trapped_turns > 0 and self._held_item_name(self.player_active) != "shed shell":
            return TurnResult("Pokémon hiện tại đang bị giữ chân, không thể đổi Pokémon.", success=False)
        if self.player_ingrain:
            return TurnResult("Pokémon hiện tại đang bám rễ bằng Ingrain, không thể đổi Pokémon.", success=False)
        old_active = self.player_active
        self.booster_energy_boost_stat.pop(id(old_active), None)
        if old_active.status == "tox":
            old_active.status_counter = 1
        self._reset_player_stages()
        self.player_seeded = False
        self.player_ingrain = False
        self.player_aqua_ring = False
        self.player_trapped_turns = 0
        self.player_bound_turns = 0
        self.player_flinched = False
        self.player_bounce_charging = False
        self.player_dig_charging = False
        self.player_dive_charging = False
        self.player_fly_charging = False
        self.player_freeze_shock_charging = False
        self.player_destiny_bond_active = False
        self.player_cursed = False
        self.player_focus_energy = False
        self.player_identified = False
        self.player_fury_cutter_chain = 0
        self.player_geomancy_charging = False
        self.player_glaive_rush_vulnerable_turns = 0
        self.player_ice_burn_charging = False
        self.player_ice_ball_chain = 0
        self.player_rollout_chain = 0
        self.player_electrified = False
        self.player_electro_shot_charging = False
        self.player_endure_active = False
        self.player_encore_turns = 0
        self.player_encore_move = None
        self.wild_imprisoned_moves = set()
        self.player_heal_block_turns = 0
        self.player_last_move_name = None
        self.player_lock_on_ready = False
        self.player_magnet_rise_turns = 0
        self.player_miracle_eye = False
        self.player_nightmare = False
        self.player_octolock = False
        self.player_outrage_turns = 0
        self.player_perish_song_turns = 0
        self.player_salt_cure_turns = 0
        self.player_syrup_bomb_turns = 0
        self.player_stockpile_count = 0
        self.player_taunt_turns = 0
        self.player_throat_chop_turns = 0
        self.player_torment_turns = 0
        self.player_tar_shot = False
        self.player_powdered = False
        self.player_rage_active = False
        self.player_hit_count = 0
        self.player_razor_wind_charging = False
        self.player_sky_attack_charging = False
        self.player_skull_bash_charging = False
        self.player_sky_drop_charging = False
        self.player_solar_beam_charging = False
        self.player_solar_blade_charging = False
        self.player_roost_original_types = None
        self.player_smack_down_grounded = False
        self.player_choice_lock_move = None
        self.player_metronome_move = None
        self.player_metronome_chain = 0
        self.player_micle_accuracy_boost = False
        self.player_lansat_crit_boost = False
        self.player_active_index = new_index
        self.player_yawn_turns = 0
        self.player_infatuated = False
        self.wild_infatuated = False
        pkmn = self.player.party[new_index]
        hazard_logs = self._apply_switch_in_hazards(pkmn, is_player=True)
        ability_logs = self._trigger_switch_in_ability(pkmn, is_player=True)
        wish_logs = self._apply_healing_wish_on_switch_in(pkmn, is_player=True)
        text = f"Bạn đã đổi sang {pkmn.name}."
        if hazard_logs:
            text = text + "\n" + "\n".join(hazard_logs)
        if ability_logs:
            text = text + "\n" + "\n".join(ability_logs)
        if wish_logs:
            text = text + "\n" + "\n".join(wish_logs)
        return TurnResult(text)
    def __init__(
        self,
        game_data: GameData,
        player: PlayerProfile,
        wild: PokemonInstance,
        *,
        exp_multiplier: float = 1.0,
        money_multiplier: float = 1.0,
        allow_catch: bool = True,
        allow_run: bool = True,
        opponent_is_trainer: bool = False,
        opponent_exp_coefficient: float | None = None,
    ):
        self.rng = random
        self.game_data = game_data
        self.player = player
        self.wild = wild
        self._victory_rewards_granted = False

        # Defensive fix: some persisted/edge states can produce a fainted wild on entry.
        self.wild.max_hp = max(1, int(getattr(self.wild, "max_hp", 1)))
        if int(getattr(self.wild, "current_hp", 0)) <= 0:
            self.wild.current_hp = self.wild.max_hp

        self.exp_multiplier = max(0.0, float(exp_multiplier))
        self.money_multiplier = max(0.0, float(money_multiplier))
        self.allow_catch = bool(allow_catch)
        self.allow_run = bool(allow_run)
        self.opponent_is_trainer = bool(opponent_is_trainer)
        self.opponent_exp_coefficient = (
            None if opponent_exp_coefficient is None else float(opponent_exp_coefficient)
        )
        self.player_active_index = self._first_alive(player.party)
        self.turn_count = 1
        self.player_stat_stages: dict[str, int] = {
            "attack": 0,
            "defense": 0,
            "sp_attack": 0,
            "sp_defense": 0,
            "speed": 0,
        }
        self.wild_stat_stages: dict[str, int] = {
            "attack": 0,
            "defense": 0,
            "sp_attack": 0,
            "sp_defense": 0,
            "speed": 0,
        }
        self.player_z_power_used = False
        self.player_protect_chain = 0
        self.wild_protect_chain = 0
        self.player_protect_active = False
        self.wild_protect_active = False

        self.player_reflect_turns = 0
        self.player_light_screen_turns = 0
        self.wild_reflect_turns = 0
        self.wild_light_screen_turns = 0

        self.player_spikes_layers = 0
        self.player_toxic_spikes_layers = 0
        self.player_stealth_rock = False
        self.player_sticky_web = False
        self.wild_spikes_layers = 0
        self.wild_toxic_spikes_layers = 0
        self.wild_stealth_rock = False
        self.wild_sticky_web = False

        self.player_seeded = False
        self.wild_seeded = False
        self.player_aqua_ring = False
        self.wild_aqua_ring = False
        self.player_flinched = False
        self.wild_flinched = False
        self.player_infatuated = False
        self.wild_infatuated = False
        self.player_trapped_turns = 0
        self.wild_trapped_turns = 0
        self.player_took_damage_this_turn = False
        self.wild_took_damage_this_turn = False
        self.player_baneful_bunker_active = False
        self.wild_baneful_bunker_active = False
        self.player_burning_bulwark_active = False
        self.wild_burning_bulwark_active = False
        self.player_kings_shield_active = False
        self.wild_kings_shield_active = False
        self.player_silk_trap_active = False
        self.wild_silk_trap_active = False
        self.player_obstruct_active = False
        self.wild_obstruct_active = False
        self.player_crafty_shield_active = False
        self.wild_crafty_shield_active = False
        self.player_magic_coat_active = False
        self.wild_magic_coat_active = False
        self.player_snatch_active = False
        self.wild_snatch_active = False
        self.player_obstruct_active = False
        self.wild_obstruct_active = False
        self.player_laser_focus = False
        self.wild_laser_focus = False
        self.player_stats_lowered_this_turn = False
        self.wild_stats_lowered_this_turn = False
        self.ion_deluge_active = False
        self.player_lock_on_ready = False
        self.wild_lock_on_ready = False
        self.player_lucky_chant_turns = 0
        self.wild_lucky_chant_turns = 0
        self.magic_room_turns = 0
        self.player_magnet_rise_turns = 0
        self.wild_magnet_rise_turns = 0
        self.player_miracle_eye = False
        self.wild_miracle_eye = False
        self.player_mist_turns = 0
        self.wild_mist_turns = 0
        self.player_safeguard_turns = 0
        self.wild_safeguard_turns = 0
        self.mud_sport_turns = 0
        self.water_sport_turns = 0
        self.player_nightmare = False
        self.wild_nightmare = False
        self.player_octolock = False
        self.wild_octolock = False
        self.player_outrage_turns = 0
        self.wild_outrage_turns = 0
        self.player_perish_song_turns = 0
        self.wild_perish_song_turns = 0
        self.player_powdered = False
        self.wild_powdered = False
        self.player_quick_guard_active = False
        self.wild_quick_guard_active = False
        self.player_rage_active = False
        self.wild_rage_active = False
        self.player_hit_count = 0
        self.wild_hit_count = 0
        self.player_razor_wind_charging = False
        self.wild_razor_wind_charging = False
        self.player_sky_attack_charging = False
        self.wild_sky_attack_charging = False
        self.player_skull_bash_charging = False
        self.wild_skull_bash_charging = False
        self.player_sky_drop_charging = False
        self.wild_sky_drop_charging = False
        self.player_solar_beam_charging = False
        self.wild_solar_beam_charging = False
        self.player_solar_blade_charging = False
        self.wild_solar_blade_charging = False
        self.player_spiky_shield_active = False
        self.wild_spiky_shield_active = False
        self.player_roost_original_types: list[str] | None = None
        self.wild_roost_original_types: list[str] | None = None
        self.player_salt_cure_turns = 0
        self.wild_salt_cure_turns = 0
        self.player_syrup_bomb_turns = 0
        self.wild_syrup_bomb_turns = 0
        self.player_smack_down_grounded = False
        self.wild_smack_down_grounded = False
        self.player_stockpile_count = 0
        self.wild_stockpile_count = 0
        self.player_taunt_turns = 0
        self.wild_taunt_turns = 0
        self.player_throat_chop_turns = 0
        self.wild_throat_chop_turns = 0
        self.player_torment_turns = 0
        self.wild_torment_turns = 0
        self.player_yawn_turns = 0
        self.wild_yawn_turns = 0
        self.player_tar_shot = False
        self.wild_tar_shot = False
        self.player_tailwind_turns = 0
        self.wild_tailwind_turns = 0
        self.player_micle_accuracy_boost = False
        self.wild_micle_accuracy_boost = False
        self.player_lansat_crit_boost = False
        self.wild_lansat_crit_boost = False
        self.player_eject_pack_pending = False
        self.wild_eject_pack_pending = False
        self.player_switched_this_turn = False
        self.wild_switched_this_turn = False
        self.player_retaliate_ready = False
        self.wild_retaliate_ready = False
        self.pay_day_bonus = 0
        self.player_charge_boost = False
        self.wild_charge_boost = False
        self.player_bounce_charging = False
        self.wild_bounce_charging = False
        self.player_phantom_force_charging = False
        self.wild_phantom_force_charging = False
        self.player_dig_charging = False
        self.wild_dig_charging = False
        self.player_dive_charging = False
        self.wild_dive_charging = False
        self.player_disabled_move: str | None = None
        self.wild_disabled_move: str | None = None
        self.player_disable_turns = 0
        self.wild_disable_turns = 0
        self.player_destiny_bond_active = False
        self.wild_destiny_bond_active = False
        self.player_grudge_active = False
        self.wild_grudge_active = False
        self.player_cursed = False
        self.wild_cursed = False
        self.player_bound_turns = 0
        self.wild_bound_turns = 0
        self.player_bound_damage_divisor = 8
        self.wild_bound_damage_divisor = 8
        self.player_must_recharge = False
        self.wild_must_recharge = False
        self.player_endure_active = False
        self.wild_endure_active = False
        self.player_embargo_turns = 0
        self.wild_embargo_turns = 0
        self.player_encore_turns = 0
        self.wild_encore_turns = 0
        self.player_encore_move: str | None = None
        self.wild_encore_move: str | None = None
        self.player_electrified = False
        self.wild_electrified = False
        self.player_electro_shot_charging = False
        self.wild_electro_shot_charging = False
        self.player_fly_charging = False
        self.wild_fly_charging = False
        self.player_freeze_shock_charging = False
        self.wild_freeze_shock_charging = False
        self.player_focus_energy = False
        self.wild_focus_energy = False
        self.player_identified = False
        self.wild_identified = False
        self.player_fury_cutter_chain = 0
        self.wild_fury_cutter_chain = 0
        self.player_future_sight_turns = 0
        self.wild_future_sight_turns = 0
        self.player_future_sight_damage = 0
        self.wild_future_sight_damage = 0
        self.player_cannonade_turns = 0
        self.wild_cannonade_turns = 0
        self.player_vine_lash_turns = 0
        self.wild_vine_lash_turns = 0
        self.player_wildfire_turns = 0
        self.wild_wildfire_turns = 0
        self.player_volcalith_turns = 0
        self.wild_volcalith_turns = 0
        self.player_glaive_rush_vulnerable_turns = 0
        self.wild_glaive_rush_vulnerable_turns = 0
        self.player_geomancy_charging = False
        self.wild_geomancy_charging = False
        self.player_echoed_voice_chain = 0
        self.wild_echoed_voice_chain = 0
        self.player_happy_hour_active = False
        self.player_heal_block_turns = 0
        self.wild_heal_block_turns = 0
        self.player_healing_wish_pending = False
        self.wild_healing_wish_pending = False
        self.player_ingrain = False
        self.wild_ingrain = False
        self.player_imprisoned_moves: set[str] = set()
        self.wild_imprisoned_moves: set[str] = set()
        self.player_ice_burn_charging = False
        self.wild_ice_burn_charging = False
        self.player_ice_ball_chain = 0
        self.wild_ice_ball_chain = 0
        self.player_rollout_chain = 0
        self.wild_rollout_chain = 0
        self.move_usage_history: dict[int, set[str]] = {}
        self.player_metronome_move: str | None = None
        self.wild_metronome_move: str | None = None
        self.player_metronome_chain = 0
        self.wild_metronome_chain = 0
        self.booster_energy_boost_stat: dict[int, str] = {}
        self.player_last_move_name: str | None = None
        self.wild_last_move_name: str | None = None
        self.player_beak_blast_heating = False
        self.wild_beak_blast_heating = False
        self.player_bide_turns = 0
        self.wild_bide_turns = 0
        self.player_bide_damage = 0
        self.wild_bide_damage = 0
        self.player_acted_before_wild = False
        self.wild_acted_before_player = False
        self.player_last_damage_taken = 0
        self.wild_last_damage_taken = 0
        self.player_last_physical_damage_taken = 0
        self.wild_last_physical_damage_taken = 0
        self.player_endure_active = False
        self.wild_endure_active = False

        self.player_last_move_type: str | None = None
        self.wild_last_move_type: str | None = None
        self.player_dragon_cheer_turns = 0
        self.wild_dragon_cheer_turns = 0
        self.player_doom_desire_turns = 0
        self.wild_doom_desire_turns = 0
        self.player_doom_desire_damage = 0
        self.wild_doom_desire_damage = 0
        self.weather: str | None = None
        self.weather_turns = 0
        self.terrain: str | None = None
        self.terrain_turns = 0
        self.trick_room_turns = 0
        self.wonder_room_turns = 0
        self.player_wish_turns = 0
        self.wild_wish_turns = 0
        self.player_wish_heal = 0
        self.wild_wish_heal = 0
        self.player_uproar_turns = 0
        self.wild_uproar_turns = 0
        self.player_selected_move_name: str | None = None
        self.wild_selected_move_name: str | None = None
        self.player_choice_lock_move: str | None = None
        self.wild_choice_lock_move: str | None = None
        self.gravity_turns = 0
        self.pending_battle_log = ""

        for pkmn in [*self.player.party, self.wild]:
            for move in pkmn.moves:
                self._normalize_move_pp(move)

        self.pending_battle_log = self._run_turn_zero_phase()

    @property
    def player_active(self) -> PokemonInstance:
        return self.player.party[self.player_active_index]

    def _first_alive(self, team: list[PokemonInstance]) -> int:
        for i, pkmn in enumerate(team):
            if pkmn.current_hp > 0:
                return i
        return 0

    def is_finished(self) -> bool:
        if self.wild.current_hp <= 0:
            return True
        return all(p.current_hp <= 0 for p in self.player.party)

    def run_turn(self, player_move_index: int) -> TurnResult:
        if self.is_finished():
            if self.wild.current_hp <= 0:
                logs = ["Trận đấu đã kết thúc. Pokémon hoang dã đã gục."]
                if (not self._victory_rewards_granted) and any(p.current_hp > 0 for p in self.player.party):
                    self._grant_victory_rewards(self.player_active, logs)
                return TurnResult("\n".join(logs), battle_over=True)
            return TurnResult("Trận đấu đã kết thúc. Đội của bạn đã hết sức chiến đấu.", battle_over=True)

        player_move_index = max(0, min(player_move_index, len(self.player_active.moves) - 1))
        player_move = self.player_active.moves[player_move_index]
        wild_move = self._select_wild_move()
        self.player_selected_move_name = player_move.name if player_move else None
        self.wild_selected_move_name = wild_move.name if wild_move else None
        self.player_beak_blast_heating = player_move.name == "Beak Blast"
        self.wild_beak_blast_heating = wild_move is not None and wild_move.name == "Beak Blast"
        attacker_first, defender_second = self._turn_order(player_move, wild_move)
        self.player_acted_before_wild = attacker_first == "player"
        self.wild_acted_before_player = attacker_first == "wild"
        self.player_protect_active = False
        self.wild_protect_active = False
        self.player_flinched = False
        self.wild_flinched = False
        self.player_took_damage_this_turn = False
        self.wild_took_damage_this_turn = False
        self.player_baneful_bunker_active = False
        self.wild_baneful_bunker_active = False
        self.player_beak_blast_heating = False
        self.wild_beak_blast_heating = False
        self.player_burning_bulwark_active = False
        self.wild_burning_bulwark_active = False
        self.player_kings_shield_active = False
        self.wild_kings_shield_active = False
        self.player_silk_trap_active = False
        self.wild_silk_trap_active = False
        self.player_obstruct_active = False
        self.wild_obstruct_active = False
        self.player_crafty_shield_active = False
        self.wild_crafty_shield_active = False
        self.player_magic_coat_active = False
        self.wild_magic_coat_active = False
        self.player_snatch_active = False
        self.wild_snatch_active = False
        self.player_quick_guard_active = False
        self.wild_quick_guard_active = False
        self.player_spiky_shield_active = False
        self.wild_spiky_shield_active = False
        self.player_destiny_bond_active = False
        self.wild_destiny_bond_active = False
        self.player_grudge_active = False
        self.wild_grudge_active = False
        self.player_stats_lowered_this_turn = False
        self.wild_stats_lowered_this_turn = False
        self.ion_deluge_active = False
        self.player_electrified = False
        self.wild_electrified = False
        self.player_acted_before_wild = False
        self.wild_acted_before_player = False
        self.player_last_damage_taken = 0
        self.wild_last_damage_taken = 0
        self.player_last_physical_damage_taken = 0
        self.wild_last_physical_damage_taken = 0
        self.player_switched_this_turn = False
        self.wild_switched_this_turn = False
        self.player_endure_active = False
        self.wild_endure_active = False

        logs: list[str] = [f"--- Turn {self.turn_count} ---"]
        self.turn_count += 1
        room_service_logs = self._trigger_active_room_service()
        if room_service_logs:
            logs.extend(room_service_logs)

        if attacker_first == "player":
            logs.append(self._perform_player_move(player_move_index))
            if self.wild.current_hp <= 0:
                logs.append(f"{self.wild.name} đã gục!")
                self._grant_victory_rewards(self.player_active, logs)
                return TurnResult("\n".join(logs), battle_over=True)
            logs.append(self._perform_wild_move(wild_move))
        else:
            logs.append(self._perform_wild_move(wild_move))
            if self.player_active.current_hp <= 0:
                switched = self._auto_switch_player()
                if switched:
                    logs.append(switched)
                else:
                    logs.append("Toàn bộ party của bạn đã gục!")
                    return TurnResult("\n".join(logs), battle_over=True)
            logs.append(self._perform_player_move(player_move_index))
            if self.wild.current_hp <= 0:
                logs.append(f"{self.wild.name} đã gục!")
                self._grant_victory_rewards(self.player_active, logs)
                return TurnResult("\n".join(logs), battle_over=True)

        if self.player_active.current_hp <= 0:
            switched = self._auto_switch_player()
            if switched:
                logs.append(switched)
            else:
                logs.append("Toàn bộ party của bạn đã gục!")
                return TurnResult("\n".join(logs), battle_over=True)

        end_turn_logs = self._apply_end_of_turn_status()
        logs.extend(end_turn_logs)

        if self.wild.current_hp <= 0:
            logs.append(f"{self.wild.name} đã gục!")
            self._grant_victory_rewards(self.player_active, logs)
            return TurnResult("\n".join(logs), battle_over=True)

        if self.player_active.current_hp <= 0:
            switched = self._auto_switch_player()
            if switched:
                logs.append(switched)
            else:
                logs.append("Toàn bộ party của bạn đã gục!")
                return TurnResult("\n".join(logs), battle_over=True)

        return TurnResult("\n".join(logs), battle_over=False)

    def run_switch_turn(self, new_index: int) -> TurnResult:
        switch_result = self.switch_pokemon(new_index)
        if not switch_result.success:
            return switch_result

        self.player_flinched = False
        self.wild_flinched = False
        self.player_took_damage_this_turn = False
        self.wild_took_damage_this_turn = False
        self.player_baneful_bunker_active = False
        self.wild_baneful_bunker_active = False
        self.player_endure_active = False
        self.wild_endure_active = False
        self.player_beak_blast_heating = False
        self.wild_beak_blast_heating = False
        self.player_burning_bulwark_active = False
        self.wild_burning_bulwark_active = False
        self.player_kings_shield_active = False
        self.wild_kings_shield_active = False
        self.player_crafty_shield_active = False
        self.wild_crafty_shield_active = False
        self.player_silk_trap_active = False
        self.wild_silk_trap_active = False
        self.player_magic_coat_active = False
        self.wild_magic_coat_active = False
        self.player_snatch_active = False
        self.wild_snatch_active = False
        self.player_quick_guard_active = False
        self.wild_quick_guard_active = False
        self.player_spiky_shield_active = False
        self.wild_spiky_shield_active = False
        self.player_destiny_bond_active = False
        self.wild_destiny_bond_active = False
        self.player_grudge_active = False
        self.wild_grudge_active = False
        self.player_stats_lowered_this_turn = False
        self.wild_stats_lowered_this_turn = False
        self.ion_deluge_active = False
        self.player_electrified = False
        self.wild_electrified = False
        self.player_acted_before_wild = False
        self.wild_acted_before_player = False
        self.player_last_damage_taken = 0
        self.wild_last_damage_taken = 0
        self.player_last_physical_damage_taken = 0
        self.wild_last_physical_damage_taken = 0
        self.player_switched_this_turn = True
        self.wild_switched_this_turn = False

        logs: list[str] = [f"--- Turn {self.turn_count} ---", switch_result.text]
        self.turn_count += 1
        room_service_logs = self._trigger_active_room_service()
        if room_service_logs:
            logs.extend(room_service_logs)

        if self.wild.current_hp > 0:
            logs.append(self._perform_wild_move())
            if self.player_active.current_hp <= 0:
                switched = self._auto_switch_player()
                if switched:
                    logs.append(switched)
                else:
                    logs.append("Toàn bộ party của bạn đã gục!")
                    return TurnResult("\n".join(logs), battle_over=True)

        logs.extend(self._apply_end_of_turn_status())

        if self.wild.current_hp <= 0:
            logs.append(f"{self.wild.name} đã gục!")
            self._grant_victory_rewards(self.player_active, logs)
            return TurnResult("\n".join(logs), battle_over=True)

        if self.player_active.current_hp <= 0:
            switched = self._auto_switch_player()
            if switched:
                logs.append(switched)
            else:
                logs.append("Toàn bộ party của bạn đã gục!")
                return TurnResult("\n".join(logs), battle_over=True)

        return TurnResult("\n".join(logs), battle_over=False)

    def run_item_turn(
        self,
        item_name: str,
        target_index: int | None = None,
        target_move_index: int | None = None,
    ) -> TurnResult:
        item_result = self.use_item(
            item_name,
            target_index=target_index,
            target_move_index=target_move_index,
        )
        if not item_result.success:
            return item_result

        self.player_flinched = False
        self.wild_flinched = False
        self.player_took_damage_this_turn = False
        self.wild_took_damage_this_turn = False
        self.player_baneful_bunker_active = False
        self.wild_baneful_bunker_active = False
        self.player_kings_shield_active = False
        self.wild_kings_shield_active = False
        self.player_obstruct_active = False
        self.wild_obstruct_active = False
        self.player_silk_trap_active = False
        self.wild_silk_trap_active = False
        self.player_magic_coat_active = False
        self.wild_magic_coat_active = False
        self.player_snatch_active = False
        self.wild_snatch_active = False
        self.player_quick_guard_active = False
        self.wild_quick_guard_active = False
        self.player_spiky_shield_active = False
        self.wild_spiky_shield_active = False
        self.player_grudge_active = False
        self.wild_grudge_active = False
        self.player_stats_lowered_this_turn = False
        self.wild_stats_lowered_this_turn = False
        self.ion_deluge_active = False
        self.player_electrified = False
        self.wild_electrified = False
        self.player_switched_this_turn = False
        self.wild_switched_this_turn = False

        logs: list[str] = [f"--- Turn {self.turn_count} ---", item_result.text]
        self.turn_count += 1
        room_service_logs = self._trigger_active_room_service()
        if room_service_logs:
            logs.extend(room_service_logs)

        if self.wild.current_hp > 0:
            logs.append(self._perform_wild_move())
            if self.player_active.current_hp <= 0:
                switched = self._auto_switch_player()
                if switched:
                    logs.append(switched)
                else:
                    logs.append("Toàn bộ party của bạn đã gục!")
                    return TurnResult("\n".join(logs), battle_over=True)

        logs.extend(self._apply_end_of_turn_status())

        if self.wild.current_hp <= 0:
            logs.append(f"{self.wild.name} đã gục!")
            self._grant_victory_rewards(self.player_active, logs)
            return TurnResult("\n".join(logs), battle_over=True)

        if self.player_active.current_hp <= 0:
            switched = self._auto_switch_player()
            if switched:
                logs.append(switched)
            else:
                logs.append("Toàn bộ party của bạn đã gục!")
                return TurnResult("\n".join(logs), battle_over=True)

        return TurnResult("\n".join(logs), battle_over=False)

    def throw_ball(self, ball_name: str) -> TurnResult:
        if not getattr(self, "allow_catch", True):
            return TurnResult("Không thể ném Ball trong trận đấu này.", success=False)
        amount = self.player.inventory.get(ball_name, 0)
        if amount <= 0:
            return TurnResult(f"Bạn không có {ball_name}.")

        self.player.inventory[ball_name] = amount - 1

        catch_rate = self._catch_chance(ball_name)
        if random.random() <= catch_rate:
            caught = self.wild
            caught.current_hp = max(1, caught.current_hp)
            if len(self.player.party) < 6:
                self.player.party.append(caught)
                where = "party"
            else:
                self.player.pc.append(caught)
                where = "PC"
            return TurnResult(
                f"Bạn đã bắt được {caught.name} bằng {ball_name}! Pokémon được gửi vào {where}.",
                battle_over=True,
                caught=True,
            )

        logs = [f"{self.wild.name} thoát khỏi {ball_name}!" ]
        if self.wild.current_hp > 0:
            logs.append(self._perform_wild_move())
            if self.player_active.current_hp <= 0:
                switched = self._auto_switch_player()
                if switched:
                    logs.append(switched)
                else:
                    logs.append("Toàn bộ party của bạn đã gục!")
                    return TurnResult("\n".join(logs), battle_over=True)
        return TurnResult("\n".join(logs), battle_over=False)

    def use_item(
        self,
        item_name: str,
        *,
        target_index: int | None = None,
        target_move_index: int | None = None,
    ) -> TurnResult:
        if self.player_embargo_turns > 0:
            return TurnResult("Bạn đang bị Embargo nên không thể dùng item.", success=False)

        amount = self.player.inventory.get(item_name, 0)
        if amount <= 0:
            return TurnResult(f"Bạn không có {item_name}.", success=False)

        active = self.player_active
        heal_amount = self._healing_item_amount(item_name)
        status_cure = get_status_cure_item(item_name)
        pp_restore = get_pp_restore_item(item_name)
        revive_mode = get_revive_item(item_name)
        boost_stat = self._x_item_stat(item_name)
        pp_item = item_name in {"PP Up", "PP Max"}

        logs: list[str] = []

        if item_name == "Full Restore":
            if active.current_hp <= 0:
                return TurnResult(f"{active.name} đã gục, không thể dùng {item_name}.", success=False)
            can_heal = active.current_hp < active.max_hp
            can_cure = active.status is not None
            if not can_heal and not can_cure:
                return TurnResult(f"{active.name} không cần dùng {item_name}.", success=False)

            before_hp = active.current_hp
            active.current_hp = active.max_hp
            active.status = None
            active.status_counter = 0

            self.player.inventory[item_name] = amount - 1
            healed = active.current_hp - before_hp
            logs.append(
                f"Bạn dùng {item_name}. {active.name} hồi {healed} HP ({active.current_hp}/{active.max_hp}) và chữa mọi trạng thái."
            )

        elif heal_amount is not None:
            if active.current_hp <= 0:
                return TurnResult(f"{active.name} đã gục, không thể dùng {item_name}.", success=False)
            if active.current_hp >= active.max_hp:
                return TurnResult(f"{active.name} đã đầy HP, không cần dùng {item_name}.", success=False)

            before_hp = active.current_hp
            if heal_amount < 0:
                active.current_hp = active.max_hp
            else:
                active.current_hp = min(active.max_hp, active.current_hp + heal_amount)

            self.player.inventory[item_name] = amount - 1
            healed = active.current_hp - before_hp
            logs.append(f"Bạn dùng {item_name}. {active.name} hồi {healed} HP ({active.current_hp}/{active.max_hp}).")

        elif status_cure is not None:
            if active.current_hp <= 0:
                return TurnResult(f"{active.name} đã gục, không thể dùng {item_name}.", success=False)
            if active.status is None:
                return TurnResult(f"{active.name} không có trạng thái cần chữa.", success=False)

            current_status = active.status
            if status_cure != "all" and current_status not in status_cure:
                return TurnResult(f"{item_name} không chữa được trạng thái hiện tại của {active.name}.", success=False)

            active.status = None
            active.status_counter = 0
            self.player.inventory[item_name] = amount - 1
            logs.append(f"Bạn dùng {item_name}. {active.name} đã được chữa trạng thái {current_status}.")

        elif pp_restore is not None:
            if active.current_hp <= 0:
                return TurnResult(f"{active.name} đã gục, không thể dùng {item_name}.", success=False)

            mode, restore_amount = pp_restore
            if mode == "single":
                target_move = None
                if target_move_index is not None and 0 <= target_move_index < len(active.moves):
                    candidate_move = active.moves[target_move_index]
                    if candidate_move.current_pp < candidate_move.max_pp:
                        target_move = candidate_move
                if target_move is None:
                    target_move = next((mv for mv in active.moves if mv.current_pp < mv.max_pp), None)
                if target_move is None:
                    return TurnResult(f"Không có move nào của {active.name} cần hồi PP.", success=False)
                before_pp = target_move.current_pp
                if restore_amount < 0:
                    target_move.current_pp = target_move.max_pp
                else:
                    target_move.current_pp = min(target_move.max_pp, target_move.current_pp + restore_amount)
                recovered = target_move.current_pp - before_pp
                self.player.inventory[item_name] = amount - 1
                logs.append(
                    f"Bạn dùng {item_name}. {target_move.name} hồi {recovered} PP ({target_move.current_pp}/{target_move.max_pp})."
                )
            else:
                changed = False
                restored_total = 0
                for move in active.moves:
                    if move.current_pp < move.max_pp:
                        before_pp = move.current_pp
                        if restore_amount < 0:
                            move.current_pp = move.max_pp
                        else:
                            move.current_pp = min(move.max_pp, move.current_pp + restore_amount)
                        if move.current_pp > before_pp:
                            changed = True
                            restored_total += move.current_pp - before_pp
                if not changed:
                    return TurnResult(f"Không có move nào của {active.name} cần hồi PP.", success=False)
                self.player.inventory[item_name] = amount - 1
                logs.append(f"Bạn dùng {item_name}. Tổng cộng hồi {restored_total} PP cho các chiêu của {active.name}.")

        elif revive_mode is not None:
            if revive_mode == "all_full":
                fainted_party = [p for p in self.player.party if p.current_hp <= 0]
                if not fainted_party:
                    return TurnResult("Không có Pokémon nào đã gục để hồi sinh.", success=False)

                for pkmn in fainted_party:
                    pkmn.current_hp = pkmn.max_hp
                    pkmn.status = None
                    pkmn.status_counter = 0
                    pkmn.confusion_turns = 0

                self.player.inventory[item_name] = amount - 1
                logs.append(f"Bạn dùng {item_name}. Đã hồi sinh {len(fainted_party)} Pokémon trong party về đầy HP.")
            else:
                target = None
                if target_index is not None and 0 <= target_index < len(self.player.party):
                    candidate = self.player.party[target_index]
                    if candidate.current_hp <= 0:
                        target = candidate
                if target is None:
                    target = next((p for p in self.player.party if p.current_hp <= 0), None)
                if target is None:
                    return TurnResult("Không có Pokémon nào đã gục để hồi sinh.", success=False)

                if revive_mode == "half":
                    target.current_hp = max(1, target.max_hp // 2)
                else:
                    target.current_hp = target.max_hp
                target.status = None
                target.status_counter = 0
                target.confusion_turns = 0

                self.player.inventory[item_name] = amount - 1
                logs.append(
                    f"Bạn dùng {item_name}. {target.name} đã hồi sinh ({target.current_hp}/{target.max_hp} HP)."
                )

        elif boost_stat is not None:
            changed, stage_text = self._change_stat_stage(self.player_active, boost_stat, +1)
            if not changed:
                return TurnResult(f"{self.player_active.name} đã đạt giới hạn tăng chỉ số này.", success=False)
            self.player.inventory[item_name] = amount - 1
            stat_label = {
                "attack": "Attack",
                "defense": "Defense",
                "sp_attack": "Sp. Attack",
                "sp_defense": "Sp. Defense",
                "speed": "Speed",
            }.get(boost_stat, boost_stat)
            logs.append(f"Bạn dùng {item_name}. {active.name} tăng {stat_label} {stage_text}.")
        elif pp_item:
            upgraded, pp_text = self._apply_pp_item(active, item_name)
            if not upgraded:
                return TurnResult(pp_text, success=False)
            self.player.inventory[item_name] = amount - 1
            logs.append(pp_text)
        else:
            return TurnResult(f"{item_name} chưa được hỗ trợ dùng trong battle.", success=False)

        return TurnResult("\n".join(logs), battle_over=False, success=True)

    def run_away(self) -> TurnResult:
        if not getattr(self, "allow_run", True):
            return TurnResult("Bạn không thể chạy khỏi trận đấu này.", battle_over=False, success=False)
        if self._held_item_name(self.player_active) == "smoke ball":
            return TurnResult("Smoke Ball giúp bạn chạy trốn chắc chắn.", battle_over=True)
        if self.player_trapped_turns > 0 or self.player_ingrain:
            return TurnResult("Bạn đang bị trói chân nên không thể chạy trốn!", battle_over=False, success=False)
        return TurnResult("Bạn đã chạy trốn thành công.", battle_over=True)

    def _turn_order(self, player_move: MoveSet, wild_move: MoveSet | None) -> tuple[str, str]:
        if self._held_item_name(self.player_active) == "quick claw" and random.random() < 0.2:
            return "player", "wild"
        if self._held_item_name(self.wild) == "quick claw" and random.random() < 0.2:
            return "wild", "player"

        player_priority = self._effective_priority(self.player_active, player_move)
        wild_priority = self._effective_priority(self.wild, wild_move)
        if player_priority > wild_priority:
            return "player", "wild"
        if wild_priority > player_priority:
            return "wild", "player"

        player_custap = self._try_activate_custap(self.player_active, can_move=player_move is not None)
        wild_custap = self._try_activate_custap(self.wild, can_move=wild_move is not None)
        if player_custap and not wild_custap:
            return "player", "wild"
        if wild_custap and not player_custap:
            return "wild", "player"

        player_forced_last = self._held_item_name(self.player_active) in {"full incense", "lagging tail"}
        wild_forced_last = self._held_item_name(self.wild) in {"full incense", "lagging tail"}
        if player_forced_last and not wild_forced_last:
            return "wild", "player"
        if wild_forced_last and not player_forced_last:
            return "player", "wild"

        player_speed = self._effective_stat(self.player_active, "speed")
        wild_speed = self._effective_stat(self.wild, "speed")
        if getattr(self, "trick_room_turns", 0) > 0:
            if player_speed < wild_speed:
                return "player", "wild"
            if wild_speed < player_speed:
                return "wild", "player"
        else:
            if player_speed > wild_speed:
                return "player", "wild"
            if wild_speed > player_speed:
                return "wild", "player"
        return ("player", "wild") if random.random() < 0.5 else ("wild", "player")

    def _effective_priority(self, attacker: PokemonInstance, move: MoveSet | None) -> int:
        if move is None:
            return -7
        priority = move.priority
        if move.name == "Grassy Glide" and self.terrain == "grassy terrain" and self.terrain_turns > 0 and self._is_grounded(attacker):
            priority += 1
        if attacker.ability == "Prankster" and move.category == "Status":
            priority += 1
        if attacker.ability == "Gale Wings" and move.move_type == "Flying" and attacker.current_hp == attacker.max_hp:
            priority += 1
        return priority

    def _held_item_name(self, pokemon: PokemonInstance) -> str:
        side_embargo = self.player_embargo_turns if pokemon is self.player_active else self.wild_embargo_turns
        return resolve_held_item_name(
            pokemon.hold_item,
            magic_room_turns=self.magic_room_turns,
            side_embargo_turns=side_embargo,
        )

    def _highest_non_hp_stat(self, pokemon: PokemonInstance) -> str:
        candidates = [
            ("attack", int(pokemon.attack)),
            ("defense", int(pokemon.defense)),
            ("sp_attack", int(pokemon.sp_attack)),
            ("sp_defense", int(pokemon.sp_defense)),
            ("speed", int(pokemon.speed)),
        ]
        best_stat = "attack"
        best_value = -1
        for stat_key, value in candidates:
            if value > best_value:
                best_value = value
                best_stat = stat_key
        return best_stat

    def _ability_field_boost_stat(self, pokemon: PokemonInstance) -> str | None:
        ability = (pokemon.ability or "").strip()
        if ability == "Protosynthesis" and self.weather == "harsh sunlight" and self.weather_turns > 0:
            return self._highest_non_hp_stat(pokemon)
        if ability == "Quark Drive" and self.terrain == "electric terrain" and self.terrain_turns > 0:
            return self._highest_non_hp_stat(pokemon)
        return None

    def _try_activate_booster_energy(self, pokemon: PokemonInstance) -> str | None:
        return try_activate_booster_energy(self, pokemon)

    def _try_activate_terrain_seed(self, pokemon: PokemonInstance) -> str | None:
        return try_activate_terrain_seed(self, pokemon)

    def _trigger_active_terrain_seeds(self) -> list[str]:
        return trigger_active_terrain_seeds(self)

    def _try_activate_room_service(self, pokemon: PokemonInstance) -> str | None:
        return try_activate_room_service(self, pokemon)

    def _trigger_active_room_service(self) -> list[str]:
        return trigger_active_room_service(self)

    def _screen_duration(self, pokemon: PokemonInstance) -> int:
        return get_screen_duration(self._held_item_name(pokemon))

    def _weather_duration(self, pokemon: PokemonInstance, weather_name: str) -> int:
        return get_weather_duration(self._held_item_name(pokemon), weather_name)

    def _terrain_duration(self, pokemon: PokemonInstance) -> int:
        return get_terrain_duration(self._held_item_name(pokemon))

    def _has_choice_item(self, pokemon: PokemonInstance) -> bool:
        return is_choice_item(self._held_item_name(pokemon))

    def _refresh_choice_lock(self, pokemon: PokemonInstance) -> None:
        if pokemon is self.player_active:
            if not self._has_choice_item(pokemon):
                self.player_choice_lock_move = None
            return
        if not self._has_choice_item(pokemon):
            self.wild_choice_lock_move = None

    def _can_still_evolve(self, pokemon: PokemonInstance) -> bool:
        species = next((s for s in self.game_data.pokedex if int(s.get("id", 0)) == int(pokemon.species_id)), None)
        if not species:
            return False
        evolution = species.get("evolution", {})
        return bool(evolution.get("next"))

    def _try_activate_custap(self, pokemon: PokemonInstance, *, can_move: bool) -> bool:
        if not can_move:
            return False
        if pokemon.current_hp <= 0:
            return False
        if self._held_item_name(pokemon) != "custap berry":
            return False
        ability_name = (pokemon.ability or "").strip()
        threshold = max(1, pokemon.max_hp // 2) if ability_name == "Gluttony" else max(1, pokemon.max_hp // 4)
        if pokemon.current_hp > threshold:
            return False
        pokemon.hold_item = None
        pokemon.berry_consumed = True
        return True

    def _try_trigger_leppa(self, pokemon: PokemonInstance, move: MoveSet) -> str | None:
        if pokemon.current_hp <= 0:
            return None
        if self._held_item_name(pokemon) != "leppa berry":
            return None
        if move.current_pp > 0:
            return None
        if move.max_pp <= 0:
            return None

        restore = min(10, move.max_pp - move.current_pp)
        if restore <= 0:
            return None

        move.current_pp += restore
        pokemon.hold_item = None
        pokemon.berry_consumed = True
        return f"{pokemon.name} ăn Leppa Berry! {move.name} hồi {restore} PP ({move.current_pp}/{move.max_pp})."

    def _multi_hit_roll(self, attacker: PokemonInstance) -> int:
        ability_name = (attacker.ability or "").strip()
        if ability_name == "Skill Link":
            return 5
        if self._held_item_name(attacker) == "loaded dice":
            return random.choice([4, 5])
        return random.choices([2, 3, 4, 5], weights=[35, 35, 15, 15], k=1)[0]

    def _blocks_additional_effects(self, pokemon: PokemonInstance) -> bool:
        if pokemon.current_hp <= 0:
            return False
        if (pokemon.ability or "").strip() == "Shield Dust":
            return True
        return self._held_item_name(pokemon) == "covert cloak"

    def _contact_effects_suppressed(self, attacker: PokemonInstance) -> bool:
        if self._held_item_name(attacker) == "protective pads":
            return True
        return (attacker.ability or "").strip() == "Long Reach"

    def _apply_binding_effect(self, attacker: PokemonInstance, defender: PokemonInstance, turns: int) -> int:
        held_item = self._held_item_name(attacker)
        divisor = 6 if held_item == "binding band" else 8
        applied_turns = max(1, int(turns))
        if held_item == "grip claw":
            applied_turns = 7
        if defender is self.player_active:
            self.player_bound_turns = max(self.player_bound_turns, applied_turns)
            self.player_trapped_turns = max(self.player_trapped_turns, applied_turns)
            self.player_bound_damage_divisor = divisor
            return applied_turns
        self.wild_bound_turns = max(self.wild_bound_turns, applied_turns)
        self.wild_trapped_turns = max(self.wild_trapped_turns, applied_turns)
        self.wild_bound_damage_divisor = divisor
        return applied_turns

    def _drain_heal_amount(self, attacker: PokemonInstance, base_heal: int) -> int:
        if attacker.current_hp <= 0:
            return 0
        heal = max(0, int(base_heal))
        if heal <= 0:
            return 0
        if self._held_item_name(attacker) == "big root":
            heal = max(1, math.floor(heal * 1.3))
        return min(heal, attacker.max_hp - attacker.current_hp)

    def _is_infatuated(self, pokemon: PokemonInstance) -> bool:
        if pokemon is self.player_active:
            return self.player_infatuated
        return self.wild_infatuated

    def _set_infatuated(
        self,
        pokemon: PokemonInstance,
        value: bool,
        *,
        source: PokemonInstance | None = None,
    ) -> str | None:
        if pokemon is self.player_active:
            self.player_infatuated = bool(value)
        else:
            self.wild_infatuated = bool(value)

        if value and pokemon.current_hp > 0 and self._held_item_name(pokemon) == "mental herb":
            if pokemon is self.player_active:
                self.player_infatuated = False
            else:
                self.wild_infatuated = False
            pokemon.hold_item = None
            return f"{pokemon.name} kích hoạt Mental Herb và thoát khỏi mê mẩn!"

        if not value or source is None or pokemon.current_hp <= 0 or source.current_hp <= 0:
            return None
        if self._held_item_name(pokemon) != "destiny knot":
            return None
        if self._is_infatuated(source):
            return None

        if source is self.player_active:
            self.player_infatuated = True
        else:
            self.wild_infatuated = True
        return f"{pokemon.name} kích hoạt Destiny Knot! {source.name} cũng bị mê mẩn!"

    def _try_consume_mental_herb(self, pokemon: PokemonInstance) -> str | None:
        return try_consume_mental_herb(self, pokemon)

    def _consume_eject_pack_for(self, pokemon: PokemonInstance) -> str | None:
        return consume_eject_pack_for(self, pokemon)

    def _consume_pending_eject_pack(self) -> list[str]:
        return consume_pending_eject_pack(self)

    def _is_disliked_pinch_flavor(self, pokemon: PokemonInstance, berry_name: str) -> bool:
        _, down = NATURE_EFFECTS.get((pokemon.nature or "").strip(), (None, None))
        return is_disliked_pinch_flavor(berry_name, down)

    def _try_trigger_berry(self, pokemon: PokemonInstance) -> list[str]:
        return trigger_berry_effects(self, pokemon)

    def _perform_player_move(self, move_index: int) -> str:
        if self.player_active.current_hp <= 0:
            return f"{self.player_active.name} không thể tấn công vì đã gục."

        self._refresh_choice_lock(self.player_active)
        mental_herb_text = self._try_consume_mental_herb(self.player_active)

        forced_two_turn = None
        if self.player_bounce_charging:
            forced_two_turn = "Bounce"
        elif self.player_dig_charging:
            forced_two_turn = "Dig"
        elif self.player_dive_charging:
            forced_two_turn = "Dive"
        elif self.player_fly_charging:
            forced_two_turn = "Fly"
        elif self.player_freeze_shock_charging:
            forced_two_turn = "Freeze Shock"
        elif self.player_ice_burn_charging:
            forced_two_turn = "Ice Burn"
        elif self.player_geomancy_charging:
            forced_two_turn = "Geomancy"
        elif self.player_electro_shot_charging:
            forced_two_turn = "Electro Shot"
        elif self.player_razor_wind_charging:
            forced_two_turn = "Razor Wind"
        elif self.player_sky_attack_charging:
            forced_two_turn = "Sky Attack"
        elif self.player_skull_bash_charging:
            forced_two_turn = "Skull Bash"
        elif self.player_sky_drop_charging:
            forced_two_turn = "Sky Drop"
        elif self.player_solar_beam_charging:
            forced_two_turn = "Solar Beam"
        elif self.player_solar_blade_charging:
            forced_two_turn = "Solar Blade"
        elif getattr(self, "player_phantom_force_charging", False):
            forced_two_turn = self.player_last_move_name if self.player_last_move_name in {"Phantom Force", "Shadow Force"} else "Phantom Force"
        if forced_two_turn:
            forced_move = next((mv for mv in self.player_active.moves if mv.name == forced_two_turn), None)
            if forced_move is not None:
                result_text = self._execute_move(self.player_active, self.wild, forced_move)
                if mental_herb_text:
                    return f"{mental_herb_text}\n{result_text}"
                return result_text

        if move_index == -1:
            result_text = self._use_struggle(self.player_active, self.wild)
            if mental_herb_text:
                return f"{mental_herb_text}\n{result_text}"
            return result_text

        usable = [mv for mv in self.player_active.moves if mv.current_pp > 0]
        if not usable:
            result_text = self._use_struggle(self.player_active, self.wild)
            if mental_herb_text:
                return f"{mental_herb_text}\n{result_text}"
            return result_text

        move_index = max(0, min(move_index, len(self.player_active.moves) - 1))
        move = self.player_active.moves[move_index]
        if self.player_encore_turns > 0 and self.player_encore_move:
            forced_encore = next((mv for mv in self.player_active.moves if mv.name == self.player_encore_move and mv.current_pp > 0), None)
            if forced_encore is not None:
                move = forced_encore
            else:
                return self._use_struggle(self.player_active, self.wild)
        if move.name in self.player_imprisoned_moves:
            return f"{self.player_active.name} không thể dùng {move.name} vì bị Imprison khóa!"
        if self.player_disable_turns > 0 and self.player_disabled_move and move.name == self.player_disabled_move:
            return f"{self.player_active.name} không thể dùng {move.name} vì đã bị Disable!"
        if self.player_torment_turns > 0 and self.player_last_move_name and move.name == self.player_last_move_name:
            return f"{self.player_active.name} không thể dùng liên tiếp {move.name} vì đang bị Torment!"
        if self.player_choice_lock_move and move.name != self.player_choice_lock_move:
            forced = next((mv for mv in self.player_active.moves if mv.name == self.player_choice_lock_move and mv.current_pp > 0), None)
            if forced is not None:
                return f"{self.player_active.name} bị khóa bởi Choice item và chỉ có thể dùng {self.player_choice_lock_move}!"
            self.player_choice_lock_move = None
        if move.current_pp <= 0:
            return f"{self.player_active.name} muốn dùng {move.name} nhưng đã hết PP!"
        result_text = self._execute_move(self.player_active, self.wild, move)
        if mental_herb_text:
            return f"{mental_herb_text}\n{result_text}"
        return result_text

    def _select_wild_move(self) -> MoveSet | None:
        if self.wild.current_hp <= 0:
            return None
        usable = [mv for mv in self.wild.moves if mv.current_pp > 0]
        if not usable:
            return None
        return random.choice(usable)

    def _perform_wild_move(self, selected_move: MoveSet | None = None) -> str:
        if self.wild.current_hp <= 0:
            return f"{self.wild.name} không thể tấn công vì đã gục."

        self._refresh_choice_lock(self.wild)
        mental_herb_text = self._try_consume_mental_herb(self.wild)

        forced_two_turn = None
        if self.wild_bounce_charging:
            forced_two_turn = "Bounce"
        elif self.wild_dig_charging:
            forced_two_turn = "Dig"
        elif self.wild_dive_charging:
            forced_two_turn = "Dive"
        elif self.wild_fly_charging:
            forced_two_turn = "Fly"
        elif self.wild_freeze_shock_charging:
            forced_two_turn = "Freeze Shock"
        elif self.wild_ice_burn_charging:
            forced_two_turn = "Ice Burn"
        elif self.wild_geomancy_charging:
            forced_two_turn = "Geomancy"
        elif self.wild_electro_shot_charging:
            forced_two_turn = "Electro Shot"
        elif self.wild_razor_wind_charging:
            forced_two_turn = "Razor Wind"
        elif self.wild_sky_attack_charging:
            forced_two_turn = "Sky Attack"
        elif self.wild_skull_bash_charging:
            forced_two_turn = "Skull Bash"
        elif self.wild_sky_drop_charging:
            forced_two_turn = "Sky Drop"
        elif self.wild_solar_beam_charging:
            forced_two_turn = "Solar Beam"
        elif self.wild_solar_blade_charging:
            forced_two_turn = "Solar Blade"
        elif getattr(self, "wild_phantom_force_charging", False):
            forced_two_turn = self.wild_last_move_name if self.wild_last_move_name in {"Phantom Force", "Shadow Force"} else "Phantom Force"
        if forced_two_turn:
            forced_move = next((mv for mv in self.wild.moves if mv.name == forced_two_turn), None)
            if forced_move is not None:
                result_text = self._execute_move(self.wild, self.player_active, forced_move)
                if mental_herb_text:
                    return f"{mental_herb_text}\n{result_text}"
                return result_text

        move = selected_move or self._select_wild_move()
        if move is None:
            result_text = self._use_struggle(self.wild, self.player_active)
            if mental_herb_text:
                return f"{mental_herb_text}\n{result_text}"
            return result_text
        if self.wild_encore_turns > 0 and self.wild_encore_move:
            forced_encore = next((mv for mv in self.wild.moves if mv.name == self.wild_encore_move and mv.current_pp > 0), None)
            if forced_encore is not None:
                move = forced_encore
            else:
                result_text = self._use_struggle(self.wild, self.player_active)
                if mental_herb_text:
                    return f"{mental_herb_text}\n{result_text}"
                return result_text
        if move.name in self.wild_imprisoned_moves:
            return f"{self.wild.name} không thể dùng {move.name} vì bị Imprison khóa!"
        if self.wild_disable_turns > 0 and self.wild_disabled_move and move.name == self.wild_disabled_move:
            return f"{self.wild.name} không thể dùng {move.name} vì đã bị Disable!"
        if self.wild_torment_turns > 0 and self.wild_last_move_name and move.name == self.wild_last_move_name:
            alternatives = [mv for mv in self.wild.moves if mv.current_pp > 0 and mv.name != self.wild_last_move_name]
            if alternatives:
                move = random.choice(alternatives)
            else:
                return self._use_struggle(self.wild, self.player_active)
        if self.wild_choice_lock_move and move.name != self.wild_choice_lock_move:
            forced = next((mv for mv in self.wild.moves if mv.name == self.wild_choice_lock_move and mv.current_pp > 0), None)
            if forced is not None:
                move = forced
            else:
                self.wild_choice_lock_move = None
        result_text = self._execute_move(self.wild, self.player_active, move)
        if mental_herb_text:
            return f"{mental_herb_text}\n{result_text}"
        return result_text

    def _use_struggle(self, attacker: PokemonInstance, defender: PokemonInstance) -> str:
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể dùng Struggle vì đã gục."

        move = MoveSet(
            name="Struggle",
            move_type="Normal",
            category="Physical",
            power=50,
            accuracy=100,
            base_pp=1,
            max_pp=1,
            current_pp=1,
            pp_up_level=0,
            makes_contact=True,
            target="any",
            priority=0,
        )

        damage_text = self._resolve_damage(attacker, defender, move)
        recoil = max(1, attacker.max_hp // 4)
        attacker.current_hp = max(0, attacker.current_hp - recoil)
        return (
            f"{attacker.name} không còn PP nên dùng Struggle!\n"
            f"{damage_text}\n"
            f"{attacker.name} chịu phản lực {recoil} HP ({attacker.current_hp}/{attacker.max_hp})."
        )

    def _execute_move(self, attacker: PokemonInstance, defender: PokemonInstance, move: MoveSet) -> str:
        two_turn_release = False
        power_herb_text = ""

        held = self._held_item_name(attacker)

        def _activate_power_herb() -> bool:
            nonlocal held, power_herb_text
            if held != "power herb":
                return False
            attacker.hold_item = None
            held = ""
            power_herb_text = f"{attacker.name} kích hoạt Power Herb để bỏ qua lượt tích lực!"
            return True

        if held in {"choice band", "choice specs", "choice scarf"}:
            if attacker is self.player_active:
                if self.player_choice_lock_move is None:
                    self.player_choice_lock_move = move.name
            else:
                if self.wild_choice_lock_move is None:
                    self.wild_choice_lock_move = move.name

        if move.name in {"Fly", "Bounce"} and getattr(self, "gravity_turns", 0) > 0:
            return f"{attacker.name} dùng {move.name} nhưng Gravity đang hiệu lực nên thất bại!"

        if move.name == "Bounce":
            if attacker is self.player_active:
                if not self.player_bounce_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.player_bounce_charging = True
                        self.player_last_move_name = move.name
                        return f"{attacker.name} nhảy vọt lên không trung và chuẩn bị Bounce!"
                else:
                    self.player_bounce_charging = False
                    two_turn_release = True
            else:
                if not self.wild_bounce_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.wild_bounce_charging = True
                        self.wild_last_move_name = move.name
                        return f"{attacker.name} nhảy vọt lên không trung và chuẩn bị Bounce!"
                else:
                    self.wild_bounce_charging = False
                    two_turn_release = True

        if move.name == "Dig":
            if attacker is self.player_active:
                if not self.player_dig_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.player_dig_charging = True
                        self.player_last_move_name = move.name
                        return f"{attacker.name} đào xuống đất và chuẩn bị Dig!"
                else:
                    self.player_dig_charging = False
                    two_turn_release = True
            else:
                if not self.wild_dig_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.wild_dig_charging = True
                        self.wild_last_move_name = move.name
                        return f"{attacker.name} đào xuống đất và chuẩn bị Dig!"
                else:
                    self.wild_dig_charging = False
                    two_turn_release = True

        if move.name == "Dive":
            if attacker is self.player_active:
                if not self.player_dive_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.player_dive_charging = True
                        self.player_last_move_name = move.name
                        return f"{attacker.name} lặn xuống nước và chuẩn bị Dive!"
                else:
                    self.player_dive_charging = False
                    two_turn_release = True
            else:
                if not self.wild_dive_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.wild_dive_charging = True
                        self.wild_last_move_name = move.name
                        return f"{attacker.name} lặn xuống nước và chuẩn bị Dive!"
                else:
                    self.wild_dive_charging = False
                    two_turn_release = True

        if move.name == "Fly":
            if attacker is self.player_active:
                if not self.player_fly_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.player_fly_charging = True
                        self.player_last_move_name = move.name
                        return f"{attacker.name} bay vút lên trời và chuẩn bị Fly!"
                else:
                    self.player_fly_charging = False
                    two_turn_release = True
            else:
                if not self.wild_fly_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.wild_fly_charging = True
                        self.wild_last_move_name = move.name
                        return f"{attacker.name} bay vút lên trời và chuẩn bị Fly!"
                else:
                    self.wild_fly_charging = False
                    two_turn_release = True

        if move.name == "Razor Wind":
            if attacker is self.player_active:
                if not self.player_razor_wind_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.player_razor_wind_charging = True
                        self.player_last_move_name = move.name
                        return f"{attacker.name} tạo lốc gió và chuẩn bị Razor Wind!"
                else:
                    self.player_razor_wind_charging = False
                    two_turn_release = True
            else:
                if not self.wild_razor_wind_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.wild_razor_wind_charging = True
                        self.wild_last_move_name = move.name
                        return f"{attacker.name} tạo lốc gió và chuẩn bị Razor Wind!"
                else:
                    self.wild_razor_wind_charging = False
                    two_turn_release = True

        if move.name == "Sky Attack":
            if attacker is self.player_active:
                if not self.player_sky_attack_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.player_sky_attack_charging = True
                        self.player_last_move_name = move.name
                        return f"{attacker.name} tập trung năng lượng và chuẩn bị Sky Attack!"
                else:
                    self.player_sky_attack_charging = False
                    two_turn_release = True
            else:
                if not self.wild_sky_attack_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.wild_sky_attack_charging = True
                        self.wild_last_move_name = move.name
                        return f"{attacker.name} tập trung năng lượng và chuẩn bị Sky Attack!"
                else:
                    self.wild_sky_attack_charging = False
                    two_turn_release = True

        if move.name == "Skull Bash":
            if attacker is self.player_active:
                if not self.player_skull_bash_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        changed, _ = self._change_stat_stage(attacker, "defense", +1)
                        if changed:
                            two_turn_release = True
                        else:
                            two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.player_skull_bash_charging = True
                        self.player_last_move_name = move.name
                        changed, stage_text = self._change_stat_stage(attacker, "defense", +1)
                        if changed:
                            return f"{attacker.name} co đầu phòng thủ và chuẩn bị Skull Bash! Defense tăng {stage_text}."
                        return f"{attacker.name} co đầu phòng thủ và chuẩn bị Skull Bash!"
                else:
                    self.player_skull_bash_charging = False
                    two_turn_release = True
            else:
                if not self.wild_skull_bash_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        changed, _ = self._change_stat_stage(attacker, "defense", +1)
                        if changed:
                            two_turn_release = True
                        else:
                            two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.wild_skull_bash_charging = True
                        self.wild_last_move_name = move.name
                        changed, stage_text = self._change_stat_stage(attacker, "defense", +1)
                        if changed:
                            return f"{attacker.name} co đầu phòng thủ và chuẩn bị Skull Bash! Defense tăng {stage_text}."
                        return f"{attacker.name} co đầu phòng thủ và chuẩn bị Skull Bash!"
                else:
                    self.wild_skull_bash_charging = False
                    two_turn_release = True

        if move.name == "Sky Drop":
            if attacker is self.player_active:
                if not self.player_sky_drop_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.player_sky_drop_charging = True
                        self.player_last_move_name = move.name
                        return f"{attacker.name} nâng mục tiêu lên không trung và chuẩn bị Sky Drop!"
                else:
                    self.player_sky_drop_charging = False
                    two_turn_release = True
            else:
                if not self.wild_sky_drop_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.wild_sky_drop_charging = True
                        self.wild_last_move_name = move.name
                        return f"{attacker.name} nâng mục tiêu lên không trung và chuẩn bị Sky Drop!"
                else:
                    self.wild_sky_drop_charging = False
                    two_turn_release = True

        if move.name == "Solar Beam":
            if self.weather == "harsh sunlight" and self.weather_turns > 0:
                two_turn_release = True
            elif attacker is self.player_active:
                if not self.player_solar_beam_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.player_solar_beam_charging = True
                        self.player_last_move_name = move.name
                        return f"{attacker.name} hấp thụ ánh nắng và chuẩn bị Solar Beam!"
                else:
                    self.player_solar_beam_charging = False
                    two_turn_release = True
            else:
                if not self.wild_solar_beam_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.wild_solar_beam_charging = True
                        self.wild_last_move_name = move.name
                        return f"{attacker.name} hấp thụ ánh nắng và chuẩn bị Solar Beam!"
                else:
                    self.wild_solar_beam_charging = False
                    two_turn_release = True

        if move.name == "Solar Blade":
            if self.weather == "harsh sunlight" and self.weather_turns > 0:
                two_turn_release = True
            elif attacker is self.player_active:
                if not self.player_solar_blade_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.player_solar_blade_charging = True
                        self.player_last_move_name = move.name
                        return f"{attacker.name} hấp thụ ánh nắng và chuẩn bị Solar Blade!"
                else:
                    self.player_solar_blade_charging = False
                    two_turn_release = True
            else:
                if not self.wild_solar_blade_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.wild_solar_blade_charging = True
                        self.wild_last_move_name = move.name
                        return f"{attacker.name} hấp thụ ánh nắng và chuẩn bị Solar Blade!"
                else:
                    self.wild_solar_blade_charging = False
                    two_turn_release = True

        if move.name in {"Phantom Force", "Shadow Force"}:
            if attacker is self.player_active:
                if not getattr(self, "player_phantom_force_charging", False):
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.player_phantom_force_charging = True
                        self.player_last_move_name = move.name
                        return f"{attacker.name} biến mất trong bóng tối và chuẩn bị {move.name}!"
                else:
                    self.player_phantom_force_charging = False
                    two_turn_release = True
            else:
                if not getattr(self, "wild_phantom_force_charging", False):
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.wild_phantom_force_charging = True
                        self.wild_last_move_name = move.name
                        return f"{attacker.name} biến mất trong bóng tối và chuẩn bị {move.name}!"
                else:
                    self.wild_phantom_force_charging = False
                    two_turn_release = True

        if move.name == "Freeze Shock":
            if attacker is self.player_active:
                if not self.player_freeze_shock_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.player_freeze_shock_charging = True
                        self.player_last_move_name = move.name
                        return f"{attacker.name} bắt đầu tích điện băng cho Freeze Shock!"
                else:
                    self.player_freeze_shock_charging = False
                    two_turn_release = True
            else:
                if not self.wild_freeze_shock_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.wild_freeze_shock_charging = True
                        self.wild_last_move_name = move.name
                        return f"{attacker.name} bắt đầu tích điện băng cho Freeze Shock!"
                else:
                    self.wild_freeze_shock_charging = False
                    two_turn_release = True

        if move.name == "Ice Burn":
            if attacker is self.player_active:
                if not self.player_ice_burn_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.player_ice_burn_charging = True
                        self.player_last_move_name = move.name
                        return f"{attacker.name} bắt đầu tích tụ hỏa-băng cho Ice Burn!"
                else:
                    self.player_ice_burn_charging = False
                    two_turn_release = True
            else:
                if not self.wild_ice_burn_charging:
                    if _activate_power_herb():
                        move.current_pp -= 1
                        two_turn_release = True
                    else:
                        move.current_pp -= 1
                        self.wild_ice_burn_charging = True
                        self.wild_last_move_name = move.name
                        return f"{attacker.name} bắt đầu tích tụ hỏa-băng cho Ice Burn!"
                else:
                    self.wild_ice_burn_charging = False
                    two_turn_release = True

        if move.name == "Geomancy":
            if attacker is self.player_active and not self.player_geomancy_charging and _activate_power_herb():
                move.current_pp -= 1
                self.player_geomancy_charging = True
            if attacker is self.wild and not self.wild_geomancy_charging and _activate_power_herb():
                move.current_pp -= 1
                self.wild_geomancy_charging = True

        if move.name == "Geomancy":
            if attacker is self.player_active and self.player_geomancy_charging:
                two_turn_release = True
            if attacker is self.wild and self.wild_geomancy_charging:
                two_turn_release = True

        if move.name == "Electro Shot":
            if attacker is self.player_active:
                if not self.player_electro_shot_charging:
                    move.current_pp -= 1
                    self.player_electro_shot_charging = True
                    self.player_last_move_name = move.name
                    self.player_last_move_type = move.move_type
                    return f"{attacker.name} bắt đầu tích điện cho Electro Shot!"
                self.player_electro_shot_charging = False
                two_turn_release = True
            else:
                if not self.wild_electro_shot_charging:
                    move.current_pp -= 1
                    self.wild_electro_shot_charging = True
                    self.wild_last_move_name = move.name
                    self.wild_last_move_type = move.move_type
                    return f"{attacker.name} bắt đầu tích điện cho Electro Shot!"
                self.wild_electro_shot_charging = False
                two_turn_release = True

        if move.name == "Electro Shot":
            if attacker is self.player_active:
                if not self.player_electro_shot_charging and not (self.weather == "rain" and self.weather_turns > 0):
                    move.current_pp -= 1
                    self.player_electro_shot_charging = True
                    self.player_last_move_name = move.name
                    return f"{attacker.name} bắt đầu tích điện cho Electro Shot!"
                self.player_electro_shot_charging = False
                two_turn_release = True
            else:
                if not self.wild_electro_shot_charging and not (self.weather == "rain" and self.weather_turns > 0):
                    move.current_pp -= 1
                    self.wild_electro_shot_charging = True
                    self.wild_last_move_name = move.name
                    return f"{attacker.name} bắt đầu tích điện cho Electro Shot!"
                self.wild_electro_shot_charging = False
                two_turn_release = True

        if move.name == "Counter":
            if attacker is self.player_active:
                dmg = self.player_last_physical_damage_taken
                if dmg <= 0:
                    return f"{attacker.name} dùng Counter nhưng thất bại vì chưa nhận Physical damage trong lượt này."
                reflected = max(1, dmg * 2)
                self.wild.current_hp = max(0, self.wild.current_hp - reflected)
                self.wild_took_damage_this_turn = True
                self.player_last_move_name = move.name
                self.player_last_move_type = move.move_type
                move.current_pp = max(0, move.current_pp - 1)
                return f"{attacker.name} phản đòn bằng Counter gây {reflected} sát thương lên {self.wild.name}!"
            dmg = self.wild_last_physical_damage_taken
            if dmg <= 0:
                return f"{attacker.name} dùng Counter nhưng thất bại vì chưa nhận Physical damage trong lượt này."
            reflected = max(1, dmg * 2)
            self.player_active.current_hp = max(0, self.player_active.current_hp - reflected)
            self.player_took_damage_this_turn = True
            self.wild_last_move_name = move.name
            self.wild_last_move_type = move.move_type
            move.current_pp = max(0, move.current_pp - 1)
            return f"{attacker.name} phản đòn bằng Counter gây {reflected} sát thương lên {self.player_active.name}!"

        if move.name == "Mirror Coat":
            if attacker is self.player_active:
                dmg = self.player_last_damage_taken
                if dmg <= 0:
                    return f"{attacker.name} dùng Mirror Coat nhưng thất bại vì chưa nhận Special damage trong lượt này."
                reflected = max(1, dmg * 2)
                self.wild.current_hp = max(0, self.wild.current_hp - reflected)
                self.wild_took_damage_this_turn = True
                self.player_last_move_name = move.name
                self.player_last_move_type = move.move_type
                move.current_pp = max(0, move.current_pp - 1)
                return f"{attacker.name} phản đòn bằng Mirror Coat gây {reflected} sát thương lên {self.wild.name}!"
            dmg = self.wild_last_damage_taken
            if dmg <= 0:
                return f"{attacker.name} dùng Mirror Coat nhưng thất bại vì chưa nhận Special damage trong lượt này."
            reflected = max(1, dmg * 2)
            self.player_active.current_hp = max(0, self.player_active.current_hp - reflected)
            self.player_took_damage_this_turn = True
            self.wild_last_move_name = move.name
            self.wild_last_move_type = move.move_type
            move.current_pp = max(0, move.current_pp - 1)
            return f"{attacker.name} phản đòn bằng Mirror Coat gây {reflected} sát thương lên {self.player_active.name}!"

        if move.name == "Comeuppance":
            if attacker is self.player_active:
                dmg = self.player_last_damage_taken
                if dmg <= 0:
                    return f"{attacker.name} dùng Comeuppance nhưng thất bại vì chưa nhận sát thương trong lượt này."
                reflected = max(1, int(dmg * 1.5))
                self.wild.current_hp = max(0, self.wild.current_hp - reflected)
                self.wild_took_damage_this_turn = True
                self.player_last_move_name = move.name
                self.player_last_move_type = move.move_type
                move.current_pp = max(0, move.current_pp - 1)
                return f"{attacker.name} trừng phạt bằng Comeuppance gây {reflected} sát thương lên {self.wild.name}!"
            dmg = self.wild_last_damage_taken
            if dmg <= 0:
                return f"{attacker.name} dùng Comeuppance nhưng thất bại vì chưa nhận sát thương trong lượt này."
            reflected = max(1, int(dmg * 1.5))
            self.player_active.current_hp = max(0, self.player_active.current_hp - reflected)
            self.player_took_damage_this_turn = True
            self.wild_last_move_name = move.name
            self.wild_last_move_type = move.move_type
            move.current_pp = max(0, move.current_pp - 1)
            return f"{attacker.name} trừng phạt bằng Comeuppance gây {reflected} sát thương lên {self.player_active.name}!"

        self._normalize_move_pp(move)
        if move.current_pp <= 0:
            return f"{attacker.name} muốn dùng {move.name} nhưng đã hết PP!"

        if move.name == "Poltergeist" and not defender.hold_item:
            return f"{attacker.name} dùng Poltergeist nhưng thất bại vì {defender.name} không cầm item."

        last_move = self.player_last_move_name if attacker is self.player_active else self.wild_last_move_name
        if move.name == "Blood Moon" and last_move == "Blood Moon":
            return f"{attacker.name} không thể dùng Blood Moon liên tiếp 2 lượt!"

        if move.name == "Fake Out" and last_move is not None:
            return f"{attacker.name} chỉ có thể dùng Fake Out ở lượt đầu tiên khi vừa vào sân!"

        if move.name == "First Impression" and last_move is not None:
            return f"{attacker.name} chỉ có thể dùng First Impression ở lượt đầu tiên khi vừa vào sân!"

        if move.name == "Gigaton Hammer" and last_move == "Gigaton Hammer":
            return f"{attacker.name} không thể dùng Gigaton Hammer liên tiếp 2 lượt!"

        if move.name == "Last Resort":
            used_moves = self._move_usage_for(attacker)
            required = {mv.name for mv in attacker.moves if mv.name != "Last Resort"}
            if required and not required.issubset(used_moves):
                return f"{attacker.name} chưa thể dùng Last Resort vì chưa dùng hết các chiêu khác."

        if move.name == "Belch" and not attacker.berry_consumed:
            held_item = (attacker.hold_item or "").strip().lower()
            if "berry" in held_item:
                attacker.hold_item = None
                attacker.berry_consumed = True
            else:
                return f"{attacker.name} không thể dùng Belch vì chưa ăn Berry."

        if move.name == "Doom Desire":
            move.current_pp = max(0, move.current_pp - 1)
            if attacker is self.player_active:
                if self.wild_doom_desire_turns > 0:
                    return f"{attacker.name} đã gọi Doom Desire, không thể chồng thêm."
                atk = self._effective_stat(attacker, "sp_attack")
                dfn = self._effective_stat(defender, "sp_defense")
                base_damage = (((2 * attacker.level / 5 + 2) * 140 * (atk / max(1, dfn))) / 50) + 2
                stab = 1.5 if "Steel" in attacker.types else 1.0
                type_mul = self.game_data.type_multiplier("Steel", defender.types)
                dmg = math.floor(max(1.0, base_damage * stab * type_mul * 0.925))
                self.wild_doom_desire_turns = 2
                self.wild_doom_desire_damage = dmg
                return f"{attacker.name} dùng Doom Desire! Đòn sẽ giáng xuống sau 2 lượt."
            if self.player_doom_desire_turns > 0:
                return f"{attacker.name} đã gọi Doom Desire, không thể chồng thêm."
            atk = self._effective_stat(attacker, "sp_attack")
            dfn = self._effective_stat(defender, "sp_defense")
            base_damage = (((2 * attacker.level / 5 + 2) * 140 * (atk / max(1, dfn))) / 50) + 2
            stab = 1.5 if "Steel" in attacker.types else 1.0
            type_mul = self.game_data.type_multiplier("Steel", defender.types)
            dmg = math.floor(max(1.0, base_damage * stab * type_mul * 0.925))
            self.player_doom_desire_turns = 2
            self.player_doom_desire_damage = dmg
            return f"{attacker.name} dùng Doom Desire! Đòn sẽ giáng xuống sau 2 lượt."

        if move.name == "Future Sight":
            move.current_pp = max(0, move.current_pp - 1)
            if attacker is self.player_active:
                if self.wild_future_sight_turns > 0:
                    return f"{attacker.name} đã gọi Future Sight, không thể chồng thêm."
                atk = self._effective_stat(attacker, "sp_attack")
                dfn = self._effective_stat(defender, "sp_defense")
                base_damage = (((2 * attacker.level / 5 + 2) * 120 * (atk / max(1, dfn))) / 50) + 2
                stab = 1.5 if "Psychic" in attacker.types else 1.0
                type_mul = self.game_data.type_multiplier("Psychic", defender.types)
                dmg = math.floor(max(1.0, base_damage * stab * type_mul * 0.925))
                self.wild_future_sight_turns = 2
                self.wild_future_sight_damage = dmg
                return f"{attacker.name} dùng Future Sight! Đòn tâm linh sẽ đánh trúng sau 2 lượt."
            if self.player_future_sight_turns > 0:
                return f"{attacker.name} đã gọi Future Sight, không thể chồng thêm."
            atk = self._effective_stat(attacker, "sp_attack")
            dfn = self._effective_stat(defender, "sp_defense")
            base_damage = (((2 * attacker.level / 5 + 2) * 120 * (atk / max(1, dfn))) / 50) + 2
            stab = 1.5 if "Psychic" in attacker.types else 1.0
            type_mul = self.game_data.type_multiplier("Psychic", defender.types)
            dmg = math.floor(max(1.0, base_damage * stab * type_mul * 0.925))
            self.player_future_sight_turns = 2
            self.player_future_sight_damage = dmg
            return f"{attacker.name} dùng Future Sight! Đòn tâm linh sẽ đánh trúng sau 2 lượt."

        if move.name == "Sleep Talk":
            if attacker.status != "slp":
                return f"{attacker.name} dùng Sleep Talk nhưng đang không ngủ nên thất bại!"
            if attacker.status_counter <= 0:
                attacker.status_counter = random.randint(1, 3)
            attacker.status_counter -= 1
            if attacker.status_counter <= 0:
                attacker.status = None
                attacker.status_counter = 0
                return f"{attacker.name} tỉnh giấc nên Sleep Talk thất bại."
        else:
            can_act, status_text = self._pre_action_status_check(attacker)
            if not can_act:
                return status_text

        if attacker.status == "par" and random.random() < 0.25:
            return f"{attacker.name} bị tê liệt và không thể hành động!"

        if move.name == "Focus Punch":
            took_damage = self.player_took_damage_this_turn if attacker is self.player_active else self.wild_took_damage_this_turn
            if took_damage:
                return f"{attacker.name} bị phân tâm nên Focus Punch thất bại!"

        if move.name not in {"Protect", "Baneful Bunker", "Detect", "Endure", "King's Shield", "Mat Block", "Max Guard", "Obstruct", "Silk Trap", "Spiky Shield"}:
            self._reset_protect_chain(attacker)

        if move.name == "Snore" and attacker.status != "slp":
            return f"{attacker.name} dùng Snore nhưng đang không ngủ nên thất bại!"

        attacker_throat_chop_turns = self.player_throat_chop_turns if attacker is self.player_active else self.wild_throat_chop_turns
        if attacker_throat_chop_turns > 0 and self._is_sound_move(move.name):
            return f"{attacker.name} không thể dùng {move.name} vì đang bị Throat Chop khóa chiêu âm thanh!"

        if self._held_item_name(attacker) == "assault vest" and move.category == "Status":
            return f"{attacker.name} không thể dùng chiêu Status khi đang cầm Assault Vest!"

        if not two_turn_release:
            move.current_pp -= 1

        leppa_text = self._try_trigger_leppa(attacker, move)

        powdered_attr = "player_powdered" if attacker is self.player_active else "wild_powdered"
        if getattr(self, powdered_attr, False):
            setattr(self, powdered_attr, False)
            if move.move_type == "Fire" and attacker.current_hp > 0:
                burst = max(1, attacker.max_hp // 4)
                attacker.current_hp = max(0, attacker.current_hp - burst)
                return (
                    f"{attacker.name} bị phủ Powder! Khi cố dùng chiêu Fire, nó phát nổ và mất {burst} HP "
                    f"({attacker.current_hp}/{attacker.max_hp})."
                )

        if attacker is self.player_active and move.name != "Rage":
            self.player_rage_active = False
        if attacker is self.wild and move.name != "Rage":
            self.wild_rage_active = False
        if attacker is self.player_active and move.name != "Retaliate":
            self.player_retaliate_ready = False
        if attacker is self.wild and move.name != "Retaliate":
            self.wild_retaliate_ready = False

        if attacker is self.player_active:
            if move.name == "Echoed Voice":
                self.player_echoed_voice_chain = min(5, self.player_echoed_voice_chain + 1)
            else:
                self.player_echoed_voice_chain = 0
            if move.name == "Fury Cutter":
                self.player_fury_cutter_chain = min(4, max(1, self.player_fury_cutter_chain + 1))
            else:
                self.player_fury_cutter_chain = 0
            if move.name == "Ice Ball":
                self.player_ice_ball_chain = min(4, self.player_ice_ball_chain + 1)
            else:
                self.player_ice_ball_chain = 0
            if move.name == "Rollout":
                self.player_rollout_chain = min(4, self.player_rollout_chain + 1)
            else:
                self.player_rollout_chain = 0
        else:
            if move.name == "Echoed Voice":
                self.wild_echoed_voice_chain = min(5, self.wild_echoed_voice_chain + 1)
            else:
                self.wild_echoed_voice_chain = 0
            if move.name == "Fury Cutter":
                self.wild_fury_cutter_chain = min(4, max(1, self.wild_fury_cutter_chain + 1))
            else:
                self.wild_fury_cutter_chain = 0
            if move.name == "Ice Ball":
                self.wild_ice_ball_chain = min(4, self.wild_ice_ball_chain + 1)
            else:
                self.wild_ice_ball_chain = 0
            if move.name == "Rollout":
                self.wild_rollout_chain = min(4, self.wild_rollout_chain + 1)
            else:
                self.wild_rollout_chain = 0

        effective_move = move
        z_power_text = ""
        if move.name == "Judgment":
            plate_map = {
                "flame plate": "Fire",
                "splash plate": "Water",
                "zap plate": "Electric",
                "meadow plate": "Grass",
                "icicle plate": "Ice",
                "fist plate": "Fighting",
                "toxic plate": "Poison",
                "earth plate": "Ground",
                "sky plate": "Flying",
                "mind plate": "Psychic",
                "insect plate": "Bug",
                "stone plate": "Rock",
                "spooky plate": "Ghost",
                "draco plate": "Dragon",
                "dread plate": "Dark",
                "iron plate": "Steel",
                "pixie plate": "Fairy",
            }
            held = "" if self.magic_room_turns > 0 else (attacker.hold_item or "").strip().lower()
            mapped_type = plate_map.get(held, "Normal")
            effective_move = MoveSet(
                name=move.name,
                move_type=mapped_type,
                category=move.category,
                power=move.power,
                accuracy=move.accuracy,
                base_pp=move.base_pp,
                max_pp=move.max_pp,
                current_pp=move.current_pp,
                pp_up_level=move.pp_up_level,
                makes_contact=move.makes_contact,
                target=move.target,
                priority=move.priority,
            )
        if move.name == "Multi-Attack":
            memory_map = {
                "fire memory": "Fire",
                "water memory": "Water",
                "electric memory": "Electric",
                "grass memory": "Grass",
                "ice memory": "Ice",
                "fighting memory": "Fighting",
                "poison memory": "Poison",
                "ground memory": "Ground",
                "flying memory": "Flying",
                "psychic memory": "Psychic",
                "bug memory": "Bug",
                "rock memory": "Rock",
                "ghost memory": "Ghost",
                "dragon memory": "Dragon",
                "dark memory": "Dark",
                "steel memory": "Steel",
                "fairy memory": "Fairy",
            }
            held = "" if self.magic_room_turns > 0 else (attacker.hold_item or "").strip().lower()
            mapped_type = memory_map.get(held, "Normal")
            effective_move = MoveSet(
                name=move.name,
                move_type=mapped_type,
                category=move.category,
                power=move.power,
                accuracy=move.accuracy,
                base_pp=move.base_pp,
                max_pp=move.max_pp,
                current_pp=move.current_pp,
                pp_up_level=move.pp_up_level,
                makes_contact=move.makes_contact,
                target=move.target,
                priority=move.priority,
            )
        if move.name == "Natural Gift":
            held = "" if self.magic_room_turns > 0 else (attacker.hold_item or "").strip().lower()
            if "berry" not in held:
                return f"{attacker.name} dùng Natural Gift nhưng không có Berry phù hợp."
            type_map = {
                "oran berry": "Water",
                "sitrus berry": "Psychic",
                "chesto berry": "Water",
                "cheri berry": "Fire",
                "pecha berry": "Electric",
                "rawst berry": "Grass",
                "aspear berry": "Ice",
                "leppa berry": "Fighting",
                "lum berry": "Psychic",
            }
            mapped_type = type_map.get(held, "Normal")
            effective_move = MoveSet(
                name=move.name,
                move_type=mapped_type,
                category=move.category,
                power=80,
                accuracy=move.accuracy,
                base_pp=move.base_pp,
                max_pp=move.max_pp,
                current_pp=move.current_pp,
                pp_up_level=move.pp_up_level,
                makes_contact=move.makes_contact,
                target=move.target,
                priority=move.priority,
            )
            attacker.hold_item = None
            attacker.berry_consumed = True
        if self.ion_deluge_active and effective_move.move_type == "Normal":
            effective_move = MoveSet(
                name=effective_move.name,
                move_type="Electric",
                category=effective_move.category,
                power=effective_move.power,
                accuracy=effective_move.accuracy,
                base_pp=effective_move.base_pp,
                max_pp=effective_move.max_pp,
                current_pp=effective_move.current_pp,
                pp_up_level=effective_move.pp_up_level,
                makes_contact=effective_move.makes_contact,
                target=effective_move.target,
                priority=effective_move.priority,
            )
        if attacker is self.player_active and self.player_electrified:
            self.player_electrified = False
            effective_move = MoveSet(
                name=move.name,
                move_type="Electric",
                category=move.category,
                power=move.power,
                accuracy=move.accuracy,
                base_pp=move.base_pp,
                max_pp=move.max_pp,
                current_pp=move.current_pp,
                pp_up_level=move.pp_up_level,
                makes_contact=move.makes_contact,
                target=move.target,
                priority=move.priority,
            )
        elif attacker is self.wild and self.wild_electrified:
            self.wild_electrified = False
            effective_move = MoveSet(
                name=move.name,
                move_type="Electric",
                category=move.category,
                power=move.power,
                accuracy=move.accuracy,
                base_pp=move.base_pp,
                max_pp=move.max_pp,
                current_pp=move.current_pp,
                pp_up_level=move.pp_up_level,
                makes_contact=move.makes_contact,
                target=move.target,
                priority=move.priority,
            )
        if move.name == "Nature Power":
            if self.terrain == "electric terrain" and self.terrain_turns > 0:
                nature_name, nature_type = "Thunderbolt", "Electric"
            elif self.terrain == "grassy terrain" and self.terrain_turns > 0:
                nature_name, nature_type = "Energy Ball", "Grass"
            elif self.terrain == "misty terrain" and self.terrain_turns > 0:
                nature_name, nature_type = "Moonblast", "Fairy"
            elif self.terrain == "psychic terrain" and self.terrain_turns > 0:
                nature_name, nature_type = "Psychic", "Psychic"
            else:
                nature_name, nature_type = "Tri Attack", "Normal"
            effective_move = MoveSet(
                name=nature_name,
                move_type=nature_type,
                category="Special",
                power=90 if nature_name != "Tri Attack" else 80,
                accuracy=100,
                base_pp=move.base_pp,
                max_pp=move.max_pp,
                current_pp=move.current_pp,
                pp_up_level=move.pp_up_level,
                makes_contact=False,
                target=move.target,
                priority=move.priority,
            )
        if move.name in {"Revelation Dance", "Raging Bull"} and attacker.types:
            effective_move = MoveSet(
                name=move.name,
                move_type=attacker.types[0],
                category=move.category,
                power=move.power,
                accuracy=move.accuracy,
                base_pp=move.base_pp,
                max_pp=move.max_pp,
                current_pp=move.current_pp,
                pp_up_level=move.pp_up_level,
                makes_contact=move.makes_contact,
                target=move.target,
                priority=move.priority,
            )

            effective_move, z_power_text = self._try_apply_z_crystal(attacker, move, effective_move)

        if attacker is self.player_active:
            self.player_last_move_name = move.name
            self.player_last_move_type = effective_move.move_type
        else:
            self.wild_last_move_name = move.name
            self.wild_last_move_type = effective_move.move_type

        self._mark_move_used(attacker, move.name)

        if move.name in {"Blast Burn", "Eternabeam", "Frenzy Plant", "Giga Impact", "Hydro Cannon", "Hyper Beam", "Meteor Assault", "Prismatic Laser", "Roar of Time", "Rock Wrecker"}:
            if attacker is self.player_active:
                self.player_must_recharge = True
            else:
                self.wild_must_recharge = True

        if move.name == "Metal Burst":
            move.current_pp = max(0, move.current_pp - 1)
            if attacker is self.player_active:
                dmg = self.player_last_damage_taken
                if dmg <= 0:
                    return f"{attacker.name} dùng Metal Burst nhưng thất bại vì chưa nhận sát thương trong lượt này."
                reflected = max(1, int(dmg * 1.5))
                self.wild.current_hp = max(0, self.wild.current_hp - reflected)
                self.wild_took_damage_this_turn = True
                self.player_last_move_name = move.name
                self.player_last_move_type = move.move_type
                return f"{attacker.name} phản kích bằng Metal Burst gây {reflected} sát thương lên {self.wild.name}!"
            dmg = self.wild_last_damage_taken
            if dmg <= 0:
                return f"{attacker.name} dùng Metal Burst nhưng thất bại vì chưa nhận sát thương trong lượt này."
            reflected = max(1, int(dmg * 1.5))
            self.player_active.current_hp = max(0, self.player_active.current_hp - reflected)
            self.player_took_damage_this_turn = True
            self.wild_last_move_name = move.name
            self.wild_last_move_type = move.move_type
            return f"{attacker.name} phản kích bằng Metal Burst gây {reflected} sát thương lên {self.player_active.name}!"

        if (
            self.terrain == "psychic terrain"
            and self.terrain_turns > 0
            and self._effective_priority(attacker, effective_move) > 0
            and self._is_grounded(defender)
        ):
            return f"{attacker.name} dùng {move.name}, nhưng Psychic Terrain chặn đòn ưu tiên!"

        treat_as_status = effective_move.category == "Status" or (
            effective_move.power <= 0 and effective_move.name not in ZERO_POWER_DAMAGING_MOVES and effective_move.name != "Endeavor"
        )

        def _apply_throat_spray(result_text: str) -> str:
            if attacker.current_hp <= 0:
                return result_text
            if self._held_item_name(attacker) != "throat spray":
                return result_text
            if not self._is_sound_move(move.name):
                return result_text
            lowered = result_text.lower()
            if "thất bại" in lowered or "trượt" in lowered or "không thể" in lowered:
                return result_text
            changed, stage_text = self._change_stat_stage(attacker, "sp_attack", +1)
            if not changed:
                return result_text
            attacker.hold_item = None
            return result_text + f"\n{attacker.name} kích hoạt Throat Spray! Sp. Attack tăng {stage_text}."

        if treat_as_status:
            resolved_status = _apply_throat_spray(self._resolve_status_move(attacker, defender, effective_move))
            eject_pack_logs = self._consume_pending_eject_pack()
            if eject_pack_logs:
                resolved_status = resolved_status + "\n" + "\n".join(eject_pack_logs)
            if leppa_text:
                resolved_status = resolved_status + f"\n{leppa_text}"
            if z_power_text:
                resolved_status = f"{z_power_text}\n{resolved_status}"
            if power_herb_text:
                return f"{power_herb_text}\n{resolved_status}"
            return resolved_status

        resolved_damage = _apply_throat_spray(self._resolve_damage(attacker, defender, effective_move))
        eject_pack_logs = self._consume_pending_eject_pack()
        if eject_pack_logs:
            resolved_damage = resolved_damage + "\n" + "\n".join(eject_pack_logs)
        if leppa_text:
            resolved_damage = resolved_damage + f"\n{leppa_text}"
        if z_power_text:
            resolved_damage = f"{z_power_text}\n{resolved_damage}"
        if power_herb_text:
            return f"{power_herb_text}\n{resolved_damage}"
        return resolved_damage

    def _resolve_status_move(self, attacker: PokemonInstance, defender: PokemonInstance, move: MoveSet) -> str:
        attacker_taunt_turns = self.player_taunt_turns if attacker is self.player_active else self.wild_taunt_turns
        if attacker_taunt_turns > 0 and move.name != "Taunt":
            return f"{attacker.name} không thể dùng {move.name} vì đang bị Taunt!"

        defender_crafty_shield = (
            (defender is self.player_active and self.player_crafty_shield_active)
            or (defender is self.wild and self.wild_crafty_shield_active)
        )
        if defender_crafty_shield:
            return f"{attacker.name} dùng {move.name}, nhưng bị Crafty Shield chặn lại!"

        defender_magic_coat = (
            (defender is self.player_active and self.player_magic_coat_active)
            or (defender is self.wild and self.wild_magic_coat_active)
        )
        if defender_magic_coat and move.name != "Magic Coat":
            reflected = resolve_status_move_effect(self, defender, attacker, move)
            if reflected is not None:
                return f"{attacker.name} dùng {move.name}, nhưng bị Magic Coat phản lại! {reflected}"
            return f"{attacker.name} dùng {move.name}, nhưng bị Magic Coat phản lại!"

        lock_on_ready = self.player_lock_on_ready if attacker is self.player_active else self.wild_lock_on_ready
        guaranteed_hit = lock_on_ready and move.name != "Lock-On"
        if guaranteed_hit:
            if attacker is self.player_active:
                self.player_lock_on_ready = False
            else:
                self.wild_lock_on_ready = False

        def _apply_blunder_policy(miss_text: str) -> str:
            if attacker.current_hp <= 0:
                return miss_text
            if self._held_item_name(attacker) != "blunder policy":
                return miss_text
            changed, stage_text = self._change_stat_stage(attacker, "speed", +2)
            if not changed:
                return miss_text
            attacker.hold_item = None
            return miss_text + f" {attacker.name} kích hoạt Blunder Policy! Speed tăng mạnh {stage_text}."

        effective_accuracy = max(1, min(100, int(move.accuracy))) if move.accuracy > 0 else 100
        if move.accuracy > 0:
            attacker_item = self._held_item_name(attacker)
            defender_item = self._held_item_name(defender)
            if attacker_item == "wide lens":
                effective_accuracy = min(100, int(round(effective_accuracy * 1.1)))
            target_moved_first = (
                (attacker is self.player_active and self.wild_acted_before_player)
                or (attacker is self.wild and self.player_acted_before_wild)
            )
            if attacker_item == "zoom lens" and target_moved_first:
                effective_accuracy = min(100, int(round(effective_accuracy * 1.2)))
            if defender_item in {"bright powder", "lax incense", "pure incense"}:
                effective_accuracy = max(1, int(round(effective_accuracy * 0.9)))
            if attacker is self.player_active and self.player_micle_accuracy_boost:
                effective_accuracy = min(100, int(round(effective_accuracy * 1.2)))
                self.player_micle_accuracy_boost = False
            elif attacker is self.wild and self.wild_micle_accuracy_boost:
                effective_accuracy = min(100, int(round(effective_accuracy * 1.2)))
                self.wild_micle_accuracy_boost = False

        if not guaranteed_hit and move.accuracy > 0 and random.randint(1, 100) > effective_accuracy:
            return _apply_blunder_policy(f"{attacker.name} dùng {move.name} nhưng trượt!")

        defender_snatch = (
            (defender is self.player_active and getattr(self, "player_snatch_active", False))
            or (defender is self.wild and getattr(self, "wild_snatch_active", False))
        )
        if defender_snatch and move.name != "Snatch":
            if defender is self.player_active:
                self.player_snatch_active = False
            else:
                self.wild_snatch_active = False
            stolen = resolve_status_move_effect(self, defender, attacker, move)
            if stolen is not None:
                return f"{attacker.name} dùng {move.name}, nhưng bị Snatch cướp mất! {stolen}"
            return f"{attacker.name} dùng {move.name}, nhưng bị Snatch cướp mất!"

        resolved = resolve_status_move_effect(self, attacker, defender, move)
        if resolved is not None:
            return resolved

        return f"{attacker.name} dùng {move.name}, nhưng hiệu ứng chiêu này chưa được triển khai."

    def _resolve_damage(self, attacker: PokemonInstance, defender: PokemonInstance, move: MoveSet) -> str:
        if move.name == "Techno Blast":
            held = ("" if self.magic_room_turns > 0 else (attacker.hold_item or "")).strip().lower()
            if "burn drive" in held:
                move.move_type = "Fire"
            elif "douse drive" in held:
                move.move_type = "Water"
            elif "chill drive" in held:
                move.move_type = "Ice"
            elif "shock drive" in held:
                move.move_type = "Electric"
            else:
                move.move_type = "Normal"

        if move.name == "Terrain Pulse":
            if self.terrain_turns > 0 and self.terrain:
                terrain_to_type = {
                    "electric terrain": "Electric",
                    "grassy terrain": "Grass",
                    "misty terrain": "Fairy",
                    "psychic terrain": "Psychic",
                }
                move.move_type = terrain_to_type.get(self.terrain, "Normal")
            else:
                move.move_type = "Normal"

        if move.name in {"Tera Blast", "Tera Starstorm"}:
            if getattr(attacker, "form", "") == "Terastal" and attacker.types:
                move.move_type = attacker.types[0]
            else:
                move.move_type = "Normal"

        if move.name == "Weather Ball":
            if self.weather_turns > 0:
                weather_type = {
                    "rain": "Water",
                    "harsh sunlight": "Fire",
                    "sandstorm": "Rock",
                    "snow": "Ice",
                }.get(self.weather)
                if weather_type:
                    move.move_type = weather_type
            else:
                move.move_type = "Normal"

        if move.name == "Ivy Cudgel":
            attacker_name = (attacker.name or "").strip().lower()
            held = self._held_item_name(attacker)
            if attacker_name.startswith("ogerpon"):
                mask_type_map = {
                    "hearthflame mask": "Fire",
                    "wellspring mask": "Water",
                    "cornerstone mask": "Rock",
                }
                move.move_type = mask_type_map.get(held, "Grass")
            else:
                move.move_type = "Grass"

        defender_glaive_vulnerable = (
            (defender is self.player_active and self.player_glaive_rush_vulnerable_turns > 0)
            or (defender is self.wild and self.wild_glaive_rush_vulnerable_turns > 0)
        )
        always_hits = move.name in {"Aerial Ace", "Aura Sphere", "Disarming Voice", "False Surrender", "Feint Attack", "Flower Trick", "Hyper Drill", "Hyperspace Fury", "Hyperspace Hole", "Kowtow Cleave", "Magical Leaf", "Light That Burns the Sky", "Magnet Bomb", "Shadow Punch", "Shock Wave", "Smart Strike", "Swift", "Tachyon Cutter", "Vital Throw"} or (
            move.name == "Blizzard" and self.weather == "snow" and self.weather_turns > 0
        ) or defender_glaive_vulnerable
        lock_on_ready = self.player_lock_on_ready if attacker is self.player_active else self.wild_lock_on_ready
        if lock_on_ready:
            always_hits = True
            if attacker is self.player_active:
                self.player_lock_on_ready = False
            else:
                self.wild_lock_on_ready = False
        effective_accuracy = 100 if move.accuracy <= 0 else max(1, min(100, int(move.accuracy)))
        if move.name == "Thunder":
            if self.weather == "rain" and self.weather_turns > 0:
                effective_accuracy = 100
            elif self.weather == "harsh sunlight" and self.weather_turns > 0:
                effective_accuracy = 50
        if move.accuracy > 0:
            attacker_item = self._held_item_name(attacker)
            defender_item = self._held_item_name(defender)
            if attacker_item == "wide lens":
                effective_accuracy = min(100, int(round(effective_accuracy * 1.1)))
            target_moved_first = (
                (attacker is self.player_active and self.wild_acted_before_player)
                or (attacker is self.wild and self.player_acted_before_wild)
            )
            if attacker_item == "zoom lens" and target_moved_first:
                effective_accuracy = min(100, int(round(effective_accuracy * 1.2)))
            if defender_item in {"bright powder", "lax incense", "pure incense"}:
                effective_accuracy = max(1, int(round(effective_accuracy * 0.9)))
            if attacker is self.player_active and self.player_micle_accuracy_boost:
                effective_accuracy = min(100, int(round(effective_accuracy * 1.2)))
                self.player_micle_accuracy_boost = False
            elif attacker is self.wild and self.wild_micle_accuracy_boost:
                effective_accuracy = min(100, int(round(effective_accuracy * 1.2)))
                self.wild_micle_accuracy_boost = False

        def _apply_blunder_policy(miss_text: str) -> str:
            if attacker.current_hp <= 0:
                return miss_text
            if self._held_item_name(attacker) != "blunder policy":
                return miss_text
            changed, stage_text = self._change_stat_stage(attacker, "speed", +2)
            if not changed:
                return miss_text
            attacker.hold_item = None
            return miss_text + f" {attacker.name} kích hoạt Blunder Policy! Speed tăng mạnh {stage_text}."

        missed = (not always_hits and random.randint(1, 100) > effective_accuracy)
        if missed:
            if move.name == "Axe Kick":
                crash = max(1, attacker.max_hp // 2)
                attacker.current_hp = max(0, attacker.current_hp - crash)
                return _apply_blunder_policy(
                    f"{attacker.name} dùng {move.name} nhưng trượt! "
                    f"{attacker.name} bị phản lực mất {crash} HP ({attacker.current_hp}/{attacker.max_hp})."
                )
            if move.name in {"High Jump Kick", "Jump Kick"}:
                crash = max(1, attacker.max_hp // 2)
                attacker.current_hp = max(0, attacker.current_hp - crash)
                return _apply_blunder_policy(
                    f"{attacker.name} dùng {move.name} nhưng trượt! "
                    f"{attacker.name} bị phản lực mất {crash} HP ({attacker.current_hp}/{attacker.max_hp})."
                )
            if move.name == "Supercell Slam":
                crash = max(1, attacker.max_hp // 2)
                attacker.current_hp = max(0, attacker.current_hp - crash)
                return _apply_blunder_policy(
                    f"{attacker.name} dùng {move.name} nhưng trượt! "
                    f"{attacker.name} bị phản lực mất {crash} HP ({attacker.current_hp}/{attacker.max_hp})."
                )
            return _apply_blunder_policy(f"{attacker.name} dùng {move.name} nhưng trượt!")

        defender_quick_guard = (
            (defender is self.player_active and self.player_quick_guard_active)
            or (defender is self.wild and self.wild_quick_guard_active)
        )
        if defender_quick_guard and self._effective_priority(attacker, move) > 0 and move.name != "Feint":
            return f"{attacker.name} dùng {move.name}, nhưng bị Quick Guard chặn đòn ưu tiên!"

        if move.name == "Upper Hand":
            selected_name = self.player_selected_move_name if defender is self.player_active else self.wild_selected_move_name
            selected_move = next((mv for mv in defender.moves if mv.name == selected_name), None)
            selected_priority = self._effective_priority(defender, selected_move)
            defender_already_acted = (
                (defender is self.player_active and self.player_acted_before_wild)
                or (defender is self.wild and self.wild_acted_before_player)
            )
            if defender_already_acted or selected_priority <= 0:
                return f"{attacker.name} dùng Upper Hand nhưng thất bại vì mục tiêu không dùng đòn ưu tiên."

        defender_under_protect = (
            (defender is self.player_active and self.player_protect_active)
            or (defender is self.wild and self.wild_protect_active)
        )
        if move.name == "Feint" and not defender_under_protect:
            return f"{attacker.name} dùng Feint nhưng thất bại vì mục tiêu không dùng Protect/Detect trong lượt này."
        if move.name == "Feint" and defender_under_protect:
            if defender is self.player_active:
                self.player_protect_active = False
            else:
                self.wild_protect_active = False
            defender_under_protect = False
        if move.name in {"Hyper Drill", "Hyperspace Fury", "Hyperspace Hole", "Phantom Force", "Shadow Force"} and defender_under_protect:
            if defender is self.player_active:
                self.player_protect_active = False
            else:
                self.wild_protect_active = False
            defender_under_protect = False
        if move.name in {"G-Max One Blow", "G-Max Rapid Flow"} and defender_under_protect:
            if defender is self.player_active:
                self.player_protect_active = False
            else:
                self.wild_protect_active = False
            defender_under_protect = False

        if defender_under_protect:
            text = f"{attacker.name} dùng {move.name}, nhưng bị Protect chặn lại!"
            defender_bunker = (
                (defender is self.player_active and self.player_baneful_bunker_active)
                or (defender is self.wild and self.wild_baneful_bunker_active)
            )
            if defender_bunker and move.makes_contact and attacker.current_hp > 0 and attacker.status is None:
                if "Poison" not in attacker.types and "Steel" not in attacker.types and attacker.ability != "Immunity":
                    attacker.status = "psn"
                    attacker.status_counter = 0
                    text += f" {attacker.name} bị nhiễm độc do Baneful Bunker!"
            defender_bulwark = (
                (defender is self.player_active and self.player_burning_bulwark_active)
                or (defender is self.wild and self.wild_burning_bulwark_active)
            )
            if defender_bulwark and move.makes_contact and attacker.current_hp > 0 and attacker.status is None:
                if "Fire" not in attacker.types:
                    attacker.status = "brn"
                    attacker.status_counter = 0
                    text += f" {attacker.name} bị Burn do Burning Bulwark!"
            defender_kings_shield = (
                (defender is self.player_active and self.player_kings_shield_active)
                or (defender is self.wild and self.wild_kings_shield_active)
            )
            if defender_kings_shield and move.makes_contact and attacker.current_hp > 0:
                changed, stage_text = self._change_stat_stage(attacker, "attack", -1)
                if changed:
                    text += f" Attack của {attacker.name} giảm {stage_text} do King's Shield!"
            defender_obstruct = (
                (defender is self.player_active and self.player_obstruct_active)
                or (defender is self.wild and self.wild_obstruct_active)
            )
            if defender_obstruct and move.makes_contact and attacker.current_hp > 0:
                changed, stage_text = self._change_stat_stage(attacker, "defense", -2)
                if changed:
                    text += f" Defense của {attacker.name} giảm mạnh {stage_text} do Obstruct!"
            defender_spiky_shield = (
                (defender is self.player_active and self.player_spiky_shield_active)
                or (defender is self.wild and self.wild_spiky_shield_active)
            )
            if defender_spiky_shield and move.makes_contact and attacker.current_hp > 0:
                recoil = max(1, attacker.max_hp // 8)
                attacker.current_hp = max(0, attacker.current_hp - recoil)
                text += f" {attacker.name} bị gai từ Spiky Shield gây {recoil} sát thương!"
            defender_silk_trap = (
                (defender is self.player_active and self.player_silk_trap_active)
                or (defender is self.wild and self.wild_silk_trap_active)
            )
            if defender_silk_trap and move.makes_contact and attacker.current_hp > 0:
                changed, stage_text = self._change_stat_stage(attacker, "speed", -1)
                if changed:
                    text += f" Speed của {attacker.name} giảm {stage_text} do Silk Trap!"
            return text

        if defender is self.player_active and self.player_bounce_charging and move.name not in {"Sky Uppercut"}:
            return f"{attacker.name} dùng {move.name} nhưng {defender.name} đang ở trên không nên né được!"
        if defender is self.wild and self.wild_bounce_charging and move.name not in {"Sky Uppercut"}:
            return f"{attacker.name} dùng {move.name} nhưng {defender.name} đang ở trên không nên né được!"
        if defender is self.player_active and self.player_fly_charging and move.name not in {"Sky Uppercut", "Smack Down", "Sky Drop"}:
            return f"{attacker.name} dùng {move.name} nhưng {defender.name} đang ở trên không nên né được!"
        if defender is self.wild and self.wild_fly_charging and move.name not in {"Sky Uppercut", "Smack Down", "Sky Drop"}:
            return f"{attacker.name} dùng {move.name} nhưng {defender.name} đang ở trên không nên né được!"
        if defender is self.player_active and getattr(self, "player_phantom_force_charging", False):
            return f"{attacker.name} dùng {move.name} nhưng {defender.name} đã biến mất bằng Phantom Force!"
        if defender is self.wild and getattr(self, "wild_phantom_force_charging", False):
            return f"{attacker.name} dùng {move.name} nhưng {defender.name} đã biến mất bằng Phantom Force!"
        if defender is self.player_active and self.player_dig_charging and move.name != "Earthquake":
            return f"{attacker.name} dùng {move.name} nhưng {defender.name} đang ở dưới đất nên né được!"
        if defender is self.wild and self.wild_dig_charging and move.name != "Earthquake":
            return f"{attacker.name} dùng {move.name} nhưng {defender.name} đang ở dưới đất nên né được!"
        if defender is self.player_active and self.player_dive_charging:
            return f"{attacker.name} dùng {move.name} nhưng {defender.name} đang dưới nước nên né được!"
        if defender is self.wild and self.wild_dive_charging:
            return f"{attacker.name} dùng {move.name} nhưng {defender.name} đang dưới nước nên né được!"

        if move.name == "Synchronoise" and not (set(attacker.types) & set(defender.types)):
            return f"{attacker.name} dùng Synchronoise nhưng không có tác dụng lên {defender.name}!"

        contact_burn_text = ""
        defender_beak_blast_heating = (
            (defender is self.player_active and self.player_beak_blast_heating)
            or (defender is self.wild and self.wild_beak_blast_heating)
        )
        if defender_beak_blast_heating and move.makes_contact and attacker.current_hp > 0 and attacker.status is None:
            if "Fire" not in attacker.types:
                attacker.status = "brn"
                attacker.status_counter = 0
                contact_burn_text = f" {attacker.name} bị Burn do chạm vào Beak Blast đang nung nóng!"

        if move.category == "Special":
            atk = self._effective_stat(attacker, "sp_attack")
            dfn = self._effective_stat(defender, "sp_defense")
        else:
            if move.name == "Body Press":
                atk = self._effective_stat(attacker, "defense")
            elif move.name == "Foul Play":
                atk = self._effective_stat(defender, "attack")
            else:
                atk = self._effective_stat(attacker, "attack")
            if move.name == "Darkest Lariat":
                dfn = max(1, int(defender.defense))
            else:
                dfn = self._effective_stat(defender, "defense")

        if move.name in {"Psyshock", "Psystrike"}:
            atk = self._effective_stat(attacker, "sp_attack")
            dfn = self._effective_stat(defender, "defense")
        if move.name == "Secret Sword":
            atk = self._effective_stat(attacker, "sp_attack")
            dfn = self._effective_stat(defender, "defense")
        if move.name == "Sacred Sword":
            dfn = max(1, int(defender.defense))
        if move.name == "Shell Side Arm":
            physical_ratio = self._effective_stat(attacker, "attack") / max(1, self._effective_stat(defender, "defense"))
            special_ratio = self._effective_stat(attacker, "sp_attack") / max(1, self._effective_stat(defender, "sp_defense"))
            if physical_ratio > special_ratio:
                atk = self._effective_stat(attacker, "attack")
                dfn = self._effective_stat(defender, "defense")
            else:
                atk = self._effective_stat(attacker, "sp_attack")
                dfn = self._effective_stat(defender, "sp_defense")

        if move.name == "Light That Burns the Sky":
            physical_ratio = self._effective_stat(attacker, "attack") / max(1, self._effective_stat(defender, "defense"))
            special_ratio = self._effective_stat(attacker, "sp_attack") / max(1, self._effective_stat(defender, "sp_defense"))
            if special_ratio >= physical_ratio:
                atk = self._effective_stat(attacker, "sp_attack")
                dfn = self._effective_stat(defender, "sp_defense")
            else:
                atk = self._effective_stat(attacker, "attack")
                dfn = self._effective_stat(defender, "defense")

        if move.name == "Photon Geyser":
            if self._effective_stat(attacker, "sp_attack") >= self._effective_stat(attacker, "attack"):
                atk = self._effective_stat(attacker, "sp_attack")
                dfn = self._effective_stat(defender, "sp_defense")
            else:
                atk = self._effective_stat(attacker, "attack")
                dfn = self._effective_stat(defender, "defense")

        # Apply ability effect (e.g., Blaze) to damage multiplier
        ability_multiplier = 1.0
        if hasattr(attacker, "ability") and attacker.ability:
            ability_func = get_ability_effect(attacker.ability)
            try:
                value = ability_func(attacker, move)
                if isinstance(value, (int, float)):
                    ability_multiplier = float(value)
                else:
                    ability_multiplier = 1.0
            except TypeError:
                ability_multiplier = 1.0

        if attacker.status == "brn" and move.category == "Physical":
            if attacker.ability != "Guts":
                ability_multiplier *= 0.5

        present_power_override: int | None = None
        if move.name == "Present":
            roll = random.random()
            if roll < 0.25:
                if defender.current_hp <= 0:
                    return f"{attacker.name} dùng Present, nhưng mục tiêu đã gục."
                heal = max(1, defender.max_hp // 4)
                before = defender.current_hp
                defender.current_hp = min(defender.max_hp, defender.current_hp + heal)
                healed = max(0, defender.current_hp - before)
                return (
                    f"{attacker.name} dùng Present, nhưng nó trở thành quà hồi máu cho {defender.name}: "
                    f"hồi {healed} HP ({defender.current_hp}/{defender.max_hp})."
                )
            if roll < 0.50:
                present_power_override = 40
            elif roll < 0.80:
                present_power_override = 80
            else:
                present_power_override = 120

        move_power = move.power
        if present_power_override is not None:
            move_power = present_power_override
        if defender_glaive_vulnerable:
            move_power = move_power * 2
        if move_power <= 0 and move.name in ZERO_POWER_DAMAGE_OVERRIDES:
            move_power = ZERO_POWER_DAMAGE_OVERRIDES[move.name]
        if move.name == "Acrobatics" and not attacker.hold_item:
            move_power = move_power * 2
        if move.name == "Assurance":
            defender_took_damage = self.player_took_damage_this_turn if defender is self.player_active else self.wild_took_damage_this_turn
            if defender_took_damage:
                move_power = move_power * 2
        if move.name == "Avalanche":
            attacker_took_damage = self.player_took_damage_this_turn if attacker is self.player_active else self.wild_took_damage_this_turn
            if attacker_took_damage:
                move_power = move_power * 2
        if move.name == "Shell Trap":
            attacker_took_physical = self.player_last_physical_damage_taken > 0 if attacker is self.player_active else self.wild_last_physical_damage_taken > 0
            if attacker_took_physical:
                move_power = int(move_power * 1.5)
        if move.name == "Barb Barrage" and defender.status in {"psn", "tox"}:
            move_power = move_power * 2
        if move.name in {"Behemoth Bash", "Behemoth Blade"} and getattr(defender, "is_dynamaxed", False):
            move_power = move_power * 2
        if move.name == "Dynamax Cannon" and getattr(defender, "is_dynamaxed", False):
            move_power = move_power * 2
        if move.name == "Collision Course" and self.game_data.type_multiplier(move.move_type, defender.types) > 1:
            move_power = int(move_power * 4 / 3)
        if move.name == "Electro Drift" and self.game_data.type_multiplier(move.move_type, defender.types) > 1:
            move_power = int(move_power * 4 / 3)
        if move.name == "Crush Grip":
            ratio = defender.current_hp / max(1, defender.max_hp)
            move_power = max(1, int(120 * ratio))
        if move.name == "Wring Out":
            ratio = defender.current_hp / max(1, defender.max_hp)
            move_power = max(1, int(120 * ratio))
        if move.name == "Electro Ball":
            attacker_speed = max(1, self._effective_stat(attacker, "speed"))
            defender_speed = max(1, self._effective_stat(defender, "speed"))
            speed_ratio = attacker_speed / defender_speed
            if speed_ratio >= 4:
                move_power = 150
            elif speed_ratio >= 3:
                move_power = 120
            elif speed_ratio >= 2:
                move_power = 80
            elif speed_ratio >= 1:
                move_power = 60
            else:
                move_power = 40
        if move.name == "Magnitude":
            roll = random.choices(
                [10, 30, 50, 70, 90, 110, 150],
                weights=[5, 10, 20, 30, 20, 10, 5],
                k=1,
            )[0]
            move_power = roll
        if move.name == "Charge Beam" and attacker is self.player_active and self.player_charge_boost:
            move_power = move_power * 2
            self.player_charge_boost = False
        if move.name == "Charge Beam" and attacker is self.wild and self.wild_charge_boost:
            move_power = move_power * 2
            self.wild_charge_boost = False
        if move.move_type == "Electric" and move.name != "Charge Beam":
            if attacker is self.player_active and self.player_charge_boost:
                move_power = move_power * 2
                self.player_charge_boost = False
            if attacker is self.wild and self.wild_charge_boost:
                move_power = move_power * 2
                self.wild_charge_boost = False
        if move.name == "Bolt Beak":
            moved_first = (attacker is self.player_active and self.player_acted_before_wild) or (
                attacker is self.wild and self.wild_acted_before_player
            )
            if moved_first:
                move_power = move_power * 2
        if move.name == "Fishious Rend":
            moved_first = (attacker is self.player_active and self.player_acted_before_wild) or (
                attacker is self.wild and self.wild_acted_before_player
            )
            if moved_first:
                move_power = move_power * 2
        if move.name == "Temper Flare":
            attacker_took_damage = self.player_took_damage_this_turn if attacker is self.player_active else self.wild_took_damage_this_turn
            if attacker_took_damage:
                move_power = move_power * 2
        if move.name == "Fusion Bolt":
            boosted = (attacker is self.player_active and self.wild_acted_before_player and self.wild_last_move_name == "Fusion Flare") or (
                attacker is self.wild and self.player_acted_before_wild and self.player_last_move_name == "Fusion Flare"
            )
            if boosted:
                move_power = move_power * 2
        if move.name == "Fusion Flare":
            boosted = (attacker is self.player_active and self.wild_acted_before_player and self.wild_last_move_name == "Fusion Bolt") or (
                attacker is self.wild and self.player_acted_before_wild and self.player_last_move_name == "Fusion Bolt"
            )
            if boosted:
                move_power = move_power * 2
        if move.name == "Brine" and defender.current_hp <= (defender.max_hp // 2):
            move_power = move_power * 2
        if move.name == "Stored Power":
            stages = self._stat_stages_for(attacker)
            positive_total = sum(max(0, value) for value in stages.values())
            move_power = 20 + (20 * positive_total)
        if move.name == "Trump Card":
            pp_left = max(0, move.current_pp)
            if pp_left <= 0:
                move_power = 200
            elif pp_left == 1:
                move_power = 80
            elif pp_left == 2:
                move_power = 60
            elif pp_left == 3:
                move_power = 50
            else:
                move_power = 40
        if move.name == "Surging Strikes":
            atk = max(1, int(attacker.attack))
            dfn = max(1, int(defender.defense))
        if move.name == "Dragon Energy":
            ratio = attacker.current_hp / max(1, attacker.max_hp)
            move_power = max(1, int(150 * ratio))
        if move.name == "Eruption":
            ratio = attacker.current_hp / max(1, attacker.max_hp)
            move_power = max(1, int(150 * ratio))
        if move.name == "Water Spout":
            ratio = attacker.current_hp / max(1, attacker.max_hp)
            move_power = max(1, int(150 * ratio))
        if move.name == "Expanding Force" and self.terrain == "psychic terrain" and self.terrain_turns > 0 and self._is_grounded(attacker):
            move_power = int(move_power * 1.5)
        if move.name == "Misty Explosion" and self.terrain == "misty terrain" and self.terrain_turns > 0 and self._is_grounded(attacker):
            move_power = int(move_power * 1.5)
        if move.name == "Terrain Pulse" and self.terrain_turns > 0 and self.terrain:
            move_power = move_power * 2
        if move.name == "Weather Ball" and self.weather_turns > 0:
            move_power = move_power * 2
        if move.name == "Venoshock" and defender.status in {"psn", "tox"}:
            move_power = move_power * 2
        if move.name == "Twister" and (
            (defender is self.player_active and (self.player_fly_charging or self.player_bounce_charging))
            or (defender is self.wild and (self.wild_fly_charging or self.wild_bounce_charging))
        ):
            move_power = move_power * 2
        if move.name == "Twinkle Tackle":
            move_power = max(move_power, 190)
        if move.name == "Veevee Volley":
            friendship = max(0, int(getattr(attacker, "friendship", 70)))
            move_power = max(1, min(102, friendship // 2))
        if move.name == "Venoshock" and defender.status in {"psn", "tox"}:
            move_power = move_power * 2
        if move.name == "Facade" and attacker.status in {"brn", "psn", "tox", "par"}:
            move_power = move_power * 2
        if move.name == "Smelling Salts" and defender.status == "par":
            move_power = move_power * 2
        if move.name == "Spit Up":
            stockpile_count = self.player_stockpile_count if attacker is self.player_active else self.wild_stockpile_count
            if stockpile_count <= 0:
                return f"{attacker.name} dùng Spit Up nhưng chưa Stockpile nên thất bại!"
            move_power = 100 * stockpile_count
            if attacker is self.player_active:
                self.player_stockpile_count = 0
            else:
                self.wild_stockpile_count = 0
        if move.name == "Steel Roller":
            if self.terrain_turns <= 0 or not self.terrain:
                return f"{attacker.name} dùng Steel Roller nhưng không có terrain nên thất bại!"
            self.terrain = None
            self.terrain_turns = 0
        if move.name == "Earthquake" and (
            (defender is self.player_active and self.player_dig_charging)
            or (defender is self.wild and self.wild_dig_charging)
        ):
            move_power = move_power * 2
        if move.name == "Echoed Voice":
            chain = self.player_echoed_voice_chain if attacker is self.player_active else self.wild_echoed_voice_chain
            chain = max(1, min(5, chain))
            move_power = min(200, 40 * chain)
        if move.name == "Fickle Beam" and random.random() < 0.30:
            move_power = move_power * 2
        if move.name == "Flail":
            hp_ratio = attacker.current_hp / max(1, attacker.max_hp)
            if hp_ratio <= 1 / 48:
                move_power = 200
            elif hp_ratio <= 1 / 5:
                move_power = 150
            elif hp_ratio <= 7 / 20:
                move_power = 100
            elif hp_ratio <= 17 / 35:
                move_power = 80
            elif hp_ratio <= 11 / 16:
                move_power = 40
            else:
                move_power = 20
        if move.name == "Fling":
            held = (attacker.hold_item or "").strip().lower()
            if not held:
                return f"{attacker.name} dùng Fling nhưng không cầm item để ném."
            if "iron ball" in held:
                move_power = 130
            elif "flame orb" in held or "toxic orb" in held:
                move_power = 30
            elif "berry" in held:
                move_power = 10
            else:
                move_power = 50
        if move.name == "Fury Cutter":
            chain = self.player_fury_cutter_chain if attacker is self.player_active else self.wild_fury_cutter_chain
            chain = max(1, min(4, chain))
            move_power = min(160, 40 * (2 ** (chain - 1)))
        if move.name == "Frustration":
            move_power = 102
        if move.name == "Grass Knot":
            hp_ref = defender.max_hp
            if hp_ref >= 220:
                move_power = 120
            elif hp_ref >= 180:
                move_power = 100
            elif hp_ref >= 140:
                move_power = 80
            elif hp_ref >= 110:
                move_power = 60
            elif hp_ref >= 80:
                move_power = 40
            else:
                move_power = 20
        if move.name == "Low Kick":
            hp_ref = defender.max_hp
            if hp_ref >= 220:
                move_power = 120
            elif hp_ref >= 180:
                move_power = 100
            elif hp_ref >= 140:
                move_power = 80
            elif hp_ref >= 110:
                move_power = 60
            elif hp_ref >= 80:
                move_power = 40
            else:
                move_power = 20
        if move.name == "Gyro Ball":
            attacker_speed = max(1, self._effective_stat(attacker, "speed"))
            defender_speed = max(1, self._effective_stat(defender, "speed"))
            move_power = min(150, max(1, int(25 * defender_speed / attacker_speed)))
        if move.name == "Hard Press":
            ratio = defender.current_hp / max(1, defender.max_hp)
            move_power = max(1, int(100 * ratio))
        if move.name in {"Heat Crash", "Heavy Slam"}:
            attacker_hp = max(1, attacker.max_hp)
            defender_hp = max(1, defender.max_hp)
            ratio = attacker_hp / defender_hp
            if ratio >= 5:
                move_power = 120
            elif ratio >= 4:
                move_power = 100
            elif ratio >= 3:
                move_power = 80
            elif ratio >= 2:
                move_power = 60
            else:
                move_power = 40
        if move.name == "Ice Ball":
            chain = self.player_ice_ball_chain if attacker is self.player_active else self.wild_ice_ball_chain
            chain = max(0, min(4, chain - 1))
            move_power = min(480, move_power * (2 ** chain))
        if move.name == "Rollout":
            chain = self.player_rollout_chain if attacker is self.player_active else self.wild_rollout_chain
            chain = max(0, min(4, chain - 1))
            move_power = min(480, move_power * (2 ** chain))
        if move.name == "Infernal Parade" and defender.status is not None:
            move_power = move_power * 2
        if move.name == "Lash Out":
            lowered = self.player_stats_lowered_this_turn if attacker is self.player_active else self.wild_stats_lowered_this_turn
            if lowered:
                move_power = move_power * 2
        if move.name == "Payback":
            moved_second = (attacker is self.player_active and not self.player_acted_before_wild) or (
                attacker is self.wild and not self.wild_acted_before_player
            )
            if moved_second:
                move_power = move_power * 2
        if move.name == "Punishment":
            positive_target_stages = sum(max(0, value) for value in self._stat_stages_for(defender).values())
            move_power = min(200, 60 + (20 * positive_target_stages))
        if move.name == "Pursuit":
            target_switching = (
                attacker is self.wild and self.player_switched_this_turn
            ) or (
                attacker is self.player_active and self.wild_switched_this_turn
            )
            if target_switching:
                move_power = move_power * 2
        if move.name == "Power Trip":
            positive_stages = sum(max(0, value) for value in self._stat_stages_for(attacker).values())
            move_power = 20 + (20 * positive_stages)
        if move.name == "Rage Fist":
            hit_count = self.player_hit_count if attacker is self.player_active else self.wild_hit_count
            move_power = min(350, 50 + 50 * max(0, hit_count))
        if move.name == "Knock Off" and defender.hold_item:
            move_power = int(move_power * 1.5)
        if move.name == "Last Respects":
            if attacker is self.player_active:
                fainted = sum(1 for p in self.player.party if p.current_hp <= 0 and p is not attacker)
            else:
                fainted = 0
            move_power = max(50, min(300, 50 + 50 * fainted))
        if move.name == "Pika Papow":
            move_power = max(40, min(190, 40 + attacker.level * 3))
        if move.name == "Return":
            move_power = 102
        if move.name == "Retaliate":
            ready = self.player_retaliate_ready if attacker is self.player_active else self.wild_retaliate_ready
            if ready:
                move_power = move_power * 2
                if attacker is self.player_active:
                    self.player_retaliate_ready = False
                else:
                    self.wild_retaliate_ready = False
        if move.name == "Revenge":
            attacker_took_damage = self.player_took_damage_this_turn if attacker is self.player_active else self.wild_took_damage_this_turn
            if attacker_took_damage:
                move_power = move_power * 2
        if move.name == "Reversal":
            hp_ratio = attacker.current_hp / max(1, attacker.max_hp)
            if hp_ratio <= 1 / 48:
                move_power = 200
            elif hp_ratio <= 1 / 5:
                move_power = 150
            elif hp_ratio <= 7 / 20:
                move_power = 100
            elif hp_ratio <= 17 / 35:
                move_power = 80
            elif hp_ratio <= 11 / 16:
                move_power = 40
            else:
                move_power = 20
        if move.name == "Rising Voltage" and self.terrain == "electric terrain" and self.terrain_turns > 0 and self._is_grounded(defender):
            move_power = move_power * 2
        if move.name == "Ruination":
            move_power = 1
        if move.name == "Psyblade" and self.terrain == "electric terrain" and self.terrain_turns > 0:
            move_power = int(move_power * 1.5)
        if move.name == "Gust" and (
            (defender is self.player_active and (self.player_fly_charging or self.player_bounce_charging))
            or (defender is self.wild and (self.wild_fly_charging or self.wild_bounce_charging))
        ):
            move_power = move_power * 2
        if move.name == "Hex" and defender.status is not None:
            move_power = move_power * 2
        if move.name == "Hydro Steam" and self.weather == "harsh sunlight" and self.weather_turns > 0:
            move_power = int(move_power * 1.5)

        if move.name == "Beat Up":
            if attacker is self.player_active:
                members = [pkmn for pkmn in self.player.party if pkmn.current_hp > 0]
            else:
                members = [attacker]

            total_damage = 0
            hit_count = 0
            for member in members:
                if defender.current_hp <= 0:
                    break
                member_atk = max(1, int(member.attack))
                member_power = 25
                per_hit = (((2 * member.level / 5 + 2) * member_power * (member_atk / max(1, dfn))) / 50) + 2
                if type_mul == 0:
                    hit_damage = 0
                else:
                    hit_damage = math.floor(max(1.0, per_hit * type_mul * random.uniform(0.85, 1.0)))
                applied = min(hit_damage, defender.current_hp)
                defender.current_hp = max(0, defender.current_hp - applied)
                total_damage += applied
                hit_count += 1

            if total_damage > 0:
                if defender is self.player_active:
                    self.player_took_damage_this_turn = True
                else:
                    self.wild_took_damage_this_turn = True
                if defender is self.player_active and self.player_bide_turns > 0:
                    self.player_bide_damage += total_damage
                if defender is self.wild and self.wild_bide_turns > 0:
                    self.wild_bide_damage += total_damage

            effect_text = ""
            if type_mul >= 2:
                effect_text = " Rất hiệu quả!"
            elif 0 < type_mul < 1:
                effect_text = " Không hiệu quả lắm..."
            elif type_mul == 0:
                effect_text = " Không có tác dụng!"

            text = (
                f"{attacker.name} dùng Beat Up gây {total_damage} sát thương lên {defender.name}."
                f" {defender.name}: {defender.current_hp}/{defender.max_hp} HP.{effect_text}"
            )
            if hit_count > 1:
                text += f"\nBeat Up trúng {hit_count} đòn từ các thành viên còn chiến đấu trong đội."
            if contact_burn_text:
                text += "\n" + contact_burn_text.strip()
            return text

        base_damage = (((2 * attacker.level / 5 + 2) * move_power * (atk / max(1, dfn))) / 50) + 2
        stab = 1.5 if move.move_type in attacker.types else 1.0
        type_mul = self.game_data.type_multiplier(move.move_type, defender.types)
        high_crit_moves = {
            "Aeroblast",
            "Air Cutter",
            "Aqua Cutter",
            "Attack Order",
            "Blaze Kick",
            "Crabhammer",
            "Cross Chop",
            "Drill Run",
            "Esper Wing",
            "Karate Chop",
            "Leaf Blade",
            "Night Slash",
            "Poison Tail",
            "Psycho Cut",
            "Razor Leaf",
            "Razor Wind",
            "Snipe Shot",
            "Spacial Rend",
            "Slash",
            "Stone Edge",
            "Shadow Claw",
            "Triple Arrows",
            "Ivy Cudgel",
            "10,000,000 Volt Thunderbolt",
        }
        crit_chance = 1 / 8 if move.name in high_crit_moves else 1 / 24
        if attacker is self.player_active and self.player_laser_focus:
            crit_chance = 1.0
            self.player_laser_focus = False
        if attacker is self.wild and self.wild_laser_focus:
            crit_chance = 1.0
            self.wild_laser_focus = False
        if move.name == "Frost Breath":
            crit_chance = 1.0
        if attacker is self.player_active and self.player_focus_energy:
            crit_chance = 1 / 2 if move.name in high_crit_moves else 1 / 8
        if attacker is self.wild and self.wild_focus_energy:
            crit_chance = 1 / 2 if move.name in high_crit_moves else 1 / 8
        if attacker is self.player_active and self.player_lansat_crit_boost:
            crit_chance = max(crit_chance, 1 / 2 if move.name in high_crit_moves else 1 / 8)
        if attacker is self.wild and self.wild_lansat_crit_boost:
            crit_chance = max(crit_chance, 1 / 2 if move.name in high_crit_moves else 1 / 8)
        attacker_crit_item = self._held_item_name(attacker)
        if attacker_crit_item in {"scope lens", "razor claw"}:
            crit_chance = max(crit_chance, 1 / 2 if move.name in high_crit_moves else 1 / 8)
        if attacker_crit_item == "lucky punch" and (attacker.name or "").strip().lower() == "chansey":
            crit_chance = max(crit_chance, 1 / 2 if move.name in high_crit_moves else 1 / 8)
        if attacker_crit_item in {"leek", "stick"}:
            attacker_name_norm = (attacker.name or "").strip().lower().replace("'", "").replace(" ", "")
            if attacker_name_norm in {"farfetchd", "sirfetchd"}:
                crit_chance = max(crit_chance, 1 / 2 if move.name in high_crit_moves else 1 / 8)
        if move.name == "Flower Trick":
            crit_chance = 1.0
        if move.name == "Storm Throw":
            crit_chance = 1.0
        if move.name == "Surging Strikes":
            crit_chance = 1.0
        if move.name == "Wicked Blow":
            crit_chance = 1.0
        if move.name == "Zippy Zap":
            crit_chance = 1.0
        cheer_turns = self.player_dragon_cheer_turns if attacker is self.player_active else self.wild_dragon_cheer_turns
        if cheer_turns > 0:
            if move.name in high_crit_moves:
                crit_chance = 1 / 2
            else:
                crit_chance = 1 / 8
        defender_lucky_chant = self.player_lucky_chant_turns if defender is self.player_active else self.wild_lucky_chant_turns
        if defender_lucky_chant > 0:
            crit_chance = 0.0
        weather_mul = 1.0
        terrain_mul = 1.0

        if move.move_type == "Fire":
            defender_tar_shot = self.player_tar_shot if defender is self.player_active else self.wild_tar_shot
            if defender_tar_shot:
                type_mul = type_mul * 2

        attacker_item_early = self._held_item_name(attacker)
        weather_blocked = (
            attacker_item_early == "utility umbrella"
            or self._held_item_name(defender) == "utility umbrella"
        )
        if not weather_blocked:
            if self.weather == "rain" and self.weather_turns > 0:
                if move.move_type == "Water":
                    weather_mul = 1.5
                elif move.move_type == "Fire":
                    weather_mul = 0.5
            elif self.weather == "harsh sunlight" and self.weather_turns > 0:
                if move.move_type == "Fire":
                    weather_mul = 1.5
                elif move.move_type == "Water":
                    weather_mul = 0.5

        if self.mud_sport_turns > 0 and move.move_type == "Electric":
            weather_mul *= 0.5
        if self.water_sport_turns > 0 and move.move_type == "Fire":
            weather_mul *= 0.5

        if self.terrain_turns > 0:
            if self.terrain == "electric terrain" and move.move_type == "Electric" and self._is_grounded(attacker):
                terrain_mul = 1.3
            elif self.terrain == "grassy terrain" and move.move_type == "Grass" and self._is_grounded(attacker):
                terrain_mul = 1.3
            elif self.terrain == "psychic terrain" and move.move_type == "Psychic" and self._is_grounded(attacker):
                terrain_mul = 1.3
            elif self.terrain == "misty terrain" and move.move_type == "Dragon" and self._is_grounded(defender):
                terrain_mul = 0.5

        if move.name == "Flying Press":
            type_mul = self.game_data.type_multiplier("Fighting", defender.types) * self.game_data.type_multiplier("Flying", defender.types)

        if move.name == "Freeze-Dry" and "Water" in defender.types:
            type_mul = type_mul * 4

        attacker_item = self._held_item_name(attacker)
        item_damage_mul = 1.0
        consumed_gem_name: str | None = None
        if move.category == "Physical" and attacker_item == "choice band":
            item_damage_mul *= 1.5
        if move.category == "Special" and attacker_item == "choice specs":
            item_damage_mul *= 1.5
        if move.category == "Physical" and attacker_item == "muscle band":
            item_damage_mul *= 1.1
        if move.category == "Special" and attacker_item == "wise glasses":
            item_damage_mul *= 1.1
        if attacker_item == "punching glove" and "punch" in move.name.lower():
            item_damage_mul *= 1.1
        if attacker_item == "life orb":
            item_damage_mul *= 1.3
        if attacker_item == "metronome":
            if attacker is self.player_active:
                if self.player_metronome_move == move.name:
                    self.player_metronome_chain = min(5, self.player_metronome_chain + 1)
                else:
                    self.player_metronome_move = move.name
                    self.player_metronome_chain = 1
                item_damage_mul *= 1.0 + 0.2 * max(0, self.player_metronome_chain - 1)
            else:
                if self.wild_metronome_move == move.name:
                    self.wild_metronome_chain = min(5, self.wild_metronome_chain + 1)
                else:
                    self.wild_metronome_move = move.name
                    self.wild_metronome_chain = 1
                item_damage_mul *= 1.0 + 0.2 * max(0, self.wild_metronome_chain - 1)
        else:
            if attacker is self.player_active:
                self.player_metronome_move = None
                self.player_metronome_chain = 0
            else:
                self.wild_metronome_move = None
                self.wild_metronome_chain = 0
        if attacker_item == "expert belt" and type_mul > 1.0:
            item_damage_mul *= 1.2
        attacker_name = (attacker.name or "").strip().lower()
        if attacker_item == "adamant orb" and attacker_name.startswith("dialga") and move.move_type in {"Dragon", "Steel"}:
            item_damage_mul *= 1.2
        if attacker_item in {"lustrous orb", "lustrous globe"} and attacker_name.startswith("palkia") and move.move_type in {"Dragon", "Water"}:
            item_damage_mul *= 1.2
        if attacker_item in {"griseous orb", "griseous core"} and attacker_name.startswith("giratina") and move.move_type in {"Dragon", "Ghost"}:
            item_damage_mul *= 1.2
        if attacker_item == "soul dew" and (attacker_name.startswith("latios") or attacker_name.startswith("latias")) and move.move_type in {"Dragon", "Psychic"}:
            item_damage_mul *= 1.2
        gem_boost_items: dict[str, str] = {
            "normal gem": "Normal",
            "fire gem": "Fire",
            "water gem": "Water",
            "electric gem": "Electric",
            "grass gem": "Grass",
            "ice gem": "Ice",
            "fighting gem": "Fighting",
            "poison gem": "Poison",
            "ground gem": "Ground",
            "flying gem": "Flying",
            "psychic gem": "Psychic",
            "bug gem": "Bug",
            "rock gem": "Rock",
            "ghost gem": "Ghost",
            "dragon gem": "Dragon",
            "dark gem": "Dark",
            "steel gem": "Steel",
            "fairy gem": "Fairy",
        }
        gem_type = gem_boost_items.get(attacker_item)
        if gem_type and move.move_type == gem_type:
            item_damage_mul *= 1.3
            consumed_gem_name = attacker_item

        type_boost_items: dict[str, str] = {
            "silk scarf": "Normal",
            "pink bow": "Normal",
            "polkadot bow": "Normal",
            "charcoal": "Fire",
            "mystic water": "Water",
            "sea incense": "Water",
            "wave incense": "Water",
            "magnet": "Electric",
            "miracle seed": "Grass",
            "rose incense": "Grass",
            "never-melt ice": "Ice",
            "never melt ice": "Ice",
            "black belt": "Fighting",
            "poison barb": "Poison",
            "soft sand": "Ground",
            "sharp beak": "Flying",
            "twisted spoon": "Psychic",
            "odd incense": "Psychic",
            "silver powder": "Bug",
            "silverpowder": "Bug",
            "hard stone": "Rock",
            "rock incense": "Rock",
            "spell tag": "Ghost",
            "dragon fang": "Dragon",
            "black glasses": "Dark",
            "metal coat": "Steel",
            "fairy feather": "Fairy",
            "pixie plate": "Fairy",
            "fist plate": "Fighting",
            "toxic plate": "Poison",
            "earth plate": "Ground",
            "sky plate": "Flying",
            "mind plate": "Psychic",
            "insect plate": "Bug",
            "stone plate": "Rock",
            "spooky plate": "Ghost",
            "draco plate": "Dragon",
            "dread plate": "Dark",
            "iron plate": "Steel",
            "flame plate": "Fire",
            "splash plate": "Water",
            "zap plate": "Electric",
            "meadow plate": "Grass",
            "icicle plate": "Ice",
        }
        boost_type = type_boost_items.get(attacker_item)
        if boost_type and move.move_type == boost_type:
            item_damage_mul *= 1.2

        defender_item = self._held_item_name(defender)
        if type_mul == 0 and defender_item == "ring target":
            type_mul = 1
        resist_berries: dict[str, set[str]] = {
            "occa berry": {"Fire"},
            "passho berry": {"Water"},
            "wacan berry": {"Electric"},
            "rindo berry": {"Grass"},
            "yache berry": {"Ice"},
            "chople berry": {"Fighting"},
            "kebia berry": {"Poison"},
            "shuca berry": {"Ground"},
            "coba berry": {"Flying"},
            "payapa berry": {"Psychic"},
            "tanga berry": {"Bug"},
            "charti berry": {"Rock"},
            "kasib berry": {"Ghost"},
            "haban berry": {"Dragon"},
            "colbur berry": {"Dark"},
            "babiri berry": {"Steel"},
            "chilan berry": {"Normal"},
        }
        consumed_resist_berry = False
        if type_mul > 1.0 and defender_item in resist_berries and move.move_type in resist_berries[defender_item]:
            item_damage_mul *= 0.5
            defender.hold_item = None
            defender.berry_consumed = True
            consumed_resist_berry = True

        defender_magnet_rise = self.player_magnet_rise_turns if defender is self.player_active else self.wild_magnet_rise_turns
        if move.move_type == "Ground" and defender_magnet_rise > 0:
            type_mul = 0

        if move.name == "Thousand Arrows":
            defender_has_flying = "Flying" in defender.types
            if type_mul == 0 and (defender_has_flying or defender_magnet_rise > 0):
                type_mul = 1

        defender_identified = self.player_identified if defender is self.player_active else self.wild_identified
        if defender_identified and move.move_type in {"Normal", "Fighting"} and "Ghost" in defender.types and type_mul == 0:
            type_mul = 1
        defender_miracle_eye = self.player_miracle_eye if defender is self.player_active else self.wild_miracle_eye
        if defender_miracle_eye and move.move_type == "Psychic" and "Dark" in defender.types and type_mul == 0:
            type_mul = 1

        if move.name == "Fissure":
            type_mul = self.game_data.type_multiplier(move.move_type, defender.types)
            if type_mul == 0:
                return f"{attacker.name} dùng Fissure nhưng không có tác dụng lên {defender.name}!"
            if attacker.level < defender.level:
                return f"{attacker.name} dùng Fissure nhưng thất bại vì cấp thấp hơn mục tiêu."
            pre_hp = defender.current_hp
            defender.current_hp = 0
            if defender is self.player_active:
                self.player_took_damage_this_turn = True
                self.player_last_damage_taken = pre_hp
            else:
                self.wild_took_damage_this_turn = True
                self.wild_last_damage_taken = pre_hp
            return f"{attacker.name} dùng Fissure! Đòn One-Hit-KO khiến {defender.name} gục ngay lập tức!"

        if move.name == "Guillotine":
            type_mul = self.game_data.type_multiplier(move.move_type, defender.types)
            if type_mul == 0:
                return f"{attacker.name} dùng Guillotine nhưng không có tác dụng lên {defender.name}!"
            if attacker.level < defender.level:
                return f"{attacker.name} dùng Guillotine nhưng thất bại vì cấp thấp hơn mục tiêu."
            pre_hp = defender.current_hp
            defender.current_hp = 0
            if defender is self.player_active:
                self.player_took_damage_this_turn = True
                self.player_last_damage_taken = pre_hp
            else:
                self.wild_took_damage_this_turn = True
                self.wild_last_damage_taken = pre_hp
            return f"{attacker.name} dùng Guillotine! Đòn One-Hit-KO khiến {defender.name} gục ngay lập tức!"

        if move.name == "Horn Drill":
            type_mul = self.game_data.type_multiplier(move.move_type, defender.types)
            if type_mul == 0:
                return f"{attacker.name} dùng Horn Drill nhưng không có tác dụng lên {defender.name}!"
            if attacker.level < defender.level:
                return f"{attacker.name} dùng Horn Drill nhưng thất bại vì cấp thấp hơn mục tiêu."
            pre_hp = defender.current_hp
            defender.current_hp = 0
            if defender is self.player_active:
                self.player_took_damage_this_turn = True
                self.player_last_damage_taken = pre_hp
            else:
                self.wild_took_damage_this_turn = True
                self.wild_last_damage_taken = pre_hp
            return f"{attacker.name} dùng Horn Drill! Đòn One-Hit-KO khiến {defender.name} gục ngay lập tức!"

        if move.name == "Sheer Cold":
            type_mul = self.game_data.type_multiplier(move.move_type, defender.types)
            if type_mul == 0:
                return f"{attacker.name} dùng Sheer Cold nhưng không có tác dụng lên {defender.name}!"
            if "Ice" in defender.types:
                return f"{attacker.name} dùng Sheer Cold nhưng {defender.name} miễn nhiễm vì hệ Ice!"
            if attacker.level < defender.level:
                return f"{attacker.name} dùng Sheer Cold nhưng thất bại vì cấp thấp hơn mục tiêu."
            pre_hp = defender.current_hp
            defender.current_hp = 0
            if defender is self.player_active:
                self.player_took_damage_this_turn = True
                self.player_last_damage_taken = pre_hp
            else:
                self.wild_took_damage_this_turn = True
                self.wild_last_damage_taken = pre_hp
            return f"{attacker.name} dùng Sheer Cold! Đòn One-Hit-KO khiến {defender.name} gục ngay lập tức!"

        if move.name == "Guardian of Alola":
            type_mul = self.game_data.type_multiplier(move.move_type, defender.types)
            if type_mul == 0:
                return f"{attacker.name} dùng Guardian of Alola nhưng không có tác dụng lên {defender.name}!"
            dealt = min(defender.current_hp, max(1, int(defender.current_hp * 0.75)))
            defender.current_hp = max(0, defender.current_hp - dealt)
            if defender is self.player_active:
                self.player_took_damage_this_turn = True
                self.player_last_damage_taken = dealt
            else:
                self.wild_took_damage_this_turn = True
                self.wild_last_damage_taken = dealt
            return (
                f"{attacker.name} dùng Guardian of Alola gây {dealt} sát thương lên {defender.name}."
                f" {defender.name}: {defender.current_hp}/{defender.max_hp} HP."
            )

        if move.name == "Nature's Madness":
            type_mul = self.game_data.type_multiplier(move.move_type, defender.types)
            if type_mul == 0:
                return f"{attacker.name} dùng Nature's Madness nhưng không có tác dụng lên {defender.name}!"
            dealt = min(defender.current_hp, max(1, defender.current_hp // 2))
            defender.current_hp = max(0, defender.current_hp - dealt)
            if defender is self.player_active:
                self.player_took_damage_this_turn = True
                self.player_last_damage_taken = dealt
            else:
                self.wild_took_damage_this_turn = True
                self.wild_last_damage_taken = dealt
            return (
                f"{attacker.name} dùng Nature's Madness gây {dealt} sát thương lên {defender.name}."
                f" {defender.name}: {defender.current_hp}/{defender.max_hp} HP."
            )

        if move.name == "Ruination":
            type_mul = self.game_data.type_multiplier(move.move_type, defender.types)
            if type_mul == 0:
                return f"{attacker.name} dùng Ruination nhưng không có tác dụng lên {defender.name}!"
            dealt = min(defender.current_hp, max(1, defender.current_hp // 2))
            defender.current_hp = max(0, defender.current_hp - dealt)
            if defender is self.player_active:
                self.player_took_damage_this_turn = True
                self.player_last_damage_taken = dealt
            else:
                self.wild_took_damage_this_turn = True
                self.wild_last_damage_taken = dealt
            return (
                f"{attacker.name} dùng Ruination gây {dealt} sát thương lên {defender.name}."
                f" {defender.name}: {defender.current_hp}/{defender.max_hp} HP."
            )

        if move.name == "Night Shade":
            type_mul = self.game_data.type_multiplier(move.move_type, defender.types)
            if type_mul == 0:
                return f"{attacker.name} dùng Night Shade nhưng không có tác dụng lên {defender.name}!"
            dealt = min(defender.current_hp, max(1, attacker.level))
            defender.current_hp = max(0, defender.current_hp - dealt)
            if defender is self.player_active:
                self.player_took_damage_this_turn = True
                self.player_last_damage_taken = dealt
            else:
                self.wild_took_damage_this_turn = True
                self.wild_last_damage_taken = dealt
            return (
                f"{attacker.name} dùng Night Shade gây {dealt} sát thương lên {defender.name}."
                f" {defender.name}: {defender.current_hp}/{defender.max_hp} HP."
            )

        if move.name == "Seismic Toss":
            type_mul = self.game_data.type_multiplier(move.move_type, defender.types)
            if type_mul == 0:
                return f"{attacker.name} dùng Seismic Toss nhưng không có tác dụng lên {defender.name}!"
            dealt = min(defender.current_hp, max(1, attacker.level))
            defender.current_hp = max(0, defender.current_hp - dealt)
            if defender is self.player_active:
                self.player_took_damage_this_turn = True
                self.player_last_damage_taken = dealt
            else:
                self.wild_took_damage_this_turn = True
                self.wild_last_damage_taken = dealt
            return (
                f"{attacker.name} dùng Seismic Toss gây {dealt} sát thương lên {defender.name}."
                f" {defender.name}: {defender.current_hp}/{defender.max_hp} HP."
            )

        if move.name == "Psywave":
            type_mul = self.game_data.type_multiplier(move.move_type, defender.types)
            if type_mul == 0:
                return f"{attacker.name} dùng Psywave nhưng không có tác dụng lên {defender.name}!"
            low = max(1, attacker.level // 2)
            high = max(low, int(attacker.level * 1.5))
            dealt = min(defender.current_hp, random.randint(low, high))
            defender.current_hp = max(0, defender.current_hp - dealt)
            if defender is self.player_active:
                self.player_took_damage_this_turn = True
                self.player_last_damage_taken = dealt
            else:
                self.wild_took_damage_this_turn = True
                self.wild_last_damage_taken = dealt
            return (
                f"{attacker.name} dùng Psywave gây {dealt} sát thương lên {defender.name}."
                f" {defender.name}: {defender.current_hp}/{defender.max_hp} HP."
            )

        if move.name == "Super Fang":
            type_mul = self.game_data.type_multiplier(move.move_type, defender.types)
            if type_mul == 0:
                return f"{attacker.name} dùng Super Fang nhưng không có tác dụng lên {defender.name}!"
            dealt = min(defender.current_hp, max(1, defender.current_hp // 2))
            defender.current_hp = max(0, defender.current_hp - dealt)
            if defender is self.player_active:
                self.player_took_damage_this_turn = True
                self.player_last_damage_taken = dealt
            else:
                self.wild_took_damage_this_turn = True
                self.wild_last_damage_taken = dealt
            return (
                f"{attacker.name} dùng Super Fang gây {dealt} sát thương lên {defender.name}."
                f" {defender.name}: {defender.current_hp}/{defender.max_hp} HP."
            )

        if move.name == "Hydro Vortex":
            type_mul = self.game_data.type_multiplier(move.move_type, defender.types)
            base = (((2 * attacker.level / 5 + 2) * 180 * (atk / max(1, dfn))) / 50) + 2
            stab = 1.5 if move.move_type in attacker.types else 1.0
            dealt = 0 if type_mul == 0 else min(defender.current_hp, math.floor(max(1.0, base * stab * type_mul * random.uniform(0.85, 1.0))))
            defender.current_hp = max(0, defender.current_hp - dealt)
            if dealt > 0:
                if defender is self.player_active:
                    self.player_took_damage_this_turn = True
                    self.player_last_damage_taken = dealt
                else:
                    self.wild_took_damage_this_turn = True
                    self.wild_last_damage_taken = dealt
            return (
                f"{attacker.name} dùng Hydro Vortex gây {dealt} sát thương lên {defender.name}."
                f" {defender.name}: {defender.current_hp}/{defender.max_hp} HP."
            )

        if move.name == "Final Gambit":
            if type_mul == 0:
                inflicted = 0
            else:
                inflicted = min(attacker.current_hp, defender.current_hp)
                defender.current_hp = max(0, defender.current_hp - inflicted)
            attacker.current_hp = 0
            effect_text = ""
            if type_mul >= 2:
                effect_text = " Rất hiệu quả!"
            elif 0 < type_mul < 1:
                effect_text = " Không hiệu quả lắm..."
            elif type_mul == 0:
                effect_text = " Không có tác dụng!"
            if inflicted > 0:
                if defender is self.player_active:
                    self.player_took_damage_this_turn = True
                    self.player_last_damage_taken = inflicted
                else:
                    self.wild_took_damage_this_turn = True
                    self.wild_last_damage_taken = inflicted
            return (
                f"{attacker.name} dùng Final Gambit gây {inflicted} sát thương lên {defender.name}."
                f" {defender.name}: {defender.current_hp}/{defender.max_hp} HP.{effect_text}\n"
                f"{attacker.name} đã gục sau Final Gambit!"
            )

        def _single_hit_damage() -> tuple[int, bool]:
            if type_mul == 0:
                return 0, False
            crit_mul_local = 1.5 if random.random() < crit_chance else 1.0
            random_mul_local = random.uniform(0.85, 1.0)
            hit_damage = math.floor(
                max(
                    1.0,
                    base_damage * stab * type_mul * random_mul_local * ability_multiplier * weather_mul * terrain_mul * item_damage_mul * crit_mul_local,
                )
            )

            if move.category == "Physical":
                if defender is self.player_active and self.player_reflect_turns > 0:
                    hit_damage = max(1, hit_damage // 2)
                if defender is self.wild and self.wild_reflect_turns > 0:
                    hit_damage = max(1, hit_damage // 2)
            elif move.category == "Special":
                if defender is self.player_active and self.player_light_screen_turns > 0:
                    hit_damage = max(1, hit_damage // 2)
                if defender is self.wild and self.wild_light_screen_turns > 0:
                    hit_damage = max(1, hit_damage // 2)
            return hit_damage, crit_mul_local > 1.0

        hit_count = 1
        if move.name in {"Arm Thrust", "Barrage"}:
            hit_count = self._multi_hit_roll(attacker)
        if move.name in {"Bone Rush", "Bullet Seed"}:
            hit_count = self._multi_hit_roll(attacker)
        if move.name == "Comet Punch":
            hit_count = self._multi_hit_roll(attacker)
        if move.name in {"Double Hit", "Double Kick", "Dragon Darts"}:
            hit_count = 2
        if move.name in {"Dual Chop", "Dual Wingbeat"}:
            hit_count = 2
        if move.name == "Double Iron Bash":
            hit_count = 2
        if move.name == "Double Slap":
            hit_count = self._multi_hit_roll(attacker)
        if move.name == "Bonemerang":
            hit_count = 2
        if move.name in {"Fury Attack", "Fury Swipes"}:
            hit_count = self._multi_hit_roll(attacker)
        if move.name == "Pin Missile":
            hit_count = self._multi_hit_roll(attacker)
        if move.name == "Spike Cannon":
            hit_count = self._multi_hit_roll(attacker)
        if move.name == "Rock Blast":
            hit_count = self._multi_hit_roll(attacker)
        if move.name == "Gear Grind":
            hit_count = 2
        if move.name == "Icicle Spear":
            hit_count = self._multi_hit_roll(attacker)
        if move.name == "Population Bomb":
            hit_count = random.randint(1, 10)
        if move.name == "Scale Shot":
            hit_count = self._multi_hit_roll(attacker)
        if move.name == "Surging Strikes":
            hit_count = 3
        if move.name == "Tail Slap":
            hit_count = self._multi_hit_roll(attacker)
        if move.name == "Tachyon Cutter":
            hit_count = 2
        if move.name == "Twin Beam":
            hit_count = 2
        if move.name == "Twineedle":
            hit_count = 2
        if move.name == "Triple Dive":
            hit_count = 3
        if move.name == "Water Shuriken":
            hit_count = self._multi_hit_roll(attacker)

        total_damage = 0
        crit_happened = False
        if move.name in {"Triple Axel", "Triple Kick"}:
            for mult in (1, 2, 3):
                if defender.current_hp <= 0:
                    break
                if type_mul == 0:
                    break
                crit_mul_local = 1.5 if random.random() < crit_chance else 1.0
                random_mul_local = random.uniform(0.85, 1.0)
                scaled_base = base_damage * mult
                hit_damage = math.floor(
                    max(
                        1.0,
                        scaled_base * stab * type_mul * random_mul_local * ability_multiplier * weather_mul * terrain_mul * item_damage_mul * crit_mul_local,
                    )
                )
                if move.category == "Physical":
                    if defender is self.player_active and self.player_reflect_turns > 0:
                        hit_damage = max(1, hit_damage // 2)
                    if defender is self.wild and self.wild_reflect_turns > 0:
                        hit_damage = max(1, hit_damage // 2)
                elif move.category == "Special":
                    if defender is self.player_active and self.player_light_screen_turns > 0:
                        hit_damage = max(1, hit_damage // 2)
                    if defender is self.wild and self.wild_light_screen_turns > 0:
                        hit_damage = max(1, hit_damage // 2)
                applied = min(hit_damage, defender.current_hp)
                defender.current_hp = max(0, defender.current_hp - applied)
                total_damage += applied
                crit_happened = crit_happened or (crit_mul_local > 1.0)
        else:
            for _ in range(hit_count):
                if defender.current_hp <= 0:
                    break
                hit_damage, is_crit = _single_hit_damage()
                applied = min(hit_damage, defender.current_hp)
                defender.current_hp = max(0, defender.current_hp - applied)
                total_damage += applied
                crit_happened = crit_happened or is_crit

        damage = max(0, total_damage)
        endure_triggered = False
        focus_sash_triggered = False
        focus_band_triggered = False
        sturdy_triggered = False
        defender_item = self._held_item_name(defender)
        if damage > 0 and defender.current_hp <= 0 and defender_item == "focus sash":
            hp_before_hit = defender.current_hp + damage
            if hp_before_hit == defender.max_hp and hp_before_hit > 1:
                defender.current_hp = 1
                damage = hp_before_hit - 1
                total_damage = damage
                defender.hold_item = None
                focus_sash_triggered = True

        if damage > 0 and defender.current_hp <= 0 and defender_item == "focus band":
            hp_before_hit = defender.current_hp + damage
            if hp_before_hit > 1 and random.random() < 0.10:
                defender.current_hp = 1
                damage = hp_before_hit - 1
                total_damage = damage
                focus_band_triggered = True

        defender_endure_active = (
            (defender is self.player_active and self.player_endure_active)
            or (defender is self.wild and self.wild_endure_active)
        )
        if damage > 0 and defender_endure_active and defender.current_hp <= 0:
            hp_before_hit = defender.current_hp + damage
            if hp_before_hit > 1:
                defender.current_hp = 1
                damage = hp_before_hit - 1
                total_damage = damage
                endure_triggered = True

        if damage > 0 and defender.current_hp <= 0 and defender.ability == "Sturdy":
            hp_before_hit = defender.current_hp + damage
            if hp_before_hit == defender.max_hp and hp_before_hit > 1:
                defender.current_hp = 1
                damage = hp_before_hit - 1
                total_damage = damage
                sturdy_triggered = True

        if move.name == "Endeavor":
            hp_before_hit = defender.current_hp + damage
            if type_mul != 0 and hp_before_hit > attacker.current_hp:
                defender.current_hp = max(1, attacker.current_hp)
                damage = hp_before_hit - defender.current_hp
                total_damage = damage
            else:
                defender.current_hp = hp_before_hit
                damage = 0
                total_damage = 0

        if move.name == "False Swipe" and damage > 0 and defender.current_hp <= 0 and type_mul != 0:
            defender.current_hp = 1
            damage = max(0, damage - 1)
            total_damage = damage

        if damage > 0:
            if defender is self.player_active:
                self.player_took_damage_this_turn = True
                self.player_last_damage_taken = damage
                if move.category == "Physical":
                    self.player_last_physical_damage_taken = damage
                self.player_hit_count += 1
            else:
                self.wild_took_damage_this_turn = True
                self.wild_last_damage_taken = damage
                if move.category == "Physical":
                    self.wild_last_physical_damage_taken = damage
                self.wild_hit_count += 1
            if defender is self.player_active and self.player_bide_turns > 0:
                self.player_bide_damage += damage
            if defender is self.wild and self.wild_bide_turns > 0:
                self.wild_bide_damage += damage

        gem_consumed = False
        if damage > 0 and consumed_gem_name and self._held_item_name(attacker) == consumed_gem_name:
            attacker.hold_item = None
            gem_consumed = True

        if damage > 0 and defender.hold_item and self._held_item_name(defender) == "air balloon":
            defender.hold_item = None

        effect_text = ""
        if type_mul >= 2:
            effect_text = " Rất hiệu quả!"
        elif 0 < type_mul < 1:
            effect_text = " Không hiệu quả lắm..."
        elif type_mul == 0:
            effect_text = " Không có tác dụng!"

        extra_parts: list[str] = []
        if damage > 0 and defender.current_hp > 0:
            if defender is self.player_active and self.player_rage_active:
                changed, stage_text = self._change_stat_stage(defender, "attack", +1)
                if changed:
                    extra_parts.append(f"Rage của {defender.name} bùng lên! Attack tăng {stage_text}.")
            if defender is self.wild and self.wild_rage_active:
                changed, stage_text = self._change_stat_stage(defender, "attack", +1)
                if changed:
                    extra_parts.append(f"Rage của {defender.name} bùng lên! Attack tăng {stage_text}.")
        if endure_triggered:
            extra_parts.append(f"{defender.name} chịu đựng nhờ Endure và còn lại 1 HP!")
        if focus_sash_triggered:
            extra_parts.append(f"{defender.name} kích hoạt Focus Sash và trụ lại với 1 HP!")
        if focus_band_triggered:
            extra_parts.append(f"{defender.name} may mắn nhờ Focus Band và trụ lại với 1 HP!")
        if sturdy_triggered:
            extra_parts.append(f"{defender.name} trụ lại nhờ Sturdy và còn 1 HP!")
        if hit_count > 1:
            extra_parts.append(f"Trúng {hit_count} lần!")
        if crit_happened:
            extra_parts.append("Đòn chí mạng!")
        if consumed_resist_berry:
            extra_parts.append(f"{defender.name} ăn Berry kháng hệ và giảm sát thương đòn siêu hiệu quả!")
        if gem_consumed and consumed_gem_name:
            extra_parts.append(f"{attacker.name} kích hoạt {consumed_gem_name.title()} để cường hóa đòn đánh!")
        if damage > 0 and type_mul > 1 and defender_item == "weakness policy":
            atk_up, atk_text = self._change_stat_stage(defender, "attack", +2)
            spa_up, spa_text = self._change_stat_stage(defender, "sp_attack", +2)
            defender.hold_item = None
            if atk_up or spa_up:
                detail = []
                if atk_up:
                    detail.append(f"Attack {atk_text}")
                if spa_up:
                    detail.append(f"Sp. Attack {spa_text}")
                extra_parts.append(f"Weakness Policy kích hoạt! {defender.name} tăng {' và '.join(detail)}.")
        if damage > 0 and defender.hold_item is None and defender_item == "air balloon":
            extra_parts.append(f"Air Balloon của {defender.name} đã vỡ!")

        if damage > 0 and move.makes_contact and defender.current_hp > 0 and attacker.current_hp > 0:
            contact_suppressed = self._contact_effects_suppressed(attacker) or (
                self._held_item_name(attacker) == "punching glove" and "punch" in move.name.lower()
            )
            if not contact_suppressed and self._held_item_name(defender) == "rocky helmet" and attacker.ability != "Magic Guard":
                recoil = max(1, attacker.max_hp // 6)
                attacker.current_hp = max(0, attacker.current_hp - recoil)
                extra_parts.append(f"{attacker.name} bị Rocky Helmet gây {recoil} sát thương!")

            if not contact_suppressed and self._held_item_name(defender) == "sticky barb" and not attacker.hold_item:
                attacker.hold_item = defender.hold_item
                defender.hold_item = None
                extra_parts.append(f"Sticky Barb dính sang {attacker.name} do đòn tiếp xúc!")

            if not contact_suppressed and attacker.current_hp > 0:
                defender_ability = (defender.ability or "").strip()
                if defender_ability in {"Rough Skin", "Iron Barbs"} and attacker.ability != "Magic Guard":
                    recoil = max(1, attacker.max_hp // 8)
                    attacker.current_hp = max(0, attacker.current_hp - recoil)
                    extra_parts.append(f"{attacker.name} bị {defender_ability} gây {recoil} sát thương!")
                elif defender_ability == "Static" and attacker.status is None and "Electric" not in attacker.types and random.random() < 0.30:
                    attacker.status = "par"
                    attacker.status_counter = 0
                    extra_parts.append(f"{attacker.name} bị tê liệt do Static!")
                elif defender_ability == "Flame Body" and attacker.status is None and "Fire" not in attacker.types and random.random() < 0.30:
                    attacker.status = "brn"
                    attacker.status_counter = 0
                    extra_parts.append(f"{attacker.name} bị Burn do Flame Body!")
                elif (
                    defender_ability == "Poison Point"
                    and attacker.status is None
                    and "Poison" not in attacker.types
                    and "Steel" not in attacker.types
                    and attacker.ability != "Immunity"
                    and random.random() < 0.30
                ):
                    attacker.status = "psn"
                    attacker.status_counter = 0
                    extra_parts.append(f"{attacker.name} bị Poison do Poison Point!")

                if defender_ability == "Effect Spore" and attacker.status is None and random.random() < 0.30:
                    powder_blocked = (
                        "Grass" in attacker.types
                        or (attacker.ability or "").strip() == "Overcoat"
                        or self._held_item_name(attacker) == "safety goggles"
                    )
                    if not powder_blocked:
                        proc = random.choice(["slp", "par", "psn"])
                        if proc == "slp":
                            attacker.status = "slp"
                            attacker.status_counter = random.randint(1, 3)
                            extra_parts.append(f"{attacker.name} bị ngủ do Effect Spore!")
                        elif proc == "par" and "Electric" not in attacker.types:
                            attacker.status = "par"
                            attacker.status_counter = 0
                            extra_parts.append(f"{attacker.name} bị tê liệt do Effect Spore!")
                        elif (
                            proc == "psn"
                            and "Poison" not in attacker.types
                            and "Steel" not in attacker.types
                            and attacker.ability != "Immunity"
                        ):
                            attacker.status = "psn"
                            attacker.status_counter = 0
                            extra_parts.append(f"{attacker.name} bị Poison do Effect Spore!")

                if defender_ability == "Cute Charm" and random.random() < 0.30:
                    if not self._is_infatuated(attacker):
                        knot_text = self._set_infatuated(attacker, True, source=defender)
                        extra_parts.append(f"{attacker.name} bị Cute Charm làm mê mẩn!")
                        if knot_text:
                            extra_parts.append(knot_text)

                if defender_ability == "Mummy" and attacker.ability and attacker.ability != "Mummy":
                    old_ability = attacker.ability
                    attacker.ability = "Mummy"
                    extra_parts.append(f"{attacker.name} bị Mummy biến Ability từ {old_ability} thành Mummy!")

                if defender_ability == "Wandering Spirit" and attacker.ability and attacker.ability != "Wandering Spirit":
                    attacker_ability_before = attacker.ability
                    defender_ability_before = defender.ability
                    attacker.ability = defender_ability_before
                    defender.ability = attacker_ability_before
                    extra_parts.append(
                        f"Wandering Spirit hoán đổi Ability! {attacker.name}: {attacker_ability_before} -> {attacker.ability}, "
                        f"{defender.name}: {defender_ability_before} -> {defender.ability}."
                    )

        defender_blocks_additional = self._blocks_additional_effects(defender)

        if damage > 0 and defender.current_hp > 0 and attacker.current_hp > 0:
            attacker_item_now = self._held_item_name(attacker)
            if attacker_item_now in {"king's rock", "razor fang"} and not defender_blocks_additional and random.random() < 0.10:
                if defender is self.player_active:
                    self.player_flinched = True
                else:
                    self.wild_flinched = True
                extra_parts.append(f"{defender.name} bị flinch do {attacker_item_now.title()}!")

        if damage > 0 and attacker.current_hp > 0 and self._held_item_name(attacker) == "life orb" and attacker.ability != "Magic Guard":
            orb_recoil = max(1, attacker.max_hp // 10)
            attacker.current_hp = max(0, attacker.current_hp - orb_recoil)
            extra_parts.append(f"{attacker.name} mất {orb_recoil} HP do Life Orb ({attacker.current_hp}/{attacker.max_hp}).")

        if damage > 0 and attacker.current_hp > 0 and self._held_item_name(attacker) == "shell bell":
            shell_heal = min(max(1, damage // 8), attacker.max_hp - attacker.current_hp)
            if shell_heal > 0:
                attacker.current_hp += shell_heal
                extra_parts.append(f"{attacker.name} hồi {shell_heal} HP nhờ Shell Bell ({attacker.current_hp}/{attacker.max_hp}).")

        extra_parts.extend(self._try_trigger_berry(defender))
        extra_parts.extend(self._try_trigger_berry(attacker))

        if move.name == "Absorb" and damage > 0 and attacker.current_hp > 0:
            heal = self._drain_heal_amount(attacker, max(1, damage // 2))
            if heal > 0:
                attacker.current_hp += heal
                extra_parts.append(f"{attacker.name} hấp thụ và hồi {heal} HP ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Acid" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -1)
            if changed:
                extra_parts.append(f"Sp. Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Acid Spray" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -2)
            if changed:
                extra_parts.append(f"Sp. Defense của {defender.name} giảm mạnh {stage_text}.")

        if move.name == "Apple Acid" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -1)
            if changed:
                extra_parts.append(f"Sp. Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Ancient Power" and attacker.current_hp > 0 and random.random() < 0.10:
            boosted: list[str] = []
            for stat_key, label in [
                ("attack", "Attack"),
                ("defense", "Defense"),
                ("sp_attack", "Sp. Attack"),
                ("sp_defense", "Sp. Defense"),
                ("speed", "Speed"),
            ]:
                changed, _ = self._change_stat_stage(attacker, stat_key, +1)
                if changed:
                    boosted.append(label)
            if boosted:
                extra_parts.append(f"Ancient Power kích hoạt! {attacker.name} tăng: {', '.join(boosted)}.")

        if move.name == "Air Slash" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Astonish" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị giật mình và flinch!")

        if move.name == "Bite" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Bone Club" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Aqua Step" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "speed", +1)
            if changed:
                extra_parts.append(f"{attacker.name} tăng Speed {stage_text}.")

        if move.name == "Armor Cannon" and attacker.current_hp > 0:
            changed_def, def_text = self._change_stat_stage(attacker, "defense", -1)
            changed_spd, spd_text = self._change_stat_stage(attacker, "sp_defense", -1)
            if changed_def:
                extra_parts.append(f"{attacker.name} giảm Defense {def_text}.")
            if changed_spd:
                extra_parts.append(f"{attacker.name} giảm Sp. Defense {spd_text}.")

        if move.name == "Aurora Beam" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            changed, stage_text = self._change_stat_stage(defender, "attack", -1)
            if changed:
                extra_parts.append(f"Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Axe Kick" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            if defender.confusion_turns <= 0:
                defender.confusion_turns = random.randint(2, 5)
                extra_parts.append(f"{defender.name} bị Confusion!")

        if move.name == "Baddy Bad" and attacker.current_hp > 0:
            if attacker is self.player_active:
                self.player_reflect_turns = max(self.player_reflect_turns, 5)
            else:
                self.wild_reflect_turns = max(self.wild_reflect_turns, 5)
            extra_parts.append(f"Baddy Bad dựng lá chắn vật lý cho phe của {attacker.name}.")

        if move.name == "Bind" and defender.current_hp > 0 and not defender_blocks_additional:
            turns = random.randint(4, 5)
            applied_turns = self._apply_binding_effect(attacker, defender, turns)
            extra_parts.append(f"{defender.name} bị Bind trói trong {applied_turns} lượt!")

        if move.name == "Bitter Blade" and damage > 0 and attacker.current_hp > 0:
            heal = self._drain_heal_amount(attacker, max(1, damage // 2))
            if heal > 0:
                attacker.current_hp += heal
                extra_parts.append(f"{attacker.name} hồi {heal} HP nhờ Bitter Blade ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Bitter Malice" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "attack", -1)
            if changed:
                extra_parts.append(f"Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Blaze Kick" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Blazing Torque" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Bleakwind Storm" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            changed, stage_text = self._change_stat_stage(defender, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {defender.name} giảm {stage_text}.")

        if move.name == "Blizzard" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            defender.status = "slp"
            defender.status_counter = 1
            extra_parts.append(f"{defender.name} bị đóng băng tạm mô phỏng bằng Sleep 1 lượt.")

        if move.name == "Blue Flare" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.20:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Bolt Strike" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.20:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Body Slam" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Buzzy Buzz" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Bounce" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")
            if attacker is self.player_active:
                self.player_bounce_charging = False
            else:
                self.wild_bounce_charging = False

        if move.name == "Brave Bird" and damage > 0 and attacker.current_hp > 0:
            recoil = max(1, damage // 3)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} chịu phản lực {recoil} HP ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Bouncy Bubble" and damage > 0 and attacker.current_hp > 0:
            heal = self._drain_heal_amount(attacker, max(1, damage // 2))
            if heal > 0:
                attacker.current_hp += heal
                extra_parts.append(f"{attacker.name} hồi {heal} HP nhờ Bouncy Bubble ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name in {"Bubble", "Bubble Beam"} and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            changed, stage_text = self._change_stat_stage(defender, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {defender.name} giảm {stage_text}.")

        if move.name == "Bulldoze" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {defender.name} giảm {stage_text}.")

        if move.name == "Breaking Swipe" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "attack", -1)
            if changed:
                extra_parts.append(f"Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Brick Break" and defender.current_hp > 0:
            if defender is self.player_active:
                cleared = []
                if self.player_reflect_turns > 0:
                    self.player_reflect_turns = 0
                    cleared.append("Reflect")
                if self.player_light_screen_turns > 0:
                    self.player_light_screen_turns = 0
                    cleared.append("Light Screen")
            else:
                cleared = []
                if self.wild_reflect_turns > 0:
                    self.wild_reflect_turns = 0
                    cleared.append("Reflect")
                if self.wild_light_screen_turns > 0:
                    self.wild_light_screen_turns = 0
                    cleared.append("Light Screen")
            if cleared:
                extra_parts.append(f"Brick Break phá vỡ {', '.join(cleared)} của phe {defender.name}.")

        if move.name == "Bug Bite" and defender.current_hp > 0:
            stolen_item = (defender.hold_item or "").strip()
            if stolen_item and "berry" in stolen_item.lower():
                defender.hold_item = None
                defender.berry_consumed = True
                attacker.berry_consumed = True
                berry_lower = stolen_item.lower()
                if "oran" in berry_lower:
                    heal = min(10, attacker.max_hp - attacker.current_hp)
                elif "sitrus" in berry_lower:
                    heal = min(max(1, attacker.max_hp // 4), attacker.max_hp - attacker.current_hp)
                else:
                    heal = 0
                if heal > 0:
                    attacker.current_hp += heal
                    extra_parts.append(
                        f"{attacker.name} ăn {stolen_item} từ {defender.name} và hồi {heal} HP ({attacker.current_hp}/{attacker.max_hp})."
                    )
                else:
                    extra_parts.append(f"{attacker.name} ăn {stolen_item} cướp từ {defender.name}.")

        if move.name == "Bug Buzz" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -1)
            if changed:
                extra_parts.append(f"Sp. Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Combat Torque" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Confusion" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            if defender.confusion_turns <= 0:
                defender.confusion_turns = random.randint(2, 5)
                extra_parts.append(f"{defender.name} bị Confusion!")

        if move.name == "Constrict" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            changed, stage_text = self._change_stat_stage(defender, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {defender.name} giảm {stage_text}.")

        if move.name == "Cross Poison" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison!")

        if move.name == "Dragon Breath" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Esper Wing" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "speed", +1)
            if changed:
                extra_parts.append(f"Speed của {attacker.name} tăng {stage_text}.")

        if move.name == "Drum Beating" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {defender.name} giảm {stage_text}.")

        if move.name == "Dynamic Punch" and defender.current_hp > 0 and defender.confusion_turns <= 0 and not defender_blocks_additional:
            defender.confusion_turns = random.randint(2, 5)
            extra_parts.append(f"{defender.name} bị Confusion!")

        if move.name == "Earth Power" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -1)
            if changed:
                extra_parts.append(f"Sp. Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Focus Blast" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -1)
            if changed:
                extra_parts.append(f"Sp. Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Force Palm" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Earthquake" and (
            (defender is self.player_active and self.player_dig_charging)
            or (defender is self.wild and self.wild_dig_charging)
        ):
            extra_parts.append("Earthquake đánh trúng mục tiêu đang Dig với sức mạnh nhân đôi.")

        if move.name == "Extrasensory" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Fake Out" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch bởi Fake Out!")

        if move.name == "Dragon Rush" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Crunch" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20:
            changed, stage_text = self._change_stat_stage(defender, "defense", -1)
            if changed:
                extra_parts.append(f"Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Crush Claw" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.50:
            changed, stage_text = self._change_stat_stage(defender, "defense", -1)
            if changed:
                extra_parts.append(f"Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Dark Pulse" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Dark Void" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            defender.status = "slp"
            defender.status_counter = random.randint(1, 3)
            extra_parts.append(f"{defender.name} bị Sleep do Dark Void!")

        if move.name == "Diamond Storm" and attacker.current_hp > 0 and random.random() < 0.50:
            changed, stage_text = self._change_stat_stage(attacker, "defense", +2)
            if changed:
                extra_parts.append(f"Defense của {attacker.name} tăng mạnh {stage_text}.")

        if move.name == "Dire Claw" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.50:
            roll = random.choice(["psn", "par", "slp"])
            if roll == "psn":
                if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                    defender.status = "psn"
                    defender.status_counter = 0
                    extra_parts.append(f"{defender.name} bị Poison!")
            elif roll == "par":
                if "Electric" not in defender.types:
                    defender.status = "par"
                    defender.status_counter = 0
                    extra_parts.append(f"{defender.name} bị Paralysis!")
            else:
                defender.status = "slp"
                defender.status_counter = random.randint(1, 3)
                extra_parts.append(f"{defender.name} bị Sleep!")

        if move.name == "Discharge" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Eerie Spell" and defender.current_hp > 0:
            target_last = self.player_last_move_name if defender is self.player_active else self.wild_last_move_name
            if target_last:
                target_move = next((mv for mv in defender.moves if mv.name == target_last), None)
                if target_move is not None and target_move.current_pp > 0:
                    reduced = min(3, target_move.current_pp)
                    target_move.current_pp -= reduced
                    extra_parts.append(f"Eerie Spell làm {target_last} của {defender.name} mất {reduced} PP.")

        if move.name == "Electroweb" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {defender.name} giảm {stage_text}.")

        if move.name == "Ember" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Energy Ball" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -1)
            if changed:
                extra_parts.append(f"Sp. Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Fire Fang" and defender.current_hp > 0:
            if not defender_blocks_additional and defender.status is None and random.random() < 0.10 and "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")
            if not defender_blocks_additional and random.random() < 0.10:
                if defender is self.player_active:
                    self.player_flinched = True
                else:
                    self.wild_flinched = True
                extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Fire Lash" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "defense", -1)
            if changed:
                extra_parts.append(f"Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Fire Pledge" and defender.current_hp > 0:
            extra_parts.append("Hiệu ứng combo với Grass/Water Pledge chưa áp dụng trong battle 1v1 hiện tại.")

        if move.name == "Fire Punch" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Fire Spin" and defender.current_hp > 0 and not defender_blocks_additional:
            turns = random.randint(4, 5)
            applied_turns = self._apply_binding_effect(attacker, defender, turns)
            extra_parts.append(f"{defender.name} bị Fire Spin trói trong {applied_turns} lượt!")

        if move.name == "Flame Charge" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "speed", +1)
            if changed:
                extra_parts.append(f"Speed của {attacker.name} tăng {stage_text}.")

        if move.name == "Flame Wheel" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Flamethrower" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Flare Blitz" and damage > 0 and attacker.current_hp > 0:
            recoil = max(1, damage // 3)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} chịu phản lực {recoil} HP ({attacker.current_hp}/{attacker.max_hp}).")
            if defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10 and "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Take Down" and damage > 0 and attacker.current_hp > 0:
            recoil = max(1, damage // 4)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} chịu phản lực {recoil} HP ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Volt Tackle" and damage > 0 and attacker.current_hp > 0:
            recoil = max(1, damage // 3)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} chịu phản lực {recoil} HP ({attacker.current_hp}/{attacker.max_hp}).")
            if defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10 and "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Wave Crash" and damage > 0 and attacker.current_hp > 0:
            recoil = max(1, damage // 3)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} chịu phản lực {recoil} HP ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Wild Charge" and damage > 0 and attacker.current_hp > 0:
            recoil = max(1, damage // 4)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} chịu phản lực {recoil} HP ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Wood Hammer" and damage > 0 and attacker.current_hp > 0:
            recoil = max(1, damage // 3)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} chịu phản lực {recoil} HP ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Flash Cannon" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -1)
            if changed:
                extra_parts.append(f"Sp. Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Fleur Cannon" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "sp_attack", -2)
            if changed:
                extra_parts.append(f"Sp. Attack của {attacker.name} giảm mạnh {stage_text}.")

        if move.name == "Fling" and damage > 0:
            thrown_item = attacker.hold_item
            held_lower = (attacker.hold_item or "").strip().lower()
            attacker.hold_item = None
            if thrown_item:
                extra_parts.append(f"{attacker.name} ném {thrown_item} bằng Fling!")
            if defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
                if "flame orb" in held_lower and "Fire" not in defender.types:
                    defender.status = "brn"
                    defender.status_counter = 0
                    extra_parts.append(f"{defender.name} bị Burn do Flame Orb!")
                elif "toxic orb" in held_lower and "Poison" not in defender.types and "Steel" not in defender.types:
                    defender.status = "tox"
                    defender.status_counter = 1
                    extra_parts.append(f"{defender.name} bị Badly Poisoned do Toxic Orb!")

        if move.name == "Flip Turn" and attacker.current_hp > 0:
            if attacker is self.player_active:
                options = [
                    (idx, pkmn)
                    for idx, pkmn in enumerate(self.player.party)
                    if idx != self.player_active_index and pkmn.current_hp > 0
                ]
                if options:
                    next_index, next_pokemon = options[0]
                    self.booster_energy_boost_stat.pop(id(self.player_active), None)
                    self.player_seeded = False
                    self.player_aqua_ring = False
                    self.player_trapped_turns = 0
                    self.player_bound_turns = 0
                    self.player_flinched = False
                    self.player_last_move_name = None
                    self.player_active_index = next_index
                    self.player_yawn_turns = 0
                    self.player_infatuated = False
                    self.wild_infatuated = False
                    hazard_logs = self._apply_switch_in_hazards(next_pokemon, is_player=True)
                    ability_logs = self._trigger_switch_in_ability(next_pokemon, is_player=True)
                    extra_parts.append(f"{attacker.name} rút lui sau Flip Turn! Bạn đổi sang {next_pokemon.name}.")
                    if hazard_logs:
                        extra_parts.extend(hazard_logs)
                    if ability_logs:
                        extra_parts.extend(ability_logs)
            else:
                extra_parts.append("Flip Turn của wild không đổi được Pokémon vì không có party dự bị.")

        if move.name == "Floaty Fall" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Fiery Dance" and attacker.current_hp > 0 and random.random() < 0.50:
            changed, stage_text = self._change_stat_stage(attacker, "sp_attack", +1)
            if changed:
                extra_parts.append(f"Sp. Attack của {attacker.name} tăng {stage_text}.")

        if move.name == "Fiery Wrath" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Fire Blast" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Freeze Shock" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Freeze-Dry" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            defender.status = "slp"
            defender.status_counter = 1
            extra_parts.append(f"{defender.name} bị đóng băng tạm mô phỏng bằng Sleep 1 lượt.")

        if move.name == "Freezing Glare" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            defender.status = "slp"
            defender.status_counter = 1
            extra_parts.append(f"{defender.name} bị đóng băng tạm mô phỏng bằng Sleep 1 lượt.")

        if move.name == "Freezy Frost" and defender.current_hp > 0:
            self.player_stat_stages = {"attack": 0, "defense": 0, "sp_attack": 0, "sp_defense": 0, "speed": 0}
            self.wild_stat_stages = {"attack": 0, "defense": 0, "sp_attack": 0, "sp_defense": 0, "speed": 0}
            extra_parts.append("Freezy Frost xóa toàn bộ thay đổi chỉ số của cả hai bên.")

        if move.name == "Flame Burst" and defender.current_hp > 0:
            extra_parts.append("Flame Burst: hiệu ứng gây sát thương Pokémon kề bên không áp dụng trong battle 1v1.")

        if move.name in {"Fusion Bolt", "Fusion Flare"} and (
            (attacker is self.player_active and self.wild_acted_before_player)
            or (attacker is self.wild and self.player_acted_before_wild)
        ):
            extra_parts.append(f"{move.name} được khuếch đại nhờ combo Fusion cùng lượt!")

        if move.name == "G-Max Befuddle" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            roll = random.choice(["psn", "par", "slp"])
            if roll == "psn":
                if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                    defender.status = "psn"
                    defender.status_counter = 0
                    extra_parts.append(f"{defender.name} bị Poison bởi G-Max Befuddle!")
            elif roll == "par":
                if "Electric" not in defender.types:
                    defender.status = "par"
                    defender.status_counter = 0
                    extra_parts.append(f"{defender.name} bị Paralysis bởi G-Max Befuddle!")
            else:
                defender.status = "slp"
                defender.status_counter = random.randint(1, 3)
                extra_parts.append(f"{defender.name} bị Sleep bởi G-Max Befuddle!")

        if move.name == "G-Max Cannonade" and defender.current_hp > 0:
            if defender is self.player_active:
                self.player_cannonade_turns = 4
            else:
                self.wild_cannonade_turns = 4
            extra_parts.append(f"{defender.name} bị bao phủ bởi Cannonade trong 4 lượt!")

        if move.name == "G-Max Tartness" and defender.current_hp > 0:
            extra_parts.append("G-Max Tartness: giảm Evasion chưa được mô phỏng chi tiết trong engine hiện tại.")

        if move.name == "G-Max Terror" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_trapped_turns = max(self.player_trapped_turns, 4)
            else:
                self.wild_trapped_turns = max(self.wild_trapped_turns, 4)
            extra_parts.append(f"{defender.name} bị khóa đổi Pokémon bởi G-Max Terror.")

        if move.name == "G-Max Vine Lash" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_vine_lash_turns = 4
            else:
                self.wild_vine_lash_turns = 4
            extra_parts.append(f"{defender.name} chịu hiệu ứng Vine Lash trong 4 lượt!")

        if move.name == "G-Max Volcalith" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_volcalith_turns = 4
            else:
                self.wild_volcalith_turns = 4
            extra_parts.append(f"{defender.name} chịu hiệu ứng Volcalith trong 4 lượt!")

        if move.name == "G-Max Volt Crash" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis bởi G-Max Volt Crash!")

        if move.name == "G-Max Wildfire" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_wildfire_turns = 4
            else:
                self.wild_wildfire_turns = 4
            extra_parts.append(f"{defender.name} chịu hiệu ứng Wildfire trong 4 lượt!")

        if move.name == "G-Max Wind Rage" and defender.current_hp > 0:
            self.player_spikes_layers = 0
            self.player_toxic_spikes_layers = 0
            self.player_stealth_rock = False
            self.player_sticky_web = False
            self.wild_spikes_layers = 0
            self.wild_toxic_spikes_layers = 0
            self.wild_stealth_rock = False
            self.wild_sticky_web = False
            extra_parts.append("G-Max Wind Rage quét sạch hazards trên sân.")

        if move.name == "G-Max Centiferno" and defender.current_hp > 0 and not defender_blocks_additional:
            turns = random.randint(4, 5)
            applied_turns = self._apply_binding_effect(attacker, defender, turns)
            extra_parts.append(f"{defender.name} bị G-Max Centiferno trói trong {applied_turns} lượt!")

        if move.name == "G-Max Chi Strike" and attacker.current_hp > 0:
            if attacker is self.player_active:
                self.player_dragon_cheer_turns = max(self.player_dragon_cheer_turns, 3)
            else:
                self.wild_dragon_cheer_turns = max(self.wild_dragon_cheer_turns, 3)
            extra_parts.append(f"G-Max Chi Strike tăng tỉ lệ chí mạng cho phe của {attacker.name} trong vài lượt!")

        if move.name == "G-Max Cuddle" and defender.current_hp > 0 and not defender_blocks_additional:
            if not self._is_infatuated(defender):
                knot_text = self._set_infatuated(defender, True, source=attacker)
                extra_parts.append(f"{defender.name} bị mê mẩn bởi G-Max Cuddle!")
                if knot_text:
                    extra_parts.append(knot_text)

        if move.name == "G-Max Depletion" and defender.current_hp > 0 and not defender_blocks_additional:
            target_last = self.player_last_move_name if defender is self.player_active else self.wild_last_move_name
            if target_last:
                target_move = next((mv for mv in defender.moves if mv.name == target_last), None)
                if target_move is not None and target_move.current_pp > 0:
                    reduced = min(2, target_move.current_pp)
                    target_move.current_pp -= reduced
                    extra_parts.append(f"G-Max Depletion làm {target_last} của {defender.name} mất {reduced} PP.")

        if move.name in {"G-Max Drum Solo", "G-Max Fireball", "G-Max Hydrosnipe"} and defender.current_hp > 0:
            extra_parts.append(f"{move.name} bỏ qua Ability của mục tiêu (mô phỏng cơ bản).")

        if move.name == "G-Max Finale" and attacker.current_hp > 0:
            healed_total = 0
            if attacker is self.player_active:
                for pkmn in self.player.party:
                    if pkmn.current_hp <= 0:
                        continue
                    heal = max(1, pkmn.max_hp // 6)
                    before = pkmn.current_hp
                    pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + heal)
                    healed_total += max(0, pkmn.current_hp - before)
            else:
                heal = max(1, attacker.max_hp // 6)
                before = attacker.current_hp
                attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal)
                healed_total = max(0, attacker.current_hp - before)
            if healed_total > 0:
                extra_parts.append(f"G-Max Finale hồi tổng cộng {healed_total} HP cho phe của {attacker.name}.")

        if move.name == "G-Max Foam Burst" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "speed", -2)
            if changed:
                extra_parts.append(f"Speed của {defender.name} giảm mạnh {stage_text}.")

        if move.name == "G-Max Gold Rush" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender.confusion_turns <= 0:
                defender.confusion_turns = random.randint(2, 5)
                extra_parts.append(f"{defender.name} bị Confusion bởi G-Max Gold Rush!")
            if attacker is self.player_active:
                bonus_money = max(100, attacker.level * 100)
                self.player.money += bonus_money
                extra_parts.append(f"Bạn kiếm thêm {bonus_money} tiền nhờ G-Max Gold Rush!")

        if move.name == "G-Max Gravitas" and attacker.current_hp > 0:
            self.gravity_turns = max(self.gravity_turns, 5)
            extra_parts.append("G-Max Gravitas tạo Gravity trong 5 lượt.")

        if move.name == "G-Max Malodor" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison bởi G-Max Malodor!")

        if move.name == "G-Max Meltdown" and defender.current_hp > 0 and not defender_blocks_additional:
            target_last = self.player_last_move_name if defender is self.player_active else self.wild_last_move_name
            if target_last:
                if defender is self.player_active:
                    self.player_disabled_move = target_last
                    self.player_disable_turns = max(self.player_disable_turns, 2)
                else:
                    self.wild_disabled_move = target_last
                    self.wild_disable_turns = max(self.wild_disable_turns, 2)
                extra_parts.append(f"G-Max Meltdown khóa tạm chiêu {target_last} của {defender.name}.")

        if move.name == "G-Max Replenish" and attacker.current_hp > 0:
            restored = 0
            if attacker is self.player_active:
                for pkmn in self.player.party:
                    if pkmn.berry_consumed:
                        pkmn.berry_consumed = False
                        restored += 1
            else:
                if attacker.berry_consumed:
                    attacker.berry_consumed = False
                    restored = 1
            if restored > 0:
                extra_parts.append(f"G-Max Replenish khôi phục trạng thái Berry cho {restored} Pokémon.")

        if move.name == "G-Max Resonance" and attacker.current_hp > 0:
            screen_turns = self._screen_duration(attacker)
            if attacker is self.player_active:
                self.player_reflect_turns = max(self.player_reflect_turns, screen_turns)
                self.player_light_screen_turns = max(self.player_light_screen_turns, screen_turns)
            else:
                self.wild_reflect_turns = max(self.wild_reflect_turns, screen_turns)
                self.wild_light_screen_turns = max(self.wild_light_screen_turns, screen_turns)
            extra_parts.append(f"G-Max Resonance dựng cả Reflect và Light Screen cho phe {attacker.name} trong {screen_turns} lượt.")

        if move.name == "G-Max Sandblast" and defender.current_hp > 0 and not defender_blocks_additional:
            turns = random.randint(4, 5)
            applied_turns = self._apply_binding_effect(attacker, defender, turns)
            extra_parts.append(f"{defender.name} bị G-Max Sandblast trói trong {applied_turns} lượt!")

        if move.name == "G-Max Smite" and defender.current_hp > 0 and defender.confusion_turns <= 0 and not defender_blocks_additional:
            defender.confusion_turns = random.randint(2, 5)
            extra_parts.append(f"{defender.name} bị Confusion bởi G-Max Smite!")

        if move.name == "G-Max Snooze" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            defender.status = "slp"
            defender.status_counter = 1
            extra_parts.append(f"{defender.name} trở nên buồn ngủ và ngủ 1 lượt (mô phỏng drowsy).")

        if move.name == "G-Max Steelsurge" and attacker.current_hp > 0:
            if attacker is self.player_active:
                if self.wild_spikes_layers < 3:
                    self.wild_spikes_layers += 1
                    extra_parts.append(f"G-Max Steelsurge rải thêm Spikes phía đối thủ ({self.wild_spikes_layers}/3).")
            else:
                if self.player_spikes_layers < 3:
                    self.player_spikes_layers += 1
                    extra_parts.append(f"G-Max Steelsurge rải thêm Spikes phía bạn ({self.player_spikes_layers}/3).")

        if move.name == "G-Max Stonesurge" and attacker.current_hp > 0:
            if attacker is self.player_active:
                if not self.wild_stealth_rock:
                    self.wild_stealth_rock = True
                    extra_parts.append("G-Max Stonesurge dựng Stealth Rock phía đối thủ.")
            else:
                if not self.player_stealth_rock:
                    self.player_stealth_rock = True
                    extra_parts.append("G-Max Stonesurge dựng Stealth Rock phía bạn.")

        if move.name == "G-Max Stun Shock" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            roll = random.choice(["psn", "par"])
            if roll == "psn":
                if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                    defender.status = "psn"
                    defender.status_counter = 0
                    extra_parts.append(f"{defender.name} bị Poison bởi G-Max Stun Shock!")
            else:
                if "Electric" not in defender.types:
                    defender.status = "par"
                    defender.status_counter = 0
                    extra_parts.append(f"{defender.name} bị Paralysis bởi G-Max Stun Shock!")

        if move.name == "G-Max Sweetness" and attacker.current_hp > 0:
            cured = 0
            if attacker is self.player_active:
                for pkmn in self.player.party:
                    if pkmn.status is not None:
                        pkmn.status = None
                        pkmn.status_counter = 0
                        cured += 1
            else:
                if attacker.status is not None:
                    attacker.status = None
                    attacker.status_counter = 0
                    cured = 1
            if cured > 0:
                extra_parts.append(f"G-Max Sweetness chữa trạng thái cho {cured} Pokémon.")

        if move.name == "Genesis Supernova" and attacker.current_hp > 0:
            self.terrain = "psychic terrain"
            terrain_turns = self._terrain_duration(attacker)
            self.terrain_turns = terrain_turns
            extra_parts.append(f"Genesis Supernova tạo Psychic Terrain trong {terrain_turns} lượt.")

        if move.name == "Giga Drain" and damage > 0 and attacker.current_hp > 0:
            heal = self._drain_heal_amount(attacker, max(1, damage // 2))
            if heal > 0:
                attacker.current_hp += heal
                extra_parts.append(f"{attacker.name} hồi {heal} HP nhờ Giga Drain ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Leech Life" and damage > 0 and attacker.current_hp > 0:
            heal = self._drain_heal_amount(attacker, max(1, damage // 2))
            if heal > 0:
                attacker.current_hp += heal
                extra_parts.append(f"{attacker.name} hồi {heal} HP nhờ Leech Life ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Glaciate" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {defender.name} giảm {stage_text}.")

        if move.name == "Glaive Rush" and attacker.current_hp > 0:
            if attacker is self.player_active:
                self.player_glaive_rush_vulnerable_turns = 1
            else:
                self.wild_glaive_rush_vulnerable_turns = 1
            extra_parts.append(f"{attacker.name} trở nên dễ bị trúng đòn hơn trong lượt kế tiếp do Glaive Rush.")

        if move.name == "Glitzy Glow" and attacker.current_hp > 0:
            screen_turns = self._screen_duration(attacker)
            if attacker is self.player_active:
                self.player_light_screen_turns = max(self.player_light_screen_turns, screen_turns)
            else:
                self.wild_light_screen_turns = max(self.wild_light_screen_turns, screen_turns)
            extra_parts.append(f"Glitzy Glow dựng Light Screen cho phe {attacker.name} trong {screen_turns} lượt.")

        if move.name == "Grass Pledge" and defender.current_hp > 0:
            extra_parts.append("Grass Pledge: hiệu ứng combo với Fire/Water Pledge chưa áp dụng trong battle 1v1 hiện tại.")

        if move.name == "Grav Apple" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "defense", -1)
            if changed:
                extra_parts.append(f"Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Gunk Shot" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison!")

        if move.name == "Gust" and (
            (defender is self.player_active and (self.player_fly_charging or self.player_bounce_charging))
            or (defender is self.wild and (self.wild_fly_charging or self.wild_bounce_charging))
        ):
            extra_parts.append("Gust đánh trúng mục tiêu đang bay với sức mạnh nhân đôi.")

        if move.name == "Hammer Arm" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {attacker.name} giảm {stage_text}.")

        if move.name == "Head Charge" and damage > 0 and attacker.current_hp > 0:
            recoil = max(1, damage // 4)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} chịu phản lực {recoil} HP ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Head Smash" and damage > 0 and attacker.current_hp > 0:
            recoil = max(1, damage // 2)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} chịu phản lực {recoil} HP ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Headbutt" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Headlong Rush" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "defense", -1)
            if changed:
                extra_parts.append(f"Defense của {attacker.name} giảm {stage_text}.")

        if move.name == "Lava Plume" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Leaf Storm" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "sp_attack", -2)
            if changed:
                extra_parts.append(f"Sp. Attack của {attacker.name} giảm mạnh {stage_text}.")

        if move.name == "Leaf Tornado" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.50:
            extra_parts.append("Leaf Tornado: hiệu ứng giảm Accuracy được rút gọn trong engine hiện tại.")

        if move.name == "Lick" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Light of Ruin" and damage > 0 and attacker.current_hp > 0:
            recoil = max(1, damage // 2)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} chịu phản lực {recoil} HP từ Light of Ruin ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Liquidation" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20:
            changed, stage_text = self._change_stat_stage(defender, "defense", -1)
            if changed:
                extra_parts.append(f"Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Low Sweep" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {defender.name} giảm {stage_text}.")

        if move.name == "Lunge" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "attack", -1)
            if changed:
                extra_parts.append(f"Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Luster Purge" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.50:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -1)
            if changed:
                extra_parts.append(f"Sp. Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Lumina Crash" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -2)
            if changed:
                extra_parts.append(f"Sp. Defense của {defender.name} giảm mạnh {stage_text}.")

        if move.name == "Magical Torque" and defender.current_hp > 0 and defender.confusion_turns <= 0 and not defender_blocks_additional and random.random() < 0.30:
            defender.confusion_turns = random.randint(2, 5)
            extra_parts.append(f"{defender.name} bị Confusion!")

        if move.name == "Magma Storm" and defender.current_hp > 0 and not defender_blocks_additional:
            turns = random.randint(4, 5)
            self._apply_binding_effect(attacker, defender, turns)
            extra_parts.append(f"{defender.name} bị mắc kẹt trong Magma Storm {turns} lượt!")

        if move.name == "Make It Rain" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "sp_attack", -1)
            if changed:
                extra_parts.append(f"Sp. Attack của {attacker.name} giảm {stage_text} do Make It Rain.")
            if attacker is self.player_active:
                bonus_money = max(50, attacker.level * 50)
                self.player.money += bonus_money
                extra_parts.append(f"Bạn nhặt được thêm {bonus_money} tiền nhờ Make It Rain!")

        if move.name == "Malignant Chain" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.50:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison bởi Malignant Chain!")

        if move.name == "Matcha Gotcha" and damage > 0 and attacker.current_hp > 0:
            heal = self._drain_heal_amount(attacker, max(1, damage // 2))
            if heal > 0:
                attacker.current_hp += heal
                extra_parts.append(f"{attacker.name} hồi {heal} HP nhờ Matcha Gotcha ({attacker.current_hp}/{attacker.max_hp}).")
            if defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.20 and "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn bởi Matcha Gotcha!")

        if move.name == "Mega Drain" and damage > 0 and attacker.current_hp > 0:
            heal = self._drain_heal_amount(attacker, max(1, damage // 2))
            if heal > 0:
                attacker.current_hp += heal
                extra_parts.append(f"{attacker.name} hồi {heal} HP nhờ Mega Drain ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Metal Claw" and attacker.current_hp > 0 and random.random() < 0.10:
            changed, stage_text = self._change_stat_stage(attacker, "attack", +1)
            if changed:
                extra_parts.append(f"Attack của {attacker.name} tăng {stage_text} nhờ Metal Claw.")

        if move.name == "Meteor Beam" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "sp_attack", +1)
            if changed:
                extra_parts.append(f"Meteor Beam tăng Sp. Attack của {attacker.name} {stage_text}.")

        if move.name == "Mind Blown" and attacker.current_hp > 0:
            recoil = max(1, attacker.max_hp // 2)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} chịu phản lực {recoil} HP từ Mind Blown ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Mirror Shot" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            extra_parts.append("Mirror Shot: hiệu ứng giảm Accuracy được rút gọn trong engine hiện tại.")

        if move.name == "Mist Ball" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.50:
            changed, stage_text = self._change_stat_stage(defender, "sp_attack", -1)
            if changed:
                extra_parts.append(f"Sp. Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Misty Explosion" and attacker.current_hp > 0:
            attacker.current_hp = 0
            extra_parts.append(f"{attacker.name} gục sau khi dùng Misty Explosion.")

        if move.name == "Moonblast" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            changed, stage_text = self._change_stat_stage(defender, "sp_attack", -1)
            if changed:
                extra_parts.append(f"Sp. Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Needle Arm" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Night Daze" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.40:
            extra_parts.append("Night Daze: hiệu ứng giảm Accuracy được rút gọn trong engine hiện tại.")

        if move.name == "Noxious Torque" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison bởi Noxious Torque!")

        if move.name == "Nuzzle" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis bởi Nuzzle!")

        if move.name == "Oblivion Wing" and damage > 0 and attacker.current_hp > 0:
            heal = self._drain_heal_amount(attacker, max(1, (damage * 3) // 4))
            if heal > 0:
                attacker.current_hp += heal
                extra_parts.append(f"{attacker.name} hồi {heal} HP nhờ Oblivion Wing ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Octazooka" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.50:
            extra_parts.append("Octazooka: hiệu ứng giảm Accuracy được rút gọn trong engine hiện tại.")

        if move.name == "Ominous Wind" and attacker.current_hp > 0 and random.random() < 0.10:
            for stat_key in ["attack", "defense", "sp_attack", "sp_defense", "speed"]:
                self._change_stat_stage(attacker, stat_key, +1)
            extra_parts.append(f"Ominous Wind tăng toàn bộ chỉ số của {attacker.name}!")

        if move.name == "Order Up" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "attack", +1)
            if changed:
                extra_parts.append(f"Order Up tăng Attack của {attacker.name} {stage_text}.")

        if move.name == "Outrage" and attacker.current_hp > 0:
            if attacker is self.player_active:
                if self.player_outrage_turns <= 0:
                    self.player_outrage_turns = random.randint(2, 3)
                self.player_outrage_turns -= 1
                if self.player_outrage_turns <= 0 and attacker.confusion_turns <= 0:
                    attacker.confusion_turns = random.randint(2, 5)
                    extra_parts.append(f"{attacker.name} rơi vào Confusion sau Outrage!")
            else:
                if self.wild_outrage_turns <= 0:
                    self.wild_outrage_turns = random.randint(2, 3)
                self.wild_outrage_turns -= 1
                if self.wild_outrage_turns <= 0 and attacker.confusion_turns <= 0:
                    attacker.confusion_turns = random.randint(2, 5)
                    extra_parts.append(f"{attacker.name} rơi vào Confusion sau Outrage!")

        if move.name == "Raging Fury" and attacker.current_hp > 0:
            if attacker is self.player_active:
                if self.player_outrage_turns <= 0:
                    self.player_outrage_turns = random.randint(2, 3)
                self.player_outrage_turns -= 1
                if self.player_outrage_turns <= 0 and attacker.confusion_turns <= 0:
                    attacker.confusion_turns = random.randint(2, 5)
                    extra_parts.append(f"{attacker.name} rơi vào Confusion sau Raging Fury!")
            else:
                if self.wild_outrage_turns <= 0:
                    self.wild_outrage_turns = random.randint(2, 3)
                self.wild_outrage_turns -= 1
                if self.wild_outrage_turns <= 0 and attacker.confusion_turns <= 0:
                    attacker.confusion_turns = random.randint(2, 5)
                    extra_parts.append(f"{attacker.name} rơi vào Confusion sau Raging Fury!")

        if move.name == "Rage" and attacker.current_hp > 0:
            if attacker is self.player_active:
                self.player_rage_active = True
            else:
                self.wild_rage_active = True
            extra_parts.append(f"{attacker.name} đang nổi Rage! Khi bị đánh trúng, Attack sẽ tăng.")

        if move.name == "Petal Dance" and attacker.current_hp > 0:
            if attacker is self.player_active:
                if self.player_outrage_turns <= 0:
                    self.player_outrage_turns = random.randint(2, 3)
                self.player_outrage_turns -= 1
                if self.player_outrage_turns <= 0 and attacker.confusion_turns <= 0:
                    attacker.confusion_turns = random.randint(2, 5)
                    extra_parts.append(f"{attacker.name} rơi vào Confusion sau Petal Dance!")
            else:
                if self.wild_outrage_turns <= 0:
                    self.wild_outrage_turns = random.randint(2, 3)
                self.wild_outrage_turns -= 1
                if self.wild_outrage_turns <= 0 and attacker.confusion_turns <= 0:
                    attacker.confusion_turns = random.randint(2, 5)
                    extra_parts.append(f"{attacker.name} rơi vào Confusion sau Petal Dance!")

        if move.name == "Overheat" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "sp_attack", -2)
            if changed:
                extra_parts.append(f"Sp. Attack của {attacker.name} giảm mạnh {stage_text} do Overheat.")

        if move.name == "Mountain Gale" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {attacker.name} giảm {stage_text} do Mountain Gale.")

        if move.name == "Mud Bomb" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            extra_parts.append("Mud Bomb: hiệu ứng giảm Accuracy được rút gọn trong engine hiện tại.")

        if move.name == "Mud Shot" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {defender.name} giảm {stage_text}.")

        if move.name == "Mud-Slap" and defender.current_hp > 0 and not defender_blocks_additional:
            extra_parts.append("Mud-Slap: hiệu ứng giảm Accuracy được rút gọn trong engine hiện tại.")

        if move.name == "Muddy Water" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            extra_parts.append("Muddy Water: hiệu ứng giảm Accuracy được rút gọn trong engine hiện tại.")

        if move.name == "Mortal Spin" and attacker.current_hp > 0:
            if attacker is self.player_active:
                self.player_spikes_layers = 0
                self.player_toxic_spikes_layers = 0
                self.player_stealth_rock = False
                self.player_sticky_web = False
                self.player_bound_turns = 0
                self.player_trapped_turns = 0
                self.player_seeded = False
            else:
                self.wild_spikes_layers = 0
                self.wild_toxic_spikes_layers = 0
                self.wild_stealth_rock = False
                self.wild_sticky_web = False
                self.wild_bound_turns = 0
                self.wild_trapped_turns = 0
                self.wild_seeded = False
            extra_parts.append(f"Mortal Spin quét sạch hazard và giải trói cho {attacker.name}.")
            if defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
                if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                    defender.status = "psn"
                    defender.status_counter = 0
                    extra_parts.append(f"{defender.name} bị Poison bởi Mortal Spin!")

        if move.name == "Parabolic Charge" and damage > 0 and attacker.current_hp > 0:
            heal = self._drain_heal_amount(attacker, max(1, damage // 2))
            if heal > 0:
                attacker.current_hp += heal
                extra_parts.append(f"{attacker.name} hồi {heal} HP nhờ Parabolic Charge ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Psyshield Bash" and attacker.current_hp > 0:
            changed_def, def_text = self._change_stat_stage(attacker, "defense", +1)
            changed_spd, spd_text = self._change_stat_stage(attacker, "sp_defense", +1)
            if changed_def:
                extra_parts.append(f"Defense của {attacker.name} tăng {def_text}.")
            if changed_spd:
                extra_parts.append(f"Sp. Defense của {attacker.name} tăng {spd_text}.")

        if move.name == "Pounce" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {defender.name} giảm {stage_text}.")

        if move.name == "Pay Day" and attacker is self.player_active and damage > 0:
            gained = max(1, attacker.level * 5)
            self.pay_day_bonus += gained
            extra_parts.append(f"Pay Day rải tiền: tích lũy thêm {gained} PokéDollars sau trận.")

        if move.name == "Play Rough" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            changed, stage_text = self._change_stat_stage(defender, "attack", -1)
            if changed:
                extra_parts.append(f"Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Power-Up Punch" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "attack", +1)
            if changed:
                extra_parts.append(f"Attack của {attacker.name} tăng {stage_text} nhờ Power-Up Punch.")

        if move.name == "Pluck" and defender.current_hp > 0 and defender.hold_item:
            held = (defender.hold_item or "").strip().lower()
            if "berry" in held:
                stolen = defender.hold_item
                defender.hold_item = None
                defender.berry_consumed = True
                heal = min(max(1, attacker.max_hp // 4), attacker.max_hp - attacker.current_hp)
                if heal > 0:
                    attacker.current_hp += heal
                extra_parts.append(f"Pluck ăn {stolen} của {defender.name} và hồi {heal} HP cho {attacker.name}.")

        if move.name == "Poison Fang" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.50:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "tox"
                defender.status_counter = 1
                extra_parts.append(f"{defender.name} bị Badly Poisoned bởi Poison Fang!")

        if move.name == "Poison Jab" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison!")

        if move.name == "Poison Sting" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison!")

        if move.name == "Poison Tail" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison!")

        if move.name == "Powder Snow" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            defender.status = "slp"
            defender.status_counter = 1
            extra_parts.append(f"{defender.name} bị đóng băng tạm mô phỏng bằng Sleep 1 lượt.")

        if move.name == "Psybeam" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            if defender.confusion_turns <= 0:
                defender.confusion_turns = random.randint(2, 5)
                extra_parts.append(f"{defender.name} bị Confusion!")

        if move.name == "Psychic" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -1)
            if changed:
                extra_parts.append(f"Sp. Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Psychic Fangs" and defender.current_hp > 0:
            if defender is self.player_active:
                cleared = []
                if self.player_reflect_turns > 0:
                    self.player_reflect_turns = 0
                    cleared.append("Reflect")
                if self.player_light_screen_turns > 0:
                    self.player_light_screen_turns = 0
                    cleared.append("Light Screen")
            else:
                cleared = []
                if self.wild_reflect_turns > 0:
                    self.wild_reflect_turns = 0
                    cleared.append("Reflect")
                if self.wild_light_screen_turns > 0:
                    self.wild_light_screen_turns = 0
                    cleared.append("Light Screen")
            if cleared:
                extra_parts.append(f"Psychic Fangs phá vỡ {', '.join(cleared)} của phe {defender.name}.")

        if move.name == "Psychic Noise" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_heal_block_turns = max(self.player_heal_block_turns, 2)
            else:
                self.wild_heal_block_turns = max(self.wild_heal_block_turns, 2)
            extra_parts.append(f"{defender.name} bị chặn hồi máu bởi Psychic Noise trong 2 lượt.")

        if move.name == "Psycho Boost" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "sp_attack", -2)
            if changed:
                extra_parts.append(f"Sp. Attack của {attacker.name} giảm mạnh {stage_text}.")

        if move.name == "Pyro Ball" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Rapid Spin" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "speed", +1)
            if changed:
                extra_parts.append(f"Speed của {attacker.name} tăng {stage_text} nhờ Rapid Spin.")
            if attacker is self.player_active:
                self.player_spikes_layers = 0
                self.player_toxic_spikes_layers = 0
                self.player_stealth_rock = False
                self.player_sticky_web = False
                self.player_bound_turns = 0
                self.player_trapped_turns = 0
                self.player_seeded = False
            else:
                self.wild_spikes_layers = 0
                self.wild_toxic_spikes_layers = 0
                self.wild_stealth_rock = False
                self.wild_sticky_web = False
                self.wild_bound_turns = 0
                self.wild_trapped_turns = 0
                self.wild_seeded = False
            extra_parts.append(f"Rapid Spin quét sạch hazard và giải trói cho {attacker.name}.")

        if move.name == "Raging Bull" and defender.current_hp > 0:
            if defender is self.player_active:
                cleared = []
                if self.player_reflect_turns > 0:
                    self.player_reflect_turns = 0
                    cleared.append("Reflect")
                if self.player_light_screen_turns > 0:
                    self.player_light_screen_turns = 0
                    cleared.append("Light Screen")
            else:
                cleared = []
                if self.wild_reflect_turns > 0:
                    self.wild_reflect_turns = 0
                    cleared.append("Reflect")
                if self.wild_light_screen_turns > 0:
                    self.wild_light_screen_turns = 0
                    cleared.append("Light Screen")
            if cleared:
                extra_parts.append(f"Raging Bull phá vỡ {', '.join(cleared)} của phe {defender.name}.")

        if move.name == "Razor Shell" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.50:
            changed, stage_text = self._change_stat_stage(defender, "defense", -1)
            if changed:
                extra_parts.append(f"Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Relic Song" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            defender.status = "slp"
            defender.status_counter = random.randint(1, 3)
            extra_parts.append(f"{defender.name} bị Sleep bởi Relic Song!")

        if move.name == "Rock Climb" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20:
            if defender.confusion_turns <= 0:
                defender.confusion_turns = random.randint(2, 5)
                extra_parts.append(f"{defender.name} bị Confusion!")

        if move.name == "Rock Slide" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Rock Smash" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.50:
            changed, stage_text = self._change_stat_stage(defender, "defense", -1)
            if changed:
                extra_parts.append(f"Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Rock Tomb" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {defender.name} giảm {stage_text}.")

        if move.name == "Rolling Kick" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Sacred Fire" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.50:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Salt Cure" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_salt_cure_turns = max(self.player_salt_cure_turns, 4)
            else:
                self.wild_salt_cure_turns = max(self.wild_salt_cure_turns, 4)
            extra_parts.append(f"{defender.name} bị Salt Cure và sẽ mất HP mỗi lượt.")

        if move.name == "Sand Tomb" and defender.current_hp > 0 and not defender_blocks_additional:
            turns = random.randint(4, 5)
            applied_turns = self._apply_binding_effect(attacker, defender, turns)
            extra_parts.append(f"{defender.name} bị Sand Tomb trói trong {applied_turns} lượt!")

        if move.name == "Sandsear Storm" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.20:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Sappy Seed" and defender.current_hp > 0 and not defender_blocks_additional:
            if "Grass" in defender.types:
                extra_parts.append(f"{defender.name} miễn nhiễm với Sappy Seed do hệ Grass.")
            elif defender is self.player_active:
                self.player_seeded = True
                extra_parts.append(f"{defender.name} bị gieo hạt bởi Sappy Seed.")
            else:
                self.wild_seeded = True
                extra_parts.append(f"{defender.name} bị gieo hạt bởi Sappy Seed.")

        if move.name == "Scald" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Scale Shot" and attacker.current_hp > 0:
            changed_spe, spe_text = self._change_stat_stage(attacker, "speed", +1)
            changed_def, def_text = self._change_stat_stage(attacker, "defense", -1)
            if changed_spe:
                extra_parts.append(f"Speed của {attacker.name} tăng {spe_text}.")
            if changed_def:
                extra_parts.append(f"Defense của {attacker.name} giảm {def_text}.")

        if move.name == "Scorching Sands" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Searing Shot" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Seed Flare" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.40:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -2)
            if changed:
                extra_parts.append(f"Sp. Defense của {defender.name} giảm mạnh {stage_text}.")

        if move.name == "Shadow Ball" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -1)
            if changed:
                extra_parts.append(f"Sp. Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Shadow Bone" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20:
            changed, stage_text = self._change_stat_stage(defender, "defense", -1)
            if changed:
                extra_parts.append(f"Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Shell Side Arm" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.20:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison!")

        if move.name == "Signal Beam" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            if defender.confusion_turns <= 0:
                defender.confusion_turns = random.randint(2, 5)
                extra_parts.append(f"{defender.name} bị Confusion!")

        if move.name == "Sizzly Slide" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Skitter Smack" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "sp_attack", -1)
            if changed:
                extra_parts.append(f"Sp. Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Sludge" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison!")

        if move.name == "Sludge Bomb" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison!")

        if move.name == "Sludge Wave" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison!")

        if move.name == "Smog" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.40:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison!")

        if move.name == "Snarl" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "sp_attack", -1)
            if changed:
                extra_parts.append(f"Sp. Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Smack Down" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_smack_down_grounded = True
                self.player_magnet_rise_turns = 0
                self.player_fly_charging = False
                self.player_bounce_charging = False
                self.player_sky_drop_charging = False
            else:
                self.wild_smack_down_grounded = True
                self.wild_magnet_rise_turns = 0
                self.wild_fly_charging = False
                self.wild_bounce_charging = False
                self.wild_sky_drop_charging = False
            extra_parts.append(f"{defender.name} bị Smack Down kéo xuống đất và trở nên dễ trúng chiêu Ground.")

        if move.name == "Smelling Salts" and damage > 0:
            if defender.status == "par":
                healed = min(defender.max_hp, defender.current_hp + damage)
                applied = healed - defender.current_hp
                defender.current_hp = healed
                damage = max(0, damage - applied)
                defender.status = None
                defender.status_counter = 0
                extra_parts.append(f"Smelling Salts gây gấp đôi lên mục tiêu tê liệt và chữa Paralysis cho {defender.name}.")

        if move.name == "Silver Wind" and attacker.current_hp > 0 and random.random() < 0.10:
            boosted: list[str] = []
            for stat_key, label in [
                ("attack", "Attack"),
                ("defense", "Defense"),
                ("sp_attack", "Sp. Attack"),
                ("sp_defense", "Sp. Defense"),
                ("speed", "Speed"),
            ]:
                changed, _ = self._change_stat_stage(attacker, stat_key, +1)
                if changed:
                    boosted.append(label)
            if boosted:
                extra_parts.append(f"Silver Wind tăng {', '.join(boosted)} cho {attacker.name}.")

        if move.name == "Secret Power" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Plasma Fists" and attacker.current_hp > 0:
            self.ion_deluge_active = True
            extra_parts.append("Plasma Fists khiến các chiêu Normal trong lượt này đổi thành Electric.")

        if move.name == "Mystical Fire" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "sp_attack", -1)
            if changed:
                extra_parts.append(f"Sp. Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Mystical Power" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "sp_attack", +1)
            if changed:
                extra_parts.append(f"Sp. Attack của {attacker.name} tăng {stage_text}.")

        if move.name == "Max Airstream" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "speed", +1)
            if changed:
                extra_parts.append(f"Max Airstream tăng Speed của {attacker.name} {stage_text}.")

        if move.name == "Max Darkness" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "sp_defense", -1)
            if changed:
                extra_parts.append(f"Max Darkness làm Sp. Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Max Flare" and attacker.current_hp > 0:
            self.weather = "harsh sunlight"
            weather_turns = self._weather_duration(attacker, "harsh sunlight")
            self.weather_turns = weather_turns
            extra_parts.append(f"Max Flare tạo nắng gắt trong {weather_turns} lượt.")

        if move.name == "Max Flutterby" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "sp_attack", -1)
            if changed:
                extra_parts.append(f"Max Flutterby làm Sp. Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Max Geyser" and attacker.current_hp > 0:
            self.weather = "rain"
            weather_turns = self._weather_duration(attacker, "rain")
            self.weather_turns = weather_turns
            extra_parts.append(f"Max Geyser tạo mưa trong {weather_turns} lượt.")

        if move.name == "Max Hailstorm" and attacker.current_hp > 0:
            self.weather = "snow"
            weather_turns = self._weather_duration(attacker, "snow")
            self.weather_turns = weather_turns
            extra_parts.append(f"Max Hailstorm tạo tuyết trong {weather_turns} lượt.")

        if move.name == "Max Knuckle" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "attack", +1)
            if changed:
                extra_parts.append(f"Max Knuckle tăng Attack của {attacker.name} {stage_text}.")

        if move.name == "Max Lightning" and attacker.current_hp > 0:
            self.terrain = "electric terrain"
            terrain_turns = self._terrain_duration(attacker)
            self.terrain_turns = terrain_turns
            extra_parts.append(f"Max Lightning tạo Electric Terrain trong {terrain_turns} lượt.")

        if move.name == "Max Mindstorm" and attacker.current_hp > 0:
            self.terrain = "psychic terrain"
            terrain_turns = self._terrain_duration(attacker)
            self.terrain_turns = terrain_turns
            extra_parts.append(f"Max Mindstorm tạo Psychic Terrain trong {terrain_turns} lượt.")

        if move.name == "Max Ooze" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "sp_attack", +1)
            if changed:
                extra_parts.append(f"Max Ooze tăng Sp. Attack của {attacker.name} {stage_text}.")

        if move.name == "Max Overgrowth" and attacker.current_hp > 0:
            self.terrain = "grassy terrain"
            terrain_turns = self._terrain_duration(attacker)
            self.terrain_turns = terrain_turns
            extra_parts.append(f"Max Overgrowth tạo Grassy Terrain trong {terrain_turns} lượt.")

        if move.name == "Max Phantasm" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "defense", -1)
            if changed:
                extra_parts.append(f"Max Phantasm làm Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Max Quake" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "sp_defense", +1)
            if changed:
                extra_parts.append(f"Max Quake tăng Sp. Defense của {attacker.name} {stage_text}.")

        if move.name == "Max Rockfall" and attacker.current_hp > 0:
            self.weather = "sandstorm"
            weather_turns = self._weather_duration(attacker, "sandstorm")
            self.weather_turns = weather_turns
            extra_parts.append(f"Max Rockfall tạo bão cát trong {weather_turns} lượt.")

        if move.name == "Max Starfall" and attacker.current_hp > 0:
            self.terrain = "misty terrain"
            terrain_turns = self._terrain_duration(attacker)
            self.terrain_turns = terrain_turns
            extra_parts.append(f"Max Starfall tạo Misty Terrain trong {terrain_turns} lượt.")

        if move.name == "Max Steelspike" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "defense", +1)
            if changed:
                extra_parts.append(f"Max Steelspike tăng Defense của {attacker.name} {stage_text}.")

        if move.name == "Max Strike" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "speed", -1)
            if changed:
                extra_parts.append(f"Max Strike làm Speed của {defender.name} giảm {stage_text}.")

        if move.name == "Max Wyrmwind" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "attack", -1)
            if changed:
                extra_parts.append(f"Max Wyrmwind làm Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Hyper Fang" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.10:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Hyperspace Fury" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "defense", -1)
            if changed:
                extra_parts.append(f"Defense của {attacker.name} giảm {stage_text}.")

        if move.name == "Ice Beam" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            defender.status = "slp"
            defender.status_counter = 1
            extra_parts.append(f"{defender.name} bị đóng băng tạm mô phỏng bằng Sleep 1 lượt.")

        if move.name == "Ice Burn" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Ice Fang" and defender.current_hp > 0:
            if not defender_blocks_additional and random.random() < 0.10:
                if defender is self.player_active:
                    self.player_flinched = True
                else:
                    self.wild_flinched = True
                extra_parts.append(f"{defender.name} bị flinch!")
            if defender.status is None and not defender_blocks_additional and random.random() < 0.10:
                defender.status = "slp"
                defender.status_counter = 1
                extra_parts.append(f"{defender.name} bị đóng băng tạm mô phỏng bằng Sleep 1 lượt.")

        if move.name == "Ice Hammer" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {attacker.name} giảm {stage_text}.")

        if move.name == "Ice Punch" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            defender.status = "slp"
            defender.status_counter = 1
            extra_parts.append(f"{defender.name} bị đóng băng tạm mô phỏng bằng Sleep 1 lượt.")

        if move.name == "Ice Spinner" and defender.current_hp > 0 and self.terrain_turns > 0:
            removed = self.terrain
            self.terrain = None
            self.terrain_turns = 0
            extra_parts.append(f"Ice Spinner xóa terrain ({removed}).")

        if move.name == "Icicle Crash" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Icy Wind" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "speed", -1)
            if changed:
                extra_parts.append(f"Speed của {defender.name} giảm {stage_text}.")

        if move.name == "Incinerate" and defender.current_hp > 0 and defender.hold_item:
            held = (defender.hold_item or "").strip().lower()
            if "berry" in held:
                removed = defender.hold_item
                defender.hold_item = None
                defender.berry_consumed = True
                extra_parts.append(f"Incinerate thiêu rụi {removed} của {defender.name}!")

        if move.name == "Infernal Parade" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Inferno" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Infestation" and defender.current_hp > 0 and not defender_blocks_additional:
            turns = random.randint(4, 5)
            applied_turns = self._apply_binding_effect(attacker, defender, turns)
            extra_parts.append(f"{defender.name} bị Infestation trói trong {applied_turns} lượt!")

        if move.name == "Heart Stamp" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Iron Head" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Iron Tail" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            changed, stage_text = self._change_stat_stage(defender, "defense", -1)
            if changed:
                extra_parts.append(f"Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Jaw Lock" and defender.current_hp > 0 and not defender_blocks_additional:
            if attacker is self.player_active:
                self.player_trapped_turns = max(self.player_trapped_turns, 4)
            else:
                self.wild_trapped_turns = max(self.wild_trapped_turns, 4)
            if defender is self.player_active:
                self.player_trapped_turns = max(self.player_trapped_turns, 4)
            else:
                self.wild_trapped_turns = max(self.wild_trapped_turns, 4)
            extra_parts.append("Jaw Lock giữ chân cả hai bên trong vài lượt.")

        if move.name == "Knock Off" and defender.current_hp > 0 and defender.hold_item:
            removed = defender.hold_item
            defender.hold_item = None
            extra_parts.append(f"Knock Off làm {defender.name} rơi mất {removed}.")

        if move.name == "Heat Wave" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name in {"High Jump Kick", "Jump Kick"} and damage == 0 and attacker.current_hp > 0:
            crash = max(1, attacker.max_hp // 2)
            attacker.current_hp = max(0, attacker.current_hp - crash)
            extra_parts.append(f"{attacker.name} chịu crash damage {crash} HP do {move.name} thất bại.")

        if move.name == "Hold Back" and damage > 0 and defender.current_hp <= 0 and type_mul != 0:
            defender.current_hp = 1
            damage = max(0, damage - 1)
            total_damage = damage
            extra_parts.append("Hold Back để lại mục tiêu còn 1 HP.")

        if move.name == "Horn Leech" and damage > 0 and attacker.current_hp > 0:
            heal = self._drain_heal_amount(attacker, max(1, damage // 2))
            if heal > 0:
                attacker.current_hp += heal
                extra_parts.append(f"{attacker.name} hồi {heal} HP nhờ Horn Leech ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Hurricane" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender.confusion_turns <= 0:
                defender.confusion_turns = random.randint(2, 5)
                extra_parts.append(f"{defender.name} bị Confusion!")

        if move.name == "Hydro Steam" and self.weather == "harsh sunlight" and self.weather_turns > 0:
            extra_parts.append("Hydro Steam được cường hóa dưới nắng gắt.")

        if move.name == "Dizzy Punch" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20:
            if defender.confusion_turns <= 0:
                defender.confusion_turns = random.randint(2, 5)
                extra_parts.append(f"{defender.name} bị Confusion!")

        if move.name == "Double Iron Bash" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Double-Edge" and damage > 0 and attacker.current_hp > 0:
            recoil = max(1, damage // 3)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} chịu phản lực {recoil} HP ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Double Shock" and attacker.current_hp > 0 and "Electric" in attacker.types:
            attacker.types = [tp for tp in attacker.types if tp != "Electric"]
            if not attacker.types:
                attacker.types = ["Normal"]
            extra_parts.append(f"{attacker.name} mất hệ Electric sau Double Shock.")

        if move.name == "Draco Meteor" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "sp_attack", -2)
            if changed:
                extra_parts.append(f"{attacker.name} giảm mạnh Sp. Attack {stage_text}.")

        if move.name == "Dragon Ascent" and attacker.current_hp > 0:
            changed_def, def_text = self._change_stat_stage(attacker, "defense", -1)
            changed_spd, spd_text = self._change_stat_stage(attacker, "sp_defense", -1)
            if changed_def:
                extra_parts.append(f"{attacker.name} giảm Defense {def_text}.")
            if changed_spd:
                extra_parts.append(f"{attacker.name} giảm Sp. Defense {spd_text}.")

        if move.name == "Dragon Rage":
            fixed = min(40, defender.current_hp + damage)
            defender.current_hp = max(0, defender.current_hp + damage - fixed)
            damage = fixed
            total_damage = damage
            extra_parts.append("Dragon Rage luôn gây đúng 40 HP (hoặc phần HP còn lại).")

        if move.name == "Sonic Boom":
            fixed = min(20, defender.current_hp + damage)
            defender.current_hp = max(0, defender.current_hp + damage - fixed)
            damage = fixed
            total_damage = damage
            extra_parts.append("Sonic Boom luôn gây đúng 20 HP (hoặc phần HP còn lại).")

        if move.name == "Spark" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Snore" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Spin Out" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "speed", -2)
            if changed:
                extra_parts.append(f"Speed của {attacker.name} giảm mạnh {stage_text}.")

        if move.name == "Spirit Break" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "sp_attack", -1)
            if changed:
                extra_parts.append(f"Sp. Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Stomp" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Stomping Tantrum" and attacker.current_hp > 0:
            extra_parts.append("Stomping Tantrum: cơ chế nhân đôi khi lượt trước thất bại được rút gọn trong engine hiện tại.")

        if move.name == "Steel Beam" and attacker.current_hp > 0:
            recoil = max(1, attacker.max_hp // 2)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} mất {recoil} HP do phản lực của Steel Beam ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Spirit Shackle" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_trapped_turns = max(self.player_trapped_turns, 4)
            else:
                self.wild_trapped_turns = max(self.wild_trapped_turns, 4)
            extra_parts.append(f"{defender.name} bị Spirit Shackle giữ chân trong vài lượt!")

        if move.name == "Soul-Stealing 7-Star Strike" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "attack", +1)
            if changed:
                extra_parts.append(f"Soul-Stealing 7-Star Strike tăng Attack của {attacker.name} {stage_text}.")

        if move.name == "Spectral Thief" and defender.current_hp > 0:
            attacker_stages = self._stat_stages_for(attacker)
            defender_stages = self._stat_stages_for(defender)
            stolen_labels: list[str] = []
            stat_labels = {
                "attack": "Attack",
                "defense": "Defense",
                "sp_attack": "Sp. Attack",
                "sp_defense": "Sp. Defense",
                "speed": "Speed",
            }
            for stat_key, label in stat_labels.items():
                positive = max(0, defender_stages.get(stat_key, 0))
                if positive <= 0:
                    continue
                attacker_stages[stat_key] = max(-6, min(6, attacker_stages.get(stat_key, 0) + positive))
                defender_stages[stat_key] = max(-6, min(6, defender_stages.get(stat_key, 0) - positive))
                stolen_labels.append(label)
            if stolen_labels:
                extra_parts.append(f"Spectral Thief cướp boost {', '.join(stolen_labels)} từ {defender.name}.")

        if move.name == "Splintered Stormshards" and attacker.current_hp > 0 and self.terrain_turns > 0:
            self.terrain = None
            self.terrain_turns = 0
            extra_parts.append("Splintered Stormshards quét sạch terrain trên sân.")

        if move.name == "Splishy Splash" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Steam Eruption" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn!")

        if move.name == "Syrup Bomb" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_syrup_bomb_turns = max(self.player_syrup_bomb_turns, 3)
            else:
                self.wild_syrup_bomb_turns = max(self.wild_syrup_bomb_turns, 3)
            extra_parts.append(f"{defender.name} bị phủ siro, Speed sẽ giảm trong 3 lượt.")

        if move.name == "Thunder" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name in {"Thunder Punch", "Thunder Shock", "Thunderbolt"} and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Thunder Fang" and defender.current_hp > 0:
            if defender.status is None and not defender_blocks_additional and random.random() < 0.10 and "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")
            if not defender_blocks_additional and random.random() < 0.10:
                if defender is self.player_active:
                    self.player_flinched = True
                else:
                    self.wild_flinched = True
                extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Thunder Cage" and defender.current_hp > 0 and not defender_blocks_additional:
            turns = random.randint(4, 5)
            applied_turns = self._apply_binding_effect(attacker, defender, turns)
            extra_parts.append(f"{defender.name} bị Thunder Cage trói trong {applied_turns} lượt!")

        if move.name == "Thundurous Kick" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "defense", -1)
            if changed:
                extra_parts.append(f"Defense của {defender.name} giảm {stage_text}.")

        if move.name == "Trailblaze" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "speed", +1)
            if changed:
                extra_parts.append(f"Speed của {attacker.name} tăng {stage_text}.")

        if move.name == "Trop Kick" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "attack", -1)
            if changed:
                extra_parts.append(f"Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Torch Song" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "sp_attack", +1)
            if changed:
                extra_parts.append(f"Sp. Attack của {attacker.name} tăng {stage_text}.")

        if move.name == "Tri Attack" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.20:
            roll = random.choice(["brn", "par", "slp"])
            if roll == "brn":
                if "Fire" not in defender.types:
                    defender.status = "brn"
                    defender.status_counter = 0
                    extra_parts.append(f"{defender.name} bị Burn!")
            elif roll == "par":
                if "Electric" not in defender.types:
                    defender.status = "par"
                    defender.status_counter = 0
                    extra_parts.append(f"{defender.name} bị Paralysis!")
            else:
                defender.status = "slp"
                defender.status_counter = 1
                extra_parts.append(f"{defender.name} bị đóng băng tạm mô phỏng bằng Sleep 1 lượt.")

        if move.name == "Thief" and defender.current_hp > 0 and not attacker.hold_item and defender.hold_item:
            attacker.hold_item = defender.hold_item
            defender.hold_item = None
            extra_parts.append(f"{attacker.name} cướp được item {attacker.hold_item} từ {defender.name}.")

        if move.name == "Thousand Waves" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_trapped_turns = max(self.player_trapped_turns, 999)
            else:
                self.wild_trapped_turns = max(self.wild_trapped_turns, 999)
            extra_parts.append(f"{defender.name} bị Thousand Waves giữ chân, không thể đổi ra.")

        if move.name == "Thousand Arrows" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_smack_down_grounded = True
                self.player_magnet_rise_turns = 0
            else:
                self.wild_smack_down_grounded = True
                self.wild_magnet_rise_turns = 0
            extra_parts.append(f"Thousand Arrows kéo {defender.name} xuống đất.")

        if move.name == "Throat Chop" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_throat_chop_turns = max(self.player_throat_chop_turns, 2)
            else:
                self.wild_throat_chop_turns = max(self.wild_throat_chop_turns, 2)
            extra_parts.append(f"{defender.name} bị Throat Chop khóa chiêu âm thanh trong 2 lượt.")

        if move.name == "Thrash" and attacker.current_hp > 0:
            if attacker is self.player_active:
                if self.player_outrage_turns <= 0:
                    self.player_outrage_turns = random.randint(2, 3)
                self.player_outrage_turns -= 1
                if self.player_outrage_turns <= 0 and attacker.confusion_turns <= 0:
                    attacker.confusion_turns = random.randint(2, 5)
                    extra_parts.append(f"{attacker.name} rơi vào Confusion sau Thrash!")
            else:
                if self.wild_outrage_turns <= 0:
                    self.wild_outrage_turns = random.randint(2, 3)
                self.wild_outrage_turns -= 1
                if self.wild_outrage_turns <= 0 and attacker.confusion_turns <= 0:
                    attacker.confusion_turns = random.randint(2, 5)
                    extra_parts.append(f"{attacker.name} rơi vào Confusion sau Thrash!")

        if move.name == "Triple Arrows" and defender.current_hp > 0 and not defender_blocks_additional:
            if random.random() < 0.50:
                changed, stage_text = self._change_stat_stage(defender, "defense", -1)
                if changed:
                    extra_parts.append(f"Defense của {defender.name} giảm {stage_text}.")
            elif random.random() < 0.30:
                if defender is self.player_active:
                    self.player_flinched = True
                else:
                    self.wild_flinched = True
                extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Twineedle" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.20:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison!")

        if move.name == "Twister" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "U-turn" and attacker.current_hp > 0:
            if attacker is self.player_active:
                options = [
                    (idx, pkmn)
                    for idx, pkmn in enumerate(self.player.party)
                    if idx != self.player_active_index and pkmn.current_hp > 0
                ]
                if options:
                    next_index, next_pokemon = options[0]
                    self.booster_energy_boost_stat.pop(id(self.player_active), None)
                    self.player_seeded = False
                    self.player_aqua_ring = False
                    self.player_trapped_turns = 0
                    self.player_bound_turns = 0
                    self.player_flinched = False
                    self.player_last_move_name = None
                    self.player_active_index = next_index
                    self.player_yawn_turns = 0
                    self.player_infatuated = False
                    self.wild_infatuated = False
                    hazard_logs = self._apply_switch_in_hazards(next_pokemon, is_player=True)
                    ability_logs = self._trigger_switch_in_ability(next_pokemon, is_player=True)
                    extra_parts.append(f"{attacker.name} rút lui sau U-turn! Bạn đổi sang {next_pokemon.name}.")
                    if hazard_logs:
                        extra_parts.extend(hazard_logs)
                    if ability_logs:
                        extra_parts.extend(ability_logs)
            else:
                extra_parts.append("U-turn của wild không đổi được Pokémon vì không có party dự bị.")

        if move.name == "Volt Switch" and attacker.current_hp > 0:
            if attacker is self.player_active:
                options = [
                    (idx, pkmn)
                    for idx, pkmn in enumerate(self.player.party)
                    if idx != self.player_active_index and pkmn.current_hp > 0
                ]
                if options:
                    next_index, next_pokemon = options[0]
                    self.booster_energy_boost_stat.pop(id(self.player_active), None)
                    self.player_seeded = False
                    self.player_aqua_ring = False
                    self.player_trapped_turns = 0
                    self.player_bound_turns = 0
                    self.player_flinched = False
                    self.player_last_move_name = None
                    self.player_active_index = next_index
                    self.player_yawn_turns = 0
                    self.player_infatuated = False
                    self.wild_infatuated = False
                    hazard_logs = self._apply_switch_in_hazards(next_pokemon, is_player=True)
                    ability_logs = self._trigger_switch_in_ability(next_pokemon, is_player=True)
                    extra_parts.append(f"{attacker.name} rút lui sau Volt Switch! Bạn đổi sang {next_pokemon.name}.")
                    if hazard_logs:
                        extra_parts.extend(hazard_logs)
                    if ability_logs:
                        extra_parts.extend(ability_logs)
            else:
                extra_parts.append("Volt Switch của wild không đổi được Pokémon vì không có party dự bị.")

        if move.name == "Uproar" and attacker.current_hp > 0:
            if attacker is self.player_active:
                self.player_uproar_turns = max(self.player_uproar_turns, 3)
            else:
                self.wild_uproar_turns = max(self.wild_uproar_turns, 3)
            if self.player_active.status == "slp":
                self.player_active.status = None
                self.player_active.status_counter = 0
            if self.wild.status == "slp":
                self.wild.status = None
                self.wild.status_counter = 0
            extra_parts.append("Uproar khiến mọi Pokémon tỉnh giấc và tạm thời không thể ngủ.")

        if move.name == "V-create" and attacker.current_hp > 0:
            changed_def, def_text = self._change_stat_stage(attacker, "defense", -1)
            changed_spd, spd_text = self._change_stat_stage(attacker, "sp_defense", -1)
            changed_spe, spe_text = self._change_stat_stage(attacker, "speed", -1)
            if changed_def:
                extra_parts.append(f"Defense của {attacker.name} giảm {def_text}.")
            if changed_spd:
                extra_parts.append(f"Sp. Defense của {attacker.name} giảm {spd_text}.")
            if changed_spe:
                extra_parts.append(f"Speed của {attacker.name} giảm {spe_text}.")

        if move.name == "Wake-Up Slap" and damage > 0 and defender.status == "slp":
            defender.status = None
            defender.status_counter = 0
            extra_parts.append(f"{defender.name} tỉnh giấc sau Wake-Up Slap!")

        if move.name == "Water Pulse" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20 and defender.confusion_turns <= 0:
            defender.confusion_turns = random.randint(2, 5)
            extra_parts.append(f"{defender.name} bị Confusion!")

        if move.name == "Waterfall" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Whirlpool" and defender.current_hp > 0 and not defender_blocks_additional:
            turns = random.randint(4, 5)
            applied_turns = self._apply_binding_effect(attacker, defender, turns)
            extra_parts.append(f"{defender.name} bị Whirlpool trói trong {applied_turns} lượt!")

        if move.name == "Wrap" and defender.current_hp > 0 and not defender_blocks_additional:
            turns = random.randint(4, 5)
            applied_turns = self._apply_binding_effect(attacker, defender, turns)
            extra_parts.append(f"{defender.name} bị Wrap trói trong {applied_turns} lượt!")

        if move.name == "Wicked Torque" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.10:
            defender.status = "slp"
            defender.status_counter = random.randint(1, 3)
            extra_parts.append(f"{defender.name} bị Sleep!")

        if move.name == "Wildbolt Storm" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.20:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Zap Cannon" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis!")

        if move.name == "Zen Headbutt" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Zing Zap" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Water Pledge" and defender.current_hp > 0:
            extra_parts.append("Water Pledge: hiệu ứng combo với Fire/Grass Pledge chưa áp dụng trong battle 1v1 hiện tại.")

        if move.name in {"Water Gun", "Wing Attack", "X-Scissor"} and defender.current_hp > 0:
            extra_parts.append(f"{move.name} gây sát thương chuẩn (không có hiệu ứng phụ).")

        if move.name == "Steamroller" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            if defender is self.player_active:
                self.player_flinched = True
            else:
                self.wild_flinched = True
            extra_parts.append(f"{defender.name} bị flinch!")

        if move.name == "Steel Wing" and attacker.current_hp > 0 and random.random() < 0.10:
            changed, stage_text = self._change_stat_stage(attacker, "defense", +1)
            if changed:
                extra_parts.append(f"Defense của {attacker.name} tăng {stage_text}.")

        if move.name == "Stone Axe" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                if not self.player_stealth_rock:
                    self.player_stealth_rock = True
                    extra_parts.append(f"Stone Axe dựng Stealth Rock phía {defender.name}.")
            else:
                if not self.wild_stealth_rock:
                    self.wild_stealth_rock = True
                    extra_parts.append(f"Stone Axe dựng Stealth Rock phía {defender.name}.")

        if move.name == "Strange Steam" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.20:
            if defender.confusion_turns <= 0:
                defender.confusion_turns = random.randint(2, 5)
                extra_parts.append(f"{defender.name} bị Confusion!")

        if move.name == "Springtide Storm" and defender.current_hp > 0 and not defender_blocks_additional and random.random() < 0.30:
            changed, stage_text = self._change_stat_stage(defender, "attack", -1)
            if changed:
                extra_parts.append(f"Springtide Storm làm Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Stoked Sparksurfer" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis bởi Stoked Sparksurfer!")

        if move.name == "Sparkling Aria" and defender.current_hp > 0 and defender.status == "brn":
            defender.status = None
            defender.status_counter = 0
            extra_parts.append(f"Sparkling Aria chữa Burn cho {defender.name}.")

        if move.name == "Strength" and defender.current_hp > 0:
            extra_parts.append("Strength gây sát thương chuẩn (không có hiệu ứng phụ trong battle).")

        if move.name == "Dragon Tail" and defender is self.wild and defender.current_hp > 0:
            extra_parts.append("Dragon Tail: hiệu ứng ép đổi mục tiêu không áp dụng trong wild 1v1.")

        if move.name == "Drain Punch" and damage > 0 and attacker.current_hp > 0:
            heal = self._drain_heal_amount(attacker, max(1, damage // 2))
            if heal > 0:
                attacker.current_hp += heal
                extra_parts.append(f"{attacker.name} hồi {heal} HP nhờ Drain Punch ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Draining Kiss" and damage > 0 and attacker.current_hp > 0:
            heal = self._drain_heal_amount(attacker, max(1, (damage * 3) // 4))
            if heal > 0:
                attacker.current_hp += heal
                extra_parts.append(f"{attacker.name} hồi {heal} HP nhờ Draining Kiss ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Dream Eater" and defender.status != "slp":
            defender.current_hp = min(defender.max_hp, defender.current_hp + damage)
            damage = 0
            extra_parts.append("Dream Eater thất bại vì mục tiêu không ngủ.")
        elif move.name == "Dream Eater" and damage > 0 and attacker.current_hp > 0:
            heal = self._drain_heal_amount(attacker, max(1, damage // 2))
            if heal > 0:
                attacker.current_hp += heal
                extra_parts.append(f"{attacker.name} hồi {heal} HP nhờ Dream Eater ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Core Enforcer" and defender.current_hp > 0:
            target_moved_already = (
                (defender is self.player_active and self.player_acted_before_wild)
                or (defender is self.wild and self.wild_acted_before_player)
            )
            if target_moved_already and defender.ability:
                defender.ability = ""
                extra_parts.append(f"Core Enforcer vô hiệu hóa Ability của {defender.name} trong trận này.")

        if move.name == "Corrosive Gas" and defender.current_hp > 0 and defender.hold_item and not defender_blocks_additional:
            removed = defender.hold_item
            defender.hold_item = None
            extra_parts.append(f"Corrosive Gas làm {defender.name} rơi mất {removed}.")

        if move.name == "Covet" and defender.current_hp > 0 and not attacker.hold_item and defender.hold_item:
            attacker.hold_item = defender.hold_item
            defender.hold_item = None
            extra_parts.append(f"{attacker.name} cướp được item {attacker.hold_item} từ {defender.name}.")

        if move.name == "Burn Up" and attacker.current_hp > 0 and "Fire" in attacker.types:
            attacker.types = [tp for tp in attacker.types if tp != "Fire"]
            if not attacker.types:
                attacker.types = ["Normal"]
            extra_parts.append(f"{attacker.name} mất hệ Fire sau khi dùng Burn Up.")

        if move.name == "Burning Jealousy" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            stages = self._stat_stages_for(defender)
            if any(value > 0 for value in stages.values()) and "Fire" not in defender.types:
                defender.status = "brn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Burn do Burning Jealousy khi đang được tăng chỉ số!")

        if move.name == "Ceaseless Edge" and attacker.current_hp > 0:
            if attacker is self.player_active:
                if self.wild_spikes_layers < 3:
                    self.wild_spikes_layers += 1
                    extra_parts.append(f"Ceaseless Edge rải thêm 1 lớp Spikes phía đối thủ ({self.wild_spikes_layers}/3).")
            else:
                if self.player_spikes_layers < 3:
                    self.player_spikes_layers += 1
                    extra_parts.append(f"Ceaseless Edge rải thêm 1 lớp Spikes phía bạn ({self.player_spikes_layers}/3).")

        if move.name == "Catastropika" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional:
            if "Electric" not in defender.types:
                defender.status = "par"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Paralysis bởi Catastropika!")

        if move.name == "Chatter" and defender.current_hp > 0 and defender.confusion_turns <= 0 and not defender_blocks_additional:
            defender.confusion_turns = random.randint(2, 5)
            extra_parts.append(f"{defender.name} bị Confusion!")

        if move.name == "Chilling Water" and defender.current_hp > 0 and not defender_blocks_additional:
            changed, stage_text = self._change_stat_stage(defender, "attack", -1)
            if changed:
                extra_parts.append(f"Attack của {defender.name} giảm {stage_text}.")

        if move.name == "Chip Away" and defender.current_hp > 0:
            extra_parts.append("Chip Away bỏ qua modifier chỉ số của mục tiêu (mô phỏng cơ bản).")

        if move.name == "Chloroblast" and attacker.current_hp > 0:
            recoil = max(1, attacker.max_hp // 2)
            attacker.current_hp = max(0, attacker.current_hp - recoil)
            extra_parts.append(f"{attacker.name} chịu phản lực {recoil} HP ({attacker.current_hp}/{attacker.max_hp}).")

        if move.name == "Circle Throw" and defender is self.wild and defender.current_hp > 0:
            defender.current_hp = 0
            extra_parts.append(f"{defender.name} bị Circle Throw đuổi khỏi trận đấu hoang dã!")

        if move.name == "Clamp" and defender.current_hp > 0 and not defender_blocks_additional:
            turns = random.randint(4, 5)
            applied_turns = self._apply_binding_effect(attacker, defender, turns)
            extra_parts.append(f"{defender.name} bị Clamp trong {applied_turns} lượt!")

        if move.name == "Clanging Scales" and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "defense", -1)
            if changed:
                extra_parts.append(f"{attacker.name} giảm Defense {stage_text}.")

        if move.name == "Clangorous Soulblaze" and attacker.current_hp > 0:
            boosted: list[str] = []
            for stat_key, label in [
                ("attack", "Attack"),
                ("defense", "Defense"),
                ("sp_attack", "Sp. Attack"),
                ("sp_defense", "Sp. Defense"),
                ("speed", "Speed"),
            ]:
                changed, _ = self._change_stat_stage(attacker, stat_key, +1)
                if changed:
                    boosted.append(label)
            if boosted:
                extra_parts.append(f"Clangorous Soulblaze tăng {', '.join(boosted)} cho {attacker.name}.")

        if move.name == "Clear Smog" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_stat_stages = {"attack": 0, "defense": 0, "sp_attack": 0, "sp_defense": 0, "speed": 0}
            else:
                self.wild_stat_stages = {"attack": 0, "defense": 0, "sp_attack": 0, "sp_defense": 0, "speed": 0}
            extra_parts.append(f"Clear Smog xóa toàn bộ thay đổi chỉ số của {defender.name}.")

        if move.name == "Close Combat" and attacker.current_hp > 0:
            changed_def, def_text = self._change_stat_stage(attacker, "defense", -1)
            changed_spd, spd_text = self._change_stat_stage(attacker, "sp_defense", -1)
            if changed_def:
                extra_parts.append(f"{attacker.name} giảm Defense {def_text}.")
            if changed_spd:
                extra_parts.append(f"{attacker.name} giảm Sp. Defense {spd_text}.")

        if move.name == "Barb Barrage" and defender.current_hp > 0 and defender.status is None and not defender_blocks_additional and random.random() < 0.30:
            if "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
                defender.status = "psn"
                defender.status_counter = 0
                extra_parts.append(f"{defender.name} bị Poison bởi Barb Barrage!")

        if move.name == "Anchor Shot" and defender.current_hp > 0 and not defender_blocks_additional:
            if defender is self.player_active:
                self.player_trapped_turns = max(self.player_trapped_turns, 4)
            else:
                self.wild_trapped_turns = max(self.wild_trapped_turns, 4)
            extra_parts.append(f"{defender.name} bị Anchor Shot giữ chân trong vài lượt!")

        if move.name == "False Swipe" and defender.current_hp == 1 and damage > 0:
            extra_parts.append("False Swipe để lại mục tiêu còn 1 HP.")

        if move.name == "Fell Stinger" and defender.current_hp <= 0 and attacker.current_hp > 0:
            changed, stage_text = self._change_stat_stage(attacker, "attack", +3)
            if changed:
                extra_parts.append(f"Fell Stinger kích hoạt! Attack của {attacker.name} tăng mạnh {stage_text}.")

        if move.name == "Explosion" and attacker.current_hp > 0:
            attacker.current_hp = 0
            extra_parts.append(f"{attacker.name} phát nổ và gục xuống!")

        if move.name == "Self-Destruct" and attacker.current_hp > 0:
            attacker.current_hp = 0
            extra_parts.append(f"{attacker.name} tự hủy và gục xuống!")

        if damage > 0 and attacker.current_hp > 0 and defender.current_hp > 0:
            defender_item_reactive = self._held_item_name(defender)

            on_hit_boost_items: dict[str, tuple[str, str, str]] = {
                "absorb bulb": ("Water", "sp_attack", "Absorb Bulb"),
                "luminous moss": ("Water", "sp_defense", "Luminous Moss"),
                "cell battery": ("Electric", "attack", "Cell Battery"),
                "snowball": ("Ice", "attack", "Snowball"),
            }
            boost_trigger = on_hit_boost_items.get(defender_item_reactive)
            if boost_trigger and move.move_type == boost_trigger[0]:
                changed, stage_text = self._change_stat_stage(defender, boost_trigger[1], +1)
                if changed:
                    defender.hold_item = None
                    stat_label = {
                        "attack": "Attack",
                        "sp_attack": "Sp. Attack",
                        "sp_defense": "Sp. Defense",
                    }.get(boost_trigger[1], boost_trigger[1])
                    extra_parts.append(
                        f"{defender.name} kích hoạt {boost_trigger[2]}! {stat_label} tăng {stage_text}."
                    )

            berry_hit_triggers: dict[str, tuple[str, str]] = {
                "kee berry": ("Physical", "defense"),
                "maranga berry": ("Special", "sp_defense"),
            }
            berry_hit_trigger = berry_hit_triggers.get(defender_item_reactive)
            if berry_hit_trigger and move.category == berry_hit_trigger[0]:
                changed, stage_text = self._change_stat_stage(defender, berry_hit_trigger[1], +1)
                if changed:
                    defender.hold_item = None
                    defender.berry_consumed = True
                    stat_label = "Defense" if berry_hit_trigger[1] == "defense" else "Sp. Defense"
                    berry_label = "Kee Berry" if defender_item_reactive == "kee berry" else "Maranga Berry"
                    extra_parts.append(
                        f"{defender.name} ăn {berry_label}! {stat_label} tăng {stage_text}."
                    )

            if defender_item_reactive == "enigma berry" and type_mul > 1.0:
                heal = min(max(1, defender.max_hp // 4), defender.max_hp - defender.current_hp)
                if heal > 0:
                    defender.current_hp += heal
                    defender.hold_item = None
                    defender.berry_consumed = True
                    extra_parts.append(
                        f"{defender.name} ăn Enigma Berry và hồi {heal} HP ({defender.current_hp}/{defender.max_hp})."
                    )

            if defender_item_reactive == "jaboca berry" and move.category == "Physical" and attacker.current_hp > 0:
                backlash = max(1, attacker.max_hp // 8)
                attacker.current_hp = max(0, attacker.current_hp - backlash)
                defender.hold_item = None
                defender.berry_consumed = True
                extra_parts.append(
                    f"{defender.name} ăn Jaboca Berry! {attacker.name} chịu {backlash} sát thương phản đòn."
                )
            elif defender_item_reactive == "rowap berry" and move.category == "Special" and attacker.current_hp > 0:
                backlash = max(1, attacker.max_hp // 8)
                attacker.current_hp = max(0, attacker.current_hp - backlash)
                defender.hold_item = None
                defender.berry_consumed = True
                extra_parts.append(
                    f"{defender.name} ăn Rowap Berry! {attacker.name} chịu {backlash} sát thương phản đòn."
                )

            if defender_item_reactive == "red card" and attacker is self.player_active:
                forced_switch_text = self._force_switch_player()
                if forced_switch_text:
                    defender.hold_item = None
                    extra_parts.append(f"{defender.name} kích hoạt Red Card! {forced_switch_text}")
            elif defender_item_reactive == "eject button" and defender is self.player_active:
                forced_switch_text = self._force_switch_player()
                if forced_switch_text:
                    defender.hold_item = None
                    extra_parts.append(f"{defender.name} kích hoạt Eject Button! {forced_switch_text}")

        text = (
            f"{attacker.name} dùng {move.name} gây {damage} sát thương lên {defender.name}."
            f" {defender.name}: {defender.current_hp}/{defender.max_hp} HP.{effect_text}"
        )
        if extra_parts:
            text = text + "\n" + " ".join(extra_parts)
        if contact_burn_text:
            text = text + "\n" + contact_burn_text.strip()

        if defender.current_hp <= 0:
            defender_grudge = (
                (defender is self.player_active and self.player_grudge_active)
                or (defender is self.wild and self.wild_grudge_active)
            )
            if defender_grudge:
                move.current_pp = 0
                text += f"\nGrudge kích hoạt! PP của {move.name} giảm về 0."
            defender_destiny = (
                (defender is self.player_active and self.player_destiny_bond_active)
                or (defender is self.wild and self.wild_destiny_bond_active)
            )
            if defender_destiny and attacker.current_hp > 0:
                attacker.current_hp = 0
                text += f"\n{defender.name} kéo theo {attacker.name} bằng Destiny Bond!"
        return text

    def _auto_switch_player(self) -> str | None:
        old_active = self.player_active
        self.booster_energy_boost_stat.pop(id(old_active), None)
        if old_active.status == "tox":
            old_active.status_counter = 1
        for i, pkmn in enumerate(self.player.party):
            if pkmn.current_hp > 0:
                self._reset_player_stages()
                self.player_seeded = False
                self.player_ingrain = False
                self.player_aqua_ring = False
                self.player_trapped_turns = 0
                self.player_bound_turns = 0
                self.player_flinched = False
                self.player_bounce_charging = False
                self.player_dig_charging = False
                self.player_dive_charging = False
                self.player_fly_charging = False
                self.player_freeze_shock_charging = False
                self.player_destiny_bond_active = False
                self.player_cursed = False
                self.player_focus_energy = False
                self.player_identified = False
                self.player_fury_cutter_chain = 0
                self.player_geomancy_charging = False
                self.player_glaive_rush_vulnerable_turns = 0
                self.player_ice_burn_charging = False
                self.player_ice_ball_chain = 0
                self.player_rollout_chain = 0
                self.player_electrified = False
                self.player_electro_shot_charging = False
                self.player_endure_active = False
                self.player_encore_turns = 0
                self.player_encore_move = None
                self.wild_imprisoned_moves = set()
                self.player_heal_block_turns = 0
                self.player_salt_cure_turns = 0
                self.player_syrup_bomb_turns = 0
                self.player_stockpile_count = 0
                self.player_taunt_turns = 0
                self.player_throat_chop_turns = 0
                self.player_torment_turns = 0
                self.player_tar_shot = False
                self.player_sky_attack_charging = False
                self.player_skull_bash_charging = False
                self.player_sky_drop_charging = False
                self.player_solar_beam_charging = False
                self.player_solar_blade_charging = False
                self.player_last_move_name = None
                self.player_roost_original_types = None
                self.player_smack_down_grounded = False
                self.player_choice_lock_move = None
                self.player_micle_accuracy_boost = False
                self.player_lansat_crit_boost = False
                self.player_yawn_turns = 0
                self.player_retaliate_ready = True
                self.player_active_index = i
                self.player_infatuated = False
                self.wild_infatuated = False
                hazard_logs = self._apply_switch_in_hazards(pkmn, is_player=True)
                ability_logs = self._trigger_switch_in_ability(pkmn, is_player=True)
                wish_logs = self._apply_healing_wish_on_switch_in(pkmn, is_player=True)
                base = f"Bạn tự động đổi sang {pkmn.name}."
                if hazard_logs:
                    base = base + "\n" + "\n".join(hazard_logs)
                if ability_logs:
                    base = base + "\n" + "\n".join(ability_logs)
                if wish_logs:
                    base = base + "\n" + "\n".join(wish_logs)
                return base
        return None

    def _force_switch_player(self) -> str | None:
        options = [
            idx
            for idx, pkmn in enumerate(self.player.party)
            if idx != self.player_active_index and pkmn.current_hp > 0
        ]
        if not options:
            return None

        new_index = random.choice(options)
        saved_trapped = self.player_trapped_turns
        saved_ingrain = self.player_ingrain
        self.player_trapped_turns = 0
        self.player_ingrain = False
        result = self.switch_pokemon(new_index)
        if result.success:
            return result.text

        self.player_trapped_turns = saved_trapped
        self.player_ingrain = saved_ingrain
        return None

    def _run_turn_zero_phase(self) -> str:
        logs: list[str] = ["--- Turn 0 ---", f"Bạn tung ra {self.player_active.name}!", f"Pokémon hoang dã {self.wild.name} xuất hiện!"]

        player_speed = self._effective_stat(self.player_active, "speed")
        wild_speed = self._effective_stat(self.wild, "speed")
        order: list[tuple[PokemonInstance, bool]]
        if player_speed > wild_speed:
            order = [(self.player_active, True), (self.wild, False)]
        elif wild_speed > player_speed:
            order = [(self.wild, False), (self.player_active, True)]
        else:
            if random.random() < 0.5:
                order = [(self.player_active, True), (self.wild, False)]
            else:
                order = [(self.wild, False), (self.player_active, True)]

        for pokemon, is_player in order:
            logs.extend(self._trigger_switch_in_ability(pokemon, is_player=is_player))

        return "\n".join(logs)

    def consume_pending_battle_log(self) -> str:
        text = self.pending_battle_log
        self.pending_battle_log = ""
        return text

    def _apply_healing_wish_on_switch_in(self, pokemon: PokemonInstance, is_player: bool) -> list[str]:
        logs: list[str] = []
        if is_player:
            if not getattr(self, "player_healing_wish_pending", False):
                return logs
            self.player_healing_wish_pending = False
        else:
            if not getattr(self, "wild_healing_wish_pending", False):
                return logs
            self.wild_healing_wish_pending = False

        before_hp = pokemon.current_hp
        pokemon.current_hp = pokemon.max_hp
        pokemon.status = None
        pokemon.status_counter = 0
        pokemon.confusion_turns = 0
        healed = pokemon.current_hp - before_hp
        logs.append(f"Healing Wish hồi {healed} HP và chữa mọi trạng thái cho {pokemon.name}.")
        return logs

    def _trigger_switch_in_ability(self, pokemon: PokemonInstance, is_player: bool) -> list[str]:
        logs: list[str] = []
        ability = (pokemon.ability or "").strip()
        target = self.wild if is_player else self.player_active

        if ability:
            if ability == "Intimidate":
                if self._held_item_name(target) == "clear amulet":
                    logs.append(f"{pokemon.name} kích hoạt Intimidate, nhưng {target.name} được Clear Amulet bảo vệ!")
                else:
                    changed, stage_text = self._change_stat_stage(target, "attack", -1)
                    if changed:
                        logs.append(f"{pokemon.name} kích hoạt Intimidate! {target.name} giảm Attack {stage_text}.")
                        if self._held_item_name(target) == "adrenaline orb":
                            changed_speed, speed_text = self._change_stat_stage(target, "speed", +1)
                            if changed_speed:
                                target.hold_item = None
                                logs.append(f"{target.name} kích hoạt Adrenaline Orb! Speed tăng {speed_text}.")
                    else:
                        logs.append(f"{pokemon.name} kích hoạt Intimidate, nhưng Attack của {target.name} không thể giảm thêm.")

            weather_map = {
                "Drought": ("harsh sunlight", "heat rock"),
                "Drizzle": ("rain", "damp rock"),
                "Sand Stream": ("sandstorm", "smooth rock"),
                "Snow Warning": ("snow", "icy rock"),
            }
            if ability in weather_map:
                weather_name, _ = weather_map[ability]
                duration = self._weather_duration(pokemon, weather_name)
                self.weather = weather_name
                self.weather_turns = duration
                logs.append(
                    f"{pokemon.name} kích hoạt {ability}! Thời tiết chuyển thành {self.weather} trong {duration} lượt."
                )

            booster_log = self._try_activate_booster_energy(pokemon)
            if booster_log:
                logs.append(booster_log)

        seed_log = self._try_activate_terrain_seed(pokemon)
        if seed_log:
            logs.append(seed_log)

        return logs

    def _reset_player_stages(self) -> None:
        self.player_stat_stages = {
            "attack": 0,
            "defense": 0,
            "sp_attack": 0,
            "sp_defense": 0,
            "speed": 0,
        }

    def _catch_chance(self, ball_name: str) -> float:
        return calculate_catch_chance(self, ball_name)

    def _grant_victory_rewards(self, winner: PokemonInstance, logs: list[str]) -> None:
        if self._victory_rewards_granted:
            return

        base_exp = self._calculate_exp_reward(self.wild)
        exp_gain = max(1, int(round(base_exp * getattr(self, "exp_multiplier", 1.0))))
        base_money = max(0, 5 * self.wild.level)
        money_gain = max(0, int(round(base_money * getattr(self, "money_multiplier", 1.0))))
        winner_item = self._held_item_name(winner)
        if winner_item in {"amulet coin", "luck incense"}:
            money_gain *= 2
        if getattr(self, "player_happy_hour_active", False):
            money_gain *= 2
        pay_day_gain = 0
        if getattr(self, "money_multiplier", 1.0) > 0:
            pay_day_gain = max(0, int(getattr(self, "pay_day_bonus", 0)))
        money_gain += pay_day_gain
        self.pay_day_bonus = 0

        winner.exp += exp_gain
        battle_happiness_gain = add_happiness(winner, 3)
        ev_logs = self._grant_ev_rewards(winner)
        self.player.money += money_gain

        logs.append(f"{winner.name} nhận {exp_gain} EXP.")
        if battle_happiness_gain > 0:
            logs.append(f"{winner.name} tăng {battle_happiness_gain} Happiness sau trận đấu.")
        logs.extend(ev_logs)
        logs.extend(self._apply_level_up_progression(winner))
        logs.append(
            f"EXP hiện tại: {winner.exp} (cần {winner.exp_to_next_level()} EXP để lên level tiếp theo)."
        )
        logs.append(f"Bạn nhận {money_gain} PokéDollars.")
        if pay_day_gain > 0:
            logs.append(f"Trong đó có {pay_day_gain} PokéDollars từ Pay Day.")
        self._victory_rewards_granted = True

    def _grant_ev_rewards(self, winner: PokemonInstance) -> list[str]:
        defeated_species = get_species_by_id(self.game_data, getattr(self.wild, "species_id", -1))
        ev_stat, ev_amount = derive_ev_yield_from_species(defeated_species)
        gained = award_evs(winner, ev_stat, ev_amount)
        if gained <= 0:
            return []
        recalculate_pokemon_stats(self.game_data, winner, preserve_current_hp_ratio=True)
        return [f"{winner.name} nhận {gained} EV vào {ev_stat}."]

    def _apply_level_up_progression(self, pokemon: PokemonInstance) -> list[str]:
        logs: list[str] = []
        levels_gained = 0
        happiness_total = 0

        while pokemon.level < 100 and pokemon.exp >= PokemonInstance.exp_for_level(pokemon.level + 1):
            pokemon.level += 1
            levels_gained += 1
            recalculate_pokemon_stats(self.game_data, pokemon, preserve_current_hp_ratio=True)
            happiness_total += add_happiness(pokemon, 15)

        if levels_gained > 0:
            logs.append(f"{pokemon.name} đã lên Lv.{pokemon.level} (+{levels_gained} cấp).")
            if happiness_total > 0:
                logs.append(f"{pokemon.name} tăng thêm {happiness_total} Happiness do lên cấp.")

        return logs

    def _derived_base_exp_yield(self, defeated: PokemonInstance) -> int:
        stat_total = (
            defeated.max_hp
            + defeated.attack
            + defeated.defense
            + defeated.sp_attack
            + defeated.sp_defense
            + defeated.speed
        )
        return max(20, min(300, int(round(stat_total * 0.20))))

    def _calculate_exp_reward(self, defeated: PokemonInstance) -> int:
        defeated_level = max(1, int(defeated.level))
        winner_level = max(1, int(self.player_active.level))

        if getattr(self, "opponent_exp_coefficient", None) is not None:
            a = max(0.0, float(self.opponent_exp_coefficient))
        else:
            a = 1.5 if getattr(self, "opponent_is_trainer", False) else 1.0
        b = float(self._derived_base_exp_yield(defeated))
        s = 1.0

        ratio = ((2 * defeated_level + 10) / (defeated_level + winner_level + 10)) ** 2.5
        core = ((a * b * defeated_level) / (5.0 * s)) * ratio + 1.0

        outsider = (
            self.player_active.owner_id is not None
            and self.player_active.owner_id != self.player.user_id
        )
        t = 1.5 if outsider else 1.0

        held_item = (self.player_active.hold_item or "").strip().lower()
        e = 1.5 if held_item == "lucky egg" else 1.0

        v = 1.0
        f = 1.0
        p = 1.0

        total = core * t * e * v * f * p
        return max(1, int(math.floor(total)))

    def _normalize_move_pp(self, move: MoveSet) -> None:
        if move.base_pp <= 0 and move.max_pp > 0:
            move.base_pp = max(1, move.max_pp)
        if move.base_pp <= 0:
            move.base_pp = 1
        move.pp_up_level = max(0, min(3, getattr(move, "pp_up_level", 0)))
        target_max_pp = _max_pp_from_stage(move.base_pp, move.pp_up_level)
        move.max_pp = target_max_pp
        if move.current_pp <= 0 and move.current_pp != 0:
            move.current_pp = move.max_pp
        if move.current_pp > move.max_pp:
            move.current_pp = move.max_pp
        if move.current_pp < 0:
            move.current_pp = 0

    def _apply_pp_item(self, pokemon: PokemonInstance, item_name: str) -> tuple[bool, str]:
        return apply_pp_item_for_pokemon(
            pokemon,
            item_name,
            max_pp_from_stage=_max_pp_from_stage,
        )

    def _stat_stages_for(self, pokemon: PokemonInstance) -> dict[str, int]:
        if pokemon is self.player_active:
            return self.player_stat_stages
        return self.wild_stat_stages

    def _effective_stat(self, pokemon: PokemonInstance, stat_key: str) -> int:
        if getattr(self, "wonder_room_turns", 0) > 0:
            if stat_key == "defense":
                stat_key = "sp_defense"
            elif stat_key == "sp_defense":
                stat_key = "defense"
        base_value = int(getattr(pokemon, stat_key))
        stage = self._stat_stages_for(pokemon).get(stat_key, 0)
        value = max(1, int(base_value * _stage_multiplier(stage)))
        if stat_key == "speed":
            if pokemon is self.player_active and getattr(self, "player_tailwind_turns", 0) > 0:
                value = max(1, int(value * 2))
            if pokemon is self.wild and getattr(self, "wild_tailwind_turns", 0) > 0:
                value = max(1, int(value * 2))
        if self.weather == "snow" and self.weather_turns > 0 and stat_key == "defense" and "Ice" in pokemon.types:
            value = max(1, int(value * 1.5))
        if pokemon.status == "par" and stat_key == "speed":
            value = max(1, int(value * 0.5))
        if pokemon.ability == "Guts" and stat_key == "attack" and pokemon.status is not None:
            value = max(1, int(value * 1.5))

        held_item = self._held_item_name(pokemon)
        value = apply_held_item_stat_modifiers(
            value,
            stat_key=stat_key,
            held_item_name=held_item,
            pokemon_name=pokemon.name,
            can_still_evolve=self._can_still_evolve(pokemon),
        )

        boost_stat = self._ability_field_boost_stat(pokemon)
        if boost_stat is None:
            boost_stat = self.booster_energy_boost_stat.get(id(pokemon))
        if boost_stat == stat_key:
            value = max(1, int(value * (1.5 if stat_key == "speed" else 1.3)))
        return value

    def _is_grounded(self, pokemon: PokemonInstance) -> bool:
        if getattr(self, "gravity_turns", 0) > 0:
            return True
        if self._held_item_name(pokemon) == "iron ball":
            return True
        if pokemon is self.player_active and getattr(self, "player_magnet_rise_turns", 0) > 0:
            return False
        if pokemon is self.wild and getattr(self, "wild_magnet_rise_turns", 0) > 0:
            return False
        if pokemon is self.player_active and getattr(self, "player_smack_down_grounded", False):
            return True
        if pokemon is self.wild and getattr(self, "wild_smack_down_grounded", False):
            return True
        if self._held_item_name(pokemon) == "air balloon":
            return False
        if pokemon.ability == "Levitate":
            return False
        return "Flying" not in pokemon.types

    def _change_stat_stage(self, pokemon: PokemonInstance, stat_key: str, delta: int, *, allow_mirror_herb: bool = True) -> tuple[bool, str]:
        if delta < 0:
            side_mist_turns = self.player_mist_turns if pokemon is self.player_active else self.wild_mist_turns
            if side_mist_turns > 0:
                return False, "(Mist bảo vệ)"
        stages = self._stat_stages_for(pokemon)
        current = stages.get(stat_key, 0)
        updated = max(-6, min(6, current + delta))
        if updated == current:
            return False, f"({updated:+d})"
        stages[stat_key] = updated
        if delta < 0:
            if pokemon is self.player_active:
                self.player_stats_lowered_this_turn = True
                if self._held_item_name(pokemon) == "eject pack":
                    self.player_eject_pack_pending = True
            elif pokemon is self.wild:
                self.wild_stats_lowered_this_turn = True
                if self._held_item_name(pokemon) == "eject pack":
                    self.wild_eject_pack_pending = True
            if self._held_item_name(pokemon) == "white herb":
                lowered_stats = [key for key, value in stages.items() if value < 0]
                if lowered_stats:
                    for key in lowered_stats:
                        stages[key] = 0
                    pokemon.hold_item = None
        if delta > 0 and allow_mirror_herb:
            mirror_holder: PokemonInstance | None = None
            if pokemon is self.player_active:
                mirror_holder = self.wild
            elif pokemon is self.wild:
                mirror_holder = self.player_active

            if (
                mirror_holder is not None
                and mirror_holder.current_hp > 0
                and self._held_item_name(mirror_holder) == "mirror herb"
            ):
                copied, copied_text = self._change_stat_stage(
                    mirror_holder,
                    stat_key,
                    delta,
                    allow_mirror_herb=False,
                )
                if copied:
                    mirror_holder.hold_item = None
                    stat_label = {
                        "attack": "Attack",
                        "defense": "Defense",
                        "sp_attack": "Sp. Attack",
                        "sp_defense": "Sp. Defense",
                        "speed": "Speed",
                    }.get(stat_key, stat_key)
                    mirror_log = (
                        f"{mirror_holder.name} kích hoạt Mirror Herb! "
                        f"{stat_label} cũng tăng {copied_text}."
                    )
                    if self.pending_battle_log:
                        self.pending_battle_log = self.pending_battle_log + "\n" + mirror_log
                    else:
                        self.pending_battle_log = mirror_log
        return True, f"({updated:+d})"

    def _can_trigger_normalium_z(self, attacker: PokemonInstance, move: MoveSet) -> bool:
        if attacker is not self.player_active:
            return False
        if self.player_z_power_used:
            return False
        if attacker.hold_item != "Normalium Z":
            return False
        if move.move_type != "Normal" or move.category != "Status":
            return False
        return True

    def _try_apply_z_crystal(
        self,
        attacker: PokemonInstance,
        original_move: MoveSet,
        effective_move: MoveSet,
    ) -> tuple[MoveSet, str]:
        if attacker is not self.player_active:
            return effective_move, ""
        if self.player_z_power_used:
            return effective_move, ""

        held_item = (attacker.hold_item or "").strip().lower()
        attacker_name = (attacker.name or "").strip().lower()

        if held_item == "primarium z" and attacker_name.startswith("primarina") and original_move.name == "Sparkling Aria":
            self.player_z_power_used = True
            return (
                MoveSet(
                    name="Oceanic Operetta",
                    move_type="Water",
                    category="Special",
                    power=195,
                    accuracy=effective_move.accuracy,
                    base_pp=original_move.base_pp,
                    max_pp=original_move.max_pp,
                    current_pp=original_move.current_pp,
                    pp_up_level=original_move.pp_up_level,
                    makes_contact=False,
                    target=original_move.target,
                    priority=original_move.priority,
                ),
                f"{attacker.name} giải phóng Z-Power! Sparkling Aria biến thành Oceanic Operetta!",
            )

        if held_item == "snorlium z" and attacker_name.startswith("snorlax") and original_move.name == "Giga Impact":
            self.player_z_power_used = True
            return (
                MoveSet(
                    name="Pulverizing Pancake",
                    move_type="Normal",
                    category="Physical",
                    power=210,
                    accuracy=effective_move.accuracy,
                    base_pp=original_move.base_pp,
                    max_pp=original_move.max_pp,
                    current_pp=original_move.current_pp,
                    pp_up_level=original_move.pp_up_level,
                    makes_contact=True,
                    target=original_move.target,
                    priority=original_move.priority,
                ),
                f"{attacker.name} giải phóng Z-Power! Giga Impact biến thành Pulverizing Pancake!",
            )

        if held_item == "solganium z" and attacker_name.startswith("solgaleo") and original_move.name == "Sunsteel Strike":
            self.player_z_power_used = True
            return (
                MoveSet(
                    name="Searing Sunraze Smash",
                    move_type="Steel",
                    category="Physical",
                    power=200,
                    accuracy=effective_move.accuracy,
                    base_pp=original_move.base_pp,
                    max_pp=original_move.max_pp,
                    current_pp=original_move.current_pp,
                    pp_up_level=original_move.pp_up_level,
                    makes_contact=True,
                    target=original_move.target,
                    priority=original_move.priority,
                ),
                f"{attacker.name} giải phóng Z-Power! Sunsteel Strike biến thành Searing Sunraze Smash!",
            )

        if held_item == "ultranecrozium z" and "necrozma" in attacker_name and original_move.name == "Photon Geyser":
            self.player_z_power_used = True
            return (
                MoveSet(
                    name="Light That Burns the Sky",
                    move_type=effective_move.move_type,
                    category=effective_move.category,
                    power=200,
                    accuracy=effective_move.accuracy,
                    base_pp=original_move.base_pp,
                    max_pp=original_move.max_pp,
                    current_pp=original_move.current_pp,
                    pp_up_level=original_move.pp_up_level,
                    makes_contact=effective_move.makes_contact,
                    target=effective_move.target,
                    priority=effective_move.priority,
                ),
                f"{attacker.name} giải phóng Z-Power! Photon Geyser biến thành Light That Burns the Sky!",
            )

        if held_item == "tapunium z" and attacker_name.startswith("tapu") and original_move.name == "Nature's Madness":
            self.player_z_power_used = True
            return (
                MoveSet(
                    name="Guardian of Alola",
                    move_type="Fairy",
                    category="Special",
                    power=1,
                    accuracy=effective_move.accuracy,
                    base_pp=original_move.base_pp,
                    max_pp=original_move.max_pp,
                    current_pp=original_move.current_pp,
                    pp_up_level=original_move.pp_up_level,
                    makes_contact=False,
                    target=effective_move.target,
                    priority=effective_move.priority,
                ),
                f"{attacker.name} giải phóng Z-Power! Nature's Madness biến thành Guardian of Alola!",
            )

        if held_item == "steelium z" and effective_move.category != "Status" and effective_move.move_type == "Steel":
            self.player_z_power_used = True
            z_power = max(100, min(200, int(round(max(1, effective_move.power) * 1.5))))
            return (
                MoveSet(
                    name="Corkscrew Crash",
                    move_type="Steel",
                    category=effective_move.category,
                    power=z_power,
                    accuracy=effective_move.accuracy,
                    base_pp=original_move.base_pp,
                    max_pp=original_move.max_pp,
                    current_pp=original_move.current_pp,
                    pp_up_level=original_move.pp_up_level,
                    makes_contact=effective_move.makes_contact,
                    target=effective_move.target,
                    priority=effective_move.priority,
                ),
                f"{attacker.name} giải phóng Z-Power! {original_move.name} biến thành Corkscrew Crash!",
            )

        if held_item == "waterium z" and effective_move.category != "Status" and effective_move.move_type == "Water":
            self.player_z_power_used = True
            z_power = max(100, min(200, int(round(max(1, effective_move.power) * 1.5))))
            return (
                MoveSet(
                    name="Hydro Vortex",
                    move_type="Water",
                    category=effective_move.category,
                    power=z_power,
                    accuracy=effective_move.accuracy,
                    base_pp=original_move.base_pp,
                    max_pp=original_move.max_pp,
                    current_pp=original_move.current_pp,
                    pp_up_level=original_move.pp_up_level,
                    makes_contact=effective_move.makes_contact,
                    target=effective_move.target,
                    priority=effective_move.priority,
                ),
                f"{attacker.name} giải phóng Z-Power! {original_move.name} biến thành Hydro Vortex!",
            )

        if held_item == "psychium z" and effective_move.category != "Status" and effective_move.move_type == "Psychic":
            self.player_z_power_used = True
            z_power = max(100, min(200, int(round(max(1, effective_move.power) * 1.5))))
            return (
                MoveSet(
                    name="Shattered Psyche",
                    move_type="Psychic",
                    category=effective_move.category,
                    power=z_power,
                    accuracy=effective_move.accuracy,
                    base_pp=original_move.base_pp,
                    max_pp=original_move.max_pp,
                    current_pp=original_move.current_pp,
                    pp_up_level=original_move.pp_up_level,
                    makes_contact=effective_move.makes_contact,
                    target=effective_move.target,
                    priority=effective_move.priority,
                ),
                f"{attacker.name} giải phóng Z-Power! {original_move.name} biến thành Shattered Psyche!",
            )

        if held_item == "rockium z" and effective_move.category != "Status" and effective_move.move_type == "Rock":
            self.player_z_power_used = True
            z_power = max(100, min(200, int(round(max(1, effective_move.power) * 1.5))))
            return (
                MoveSet(
                    name="Continental Crush",
                    move_type="Rock",
                    category=effective_move.category,
                    power=z_power,
                    accuracy=effective_move.accuracy,
                    base_pp=original_move.base_pp,
                    max_pp=original_move.max_pp,
                    current_pp=original_move.current_pp,
                    pp_up_level=original_move.pp_up_level,
                    makes_contact=effective_move.makes_contact,
                    target=effective_move.target,
                    priority=effective_move.priority,
                ),
                f"{attacker.name} giải phóng Z-Power! {original_move.name} biến thành Continental Crush!",
            )

        return effective_move, ""

    def _move_usage_for(self, pokemon: PokemonInstance) -> set[str]:
        key = id(pokemon)
        if key not in self.move_usage_history:
            self.move_usage_history[key] = set()
        return self.move_usage_history[key]

    def _mark_move_used(self, pokemon: PokemonInstance, move_name: str) -> None:
        self._move_usage_for(pokemon).add(move_name)

    def _pre_action_status_check(self, attacker: PokemonInstance) -> tuple[bool, str]:
        uproar_active = getattr(self, "player_uproar_turns", 0) > 0 or getattr(self, "wild_uproar_turns", 0) > 0
        if uproar_active and attacker.status == "slp":
            attacker.status = None
            attacker.status_counter = 0
            return True, f"{attacker.name} tỉnh giấc do tiếng ồn từ Uproar!"

        if attacker is self.player_active and self.player_must_recharge:
            self.player_must_recharge = False
            return False, f"{attacker.name} phải nạp lại năng lượng nên không thể hành động!"
        if attacker is self.wild and self.wild_must_recharge:
            self.wild_must_recharge = False
            return False, f"{attacker.name} phải nạp lại năng lượng nên không thể hành động!"

        if attacker is self.player_active and self.player_bide_turns > 0:
            self.player_bide_turns -= 1
            if self.player_bide_turns > 0:
                return False, f"{attacker.name} đang tích trữ năng lượng với Bide..."
            damage = max(0, self.player_bide_damage * 2)
            self.player_bide_damage = 0
            self.wild.current_hp = max(0, self.wild.current_hp - damage)
            if damage > 0:
                self.wild_took_damage_this_turn = True
            return False, f"{attacker.name} giải phóng Bide gây {damage} sát thương lên {self.wild.name}!"

        if attacker is self.wild and self.wild_bide_turns > 0:
            self.wild_bide_turns -= 1
            if self.wild_bide_turns > 0:
                return False, f"{attacker.name} đang tích trữ năng lượng với Bide..."
            damage = max(0, self.wild_bide_damage * 2)
            self.wild_bide_damage = 0
            self.player_active.current_hp = max(0, self.player_active.current_hp - damage)
            if damage > 0:
                self.player_took_damage_this_turn = True
            return False, f"{attacker.name} giải phóng Bide gây {damage} sát thương lên {self.player_active.name}!"

        if attacker is self.player_active and self.player_flinched:
            self.player_flinched = False
            return False, f"{attacker.name} bị flinch và không thể hành động!"
        if attacker is self.wild and self.wild_flinched:
            self.wild_flinched = False
            return False, f"{attacker.name} bị flinch và không thể hành động!"

        if attacker.status == "slp":
            if attacker.status_counter <= 0:
                attacker.status_counter = random.randint(1, 3)
            attacker.status_counter -= 1
            if attacker.status_counter <= 0:
                attacker.status = None
                attacker.status_counter = 0
                return True, f"{attacker.name} tỉnh giấc!"
            return False, f"{attacker.name} đang ngủ và không thể hành động!"

        if attacker.confusion_turns > 0:
            attacker.confusion_turns -= 1
            if random.random() < (1 / 3):
                damage = self._confusion_self_damage(attacker)
                if attacker.confusion_turns <= 0:
                    return False, (
                        f"{attacker.name} tự gây {damage} sát thương vì Confusion và đã hết Confusion!"
                    )
                return False, f"{attacker.name} tự gây {damage} sát thương vì Confusion!"

        if self._is_infatuated(attacker) and random.random() < 0.5:
            return False, f"{attacker.name} bị mê mẩn và không thể hành động!"

        return True, ""

    def _confusion_self_damage(self, pokemon: PokemonInstance) -> int:
        atk = self._effective_stat(pokemon, "attack")
        dfn = self._effective_stat(pokemon, "defense")
        level = pokemon.level
        base_damage = (((2 * level / 5 + 2) * 40 * (atk / max(1, dfn))) / 50) + 2
        damage = max(1, int(base_damage))
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        return damage

    def _is_sound_move(self, move_name: str) -> bool:
        return move_name in {
            "Boomburst",
            "Bug Buzz",
            "Chatter",
            "Clanging Scales",
            "Clangorous Soul",
            "Clangorous Soulblaze",
            "Disarming Voice",
            "Echoed Voice",
            "Eerie Spell",
            "Grass Whistle",
            "Growl",
            "Heal Bell",
            "Howl",
            "Hyper Voice",
            "Metal Sound",
            "Noble Roar",
            "Overdrive",
            "Parting Shot",
            "Perish Song",
            "Relic Song",
            "Roar",
            "Round",
            "Screech",
            "Sing",
            "Snarl",
            "Snore",
            "Sparkling Aria",
            "Supersonic",
            "Uproar",
        }

    def _apply_end_of_turn_status(self) -> list[str]:
        return apply_end_of_turn_status(self)

    def _decrement_side_conditions(self) -> None:
        decrement_side_conditions(self)

    def _apply_leech_seed_drain(self) -> list[str]:
        return apply_leech_seed_drain(self)

    def _apply_switch_in_hazards(self, pokemon: PokemonInstance, is_player: bool) -> list[str]:
        return apply_switch_in_hazards(self, pokemon, is_player)

    def _residual_status_damage(self, pokemon: PokemonInstance, is_player: bool) -> list[str]:
        return residual_status_damage(self, pokemon)

    def _apply_primary_status(self, attacker: PokemonInstance, defender: PokemonInstance, status: str, move_name: str) -> str:
        if defender.current_hp <= 0:
            return f"{attacker.name} dùng {move_name}, nhưng mục tiêu đã gục."
        if defender.status is not None:
            return f"{attacker.name} dùng {move_name}, nhưng {defender.name} đã có trạng thái {defender.status}."

        if self.terrain == "electric terrain" and self.terrain_turns > 0 and status == "slp" and self._is_grounded(defender):
            return f"{attacker.name} dùng {move_name}, nhưng Electric Terrain ngăn {defender.name} ngủ."
        if status == "slp" and (getattr(self, "player_uproar_turns", 0) > 0 or getattr(self, "wild_uproar_turns", 0) > 0):
            return f"{attacker.name} dùng {move_name}, nhưng tiếng ồn từ Uproar ngăn {defender.name} ngủ."
        if self.terrain == "misty terrain" and self.terrain_turns > 0 and self._is_grounded(defender):
            return f"{attacker.name} dùng {move_name}, nhưng Misty Terrain bảo vệ {defender.name} khỏi trạng thái."
        safeguard_turns = self.player_safeguard_turns if defender is self.player_active else self.wild_safeguard_turns
        if safeguard_turns > 0:
            return f"{attacker.name} dùng {move_name}, nhưng Safeguard bảo vệ {defender.name} khỏi trạng thái."

        if status == "brn" and "Fire" in defender.types:
            return f"{attacker.name} dùng {move_name}, nhưng {defender.name} miễn nhiễm Burn."
        if status == "par" and "Electric" in defender.types:
            return f"{attacker.name} dùng {move_name}, nhưng {defender.name} miễn nhiễm Paralysis."
        if status in {"psn", "tox"} and ("Poison" in defender.types or "Steel" in defender.types):
            return f"{attacker.name} dùng {move_name}, nhưng {defender.name} miễn nhiễm Poison."
        if status in {"psn", "tox"} and defender.ability == "Immunity":
            return f"{attacker.name} dùng {move_name}, nhưng {defender.name} miễn nhiễm Poison nhờ Immunity."

        defender.status = status
        if status == "slp":
            defender.status_counter = random.randint(1, 3)
        elif status == "tox":
            defender.status_counter = 1
        else:
            defender.status_counter = 0
        status_text = {
            "par": "Paralysis",
            "brn": "Burn",
            "psn": "Poison",
            "tox": "Badly Poisoned",
            "slp": "Sleep",
        }.get(status, status)
        return f"{attacker.name} dùng {move_name}. {defender.name} bị {status_text}."

    def _try_activate_protect(self, attacker: PokemonInstance) -> bool:
        if attacker is self.player_active:
            chance = 1 / (3 ** self.player_protect_chain)
            if random.random() <= chance:
                self.player_protect_active = True
                self.player_protect_chain += 1
                return True
            self.player_protect_active = False
            self.player_protect_chain = 0
            return False

        chance = 1 / (3 ** self.wild_protect_chain)
        if random.random() <= chance:
            self.wild_protect_active = True
            self.wild_protect_chain += 1
            return True
        self.wild_protect_active = False
        self.wild_protect_chain = 0
        return False

    def _reset_protect_chain(self, attacker: PokemonInstance) -> None:
        if attacker is self.player_active:
            self.player_protect_chain = 0
            return
        self.wild_protect_chain = 0

    def _healing_item_amount(self, item_name: str) -> int | None:
        return get_healing_item_amount(item_name)

    def _x_item_stat(self, item_name: str) -> str | None:
        return get_x_item_stat(item_name)


def create_pokemon_instance(game_data: GameData, species: dict[str, Any], level: int, owner_id: int | None = None) -> PokemonInstance:
    from .data_loader import get_learnset_for_species
    base = species["base"]
    ivs = {key: random.randint(0, 31) for key in STAT_KEYS}
    evs = {key: 0 for key in STAT_KEYS}
    nature = random.choice(list(NATURE_EFFECTS.keys()))

    hp = int(((2 * base["HP"] + ivs["HP"] + (evs["HP"] // 4)) * level) / 100) + level + 10

    attack_base = int(((2 * base["Attack"] + ivs["Attack"] + (evs["Attack"] // 4)) * level) / 100) + 5
    defense_base = int(((2 * base["Defense"] + ivs["Defense"] + (evs["Defense"] // 4)) * level) / 100) + 5
    sp_attack_base = int(((2 * base["Sp. Attack"] + ivs["Sp. Attack"] + (evs["Sp. Attack"] // 4)) * level) / 100) + 5
    sp_defense_base = int(((2 * base["Sp. Defense"] + ivs["Sp. Defense"] + (evs["Sp. Defense"] // 4)) * level) / 100) + 5
    speed_base = int(((2 * base["Speed"] + ivs["Speed"] + (evs["Speed"] // 4)) * level) / 100) + 5

    attack = int(attack_base * _nature_multiplier(nature, "attack"))
    defense = int(defense_base * _nature_multiplier(nature, "defense"))
    sp_attack = int(sp_attack_base * _nature_multiplier(nature, "sp_attack"))
    sp_defense = int(sp_defense_base * _nature_multiplier(nature, "sp_defense"))
    speed = int(speed_base * _nature_multiplier(nature, "speed"))

    # Lấy moveset hợp lệ từ learnsets
    learnset_moves = get_learnset_for_species(species["name"]["english"], level, gen="9")
    moves: list[MoveSet] = []
    if learnset_moves:
        # Map move name sang MoveData từ game_data.moves
        move_lookup = {m["name"]["english"].lower(): m for m in game_data.moves}
        for mv_name in learnset_moves:
            m = move_lookup.get(mv_name.lower())
            if m:
                # Safe parse for power
                power = _parse_move_numeric(m.get("power", 0), default=0)
                # Safe parse for accuracy
                accuracy = max(1, min(100, _parse_move_numeric(m.get("accuracy", 100), default=100)))
                base_pp = max(1, _parse_move_numeric(m.get("pp", 1), default=1))
                max_pp = _max_pp_from_stage(base_pp, 0)
                move_name = m["name"]["english"]
                target = get_default_target(move_name)
                priority = get_move_priority(move_name, m.get("priority"))
                moves.append(MoveSet(
                    name=move_name,
                    move_type=m.get("type", "Normal"),
                    category=m.get("category", "Physical"),
                    power=power,
                    accuracy=accuracy,
                    base_pp=base_pp,
                    max_pp=max_pp,
                    current_pp=max_pp,
                    pp_up_level=0,
                    makes_contact=False,
                    target=target,
                    priority=priority,
                ))
    if not moves:
        # fallback: random moves như cũ
        raw_moves: list[MoveData] = game_data.random_moves_for_species(species.get("type", ["Normal"]))
        moves = [
            MoveSet(
                name=m.name,
                move_type=m.move_type,
                category=m.category,
                power=m.power,
                accuracy=m.accuracy,
                base_pp=20,
                max_pp=_max_pp_from_stage(20, 0),
                current_pp=_max_pp_from_stage(20, 0),
                pp_up_level=0,
                makes_contact=False,
                target="any",
                priority=get_move_priority(m.name),
            )
            for m in raw_moves
        ]

    ability = get_default_ability_for_species(species)

    return PokemonInstance(
        species_id=int(species["id"]),
        name=species["name"]["english"],
        level=level,
        types=list(species.get("type", ["Normal"])),
        max_hp=hp,
        attack=attack,
        defense=defense,
        sp_attack=sp_attack,
        sp_defense=sp_defense,
        speed=speed,
        current_hp=hp,
        moves=moves,
        ivs=ivs,
        evs=evs,
        nature=nature,
        exp=PokemonInstance.exp_for_level(level),
        hold_item=None,
        image_url=(species.get("image", {}).get("thumbnail") or species.get("image", {}).get("sprite")),
        owner_id=owner_id,
        ability=ability,
        happiness=HAPPINESS_START,
    )
