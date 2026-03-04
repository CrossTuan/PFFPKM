from __future__ import annotations

from typing import Any


MOVE_PRIORITY_OVERRIDES: dict[str, int] = {
    "Protect": 4,
    "Detect": 4,
    "Baneful Bunker": 4,
    "Burning Bulwark": 4,
    "Accelerock": 1,
    "Baby-Doll Eyes": 1,
    "Quick Attack": 1,
    "Mach Punch": 1,
    "Bullet Punch": 1,
    "Aqua Jet": 1,
    "Water Shuriken": 1,
    "Ice Shard": 1,
    "Vacuum Wave": 1,
    "Shadow Sneak": 1,
    "Sucker Punch": 1,
    "Thunderclap": 1,
    "Extreme Speed": 2,
    "Zippy Zap": 2,
    "First Impression": 2,
    "Fake Out": 3,
    "Feint": 2,
    "Jet Punch": 1,
    "King's Shield": 4,
    "Max Guard": 4,
    "Obstruct": 4,
    "Spiky Shield": 4,
    "Snatch": 4,
    "Quick Guard": 3,
    "Upper Hand": 3,
    "Vital Throw": -1,
}


STAGE_MOVES: dict[str, tuple[str, int]] = {
    "Growl": ("attack", -1),
    "Tail Whip": ("defense", -1),
    "Leer": ("defense", -1),
    "Swords Dance": ("attack", 2),
    "Agility": ("speed", 2),
    "Acid Armor": ("defense", 2),
    "Amnesia": ("sp_defense", 2),
    "Autotomize": ("speed", 2),
    "Barrier": ("defense", 2),
    "Baby-Doll Eyes": ("attack", -1),
    "Calm Mind": ("sp_attack", 1),
    "Iron Defense": ("defense", 2),
    "Meditate": ("attack", 1),
    "Nasty Plot": ("sp_attack", 2),
    "Rock Polish": ("speed", 2),
    "Sharpen": ("attack", 1),
    "Scary Face": ("speed", -2),
    "Screech": ("defense", -2),
    "Shelter": ("defense", 2),
    "String Shot": ("speed", -2),
    "Withdraw": ("defense", 1),
}


STATUS_MOVES: dict[str, str] = {
    "Thunder Wave": "par",
    "Will-O-Wisp": "brn",
    "Poison Powder": "psn",
    "Toxic": "tox",
    "Sleep Powder": "slp",
    "Sing": "slp",
    "Spore": "slp",
    "Glare": "par",
    "Grass Whistle": "slp",
    "Hypnosis": "slp",
    "Lovely Kiss": "slp",
    "Poison Gas": "psn",
    "Stun Spore": "par",
}


HEALING_MOVES: dict[str, float] = {
    "Recover": 0.5,
    "Roost": 0.5,
    "Milk Drink": 0.5,
}


def get_move_priority(move_name: str, raw_priority: Any = None) -> int:
    if raw_priority is not None:
        text = str(raw_priority).strip().replace("*", "")
        if text:
            try:
                return int(float(text))
            except ValueError:
                pass
    return MOVE_PRIORITY_OVERRIDES.get(move_name, 0)


def get_default_target(move_name: str) -> str:
    if move_name == "Growl":
        return "all-adjacent-foes"
    return "any"


def resolve_status_move_effect(battle: Any, attacker: Any, defender: Any, move: Any) -> str | None:
    move_name = move.name
    held_item = battle._held_item_name(attacker) if hasattr(battle, "_held_item_name") else (
        "" if getattr(battle, "magic_room_turns", 0) > 0 else (getattr(attacker, "hold_item", "") or "").strip().lower()
    )

    if move_name == "Growl":
        parts = [f"{attacker.name} dùng Growl!"]

        if battle._can_trigger_normalium_z(attacker, move):
            battle.player_z_power_used = True
            changed_user, stage_text_user = battle._change_stat_stage(attacker, "defense", +1)
            if changed_user:
                parts.append(f"Z-Power kích hoạt! {attacker.name} tăng Defense {stage_text_user}.")

        changed_target, stage_text_target = battle._change_stat_stage(defender, "attack", -1)
        if changed_target:
            parts.append(f"{defender.name} bị giảm Attack {stage_text_target}.")
        else:
            parts.append(f"Attack của {defender.name} không thể giảm thêm nữa.")
        return " ".join(parts)

    if move_name in STAGE_MOVES:
        stat_key, delta = STAGE_MOVES[move_name]
        target = attacker if delta > 0 else defender
        changed, stage_text = battle._change_stat_stage(target, stat_key, delta)
        if changed:
            stat_label = {
                "attack": "Attack",
                "defense": "Defense",
                "sp_attack": "Sp. Attack",
                "sp_defense": "Sp. Defense",
                "speed": "Speed",
            }.get(stat_key, stat_key)
            return f"{attacker.name} dùng {move_name}. {target.name} {'tăng' if delta > 0 else 'giảm'} {stat_label} {stage_text}."
        return f"{attacker.name} dùng {move_name}, nhưng chỉ số không thể thay đổi thêm."

    if move_name in STATUS_MOVES:
        return battle._apply_primary_status(attacker, defender, STATUS_MOVES[move_name], move_name)

    if move_name == "Confuse Ray":
        if defender.current_hp <= 0:
            return f"{attacker.name} dùng Confuse Ray, nhưng mục tiêu đã gục."
        if defender.confusion_turns > 0:
            return f"{attacker.name} dùng Confuse Ray, nhưng {defender.name} đã bị Confusion."
        defender.confusion_turns = battle.rng.randint(2, 5)
        return f"{attacker.name} dùng Confuse Ray. {defender.name} bị Confusion."

    if move_name == "Acupressure":
        stat_keys = ["attack", "defense", "sp_attack", "sp_defense", "speed"]
        battle.rng.shuffle(stat_keys)
        for stat_key in stat_keys:
            changed, stage_text = battle._change_stat_stage(attacker, stat_key, +2)
            if changed:
                stat_label = {
                    "attack": "Attack",
                    "defense": "Defense",
                    "sp_attack": "Sp. Attack",
                    "sp_defense": "Sp. Defense",
                    "speed": "Speed",
                }.get(stat_key, stat_key)
                return f"{attacker.name} dùng Acupressure. {attacker.name} tăng mạnh {stat_label} {stage_text}."
        return f"{attacker.name} dùng Acupressure, nhưng mọi chỉ số đã tối đa."

    if move_name == "Aqua Ring":
        if attacker is battle.player_active:
            if battle.player_aqua_ring:
                return f"{attacker.name} đã có Aqua Ring từ trước."
            battle.player_aqua_ring = True
        else:
            if battle.wild_aqua_ring:
                return f"{attacker.name} đã có Aqua Ring từ trước."
            battle.wild_aqua_ring = True
        return f"{attacker.name} dùng Aqua Ring. Một lớp nước bao quanh và sẽ hồi HP mỗi lượt."

    if move_name == "Aromatherapy":
        cured = 0
        if attacker is battle.player_active:
            for pkmn in battle.player.party:
                if pkmn.status is not None:
                    pkmn.status = None
                    pkmn.status_counter = 0
                    cured += 1
        else:
            if attacker.status is not None:
                attacker.status = None
                attacker.status_counter = 0
                cured = 1
        if cured <= 0:
            return f"{attacker.name} dùng Aromatherapy, nhưng không ai có trạng thái để chữa."
        return f"{attacker.name} dùng Aromatherapy và chữa trạng thái cho {cured} Pokémon."

    if move_name == "Baton Pass":
        if attacker is not battle.player_active:
            return f"{attacker.name} dùng Baton Pass, nhưng cơ chế này chưa hỗ trợ cho wild AI."
        options = [
            (idx, pkmn)
            for idx, pkmn in enumerate(battle.player.party)
            if idx != battle.player_active_index and pkmn.current_hp > 0
        ]
        if not options:
            return f"{attacker.name} dùng Baton Pass, nhưng không có Pokémon nào để đổi."
        next_index, next_pokemon = options[0]
        battle.player_seeded = False
        battle.player_aqua_ring = False
        battle.player_trapped_turns = 0
        battle.player_flinched = False
        battle.player_active_index = next_index
        battle.player_infatuated = False
        battle.wild_infatuated = False
        hazard_logs = battle._apply_switch_in_hazards(next_pokemon, is_player=True)
        ability_logs = battle._trigger_switch_in_ability(next_pokemon, is_player=True)
        text = f"{attacker.name} dùng Baton Pass! Bạn đổi sang {next_pokemon.name} và truyền lại stat stages."
        if hazard_logs:
            text += "\n" + "\n".join(hazard_logs)
        if ability_logs:
            text += "\n" + "\n".join(ability_logs)
        return text

    if move_name == "Belly Drum":
        if attacker.current_hp <= attacker.max_hp // 2:
            return f"{attacker.name} không đủ HP để dùng Belly Drum."
        stages = battle._stat_stages_for(attacker)
        current = stages.get("attack", 0)
        if current >= 6:
            return f"{attacker.name} dùng Belly Drum, nhưng Attack đã tối đa."
        cost = max(1, attacker.max_hp // 2)
        attacker.current_hp = max(1, attacker.current_hp - cost)
        delta = 6 - current
        battle._change_stat_stage(attacker, "attack", delta)
        return (
            f"{attacker.name} dùng Belly Drum! Mất {cost} HP ({attacker.current_hp}/{attacker.max_hp}) "
            f"và Attack tăng lên tối đa (+6)."
        )

    if move_name == "Burning Bulwark":
        if battle._try_activate_protect(attacker):
            if attacker is battle.player_active:
                battle.player_burning_bulwark_active = True
            else:
                battle.wild_burning_bulwark_active = True
            return f"{attacker.name} dùng Burning Bulwark và dựng khiên lửa bảo vệ."
        return f"{attacker.name} dùng Burning Bulwark nhưng thất bại do dùng liên tiếp."

    if move_name == "Camouflage":
        attacker.types = ["Normal"]
        return f"{attacker.name} dùng Camouflage và chuyển thành hệ Normal."

    if move_name == "Captivate":
        changed, stage_text = battle._change_stat_stage(defender, "sp_attack", -2)
        if changed:
            return f"{attacker.name} dùng Captivate. Sp. Attack của {defender.name} giảm mạnh {stage_text}."
        return f"{attacker.name} dùng Captivate, nhưng Sp. Attack của {defender.name} không thể giảm thêm."

    if move_name == "Celebrate":
        return f"{attacker.name} dùng Celebrate! Không có hiệu ứng battle."

    if move_name == "Charge":
        changed, stage_text = battle._change_stat_stage(attacker, "sp_defense", +1)
        if attacker is battle.player_active:
            battle.player_charge_boost = True
        else:
            battle.wild_charge_boost = True
        if changed:
            return f"{attacker.name} dùng Charge. Sp. Defense tăng {stage_text}, đòn Electric kế tiếp sẽ mạnh hơn."
        return f"{attacker.name} dùng Charge. Đòn Electric kế tiếp sẽ mạnh hơn."

    if move_name == "Coaching":
        return f"{attacker.name} dùng Coaching, nhưng trận hiện tại là 1v1 nên không có đồng minh để buff."

    if move_name == "Coil":
        changed_atk, atk_text = battle._change_stat_stage(attacker, "attack", +1)
        changed_def, def_text = battle._change_stat_stage(attacker, "defense", +1)
        if not changed_atk and not changed_def:
            return f"{attacker.name} dùng Coil, nhưng Attack/Defense đã tối đa."
        parts = [f"{attacker.name} dùng Coil."]
        if changed_atk:
            parts.append(f"Attack tăng {atk_text}.")
        if changed_def:
            parts.append(f"Defense tăng {def_text}.")
        parts.append("(Accuracy boost chưa được mô phỏng chi tiết).")
        return " ".join(parts)

    if move_name == "Comfide":
        changed, stage_text = battle._change_stat_stage(defender, "sp_attack", -1)
        if changed:
            return f"{attacker.name} dùng Comfide. Sp. Attack của {defender.name} giảm {stage_text}."
        return f"{attacker.name} dùng Comfide, nhưng Sp. Attack của {defender.name} không thể giảm thêm."

    if move_name == "Curse":
        if "Ghost" in attacker.types:
            cost = max(1, attacker.max_hp // 2)
            if attacker.current_hp <= cost:
                return f"{attacker.name} không đủ HP để dùng Curse hệ Ghost."
            attacker.current_hp = max(1, attacker.current_hp - cost)
            if defender is battle.player_active:
                battle.player_cursed = True
            else:
                battle.wild_cursed = True
            return (
                f"{attacker.name} dùng Curse hệ Ghost, mất {cost} HP ({attacker.current_hp}/{attacker.max_hp}) "
                f"và nguyền rủa {defender.name}."
            )
        changed_atk, atk_text = battle._change_stat_stage(attacker, "attack", +1)
        changed_def, def_text = battle._change_stat_stage(attacker, "defense", +1)
        changed_spe, spe_text = battle._change_stat_stage(attacker, "speed", -1)
        parts = [f"{attacker.name} dùng Curse."]
        if changed_atk:
            parts.append(f"Attack tăng {atk_text}.")
        if changed_def:
            parts.append(f"Defense tăng {def_text}.")
        if changed_spe:
            parts.append(f"Speed giảm {spe_text}.")
        return " ".join(parts)

    if move_name == "Conversion":
        if not attacker.moves:
            return f"{attacker.name} dùng Conversion nhưng không có move để tham chiếu hệ."
        first_type = attacker.moves[0].move_type
        attacker.types = [first_type]
        return f"{attacker.name} dùng Conversion và đổi thành hệ {first_type}."

    if move_name == "Doodle":
        target_ability = (defender.ability or "").strip()
        if not target_ability:
            return f"{attacker.name} dùng Doodle nhưng mục tiêu không có Ability để sao chép."
        attacker.ability = target_ability
        if attacker is battle.player_active:
            for idx, pkmn in enumerate(battle.player.party):
                if idx != battle.player_active_index and pkmn.current_hp > 0:
                    pkmn.ability = target_ability
        return f"{attacker.name} dùng Doodle. Ability của bạn (và đồng đội) đổi thành {target_ability}."

    if move_name == "Double Team":
        return f"{attacker.name} dùng Double Team. (Evasion chưa được mô phỏng chi tiết trong engine hiện tại)."

    if move_name == "Dragon Cheer":
        if attacker is battle.player_active:
            battle.player_dragon_cheer_turns = max(battle.player_dragon_cheer_turns, 2)
        else:
            battle.wild_dragon_cheer_turns = max(battle.wild_dragon_cheer_turns, 2)
        return f"{attacker.name} dùng Dragon Cheer. Tỉ lệ chí mạng của phe này được tăng trong 2 lượt."

    if move_name == "Dragon Dance":
        changed_atk, atk_text = battle._change_stat_stage(attacker, "attack", +1)
        changed_spe, spe_text = battle._change_stat_stage(attacker, "speed", +1)
        if not changed_atk and not changed_spe:
            return f"{attacker.name} dùng Dragon Dance, nhưng Attack/Speed đã tối đa."
        parts = [f"{attacker.name} dùng Dragon Dance."]
        if changed_atk:
            parts.append(f"Attack tăng {atk_text}.")
        if changed_spe:
            parts.append(f"Speed tăng {spe_text}.")
        return " ".join(parts)

    if move_name == "Conversion 2":
        opp_last_type = battle.wild_last_move_type if attacker is battle.player_active else battle.player_last_move_type
        if not opp_last_type:
            return f"{attacker.name} dùng Conversion 2 nhưng chưa có đòn gần nhất của đối thủ để tham chiếu."
        resist_map = {
            "Fire": "Water",
            "Water": "Grass",
            "Grass": "Fire",
            "Electric": "Ground",
            "Ground": "Grass",
            "Fighting": "Psychic",
            "Psychic": "Dark",
            "Dark": "Fairy",
            "Dragon": "Fairy",
            "Ice": "Steel",
            "Rock": "Steel",
            "Ghost": "Normal",
            "Poison": "Steel",
            "Bug": "Fire",
            "Steel": "Fire",
            "Flying": "Electric",
            "Normal": "Rock",
            "Fairy": "Steel",
        }
        new_type = resist_map.get(opp_last_type, "Normal")
        attacker.types = [new_type]
        return f"{attacker.name} dùng Conversion 2 và đổi sang hệ {new_type} để kháng {opp_last_type}."

    if move_name == "Copycat":
        copied_name = battle.wild_last_move_name if attacker is battle.player_active else battle.player_last_move_name
        if not copied_name or copied_name == "Copycat":
            return f"{attacker.name} dùng Copycat nhưng không có đòn hợp lệ để sao chép."
        source = next((mv for mv in battle.game_data.moves if mv.name == copied_name), None)
        if source is None:
            return f"{attacker.name} dùng Copycat nhưng không tìm thấy dữ liệu move {copied_name}."
        copied_move = battle._build_moveset_from_data(source)
        copied_move.current_pp = 1
        copied_move.max_pp = 1
        copied_move.base_pp = 1
        copied_move.pp_up_level = 0
        return battle._execute_move(attacker, defender, copied_move)

    if move_name == "Cosmic Power":
        changed_def, def_text = battle._change_stat_stage(attacker, "defense", +1)
        changed_spd, spd_text = battle._change_stat_stage(attacker, "sp_defense", +1)
        if not changed_def and not changed_spd:
            return f"{attacker.name} dùng Cosmic Power, nhưng Defense/Sp. Defense đã tối đa."
        parts = [f"{attacker.name} dùng Cosmic Power."]
        if changed_def:
            parts.append(f"Defense tăng {def_text}.")
        if changed_spd:
            parts.append(f"Sp. Defense tăng {spd_text}.")
        return " ".join(parts)

    if move_name == "Cotton Guard":
        changed, stage_text = battle._change_stat_stage(attacker, "defense", +3)
        if changed:
            return f"{attacker.name} dùng Cotton Guard. Defense tăng mạnh {stage_text}."
        return f"{attacker.name} dùng Cotton Guard, nhưng Defense đã tối đa."

    if move_name == "Cotton Spore":
        changed, stage_text = battle._change_stat_stage(defender, "speed", -2)
        if changed:
            return f"{attacker.name} dùng Cotton Spore. Speed của {defender.name} giảm mạnh {stage_text}."
        return f"{attacker.name} dùng Cotton Spore, nhưng Speed của {defender.name} không thể giảm thêm."

    if move_name == "Court Change":
        (
            battle.player_spikes_layers,
            battle.wild_spikes_layers,
        ) = (
            battle.wild_spikes_layers,
            battle.player_spikes_layers,
        )
        (
            battle.player_toxic_spikes_layers,
            battle.wild_toxic_spikes_layers,
        ) = (
            battle.wild_toxic_spikes_layers,
            battle.player_toxic_spikes_layers,
        )
        (
            battle.player_stealth_rock,
            battle.wild_stealth_rock,
        ) = (
            battle.wild_stealth_rock,
            battle.player_stealth_rock,
        )
        (
            battle.player_sticky_web,
            battle.wild_sticky_web,
        ) = (
            battle.wild_sticky_web,
            battle.player_sticky_web,
        )
        (
            battle.player_reflect_turns,
            battle.wild_reflect_turns,
        ) = (
            battle.wild_reflect_turns,
            battle.player_reflect_turns,
        )
        (
            battle.player_light_screen_turns,
            battle.wild_light_screen_turns,
        ) = (
            battle.wild_light_screen_turns,
            battle.player_light_screen_turns,
        )
        return f"{attacker.name} dùng Court Change và hoán đổi các hiệu ứng sân giữa hai bên!"

    if move_name == "Crafty Shield":
        if attacker is battle.player_active:
            battle.player_crafty_shield_active = True
        else:
            battle.wild_crafty_shield_active = True
        return f"{attacker.name} dựng Crafty Shield để chặn status move trong lượt này."

    if move_name == "Dark Void":
        return battle._apply_primary_status(attacker, defender, "slp", move_name)

    if move_name == "Decorate":
        changed_atk, atk_text = battle._change_stat_stage(defender, "attack", +2)
        changed_spa, spa_text = battle._change_stat_stage(defender, "sp_attack", +2)
        if not changed_atk and not changed_spa:
            return f"{attacker.name} dùng Decorate, nhưng chỉ số của {defender.name} đã tối đa."
        parts = [f"{attacker.name} dùng Decorate lên {defender.name}."]
        if changed_atk:
            parts.append(f"Attack tăng mạnh {atk_text}.")
        if changed_spa:
            parts.append(f"Sp. Attack tăng mạnh {spa_text}.")
        return " ".join(parts)

    if move_name == "Defend Order":
        changed_def, def_text = battle._change_stat_stage(attacker, "defense", +1)
        changed_spd, spd_text = battle._change_stat_stage(attacker, "sp_defense", +1)
        if not changed_def and not changed_spd:
            return f"{attacker.name} dùng Defend Order, nhưng Defense/Sp. Defense đã tối đa."
        parts = [f"{attacker.name} dùng Defend Order."]
        if changed_def:
            parts.append(f"Defense tăng {def_text}.")
        if changed_spd:
            parts.append(f"Sp. Defense tăng {spd_text}.")
        return " ".join(parts)

    if move_name == "Defense Curl":
        changed, stage_text = battle._change_stat_stage(attacker, "defense", +1)
        if changed:
            return f"{attacker.name} dùng Defense Curl. Defense tăng {stage_text}."
        return f"{attacker.name} dùng Defense Curl, nhưng Defense đã tối đa."

    if move_name == "Defog":
        battle.player_spikes_layers = 0
        battle.player_toxic_spikes_layers = 0
        battle.player_stealth_rock = False
        battle.player_sticky_web = False
        battle.wild_spikes_layers = 0
        battle.wild_toxic_spikes_layers = 0
        battle.wild_stealth_rock = False
        battle.wild_sticky_web = False
        battle.player_reflect_turns = 0
        battle.player_light_screen_turns = 0
        battle.wild_reflect_turns = 0
        battle.wild_light_screen_turns = 0
        return f"{attacker.name} dùng Defog và xóa toàn bộ hazards/screens trên sân."

    if move_name == "Destiny Bond":
        if attacker is battle.player_active:
            battle.player_destiny_bond_active = True
        else:
            battle.wild_destiny_bond_active = True
        return f"{attacker.name} dùng Destiny Bond. Nếu gục trong lượt này, đối thủ sẽ bị kéo theo."

    if move_name == "Detect":
        if battle._try_activate_protect(attacker):
            return f"{attacker.name} dùng Detect và dựng khiên bảo vệ."
        return f"{attacker.name} dùng Detect nhưng thất bại do dùng liên tiếp."

    if move_name == "Disable":
        target_last = battle.player_last_move_name if defender is battle.player_active else battle.wild_last_move_name
        if not target_last:
            return f"{attacker.name} dùng Disable nhưng đối thủ chưa dùng chiêu nào."
        if defender is battle.player_active:
            battle.player_disabled_move = target_last
            battle.player_disable_turns = 4
        else:
            battle.wild_disabled_move = target_last
            battle.wild_disable_turns = 4
        return f"{attacker.name} dùng Disable. {defender.name} bị khóa chiêu {target_last} trong vài lượt."

    if move_name == "Eerie Impulse":
        changed, stage_text = battle._change_stat_stage(defender, "sp_attack", -2)
        if changed:
            return f"{attacker.name} dùng Eerie Impulse. Sp. Attack của {defender.name} giảm mạnh {stage_text}."
        return f"{attacker.name} dùng Eerie Impulse, nhưng Sp. Attack của {defender.name} không thể giảm thêm."

    if move_name == "Electrify":
        if defender is battle.player_active:
            battle.player_electrified = True
        else:
            battle.wild_electrified = True
        return f"{attacker.name} dùng Electrify. Đòn kế tiếp của {defender.name} sẽ bị đổi sang hệ Electric."

    if move_name == "Embargo":
        if defender is battle.player_active:
            battle.player_embargo_turns = max(battle.player_embargo_turns, 5)
        else:
            battle.wild_embargo_turns = max(battle.wild_embargo_turns, 5)
        return f"{attacker.name} dùng Embargo. {defender.name} không thể dùng item trong 5 lượt."

    if move_name == "Encore":
        target_last = battle.player_last_move_name if defender is battle.player_active else battle.wild_last_move_name
        if not target_last:
            return f"{attacker.name} dùng Encore nhưng đối thủ chưa dùng chiêu nào."
        target_move = next((mv for mv in defender.moves if mv.name == target_last), None)
        if target_move is None:
            return f"{attacker.name} dùng Encore nhưng không thể khóa chiêu của {defender.name}."
        if defender is battle.player_active:
            battle.player_encore_move = target_last
            battle.player_encore_turns = 3
        else:
            battle.wild_encore_move = target_last
            battle.wild_encore_turns = 3
        return f"{attacker.name} dùng Encore. {defender.name} bị ép dùng {target_last} trong 3 lượt."

    if move_name == "Endure":
        if battle._try_activate_protect(attacker):
            if attacker is battle.player_active:
                battle.player_endure_active = True
            else:
                battle.wild_endure_active = True
            return f"{attacker.name} dùng Endure. Dù nhận đòn vẫn sẽ còn lại ít nhất 1 HP trong lượt này."
        return f"{attacker.name} dùng Endure nhưng thất bại do dùng liên tiếp."

    if move_name == "Entrainment":
        source_ability = (attacker.ability or "").strip()
        if not source_ability:
            return f"{attacker.name} dùng Entrainment nhưng không có Ability để truyền."
        defender.ability = source_ability
        return f"{attacker.name} dùng Entrainment. Ability của {defender.name} đổi thành {source_ability}."

    if move_name == "Extreme Evoboost":
        boosted: list[str] = []
        for stat_key, label in [
            ("attack", "Attack"),
            ("defense", "Defense"),
            ("sp_attack", "Sp. Attack"),
            ("sp_defense", "Sp. Defense"),
            ("speed", "Speed"),
        ]:
            changed, _ = battle._change_stat_stage(attacker, stat_key, +2)
            if changed:
                boosted.append(label)
        if not boosted:
            return f"{attacker.name} dùng Extreme Evoboost, nhưng các chỉ số đã tối đa."
        return f"{attacker.name} dùng Extreme Evoboost và tăng mạnh: {', '.join(boosted)}."

    if move_name == "Fairy Lock":
        battle.player_trapped_turns = max(battle.player_trapped_turns, 2)
        battle.wild_trapped_turns = max(battle.wild_trapped_turns, 2)
        return f"{attacker.name} dùng Fairy Lock. Cả hai bên bị khóa chạy trốn/đổi Pokémon tới hết lượt kế tiếp."

    if move_name == "Fake Tears":
        changed, stage_text = battle._change_stat_stage(defender, "sp_defense", -2)
        if changed:
            return f"{attacker.name} dùng Fake Tears. Sp. Defense của {defender.name} giảm mạnh {stage_text}."
        return f"{attacker.name} dùng Fake Tears, nhưng Sp. Defense của {defender.name} không thể giảm thêm."

    if move_name == "Feather Dance":
        changed, stage_text = battle._change_stat_stage(defender, "attack", -2)
        if changed:
            return f"{attacker.name} dùng Feather Dance. Attack của {defender.name} giảm mạnh {stage_text}."
        return f"{attacker.name} dùng Feather Dance, nhưng Attack của {defender.name} không thể giảm thêm."

    if move_name == "Fillet Away":
        cost = max(1, attacker.max_hp // 2)
        if attacker.current_hp <= cost:
            return f"{attacker.name} không đủ HP để dùng Fillet Away."
        attacker.current_hp = max(1, attacker.current_hp - cost)
        parts = [f"{attacker.name} dùng Fillet Away, mất {cost} HP ({attacker.current_hp}/{attacker.max_hp})."]
        changed_atk, atk_text = battle._change_stat_stage(attacker, "attack", +2)
        changed_spa, spa_text = battle._change_stat_stage(attacker, "sp_attack", +2)
        changed_spe, spe_text = battle._change_stat_stage(attacker, "speed", +2)
        if changed_atk:
            parts.append(f"Attack tăng mạnh {atk_text}.")
        if changed_spa:
            parts.append(f"Sp. Attack tăng mạnh {spa_text}.")
        if changed_spe:
            parts.append(f"Speed tăng mạnh {spe_text}.")
        return " ".join(parts)

    if move_name == "Flash":
        return f"{attacker.name} dùng Flash. (Hệ thống Accuracy/Evasion stage chưa được mô phỏng chi tiết)."

    if move_name == "Flatter":
        changed, stage_text = battle._change_stat_stage(defender, "sp_attack", +1)
        if defender.confusion_turns <= 0:
            defender.confusion_turns = battle.rng.randint(2, 5)
            if changed:
                return f"{attacker.name} dùng Flatter. Sp. Attack của {defender.name} tăng {stage_text} nhưng bị Confusion!"
            return f"{attacker.name} dùng Flatter. {defender.name} bị Confusion!"
        if changed:
            return f"{attacker.name} dùng Flatter. Sp. Attack của {defender.name} tăng {stage_text}."
        return f"{attacker.name} dùng Flatter, nhưng {defender.name} đã bị Confusion và Sp. Attack không thể tăng thêm."

    if move_name == "Floral Healing":
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể dùng Floral Healing vì đã gục."
        if attacker.current_hp >= attacker.max_hp:
            return f"{attacker.name} dùng Floral Healing, nhưng HP đã đầy."
        ratio = 2 / 3 if battle.terrain == "grassy terrain" and battle.terrain_turns > 0 else 1 / 2
        heal = max(1, int(attacker.max_hp * ratio))
        before = attacker.current_hp
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal)
        actual = attacker.current_hp - before
        return f"{attacker.name} dùng Floral Healing và hồi {actual} HP ({attacker.current_hp}/{attacker.max_hp})."

    if move_name == "Flower Shield":
        boosted: list[str] = []
        if "Grass" in attacker.types:
            changed, stage_text = battle._change_stat_stage(attacker, "defense", +1)
            if changed:
                boosted.append(f"{attacker.name} (Defense {stage_text})")
        if "Grass" in defender.types:
            changed, stage_text = battle._change_stat_stage(defender, "defense", +1)
            if changed:
                boosted.append(f"{defender.name} (Defense {stage_text})")
        if not boosted:
            return f"{attacker.name} dùng Flower Shield, nhưng không có Pokémon hệ Grass nào được tăng Defense."
        return f"{attacker.name} dùng Flower Shield. Tăng Defense cho: {', '.join(boosted)}."

    if move_name == "Focus Energy":
        if attacker is battle.player_active:
            battle.player_focus_energy = True
        else:
            battle.wild_focus_energy = True
        return f"{attacker.name} dùng Focus Energy. Tỉ lệ chí mạng được tăng lên."

    if move_name == "Follow Me":
        return f"{attacker.name} dùng Follow Me, nhưng trận hiện tại là 1v1 nên không đổi mục tiêu tấn công."

    if move_name == "Foresight":
        if defender is battle.player_active:
            battle.player_identified = True
        else:
            battle.wild_identified = True
        return f"{attacker.name} dùng Foresight. Các đòn Normal/Fighting giờ có thể đánh trúng {defender.name} dù là Ghost."

    if move_name == "Forest's Curse":
        if "Grass" in defender.types:
            return f"{attacker.name} dùng Forest's Curse, nhưng {defender.name} đã mang hệ Grass."
        defender.types = [*defender.types, "Grass"]
        return f"{attacker.name} dùng Forest's Curse. {defender.name} bị thêm hệ Grass."

    if move_name == "Growth":
        boost = 2 if battle.weather == "harsh sunlight" and battle.weather_turns > 0 else 1
        changed_atk, atk_text = battle._change_stat_stage(attacker, "attack", +boost)
        changed_spa, spa_text = battle._change_stat_stage(attacker, "sp_attack", +boost)
        if not changed_atk and not changed_spa:
            return f"{attacker.name} dùng Growth, nhưng Attack/Sp. Attack đã tối đa."
        parts = [f"{attacker.name} dùng Growth."]
        if changed_atk:
            parts.append(f"Attack tăng {atk_text}.")
        if changed_spa:
            parts.append(f"Sp. Attack tăng {spa_text}.")
        return " ".join(parts)

    if move_name == "Gravity":
        battle.gravity_turns = max(getattr(battle, "gravity_turns", 0), 5)
        return f"{attacker.name} dùng Gravity. Trọng lực tăng mạnh trong 5 lượt."

    if move_name == "Grudge":
        if attacker is battle.player_active:
            battle.player_grudge_active = True
        else:
            battle.wild_grudge_active = True
        return f"{attacker.name} dùng Grudge. Nếu bị hạ, PP của chiêu vừa kết liễu sẽ bị về 0."

    if move_name == "Guard Split":
        atk_stages = battle._stat_stages_for(attacker)
        def_stages = battle._stat_stages_for(defender)
        avg_def = int(round((atk_stages.get("defense", 0) + def_stages.get("defense", 0)) / 2))
        avg_spd = int(round((atk_stages.get("sp_defense", 0) + def_stages.get("sp_defense", 0)) / 2))
        atk_stages["defense"] = max(-6, min(6, avg_def))
        def_stages["defense"] = max(-6, min(6, avg_def))
        atk_stages["sp_defense"] = max(-6, min(6, avg_spd))
        def_stages["sp_defense"] = max(-6, min(6, avg_spd))
        return f"{attacker.name} dùng Guard Split. Defense/Sp. Defense stage của hai bên được trung bình hóa."

    if move_name == "Guard Swap":
        atk_stages = battle._stat_stages_for(attacker)
        def_stages = battle._stat_stages_for(defender)
        atk_stages["defense"], def_stages["defense"] = def_stages.get("defense", 0), atk_stages.get("defense", 0)
        atk_stages["sp_defense"], def_stages["sp_defense"] = def_stages.get("sp_defense", 0), atk_stages.get("sp_defense", 0)
        return f"{attacker.name} dùng Guard Swap. Hai bên hoán đổi stage Defense/Sp. Defense."

    if move_name == "Happy Hour":
        battle.player_happy_hour_active = True
        return f"{attacker.name} dùng Happy Hour. Tiền thưởng sau trận của bạn sẽ được nhân đôi."

    if move_name == "Harden":
        changed, stage_text = battle._change_stat_stage(attacker, "defense", +1)
        if changed:
            return f"{attacker.name} dùng Harden. Defense tăng {stage_text}."
        return f"{attacker.name} dùng Harden, nhưng Defense đã tối đa."

    if move_name == "Haze":
        battle.player_stat_stages = {"attack": 0, "defense": 0, "sp_attack": 0, "sp_defense": 0, "speed": 0}
        battle.wild_stat_stages = {"attack": 0, "defense": 0, "sp_attack": 0, "sp_defense": 0, "speed": 0}
        return f"{attacker.name} dùng Haze. Toàn bộ thay đổi chỉ số bị xóa."

    if move_name in {"Heal Bell", "Head Bell"}:
        cured = 0
        if attacker is battle.player_active:
            for pkmn in battle.player.party:
                if pkmn.status is not None:
                    pkmn.status = None
                    pkmn.status_counter = 0
                    cured += 1
        else:
            if attacker.status is not None:
                attacker.status = None
                attacker.status_counter = 0
                cured = 1
        if cured <= 0:
            return f"{attacker.name} dùng Heal Bell, nhưng không ai có trạng thái để chữa."
        return f"{attacker.name} dùng Heal Bell và chữa trạng thái cho {cured} Pokémon."

    if move_name == "Gastro Acid":
        if not defender.ability:
            return f"{attacker.name} dùng Gastro Acid, nhưng {defender.name} không có Ability để vô hiệu hóa."
        defender.ability = ""
        return f"{attacker.name} dùng Gastro Acid. Ability của {defender.name} bị vô hiệu hóa."

    if move_name == "Gear Up":
        return f"{attacker.name} dùng Gear Up, nhưng trận hiện tại là 1v1 nên không có đồng minh Plus/Minus để buff."

    if move_name == "Geomancy":
        if attacker is battle.player_active:
            if not battle.player_geomancy_charging:
                battle.player_geomancy_charging = True
                return f"{attacker.name} dùng Geomancy và bắt đầu tích tụ năng lượng!"
            battle.player_geomancy_charging = False
        else:
            if not battle.wild_geomancy_charging:
                battle.wild_geomancy_charging = True
                return f"{attacker.name} dùng Geomancy và bắt đầu tích tụ năng lượng!"
            battle.wild_geomancy_charging = False

        changed_spa, spa_text = battle._change_stat_stage(attacker, "sp_attack", +2)
        changed_spd, spd_text = battle._change_stat_stage(attacker, "sp_defense", +2)
        changed_spe, spe_text = battle._change_stat_stage(attacker, "speed", +2)
        if not changed_spa and not changed_spd and not changed_spe:
            return f"{attacker.name} giải phóng Geomancy, nhưng các chỉ số đã tối đa."
        parts = [f"{attacker.name} giải phóng Geomancy!"]
        if changed_spa:
            parts.append(f"Sp. Attack tăng mạnh {spa_text}.")
        if changed_spd:
            parts.append(f"Sp. Defense tăng mạnh {spd_text}.")
        if changed_spe:
            parts.append(f"Speed tăng mạnh {spe_text}.")
        return " ".join(parts)

    if move_name == "Chilly Reception":
        battle.weather = "snow"
        battle.weather_turns = 5
        if attacker is battle.player_active:
            options = [
                (idx, pkmn)
                for idx, pkmn in enumerate(battle.player.party)
                if idx != battle.player_active_index and pkmn.current_hp > 0
            ]
            if options:
                next_index, next_pokemon = options[0]
                battle.player_seeded = False
                battle.player_aqua_ring = False
                battle.player_trapped_turns = 0
                battle.player_bound_turns = 0
                battle.player_flinched = False
                battle.player_last_move_name = None
                battle.player_active_index = next_index
                hazard_logs = battle._apply_switch_in_hazards(next_pokemon, is_player=True)
                ability_logs = battle._trigger_switch_in_ability(next_pokemon, is_player=True)
                text = (
                    f"{attacker.name} dùng Chilly Reception! Trời chuyển thành snow 5 lượt, "
                    f"bạn đổi sang {next_pokemon.name}."
                )
                if hazard_logs:
                    text += "\n" + "\n".join(hazard_logs)
                if ability_logs:
                    text += "\n" + "\n".join(ability_logs)
                return text
        return f"{attacker.name} dùng Chilly Reception! Trời chuyển thành snow trong 5 lượt."

    if move_name == "Clangorous Soul":
        cost = max(1, attacker.max_hp // 3)
        if attacker.current_hp <= cost:
            return f"{attacker.name} không đủ HP để dùng Clangorous Soul."
        attacker.current_hp = max(1, attacker.current_hp - cost)
        boosted: list[str] = []
        for stat_key, label in [
            ("attack", "Attack"),
            ("defense", "Defense"),
            ("sp_attack", "Sp. Attack"),
            ("sp_defense", "Sp. Defense"),
            ("speed", "Speed"),
        ]:
            changed, _ = battle._change_stat_stage(attacker, stat_key, +1)
            if changed:
                boosted.append(label)
        if boosted:
            return (
                f"{attacker.name} dùng Clangorous Soul, mất {cost} HP ({attacker.current_hp}/{attacker.max_hp}) "
                f"và tăng {', '.join(boosted)}."
            )
        return f"{attacker.name} dùng Clangorous Soul, mất {cost} HP nhưng không thể tăng thêm chỉ số."

    if move_name == "Bulk Up":
        changed_atk, atk_text = battle._change_stat_stage(attacker, "attack", +1)
        changed_def, def_text = battle._change_stat_stage(attacker, "defense", +1)
        if not changed_atk and not changed_def:
            return f"{attacker.name} dùng Bulk Up, nhưng Attack và Defense đều đã tối đa."
        parts = [f"{attacker.name} dùng Bulk Up."]
        if changed_atk:
            parts.append(f"Attack tăng {atk_text}.")
        if changed_def:
            parts.append(f"Defense tăng {def_text}.")
        return " ".join(parts)

    if move_name == "Bestow":
        give_item = (attacker.hold_item or "").strip()
        if not give_item:
            return f"{attacker.name} dùng Bestow, nhưng không cầm item để cho."
        if defender.hold_item:
            return f"{attacker.name} dùng Bestow, nhưng {defender.name} đã cầm item rồi."
        defender.hold_item = give_item
        attacker.hold_item = None
        return f"{attacker.name} dùng Bestow và đưa {give_item} cho {defender.name}."

    if move_name == "Block":
        if defender is battle.player_active:
            battle.player_trapped_turns = max(battle.player_trapped_turns, 5)
        else:
            battle.wild_trapped_turns = max(battle.wild_trapped_turns, 5)
        return f"{attacker.name} dùng Block. {defender.name} không thể chạy trốn/đổi Pokémon trong vài lượt."

    if move_name == "Aromatic Mist":
        return f"{attacker.name} dùng Aromatic Mist, nhưng trận hiện tại là 1v1 nên không có đồng minh để buff."

    if move_name == "Ally Switch":
        return f"{attacker.name} dùng Ally Switch, nhưng trận hiện tại là 1v1 nên không có tác dụng."

    if move_name == "After You":
        return f"{attacker.name} dùng After You, nhưng cơ chế lượt kế tiếp của 1v1 chưa hỗ trợ chiêu này."

    if move_name == "Assist":
        return f"{attacker.name} dùng Assist, nhưng cơ chế mượn chiêu từ đồng đội chưa hỗ trợ trong bản hiện tại."

    if move_name == "Bide":
        if attacker is battle.player_active:
            if battle.player_bide_turns > 0:
                return f"{attacker.name} đang tích trữ năng lượng bằng Bide."
            battle.player_bide_turns = 2
            battle.player_bide_damage = 0
        else:
            if battle.wild_bide_turns > 0:
                return f"{attacker.name} đang tích trữ năng lượng bằng Bide."
            battle.wild_bide_turns = 2
            battle.wild_bide_damage = 0
        return f"{attacker.name} dùng Bide và bắt đầu tích trữ sát thương trong 2 lượt!"

    if move_name == "Belch":
        return f"{attacker.name} dùng Belch, nhưng điều kiện Berry-consumed chưa hỗ trợ đầy đủ trong bản hiện tại."

    if move_name == "Attract":
        if defender.current_hp <= 0:
            return f"{attacker.name} dùng Attract, nhưng mục tiêu đã gục."
        if battle._is_infatuated(defender):
            return f"{attacker.name} dùng Attract, nhưng {defender.name} đã bị mê mẩn từ trước."
        knot_text = battle._set_infatuated(defender, True, source=attacker)
        text = f"{attacker.name} dùng Attract. {defender.name} bị mê mẩn!"
        if knot_text:
            text = text + f" {knot_text}"
        return text

    if move_name == "Heal Block":
        if defender is battle.player_active:
            battle.player_heal_block_turns = max(battle.player_heal_block_turns, 5)
        else:
            battle.wild_heal_block_turns = max(battle.wild_heal_block_turns, 5)
        return f"{attacker.name} dùng Heal Block. {defender.name} không thể hồi HP bằng move trong 5 lượt."

    if move_name == "Heal Order":
        blocked = battle.player_heal_block_turns > 0 if attacker is battle.player_active else battle.wild_heal_block_turns > 0
        if blocked:
            return f"{attacker.name} dùng Heal Order nhưng thất bại do Heal Block."
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể hồi phục vì đã gục."
        if attacker.current_hp >= attacker.max_hp:
            return f"{attacker.name} dùng Heal Order, nhưng HP đã đầy."
        before_hp = attacker.current_hp
        heal_amount = max(1, int(attacker.max_hp * 0.5))
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
        healed = attacker.current_hp - before_hp
        return f"{attacker.name} dùng Heal Order và hồi {healed} HP ({attacker.current_hp}/{attacker.max_hp})."

    if move_name == "Heal Pulse":
        blocked = battle.player_heal_block_turns > 0 if defender is battle.player_active else battle.wild_heal_block_turns > 0
        if blocked:
            return f"{attacker.name} dùng Heal Pulse nhưng mục tiêu đang bị Heal Block."
        if defender.current_hp <= 0:
            return f"{attacker.name} dùng Heal Pulse, nhưng mục tiêu đã gục."
        if defender.current_hp >= defender.max_hp:
            return f"{attacker.name} dùng Heal Pulse, nhưng {defender.name} đã đầy HP."
        before_hp = defender.current_hp
        heal_amount = max(1, int(defender.max_hp * 0.5))
        defender.current_hp = min(defender.max_hp, defender.current_hp + heal_amount)
        healed = defender.current_hp - before_hp
        return f"{attacker.name} dùng Heal Pulse và hồi {healed} HP cho {defender.name} ({defender.current_hp}/{defender.max_hp})."

    if move_name == "Healing Wish":
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể dùng Healing Wish vì đã gục."
        attacker.current_hp = 0
        if attacker is battle.player_active:
            battle.player_healing_wish_pending = True
        else:
            battle.wild_healing_wish_pending = True
        return f"{attacker.name} hiến tế bằng Healing Wish. Pokémon vào sân kế tiếp sẽ được hồi phục hoàn toàn."

    if move_name == "Heart Swap":
        atk_stages = battle._stat_stages_for(attacker)
        def_stages = battle._stat_stages_for(defender)
        for stat_key in ["attack", "defense", "sp_attack", "sp_defense", "speed"]:
            atk_stages[stat_key], def_stages[stat_key] = def_stages.get(stat_key, 0), atk_stages.get(stat_key, 0)
        return f"{attacker.name} dùng Heart Swap. Hai bên hoán đổi toàn bộ stat stages."

    if move_name == "Helping Hand":
        return f"{attacker.name} dùng Helping Hand, nhưng trận hiện tại là 1v1 nên không có đồng minh để tăng lực."

    if move_name == "Hold Hands":
        return f"{attacker.name} dùng Hold Hands, nhưng trận hiện tại là 1v1 nên không có đồng minh để nắm tay."

    if move_name == "Hone Claws":
        changed, stage_text = battle._change_stat_stage(attacker, "attack", +1)
        if changed:
            return f"{attacker.name} dùng Hone Claws. Attack tăng {stage_text}. (Accuracy boost chưa được mô phỏng chi tiết)."
        return f"{attacker.name} dùng Hone Claws, nhưng Attack đã tối đa."

    if move_name == "Howl":
        changed, stage_text = battle._change_stat_stage(attacker, "attack", +1)
        if changed:
            return f"{attacker.name} dùng Howl. Attack tăng {stage_text}."
        return f"{attacker.name} dùng Howl, nhưng Attack đã tối đa."

    if move_name == "Instruct":
        return f"{attacker.name} dùng Instruct, nhưng trận hiện tại là 1v1 nên không có đồng minh để ra lệnh."

    if move_name == "Ion Deluge":
        battle.ion_deluge_active = True
        return f"{attacker.name} dùng Ion Deluge. Các chiêu Normal trong lượt này sẽ đổi thành hệ Electric."

    if move_name == "Jungle Healing":
        healed = 0
        cured = 0
        if attacker is battle.player_active:
            for pkmn in battle.player.party:
                if pkmn.current_hp > 0 and pkmn.current_hp < pkmn.max_hp:
                    before = pkmn.current_hp
                    pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + max(1, pkmn.max_hp // 4))
                    healed += max(0, pkmn.current_hp - before)
                if pkmn.status is not None:
                    pkmn.status = None
                    pkmn.status_counter = 0
                    cured += 1
        else:
            if attacker.current_hp < attacker.max_hp:
                before = attacker.current_hp
                attacker.current_hp = min(attacker.max_hp, attacker.current_hp + max(1, attacker.max_hp // 4))
                healed = max(0, attacker.current_hp - before)
            if attacker.status is not None:
                attacker.status = None
                attacker.status_counter = 0
                cured = 1
        return f"{attacker.name} dùng Jungle Healing. Hồi tổng {healed} HP và chữa trạng thái cho {cured} Pokémon."

    if move_name == "Kinesis":
        return f"{attacker.name} dùng Kinesis. (Giảm Accuracy chưa được mô phỏng chi tiết trong engine hiện tại)."

    if move_name == "King's Shield":
        if battle._try_activate_protect(attacker):
            if attacker is battle.player_active:
                battle.player_kings_shield_active = True
            else:
                battle.wild_kings_shield_active = True
            return f"{attacker.name} dùng King's Shield và dựng khiên bảo vệ."
        return f"{attacker.name} dùng King's Shield nhưng thất bại do dùng liên tiếp."

    if move_name == "Laser Focus":
        if attacker is battle.player_active:
            battle.player_laser_focus = True
        else:
            battle.wild_laser_focus = True
        return f"{attacker.name} dùng Laser Focus. Đòn tấn công kế tiếp sẽ chắc chắn chí mạng."

    if move_name == "Life Dew":
        healed_targets = 0
        total_healed = 0
        if attacker is battle.player_active:
            for pkmn in battle.player.party:
                if pkmn.current_hp > 0 and pkmn.current_hp < pkmn.max_hp:
                    before = pkmn.current_hp
                    pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + max(1, pkmn.max_hp // 4))
                    total_healed += max(0, pkmn.current_hp - before)
                    healed_targets += 1
        else:
            if attacker.current_hp > 0 and attacker.current_hp < attacker.max_hp:
                before = attacker.current_hp
                attacker.current_hp = min(attacker.max_hp, attacker.current_hp + max(1, attacker.max_hp // 4))
                total_healed = max(0, attacker.current_hp - before)
                healed_targets = 1
        if healed_targets <= 0:
            return f"{attacker.name} dùng Life Dew, nhưng không có Pokémon nào cần hồi HP."
        return f"{attacker.name} dùng Life Dew, hồi tổng {total_healed} HP cho {healed_targets} Pokémon."

    if move_name == "Lock-On":
        if attacker is battle.player_active:
            battle.player_lock_on_ready = True
        else:
            battle.wild_lock_on_ready = True
        return f"{attacker.name} dùng Lock-On. Đòn kế tiếp của {attacker.name} sẽ không thể trượt."

    if move_name == "Mind Reader":
        if attacker is battle.player_active:
            battle.player_lock_on_ready = True
        else:
            battle.wild_lock_on_ready = True
        return f"{attacker.name} dùng Mind Reader. Đòn kế tiếp của {attacker.name} sẽ không thể trượt."

    if move_name == "Minimize":
        return f"{attacker.name} dùng Minimize. (Tăng Evasion chưa được mô phỏng chi tiết trong engine hiện tại)."

    if move_name == "Miracle Eye":
        if defender is battle.player_active:
            battle.player_miracle_eye = True
        else:
            battle.wild_miracle_eye = True
        return f"{attacker.name} dùng Miracle Eye. {defender.name} không còn né tránh miễn nhiễm Psychic từ hệ Dark trong lúc còn trên sân."

    if move_name == "Mirror Move":
        return f"{attacker.name} dùng Mirror Move, nhưng cơ chế sao chép tức thì chiêu vừa dùng của đối thủ chưa được mô phỏng đầy đủ trong engine 1v1."

    if move_name == "Lucky Chant":
        if attacker is battle.player_active:
            battle.player_lucky_chant_turns = max(battle.player_lucky_chant_turns, 5)
        else:
            battle.wild_lucky_chant_turns = max(battle.wild_lucky_chant_turns, 5)
        return f"{attacker.name} dùng Lucky Chant. Phe này được chặn đòn chí mạng trong 5 lượt."

    if move_name == "Mean Look":
        if defender is battle.player_active:
            battle.player_trapped_turns = max(battle.player_trapped_turns, 999)
        else:
            battle.wild_trapped_turns = max(battle.wild_trapped_turns, 999)
        return f"{attacker.name} dùng Mean Look. {defender.name} không thể chạy trốn/đổi Pokémon."

    if move_name == "Nightmare":
        if defender.status != "slp":
            return f"{attacker.name} dùng Nightmare nhưng thất bại vì {defender.name} không ngủ."
        if defender is battle.player_active:
            battle.player_nightmare = True
        else:
            battle.wild_nightmare = True
        return f"{attacker.name} dùng Nightmare. {defender.name} sẽ mất HP mỗi lượt khi còn ngủ."

    if move_name == "No Retreat":
        changed_any = False
        for stat_key in ["attack", "defense", "sp_attack", "sp_defense", "speed"]:
            changed, _ = battle._change_stat_stage(attacker, stat_key, +1)
            changed_any = changed_any or changed
        if attacker is battle.player_active:
            battle.player_trapped_turns = max(battle.player_trapped_turns, 999)
        else:
            battle.wild_trapped_turns = max(battle.wild_trapped_turns, 999)
        if changed_any:
            return f"{attacker.name} dùng No Retreat. Toàn bộ chỉ số tăng và không thể đổi Pokémon."
        return f"{attacker.name} dùng No Retreat, nhưng chỉ số đã tối đa; vẫn bị giữ chân trên sân."

    if move_name == "Noble Roar":
        changed_atk, atk_text = battle._change_stat_stage(defender, "attack", -1)
        changed_spa, spa_text = battle._change_stat_stage(defender, "sp_attack", -1)
        parts = [f"{attacker.name} dùng Noble Roar."]
        if changed_atk:
            parts.append(f"Attack của {defender.name} giảm {atk_text}.")
        if changed_spa:
            parts.append(f"Sp. Attack của {defender.name} giảm {spa_text}.")
        if not changed_atk and not changed_spa:
            parts.append("Nhưng các chỉ số không thể giảm thêm.")
        return " ".join(parts)

    if move_name == "Mist":
        if attacker is battle.player_active:
            battle.player_mist_turns = max(getattr(battle, "player_mist_turns", 0), 5)
        else:
            battle.wild_mist_turns = max(getattr(battle, "wild_mist_turns", 0), 5)
        return f"{attacker.name} dùng Mist. Phe này được bảo vệ khỏi giảm chỉ số trong 5 lượt (mô phỏng rút gọn)."

    if move_name == "Lunar Blessing":
        healed = 0
        cured = 0
        if attacker is battle.player_active:
            for pkmn in battle.player.party:
                if pkmn.current_hp > 0 and pkmn.current_hp < pkmn.max_hp:
                    before = pkmn.current_hp
                    pkmn.current_hp = min(pkmn.max_hp, pkmn.current_hp + max(1, pkmn.max_hp // 4))
                    healed += max(0, pkmn.current_hp - before)
                if pkmn.status is not None:
                    pkmn.status = None
                    pkmn.status_counter = 0
                    cured += 1
        else:
            if attacker.current_hp < attacker.max_hp:
                before = attacker.current_hp
                attacker.current_hp = min(attacker.max_hp, attacker.current_hp + max(1, attacker.max_hp // 4))
                healed = max(0, attacker.current_hp - before)
            if attacker.status is not None:
                attacker.status = None
                attacker.status_counter = 0
                cured = 1
        return f"{attacker.name} dùng Lunar Blessing. Hồi tổng {healed} HP và chữa trạng thái cho {cured} Pokémon."

    if move_name == "Memento":
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể dùng Memento vì đã gục."
        attacker.current_hp = 0
        changed_atk, text_atk = battle._change_stat_stage(defender, "attack", -2)
        changed_spa, text_spa = battle._change_stat_stage(defender, "sp_attack", -2)
        parts = [f"{attacker.name} hy sinh bằng Memento."]
        if changed_atk:
            parts.append(f"Attack của {defender.name} giảm mạnh {text_atk}.")
        if changed_spa:
            parts.append(f"Sp. Attack của {defender.name} giảm mạnh {text_spa}.")
        if not changed_atk and not changed_spa:
            parts.append("Nhưng chỉ số của mục tiêu không thể giảm thêm.")
        return " ".join(parts)

    if move_name == "Moonlight":
        blocked = battle.player_heal_block_turns > 0 if attacker is battle.player_active else battle.wild_heal_block_turns > 0
        if blocked:
            return f"{attacker.name} dùng Moonlight nhưng thất bại do Heal Block."
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể hồi phục vì đã gục."
        if attacker.current_hp >= attacker.max_hp:
            return f"{attacker.name} dùng Moonlight, nhưng HP đã đầy."
        ratio = 0.5
        if getattr(battle, "weather", None) == "harsh sunlight" and getattr(battle, "weather_turns", 0) > 0:
            ratio = 2 / 3
        elif getattr(battle, "weather", None) in {"rain", "sandstorm", "snow"} and getattr(battle, "weather_turns", 0) > 0:
            ratio = 0.25
        before_hp = attacker.current_hp
        heal_amount = max(1, int(attacker.max_hp * ratio))
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
        healed = attacker.current_hp - before_hp
        return f"{attacker.name} dùng Moonlight và hồi {healed} HP ({attacker.current_hp}/{attacker.max_hp})."

    if move_name == "Morning Sun":
        blocked = battle.player_heal_block_turns > 0 if attacker is battle.player_active else battle.wild_heal_block_turns > 0
        if blocked:
            return f"{attacker.name} dùng Morning Sun nhưng thất bại do Heal Block."
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể hồi phục vì đã gục."
        if attacker.current_hp >= attacker.max_hp:
            return f"{attacker.name} dùng Morning Sun, nhưng HP đã đầy."
        ratio = 0.5
        if getattr(battle, "weather", None) == "harsh sunlight" and getattr(battle, "weather_turns", 0) > 0:
            ratio = 2 / 3
        elif getattr(battle, "weather", None) in {"rain", "sandstorm", "snow"} and getattr(battle, "weather_turns", 0) > 0:
            ratio = 0.25
        before_hp = attacker.current_hp
        heal_amount = max(1, int(attacker.max_hp * ratio))
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
        healed = attacker.current_hp - before_hp
        return f"{attacker.name} dùng Morning Sun và hồi {healed} HP ({attacker.current_hp}/{attacker.max_hp})."

    if move_name == "Metal Sound":
        changed, stage_text = battle._change_stat_stage(defender, "sp_defense", -2)
        if changed:
            return f"{attacker.name} dùng Metal Sound. Sp. Defense của {defender.name} giảm mạnh {stage_text}."
        return f"{attacker.name} dùng Metal Sound, nhưng Sp. Defense của {defender.name} không thể giảm thêm."

    if move_name == "Odor Sleuth":
        if defender is battle.player_active:
            battle.player_identified = True
        else:
            battle.wild_identified = True
        return f"{attacker.name} dùng Odor Sleuth. {defender.name} không còn né tránh đòn Normal/Fighting bằng hệ Ghost."

    if move_name == "Octolock":
        if defender is battle.player_active:
            battle.player_octolock = True
            battle.player_trapped_turns = max(battle.player_trapped_turns, 999)
        else:
            battle.wild_octolock = True
            battle.wild_trapped_turns = max(battle.wild_trapped_turns, 999)
        return f"{attacker.name} dùng Octolock. {defender.name} bị giữ chân và sẽ bị giảm Defense/Sp. Defense mỗi lượt."

    if move_name == "Pain Split":
        if attacker.current_hp <= 0 or defender.current_hp <= 0:
            return f"{attacker.name} dùng Pain Split nhưng thất bại vì một bên đã gục."
        average = max(1, (attacker.current_hp + defender.current_hp) // 2)
        attacker.current_hp = min(attacker.max_hp, average)
        defender.current_hp = min(defender.max_hp, average)
        return f"{attacker.name} dùng Pain Split. HP của cả hai được cân bằng về {average}."

    if move_name == "Parting Shot":
        changed_atk, atk_text = battle._change_stat_stage(defender, "attack", -1)
        changed_spa, spa_text = battle._change_stat_stage(defender, "sp_attack", -1)
        parts = [f"{attacker.name} dùng Parting Shot."]
        if changed_atk:
            parts.append(f"Attack của {defender.name} giảm {atk_text}.")
        if changed_spa:
            parts.append(f"Sp. Attack của {defender.name} giảm {spa_text}.")
        if attacker is battle.player_active:
            options = [
                idx
                for idx, pkmn in enumerate(battle.player.party)
                if idx != battle.player_active_index and pkmn.current_hp > 0
            ]
            if options:
                switch_result = battle.switch_pokemon(options[0])
                parts.append(switch_result.text)
            else:
                parts.append("Nhưng không có Pokémon nào khác để đổi vào.")
        else:
            parts.append("Wild dùng Parting Shot nhưng cơ chế đổi ra của AI chưa hỗ trợ đầy đủ.")
        return " ".join(parts)

    if move_name == "Powder":
        if defender.current_hp <= 0:
            return f"{attacker.name} dùng Powder, nhưng mục tiêu đã gục."
        if defender is battle.player_active:
            battle.player_powdered = True
        else:
            battle.wild_powdered = True
        return f"{attacker.name} rắc Powder lên {defender.name}. Nếu dùng chiêu Fire trong lượt tới, mục tiêu sẽ nổ và mất HP."

    if move_name == "Power Shift":
        attacker.attack, attacker.defense = attacker.defense, attacker.attack
        return f"{attacker.name} dùng Power Shift. Attack và Defense của nó đã hoán đổi cho nhau."

    if move_name == "Power Split":
        avg_atk = max(1, (attacker.attack + defender.attack) // 2)
        avg_spa = max(1, (attacker.sp_attack + defender.sp_attack) // 2)
        attacker.attack = avg_atk
        defender.attack = avg_atk
        attacker.sp_attack = avg_spa
        defender.sp_attack = avg_spa
        return (
            f"{attacker.name} dùng Power Split. Attack và Sp. Attack của cả hai được san bằng "
            f"({avg_atk}/{avg_spa})."
        )

    if move_name == "Power Swap":
        attacker.attack, defender.attack = defender.attack, attacker.attack
        attacker.sp_attack, defender.sp_attack = defender.sp_attack, attacker.sp_attack
        return f"{attacker.name} dùng Power Swap. Hai bên hoán đổi Attack và Sp. Attack cho nhau."

    if move_name == "Power Trick":
        attacker.attack, attacker.defense = attacker.defense, attacker.attack
        return f"{attacker.name} dùng Power Trick. Attack và Defense của nó đã đảo vị trí."

    if move_name == "Psych Up":
        attacker_stages = battle._stat_stages_for(attacker)
        defender_stages = battle._stat_stages_for(defender)
        for stat_key in ["attack", "defense", "sp_attack", "sp_defense", "speed"]:
            attacker_stages[stat_key] = defender_stages.get(stat_key, 0)
        return f"{attacker.name} dùng Psych Up và sao chép toàn bộ thay đổi chỉ số của {defender.name}."

    if move_name == "Recycle":
        if attacker.hold_item:
            return f"{attacker.name} dùng Recycle nhưng đã có item trên tay."
        if not attacker.berry_consumed:
            return f"{attacker.name} dùng Recycle nhưng chưa tiêu thụ item để khôi phục."
        attacker.hold_item = "Sitrus Berry"
        attacker.berry_consumed = False
        return f"{attacker.name} dùng Recycle và khôi phục lại Sitrus Berry (mô phỏng rút gọn)."

    if move_name == "Reflect Type":
        if defender.current_hp <= 0:
            return f"{attacker.name} dùng Reflect Type, nhưng mục tiêu đã gục."
        attacker.types = list(defender.types)
        return f"{attacker.name} dùng Reflect Type và đổi hệ thành {', '.join(attacker.types)}."

    if move_name == "Refresh":
        if attacker.status not in {"par", "psn", "tox", "brn"}:
            return f"{attacker.name} dùng Refresh nhưng không có trạng thái phù hợp để chữa."
        attacker.status = None
        attacker.status_counter = 0
        return f"{attacker.name} dùng Refresh và chữa khỏi trạng thái bất lợi."

    if move_name == "Psycho Shift":
        if attacker.status is None:
            return f"{attacker.name} dùng Psycho Shift nhưng không có trạng thái để chuyển."
        if defender.status is not None:
            return f"{attacker.name} dùng Psycho Shift nhưng {defender.name} đã có trạng thái."
        status = attacker.status
        if status in {"psn", "tox"} and ("Poison" in defender.types or "Steel" in defender.types or defender.ability == "Immunity"):
            return f"{attacker.name} dùng Psycho Shift nhưng {defender.name} miễn nhiễm độc."
        if status == "brn" and "Fire" in defender.types:
            return f"{attacker.name} dùng Psycho Shift nhưng {defender.name} miễn nhiễm Burn."
        if status == "par" and "Electric" in defender.types:
            return f"{attacker.name} dùng Psycho Shift nhưng {defender.name} miễn nhiễm Paralysis."
        attacker.status = None
        attacker.status_counter = 0
        defender.status = status
        defender.status_counter = 1 if status in {"slp", "tox"} else 0
        return f"{attacker.name} chuyển trạng thái {status} sang {defender.name} bằng Psycho Shift."

    if move_name == "Purify":
        if defender.status is None:
            return f"{attacker.name} dùng Purify nhưng mục tiêu không có trạng thái để chữa."
        defender.status = None
        defender.status_counter = 0
        healed = 0
        if attacker.current_hp > 0 and attacker.current_hp < attacker.max_hp:
            before = attacker.current_hp
            attacker.current_hp = min(attacker.max_hp, attacker.current_hp + max(1, attacker.max_hp // 2))
            healed = max(0, attacker.current_hp - before)
        return f"{attacker.name} dùng Purify, chữa trạng thái cho {defender.name} và hồi {healed} HP."

    if move_name == "Quash":
        return f"{attacker.name} dùng Quash. Trong battle 1v1, mục tiêu vốn đã chỉ còn lượt của mình nên hiệu ứng bị rút gọn."

    if move_name == "Quick Guard":
        if attacker is battle.player_active:
            battle.player_quick_guard_active = True
        else:
            battle.wild_quick_guard_active = True
        return f"{attacker.name} dùng Quick Guard. Đòn ưu tiên nhắm vào phe này sẽ bị chặn trong lượt hiện tại."

    if move_name == "Quiver Dance":
        changed_spa, spa_text = battle._change_stat_stage(attacker, "sp_attack", +1)
        changed_spd, spd_text = battle._change_stat_stage(attacker, "sp_defense", +1)
        changed_spe, spe_text = battle._change_stat_stage(attacker, "speed", +1)
        if not changed_spa and not changed_spd and not changed_spe:
            return f"{attacker.name} dùng Quiver Dance, nhưng các chỉ số đã tối đa."
        parts = [f"{attacker.name} dùng Quiver Dance."]
        if changed_spa:
            parts.append(f"Sp. Attack tăng {spa_text}.")
        if changed_spd:
            parts.append(f"Sp. Defense tăng {spd_text}.")
        if changed_spe:
            parts.append(f"Speed tăng {spe_text}.")
        return " ".join(parts)

    if move_name == "Rage Powder":
        return f"{attacker.name} dùng Rage Powder, nhưng đây là battle 1v1 nên không có mục tiêu đồng minh để đổi hướng tấn công."

    if move_name == "Sinister Arrow Raid":
        return f"{attacker.name} dùng Sinister Arrow Raid (Z-Move). Hiệu ứng phụ đặc trưng được rút gọn, chỉ áp dụng sát thương thuần trong engine hiện tại."

    if move_name == "Revival Blessing":
        if attacker is not battle.player_active:
            return f"{attacker.name} dùng Revival Blessing, nhưng cơ chế hồi sinh cho wild chưa hỗ trợ trong 1v1."
        candidates = [pkmn for pkmn in battle.player.party if pkmn.current_hp <= 0]
        if not candidates:
            return f"{attacker.name} dùng Revival Blessing, nhưng không có Pokémon nào đã gục để hồi sinh."
        revived = candidates[0]
        revived.current_hp = max(1, revived.max_hp // 2)
        revived.status = None
        revived.status_counter = 0
        revived.confusion_turns = 0
        return f"{attacker.name} dùng Revival Blessing và hồi sinh {revived.name} với {revived.current_hp}/{revived.max_hp} HP."

    if move_name == "Shed Tail":
        if attacker.current_hp <= 1:
            return f"{attacker.name} dùng Shed Tail nhưng không đủ HP để tạo bù nhìn."
        if attacker is not battle.player_active:
            return f"{attacker.name} dùng Shed Tail, nhưng cơ chế đổi chỗ cho wild chưa hỗ trợ trong 1v1."
        options = [
            (idx, pkmn)
            for idx, pkmn in enumerate(battle.player.party)
            if idx != battle.player_active_index and pkmn.current_hp > 0
        ]
        if not options:
            return f"{attacker.name} dùng Shed Tail, nhưng không có Pokémon nào để đổi vào."
        cost = max(1, attacker.max_hp // 2)
        if attacker.current_hp <= cost:
            return f"{attacker.name} dùng Shed Tail nhưng không đủ HP (cần hơn {cost} HP)."
        attacker.current_hp = max(1, attacker.current_hp - cost)
        next_index, next_pokemon = options[0]
        battle.player_seeded = False
        battle.player_trapped_turns = 0
        battle.player_flinched = False
        battle.player_active_index = next_index
        hazard_logs = battle._apply_switch_in_hazards(next_pokemon, is_player=True)
        ability_logs = battle._trigger_switch_in_ability(next_pokemon, is_player=True)
        text = (
            f"{attacker.name} dùng Shed Tail, mất {cost} HP ({attacker.current_hp}/{attacker.max_hp}) và đổi sang {next_pokemon.name}."
            f" Bù nhìn được truyền cho Pokémon mới (mô phỏng rút gọn)."
        )
        if hazard_logs:
            text += "\n" + "\n".join(hazard_logs)
        if ability_logs:
            text += "\n" + "\n".join(ability_logs)
        return text

    if move_name == "Work Up":
        changed_atk, atk_text = battle._change_stat_stage(attacker, "attack", +1)
        changed_spa, spa_text = battle._change_stat_stage(attacker, "sp_attack", +1)
        if not changed_atk and not changed_spa:
            return f"{attacker.name} dùng Work Up, nhưng Attack/Sp. Attack đã tối đa."
        parts = [f"{attacker.name} dùng Work Up."]
        if changed_atk:
            parts.append(f"Attack tăng {atk_text}.")
        if changed_spa:
            parts.append(f"Sp. Attack tăng {spa_text}.")
        return " ".join(parts)

    if move_name == "Worry Seed":
        if defender.current_hp <= 0:
            return f"{attacker.name} dùng Worry Seed, nhưng mục tiêu đã gục."
        defender.ability = "Insomnia"
        if defender.status == "slp":
            defender.status = None
            defender.status_counter = 0
            return f"{attacker.name} dùng Worry Seed. Ability của {defender.name} thành Insomnia và tỉnh dậy."
        return f"{attacker.name} dùng Worry Seed. Ability của {defender.name} thành Insomnia."

    if move_name == "Yawn":
        if defender.current_hp <= 0:
            return f"{attacker.name} dùng Yawn, nhưng mục tiêu đã gục."
        if defender.status is not None:
            return f"{attacker.name} dùng Yawn, nhưng {defender.name} đã có trạng thái bất lợi."
        if defender.ability == "Insomnia":
            return f"{attacker.name} dùng Yawn, nhưng Insomnia của {defender.name} ngăn ngủ."
        if defender is battle.player_active:
            if getattr(battle, "player_yawn_turns", 0) > 0:
                return f"{attacker.name} dùng Yawn, nhưng {defender.name} đã buồn ngủ rồi."
            battle.player_yawn_turns = 2
        else:
            if getattr(battle, "wild_yawn_turns", 0) > 0:
                return f"{attacker.name} dùng Yawn, nhưng {defender.name} đã buồn ngủ rồi."
            battle.wild_yawn_turns = 2
        return f"{attacker.name} dùng Yawn. {defender.name} sẽ ngủ vào cuối lượt kế tiếp."

    if move_name == "Shift Gear":
        changed_atk, atk_text = battle._change_stat_stage(attacker, "attack", +1)
        changed_spe, spe_text = battle._change_stat_stage(attacker, "speed", +2)
        if not changed_atk and not changed_spe:
            return f"{attacker.name} dùng Shift Gear, nhưng chỉ số đã tối đa."
        parts = [f"{attacker.name} dùng Shift Gear."]
        if changed_atk:
            parts.append(f"Attack tăng {atk_text}.")
        if changed_spe:
            parts.append(f"Speed tăng mạnh {spe_text}.")
        return " ".join(parts)

    if move_name == "Synthesis":
        blocked = battle.player_heal_block_turns > 0 if attacker is battle.player_active else battle.wild_heal_block_turns > 0
        if blocked:
            return f"{attacker.name} dùng Synthesis nhưng thất bại do Heal Block."
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể hồi phục vì đã gục."
        if attacker.current_hp >= attacker.max_hp:
            return f"{attacker.name} dùng Synthesis, nhưng HP đã đầy."
        ratio = 0.5
        if getattr(battle, "weather", None) == "harsh sunlight" and getattr(battle, "weather_turns", 0) > 0:
            ratio = 2 / 3
        elif getattr(battle, "weather", None) in {"rain", "sandstorm", "snow"} and getattr(battle, "weather_turns", 0) > 0:
            ratio = 0.25
        before_hp = attacker.current_hp
        heal_amount = max(1, int(attacker.max_hp * ratio))
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
        healed = attacker.current_hp - before_hp
        return f"{attacker.name} dùng Synthesis và hồi {healed} HP ({attacker.current_hp}/{attacker.max_hp})."

    if move_name == "Tail Glow":
        changed, stage_text = battle._change_stat_stage(attacker, "sp_attack", +3)
        if changed:
            return f"{attacker.name} dùng Tail Glow. Sp. Attack tăng mạnh {stage_text}."
        return f"{attacker.name} dùng Tail Glow, nhưng Sp. Attack đã tối đa."

    if move_name == "Tailwind":
        if attacker is battle.player_active:
            battle.player_tailwind_turns = max(getattr(battle, "player_tailwind_turns", 0), 4)
        else:
            battle.wild_tailwind_turns = max(getattr(battle, "wild_tailwind_turns", 0), 4)
        return f"{attacker.name} dùng Tailwind. Speed của phe này được tăng trong 4 lượt."

    if move_name == "Take Heart":
        changed_spa, spa_text = battle._change_stat_stage(attacker, "sp_attack", +1)
        changed_spd, spd_text = battle._change_stat_stage(attacker, "sp_defense", +1)
        cured = False
        if attacker.status is not None:
            attacker.status = None
            attacker.status_counter = 0
            cured = True
        parts = [f"{attacker.name} dùng Take Heart."]
        if changed_spa:
            parts.append(f"Sp. Attack tăng {spa_text}.")
        if changed_spd:
            parts.append(f"Sp. Defense tăng {spd_text}.")
        if cured:
            parts.append("Trạng thái bất lợi được chữa khỏi.")
        if not changed_spa and not changed_spd and not cured:
            parts.append("Nhưng không có hiệu ứng nào thêm.")
        return " ".join(parts)

    if move_name == "Tar Shot":
        if defender is battle.player_active:
            if getattr(battle, "player_tar_shot", False):
                return f"{attacker.name} dùng Tar Shot, nhưng {defender.name} đã bị phủ nhựa đường."
            battle.player_tar_shot = True
        else:
            if getattr(battle, "wild_tar_shot", False):
                return f"{attacker.name} dùng Tar Shot, nhưng {defender.name} đã bị phủ nhựa đường."
            battle.wild_tar_shot = True
        changed, stage_text = battle._change_stat_stage(defender, "speed", -1)
        if changed:
            return f"{attacker.name} dùng Tar Shot. Speed của {defender.name} giảm {stage_text} và trở nên yếu hơn trước đòn Fire."
        return f"{attacker.name} dùng Tar Shot. {defender.name} trở nên yếu hơn trước đòn Fire."

    if move_name == "Taunt":
        if defender is battle.player_active:
            battle.player_taunt_turns = max(getattr(battle, "player_taunt_turns", 0), 3)
        else:
            battle.wild_taunt_turns = max(getattr(battle, "wild_taunt_turns", 0), 3)
        return f"{attacker.name} dùng Taunt. {defender.name} bị khiêu khích và không thể dùng status move trong 3 lượt."

    if move_name == "Tearful Look":
        changed_atk, atk_text = battle._change_stat_stage(defender, "attack", -1)
        changed_spa, spa_text = battle._change_stat_stage(defender, "sp_attack", -1)
        if not changed_atk and not changed_spa:
            return f"{attacker.name} dùng Tearful Look, nhưng chỉ số của {defender.name} không thể giảm thêm."
        parts = [f"{attacker.name} dùng Tearful Look."]
        if changed_atk:
            parts.append(f"Attack của {defender.name} giảm {atk_text}.")
        if changed_spa:
            parts.append(f"Sp. Attack của {defender.name} giảm {spa_text}.")
        return " ".join(parts)

    if move_name == "Teatime":
        consumed: list[str] = []
        for target in (attacker, defender):
            item = (target.hold_item or "").strip()
            if not item or "berry" not in item.lower():
                continue
            target.hold_item = None
            target.berry_consumed = True
            berry_lower = item.lower()
            healed = 0
            if "oran" in berry_lower:
                healed = min(10, target.max_hp - target.current_hp)
            elif "sitrus" in berry_lower:
                healed = min(max(1, target.max_hp // 4), target.max_hp - target.current_hp)
            if healed > 0:
                target.current_hp += healed
                consumed.append(f"{target.name} ăn {item} và hồi {healed} HP")
            else:
                consumed.append(f"{target.name} ăn {item}")
        if not consumed:
            return f"{attacker.name} dùng Teatime, nhưng không có Berry nào được ăn."
        return f"{attacker.name} dùng Teatime. " + "; ".join(consumed) + "."

    if move_name == "Teeter Dance":
        affected: list[str] = []
        for target in (attacker, defender):
            if target.current_hp <= 0 or target.confusion_turns > 0:
                continue
            target.confusion_turns = battle.rng.randint(2, 5)
            affected.append(target.name)
        if not affected:
            return f"{attacker.name} dùng Teeter Dance, nhưng không ai bị Confusion thêm."
        return f"{attacker.name} dùng Teeter Dance. Các Pokémon bị Confusion: {', '.join(affected)}."

    if move_name == "Telekinesis":
        if defender is battle.player_active:
            battle.player_magnet_rise_turns = max(getattr(battle, "player_magnet_rise_turns", 0), 3)
        else:
            battle.wild_magnet_rise_turns = max(getattr(battle, "wild_magnet_rise_turns", 0), 3)
        return f"{attacker.name} dùng Telekinesis. {defender.name} bị nâng lên trong 3 lượt (mô phỏng rút gọn: miễn nhiễm Ground)."

    if move_name == "Teleport":
        return f"{attacker.name} dùng Teleport. Cơ chế rời battle bằng move này được rút gọn trong bản hiện tại."

    if move_name == "Shell Smash":
        changed_atk, atk_text = battle._change_stat_stage(attacker, "attack", +2)
        changed_spa, spa_text = battle._change_stat_stage(attacker, "sp_attack", +2)
        changed_spe, spe_text = battle._change_stat_stage(attacker, "speed", +2)
        changed_def, def_text = battle._change_stat_stage(attacker, "defense", -1)
        changed_spd, spd_text = battle._change_stat_stage(attacker, "sp_defense", -1)
        if not any([changed_atk, changed_spa, changed_spe, changed_def, changed_spd]):
            return f"{attacker.name} dùng Shell Smash, nhưng chỉ số không thể thay đổi thêm."
        parts = [f"{attacker.name} dùng Shell Smash."]
        if changed_atk:
            parts.append(f"Attack tăng mạnh {atk_text}.")
        if changed_spa:
            parts.append(f"Sp. Attack tăng mạnh {spa_text}.")
        if changed_spe:
            parts.append(f"Speed tăng mạnh {spe_text}.")
        if changed_def:
            parts.append(f"Defense giảm {def_text}.")
        if changed_spd:
            parts.append(f"Sp. Defense giảm {spd_text}.")
        return " ".join(parts)

    if move_name == "Shore Up":
        blocked = battle.player_heal_block_turns > 0 if attacker is battle.player_active else battle.wild_heal_block_turns > 0
        if blocked:
            return f"{attacker.name} dùng Shore Up nhưng thất bại do Heal Block."
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể hồi phục vì đã gục."
        if attacker.current_hp >= attacker.max_hp:
            return f"{attacker.name} dùng Shore Up, nhưng HP đã đầy."
        ratio = 2 / 3 if getattr(battle, "weather", None) == "sandstorm" and getattr(battle, "weather_turns", 0) > 0 else 1 / 2
        before_hp = attacker.current_hp
        heal_amount = max(1, int(attacker.max_hp * ratio))
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
        healed = attacker.current_hp - before_hp
        return f"{attacker.name} dùng Shore Up và hồi {healed} HP ({attacker.current_hp}/{attacker.max_hp})."

    if move_name == "Silk Trap":
        if battle._try_activate_protect(attacker):
            if attacker is battle.player_active:
                battle.player_silk_trap_active = True
            else:
                battle.wild_silk_trap_active = True
            return f"{attacker.name} dùng Silk Trap và dựng lớp tơ phòng thủ."
        return f"{attacker.name} dùng Silk Trap nhưng thất bại do dùng liên tiếp."

    if move_name == "Simple Beam":
        defender.ability = "Simple"
        return f"{attacker.name} dùng Simple Beam. Ability của {defender.name} đổi thành Simple."

    if move_name == "Sketch":
        source_name = battle.player_last_move_name if defender is battle.player_active else battle.wild_last_move_name
        if not source_name or source_name in {"Sketch", "Struggle"}:
            return f"{attacker.name} dùng Sketch nhưng không có chiêu hợp lệ để sao chép."
        move_lookup = {m["name"]["english"]: m for m in getattr(battle.game_data, "moves", []) if m.get("name", {}).get("english")}
        raw = move_lookup.get(source_name)
        if raw is None:
            return f"{attacker.name} dùng Sketch nhưng không thể sao chép {source_name}."
        power_text = str(raw.get("power", "0")).replace("%", "").replace("—", "0").strip()
        try:
            power = max(0, int(float(power_text or "0")))
        except ValueError:
            power = 0
        accuracy_text = str(raw.get("accuracy", "100")).replace("%", "").strip()
        if accuracy_text in {"", "—"}:
            accuracy = 100
        else:
            try:
                accuracy = max(1, min(100, int(float(accuracy_text))))
            except ValueError:
                accuracy = 100
        pp_text = str(raw.get("pp", "1")).strip()
        try:
            base_pp = max(1, int(float(pp_text)))
        except ValueError:
            base_pp = 1
        move.name = source_name
        move.move_type = raw.get("type", "Normal")
        move.category = raw.get("category", "Physical")
        move.power = power
        move.accuracy = accuracy
        move.base_pp = base_pp
        move.max_pp = max(1, int(base_pp * 8 / 5))
        move.current_pp = min(move.max_pp, move.current_pp)
        move.target = get_default_target(source_name)
        move.priority = get_move_priority(source_name, raw.get("priority"))
        return f"{attacker.name} dùng Sketch và vĩnh viễn học chiêu {source_name} trong trận này."

    if move_name == "Skill Swap":
        attacker_ability = (attacker.ability or "").strip()
        defender_ability = (defender.ability or "").strip()
        attacker.ability, defender.ability = defender_ability, attacker_ability
        return f"{attacker.name} dùng Skill Swap. Ability của hai Pokémon đã hoán đổi cho nhau."

    if move_name == "Snatch":
        if attacker is battle.player_active:
            battle.player_snatch_active = True
        else:
            battle.wild_snatch_active = True
        return f"{attacker.name} dùng Snatch và sẵn sàng cướp hiệu ứng chiêu hỗ trợ của đối thủ trong lượt này (mô phỏng rút gọn)."

    if move_name == "Spite":
        target_last_move_name = battle.player_last_move_name if defender is battle.player_active else battle.wild_last_move_name
        if not target_last_move_name:
            return f"{attacker.name} dùng Spite nhưng mục tiêu chưa dùng chiêu nào để giảm PP."
        target_move = next((mv for mv in defender.moves if mv.name == target_last_move_name), None)
        if target_move is None:
            return f"{attacker.name} dùng Spite nhưng không tìm thấy chiêu phù hợp để giảm PP."
        if target_move.current_pp <= 0:
            return f"{attacker.name} dùng Spite nhưng PP của {target_last_move_name} đã bằng 0."
        reduced = min(target_move.current_pp, battle.rng.randint(2, 5))
        target_move.current_pp -= reduced
        return f"{attacker.name} dùng Spite. {target_last_move_name} của {defender.name} mất {reduced} PP."

    if move_name == "Splash":
        return f"{attacker.name} dùng Splash... nhưng không có gì xảy ra."

    if move_name == "Spotlight":
        return f"{attacker.name} dùng Spotlight, nhưng battle 1v1 nên không có đổi hướng mục tiêu."

    if move_name == "Sleep Talk":
        if attacker.status != "slp":
            return f"{attacker.name} dùng Sleep Talk nhưng đang không ngủ nên thất bại."
        candidates = [mv for mv in attacker.moves if mv.name not in {"Sleep Talk"} and mv.current_pp > 0]
        if not candidates:
            return f"{attacker.name} dùng Sleep Talk nhưng không có chiêu nào khác để gọi ra."
        chosen = battle.rng.choice(candidates)
        return f"{attacker.name} lảm nhảm trong giấc ngủ và gọi ra {chosen.name} (mô phỏng rút gọn)."

    if move_name == "Slack Off":
        blocked = battle.player_heal_block_turns > 0 if attacker is battle.player_active else battle.wild_heal_block_turns > 0
        if blocked:
            return f"{attacker.name} dùng Slack Off nhưng thất bại do Heal Block."
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể hồi phục vì đã gục."
        if attacker.current_hp >= attacker.max_hp:
            return f"{attacker.name} dùng Slack Off, nhưng HP đã đầy."
        before_hp = attacker.current_hp
        heal_amount = max(1, attacker.max_hp // 2)
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
        healed = attacker.current_hp - before_hp
        return f"{attacker.name} dùng Slack Off và hồi {healed} HP ({attacker.current_hp}/{attacker.max_hp})."

    if move_name == "Soft-Boiled":
        blocked = battle.player_heal_block_turns > 0 if attacker is battle.player_active else battle.wild_heal_block_turns > 0
        if blocked:
            return f"{attacker.name} dùng Soft-Boiled nhưng thất bại do Heal Block."
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể hồi phục vì đã gục."
        if attacker.current_hp >= attacker.max_hp:
            return f"{attacker.name} dùng Soft-Boiled, nhưng HP đã đầy."
        before_hp = attacker.current_hp
        heal_amount = max(1, attacker.max_hp // 2)
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
        healed = attacker.current_hp - before_hp
        return f"{attacker.name} dùng Soft-Boiled và hồi {healed} HP ({attacker.current_hp}/{attacker.max_hp})."

    if move_name == "Soak":
        if defender.current_hp <= 0:
            return f"{attacker.name} dùng Soak, nhưng mục tiêu đã gục."
        defender.types = ["Water"]
        return f"{attacker.name} dùng Soak. {defender.name} đổi thành hệ Water."

    if move_name == "Speed Swap":
        attacker.speed, defender.speed = defender.speed, attacker.speed
        return f"{attacker.name} dùng Speed Swap. Chỉ số Speed của hai bên đã hoán đổi."

    if move_name == "Spicy Extract":
        changed_def, def_text = battle._change_stat_stage(defender, "defense", -2)
        changed_atk, atk_text = battle._change_stat_stage(defender, "attack", +2)
        if not changed_def and not changed_atk:
            return f"{attacker.name} dùng Spicy Extract nhưng chỉ số của {defender.name} không thể thay đổi thêm."
        parts = [f"{attacker.name} dùng Spicy Extract."]
        if changed_def:
            parts.append(f"Defense của {defender.name} giảm mạnh {def_text}.")
        if changed_atk:
            parts.append(f"Attack của {defender.name} tăng mạnh {atk_text}.")
        return " ".join(parts)

    if move_name == "Spider Web":
        if defender is battle.player_active:
            battle.player_trapped_turns = max(battle.player_trapped_turns, 999)
        else:
            battle.wild_trapped_turns = max(battle.wild_trapped_turns, 999)
        return f"{attacker.name} dùng Spider Web. {defender.name} bị giữ chân, không thể đổi ra."

    if move_name == "Stockpile":
        if attacker is battle.player_active:
            if battle.player_stockpile_count >= 3:
                return f"{attacker.name} dùng Stockpile nhưng đã tích trữ tối đa 3 lần."
            battle.player_stockpile_count += 1
            count = battle.player_stockpile_count
        else:
            if battle.wild_stockpile_count >= 3:
                return f"{attacker.name} dùng Stockpile nhưng đã tích trữ tối đa 3 lần."
            battle.wild_stockpile_count += 1
            count = battle.wild_stockpile_count
        changed_def, def_text = battle._change_stat_stage(attacker, "defense", +1)
        changed_spd, spd_text = battle._change_stat_stage(attacker, "sp_defense", +1)
        parts = [f"{attacker.name} dùng Stockpile ({count}/3)."]
        if changed_def:
            parts.append(f"Defense tăng {def_text}.")
        if changed_spd:
            parts.append(f"Sp. Defense tăng {spd_text}.")
        return " ".join(parts)

    if move_name == "Strength Sap":
        target_attack = max(1, battle._effective_stat(defender, "attack"))
        changed, stage_text = battle._change_stat_stage(defender, "attack", -1)
        blocked = battle.player_heal_block_turns > 0 if attacker is battle.player_active else battle.wild_heal_block_turns > 0
        healed = 0
        if not blocked and attacker.current_hp > 0 and attacker.current_hp < attacker.max_hp:
            before_hp = attacker.current_hp
            attacker.current_hp = min(attacker.max_hp, attacker.current_hp + target_attack)
            healed = max(0, attacker.current_hp - before_hp)
        parts = [f"{attacker.name} dùng Strength Sap."]
        if changed:
            parts.append(f"Attack của {defender.name} giảm {stage_text}.")
        else:
            parts.append(f"Attack của {defender.name} không thể giảm thêm.")
        if blocked:
            parts.append("Nhưng hồi máu bị chặn bởi Heal Block.")
        else:
            parts.append(f"{attacker.name} hồi {healed} HP ({attacker.current_hp}/{attacker.max_hp}).")
        return " ".join(parts)

    if move_name == "Stuff Cheeks":
        held = (attacker.hold_item or "").strip()
        if not held:
            return f"{attacker.name} dùng Stuff Cheeks nhưng không có Berry để ăn."
        if "berry" not in held.lower():
            return f"{attacker.name} dùng Stuff Cheeks nhưng item hiện tại không phải Berry."
        attacker.hold_item = None
        attacker.berry_consumed = True
        changed, stage_text = battle._change_stat_stage(attacker, "defense", +2)
        if changed:
            return f"{attacker.name} ăn {held} bằng Stuff Cheeks và tăng mạnh Defense {stage_text}."
        return f"{attacker.name} ăn {held} bằng Stuff Cheeks, nhưng Defense đã tối đa."

    if move_name == "Substitute":
        cost = max(1, attacker.max_hp // 4)
        if attacker.current_hp <= cost:
            return f"{attacker.name} dùng Substitute nhưng không đủ HP để tạo bù nhìn."
        attacker.current_hp = max(1, attacker.current_hp - cost)
        return (
            f"{attacker.name} dùng Substitute, mất {cost} HP ({attacker.current_hp}/{attacker.max_hp}). "
            "Hiệu ứng bù nhìn được mô phỏng rút gọn trong bản hiện tại."
        )

    if move_name == "Swagger":
        changed, stage_text = battle._change_stat_stage(defender, "attack", +2)
        if defender.confusion_turns <= 0:
            defender.confusion_turns = battle.rng.randint(2, 5)
            confused_text = f" {defender.name} bị Confusion."
        else:
            confused_text = ""
        if changed:
            return f"{attacker.name} dùng Swagger. Attack của {defender.name} tăng mạnh {stage_text}.{confused_text}".strip()
        return f"{attacker.name} dùng Swagger.{confused_text}".strip()

    if move_name == "Swallow":
        stockpile_count = battle.player_stockpile_count if attacker is battle.player_active else battle.wild_stockpile_count
        if stockpile_count <= 0:
            return f"{attacker.name} dùng Swallow nhưng chưa Stockpile nên thất bại."
        blocked = battle.player_heal_block_turns > 0 if attacker is battle.player_active else battle.wild_heal_block_turns > 0
        if blocked:
            return f"{attacker.name} dùng Swallow nhưng thất bại do Heal Block."
        ratio_map = {1: 0.25, 2: 0.5, 3: 1.0}
        heal_ratio = ratio_map.get(stockpile_count, 1.0)
        before_hp = attacker.current_hp
        heal_amount = max(1, int(attacker.max_hp * heal_ratio))
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
        healed = max(0, attacker.current_hp - before_hp)
        battle._change_stat_stage(attacker, "defense", -stockpile_count)
        battle._change_stat_stage(attacker, "sp_defense", -stockpile_count)
        if attacker is battle.player_active:
            battle.player_stockpile_count = 0
        else:
            battle.wild_stockpile_count = 0
        return f"{attacker.name} dùng Swallow, hồi {healed} HP ({attacker.current_hp}/{attacker.max_hp}) và tiêu thụ toàn bộ Stockpile."

    if move_name == "Switcheroo":
        attacker_item = (attacker.hold_item or "").strip()
        defender_item = (defender.hold_item or "").strip()
        if not attacker_item and not defender_item:
            return f"{attacker.name} dùng Switcheroo nhưng cả hai bên đều không có item để đổi."
        attacker.hold_item, defender.hold_item = (defender_item or None), (attacker_item or None)
        return (
            f"{attacker.name} dùng Switcheroo và hoán đổi item: "
            f"{attacker.name} -> {attacker.hold_item or 'không có'}, "
            f"{defender.name} -> {defender.hold_item or 'không có'}."
        )

    if move_name == "Tickle":
        changed_atk, atk_text = battle._change_stat_stage(defender, "attack", -1)
        changed_def, def_text = battle._change_stat_stage(defender, "defense", -1)
        if not changed_atk and not changed_def:
            return f"{attacker.name} dùng Tickle, nhưng Attack/Defense của {defender.name} không thể giảm thêm."
        parts = [f"{attacker.name} dùng Tickle."]
        if changed_atk:
            parts.append(f"Attack của {defender.name} giảm {atk_text}.")
        if changed_def:
            parts.append(f"Defense của {defender.name} giảm {def_text}.")
        return " ".join(parts)

    if move_name == "Tidy Up":
        battle.player_spikes_layers = 0
        battle.player_toxic_spikes_layers = 0
        battle.player_stealth_rock = False
        battle.player_sticky_web = False
        battle.wild_spikes_layers = 0
        battle.wild_toxic_spikes_layers = 0
        battle.wild_stealth_rock = False
        battle.wild_sticky_web = False
        changed_atk, atk_text = battle._change_stat_stage(attacker, "attack", +1)
        changed_spe, spe_text = battle._change_stat_stage(attacker, "speed", +1)
        parts = [f"{attacker.name} dùng Tidy Up và dọn toàn bộ hazards trên sân."]
        if changed_atk:
            parts.append(f"Attack tăng {atk_text}.")
        if changed_spe:
            parts.append(f"Speed tăng {spe_text}.")
        parts.append("(Hiệu ứng xóa Substitute được rút gọn vì engine chưa mô phỏng Substitute đầy đủ).")
        return " ".join(parts)

    if move_name == "Topsy-Turvy":
        target_stages = battle._stat_stages_for(defender)
        if all(v == 0 for v in target_stages.values()):
            return f"{attacker.name} dùng Topsy-Turvy, nhưng {defender.name} không có thay đổi chỉ số để đảo ngược."
        for key in ["attack", "defense", "sp_attack", "sp_defense", "speed"]:
            target_stages[key] = -target_stages.get(key, 0)
        return f"{attacker.name} dùng Topsy-Turvy. Toàn bộ thay đổi chỉ số của {defender.name} đã bị đảo ngược."

    if move_name == "Torment":
        if defender is battle.player_active:
            battle.player_torment_turns = max(getattr(battle, "player_torment_turns", 0), 3)
        else:
            battle.wild_torment_turns = max(getattr(battle, "wild_torment_turns", 0), 3)
        return f"{attacker.name} dùng Torment. {defender.name} không thể dùng liên tiếp cùng một chiêu trong 3 lượt."

    if move_name == "Toxic Thread":
        if defender.status is None and "Poison" not in defender.types and "Steel" not in defender.types and defender.ability != "Immunity":
            defender.status = "psn"
            defender.status_counter = 0
            poisoned_text = f" {defender.name} bị Poison."
        else:
            poisoned_text = ""
        changed, stage_text = battle._change_stat_stage(defender, "speed", -1)
        if changed:
            return f"{attacker.name} dùng Toxic Thread. Speed của {defender.name} giảm {stage_text}.{poisoned_text}".strip()
        return f"{attacker.name} dùng Toxic Thread.{poisoned_text}".strip()

    if move_name == "Transform":
        if defender.current_hp <= 0:
            return f"{attacker.name} dùng Transform, nhưng mục tiêu đã gục."
        attacker.types = list(defender.types)
        attacker.attack = defender.attack
        attacker.defense = defender.defense
        attacker.sp_attack = defender.sp_attack
        attacker.sp_defense = defender.sp_defense
        attacker.speed = defender.speed
        attacker.ability = defender.ability
        return f"{attacker.name} dùng Transform và biến hình theo {defender.name} (mô phỏng rút gọn)."

    if move_name == "Trick":
        attacker_item = (attacker.hold_item or "").strip()
        defender_item = (defender.hold_item or "").strip()
        if not attacker_item and not defender_item:
            return f"{attacker.name} dùng Trick nhưng cả hai bên đều không có item để đổi."
        attacker.hold_item, defender.hold_item = (defender_item or None), (attacker_item or None)
        return (
            f"{attacker.name} dùng Trick và hoán đổi item: "
            f"{attacker.name} -> {attacker.hold_item or 'không có'}, "
            f"{defender.name} -> {defender.hold_item or 'không có'}."
        )

    if move_name == "Trick Room":
        if getattr(battle, "trick_room_turns", 0) > 0:
            battle.trick_room_turns = 0
            return f"{attacker.name} dùng Trick Room. Không gian trở lại bình thường."
        battle.trick_room_turns = 5
        parts = [f"{attacker.name} dùng Trick Room. Pokémon chậm hơn sẽ đi trước trong 5 lượt."]
        for pkmn in (battle.player_active, battle.wild):
            if pkmn.current_hp <= 0:
                continue
            if battle._held_item_name(pkmn) != "room service":
                continue
            changed, stage_text = battle._change_stat_stage(pkmn, "speed", -1)
            if changed:
                pkmn.hold_item = None
                parts.append(f"{pkmn.name} kích hoạt Room Service! Speed giảm {stage_text}.")
        return " ".join(parts)

    if move_name == "Trick-or-Treat":
        if "Ghost" in defender.types:
            return f"{attacker.name} dùng Trick-or-Treat, nhưng {defender.name} đã có hệ Ghost."
        defender.types = list(defender.types) + ["Ghost"]
        return f"{attacker.name} dùng Trick-or-Treat. {defender.name} được thêm hệ Ghost."

    if move_name == "Venom Drench":
        if defender.status not in {"psn", "tox"}:
            return f"{attacker.name} dùng Venom Drench nhưng thất bại vì {defender.name} chưa bị nhiễm độc."
        changed_atk, atk_text = battle._change_stat_stage(defender, "attack", -1)
        changed_spa, spa_text = battle._change_stat_stage(defender, "sp_attack", -1)
        changed_spe, spe_text = battle._change_stat_stage(defender, "speed", -1)
        if not changed_atk and not changed_spa and not changed_spe:
            return f"{attacker.name} dùng Venom Drench, nhưng chỉ số của {defender.name} không thể giảm thêm."
        parts = [f"{attacker.name} dùng Venom Drench."]
        if changed_atk:
            parts.append(f"Attack của {defender.name} giảm {atk_text}.")
        if changed_spa:
            parts.append(f"Sp. Attack của {defender.name} giảm {spa_text}.")
        if changed_spe:
            parts.append(f"Speed của {defender.name} giảm {spe_text}.")
        return " ".join(parts)

    if move_name == "Victory Dance":
        changed_atk, atk_text = battle._change_stat_stage(attacker, "attack", +1)
        changed_def, def_text = battle._change_stat_stage(attacker, "defense", +1)
        changed_spe, spe_text = battle._change_stat_stage(attacker, "speed", +1)
        if not changed_atk and not changed_def and not changed_spe:
            return f"{attacker.name} dùng Victory Dance, nhưng các chỉ số đã tối đa."
        parts = [f"{attacker.name} dùng Victory Dance."]
        if changed_atk:
            parts.append(f"Attack tăng {atk_text}.")
        if changed_def:
            parts.append(f"Defense tăng {def_text}.")
        if changed_spe:
            parts.append(f"Speed tăng {spe_text}.")
        return " ".join(parts)

    if move_name == "Sticky Web":
        if attacker is battle.player_active:
            if battle.wild_sticky_web:
                return f"{attacker.name} dùng Sticky Web, nhưng bẫy đã tồn tại phía đối thủ."
            battle.wild_sticky_web = True
            return f"{attacker.name} dùng Sticky Web. Phía đối thủ bị phủ tơ dính."
        if battle.player_sticky_web:
            return f"{attacker.name} dùng Sticky Web, nhưng bẫy đã tồn tại phía bạn."
        battle.player_sticky_web = True
        return f"{attacker.name} dùng Sticky Web. Phía bạn bị phủ tơ dính."

    if move_name == "Spiky Shield":
        if battle._try_activate_protect(attacker):
            if attacker is battle.player_active:
                battle.player_protect_active = True
                battle.player_spiky_shield_active = True
            else:
                battle.wild_protect_active = True
                battle.wild_spiky_shield_active = True
            return f"{attacker.name} dùng Spiky Shield và dựng khiên gai bảo vệ."
        return f"{attacker.name} dùng Spiky Shield nhưng thất bại do dùng liên tiếp."

    if move_name == "Sparkly Swirl":
        cured = 0
        if attacker is battle.player_active:
            for pkmn in battle.player.party:
                if pkmn.status is not None:
                    pkmn.status = None
                    pkmn.status_counter = 0
                    cured += 1
        else:
            if attacker.status is not None:
                attacker.status = None
                attacker.status_counter = 0
                cured = 1
        if cured <= 0:
            return f"{attacker.name} dùng Sparkly Swirl, nhưng không có trạng thái để chữa."
        return f"{attacker.name} dùng Sparkly Swirl và chữa trạng thái cho {cured} Pokémon."

    if move_name == "Supersonic":
        if defender.current_hp <= 0:
            return f"{attacker.name} dùng Supersonic, nhưng mục tiêu đã gục."
        if defender.confusion_turns > 0:
            return f"{attacker.name} dùng Supersonic, nhưng {defender.name} đã bị Confusion."
        defender.confusion_turns = battle.rng.randint(2, 5)
        return f"{attacker.name} dùng Supersonic. {defender.name} bị Confusion."

    if move_name == "Sweet Kiss":
        if defender.current_hp <= 0:
            return f"{attacker.name} dùng Sweet Kiss, nhưng mục tiêu đã gục."
        if defender.confusion_turns > 0:
            return f"{attacker.name} dùng Sweet Kiss, nhưng {defender.name} đã bị Confusion."
        defender.confusion_turns = battle.rng.randint(2, 5)
        return f"{attacker.name} dùng Sweet Kiss. {defender.name} bị Confusion."

    if move_name == "Spit Up":
        return f"{attacker.name} dùng Spit Up, nhưng cơ chế Stockpile chưa được mô phỏng đầy đủ nên chiêu này được rút gọn trong bản hiện tại."

    if move_name == "Smokescreen":
        return f"{attacker.name} dùng Smokescreen. Hiệu ứng giảm Accuracy được rút gọn trong engine hiện tại."

    if move_name == "Roar":
        if defender is battle.wild:
            defender.current_hp = 0
            return f"{attacker.name} gầm lên bằng Roar, Pokémon hoang dã bỏ chạy khỏi trận!"
        return f"{attacker.name} dùng Roar, nhưng cơ chế ép đổi của đối thủ trong battle 1v1 hiện được rút gọn."

    if move_name == "Rototiller":
        boosted_targets: list[str] = []
        battlers = [attacker, defender]
        for target in battlers:
            if "Grass" not in target.types:
                continue
            changed_atk, _ = battle._change_stat_stage(target, "attack", +1)
            changed_spa, _ = battle._change_stat_stage(target, "sp_attack", +1)
            if changed_atk or changed_spa:
                boosted_targets.append(target.name)
        if not boosted_targets:
            return f"{attacker.name} dùng Rototiller, nhưng không có Pokémon hệ Grass nào được tăng chỉ số."
        return f"{attacker.name} dùng Rototiller. Các Pokémon hệ Grass được cường hóa: {', '.join(boosted_targets)}."

    if move_name == "Sand Attack":
        return f"{attacker.name} dùng Sand Attack. Hiệu ứng giảm Accuracy được rút gọn trong engine hiện tại."

    if move_name == "Safeguard":
        if attacker is battle.player_active:
            battle.player_safeguard_turns = max(getattr(battle, "player_safeguard_turns", 0), 5)
        else:
            battle.wild_safeguard_turns = max(getattr(battle, "wild_safeguard_turns", 0), 5)
        return f"{attacker.name} dùng Safeguard. Phe này được bảo vệ khỏi trạng thái trong 5 lượt."

    if move_name == "Role Play":
        copied = (defender.ability or "").strip()
        if not copied:
            return f"{attacker.name} dùng Role Play nhưng mục tiêu không có Ability để sao chép."
        attacker.ability = copied
        return f"{attacker.name} dùng Role Play và sao chép Ability {copied}."

    if move_name == "Roost":
        blocked = battle.player_heal_block_turns > 0 if attacker is battle.player_active else battle.wild_heal_block_turns > 0
        if blocked:
            return f"{attacker.name} dùng Roost nhưng thất bại do Heal Block."
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể hồi phục vì đã gục."
        if attacker.current_hp >= attacker.max_hp:
            return f"{attacker.name} dùng Roost, nhưng HP đã đầy."
        before_hp = attacker.current_hp
        heal_amount = max(1, attacker.max_hp // 2)
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
        healed = attacker.current_hp - before_hp
        if "Flying" in attacker.types:
            if attacker is battle.player_active:
                battle.player_roost_original_types = list(attacker.types)
            else:
                battle.wild_roost_original_types = list(attacker.types)
            attacker.types = [tp for tp in attacker.types if tp != "Flying"] or ["Normal"]
            return (
                f"{attacker.name} dùng Roost và hồi {healed} HP ({attacker.current_hp}/{attacker.max_hp}). "
                f"Tạm thời mất hệ Flying trong lượt này."
            )
        return f"{attacker.name} dùng Roost và hồi {healed} HP ({attacker.current_hp}/{attacker.max_hp})."

    if move_name == "Perish Song":
        battle.player_perish_song_turns = 3 if battle.player_active.current_hp > 0 else 0
        battle.wild_perish_song_turns = 3 if battle.wild.current_hp > 0 else 0
        return f"{attacker.name} dùng Perish Song. Pokémon đang trên sân sẽ gục sau 3 lượt nếu không đổi ra."

    if move_name == "Play Nice":
        changed, stage_text = battle._change_stat_stage(defender, "attack", -1)
        if changed:
            return f"{attacker.name} dùng Play Nice. Attack của {defender.name} giảm {stage_text}."
        return f"{attacker.name} dùng Play Nice, nhưng Attack của {defender.name} không thể giảm thêm."

    if move_name == "Mud Sport":
        battle.mud_sport_turns = max(getattr(battle, "mud_sport_turns", 0), 5)
        return f"{attacker.name} dùng Mud Sport. Sức mạnh chiêu Electric giảm trong 5 lượt."

    if move_name == "Water Sport":
        battle.water_sport_turns = max(getattr(battle, "water_sport_turns", 0), 5)
        return f"{attacker.name} dùng Water Sport. Sức mạnh chiêu Fire giảm trong 5 lượt."

    if move_name == "Whirlwind":
        if defender is battle.wild:
            defender.current_hp = 0
            return f"{attacker.name} dùng Whirlwind, Pokémon hoang dã bị thổi bay khỏi trận!"
        return f"{attacker.name} dùng Whirlwind, nhưng cơ chế ép đổi đối thủ trong 1v1 hiện được rút gọn."

    if move_name == "Wide Guard":
        return f"{attacker.name} dùng Wide Guard, nhưng battle hiện tại là 1v1 nên không có đòn diện rộng để chặn."

    if move_name == "Wish":
        heal_amount = max(1, attacker.max_hp // 2)
        if attacker is battle.player_active:
            battle.player_wish_turns = 2
            battle.player_wish_heal = heal_amount
        else:
            battle.wild_wish_turns = 2
            battle.wild_wish_heal = heal_amount
        return f"{attacker.name} dùng Wish. Lời ước sẽ hồi HP vào cuối lượt kế tiếp."

    if move_name == "Wonder Room":
        if getattr(battle, "wonder_room_turns", 0) > 0:
            battle.wonder_room_turns = 0
            return f"{attacker.name} dùng Wonder Room. Defense và Sp. Defense trở lại bình thường."
        battle.wonder_room_turns = 5
        return f"{attacker.name} dùng Wonder Room. Defense và Sp. Defense bị hoán đổi trong 5 lượt."

    if move_name == "Lunar Dance":
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể dùng Lunar Dance vì đã gục."
        attacker.current_hp = 0
        if attacker is battle.player_active:
            battle.player_healing_wish_pending = True
        else:
            battle.wild_healing_wish_pending = True
        return f"{attacker.name} dùng Lunar Dance và hiến tế bản thân. Pokémon vào sân tiếp theo sẽ được hồi phục hoàn toàn."

    if move_name == "Magic Coat":
        if attacker is battle.player_active:
            battle.player_magic_coat_active = True
        else:
            battle.wild_magic_coat_active = True
        return f"{attacker.name} dùng Magic Coat và phản lại các status move trong lượt này."

    if move_name == "Magic Powder":
        if defender.current_hp <= 0:
            return f"{attacker.name} dùng Magic Powder, nhưng mục tiêu đã gục."
        defender.types = ["Psychic"]
        return f"{attacker.name} dùng Magic Powder. {defender.name} bị đổi thành hệ Psychic."

    if move_name == "Magic Room":
        battle.magic_room_turns = max(getattr(battle, "magic_room_turns", 0), 5)
        return f"{attacker.name} dùng Magic Room. Hiệu ứng item bị vô hiệu hóa trong 5 lượt."

    if move_name == "Me First":
        return f"{attacker.name} dùng Me First, nhưng cơ chế sao chép chiêu theo lượt hiện chưa được mô phỏng đầy đủ trong engine 1v1."

    if move_name == "Metronome":
        return f"{attacker.name} dùng Metronome. Cơ chế random move toàn cục chưa được mô phỏng đầy đủ trong bản hiện tại."

    if move_name == "Mimic":
        source_name = battle.player_last_move_name if defender is battle.player_active else battle.wild_last_move_name
        if not source_name or source_name in {"Mimic", "Struggle"}:
            return f"{attacker.name} dùng Mimic nhưng không có chiêu hợp lệ để sao chép."
        move_lookup = {m["name"]["english"]: m for m in getattr(battle.game_data, "moves", []) if m.get("name", {}).get("english")}
        raw = move_lookup.get(source_name)
        if raw is None:
            return f"{attacker.name} dùng Mimic nhưng không thể sao chép {source_name}."
        power_text = str(raw.get("power", "0")).replace("%", "").replace("—", "0").strip()
        try:
            power = max(0, int(float(power_text or "0")))
        except ValueError:
            power = 0
        accuracy_text = str(raw.get("accuracy", "100")).replace("%", "").strip()
        if accuracy_text in {"", "—"}:
            accuracy = 100
        else:
            try:
                accuracy = max(1, min(100, int(float(accuracy_text))))
            except ValueError:
                accuracy = 100
        pp_text = str(raw.get("pp", "1")).strip()
        try:
            base_pp = max(1, int(float(pp_text)))
        except ValueError:
            base_pp = 1
        move.name = source_name
        move.move_type = raw.get("type", "Normal")
        move.category = raw.get("category", "Physical")
        move.power = power
        move.accuracy = accuracy
        move.base_pp = base_pp
        move.max_pp = max(1, int(base_pp * 8 / 5))
        move.current_pp = min(move.max_pp, move.current_pp)
        move.target = get_default_target(source_name)
        move.priority = get_move_priority(source_name, raw.get("priority"))
        return f"{attacker.name} dùng Mimic và sao chép thành công chiêu {source_name}."

    if move_name == "Magnet Rise":
        if attacker is battle.player_active:
            battle.player_magnet_rise_turns = max(getattr(battle, "player_magnet_rise_turns", 0), 5)
        else:
            battle.wild_magnet_rise_turns = max(getattr(battle, "wild_magnet_rise_turns", 0), 5)
        return f"{attacker.name} dùng Magnet Rise và bay lơ lửng, miễn nhiễm Ground trong 5 lượt."

    if move_name == "Magnetic Flux":
        ability_name = (getattr(attacker, "ability", "") or "").strip()
        if ability_name not in {"Plus", "Minus"}:
            return f"{attacker.name} dùng Magnetic Flux nhưng thất bại vì không có Plus/Minus."
        changed_def, text_def = battle._change_stat_stage(attacker, "defense", +1)
        changed_spd, text_spd = battle._change_stat_stage(attacker, "sp_defense", +1)
        if changed_def or changed_spd:
            parts: list[str] = [f"{attacker.name} dùng Magnetic Flux."]
            if changed_def:
                parts.append(f"Defense tăng {text_def}.")
            if changed_spd:
                parts.append(f"Sp. Defense tăng {text_spd}.")
            return " ".join(parts)
        return f"{attacker.name} dùng Magnetic Flux nhưng các chỉ số đã tối đa."

    if move_name == "Mat Block":
        if battle._try_activate_protect(attacker):
            if attacker is battle.player_active:
                battle.player_protect_active = True
            else:
                battle.wild_protect_active = True
            return f"{attacker.name} dùng Mat Block và chặn các đòn tấn công trong lượt này."
        return f"{attacker.name} dùng Mat Block nhưng thất bại do dùng liên tiếp."

    if move_name == "Obstruct":
        if battle._try_activate_protect(attacker):
            if attacker is battle.player_active:
                battle.player_obstruct_active = True
            else:
                battle.wild_obstruct_active = True
            return f"{attacker.name} dùng Obstruct và dựng thế phòng thủ phản đòn."
        return f"{attacker.name} dùng Obstruct nhưng thất bại do dùng liên tiếp."

    if move_name == "Max Guard":
        if battle._try_activate_protect(attacker):
            if attacker is battle.player_active:
                battle.player_protect_active = True
            else:
                battle.wild_protect_active = True
            return f"{attacker.name} dùng Max Guard và dựng khiên bảo vệ."
        return f"{attacker.name} dùng Max Guard nhưng thất bại do dùng liên tiếp."

    if move_name == "Imprison":
        names = {mv.name for mv in attacker.moves}
        if attacker is battle.player_active:
            battle.wild_imprisoned_moves = names
        else:
            battle.player_imprisoned_moves = names
        return f"{attacker.name} dùng Imprison. Đối thủ không thể dùng các chiêu trùng với chiêu của {attacker.name}."

    if move_name == "Ingrain":
        if attacker is battle.player_active:
            if battle.player_ingrain:
                return f"{attacker.name} đã bám rễ từ trước."
            battle.player_ingrain = True
            battle.player_trapped_turns = max(battle.player_trapped_turns, 999)
        else:
            if battle.wild_ingrain:
                return f"{attacker.name} đã bám rễ từ trước."
            battle.wild_ingrain = True
            battle.wild_trapped_turns = max(battle.wild_trapped_turns, 999)
        return f"{attacker.name} dùng Ingrain và bám rễ xuống đất. Mỗi lượt sẽ hồi HP nhưng không thể đổi ra."

    if move_name in HEALING_MOVES:
        blocked = battle.player_heal_block_turns > 0 if attacker is battle.player_active else battle.wild_heal_block_turns > 0
        if blocked:
            return f"{attacker.name} dùng {move_name} nhưng thất bại do Heal Block."
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể hồi phục vì đã gục."
        if attacker.current_hp >= attacker.max_hp:
            return f"{attacker.name} dùng {move_name}, nhưng HP đã đầy."
        before_hp = attacker.current_hp
        heal_amount = max(1, int(attacker.max_hp * HEALING_MOVES[move_name]))
        attacker.current_hp = min(attacker.max_hp, attacker.current_hp + heal_amount)
        healed = attacker.current_hp - before_hp
        return f"{attacker.name} dùng {move_name} và hồi {healed} HP ({attacker.current_hp}/{attacker.max_hp})."

    if move_name == "Rest":
        blocked = battle.player_heal_block_turns > 0 if attacker is battle.player_active else battle.wild_heal_block_turns > 0
        if blocked:
            return f"{attacker.name} dùng Rest nhưng thất bại do Heal Block."
        if attacker.current_hp <= 0:
            return f"{attacker.name} không thể dùng Rest vì đã gục."
        if attacker.current_hp >= attacker.max_hp and attacker.status is None:
            return f"{attacker.name} dùng Rest, nhưng HP đã đầy và không có trạng thái để chữa."
        attacker.current_hp = attacker.max_hp
        attacker.status = "slp"
        attacker.status_counter = 2
        return f"{attacker.name} dùng Rest, hồi đầy HP và ngủ 2 lượt."

    if move_name == "Protect":
        if battle._try_activate_protect(attacker):
            return f"{attacker.name} dùng Protect và dựng khiên bảo vệ."
        return f"{attacker.name} dùng Protect nhưng thất bại do dùng liên tiếp."

    if move_name == "Baneful Bunker":
        if battle._try_activate_protect(attacker):
            if attacker is battle.player_active:
                battle.player_baneful_bunker_active = True
            else:
                battle.wild_baneful_bunker_active = True
            return f"{attacker.name} dùng Baneful Bunker và dựng khiên độc bảo vệ."
        return f"{attacker.name} dùng Baneful Bunker nhưng thất bại do dùng liên tiếp."

    if move_name == "Reflect":
        duration = battle._screen_duration(attacker) if hasattr(battle, "_screen_duration") else (8 if held_item == "light clay" else 5)
        if attacker is battle.player_active:
            battle.player_reflect_turns = max(battle.player_reflect_turns, duration)
        else:
            battle.wild_reflect_turns = max(battle.wild_reflect_turns, duration)
        return f"{attacker.name} dùng Reflect. Phòng thủ vật lý của phe này được tăng cường trong {duration} lượt."

    if move_name == "Light Screen":
        duration = battle._screen_duration(attacker) if hasattr(battle, "_screen_duration") else (8 if held_item == "light clay" else 5)
        if attacker is battle.player_active:
            battle.player_light_screen_turns = max(battle.player_light_screen_turns, duration)
        else:
            battle.wild_light_screen_turns = max(battle.wild_light_screen_turns, duration)
        return f"{attacker.name} dùng Light Screen. Phòng thủ đặc biệt của phe này được tăng cường trong {duration} lượt."

    if move_name == "Aurora Veil":
        if getattr(battle, "weather", None) != "snow" or getattr(battle, "weather_turns", 0) <= 0:
            return f"{attacker.name} dùng Aurora Veil nhưng thất bại vì không có thời tiết tuyết."
        duration = battle._screen_duration(attacker) if hasattr(battle, "_screen_duration") else (8 if held_item == "light clay" else 5)
        if attacker is battle.player_active:
            battle.player_reflect_turns = max(battle.player_reflect_turns, duration)
            battle.player_light_screen_turns = max(battle.player_light_screen_turns, duration)
        else:
            battle.wild_reflect_turns = max(battle.wild_reflect_turns, duration)
            battle.wild_light_screen_turns = max(battle.wild_light_screen_turns, duration)
        return f"{attacker.name} dùng Aurora Veil. Cả sát thương vật lý và đặc biệt lên phe này đều giảm trong {duration} lượt."

    if move_name == "Leech Seed":
        if "Grass" in defender.types:
            return f"{attacker.name} dùng Leech Seed, nhưng {defender.name} miễn nhiễm."
        if defender is battle.player_active:
            if battle.player_seeded:
                return f"{attacker.name} dùng Leech Seed, nhưng {defender.name} đã bị gieo hạt."
            battle.player_seeded = True
        else:
            if battle.wild_seeded:
                return f"{attacker.name} dùng Leech Seed, nhưng {defender.name} đã bị gieo hạt."
            battle.wild_seeded = True
        return f"{attacker.name} dùng Leech Seed. {defender.name} bị gieo hạt ký sinh."

    if move_name == "Spikes":
        if attacker is battle.player_active:
            if battle.wild_spikes_layers >= 3:
                return f"{attacker.name} dùng Spikes, nhưng bẫy đã đạt tối đa."
            battle.wild_spikes_layers += 1
            return f"{attacker.name} dùng Spikes. Bên đối thủ có {battle.wild_spikes_layers} lớp Spikes."
        if battle.player_spikes_layers >= 3:
            return f"{attacker.name} dùng Spikes, nhưng bẫy đã đạt tối đa."
        battle.player_spikes_layers += 1
        return f"{attacker.name} dùng Spikes. Bên bạn có {battle.player_spikes_layers} lớp Spikes."

    if move_name == "Toxic Spikes":
        if attacker is battle.player_active:
            if battle.wild_toxic_spikes_layers >= 2:
                return f"{attacker.name} dùng Toxic Spikes, nhưng bẫy đã đạt tối đa."
            battle.wild_toxic_spikes_layers += 1
            return f"{attacker.name} dùng Toxic Spikes. Bên đối thủ có {battle.wild_toxic_spikes_layers} lớp Toxic Spikes."
        if battle.player_toxic_spikes_layers >= 2:
            return f"{attacker.name} dùng Toxic Spikes, nhưng bẫy đã đạt tối đa."
        battle.player_toxic_spikes_layers += 1
        return f"{attacker.name} dùng Toxic Spikes. Bên bạn có {battle.player_toxic_spikes_layers} lớp Toxic Spikes."

    if move_name == "Stealth Rock":
        if attacker is battle.player_active:
            if battle.wild_stealth_rock:
                return f"{attacker.name} dùng Stealth Rock, nhưng bẫy đã tồn tại."
            battle.wild_stealth_rock = True
            return f"{attacker.name} dùng Stealth Rock. Đá nhọn xuất hiện bên đối thủ."
        if battle.player_stealth_rock:
            return f"{attacker.name} dùng Stealth Rock, nhưng bẫy đã tồn tại."
        battle.player_stealth_rock = True
        return f"{attacker.name} dùng Stealth Rock. Đá nhọn xuất hiện bên bạn."

    weather_moves = {
        "Rain Dance": ("rain", "damp rock"),
        "Sunny Day": ("harsh sunlight", "heat rock"),
        "Sandstorm": ("sandstorm", "smooth rock"),
        "Hail": ("snow", "icy rock"),
        "Snowscape": ("snow", "icy rock"),
    }
    if move_name in weather_moves:
        next_weather, extender_item = weather_moves[move_name]
        duration = battle._weather_duration(attacker, next_weather) if hasattr(battle, "_weather_duration") else (8 if held_item == extender_item else 5)
        battle.weather = next_weather
        battle.weather_turns = duration
        return f"{attacker.name} dùng {move_name}. Thời tiết chuyển thành {next_weather} trong {duration} lượt."

    terrain_moves = {
        "Electric Terrain": "electric terrain",
        "Grassy Terrain": "grassy terrain",
        "Misty Terrain": "misty terrain",
        "Psychic Terrain": "psychic terrain",
    }
    if move_name in terrain_moves:
        next_terrain = terrain_moves[move_name]
        if getattr(battle, "terrain", None) == next_terrain and getattr(battle, "terrain_turns", 0) > 0:
            return f"{attacker.name} dùng {move_name}, nhưng terrain này đã đang hiệu lực."
        battle.terrain = next_terrain
        duration = battle._terrain_duration(attacker) if hasattr(battle, "_terrain_duration") else (8 if held_item == "terrain extender" else 5)
        battle.terrain_turns = duration
        text = f"{attacker.name} dùng {move_name}. Sân đấu chuyển thành {next_terrain} trong {duration} lượt."
        if hasattr(battle, "_trigger_active_terrain_seeds"):
            seed_logs = battle._trigger_active_terrain_seeds()
            if seed_logs:
                text = text + "\n" + "\n".join(seed_logs)
        return text

    return None
