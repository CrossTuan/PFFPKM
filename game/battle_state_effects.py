from __future__ import annotations

from typing import Any


def apply_end_of_turn_status(battle: Any) -> list[str]:
    logs: list[str] = []
    logs.extend(residual_status_damage(battle, battle.player_active))
    logs.extend(residual_status_damage(battle, battle.wild))
    logs.extend(apply_leech_seed_drain(battle))
    logs.extend(apply_volatile_residuals(battle))
    logs.extend(apply_end_of_turn_items(battle))
    logs.extend(apply_weather_and_terrain_residuals(battle))
    decrement_side_conditions(battle)
    logs.extend(decrement_field_conditions(battle))
    return logs


def apply_end_of_turn_items(battle: Any) -> list[str]:
    logs: list[str] = []
    for pokemon in [battle.player_active, battle.wild]:
        if pokemon.current_hp <= 0:
            continue

        held = battle._held_item_name(pokemon)
        if not held:
            continue

        if held == "leftovers" and pokemon.current_hp < pokemon.max_hp:
            heal = max(1, pokemon.max_hp // 16)
            before = pokemon.current_hp
            pokemon.current_hp = min(pokemon.max_hp, pokemon.current_hp + heal)
            actual = pokemon.current_hp - before
            if actual > 0:
                logs.append(f"Leftovers hồi {actual} HP cho {pokemon.name} ({pokemon.current_hp}/{pokemon.max_hp}).")

        if held == "black sludge":
            if "Poison" in pokemon.types:
                if pokemon.current_hp < pokemon.max_hp:
                    heal = max(1, pokemon.max_hp // 16)
                    before = pokemon.current_hp
                    pokemon.current_hp = min(pokemon.max_hp, pokemon.current_hp + heal)
                    actual = pokemon.current_hp - before
                    if actual > 0:
                        logs.append(f"Black Sludge hồi {actual} HP cho {pokemon.name} ({pokemon.current_hp}/{pokemon.max_hp}).")
            elif pokemon.ability != "Magic Guard":
                dmg = max(1, pokemon.max_hp // 8)
                pokemon.current_hp = max(0, pokemon.current_hp - dmg)
                logs.append(f"Black Sludge gây {dmg} sát thương lên {pokemon.name} ({pokemon.current_hp}/{pokemon.max_hp}).")

        if held == "flame orb" and pokemon.status is None and "Fire" not in pokemon.types:
            pokemon.status = "brn"
            pokemon.status_counter = 0
            logs.append(f"{pokemon.name} bị Burn do Flame Orb.")

        if held == "toxic orb" and pokemon.status is None and "Poison" not in pokemon.types and "Steel" not in pokemon.types:
            pokemon.status = "tox"
            pokemon.status_counter = 1
            logs.append(f"{pokemon.name} bị Badly Poisoned do Toxic Orb.")

        if held == "sticky barb" and pokemon.ability != "Magic Guard":
            dmg = max(1, pokemon.max_hp // 8)
            pokemon.current_hp = max(0, pokemon.current_hp - dmg)
            logs.append(f"Sticky Barb gây {dmg} sát thương lên {pokemon.name} ({pokemon.current_hp}/{pokemon.max_hp}).")

        logs.extend(battle._try_trigger_berry(pokemon))
    return logs


def apply_volatile_residuals(battle: Any) -> list[str]:
    logs: list[str] = []

    if getattr(battle, "player_disable_turns", 0) > 0:
        battle.player_disable_turns -= 1
        if battle.player_disable_turns <= 0:
            battle.player_disable_turns = 0
            battle.player_disabled_move = None
    if getattr(battle, "wild_disable_turns", 0) > 0:
        battle.wild_disable_turns -= 1
        if battle.wild_disable_turns <= 0:
            battle.wild_disable_turns = 0
            battle.wild_disabled_move = None

    if getattr(battle, "player_heal_block_turns", 0) > 0:
        battle.player_heal_block_turns -= 1
        if battle.player_heal_block_turns < 0:
            battle.player_heal_block_turns = 0
    if getattr(battle, "wild_heal_block_turns", 0) > 0:
        battle.wild_heal_block_turns -= 1
        if battle.wild_heal_block_turns < 0:
            battle.wild_heal_block_turns = 0

    if getattr(battle, "player_taunt_turns", 0) > 0:
        battle.player_taunt_turns -= 1
        if battle.player_taunt_turns < 0:
            battle.player_taunt_turns = 0
    if getattr(battle, "wild_taunt_turns", 0) > 0:
        battle.wild_taunt_turns -= 1
        if battle.wild_taunt_turns < 0:
            battle.wild_taunt_turns = 0

    if getattr(battle, "player_throat_chop_turns", 0) > 0:
        battle.player_throat_chop_turns -= 1
        if battle.player_throat_chop_turns < 0:
            battle.player_throat_chop_turns = 0
    if getattr(battle, "wild_throat_chop_turns", 0) > 0:
        battle.wild_throat_chop_turns -= 1
        if battle.wild_throat_chop_turns < 0:
            battle.wild_throat_chop_turns = 0

    if getattr(battle, "player_torment_turns", 0) > 0:
        battle.player_torment_turns -= 1
        if battle.player_torment_turns < 0:
            battle.player_torment_turns = 0
    if getattr(battle, "wild_torment_turns", 0) > 0:
        battle.wild_torment_turns -= 1
        if battle.wild_torment_turns < 0:
            battle.wild_torment_turns = 0

    if getattr(battle, "player_uproar_turns", 0) > 0:
        battle.player_uproar_turns -= 1
        if battle.player_uproar_turns < 0:
            battle.player_uproar_turns = 0
    if getattr(battle, "wild_uproar_turns", 0) > 0:
        battle.wild_uproar_turns -= 1
        if battle.wild_uproar_turns < 0:
            battle.wild_uproar_turns = 0

    if getattr(battle, "player_yawn_turns", 0) > 0:
        battle.player_yawn_turns -= 1
        if battle.player_yawn_turns <= 0:
            battle.player_yawn_turns = 0
            if (
                battle.player_active.current_hp > 0
                and battle.player_active.status is None
                and battle.player_active.ability != "Insomnia"
                and getattr(battle, "player_uproar_turns", 0) <= 0
                and getattr(battle, "wild_uproar_turns", 0) <= 0
            ):
                battle.player_active.status = "slp"
                battle.player_active.status_counter = battle.rng.randint(1, 3)
                logs.append(f"{battle.player_active.name} ngủ gật vì Yawn!")

    if getattr(battle, "wild_yawn_turns", 0) > 0:
        battle.wild_yawn_turns -= 1
        if battle.wild_yawn_turns <= 0:
            battle.wild_yawn_turns = 0
            if (
                battle.wild.current_hp > 0
                and battle.wild.status is None
                and battle.wild.ability != "Insomnia"
                and getattr(battle, "player_uproar_turns", 0) <= 0
                and getattr(battle, "wild_uproar_turns", 0) <= 0
            ):
                battle.wild.status = "slp"
                battle.wild.status_counter = battle.rng.randint(1, 3)
                logs.append(f"{battle.wild.name} ngủ gật vì Yawn!")

    if getattr(battle, "player_wish_turns", 0) > 0:
        battle.player_wish_turns -= 1
        if battle.player_wish_turns <= 0:
            heal = max(1, int(getattr(battle, "player_wish_heal", 0)))
            if battle.player_active.current_hp > 0:
                before = battle.player_active.current_hp
                battle.player_active.current_hp = min(battle.player_active.max_hp, battle.player_active.current_hp + heal)
                actual = battle.player_active.current_hp - before
                if actual > 0:
                    logs.append(f"Wish hồi {actual} HP cho {battle.player_active.name} ({battle.player_active.current_hp}/{battle.player_active.max_hp}).")
            battle.player_wish_turns = 0
            battle.player_wish_heal = 0

    if getattr(battle, "wild_wish_turns", 0) > 0:
        battle.wild_wish_turns -= 1
        if battle.wild_wish_turns <= 0:
            heal = max(1, int(getattr(battle, "wild_wish_heal", 0)))
            if battle.wild.current_hp > 0:
                before = battle.wild.current_hp
                battle.wild.current_hp = min(battle.wild.max_hp, battle.wild.current_hp + heal)
                actual = battle.wild.current_hp - before
                if actual > 0:
                    logs.append(f"Wish hồi {actual} HP cho {battle.wild.name} ({battle.wild.current_hp}/{battle.wild.max_hp}).")
            battle.wild_wish_turns = 0
            battle.wild_wish_heal = 0

    if getattr(battle, "player_embargo_turns", 0) > 0:
        battle.player_embargo_turns -= 1
        if battle.player_embargo_turns < 0:
            battle.player_embargo_turns = 0
    if getattr(battle, "wild_embargo_turns", 0) > 0:
        battle.wild_embargo_turns -= 1
        if battle.wild_embargo_turns < 0:
            battle.wild_embargo_turns = 0

    if getattr(battle, "player_encore_turns", 0) > 0:
        battle.player_encore_turns -= 1
        if battle.player_encore_turns <= 0:
            battle.player_encore_turns = 0
            battle.player_encore_move = None
    if getattr(battle, "wild_encore_turns", 0) > 0:
        battle.wild_encore_turns -= 1
        if battle.wild_encore_turns <= 0:
            battle.wild_encore_turns = 0
            battle.wild_encore_move = None

    if getattr(battle, "player_magnet_rise_turns", 0) > 0:
        battle.player_magnet_rise_turns -= 1
        if battle.player_magnet_rise_turns <= 0:
            battle.player_magnet_rise_turns = 0
            logs.append(f"{battle.player_active.name} không còn lơ lửng bởi Magnet Rise.")
    if getattr(battle, "wild_magnet_rise_turns", 0) > 0:
        battle.wild_magnet_rise_turns -= 1
        if battle.wild_magnet_rise_turns <= 0:
            battle.wild_magnet_rise_turns = 0
            logs.append(f"{battle.wild.name} không còn lơ lửng bởi Magnet Rise.")

    if getattr(battle, "player_doom_desire_turns", 0) > 0:
        battle.player_doom_desire_turns -= 1
        if battle.player_doom_desire_turns <= 0 and battle.player_active.current_hp > 0:
            dmg = max(0, int(getattr(battle, "player_doom_desire_damage", 0)))
            if dmg > 0:
                applied = min(dmg, battle.player_active.current_hp)
                battle.player_active.current_hp = max(0, battle.player_active.current_hp - applied)
                logs.append(f"Doom Desire giáng xuống {battle.player_active.name}, gây {applied} sát thương!")
            battle.player_doom_desire_turns = 0
            battle.player_doom_desire_damage = 0

    if getattr(battle, "wild_doom_desire_turns", 0) > 0:
        battle.wild_doom_desire_turns -= 1
        if battle.wild_doom_desire_turns <= 0 and battle.wild.current_hp > 0:
            dmg = max(0, int(getattr(battle, "wild_doom_desire_damage", 0)))
            if dmg > 0:
                applied = min(dmg, battle.wild.current_hp)
                battle.wild.current_hp = max(0, battle.wild.current_hp - applied)
                logs.append(f"Doom Desire giáng xuống {battle.wild.name}, gây {applied} sát thương!")
            battle.wild_doom_desire_turns = 0
            battle.wild_doom_desire_damage = 0

    if getattr(battle, "player_future_sight_turns", 0) > 0:
        battle.player_future_sight_turns -= 1
        if battle.player_future_sight_turns <= 0 and battle.player_active.current_hp > 0:
            dmg = max(0, int(getattr(battle, "player_future_sight_damage", 0)))
            if dmg > 0:
                applied = min(dmg, battle.player_active.current_hp)
                battle.player_active.current_hp = max(0, battle.player_active.current_hp - applied)
                logs.append(f"Future Sight đánh trúng {battle.player_active.name}, gây {applied} sát thương!")
            battle.player_future_sight_turns = 0
            battle.player_future_sight_damage = 0

    if getattr(battle, "wild_future_sight_turns", 0) > 0:
        battle.wild_future_sight_turns -= 1
        if battle.wild_future_sight_turns <= 0 and battle.wild.current_hp > 0:
            dmg = max(0, int(getattr(battle, "wild_future_sight_damage", 0)))
            if dmg > 0:
                applied = min(dmg, battle.wild.current_hp)
                battle.wild.current_hp = max(0, battle.wild.current_hp - applied)
                logs.append(f"Future Sight đánh trúng {battle.wild.name}, gây {applied} sát thương!")
            battle.wild_future_sight_turns = 0
            battle.wild_future_sight_damage = 0

    if getattr(battle, "player_cannonade_turns", 0) > 0:
        if battle.player_active.current_hp > 0 and "Water" not in battle.player_active.types and battle.player_active.ability != "Magic Guard":
            dmg = max(1, battle.player_active.max_hp // 6)
            battle.player_active.current_hp = max(0, battle.player_active.current_hp - dmg)
            logs.append(f"G-Max Cannonade gây {dmg} sát thương lên {battle.player_active.name}.")
        battle.player_cannonade_turns -= 1

    if getattr(battle, "wild_cannonade_turns", 0) > 0:
        if battle.wild.current_hp > 0 and "Water" not in battle.wild.types and battle.wild.ability != "Magic Guard":
            dmg = max(1, battle.wild.max_hp // 6)
            battle.wild.current_hp = max(0, battle.wild.current_hp - dmg)
            logs.append(f"G-Max Cannonade gây {dmg} sát thương lên {battle.wild.name}.")
        battle.wild_cannonade_turns -= 1

    if getattr(battle, "player_vine_lash_turns", 0) > 0:
        if battle.player_active.current_hp > 0 and "Grass" not in battle.player_active.types and battle.player_active.ability != "Magic Guard":
            dmg = max(1, battle.player_active.max_hp // 6)
            battle.player_active.current_hp = max(0, battle.player_active.current_hp - dmg)
            logs.append(f"G-Max Vine Lash gây {dmg} sát thương lên {battle.player_active.name}.")
        battle.player_vine_lash_turns -= 1

    if getattr(battle, "wild_vine_lash_turns", 0) > 0:
        if battle.wild.current_hp > 0 and "Grass" not in battle.wild.types and battle.wild.ability != "Magic Guard":
            dmg = max(1, battle.wild.max_hp // 6)
            battle.wild.current_hp = max(0, battle.wild.current_hp - dmg)
            logs.append(f"G-Max Vine Lash gây {dmg} sát thương lên {battle.wild.name}.")
        battle.wild_vine_lash_turns -= 1

    if getattr(battle, "player_wildfire_turns", 0) > 0:
        if battle.player_active.current_hp > 0 and "Fire" not in battle.player_active.types and battle.player_active.ability != "Magic Guard":
            dmg = max(1, battle.player_active.max_hp // 6)
            battle.player_active.current_hp = max(0, battle.player_active.current_hp - dmg)
            logs.append(f"G-Max Wildfire gây {dmg} sát thương lên {battle.player_active.name}.")
        battle.player_wildfire_turns -= 1

    if getattr(battle, "wild_wildfire_turns", 0) > 0:
        if battle.wild.current_hp > 0 and "Fire" not in battle.wild.types and battle.wild.ability != "Magic Guard":
            dmg = max(1, battle.wild.max_hp // 6)
            battle.wild.current_hp = max(0, battle.wild.current_hp - dmg)
            logs.append(f"G-Max Wildfire gây {dmg} sát thương lên {battle.wild.name}.")
        battle.wild_wildfire_turns -= 1

    if getattr(battle, "player_volcalith_turns", 0) > 0:
        if battle.player_active.current_hp > 0 and "Rock" not in battle.player_active.types and battle.player_active.ability != "Magic Guard":
            dmg = max(1, battle.player_active.max_hp // 6)
            battle.player_active.current_hp = max(0, battle.player_active.current_hp - dmg)
            logs.append(f"G-Max Volcalith gây {dmg} sát thương lên {battle.player_active.name}.")
        battle.player_volcalith_turns -= 1

    if getattr(battle, "wild_volcalith_turns", 0) > 0:
        if battle.wild.current_hp > 0 and "Rock" not in battle.wild.types and battle.wild.ability != "Magic Guard":
            dmg = max(1, battle.wild.max_hp // 6)
            battle.wild.current_hp = max(0, battle.wild.current_hp - dmg)
            logs.append(f"G-Max Volcalith gây {dmg} sát thương lên {battle.wild.name}.")
        battle.wild_volcalith_turns -= 1

    if getattr(battle, "player_glaive_rush_vulnerable_turns", 0) > 0:
        battle.player_glaive_rush_vulnerable_turns -= 1
    if getattr(battle, "wild_glaive_rush_vulnerable_turns", 0) > 0:
        battle.wild_glaive_rush_vulnerable_turns -= 1

    if getattr(battle, "player_aqua_ring", False) and battle.player_active.current_hp > 0:
        if battle.player_active.current_hp < battle.player_active.max_hp:
            heal = max(1, battle.player_active.max_hp // 16)
            before = battle.player_active.current_hp
            battle.player_active.current_hp = min(battle.player_active.max_hp, battle.player_active.current_hp + heal)
            actual = battle.player_active.current_hp - before
            if actual > 0:
                logs.append(
                    f"Aqua Ring hồi {actual} HP cho {battle.player_active.name} ({battle.player_active.current_hp}/{battle.player_active.max_hp})."
                )

    if getattr(battle, "wild_aqua_ring", False) and battle.wild.current_hp > 0:
        if battle.wild.current_hp < battle.wild.max_hp:
            heal = max(1, battle.wild.max_hp // 16)
            before = battle.wild.current_hp
            battle.wild.current_hp = min(battle.wild.max_hp, battle.wild.current_hp + heal)
            actual = battle.wild.current_hp - before
            if actual > 0:
                logs.append(f"Aqua Ring hồi {actual} HP cho {battle.wild.name} ({battle.wild.current_hp}/{battle.wild.max_hp}).")

    if getattr(battle, "player_trapped_turns", 0) > 0:
        battle.player_trapped_turns -= 1
    if getattr(battle, "wild_trapped_turns", 0) > 0:
        battle.wild_trapped_turns -= 1

    if getattr(battle, "player_bound_turns", 0) > 0 and battle.player_active.current_hp > 0:
        if battle.player_active.ability != "Magic Guard":
            divisor = max(1, int(getattr(battle, "player_bound_damage_divisor", 8)))
            dmg = max(1, battle.player_active.max_hp // divisor)
            battle.player_active.current_hp = max(0, battle.player_active.current_hp - dmg)
            logs.append(
                f"{battle.player_active.name} bị sát thương từ Bind {dmg} HP ({battle.player_active.current_hp}/{battle.player_active.max_hp})."
            )
        battle.player_bound_turns -= 1
        if battle.player_bound_turns <= 0:
            battle.player_bound_damage_divisor = 8

    if getattr(battle, "wild_bound_turns", 0) > 0 and battle.wild.current_hp > 0:
        if battle.wild.ability != "Magic Guard":
            divisor = max(1, int(getattr(battle, "wild_bound_damage_divisor", 8)))
            dmg = max(1, battle.wild.max_hp // divisor)
            battle.wild.current_hp = max(0, battle.wild.current_hp - dmg)
            logs.append(f"{battle.wild.name} bị sát thương từ Bind {dmg} HP ({battle.wild.current_hp}/{battle.wild.max_hp}).")
        battle.wild_bound_turns -= 1
        if battle.wild_bound_turns <= 0:
            battle.wild_bound_damage_divisor = 8

    if getattr(battle, "player_ingrain", False) and battle.player_active.current_hp > 0:
        battle.player_trapped_turns = max(battle.player_trapped_turns, 1)
        if battle.player_active.current_hp < battle.player_active.max_hp:
            heal = max(1, battle.player_active.max_hp // 16)
            before = battle.player_active.current_hp
            battle.player_active.current_hp = min(battle.player_active.max_hp, battle.player_active.current_hp + heal)
            actual = battle.player_active.current_hp - before
            if actual > 0:
                logs.append(f"Ingrain hồi {actual} HP cho {battle.player_active.name} ({battle.player_active.current_hp}/{battle.player_active.max_hp}).")

    if getattr(battle, "wild_ingrain", False) and battle.wild.current_hp > 0:
        battle.wild_trapped_turns = max(battle.wild_trapped_turns, 1)
        if battle.wild.current_hp < battle.wild.max_hp:
            heal = max(1, battle.wild.max_hp // 16)
            before = battle.wild.current_hp
            battle.wild.current_hp = min(battle.wild.max_hp, battle.wild.current_hp + heal)
            actual = battle.wild.current_hp - before
            if actual > 0:
                logs.append(f"Ingrain hồi {actual} HP cho {battle.wild.name} ({battle.wild.current_hp}/{battle.wild.max_hp}).")

    if getattr(battle, "player_cursed", False) and battle.player_active.current_hp > 0:
        if battle.player_active.ability != "Magic Guard":
            dmg = max(1, battle.player_active.max_hp // 4)
            battle.player_active.current_hp = max(0, battle.player_active.current_hp - dmg)
            logs.append(f"{battle.player_active.name} bị Curse rút {dmg} HP ({battle.player_active.current_hp}/{battle.player_active.max_hp}).")

    if getattr(battle, "wild_cursed", False) and battle.wild.current_hp > 0:
        if battle.wild.ability != "Magic Guard":
            dmg = max(1, battle.wild.max_hp // 4)
            battle.wild.current_hp = max(0, battle.wild.current_hp - dmg)
            logs.append(f"{battle.wild.name} bị Curse rút {dmg} HP ({battle.wild.current_hp}/{battle.wild.max_hp}).")

    if getattr(battle, "player_nightmare", False):
        if battle.player_active.status == "slp" and battle.player_active.current_hp > 0 and battle.player_active.ability != "Magic Guard":
            dmg = max(1, battle.player_active.max_hp // 4)
            battle.player_active.current_hp = max(0, battle.player_active.current_hp - dmg)
            logs.append(f"Nightmare rút {dmg} HP của {battle.player_active.name} ({battle.player_active.current_hp}/{battle.player_active.max_hp}).")
        elif battle.player_active.status != "slp":
            battle.player_nightmare = False

    if getattr(battle, "wild_nightmare", False):
        if battle.wild.status == "slp" and battle.wild.current_hp > 0 and battle.wild.ability != "Magic Guard":
            dmg = max(1, battle.wild.max_hp // 4)
            battle.wild.current_hp = max(0, battle.wild.current_hp - dmg)
            logs.append(f"Nightmare rút {dmg} HP của {battle.wild.name} ({battle.wild.current_hp}/{battle.wild.max_hp}).")
        elif battle.wild.status != "slp":
            battle.wild_nightmare = False

    if getattr(battle, "player_octolock", False) and battle.player_active.current_hp > 0:
        battle.player_trapped_turns = max(battle.player_trapped_turns, 1)
        changed_def, text_def = battle._change_stat_stage(battle.player_active, "defense", -1)
        changed_spd, text_spd = battle._change_stat_stage(battle.player_active, "sp_defense", -1)
        if changed_def:
            logs.append(f"Octolock làm Defense của {battle.player_active.name} giảm {text_def}.")
        if changed_spd:
            logs.append(f"Octolock làm Sp. Defense của {battle.player_active.name} giảm {text_spd}.")

    if getattr(battle, "wild_octolock", False) and battle.wild.current_hp > 0:
        battle.wild_trapped_turns = max(battle.wild_trapped_turns, 1)
        changed_def, text_def = battle._change_stat_stage(battle.wild, "defense", -1)
        changed_spd, text_spd = battle._change_stat_stage(battle.wild, "sp_defense", -1)
        if changed_def:
            logs.append(f"Octolock làm Defense của {battle.wild.name} giảm {text_def}.")
        if changed_spd:
            logs.append(f"Octolock làm Sp. Defense của {battle.wild.name} giảm {text_spd}.")

    if getattr(battle, "player_perish_song_turns", 0) > 0 and battle.player_active.current_hp > 0:
        battle.player_perish_song_turns -= 1
        if battle.player_perish_song_turns > 0:
            logs.append(f"Perish Song của {battle.player_active.name}: còn {battle.player_perish_song_turns} lượt.")
        else:
            battle.player_active.current_hp = 0
            logs.append(f"{battle.player_active.name} gục vì Perish Song!")

    if getattr(battle, "wild_perish_song_turns", 0) > 0 and battle.wild.current_hp > 0:
        battle.wild_perish_song_turns -= 1
        if battle.wild_perish_song_turns > 0:
            logs.append(f"Perish Song của {battle.wild.name}: còn {battle.wild_perish_song_turns} lượt.")
        else:
            battle.wild.current_hp = 0
            logs.append(f"{battle.wild.name} gục vì Perish Song!")

    if getattr(battle, "player_salt_cure_turns", 0) > 0 and battle.player_active.current_hp > 0:
        if battle.player_active.ability != "Magic Guard":
            ratio = 4 if ("Water" in battle.player_active.types or "Steel" in battle.player_active.types) else 8
            dmg = max(1, battle.player_active.max_hp // ratio)
            battle.player_active.current_hp = max(0, battle.player_active.current_hp - dmg)
            logs.append(f"Salt Cure gây {dmg} sát thương lên {battle.player_active.name} ({battle.player_active.current_hp}/{battle.player_active.max_hp}).")
        battle.player_salt_cure_turns -= 1

    if getattr(battle, "wild_salt_cure_turns", 0) > 0 and battle.wild.current_hp > 0:
        if battle.wild.ability != "Magic Guard":
            ratio = 4 if ("Water" in battle.wild.types or "Steel" in battle.wild.types) else 8
            dmg = max(1, battle.wild.max_hp // ratio)
            battle.wild.current_hp = max(0, battle.wild.current_hp - dmg)
            logs.append(f"Salt Cure gây {dmg} sát thương lên {battle.wild.name} ({battle.wild.current_hp}/{battle.wild.max_hp}).")
        battle.wild_salt_cure_turns -= 1

    if getattr(battle, "player_syrup_bomb_turns", 0) > 0 and battle.player_active.current_hp > 0:
        battle.player_syrup_bomb_turns -= 1
        changed, stage_text = battle._change_stat_stage(battle.player_active, "speed", -1)
        if changed:
            logs.append(f"Syrup Bomb làm Speed của {battle.player_active.name} giảm {stage_text}.")

    if getattr(battle, "wild_syrup_bomb_turns", 0) > 0 and battle.wild.current_hp > 0:
        battle.wild_syrup_bomb_turns -= 1
        changed, stage_text = battle._change_stat_stage(battle.wild, "speed", -1)
        if changed:
            logs.append(f"Syrup Bomb làm Speed của {battle.wild.name} giảm {stage_text}.")

    if getattr(battle, "player_roost_original_types", None):
        battle.player_active.types = list(battle.player_roost_original_types)
        battle.player_roost_original_types = None

    if getattr(battle, "wild_roost_original_types", None):
        battle.wild.types = list(battle.wild_roost_original_types)
        battle.wild_roost_original_types = None

    return logs


def _is_grounded(pokemon: Any) -> bool:
    if getattr(pokemon, "ability", "") == "Levitate":
        return False
    return "Flying" not in getattr(pokemon, "types", [])


def apply_weather_and_terrain_residuals(battle: Any) -> list[str]:
    logs: list[str] = []
    battlers = [battle.player_active, battle.wild]

    if getattr(battle, "weather", None) == "sandstorm" and getattr(battle, "weather_turns", 0) > 0:
        for pokemon in battlers:
            if pokemon.current_hp <= 0:
                continue
            if pokemon.ability == "Magic Guard":
                continue
            if battle._held_item_name(pokemon) == "safety goggles":
                continue
            if any(t in {"Rock", "Ground", "Steel"} for t in pokemon.types):
                continue
            damage = max(1, pokemon.max_hp // 16)
            pokemon.current_hp = max(0, pokemon.current_hp - damage)
            logs.append(f"Cát bão gây {damage} sát thương lên {pokemon.name} ({pokemon.current_hp}/{pokemon.max_hp}).")

    if getattr(battle, "terrain", None) == "grassy terrain" and getattr(battle, "terrain_turns", 0) > 0:
        for pokemon in battlers:
            if pokemon.current_hp <= 0 or not _is_grounded(pokemon):
                continue
            if pokemon.current_hp >= pokemon.max_hp:
                continue
            heal = max(1, pokemon.max_hp // 16)
            before = pokemon.current_hp
            pokemon.current_hp = min(pokemon.max_hp, pokemon.current_hp + heal)
            actual = pokemon.current_hp - before
            if actual > 0:
                logs.append(f"Grassy Terrain hồi {actual} HP cho {pokemon.name} ({pokemon.current_hp}/{pokemon.max_hp}).")

    return logs


def decrement_field_conditions(battle: Any) -> list[str]:
    logs: list[str] = []

    if getattr(battle, "weather", None) and getattr(battle, "weather_turns", 0) > 0:
        battle.weather_turns -= 1
        if battle.weather_turns <= 0:
            ended_weather = battle.weather
            battle.weather = None
            battle.weather_turns = 0
            logs.append(f"Thời tiết {ended_weather} đã tan.")

    if getattr(battle, "terrain", None) and getattr(battle, "terrain_turns", 0) > 0:
        battle.terrain_turns -= 1
        if battle.terrain_turns <= 0:
            ended_terrain = battle.terrain
            battle.terrain = None
            battle.terrain_turns = 0
            logs.append(f"Terrain {ended_terrain} đã biến mất.")

    if getattr(battle, "trick_room_turns", 0) > 0:
        battle.trick_room_turns -= 1
        if battle.trick_room_turns <= 0:
            battle.trick_room_turns = 0
            logs.append("Trick Room đã hết hiệu lực.")

    if getattr(battle, "wonder_room_turns", 0) > 0:
        battle.wonder_room_turns -= 1
        if battle.wonder_room_turns <= 0:
            battle.wonder_room_turns = 0
            logs.append("Wonder Room đã hết hiệu lực.")

    if getattr(battle, "gravity_turns", 0) > 0:
        battle.gravity_turns -= 1
        if battle.gravity_turns <= 0:
            battle.gravity_turns = 0
            logs.append("Gravity đã hết hiệu lực.")

    if getattr(battle, "magic_room_turns", 0) > 0:
        battle.magic_room_turns -= 1
        if battle.magic_room_turns <= 0:
            battle.magic_room_turns = 0
            logs.append("Magic Room đã hết hiệu lực.")

    if getattr(battle, "mud_sport_turns", 0) > 0:
        battle.mud_sport_turns -= 1
        if battle.mud_sport_turns <= 0:
            battle.mud_sport_turns = 0
            logs.append("Mud Sport đã hết hiệu lực.")

    if getattr(battle, "water_sport_turns", 0) > 0:
        battle.water_sport_turns -= 1
        if battle.water_sport_turns <= 0:
            battle.water_sport_turns = 0
            logs.append("Water Sport đã hết hiệu lực.")

    return logs


def decrement_side_conditions(battle: Any) -> None:
    if battle.player_reflect_turns > 0:
        battle.player_reflect_turns -= 1
    if battle.player_light_screen_turns > 0:
        battle.player_light_screen_turns -= 1
    if battle.wild_reflect_turns > 0:
        battle.wild_reflect_turns -= 1
    if battle.wild_light_screen_turns > 0:
        battle.wild_light_screen_turns -= 1
    if getattr(battle, "player_lucky_chant_turns", 0) > 0:
        battle.player_lucky_chant_turns -= 1
    if getattr(battle, "wild_lucky_chant_turns", 0) > 0:
        battle.wild_lucky_chant_turns -= 1
    if getattr(battle, "player_mist_turns", 0) > 0:
        battle.player_mist_turns -= 1
    if getattr(battle, "wild_mist_turns", 0) > 0:
        battle.wild_mist_turns -= 1
    if getattr(battle, "player_safeguard_turns", 0) > 0:
        battle.player_safeguard_turns -= 1
    if getattr(battle, "wild_safeguard_turns", 0) > 0:
        battle.wild_safeguard_turns -= 1
    if getattr(battle, "player_tailwind_turns", 0) > 0:
        battle.player_tailwind_turns -= 1
    if getattr(battle, "wild_tailwind_turns", 0) > 0:
        battle.wild_tailwind_turns -= 1


def apply_leech_seed_drain(battle: Any) -> list[str]:
    logs: list[str] = []
    if battle.player_seeded and battle.player_active.current_hp > 0 and battle.wild.current_hp > 0:
        if battle.player_active.ability == "Magic Guard":
            logs.append(f"{battle.player_active.name} được Magic Guard bảo vệ khỏi Leech Seed.")
        else:
            damage = max(1, battle.player_active.max_hp // 8)
            actual = min(damage, battle.player_active.current_hp)
            battle.player_active.current_hp -= actual
            heal_source = actual
            if battle._held_item_name(battle.wild) == "big root":
                heal_source = max(1, int(heal_source * 1.3))
            heal = min(heal_source, battle.wild.max_hp - battle.wild.current_hp)
            battle.wild.current_hp += heal
            logs.append(
                f"Leech Seed hút {actual} HP từ {battle.player_active.name} và hồi {heal} HP cho {battle.wild.name}."
            )

    if battle.wild_seeded and battle.wild.current_hp > 0 and battle.player_active.current_hp > 0:
        if battle.wild.ability == "Magic Guard":
            logs.append(f"{battle.wild.name} được Magic Guard bảo vệ khỏi Leech Seed.")
        else:
            damage = max(1, battle.wild.max_hp // 8)
            actual = min(damage, battle.wild.current_hp)
            battle.wild.current_hp -= actual
            heal_source = actual
            if battle._held_item_name(battle.player_active) == "big root":
                heal_source = max(1, int(heal_source * 1.3))
            heal = min(heal_source, battle.player_active.max_hp - battle.player_active.current_hp)
            battle.player_active.current_hp += heal
            logs.append(
                f"Leech Seed hút {actual} HP từ {battle.wild.name} và hồi {heal} HP cho {battle.player_active.name}."
            )
    return logs


def apply_switch_in_hazards(battle: Any, pokemon: Any, is_player: bool) -> list[str]:
    logs: list[str] = []
    spikes_layers = battle.player_spikes_layers if is_player else battle.wild_spikes_layers
    toxic_spikes_layers = battle.player_toxic_spikes_layers if is_player else battle.wild_toxic_spikes_layers
    stealth_rock = battle.player_stealth_rock if is_player else battle.wild_stealth_rock
    sticky_web = battle.player_sticky_web if is_player else battle.wild_sticky_web

    if battle._held_item_name(pokemon) in {"heavy-duty boots", "heavy duty boots"}:
        if spikes_layers > 0 or toxic_spikes_layers > 0 or stealth_rock or sticky_web:
            logs.append(f"{pokemon.name} được Heavy-Duty Boots bảo vệ khỏi hazards khi vào sân.")
        return logs

    grounded = battle._is_grounded(pokemon)

    if spikes_layers > 0 and grounded:
        ratio = {1: 1 / 8, 2: 1 / 6, 3: 1 / 4}.get(spikes_layers, 1 / 4)
        damage = max(1, int(pokemon.max_hp * ratio))
        if pokemon.ability != "Magic Guard":
            pokemon.current_hp = max(0, pokemon.current_hp - damage)
            logs.append(f"{pokemon.name} dẫm phải Spikes và mất {damage} HP ({pokemon.current_hp}/{pokemon.max_hp}).")
        else:
            logs.append(f"{pokemon.name} được Magic Guard bảo vệ khỏi Spikes.")

    if stealth_rock:
        rock_mul = battle.game_data.type_multiplier("Rock", pokemon.types)
        damage = max(1, int((pokemon.max_hp / 8) * rock_mul))
        if pokemon.ability != "Magic Guard":
            pokemon.current_hp = max(0, pokemon.current_hp - damage)
            logs.append(
                f"Stealth Rock gây {damage} sát thương lên {pokemon.name} ({pokemon.current_hp}/{pokemon.max_hp})."
            )
        else:
            logs.append(f"{pokemon.name} được Magic Guard bảo vệ khỏi Stealth Rock.")

    if toxic_spikes_layers > 0 and grounded and pokemon.current_hp > 0 and pokemon.status is None:
        if "Poison" in pokemon.types:
            if is_player:
                battle.player_toxic_spikes_layers = 0
            else:
                battle.wild_toxic_spikes_layers = 0
            logs.append(f"{pokemon.name} hấp thụ Toxic Spikes khỏi sân.")
        elif "Steel" not in pokemon.types:
            if toxic_spikes_layers >= 2:
                pokemon.status = "tox"
                pokemon.status_counter = 1
                logs.append(f"{pokemon.name} bị Badly Poisoned do Toxic Spikes.")
            else:
                pokemon.status = "psn"
                pokemon.status_counter = 0
                logs.append(f"{pokemon.name} bị Poison do Toxic Spikes.")

    if sticky_web and grounded and pokemon.current_hp > 0:
        changed, stage_text = battle._change_stat_stage(pokemon, "speed", -1)
        if changed:
            logs.append(f"{pokemon.name} bị Sticky Web làm giảm Speed {stage_text} khi vào sân.")

    return logs


def residual_status_damage(battle: Any, pokemon: Any) -> list[str]:
    logs: list[str] = []
    if pokemon.current_hp <= 0 or pokemon.status is None:
        return logs
    if pokemon.ability == "Magic Guard":
        return logs

    if pokemon.status == "brn":
        damage = max(1, pokemon.max_hp // 16)
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        logs.append(f"{pokemon.name} bị Burn, mất {damage} HP ({pokemon.current_hp}/{pokemon.max_hp}).")
        return logs

    if pokemon.status == "psn":
        damage = max(1, pokemon.max_hp // 16)
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        logs.append(f"{pokemon.name} bị Poison, mất {damage} HP ({pokemon.current_hp}/{pokemon.max_hp}).")
        return logs

    if pokemon.status == "tox":
        if pokemon.status_counter <= 0:
            pokemon.status_counter = 1
        damage = max(1, (pokemon.max_hp * pokemon.status_counter) // 16)
        pokemon.current_hp = max(0, pokemon.current_hp - damage)
        logs.append(
            f"{pokemon.name} bị Badly Poisoned, mất {damage} HP ({pokemon.current_hp}/{pokemon.max_hp})."
        )
        pokemon.status_counter = min(15, pokemon.status_counter + 1)
        return logs

    return logs
