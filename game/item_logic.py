from __future__ import annotations

from datetime import datetime
import random
from typing import Any, Callable


HEALING_ITEMS: dict[str, int] = {
    "Potion": 20,
    "Super Potion": 60,
    "Hyper Potion": 120,
    "Max Potion": -1,
    "Full Restore": -1,
    "Fresh Water": 30,
    "Soda Pop": 50,
    "Lemonade": 70,
    "Moomoo Milk": 100,
    "Berry Juice": 20,
    "Remedy": 60,
    "Energy Powder": 60,
    "Energy Root": 120,
    "Fine Remedy": 100,
    "Superb Remedy": 150,
    "Sweet Heart": 20,
}

STATUS_CURE_ITEMS: dict[str, set[str] | str] = {
    "Antidote": {"psn", "tox"},
    "Awakening": {"slp"},
    "Burn Heal": {"brn"},
    "Ice Heal": {"frz"},
    "Paralyze Heal": {"par"},
    "Big Malasada": "all",
    "Casteliacone": "all",
    "Fine Remedy": "all",
    "Full Heal": "all",
    "Full Restore": "all",
    "Heal Powder": "all",
    "Jubilife Muffin": "all",
    "Lava Cookie": "all",
    "Lumiose Galette": "all",
    "Old Gateau": "all",
    "Pewter Crunchies": "all",
    "Rage Candy Bar": "all",
    "Shalour Sable": "all",
}

PP_RESTORE_ITEMS: dict[str, tuple[str, int]] = {
    "Ether": ("single", 10),
    "Elixir": ("all", 10),
    "Max Ether": ("single", -1),
    "Max Elixir": ("all", -1),
}

REVIVE_ITEMS: dict[str, str] = {
    "Revive": "half",
    "Revival Herb": "full",
    "Sacred Ash": "all_full",
}

X_ITEMS: dict[str, str] = {
    "X Attack": "attack",
    "X Defend": "defense",
    "X Sp. Atk": "sp_attack",
    "X Sp. Def": "sp_defense",
    "X Speed": "speed",
}

WEATHER_EXTENDERS: dict[str, str] = {
    "rain": "damp rock",
    "harsh sunlight": "heat rock",
    "sandstorm": "smooth rock",
    "snow": "icy rock",
}

BERRY_DISLIKED_STATS: dict[str, str] = {
    "figy berry": "attack",
    "iapapa berry": "defense",
    "wiki berry": "sp_attack",
    "aguav berry": "sp_defense",
    "mago berry": "speed",
}

TERRAIN_SEED_MAP: dict[str, tuple[str, str, str]] = {
    "electric terrain": ("electric seed", "defense", "Electric Seed"),
    "grassy terrain": ("grassy seed", "defense", "Grassy Seed"),
    "misty terrain": ("misty seed", "sp_defense", "Misty Seed"),
    "psychic terrain": ("psychic seed", "sp_defense", "Psychic Seed"),
}

STATIC_CATCH_BALL_MODIFIERS: dict[str, float] = {
    "ultra ball": 2.0,
    "great ball": 1.5,
    "poké ball": 1.0,
    "poke ball": 1.0,
    "pokeball": 1.0,
    "cherish ball": 1.0,
    "friend ball": 1.0,
    "heal ball": 1.0,
    "luxury ball": 1.0,
    "premier ball": 1.0,
}

__all__ = [
    "calculate_catch_chance",
    "resolve_held_item_name",
    "get_healing_item_amount",
    "get_x_item_stat",
    "get_status_cure_item",
    "get_pp_restore_item",
    "get_revive_item",
    "apply_pp_item_for_pokemon",
    "get_screen_duration",
    "get_weather_duration",
    "get_terrain_duration",
    "is_choice_item",
    "apply_held_item_stat_modifiers",
    "is_disliked_pinch_flavor",
    "trigger_berry_effects",
    "try_activate_room_service",
    "trigger_active_room_service",
    "try_consume_mental_herb",
    "consume_eject_pack_for",
    "consume_pending_eject_pack",
    "try_activate_booster_energy",
    "try_activate_terrain_seed",
    "trigger_active_terrain_seeds",
]


def resolve_held_item_name(hold_item: str | None, *, magic_room_turns: int, side_embargo_turns: int) -> str:
    if magic_room_turns > 0 or side_embargo_turns > 0:
        return ""
    return (hold_item or "").strip().lower()


def get_healing_item_amount(item_name: str) -> int | None:
    return HEALING_ITEMS.get(item_name)


def get_x_item_stat(item_name: str) -> str | None:
    return X_ITEMS.get(item_name)


def get_status_cure_item(item_name: str) -> set[str] | str | None:
    return STATUS_CURE_ITEMS.get(item_name)


def get_pp_restore_item(item_name: str) -> tuple[str, int] | None:
    return PP_RESTORE_ITEMS.get(item_name)


def get_revive_item(item_name: str) -> str | None:
    return REVIVE_ITEMS.get(item_name)


def get_screen_duration(held_item_name: str) -> int:
    return 8 if held_item_name == "light clay" else 5


def get_weather_duration(held_item_name: str, weather_name: str) -> int:
    extender = WEATHER_EXTENDERS.get(weather_name)
    if extender and held_item_name == extender:
        return 8
    return 5


def get_terrain_duration(held_item_name: str) -> int:
    return 8 if held_item_name == "terrain extender" else 5


def is_choice_item(held_item_name: str) -> bool:
    return held_item_name in {"choice band", "choice specs", "choice scarf"}


def apply_held_item_stat_modifiers(
    value: int,
    *,
    stat_key: str,
    held_item_name: str,
    pokemon_name: str,
    can_still_evolve: bool,
) -> int:
    adjusted = max(1, int(value))

    if held_item_name == "choice scarf" and stat_key == "speed":
        adjusted = max(1, int(adjusted * 1.5))
    if held_item_name == "macho brace" and stat_key == "speed":
        adjusted = max(1, int(adjusted * 0.5))
    if held_item_name in {
        "power anklet",
        "power band",
        "power belt",
        "power bracer",
        "power lens",
        "power weight",
    } and stat_key == "speed":
        adjusted = max(1, int(adjusted * 0.5))
    if held_item_name == "iron ball" and stat_key == "speed":
        adjusted = max(1, int(adjusted * 0.5))
    if held_item_name == "assault vest" and stat_key == "sp_defense":
        adjusted = max(1, int(adjusted * 1.5))
    if held_item_name == "eviolite" and stat_key in {"defense", "sp_defense"} and can_still_evolve:
        adjusted = max(1, int(adjusted * 1.5))
    if held_item_name == "light ball" and pokemon_name == "Pikachu" and stat_key in {"attack", "sp_attack"}:
        adjusted = max(1, int(adjusted * 2))
    if held_item_name == "quick powder" and pokemon_name == "Ditto" and stat_key == "speed":
        adjusted = max(1, int(adjusted * 2))
    if held_item_name == "thick club" and pokemon_name in {"Cubone", "Marowak"} and stat_key == "attack":
        adjusted = max(1, int(adjusted * 2))
    if held_item_name == "deep sea tooth" and pokemon_name == "Clamperl" and stat_key == "sp_attack":
        adjusted = max(1, int(adjusted * 2))
    if held_item_name == "deep sea scale" and pokemon_name == "Clamperl" and stat_key == "sp_defense":
        adjusted = max(1, int(adjusted * 2))
    if held_item_name == "metal powder" and pokemon_name == "Ditto" and stat_key == "defense":
        adjusted = max(1, int(adjusted * 2))

    return adjusted


def is_disliked_pinch_flavor(berry_name: str, lowered_nature_stat: str | None) -> bool:
    lowered_stat = BERRY_DISLIKED_STATS.get(berry_name)
    if lowered_stat is None:
        return False
    return lowered_nature_stat == lowered_stat


def apply_pp_item_for_pokemon(
    pokemon: Any,
    item_name: str,
    *,
    max_pp_from_stage: Callable[[int, int], int],
) -> tuple[bool, str]:
    candidates = [mv for mv in pokemon.moves if mv.pp_up_level < 3 and mv.base_pp > 1]
    if not candidates:
        return False, f"Không có move nào của {pokemon.name} có thể tăng PP thêm."

    target = candidates[0]
    before_max = target.max_pp

    if item_name == "PP Max":
        target.pp_up_level = 3
    else:
        target.pp_up_level = min(3, target.pp_up_level + 1)

    target.max_pp = max_pp_from_stage(target.base_pp, target.pp_up_level)
    increased = max(0, target.max_pp - before_max)
    target.current_pp = min(target.max_pp, target.current_pp + increased)

    return (
        True,
        f"Bạn dùng {item_name} cho {target.name}. Max PP: {before_max} -> {target.max_pp} (bậc {target.pp_up_level}/3).",
    )


def calculate_catch_chance(battle: Any, ball_name: str) -> float:
    normalized_ball = (ball_name or "").strip().lower()
    if normalized_ball == "master ball":
        return 1.0

    wild_species = next(
        (s for s in battle.game_data.pokedex if int(s.get("id", 0)) == int(battle.wild.species_id)),
        None,
    )
    player_species = next(
        (s for s in battle.game_data.pokedex if int(s.get("id", 0)) == int(battle.player_active.species_id)),
        None,
    )

    def _deterministic_gender(pokemon: Any, species_data: dict[str, Any] | None) -> str | None:
        explicit_gender = str(getattr(pokemon, "gender", "") or "").strip().lower()
        if explicit_gender in {"male", "m", "đực", "duc"}:
            return "male"
        if explicit_gender in {"female", "f", "cái", "cai"}:
            return "female"
        profile_gender = str(((species_data or {}).get("profile", {}) or {}).get("gender", "")).strip().lower()
        if profile_gender == "100:0":
            return "male"
        if profile_gender == "0:100":
            return "female"
        return None

    def _evolves_with_moon_stone(species_data: dict[str, Any] | None) -> bool:
        evolution = (species_data or {}).get("evolution", {}) or {}
        next_entries = evolution.get("next", [])
        if not isinstance(next_entries, list):
            return False
        for entry in next_entries:
            if isinstance(entry, list):
                for part in entry:
                    if "moon stone" in str(part).strip().lower():
                        return True
        return False

    wild_base_speed = max(1, int(((wild_species or {}).get("base", {}) or {}).get("Speed", battle.wild.speed)))
    wild_description = str((wild_species or {}).get("description", "") or "").lower()
    wild_abilities = ((wild_species or {}).get("profile", {}) or {}).get("ability", [])
    wild_has_beast_boost = any(
        str(a[0]).strip().lower() == "beast boost"
        for a in wild_abilities
        if isinstance(a, list) and a
    )
    wild_is_ultra_beast = wild_has_beast_boost or "ultra beast" in wild_description

    player_gender = _deterministic_gender(battle.player_active, player_species)
    wild_gender = _deterministic_gender(battle.wild, wild_species)
    love_ball_mod = 1.0
    if (
        int(battle.player_active.species_id) == int(battle.wild.species_id)
        and player_gender is not None
        and wild_gender is not None
        and player_gender != wild_gender
    ):
        love_ball_mod = 8.0

    moon_ball_mod = 4.0 if _evolves_with_moon_stone(wild_species) else 1.0

    current_hour = datetime.now().hour
    is_night = current_hour >= 18 or current_hour <= 5
    is_water_target = "Water" in battle.wild.types
    is_bug_target = "Bug" in battle.wild.types
    is_asleep_target = battle.wild.status == "slp"
    player_level = max(1, int(getattr(battle.player_active, "level", 1)))
    wild_level = max(1, int(getattr(battle.wild, "level", 1)))
    level_ratio = player_level / wild_level
    already_caught_species = any(
        int(getattr(p, "species_id", -1)) == int(battle.wild.species_id)
        for p in [*battle.player.party, *battle.player.pc]
    )

    level_ball_mod = 1.0
    if level_ratio >= 4.0:
        level_ball_mod = 8.0
    elif level_ratio >= 2.0:
        level_ball_mod = 4.0
    elif level_ratio > 1.0:
        level_ball_mod = 2.0

    nest_ball_mod = 1.0
    if wild_level < 30:
        nest_ball_mod = max(1.0, min(4.0, (41 - wild_level) / 10))

    timer_ball_mod = min(4.0, 1.0 + max(0, battle.turn_count - 1) * 0.3)
    quick_ball_mod = 5.0 if battle.turn_count <= 1 else 1.0

    modifiers = dict(STATIC_CATCH_BALL_MODIFIERS)
    modifiers.update(
        {
            "dusk ball": 3.0 if is_night else 1.0,
            "quick ball": quick_ball_mod,
            "dive ball": 3.5 if is_water_target else 1.0,
            "lure ball": 4.0 if is_water_target else 1.0,
            "dream ball": 4.0 if is_asleep_target else 1.0,
            "fast ball": 4.0 if wild_base_speed >= 100 else 1.0,
            "level ball": level_ball_mod,
            "love ball": love_ball_mod,
            "moon ball": moon_ball_mod,
            "nest ball": nest_ball_mod,
            "net ball": 3.5 if (is_water_target or is_bug_target) else 1.0,
            "repeat ball": 3.5 if already_caught_species else 1.0,
            "timer ball": timer_ball_mod,
            "beast ball": 5.0 if wild_is_ultra_beast else 0.1,
        }
    )
    ball_mod = modifiers.get(normalized_ball, 1.0)

    hp_factor = (3 * battle.wild.max_hp - 2 * battle.wild.current_hp) / (3 * battle.wild.max_hp)
    level_factor = max(0.15, min(0.95, 0.4 + (30 - battle.wild.level) * 0.01))

    chance = min(0.95, max(0.05, hp_factor * 0.5 * ball_mod + level_factor * 0.2))
    return chance


def trigger_berry_effects(battle: Any, pokemon: Any) -> list[str]:
    logs: list[str] = []
    if pokemon.current_hp <= 0:
        return logs

    held = battle._held_item_name(pokemon)
    if not held or "berry" not in held:
        return logs

    ability_name = (pokemon.ability or "").strip()
    pinch_threshold = max(1, pokemon.max_hp // 2) if ability_name == "Gluttony" else max(1, pokemon.max_hp // 4)

    consumed = False
    if held == "oran berry" and pokemon.current_hp <= max(1, pokemon.max_hp // 2):
        heal = min(10, pokemon.max_hp - pokemon.current_hp)
        if heal > 0:
            pokemon.current_hp += heal
            logs.append(f"{pokemon.name} ăn Oran Berry và hồi {heal} HP ({pokemon.current_hp}/{pokemon.max_hp}).")
            consumed = True
    elif held == "sitrus berry" and pokemon.current_hp <= max(1, pokemon.max_hp // 2):
        heal = min(max(1, pokemon.max_hp // 4), pokemon.max_hp - pokemon.current_hp)
        if heal > 0:
            pokemon.current_hp += heal
            logs.append(f"{pokemon.name} ăn Sitrus Berry và hồi {heal} HP ({pokemon.current_hp}/{pokemon.max_hp}).")
            consumed = True
    elif held == "cheri berry" and pokemon.status == "par":
        pokemon.status = None
        pokemon.status_counter = 0
        logs.append(f"{pokemon.name} ăn Cheri Berry và chữa Paralysis.")
        consumed = True
    elif held == "chesto berry" and pokemon.status == "slp":
        pokemon.status = None
        pokemon.status_counter = 0
        logs.append(f"{pokemon.name} ăn Chesto Berry và tỉnh giấc.")
        consumed = True
    elif held == "pecha berry" and pokemon.status in {"psn", "tox"}:
        pokemon.status = None
        pokemon.status_counter = 0
        logs.append(f"{pokemon.name} ăn Pecha Berry và chữa Poison.")
        consumed = True
    elif held == "rawst berry" and pokemon.status == "brn":
        pokemon.status = None
        pokemon.status_counter = 0
        logs.append(f"{pokemon.name} ăn Rawst Berry và chữa Burn.")
        consumed = True
    elif held == "persim berry" and pokemon.confusion_turns > 0:
        pokemon.confusion_turns = 0
        logs.append(f"{pokemon.name} ăn Persim Berry và hết Confusion.")
        consumed = True
    elif held == "lum berry" and (pokemon.status is not None or pokemon.confusion_turns > 0):
        pokemon.status = None
        pokemon.status_counter = 0
        pokemon.confusion_turns = 0
        logs.append(f"{pokemon.name} ăn Lum Berry và chữa trạng thái bất lợi.")
        consumed = True
    elif held == "liechi berry" and pokemon.current_hp <= pinch_threshold:
        changed, stage_text = battle._change_stat_stage(pokemon, "attack", +1)
        if changed:
            logs.append(f"{pokemon.name} ăn Liechi Berry! Attack tăng {stage_text}.")
            consumed = True
    elif held == "ganlon berry" and pokemon.current_hp <= pinch_threshold:
        changed, stage_text = battle._change_stat_stage(pokemon, "defense", +1)
        if changed:
            logs.append(f"{pokemon.name} ăn Ganlon Berry! Defense tăng {stage_text}.")
            consumed = True
    elif held == "salac berry" and pokemon.current_hp <= pinch_threshold:
        changed, stage_text = battle._change_stat_stage(pokemon, "speed", +1)
        if changed:
            logs.append(f"{pokemon.name} ăn Salac Berry! Speed tăng {stage_text}.")
            consumed = True
    elif held == "petaya berry" and pokemon.current_hp <= pinch_threshold:
        changed, stage_text = battle._change_stat_stage(pokemon, "sp_attack", +1)
        if changed:
            logs.append(f"{pokemon.name} ăn Petaya Berry! Sp. Attack tăng {stage_text}.")
            consumed = True
    elif held == "apicot berry" and pokemon.current_hp <= pinch_threshold:
        changed, stage_text = battle._change_stat_stage(pokemon, "sp_defense", +1)
        if changed:
            logs.append(f"{pokemon.name} ăn Apicot Berry! Sp. Defense tăng {stage_text}.")
            consumed = True
    elif held in {"figy berry", "wiki berry", "mago berry", "aguav berry", "iapapa berry"} and pokemon.current_hp <= pinch_threshold:
        heal = min(max(1, pokemon.max_hp // 3), pokemon.max_hp - pokemon.current_hp)
        if heal > 0:
            pokemon.current_hp += heal
            logs.append(f"{pokemon.name} ăn {held.title()} và hồi {heal} HP ({pokemon.current_hp}/{pokemon.max_hp}).")
            if pokemon.confusion_turns <= 0 and battle._is_disliked_pinch_flavor(pokemon, held):
                pokemon.confusion_turns = random.randint(2, 5)
                logs.append(f"{pokemon.name} bị Confusion vì không hợp vị Berry!")
            consumed = True
    elif held == "starf berry" and pokemon.current_hp <= pinch_threshold:
        boostable = [
            stat_key
            for stat_key in ["attack", "defense", "sp_attack", "sp_defense", "speed"]
            if battle._stat_stages_for(pokemon).get(stat_key, 0) < 6
        ]
        if boostable:
            boosted_stat = random.choice(boostable)
            changed, stage_text = battle._change_stat_stage(pokemon, boosted_stat, +2)
            if changed:
                stat_label = {
                    "attack": "Attack",
                    "defense": "Defense",
                    "sp_attack": "Sp. Attack",
                    "sp_defense": "Sp. Defense",
                    "speed": "Speed",
                }.get(boosted_stat, boosted_stat)
                logs.append(f"{pokemon.name} ăn Starf Berry! {stat_label} tăng mạnh {stage_text}.")
                consumed = True
    elif held == "micle berry" and pokemon.current_hp <= pinch_threshold:
        if pokemon is battle.player_active:
            battle.player_micle_accuracy_boost = True
        elif pokemon is battle.wild:
            battle.wild_micle_accuracy_boost = True
        logs.append(f"{pokemon.name} ăn Micle Berry! Độ chính xác đòn kế tiếp sẽ tăng.")
        consumed = True
    elif held == "lansat berry" and pokemon.current_hp <= pinch_threshold:
        if pokemon is battle.player_active:
            battle.player_lansat_crit_boost = True
        elif pokemon is battle.wild:
            battle.wild_lansat_crit_boost = True
        logs.append(f"{pokemon.name} ăn Lansat Berry! Tỉ lệ chí mạng được tăng cường.")
        consumed = True

    if consumed:
        pokemon.hold_item = None
        pokemon.berry_consumed = True
    return logs


def try_activate_room_service(battle: Any, pokemon: Any) -> str | None:
    if pokemon.current_hp <= 0:
        return None
    if getattr(battle, "trick_room_turns", 0) <= 0:
        return None
    if battle._held_item_name(pokemon) != "room service":
        return None

    changed, stage_text = battle._change_stat_stage(pokemon, "speed", -1)
    if not changed:
        return None
    pokemon.hold_item = None
    return f"{pokemon.name} kích hoạt Room Service! Speed giảm {stage_text}."


def trigger_active_room_service(battle: Any) -> list[str]:
    logs: list[str] = []
    for pokemon in (battle.player_active, battle.wild):
        room_log = try_activate_room_service(battle, pokemon)
        if room_log:
            logs.append(room_log)
    return logs


def try_consume_mental_herb(battle: Any, pokemon: Any) -> str | None:
    if pokemon.current_hp <= 0:
        return None
    if battle._held_item_name(pokemon) != "mental herb":
        return None

    cured_effects: list[str] = []
    if battle._is_infatuated(pokemon):
        battle._set_infatuated(pokemon, False)
        cured_effects.append("Infatuation")

    if pokemon is battle.player_active:
        if battle.player_taunt_turns > 0:
            battle.player_taunt_turns = 0
            cured_effects.append("Taunt")
        if battle.player_encore_turns > 0:
            battle.player_encore_turns = 0
            battle.player_encore_move = None
            cured_effects.append("Encore")
        if battle.player_torment_turns > 0:
            battle.player_torment_turns = 0
            cured_effects.append("Torment")
        if battle.player_disable_turns > 0:
            battle.player_disable_turns = 0
            battle.player_disabled_move = None
            cured_effects.append("Disable")
    else:
        if battle.wild_taunt_turns > 0:
            battle.wild_taunt_turns = 0
            cured_effects.append("Taunt")
        if battle.wild_encore_turns > 0:
            battle.wild_encore_turns = 0
            battle.wild_encore_move = None
            cured_effects.append("Encore")
        if battle.wild_torment_turns > 0:
            battle.wild_torment_turns = 0
            cured_effects.append("Torment")
        if battle.wild_disable_turns > 0:
            battle.wild_disable_turns = 0
            battle.wild_disabled_move = None
            cured_effects.append("Disable")

    if not cured_effects:
        return None

    pokemon.hold_item = None
    return f"{pokemon.name} kích hoạt Mental Herb và hóa giải {', '.join(cured_effects)}!"


def consume_eject_pack_for(battle: Any, pokemon: Any) -> str | None:
    if pokemon.current_hp <= 0:
        return None
    if battle._held_item_name(pokemon) != "eject pack":
        return None
    if pokemon is not battle.player_active:
        return None

    switch_text = battle._force_switch_player()
    if not switch_text:
        return None

    pokemon.hold_item = None
    return f"{pokemon.name} kích hoạt Eject Pack! {switch_text}"


def consume_pending_eject_pack(battle: Any) -> list[str]:
    logs: list[str] = []
    if getattr(battle, "player_eject_pack_pending", False):
        battle.player_eject_pack_pending = False
        trigger = consume_eject_pack_for(battle, battle.player_active)
        if trigger:
            logs.append(trigger)
    if getattr(battle, "wild_eject_pack_pending", False):
        battle.wild_eject_pack_pending = False
        trigger = consume_eject_pack_for(battle, battle.wild)
        if trigger:
            logs.append(trigger)
    return logs


def try_activate_booster_energy(battle: Any, pokemon: Any) -> str | None:
    ability = (pokemon.ability or "").strip()
    if ability not in {"Protosynthesis", "Quark Drive"}:
        return None
    if battle._ability_field_boost_stat(pokemon) is not None:
        return None
    key = id(pokemon)
    if key in battle.booster_energy_boost_stat:
        return None
    if battle._held_item_name(pokemon) != "booster energy":
        return None

    boosted_stat = battle._highest_non_hp_stat(pokemon)
    battle.booster_energy_boost_stat[key] = boosted_stat
    pokemon.hold_item = None
    stat_label = {
        "attack": "Attack",
        "defense": "Defense",
        "sp_attack": "Sp. Attack",
        "sp_defense": "Sp. Defense",
        "speed": "Speed",
    }.get(boosted_stat, boosted_stat)
    return f"{pokemon.name} kích hoạt Booster Energy! {stat_label} được cường hóa cho đến khi rời sân."


def try_activate_terrain_seed(battle: Any, pokemon: Any) -> str | None:
    if pokemon.current_hp <= 0:
        return None
    if not battle.terrain or battle.terrain_turns <= 0:
        return None
    if not battle._is_grounded(pokemon):
        return None

    required = TERRAIN_SEED_MAP.get(battle.terrain)
    if required is None:
        return None

    required_item, stat_key, item_label = required
    if battle._held_item_name(pokemon) != required_item:
        return None

    changed, stage_text = battle._change_stat_stage(pokemon, stat_key, +1)
    if not changed:
        return None

    pokemon.hold_item = None
    stat_label = "Defense" if stat_key == "defense" else "Sp. Defense"
    return f"{pokemon.name} kích hoạt {item_label}! {stat_label} tăng {stage_text}."


def trigger_active_terrain_seeds(battle: Any) -> list[str]:
    logs: list[str] = []
    for pokemon in (battle.player_active, battle.wild):
        seed_log = try_activate_terrain_seed(battle, pokemon)
        if seed_log:
            logs.append(seed_log)
    return logs
