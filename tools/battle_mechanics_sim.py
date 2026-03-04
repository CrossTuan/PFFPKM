from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from game.data_loader import GameData


@dataclass(slots=True)
class SimMove:
    name: str
    move_type: str
    category: str
    power: int
    accuracy: int = 100


@dataclass(slots=True)
class SimPokemon:
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
    status: str | None = None


@dataclass(slots=True)
class MoveAction:
    move: SimMove
    forced_damage: int | None = None
    force_hit: bool = True


@dataclass(slots=True)
class SimResult:
    ok: bool
    title: str
    details: str


@dataclass(slots=True)
class SimBattle:
    data: GameData
    player: SimPokemon
    enemy: SimPokemon
    turn: int = 1
    logs: list[str] = field(default_factory=list)

    def type_multiplier(self, attack_type: str, defender_types: list[str]) -> float:
        return self.data.type_multiplier(attack_type, defender_types)

    def speed_order(self) -> list[str]:
        if self.player.speed > self.enemy.speed:
            return ["player", "enemy"]
        if self.enemy.speed > self.player.speed:
            return ["enemy", "player"]
        return ["player", "enemy"]

    def calc_damage(self, attacker: SimPokemon, defender: SimPokemon, move: SimMove, random_mul: float = 1.0) -> tuple[int, dict[str, float]]:
        if move.category == "Special":
            atk_stat = attacker.sp_attack
            def_stat = defender.sp_defense
        else:
            atk_stat = attacker.attack
            if attacker.status == "burn":
                atk_stat = math.floor(atk_stat * 0.5)
            def_stat = defender.defense

        base = (((2 * attacker.level / 5 + 2) * move.power * (atk_stat / max(1, def_stat))) / 50) + 2
        stab = 1.5 if move.move_type in attacker.types else 1.0
        type_mul = self.type_multiplier(move.move_type, defender.types)
        dmg = math.floor(max(1.0, base * stab * type_mul * random_mul))
        if type_mul == 0:
            dmg = 0

        return dmg, {
            "base": base,
            "stab": stab,
            "type": type_mul,
            "random": random_mul,
        }

    def run_turn(self, player_action: MoveAction, enemy_action: MoveAction) -> None:
        self.logs.append(f"--- Turn {self.turn} ---")
        order = self.speed_order()

        for side in order:
            if side == "player":
                self._do_action(self.player, self.enemy, player_action)
            else:
                self._do_action(self.enemy, self.player, enemy_action)

        self._apply_end_turn_status(self.player)
        self._apply_end_turn_status(self.enemy)

        self.turn += 1

    def _do_action(self, attacker: SimPokemon, defender: SimPokemon, action: MoveAction) -> None:
        if attacker.current_hp <= 0:
            self.logs.append(f"{attacker.name} đã fainted nên bỏ qua hành động.")
            return

        move = action.move
        if not action.force_hit:
            self.logs.append(f"{attacker.name} dùng {move.name} nhưng trượt!")
            return

        if action.forced_damage is not None:
            damage = action.forced_damage
            detail = "(forced damage for scenario check)"
        else:
            damage, parts = self.calc_damage(attacker, defender, move, random_mul=1.0)
            detail = f"(STAB x{parts['stab']}, Type x{parts['type']})"

        defender.current_hp = max(0, defender.current_hp - damage)
        self.logs.append(
            f"{attacker.name} dùng {move.name} gây {damage} damage lên {defender.name}. "
            f"{defender.name}: {defender.current_hp}/{defender.max_hp} HP {detail}"
        )

        if defender.current_hp <= 0:
            self.logs.append(f"{defender.name} đã fainted!")

    def _apply_end_turn_status(self, pokemon: SimPokemon) -> None:
        if pokemon.current_hp <= 0:
            return
        if pokemon.status == "burn":
            chip = max(1, math.floor(pokemon.max_hp / 16))
            pokemon.current_hp = max(0, pokemon.current_hp - chip)
            self.logs.append(
                f"{pokemon.name} bị burn mất {chip} HP cuối lượt ({pokemon.current_hp}/{pokemon.max_hp})."
            )


def test_stab(data: GameData) -> SimResult:
    battle = SimBattle(
        data=data,
        player=SimPokemon("Charmander", 20, ["Fire"], 50, 30, 20, 30, 20, 25, 50),
        enemy=SimPokemon("Eevee", 20, ["Normal"], 50, 25, 20, 25, 20, 20, 50),
    )
    fire_move = SimMove("Flamethrower", "Fire", "Special", 90)
    normal_move = SimMove("Swift", "Normal", "Special", 90)

    stab_dmg, _ = battle.calc_damage(battle.player, battle.enemy, fire_move, random_mul=1.0)
    non_stab_dmg, _ = battle.calc_damage(battle.player, battle.enemy, normal_move, random_mul=1.0)

    ratio = stab_dmg / max(1, non_stab_dmg)
    ok = stab_dmg > non_stab_dmg and ratio >= 1.45
    return SimResult(ok, "STAB 1.5x", f"Damage STAB={stab_dmg}, non-STAB={non_stab_dmg}, ratio={ratio:.2f}")


def test_physical_special_stats(data: GameData) -> SimResult:
    battle = SimBattle(
        data=data,
        player=SimPokemon("Lucario", 35, ["Fighting", "Steel"], 110, 80, 55, 80, 55, 60, 110),
        enemy=SimPokemon("Snorlax", 35, ["Normal"], 160, 60, 90, 40, 40, 30, 160),
    )

    physical = SimMove("Brick Break", "Fighting", "Physical", 75)
    special = SimMove("Aura Sphere", "Fighting", "Special", 75)

    p_dmg_tank, _ = battle.calc_damage(battle.player, battle.enemy, physical, random_mul=1.0)
    s_dmg_tank, _ = battle.calc_damage(battle.player, battle.enemy, special, random_mul=1.0)

    low_def_enemy = SimPokemon("GlassMon", 35, ["Normal"], 120, 50, 30, 40, 30, 30, 120)
    p_dmg_glass, _ = battle.calc_damage(battle.player, low_def_enemy, physical, random_mul=1.0)
    s_dmg_glass, _ = battle.calc_damage(battle.player, low_def_enemy, special, random_mul=1.0)

    ok = (
        p_dmg_glass > p_dmg_tank
        and s_dmg_glass > s_dmg_tank
        and p_dmg_tank < s_dmg_tank
    )
    details = (
        f"Physical vs high DEF={p_dmg_tank}, vs low DEF={p_dmg_glass}; "
        f"Special vs high SPDEF={s_dmg_tank}, vs low SPDEF={s_dmg_glass}."
    )
    return SimResult(ok, "Physical/Special dùng đúng chỉ số", details)


def test_speed_order(data: GameData) -> SimResult:
    battle = SimBattle(
        data=data,
        player=SimPokemon("FastMon", 10, ["Normal"], 40, 20, 20, 20, 20, 18, 40),
        enemy=SimPokemon("SlowMon", 10, ["Normal"], 40, 20, 20, 20, 20, 11, 40),
    )
    order = battle.speed_order()
    ok = order == ["player", "enemy"]
    return SimResult(ok, "Speed quyết định thứ tự", f"Order={order}, player_speed=18, enemy_speed=11")


def test_turn_flow_charmander_bulbasaur(data: GameData) -> SimResult:
    charmander = SimPokemon("Charmander", 5, ["Fire"], 20, 11, 10, 12, 10, 13, 20)
    bulbasaur = SimPokemon("Bulbasaur", 5, ["Grass", "Poison"], 21, 11, 11, 11, 11, 11, 21)
    battle = SimBattle(data, charmander, bulbasaur)

    ember = SimMove("Ember", "Fire", "Special", 40)
    vine_whip = SimMove("Vine Whip", "Grass", "Physical", 45)

    battle.run_turn(
        player_action=MoveAction(ember, forced_damage=11),
        enemy_action=MoveAction(vine_whip, forced_damage=3),
    )

    turn1_ok = battle.player.current_hp == 17 and battle.enemy.current_hp == 10

    battle.run_turn(
        player_action=MoveAction(ember, forced_damage=10),
        enemy_action=MoveAction(vine_whip, forced_damage=3),
    )

    faint_skip_logged = any("Bulbasaur đã fainted nên bỏ qua hành động." in line for line in battle.logs)
    turn2_ok = battle.enemy.current_hp == 0 and battle.player.current_hp == 17 and faint_skip_logged

    ok = turn1_ok and turn2_ok
    details = (
        "Turn1: Charmander gây 11, nhận 3 => Charmander 17/20, Bulbasaur 10/21. "
        "Turn2: Charmander gây 10 làm Bulbasaur 0 HP, Bulbasaur bị bỏ qua hành động."
    )
    return SimResult(ok, "Luồng lượt + faint skip", details)


def test_burn_effect(data: GameData) -> SimResult:
    battle = SimBattle(
        data=data,
        player=SimPokemon("BurnedMon", 30, ["Fire"], 96, 80, 50, 40, 50, 40, 96, status="burn"),
        enemy=SimPokemon("Target", 30, ["Normal"], 120, 50, 50, 50, 50, 30, 120),
    )

    slash = SimMove("Slash", "Normal", "Physical", 70)
    dmg_burn, _ = battle.calc_damage(battle.player, battle.enemy, slash, random_mul=1.0)

    fresh = SimPokemon("FreshMon", 30, ["Fire"], 96, 80, 50, 40, 50, 40, 96, status=None)
    dmg_fresh, _ = battle.calc_damage(fresh, battle.enemy, slash, random_mul=1.0)

    before_hp = battle.player.current_hp
    battle._apply_end_turn_status(battle.player)
    after_hp = battle.player.current_hp

    expected_chip = max(1, math.floor(battle.player.max_hp / 16))
    ok = dmg_burn < dmg_fresh and (before_hp - after_hp) == expected_chip
    details = (
        f"Physical damage normal={dmg_fresh}, burned={dmg_burn}; "
        f"burn chip={before_hp - after_hp} (expected {expected_chip})."
    )
    return SimResult(ok, "Burn: -50% ATK vật lý + 1/16 HP cuối lượt", details)


def test_type_interactions(data: GameData) -> SimResult:
    checks = [
        ("Fire", ["Grass"], 2.0),
        ("Fire", ["Water"], 0.5),
        ("Normal", ["Ghost"], 0.0),
        ("Electric", ["Ground"], 0.0),
        ("Ground", ["Electric"], 2.0),
    ]

    failures: list[str] = []
    for atk_type, def_types, expected in checks:
        got = data.type_multiplier(atk_type, def_types)
        if abs(got - expected) > 1e-9:
            failures.append(f"{atk_type} -> {def_types}: expected {expected}, got {got}")

    ok = len(failures) == 0
    details = "; ".join(failures) if failures else "Các cặp hệ mẫu đều đúng kỳ vọng."
    return SimResult(ok, "Tương tác hệ", details)


def print_report(results: list[SimResult]) -> None:
    print("==== BATTLE MECHANICS SIMULATION REPORT ====")
    passed = 0
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(f"[{status}] {result.title}")
        print(f"  -> {result.details}")
        if result.ok:
            passed += 1

    print("-------------------------------------------")
    print(f"Total: {passed}/{len(results)} checks passed")


def main() -> None:
    data = GameData(PROJECT_ROOT)
    data.load()

    results = [
        test_stab(data),
        test_physical_special_stats(data),
        test_speed_order(data),
        test_turn_flow_charmander_bulbasaur(data),
        test_burn_effect(data),
        test_type_interactions(data),
    ]
    print_report(results)


if __name__ == "__main__":
    main()
