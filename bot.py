from __future__ import annotations

import asyncio
import io
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Optional

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from game.data_loader import GameData
from game.logic import (
    HAPPINESS_EVOLVE_THRESHOLD,
    Battle,
    MoveSet,
    PlayerProfile,
    PokemonInstance,
    add_happiness,
    create_pokemon_instance,
    get_default_ability_for_species,
    get_species_by_id,
    recalculate_pokemon_stats,
)
from game.move_effects import get_default_target, get_move_priority
from game.storage import create_player_store
from keep_alive import start_keep_alive


ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")


def _resolve_player_store_path() -> Path:
    env_path = os.getenv("PLAYER_DATA_PATH", "").strip()
    if env_path:
        return Path(env_path)

    var_data_dir = Path("/var/data")
    if var_data_dir.exists() and var_data_dir.is_dir():
        return var_data_dir / "players.json"

    return ROOT / "data" / "players.json"


class PokemonDiscordBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        self.game_data = GameData(ROOT)
        self.store = create_player_store(_resolve_player_store_path())
        self.players: dict[int, PlayerProfile] = {}
        self.active_battles: dict[int, Battle] = {}
        self.gym_battle_meta: dict[int, dict[str, int]] = {}

    async def setup_hook(self) -> None:
        self.game_data.load()
        self.players = self.store.load_all()
        if self._migrate_missing_abilities():
            self.save_players()
        if self._migrate_legacy_move_pp():
            self.save_players()
        auto_sync = os.getenv("AUTO_SYNC_COMMANDS", "false").strip().lower() in {"1", "true", "yes", "on"}
        guild_id_raw = os.getenv("GUILD_ID", "").strip()
        command_scope = os.getenv("COMMAND_SCOPE", "guild").strip().lower()
        clean_other_scope = os.getenv("CLEAN_OTHER_SCOPE", "true").strip().lower() in {"1", "true", "yes", "on"}

        if auto_sync:
            if command_scope == "global":
                await self.tree.sync()
                print("Slash commands synced globally (single-scope mode).")
                if clean_other_scope and guild_id_raw.isdigit():
                    guild = discord.Object(id=int(guild_id_raw))
                    self.tree.clear_commands(guild=guild)
                    await self.tree.sync(guild=guild)
                    print(f"Cleared guild-scoped commands in guild {guild.id} to avoid duplicates.")
            elif guild_id_raw.isdigit():
                guild = discord.Object(id=int(guild_id_raw))
                self.tree.clear_commands(guild=guild)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                print(f"Slash commands synced to guild {guild.id} (single-scope mode).")
                if clean_other_scope:
                    self.tree.clear_commands(guild=None)
                    await self.tree.sync()
                    print("Cleared global commands to avoid duplicates with guild scope.")
            else:
                await self.tree.sync()
                print("Slash commands synced globally (fallback because GUILD_ID is missing/invalid).")
        else:
            print("AUTO_SYNC_COMMANDS is disabled; using existing registered slash commands.")

    def _migrate_legacy_move_pp(self) -> bool:
        move_base_pp_by_name: dict[str, int] = {}
        for move in self.game_data.moves:
            name = move.get("name", {}).get("english")
            if not name:
                continue
            raw_pp = str(move.get("pp", "1")).replace("*", "").strip()
            try:
                base_pp = int(float(raw_pp))
            except ValueError:
                base_pp = 1
            move_base_pp_by_name[name.lower()] = max(1, base_pp)

        changed = False
        for profile in self.players.values():
            for pokemon in [*profile.party, *profile.pc]:
                for move in pokemon.moves:
                    default_base_pp = move_base_pp_by_name.get(move.name.lower(), max(1, move.base_pp))
                    default_max_pp = default_base_pp

                    legacy_pp = move.base_pp <= 1 and move.max_pp <= 1
                    if legacy_pp:
                        move.base_pp = default_base_pp
                        move.max_pp = default_max_pp
                        move.pp_up_level = 0
                        if move.current_pp <= 1:
                            move.current_pp = default_max_pp
                        changed = True
                        continue

                    if move.base_pp <= 0:
                        move.base_pp = default_base_pp
                        changed = True
                    if getattr(move, "pp_up_level", None) is None:
                        move.pp_up_level = 0
                        changed = True
                    if move.max_pp <= 0:
                        move.max_pp = default_max_pp
                        changed = True
                    if move.max_pp > move.base_pp and move.pp_up_level == 0:
                        move.max_pp = move.base_pp
                        if move.current_pp > move.max_pp:
                            move.current_pp = move.max_pp
                        changed = True
                    if move.current_pp > move.max_pp:
                        move.current_pp = move.max_pp
                        changed = True

        return changed

    def _migrate_missing_abilities(self) -> bool:
        species_by_id: dict[int, dict] = {}
        for species in self.game_data.pokedex:
            try:
                species_by_id[int(species.get("id"))] = species
            except (TypeError, ValueError):
                continue

        changed = False
        for profile in self.players.values():
            for pokemon in [*profile.party, *profile.pc]:
                if pokemon.ability:
                    continue
                species = species_by_id.get(int(pokemon.species_id))
                if not species:
                    continue
                ability_name = get_default_ability_for_species(species)
                if ability_name:
                    pokemon.ability = ability_name
                    changed = True
        return changed

    def get_player(self, user_id: int) -> PlayerProfile:
        profile = self.players.get(user_id)
        if profile is None:
            profile = PlayerProfile(user_id=user_id)
            self.players[user_id] = profile
        return profile

    def save_players(self) -> None:
        self.store.save_all(self.players)

    def save_player(self, user_id: int) -> None:
        profile = self.players.get(user_id)
        if profile is None:
            return
        self.store.save_player(profile)


bot = PokemonDiscordBot()


def ensure_started(profile: PlayerProfile) -> bool:
    return profile.started and len(profile.party) > 0


def get_available_pokeballs(profile: PlayerProfile) -> list[tuple[str, int]]:
    balls: list[tuple[str, int]] = []
    for item_name, amount in profile.inventory.items():
        if amount <= 0:
            continue
        item_data = bot.game_data.items_by_name.get(item_name)
        if item_data and item_data.get("type") == "Pokeballs":
            balls.append((item_name, amount))
    return sorted(balls, key=lambda x: x[0])


def get_available_battle_items(profile: PlayerProfile) -> list[tuple[str, int]]:
    usable_item_names = {
        "Potion",
        "Super Potion",
        "Hyper Potion",
        "Max Potion",
        "Full Restore",
        "Fresh Water",
        "Remedy",
        "Energy Powder",
        "Energy Root",
        "Fine Remedy",
        "Superb Remedy",
        "Soda Pop",
        "Lemonade",
        "Moomoo Milk",
        "Berry Juice",
        "Sweet Heart",
        "Antidote",
        "Awakening",
        "Burn Heal",
        "Ice Heal",
        "Paralyze Heal",
        "Big Malasada",
        "Casteliacone",
        "Jubilife Muffin",
        "Lava Cookie",
        "Lumiose Galette",
        "Old Gateau",
        "Pewter Crunchies",
        "Rage Candy Bar",
        "Shalour Sable",
        "Heal Powder",
        "Full Heal",
        "Revive",
        "Revival Herb",
        "Sacred Ash",
        "Ether",
        "Elixir",
        "Max Ether",
        "Max Elixir",
        "X Attack",
        "X Defend",
        "X Sp. Atk",
        "X Sp. Def",
        "X Speed",
        "PP Up",
        "PP Max",
    }
    items: list[tuple[str, int]] = []
    for item_name, amount in profile.inventory.items():
        if amount <= 0:
            continue
        if item_name in usable_item_names:
            items.append((item_name, amount))
    return sorted(items, key=lambda x: x[0])


_EVOLUTIONARY_ITEMS_CACHE: set[str] | None = None

MANUAL_EVOLUTIONARY_ITEMS: set[str] = {
    "Auspicious Armor",
    "Berry Sweet",
    "Black Augurite",
    "Chipped Pot",
    "Clover Sweet",
    "Cracked Pot",
    "Dawn Stone",
    "Deep Sea Scale",
    "Deep Sea Tooth",
    "Dragon Scale",
    "Dubious Disc",
    "Dusk Stone",
    "Electirizer",
    "Fire Stone",
    "Flower Sweet",
    "Galarica Cuff",
    "Galarica Wreath",
    "Ice Stone",
    "King's Rock",
    "Leader's Crest",
    "Leaf Stone",
    "Linking Cord",
    "Love Sweet",
    "Magmarizer",
    "Malicious Armor",
    "Masterpiece Teacup",
    "Metal Alloy",
    "Metal Coat",
    "Moon Stone",
    "Oval Stone",
    "Peat Block",
    "Prism Scale",
    "Protector",
    "Razor Claw",
    "Razor Fang",
    "Reaper Cloth",
    "Ribbon Sweet",
    "Sachet",
    "Scroll of Darkness",
    "Scroll of Waters",
    "Shiny Stone",
    "Star Sweet",
    "Strawberry Sweet",
    "Sun Stone",
    "Sweet Apple",
    "Syrupy Apple",
    "Tart Apple",
    "Thunder Stone",
    "Unremarkable Teacup",
    "Upgrade",
    "Water Stone",
    "Whipped Dream",
}

MANUAL_KEY_ITEMS_LOWER: set[str] = {
    "exp. share",
    "exp share",
    "exp-share",
    "exp. all",
    "exp all",
    "exp-all",
    "exp. share all",
    "exp share all",
    "exp-share-all",
    "mega bracelet",
    "mega ring",
    "mega-ring",
    "shiny charm",
    "tera orb",
    "teraorb",
    "tera-orb",
    "z-ring",
    "z ring",
    "dynamax band",
    "dyna band",
}


def get_evolutionary_item_names() -> set[str]:
    global _EVOLUTIONARY_ITEMS_CACHE
    if _EVOLUTIONARY_ITEMS_CACHE is not None:
        return _EVOLUTIONARY_ITEMS_CACHE

    if not bot.game_data.items_by_name:
        _EVOLUTIONARY_ITEMS_CACHE = set()
        return _EVOLUTIONARY_ITEMS_CACHE

    canonical_by_lower = {
        item_name.lower(): item_name
        for item_name in bot.game_data.items_by_name.keys()
    }
    ordered_item_names = sorted(canonical_by_lower.keys(), key=len, reverse=True)

    evolutionary_items: set[str] = {
        canonical_by_lower.get(item_name.lower(), item_name)
        for item_name in MANUAL_EVOLUTIONARY_ITEMS
    }
    for species in bot.game_data.pokedex:
        evolution = species.get("evolution", {}) or {}
        next_entries = evolution.get("next", [])
        if not isinstance(next_entries, list):
            continue

        for entry in next_entries:
            if not isinstance(entry, list) or len(entry) < 2:
                continue

            condition_raw = entry[1]
            condition_parts: list[str]
            if isinstance(condition_raw, str):
                condition_parts = [condition_raw]
            elif isinstance(condition_raw, list):
                condition_parts = [str(part) for part in condition_raw]
            else:
                condition_parts = [str(condition_raw)]

            for condition in condition_parts:
                lowered = condition.strip().lower()
                if not lowered:
                    continue
                for normalized_item_name in ordered_item_names:
                    if normalized_item_name in lowered:
                        evolutionary_items.add(canonical_by_lower[normalized_item_name])
                        break

    _EVOLUTIONARY_ITEMS_CACHE = evolutionary_items
    return evolutionary_items


def get_pokedex_image_path(species_id: int, image_kind: str) -> Path:
    return bot.game_data.data_root / "images" / "pokedex" / image_kind / f"{species_id:03d}.png"


SHOP_PAGE_POKEBALL = "pokeball"
SHOP_PAGE_POTION = "potion"
SHOP_PAGE_OTHER = "other"

SHOP_FIXED_PRICES: dict[str, int] = {
    "Poké Ball": 200,
    "Great Ball": 600,
    "Ultra Ball": 1200,
    "Potion": 300,
    "Super Potion": 700,
    "Hyper Potion": 1200,
    "Full Heal": 600,
    "Exp. Share": 10000,
    "Exp. Share All": 100000,
    "Exp. All": 100000,
}

SHOP_TYPE_DEFAULT_PRICE: dict[str, int] = {
    "Pokeballs": 800,
    "Machines": 8000,
    "Hold items": 6000,
    "Berries": 800,
    "Battle items": 1200,
    "General items": 1500,
}

POTION_ALWAYS_STOCK = {"Potion", "Super Potion", "Hyper Potion", "Full Heal"}
POTION_EXCLUDE_RANDOM = {
    "Potion",
    "Super Potion",
    "Hyper Potion",
    "Full Heal",
    "Sacred Ash",
    "Scared Ash",
}

POTION_RANDOM_CANDIDATE_NAMES = {
    "Fresh Water",
    "Remedy",
    "Energy Powder",
    "Energy Root",
    "Fine Remedy",
    "Superb Remedy",
    "Soda Pop",
    "Lemonade",
    "Moomoo Milk",
    "Berry Juice",
    "Sweet Heart",
    "Antidote",
    "Awakening",
    "Burn Heal",
    "Ice Heal",
    "Paralyze Heal",
    "Big Malasada",
    "Casteliacone",
    "Jubilife Muffin",
    "Lava Cookie",
    "Lumiose Galette",
    "Old Gateau",
    "Pewter Crunchies",
    "Rage Candy Bar",
    "Shalour Sable",
    "Heal Powder",
    "Revive",
    "Revival Herb",
    "Ether",
    "Elixir",
    "Max Ether",
    "Max Elixir",
}


def _normalize_shop_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _resolve_item_name(item_name: str) -> str | None:
    direct = bot.game_data.items_by_name.get(item_name)
    if direct:
        return item_name

    target = _normalize_shop_name(item_name)
    for existing in bot.game_data.items_by_name.keys():
        if _normalize_shop_name(existing) == target:
            return existing
    return None


def _shop_price(item_name: str) -> int:
    direct = SHOP_FIXED_PRICES.get(item_name)
    if direct is not None:
        return direct

    item_data = bot.game_data.items_by_name.get(item_name)
    if not item_data:
        return 1000
    return SHOP_TYPE_DEFAULT_PRICE.get(str(item_data.get("type", "")), 1200)


def _daily_rng(page: str) -> random.Random:
    now = time.localtime()
    day_key = f"{now.tm_year:04d}-{now.tm_mon:02d}-{now.tm_mday:02d}:{page}"
    return random.Random(day_key)


def _shop_page_stock(page: str) -> list[str]:
    if page == SHOP_PAGE_POKEBALL:
        fixed = []
        for base_name in ["Poké Ball", "Great Ball", "Ultra Ball"]:
            resolved = _resolve_item_name(base_name)
            if resolved:
                fixed.append(resolved)

        excluded = {
            _normalize_shop_name("Poké Ball"),
            _normalize_shop_name("Great Ball"),
            _normalize_shop_name("Ultra Ball"),
            _normalize_shop_name("Master Ball"),
        }
        pool = [
            item_name
            for item_name, item_data in bot.game_data.items_by_name.items()
            if item_data.get("type") == "Pokeballs"
            and _normalize_shop_name(item_name) not in excluded
        ]
        pool = sorted(set(pool))
        rng = _daily_rng(page)
        random_slots = rng.sample(pool, k=min(2, len(pool)))
        return fixed + random_slots

    if page == SHOP_PAGE_POTION:
        fixed: list[str] = []
        for base_name in ["Potion", "Super Potion", "Hyper Potion", "Full Heal"]:
            resolved = _resolve_item_name(base_name)
            if resolved:
                fixed.append(resolved)

        excluded_norm = {_normalize_shop_name(name) for name in POTION_EXCLUDE_RANDOM}
        pool = []
        for name in POTION_RANDOM_CANDIDATE_NAMES:
            resolved = _resolve_item_name(name)
            if resolved and _normalize_shop_name(resolved) not in excluded_norm:
                pool.append(resolved)
        pool = sorted(set(pool))
        rng = _daily_rng(page)
        random_slots = rng.sample(pool, k=min(2, len(pool)))
        return fixed + random_slots

    fixed_other = []
    exp_share = _resolve_item_name("Exp. Share")
    if exp_share:
        fixed_other.append(exp_share)
    exp_share_all = _resolve_item_name("Exp. Share All") or _resolve_item_name("Exp. All") or "Exp. Share All"
    fixed_other.append(exp_share_all)

    rng = _daily_rng(page)
    tms = sorted(
        {
            name
            for name, item_data in bot.game_data.items_by_name.items()
            if item_data.get("type") == "Machines" and name.upper().startswith("TM")
        }
    )
    hold_items = sorted(
        {
            name
            for name, item_data in bot.game_data.items_by_name.items()
            if item_data.get("type") == "Hold items"
        }
    )
    berries = sorted(
        {
            name
            for name, item_data in bot.game_data.items_by_name.items()
            if item_data.get("type") == "Berries"
        }
    )

    random_tms = rng.sample(tms, k=min(2, len(tms)))
    random_hold = rng.sample(hold_items, k=min(2, len(hold_items)))
    random_berries = rng.sample(berries, k=min(2, len(berries)))
    return fixed_other + random_tms + random_hold + random_berries


def _shop_page_title(page: str) -> str:
    if page == SHOP_PAGE_POKEBALL:
        return "Shop - Poké Ball"
    if page == SHOP_PAGE_POTION:
        return "Shop - Potion"
    return "Shop - Khác"


def _build_shop_embed(profile: PlayerProfile, page: str) -> discord.Embed:
    stock = _shop_page_stock(page)
    lines = []
    for idx, item_name in enumerate(stock, start=1):
        lines.append(f"{idx}. {item_name} - {_shop_price(item_name)}₽")

    now = time.localtime()
    day_text = f"{now.tm_year:04d}-{now.tm_mon:02d}-{now.tm_mday:02d}"
    embed = discord.Embed(
        title=_shop_page_title(page),
        description="\n".join(lines) if lines else "(Hết hàng)",
        color=discord.Color.green(),
    )
    embed.set_footer(text=f"PokéDollars: {profile.money} | Random reset mỗi ngày ({day_text})")
    return embed


class ShopItemSelect(discord.ui.Select):
    def __init__(self, author_id: int, page: str, quantity: int):
        self.author_id = author_id
        self.page = page
        self.quantity = quantity
        stock = _shop_page_stock(page)
        options = [
            discord.SelectOption(
                label=item_name[:100],
                description=f"Giá: {_shop_price(item_name)}₽",
                value=item_name,
            )
            for item_name in stock[:25]
        ]
        super().__init__(
            placeholder=f"Chọn item để mua x{quantity}",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không thể mua đồ trong shop của người khác.", ephemeral=True)
            return

        profile = bot.get_player(interaction.user.id)
        if not ensure_started(profile):
            await interaction.response.send_message("Bạn cần dùng `/start` trước.", ephemeral=True)
            return

        item_name = self.values[0]
        stock = _shop_page_stock(self.page)
        if item_name not in stock:
            await interaction.response.send_message("Item này không còn trong trang shop hiện tại.", ephemeral=True)
            return

        quantity = max(1, int(getattr(self.view, "quantity", self.quantity)))
        unit_price = _shop_price(item_name)
        total_price = unit_price * quantity
        if profile.money < total_price:
            await interaction.response.send_message(
                f"Không đủ tiền. Bạn cần {total_price}₽ nhưng hiện có {profile.money}₽.",
                ephemeral=True,
            )
            return

        profile.money -= total_price
        profile.inventory[item_name] = profile.inventory.get(item_name, 0) + quantity
        await asyncio.to_thread(bot.save_player, interaction.user.id)

        embed = _build_shop_embed(profile, self.page)
        await interaction.response.edit_message(
            content=f"Đã mua {item_name} x{quantity} với giá {total_price}₽ ({unit_price}₽/món).",
            embed=embed,
            view=ShopView(self.author_id, self.page, quantity=quantity),
        )


class ShopQuantitySelect(discord.ui.Select):
    def __init__(self, author_id: int, page: str, quantity: int):
        self.author_id = author_id
        self.page = page
        self.quantity = quantity
        options = [
            discord.SelectOption(label="x1", value="1", default=quantity == 1),
            discord.SelectOption(label="x5", value="5", default=quantity == 5),
            discord.SelectOption(label="x10", value="10", default=quantity == 10),
        ]
        super().__init__(
            placeholder="Chọn số lượng mua",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không thể thao tác shop của người khác.", ephemeral=True)
            return
        selected_qty = int(self.values[0])
        profile = bot.get_player(interaction.user.id)
        embed = _build_shop_embed(profile, self.page)
        await interaction.response.edit_message(
            content=f"Đã chọn số lượng mua x{selected_qty}.",
            embed=embed,
            view=ShopView(self.author_id, self.page, quantity=selected_qty),
        )


class ShopView(discord.ui.View):
    def __init__(self, author_id: int, page: str, quantity: int = 1):
        super().__init__(timeout=180)
        self.author_id = author_id
        self.page = page
        self.quantity = max(1, quantity)
        self.add_item(ShopQuantitySelect(author_id, page, self.quantity))
        self.add_item(ShopItemSelect(author_id, page, self.quantity))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không thể thao tác shop của người khác.", ephemeral=True)
            return False
        return True

    async def _switch_page(self, interaction: discord.Interaction, page: str) -> None:
        profile = bot.get_player(interaction.user.id)
        embed = _build_shop_embed(profile, page)
        await interaction.response.edit_message(
            content=f"Số lượng hiện tại: x{self.quantity}",
            embed=embed,
            view=ShopView(self.author_id, page, quantity=self.quantity),
        )

    @discord.ui.button(label="Trang Pokeball", style=discord.ButtonStyle.primary)
    async def page_pokeball(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self._switch_page(interaction, SHOP_PAGE_POKEBALL)

    @discord.ui.button(label="Trang Potion", style=discord.ButtonStyle.primary)
    async def page_potion(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self._switch_page(interaction, SHOP_PAGE_POTION)

    @discord.ui.button(label="Trang Khác", style=discord.ButtonStyle.primary)
    async def page_other(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await self._switch_page(interaction, SHOP_PAGE_OTHER)


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _canonical_item_name(item_text: str | None) -> str | None:
    if not item_text:
        return None
    raw = str(item_text).strip()
    if not raw:
        return None

    direct = bot.game_data.items_by_name.get(raw)
    if direct:
        return raw

    wanted = _normalize_token(raw)
    if not wanted:
        return None

    for item_name in bot.game_data.items_by_name.keys():
        if _normalize_token(item_name) == wanted:
            return item_name

    for item_name in bot.game_data.items_by_name.keys():
        if wanted in _normalize_token(item_name):
            return item_name

    return raw


def _is_daytime_now() -> bool:
    hour = time.localtime().tm_hour
    return 6 <= hour < 18


def _parse_evolution_condition(condition: str) -> dict[str, Any]:
    lowered = condition.strip().lower()

    level_match = re.search(r"level\s*(\d+)", lowered)
    min_level = int(level_match.group(1)) if level_match else None

    use_item_match = re.search(r"use\s+([a-z0-9\-\'\.\s]+)", condition, flags=re.IGNORECASE)
    use_item = _canonical_item_name(use_item_match.group(1).strip()) if use_item_match else None

    trade_holding_match = re.search(r"trade\s+holding\s+([a-z0-9\-\'\.\s]+)", condition, flags=re.IGNORECASE)
    trade_holding_item = _canonical_item_name(trade_holding_match.group(1).strip()) if trade_holding_match else None

    hold_item_match = re.search(r"hold\s+([a-z0-9\-\'\.\s]+)", condition, flags=re.IGNORECASE)
    hold_item = _canonical_item_name(hold_item_match.group(1).strip()) if hold_item_match else None

    time_requirement: str | None = None
    if "daytime" in lowered or "day" in lowered:
        time_requirement = "day"
    elif "nighttime" in lowered or "night" in lowered:
        time_requirement = "night"

    return {
        "raw": condition,
        "min_level": min_level,
        "requires_friendship": "high friendship" in lowered,
        "requires_trade": "trade" in lowered,
        "use_item": use_item,
        "trade_holding_item": trade_holding_item,
        "hold_item": hold_item,
        "time_requirement": time_requirement,
    }


def _check_condition_ready(
    profile: PlayerProfile,
    pokemon: PokemonInstance,
    parsed: dict[str, Any],
    *,
    context: str,
) -> tuple[bool, str | None]:
    if parsed["requires_trade"] and context != "trade":
        return False, "Cần tiến hóa qua trao đổi"

    if not parsed["requires_trade"] and context == "trade":
        return False, "Không phải dạng tiến hóa qua trade"

    min_level = parsed.get("min_level")
    if min_level is not None and pokemon.level < min_level:
        return False, f"Cần Lv.{min_level}"

    if parsed.get("requires_friendship") and int(getattr(pokemon, "happiness", 70)) < HAPPINESS_EVOLVE_THRESHOLD:
        return False, f"Cần Happiness >= {HAPPINESS_EVOLVE_THRESHOLD}"

    time_requirement = parsed.get("time_requirement")
    if time_requirement == "day" and not _is_daytime_now():
        return False, "Chỉ tiến hóa ban ngày"
    if time_requirement == "night" and _is_daytime_now():
        return False, "Chỉ tiến hóa ban đêm"

    use_item = parsed.get("use_item")
    if use_item:
        if profile.inventory.get(use_item, 0) <= 0:
            return False, f"Thiếu item {use_item}"

    required_hold = parsed.get("trade_holding_item") or parsed.get("hold_item")
    if required_hold:
        if _normalize_token(pokemon.hold_item or "") != _normalize_token(required_hold):
            return False, f"Cần cầm {required_hold}"

    return True, None


def _collect_evolution_choices(
    profile: PlayerProfile,
    pokemon: PokemonInstance,
    *,
    context: str,
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], str | None]:
    species = get_species_by_id(bot.game_data, pokemon.species_id)
    if not species:
        return [], "Không tìm thấy dữ liệu species"

    evolution = species.get("evolution", {}) or {}
    next_entries = evolution.get("next", [])
    if not isinstance(next_entries, list) or not next_entries:
        return [], "Pokémon này không còn dạng tiến hóa"

    choices: list[tuple[dict[str, Any], dict[str, Any]]] = []
    first_block_reason: str | None = None

    for entry in next_entries:
        if not isinstance(entry, list) or len(entry) < 2:
            continue

        try:
            target_id = int(entry[0])
        except (TypeError, ValueError):
            continue
        target_species = get_species_by_id(bot.game_data, target_id)
        if not target_species:
            continue

        raw_condition = entry[1]
        condition_parts: list[str]
        if isinstance(raw_condition, str):
            condition_parts = [raw_condition]
        elif isinstance(raw_condition, list):
            condition_parts = [str(part) for part in raw_condition if str(part).strip()]
        else:
            condition_parts = [str(raw_condition)]

        if not condition_parts:
            condition_parts = [""]

        for part in condition_parts:
            parsed = _parse_evolution_condition(part)
            ready, blocked_reason = _check_condition_ready(profile, pokemon, parsed, context=context)
            if ready:
                choices.append((target_species, parsed))
            elif first_block_reason is None and blocked_reason:
                first_block_reason = blocked_reason

    if choices:
        return choices, None
    return [], first_block_reason or "Chưa đáp ứng điều kiện tiến hóa"


def _apply_evolution(
    profile: PlayerProfile,
    pokemon: PokemonInstance,
    target_species: dict[str, Any],
    parsed_condition: dict[str, Any],
) -> str:
    consumed_item = None
    use_item = parsed_condition.get("use_item")
    if use_item:
        amount = int(profile.inventory.get(use_item, 0))
        if amount > 0:
            profile.inventory[use_item] = amount - 1
            if profile.inventory[use_item] <= 0:
                profile.inventory.pop(use_item, None)
            consumed_item = use_item

    old_name = pokemon.name
    pokemon.species_id = int(target_species.get("id", pokemon.species_id))
    pokemon.name = str(target_species.get("name", {}).get("english", pokemon.name))
    pokemon.types = list(target_species.get("type", pokemon.types))
    pokemon.ability = get_default_ability_for_species(target_species)
    pokemon.image_url = (
        target_species.get("image", {}).get("thumbnail")
        or target_species.get("image", {}).get("sprite")
        or pokemon.image_url
    )
    recalculate_pokemon_stats(bot.game_data, pokemon, preserve_current_hp_ratio=True)

    if consumed_item:
        return f"{old_name} đã tiến hóa thành {pokemon.name} và tiêu hao {consumed_item}."
    return f"{old_name} đã tiến hóa thành {pokemon.name}."


def _try_evolve_pokemon(profile: PlayerProfile, pokemon: PokemonInstance, *, context: str) -> tuple[bool, str]:
    choices, reason = _collect_evolution_choices(profile, pokemon, context=context)
    if not choices:
        return False, reason or "Không thể tiến hóa lúc này"

    target_species, parsed_condition = choices[0]
    return True, _apply_evolution(profile, pokemon, target_species, parsed_condition)


TYPE_BUTTON_STYLE: dict[str, discord.ButtonStyle] = {
    "Fire": discord.ButtonStyle.danger,
    "Fighting": discord.ButtonStyle.danger,
    "Dark": discord.ButtonStyle.danger,
    "Ghost": discord.ButtonStyle.danger,
    "Dragon": discord.ButtonStyle.danger,
    "Water": discord.ButtonStyle.success,
    "Grass": discord.ButtonStyle.success,
    "Bug": discord.ButtonStyle.success,
    "Ground": discord.ButtonStyle.success,
    "Rock": discord.ButtonStyle.success,
    "Electric": discord.ButtonStyle.primary,
    "Ice": discord.ButtonStyle.primary,
    "Psychic": discord.ButtonStyle.primary,
    "Fairy": discord.ButtonStyle.primary,
    "Flying": discord.ButtonStyle.primary,
    "Steel": discord.ButtonStyle.secondary,
    "Poison": discord.ButtonStyle.secondary,
    "Normal": discord.ButtonStyle.secondary,
}


def _effectiveness_symbol(multiplier: float) -> str:
    if multiplier <= 0:
        return "🚫"
    if multiplier >= 4:
        return "🔼🔼"
    if multiplier >= 2:
        return "🔼"
    if multiplier <= 0.25:
        return "🔽🔽"
    if multiplier < 1:
        return "🔽"
    return "-"


def _move_button_visual(battle: Battle, attacker: Any, defender: Any, move: Any, slot_no: int) -> tuple[str, discord.ButtonStyle]:
    pp_text = f"{move.current_pp}/{move.max_pp}"
    move_type = str(getattr(move, "move_type", "Normal"))
    style = TYPE_BUTTON_STYLE.get(move_type, discord.ButtonStyle.secondary)

    is_damaging = str(getattr(move, "category", "")).lower() != "status" and int(getattr(move, "power", 0)) > 0
    if is_damaging:
        multiplier = float(bot.game_data.type_multiplier(move_type, getattr(defender, "types", [])))
        eff = _effectiveness_symbol(multiplier)
    else:
        eff = "-"

    stab = "★" if is_damaging and move_type in getattr(attacker, "types", []) else ""
    label = f"{slot_no}. {stab}{eff} {move.name} [{pp_text}]"
    if len(label) > 80:
        label = label[:77] + "..."
    return label, style


def build_pc_roster_image(profile: PlayerProfile) -> discord.File | None:
    try:
        from PIL import Image, ImageDraw, ImageFont  # type: ignore[import-not-found]
    except ImportError:
        return None

    row_height = 54
    width = 980

    try:
        title_font = ImageFont.truetype("arial.ttf", 30)
        text_font = ImageFont.truetype("arial.ttf", 24)
    except OSError:
        try:
            title_font = ImageFont.truetype("DejaVuSans.ttf", 30)
            text_font = ImageFont.truetype("DejaVuSans.ttf", 24)
        except OSError:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()

    party_rows = len(profile.party) if profile.party else 1
    pc_rows = min(len(profile.pc), 30) if profile.pc else 1
    total_rows = 2 + party_rows + 1 + pc_rows
    height = 28 + total_rows * row_height

    canvas = Image.new("RGBA", (width, height), (32, 34, 37, 255))
    draw = ImageDraw.Draw(canvas)

    y = 12
    draw.text((16, y), "Party", fill=(255, 255, 255, 255), font=title_font)
    y += row_height

    if profile.party:
        for idx, pokemon in enumerate(profile.party, start=1):
            sprite_path = get_pokedex_image_path(pokemon.species_id, "sprites")
            if sprite_path.exists():
                sprite = Image.open(sprite_path).convert("RGBA").resize((40, 40), Image.Resampling.NEAREST)
                canvas.paste(sprite, (74, y + 6), sprite)
            draw.text((16, y + 10), f"{idx}.", fill=(224, 224, 224, 255), font=text_font)
            draw.text(
                (124, y + 10),
                f"{pokemon.name} Lv.{pokemon.level} ({pokemon.current_hp}/{pokemon.max_hp} HP)",
                fill=(224, 224, 224, 255),
                font=text_font,
            )
            y += row_height
    else:
        draw.text((16, y + 10), "(trống)", fill=(224, 224, 224, 255), font=text_font)
        y += row_height

    draw.text((16, y), "PC", fill=(255, 255, 255, 255), font=title_font)
    y += row_height

    if profile.pc:
        for idx, pokemon in enumerate(profile.pc[:30], start=1):
            sprite_path = get_pokedex_image_path(pokemon.species_id, "sprites")
            if sprite_path.exists():
                sprite = Image.open(sprite_path).convert("RGBA").resize((40, 40), Image.Resampling.NEAREST)
                canvas.paste(sprite, (74, y + 6), sprite)
            draw.text((16, y + 10), f"{idx}.", fill=(224, 224, 224, 255), font=text_font)
            draw.text(
                (124, y + 10),
                f"{pokemon.name} Lv.{pokemon.level} ({pokemon.current_hp}/{pokemon.max_hp} HP)",
                fill=(224, 224, 224, 255),
                font=text_font,
            )
            y += row_height
    else:
        draw.text((16, y + 10), "(trống)", fill=(224, 224, 224, 255), font=text_font)

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    buffer.seek(0)
    return discord.File(buffer, filename="pc_roster.png")


GEN_STARTERS: dict[int, list[str]] = {
    1: ["Bulbasaur", "Charmander", "Squirtle"],
    2: ["Chikorita", "Cyndaquil", "Totodile"],
    3: ["Treecko", "Torchic", "Mudkip"],
    4: ["Turtwig", "Chimchar", "Piplup"],
    5: ["Snivy", "Tepig", "Oshawott"],
    6: ["Chespin", "Fennekin", "Froakie"],
    7: ["Rowlet", "Litten", "Popplio"],
    8: ["Grookey", "Scorbunny", "Sobble"],
    9: ["Sprigatito", "Fuecoco", "Quaxly"],
}

GYM_TYPES: list[str] = [
    "Normal",
    "Fire",
    "Water",
    "Electric",
    "Grass",
    "Ice",
    "Fighting",
    "Poison",
    "Ground",
    "Flying",
    "Psychic",
    "Bug",
    "Rock",
    "Ghost",
    "Dragon",
    "Dark",
    "Steel",
    "Fairy",
]

GYM_GRADE_CONFIG: dict[int, dict[str, int]] = {
    1: {"trainers": 1, "trainer_party": 2, "trainer_min": 5, "trainer_max": 8, "leader_party": 2, "leader_level": 10},
    2: {"trainers": 1, "trainer_party": 2, "trainer_min": 10, "trainer_max": 16, "leader_party": 3, "leader_level": 20},
    3: {"trainers": 2, "trainer_party": 2, "trainer_min": 20, "trainer_max": 26, "leader_party": 3, "leader_level": 30},
    4: {"trainers": 2, "trainer_party": 3, "trainer_min": 30, "trainer_max": 36, "leader_party": 4, "leader_level": 40},
    5: {"trainers": 3, "trainer_party": 3, "trainer_min": 40, "trainer_max": 46, "leader_party": 4, "leader_level": 50},
    6: {"trainers": 3, "trainer_party": 4, "trainer_min": 50, "trainer_max": 56, "leader_party": 5, "leader_level": 60},
    7: {"trainers": 3, "trainer_party": 4, "trainer_min": 60, "trainer_max": 66, "leader_party": 6, "leader_level": 70},
    8: {"trainers": 4, "trainer_party": 4, "trainer_min": 70, "trainer_max": 76, "leader_party": 6, "leader_level": 80},
}

BST_UNLOCK_BY_GRADE: dict[int, int] = {
    0: 215,
    1: 250,
    2: 280,
    3: 300,
    4: 350,
    5: 400,
    6: 450,
    7: 500,
    8: 550,
}

WALK_LEVEL_RANGE_BY_GRADE: dict[int, tuple[int, int]] = {
    0: (2, 5),
    1: (2, 8),
    2: (5, 15),
    3: (10, 22),
    4: (15, 30),
    5: (18, 35),
    6: (20, 40),
    7: (25, 50),
    8: (30, 60),
}

GYM_WITHDRAW_TIMEOUT_SECONDS = 3600

SPECIAL_EXCLUDED_NAMES: set[str] = {
    "Articuno", "Zapdos", "Moltres", "Mewtwo", "Mew", "Raikou", "Entei", "Suicune", "Lugia", "Ho-Oh", "Celebi",
    "Regirock", "Regice", "Registeel", "Latias", "Latios", "Kyogre", "Groudon", "Rayquaza", "Jirachi", "Deoxys",
    "Uxie", "Mesprit", "Azelf", "Dialga", "Palkia", "Heatran", "Regigigas", "Giratina", "Cresselia", "Phione",
    "Manaphy", "Darkrai", "Shaymin", "Arceus", "Victini", "Cobalion", "Terrakion", "Virizion", "Tornadus", "Thundurus",
    "Reshiram", "Zekrom", "Landorus", "Kyurem", "Keldeo", "Meloetta", "Genesect", "Xerneas", "Yveltal", "Zygarde",
    "Diancie", "Hoopa", "Volcanion", "Type: Null", "Silvally", "Tapu Koko", "Tapu Lele", "Tapu Bulu", "Tapu Fini",
    "Cosmog", "Cosmoem", "Solgaleo", "Lunala", "Necrozma", "Magearna", "Marshadow", "Zeraora", "Meltan", "Melmetal",
    "Zacian", "Zamazenta", "Eternatus", "Kubfu", "Urshifu", "Zarude", "Regieleki", "Regidrago", "Glastrier", "Spectrier",
    "Calyrex", "Enamorus", "Wo-Chien", "Chien-Pao", "Ting-Lu", "Chi-Yu", "Koraidon", "Miraidon", "Walking Wake",
    "Iron Leaves", "Gouging Fire", "Raging Bolt", "Iron Boulder", "Iron Crown", "Terapagos", "Pecharunt",
    "Nihilego", "Buzzwole", "Pheromosa", "Xurkitree", "Celesteela", "Kartana", "Guzzlord", "Poipole", "Naganadel",
    "Stakataka", "Blacephalon", "Great Tusk", "Scream Tail", "Brute Bonnet", "Flutter Mane", "Slither Wing", "Sandy Shocks",
    "Roaring Moon", "Iron Treads", "Iron Bundle", "Iron Hands", "Iron Jugulis", "Iron Moth", "Iron Thorns", "Iron Valiant",
}

ULTRA_BEAST_NAMES: set[str] = {
    "Nihilego", "Buzzwole", "Pheromosa", "Xurkitree", "Celesteela", "Kartana", "Guzzlord",
    "Poipole", "Naganadel", "Stakataka", "Blacephalon",
}

PARADOX_NAMES: set[str] = {
    "Great Tusk", "Scream Tail", "Brute Bonnet", "Flutter Mane", "Slither Wing", "Sandy Shocks",
    "Roaring Moon", "Iron Treads", "Iron Bundle", "Iron Hands", "Iron Jugulis", "Iron Moth",
    "Iron Thorns", "Iron Valiant", "Walking Wake", "Iron Leaves", "Gouging Fire", "Raging Bolt",
    "Iron Boulder", "Iron Crown",
}

PSEUDO_NAMES: set[str] = {
    "Dragonite", "Tyranitar", "Salamence", "Metagross", "Garchomp", "Hydreigon", "Goodra", "Kommo-o", "Dragapult", "Baxcalibur",
}

LEGENDARY_MYTHICAL_NAMES: set[str] = SPECIAL_EXCLUDED_NAMES - PSEUDO_NAMES - ULTRA_BEAST_NAMES - PARADOX_NAMES


def _now_ts() -> int:
    return int(time.time())


def _species_bst(species: dict) -> int:
    base = species.get("base", {})
    return int(base.get("HP", 0)) + int(base.get("Attack", 0)) + int(base.get("Defense", 0)) + int(base.get("Sp. Attack", 0)) + int(base.get("Sp. Defense", 0)) + int(base.get("Speed", 0))


def _is_evolved_form(species: dict) -> bool:
    evolution = species.get("evolution", {}) or {}
    return "prev" in evolution


def _has_next_evolution(species: dict) -> bool:
    evolution = species.get("evolution", {}) or {}
    nxt = evolution.get("next")
    return isinstance(nxt, list) and len(nxt) > 0


def _is_special_excluded_species(species: dict) -> bool:
    name = species.get("name", {}).get("english", "")
    return name in SPECIAL_EXCLUDED_NAMES or name in PSEUDO_NAMES


def _is_legendary_or_mythical_species(species: dict) -> bool:
    name = species.get("name", {}).get("english", "")
    return name in LEGENDARY_MYTHICAL_NAMES


def _is_ultra_beast_species(species: dict) -> bool:
    name = species.get("name", {}).get("english", "")
    if name in ULTRA_BEAST_NAMES:
        return True

    profile = species.get("profile", {}) or {}
    abilities = profile.get("ability", [])
    for ability_entry in abilities:
        if isinstance(ability_entry, list) and ability_entry:
            if str(ability_entry[0]).strip().lower() == "beast boost":
                return True
    return False


def _is_eligible_gym_species(species: dict, *, grade: int) -> bool:
    if _is_legendary_or_mythical_species(species):
        return False
    if grade < 5 and _is_ultra_beast_species(species):
        return False
    return True


def _player_best_gym_grade(profile: PlayerProfile) -> int:
    if not profile.gym_badges:
        return 0
    return max(int(v) for v in profile.gym_badges.values())


def _player_unlocked_types(profile: PlayerProfile) -> set[str]:
    return {k for k, v in profile.gym_badges.items() if int(v) > 0}


def _is_gym_run_expired(run: dict) -> bool:
    if run.get("state") != "paused":
        return False
    return _now_ts() > int(run.get("paused_until", 0))


def _cleanup_expired_gym_run(profile: PlayerProfile) -> bool:
    run = profile.gym_run
    if not isinstance(run, dict):
        return False
    if _is_gym_run_expired(run):
        profile.gym_run = None
        return True
    return False


def _is_gym_locked(profile: PlayerProfile) -> bool:
    run = profile.gym_run
    return isinstance(run, dict) and run.get("state") == "active"


def _build_walk_pool(profile: PlayerProfile) -> list[dict]:
    best_grade = max(0, min(8, _player_best_gym_grade(profile)))
    unlocked_types = _player_unlocked_types(profile)

    starter_pool: list[dict] = []
    unlocked_pool: list[dict] = []
    threshold = BST_UNLOCK_BY_GRADE.get(best_grade, 215)
    evolved_unlocked = best_grade >= 3

    for species in bot.game_data.pokedex:
        if _is_special_excluded_species(species):
            continue
        bst = _species_bst(species)
        types = set(species.get("type", []))

        if (
            bst <= 215
            and not _is_evolved_form(species)
            and _has_next_evolution(species)
        ):
            starter_pool.append(species)

        if best_grade <= 0:
            continue
        if bst > threshold:
            continue
        if not (types & unlocked_types):
            continue
        if not evolved_unlocked and (_is_evolved_form(species) or not _has_next_evolution(species)):
            continue
        unlocked_pool.append(species)

    pool_by_id: dict[int, dict] = {}
    for species in [*starter_pool, *unlocked_pool]:
        try:
            sid = int(species.get("id", 0))
        except (TypeError, ValueError):
            continue
        if sid > 0:
            pool_by_id[sid] = species
    return list(pool_by_id.values())


def _choose_walk_encounters(profile: PlayerProfile, count: int = 5) -> list[tuple[dict, int]]:
    pool = _build_walk_pool(profile)
    if not pool:
        pool = [p for p in bot.game_data.pokedex if not _is_special_excluded_species(p)]
    picks = random.sample(pool, k=min(count, len(pool)))
    best_grade = max(0, min(8, _player_best_gym_grade(profile)))
    min_lv, max_lv = WALK_LEVEL_RANGE_BY_GRADE.get(best_grade, (2, 5))
    return [(species, random.randint(min_lv, max_lv)) for species in picks]


def _is_current_gym_leader_battle(user_id: int) -> bool:
    profile = bot.get_player(user_id)
    run = profile.gym_run if isinstance(profile.gym_run, dict) else None
    meta = bot.gym_battle_meta.get(user_id)
    if not run or not meta:
        return False
    battles = run.get("battles", [])
    battle_index = int(meta.get("battle_index", -1))
    if battle_index < 0 or battle_index >= len(battles):
        return False
    return str(battles[battle_index].get("role", "trainer")) == "leader"


def _build_gym_battle_plan(gym_type: str, grade: int) -> list[dict[str, int | str]]:
    cfg = GYM_GRADE_CONFIG[grade]
    candidates = [
        species for species in bot.game_data.pokedex
        if gym_type in species.get("type", []) and _is_eligible_gym_species(species, grade=grade)
    ]
    if not candidates:
        candidates = [species for species in bot.game_data.pokedex if gym_type in species.get("type", []) and not _is_legendary_or_mythical_species(species)]

    leader_candidates = [species for species in candidates if not _has_next_evolution(species)]
    if not leader_candidates:
        leader_candidates = candidates

    battles: list[dict[str, int | str]] = []
    for trainer_no in range(1, cfg["trainers"] + 1):
        for slot in range(1, cfg["trainer_party"] + 1):
            species = random.choice(candidates)
            battles.append(
                {
                    "role": "trainer",
                    "trainer_no": trainer_no,
                    "slot": slot,
                    "slot_total": cfg["trainer_party"],
                    "species_id": int(species["id"]),
                    "level": random.randint(cfg["trainer_min"], cfg["trainer_max"]),
                    "exp_multiplier": 1,
                }
            )

    for slot in range(1, cfg["leader_party"] + 1):
        species = random.choice(leader_candidates)
        battles.append(
            {
                "role": "leader",
                "trainer_no": 0,
                "slot": slot,
                "slot_total": cfg["leader_party"],
                "species_id": int(species["id"]),
                "level": cfg["leader_level"],
                "exp_multiplier": 1,
            }
        )
    return battles


def _find_species_by_id(species_id: int) -> dict | None:
    for species in bot.game_data.pokedex:
        if int(species.get("id", 0)) == species_id:
            return species
    return None


def _choose_tm_for_type(gym_type: str) -> str | None:
    move_type_lookup = {
        m.get("name", {}).get("english", "").lower(): m.get("type", "")
        for m in bot.game_data.moves
        if m.get("name", {}).get("english")
    }
    machine_items = [
        item for item in bot.game_data.items
        if item.get("type") == "Machines" and item.get("name", {}).get("english")
    ]
    random.shuffle(machine_items)
    for item in machine_items:
        description = str(item.get("description", ""))
        move_names = re.findall(r"[A-Za-z'\-.]+(?:\s+[A-Za-z'\-.]+)*", description)
        for move_name in move_names:
            mtype = move_type_lookup.get(move_name.strip().lower())
            if mtype == gym_type:
                return item["name"]["english"]
    if machine_items:
        return machine_items[0]["name"]["english"]
    return None


def _choose_random_hold_item() -> str | None:
    hold_items = [
        item.get("name", {}).get("english")
        for item in bot.game_data.items
        if item.get("type") == "Hold items" and item.get("name", {}).get("english")
    ]
    if not hold_items:
        return None
    return random.choice(hold_items)


REVIVE_TARGET_ITEMS: set[str] = {"Revive", "Revival Herb"}
PP_MOVE_TARGET_ITEMS: set[str] = {"Ether", "Max Ether"}


def _parse_move_numeric(raw_value: Any, default: int = 0) -> int:
    text = str(raw_value).strip()
    if not text or text == "—":
        return default
    cleaned = text.replace("%", "").replace("*", "").strip()
    try:
        return int(float(cleaned))
    except (ValueError, TypeError):
        return default


def _tm_move_names() -> set[str]:
    move_lookup = {
        m.get("name", {}).get("english", "").strip().lower(): m.get("name", {}).get("english", "").strip()
        for m in bot.game_data.moves
        if m.get("name", {}).get("english")
    }
    tm_names: set[str] = set()
    for item in bot.game_data.items:
        if item.get("type") != "Machines":
            continue
        description_lower = str(item.get("description", "")).lower()
        for move_key, move_name in move_lookup.items():
            if move_key and move_key in description_lower:
                tm_names.add(move_name)
    return tm_names


def _build_tm_cover_move_for_species(species: dict, existing_move_names: set[str]) -> MoveSet | None:
    defender_types = list(species.get("type", []))
    if not defender_types:
        return None

    weakness_types = [
        atk_type
        for atk_type in bot.game_data.type_chart.keys()
        if bot.game_data.type_multiplier(atk_type, defender_types) > 1.0
    ]
    if not weakness_types:
        return None

    move_by_name = {
        m.get("name", {}).get("english", "").strip(): m
        for m in bot.game_data.moves
        if m.get("name", {}).get("english")
    }
    tm_names = _tm_move_names()
    cover_candidates: list[dict[str, Any]] = []
    for move_name in tm_names:
        if move_name in existing_move_names:
            continue
        raw = move_by_name.get(move_name)
        if not raw:
            continue

        category = str(raw.get("category", "Status"))
        power = _parse_move_numeric(raw.get("power", 0), default=0)
        if category == "Status" or power <= 0:
            continue

        attack_type = str(raw.get("type", "Normal"))
        if any(bot.game_data.type_multiplier(attack_type, [weak]) > 1.0 for weak in weakness_types):
            cover_candidates.append(raw)

    if not cover_candidates:
        return None

    chosen = random.choice(cover_candidates)
    chosen_name = str(chosen.get("name", {}).get("english", "Hidden Power"))
    base_pp = max(1, _parse_move_numeric(chosen.get("pp", 1), default=1))
    accuracy = max(1, min(100, _parse_move_numeric(chosen.get("accuracy", 100), default=100)))
    priority = get_move_priority(chosen_name, chosen.get("priority"))
    target = get_default_target(chosen_name)

    return MoveSet(
        name=chosen_name,
        move_type=str(chosen.get("type", "Normal")),
        category=str(chosen.get("category", "Physical")),
        power=_parse_move_numeric(chosen.get("power", 0), default=0),
        accuracy=accuracy,
        base_pp=base_pp,
        max_pp=base_pp,
        current_pp=base_pp,
        pp_up_level=0,
        makes_contact=False,
        target=target,
        priority=priority,
    )


def _apply_leader_cover_tm_move(wild: Any, species: dict) -> None:
    if not getattr(wild, "moves", None):
        return

    level_up_moves = list(wild.moves)
    existing_names = {mv.name for mv in level_up_moves}
    cover_move = _build_tm_cover_move_for_species(species, existing_names)
    if cover_move is None:
        return

    kept_level_up = level_up_moves[:3]
    wild.moves = [*kept_level_up, cover_move]


class StartIntroView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=180)
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    @discord.ui.button(label="Tiếp tục", style=discord.ButtonStyle.primary)
    async def continue_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        embed = discord.Embed(
            title="Chọn thế hệ starter",
            description=(
                "Bước 1: Chọn gen (1-9).\n"
                "Bước 2: Chọn 1 trong 3 starter của gen đó.\n\n"
                "Sau khi chọn, bạn sẽ nhận:\n"
                "- 25 Poké Ball\n"
                "- 1000 PokéDollars"
            ),
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(embed=embed, view=GenSelectView(self.author_id))


class GenChoiceSelect(discord.ui.Select):
    def __init__(self, author_id: int):
        options = [
            discord.SelectOption(
                label=f"Gen {gen}",
                value=str(gen),
                description=f"Starter: {', '.join(starters)}",
            )
            for gen, starters in GEN_STARTERS.items()
        ]
        super().__init__(placeholder="Chọn Gen starter", min_values=1, max_values=1, options=options)
        self.author_id = author_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không thể thao tác lựa chọn của người khác.", ephemeral=True)
            return

        selected_gen = int(self.values[0])
        starters = GEN_STARTERS[selected_gen]
        embed = discord.Embed(
            title=f"Chọn starter - Gen {selected_gen}",
            description=(
                f"Hãy chọn 1 trong 3 starter: **{starters[0]} / {starters[1]} / {starters[2]}**\n"
                "Bạn sẽ nhận 25 Poké Ball và 1000 PokéDollars sau khi chọn."
            ),
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(
            embed=embed,
            view=StarterSelectView(self.author_id, selected_gen),
        )


class GenSelectView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=180)
        self.author_id = author_id
        self.add_item(GenChoiceSelect(author_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id


class StarterSelectView(discord.ui.View):
    def __init__(self, author_id: int, gen: int):
        super().__init__(timeout=180)
        self.author_id = author_id
        self.gen = gen

        styles = [discord.ButtonStyle.success, discord.ButtonStyle.danger, discord.ButtonStyle.primary]
        for idx, starter in enumerate(GEN_STARTERS.get(gen, [])):
            btn = discord.ui.Button(label=starter, style=styles[idx % len(styles)])
            btn.callback = self._build_pick_callback(starter)
            self.add_item(btn)

        back_btn = discord.ui.Button(label="Đổi Gen", style=discord.ButtonStyle.secondary, row=1)
        back_btn.callback = self._go_back_gen
        self.add_item(back_btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    async def _go_back_gen(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Chọn thế hệ starter",
            description="Hãy chọn gen (1-9), sau đó chọn 1 trong 3 starter của gen đó.",
            color=discord.Color.green(),
        )
        await interaction.response.edit_message(embed=embed, view=GenSelectView(self.author_id))

    def _build_pick_callback(self, starter_name: str):
        async def callback(interaction: discord.Interaction):
            await self._pick(interaction, starter_name)

        return callback

    async def _pick(self, interaction: discord.Interaction, starter_name: str):
        profile = bot.get_player(interaction.user.id)
        if ensure_started(profile):
            await interaction.response.send_message("Bạn đã bắt đầu game rồi.", ephemeral=True)
            return

        species = bot.game_data.get_pokemon_by_name(starter_name)
        if species is None:
            await interaction.response.send_message("Không tìm thấy starter trong dữ liệu.", ephemeral=True)
            return

        await interaction.response.defer(thinking=False)

        starter = create_pokemon_instance(bot.game_data, species, level=5, owner_id=interaction.user.id)
        profile.started = True
        profile.money = 1000
        profile.inventory["Poké Ball"] = profile.inventory.get("Poké Ball", 0) + 25
        profile.party = [starter]
        profile.pc = []
        await asyncio.to_thread(bot.save_player, interaction.user.id)

        embed = discord.Embed(
            title="Bắt đầu hành trình thành công!",
            description=(
                f"Bạn đã chọn **{starter.name}** (Lv.{starter.level}).\n"
                f"Nhận thưởng: 25 Poké Ball và 1000 PokéDollars.\n\n"
                f"Dùng `/walk` để gặp Pokémon hoang dã."
            ),
            color=discord.Color.blurple(),
        )
        await interaction.edit_original_response(embed=embed, view=None)

class EncounterSelectView(discord.ui.View):
    def __init__(self, author_id: int, options: list[tuple[dict, int]]):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.options = options

        for idx, (species, level) in enumerate(options):
            btn = discord.ui.Button(
                label=f"{idx + 1}. {species['name']['english']} Lv.{level}",
                style=discord.ButtonStyle.secondary,
            )
            btn.callback = self._build_callback(idx)
            self.add_item(btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    def _build_callback(self, index: int):
        async def callback(interaction: discord.Interaction):
            profile = bot.get_player(interaction.user.id)
            if not ensure_started(profile):
                await interaction.response.send_message("Bạn cần dùng `/start` trước.", ephemeral=True)
                return

            species, wild_level = self.options[index]
            wild = create_pokemon_instance(bot.game_data, species, level=wild_level)
            battle = Battle(bot.game_data, profile, wild)
            bot.active_battles[interaction.user.id] = battle

            embed = battle_status_embed(profile, battle, title="Battle bắt đầu", turn_text=battle.consume_pending_battle_log())
            await interaction.response.edit_message(embed=embed, view=BattleView(interaction.user.id))

        return callback


class BattleView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=240)
        self.author_id = author_id

        battle = bot.active_battles.get(author_id)
        if battle is not None:
            active = battle.player_active
            all_depleted = all(mv.current_pp <= 0 for mv in active.moves[:4])
            for i, mv in enumerate(active.moves[:4]):
                label, style = _move_button_visual(battle, active, battle.wild, mv, i + 1)
                btn = discord.ui.Button(
                    label=label,
                    style=style,
                    row=i // 2,
                    disabled=mv.current_pp <= 0,
                )
                btn.callback = self._build_move_callback(i)
                self.add_item(btn)

            if all_depleted:
                struggle_btn = discord.ui.Button(
                    label="Struggle",
                    style=discord.ButtonStyle.danger,
                    row=2,
                )
                struggle_btn.callback = self._build_struggle_callback()
                self.add_item(struggle_btn)

        ball_button = discord.ui.Button(label="Ném Ball", style=discord.ButtonStyle.success, row=2)
        ball_button.callback = self.throw_ball
        self.add_item(ball_button)

        switch_button = discord.ui.Button(label="Pokemon", style=discord.ButtonStyle.secondary, row=2)
        switch_button.callback = self.switch_pokemon
        self.add_item(switch_button)

        item_button = discord.ui.Button(label="Item", style=discord.ButtonStyle.secondary, row=2)
        item_button.callback = self.use_item
        self.add_item(item_button)

        run_button = discord.ui.Button(label="Chạy", style=discord.ButtonStyle.danger, row=2)
        run_button.callback = self.run_away
        self.add_item(run_button)

        battle_info_button = discord.ui.Button(label="Battle Info", style=discord.ButtonStyle.secondary, row=3)
        battle_info_button.callback = self.show_battle_info
        self.add_item(battle_info_button)

    async def switch_pokemon(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return
        party = battle.player.party
        options = []
        for idx, pkmn in enumerate(party):
            if idx != battle.player_active_index and pkmn.current_hp > 0:
                options.append((idx, pkmn))
        if not options:
            await interaction.response.send_message("Không còn Pokémon nào có thể đổi ra sân.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Chọn Pokémon để đổi ra sân"),
            view=SwitchPokemonView(interaction.user.id, options),
        )

    # --- PATCH: move callbacks belong to BattleView ---
    def _build_move_callback(self, move_index: int):
        async def callback(interaction: discord.Interaction):
            battle = bot.active_battles.get(interaction.user.id)
            if not battle:
                await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
                return

            await interaction.response.defer()

            result = battle.run_turn(move_index)
            await asyncio.to_thread(bot.save_player, interaction.user.id)

            embed = battle_status_embed(battle.player, battle, title="Diễn biến lượt", turn_text=result.text)
            if result.battle_over:
                bot.active_battles.pop(interaction.user.id, None)
                await interaction.edit_original_response(embed=embed, view=None)
            else:
                await interaction.edit_original_response(embed=embed, view=BattleView(interaction.user.id))

        return callback

    def _build_struggle_callback(self):
        async def callback(interaction: discord.Interaction):
            battle = bot.active_battles.get(interaction.user.id)
            if not battle:
                await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
                return

            await interaction.response.defer()

            result = battle.run_turn(-1)
            await asyncio.to_thread(bot.save_player, interaction.user.id)

            embed = battle_status_embed(battle.player, battle, title="Diễn biến lượt", turn_text=result.text)
            if result.battle_over:
                bot.active_battles.pop(interaction.user.id, None)
                await interaction.edit_original_response(embed=embed, view=None)
            else:
                await interaction.edit_original_response(embed=embed, view=BattleView(interaction.user.id))

        return callback

    async def throw_ball(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return

        balls = get_available_pokeballs(battle.player)
        if not balls:
            await interaction.response.send_message("Bạn không có loại Poké Ball nào để ném.", ephemeral=True)
            return

        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Chọn Ball để ném"),
            view=BallSelectView(interaction.user.id, balls),
        )

    async def use_item(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return

        items = get_available_battle_items(battle.player)
        if not items:
            await interaction.response.send_message("Bạn không có item battle/hồi máu khả dụng.", ephemeral=True)
            return

        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Chọn Item để dùng"),
            view=ItemSelectView(interaction.user.id, items),
        )

    async def run_away(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return

        result = battle.run_away()
        bot.active_battles.pop(interaction.user.id, None)
        embed = battle_status_embed(battle.player, battle, title="Kết thúc trận", turn_text=result.text)
        await interaction.response.edit_message(embed=embed, view=None)

    async def show_battle_info(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return

        def _stage_multiplier(stage: int) -> float:
            stage = max(-6, min(6, stage))
            if stage >= 0:
                return (2 + stage) / 2
            return 2 / (2 - stage)

        def _format_stage_line(stage_map: dict[str, int], key: str, label: str) -> str:
            stage = stage_map.get(key, 0)
            mult = _stage_multiplier(stage)
            mult_text = f"x{mult:.2f}"
            return f"{label} {stage:+d} ({mult_text})"

        stage_order = ["attack", "defense", "sp_attack", "sp_defense", "speed"]
        stage_labels = {
            "attack": "ATK",
            "defense": "DEF",
            "sp_attack": "SPA",
            "sp_defense": "SPD",
            "speed": "SPE",
        }

        player_line = " | ".join(
            _format_stage_line(battle.player_stat_stages, key, stage_labels[key])
            for key in stage_order
        )
        wild_line = " | ".join(
            _format_stage_line(battle.wild_stat_stages, key, stage_labels[key])
            for key in stage_order
        )

        weather_turns = getattr(battle, "weather_turns", 0)
        if battle.weather:
            weather_text = f"{battle.weather} ({weather_turns} turn còn lại)" if weather_turns > 0 else battle.weather
        else:
            weather_text = "Không có"

        terrain_value = getattr(battle, "terrain", None)
        terrain_turns = getattr(battle, "terrain_turns", 0)
        if terrain_value:
            terrain_text = f"{terrain_value} ({terrain_turns} turn còn lại)" if terrain_turns > 0 else terrain_value
        else:
            terrain_text = "Không có"

        player_effects: list[str] = []
        if battle.player_reflect_turns > 0:
            player_effects.append(f"Reflect ({battle.player_reflect_turns} turn)")
        if battle.player_light_screen_turns > 0:
            player_effects.append(f"Light Screen ({battle.player_light_screen_turns} turn)")
        if battle.player_seeded:
            player_effects.append("Leech Seed")

        wild_effects: list[str] = []
        if battle.wild_reflect_turns > 0:
            wild_effects.append(f"Reflect ({battle.wild_reflect_turns} turn)")
        if battle.wild_light_screen_turns > 0:
            wild_effects.append(f"Light Screen ({battle.wild_light_screen_turns} turn)")
        if battle.wild_seeded:
            wild_effects.append("Leech Seed")

        player_hazards: list[str] = []
        if battle.player_spikes_layers > 0:
            player_hazards.append(f"Spikes x{battle.player_spikes_layers}")
        if battle.player_toxic_spikes_layers > 0:
            player_hazards.append(f"Toxic Spikes x{battle.player_toxic_spikes_layers}")
        if battle.player_stealth_rock:
            player_hazards.append("Stealth Rock")

        wild_hazards: list[str] = []
        if battle.wild_spikes_layers > 0:
            wild_hazards.append(f"Spikes x{battle.wild_spikes_layers}")
        if battle.wild_toxic_spikes_layers > 0:
            wild_hazards.append(f"Toxic Spikes x{battle.wild_toxic_spikes_layers}")
        if battle.wild_stealth_rock:
            wild_hazards.append("Stealth Rock")

        embed = discord.Embed(title="Battle Info", color=discord.Color.blurple())
        embed.add_field(name="Field", value=f"Weather: {weather_text}\nTerrain: {terrain_text}", inline=False)
        embed.add_field(name=f"Bạn - {battle.player_active.name}", value=player_line, inline=False)
        embed.add_field(
            name="Traps/Side (Bạn)",
            value=(
                f"Effects: {', '.join(player_effects) if player_effects else 'Không có'}\n"
                f"Hazards: {', '.join(player_hazards) if player_hazards else 'Không có'}"
            ),
            inline=False,
        )
        embed.add_field(name=f"Đối thủ - {battle.wild.name}", value=wild_line, inline=False)
        embed.add_field(
            name="Traps/Side (Đối thủ)",
            value=(
                f"Effects: {', '.join(wild_effects) if wild_effects else 'Không có'}\n"
                f"Hazards: {', '.join(wild_hazards) if wild_hazards else 'Không có'}"
            ),
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


def _gym_title_for_entry(run: dict, entry: dict) -> str:
    gym_type = run.get("gym_type", "Unknown")
    grade = int(run.get("grade", 1))
    role = str(entry.get("role", "trainer"))
    if role == "leader":
        return f"Gym {gym_type} - Grade {grade} | Gym Leader ({entry['slot']}/{entry['slot_total']})"
    return f"Gym {gym_type} - Grade {grade} | Trainer {entry['trainer_no']} ({entry['slot']}/{entry['slot_total']})"


def _queue_next_gym_battle(user_id: int, intro_text: str | None = None) -> tuple[discord.Embed, discord.ui.View] | None:
    profile = bot.get_player(user_id)
    run = profile.gym_run
    if not isinstance(run, dict):
        return None

    battles = run.get("battles", [])
    next_index = int(run.get("next_index", 0))
    if next_index < 0 or next_index >= len(battles):
        return None

    entry = battles[next_index]
    species = _find_species_by_id(int(entry["species_id"]))
    if species is None:
        return None

    wild = create_pokemon_instance(bot.game_data, species, level=int(entry["level"]))
    if str(entry.get("role", "trainer")) == "leader":
        _apply_leader_cover_tm_move(wild, species)
    battle = Battle(
        bot.game_data,
        profile,
        wild,
        exp_multiplier=float(entry.get("exp_multiplier", 1)),
        money_multiplier=0.0,
        allow_catch=False,
        allow_run=False,
        opponent_is_trainer=True,
        opponent_exp_coefficient=(3.0 if str(entry.get("role", "trainer")) == "leader" else 1.5),
    )
    bot.active_battles[user_id] = battle
    bot.gym_battle_meta[user_id] = {"battle_index": next_index}

    title = _gym_title_for_entry(run, entry)
    description = intro_text or f"Bạn bước vào trận tiếp theo trong Gym hệ {run.get('gym_type', '')}."
    embed = battle_status_embed(profile, battle, title=title, turn_text=description)
    return embed, GymBattleView(user_id)


def _grant_gym_clear_rewards(profile: PlayerProfile, run: dict) -> list[str]:
    gym_type = str(run.get("gym_type", "Normal"))
    grade = int(run.get("grade", 1))
    lines: list[str] = []

    money_gain = 2000 * max(1, grade)
    profile.money += money_gain
    lines.append(f"Bạn nhận {money_gain} PokéDollars từ Gym.")

    tm_name = _choose_tm_for_type(gym_type)
    if tm_name:
        profile.inventory[tm_name] = profile.inventory.get(tm_name, 0) + 1
        lines.append(f"Bạn nhận TM: {tm_name}.")

    if grade >= 4:
        hold_item = _choose_random_hold_item()
        if hold_item:
            profile.inventory[hold_item] = profile.inventory.get(hold_item, 0) + 1
            lines.append(f"Bạn nhận thêm hold item ngẫu nhiên: {hold_item}.")

    previous = int(profile.gym_badges.get(gym_type, 0))
    if grade > previous:
        profile.gym_badges[gym_type] = grade
        lines.append(f"Mở khóa tiến trình Gym hệ {gym_type}: Grade {grade}.")
    else:
        lines.append(f"Bạn đã từng hoàn thành Gym hệ {gym_type} ở Grade {previous}.")

    return lines


class GymProgressChoiceView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=600)
        self.author_id = author_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    @discord.ui.button(label="Tiếp tục", style=discord.ButtonStyle.success)
    async def continue_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        profile = bot.get_player(interaction.user.id)
        run = profile.gym_run
        if not isinstance(run, dict) or run.get("state") != "active":
            await interaction.response.send_message("Tiến trình gym không còn hợp lệ.", ephemeral=True)
            return
        run["awaiting_choice"] = False
        queued = _queue_next_gym_battle(interaction.user.id, intro_text="Bạn chọn tiếp tục hành trình gym.")
        await asyncio.to_thread(bot.save_player, interaction.user.id)
        if queued is None:
            await interaction.response.edit_message(content="Không thể tạo trận gym tiếp theo.", embed=None, view=None)
            return
        embed, view = queued
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="Tạm thời rút lui", style=discord.ButtonStyle.secondary)
    async def withdraw_button(self, interaction: discord.Interaction, _: discord.ui.Button):
        profile = bot.get_player(interaction.user.id)
        run = profile.gym_run
        if not isinstance(run, dict) or run.get("state") != "active":
            await interaction.response.send_message("Tiến trình gym không còn hợp lệ.", ephemeral=True)
            return

        run["state"] = "paused"
        run["awaiting_choice"] = False
        run["paused_until"] = _now_ts() + GYM_WITHDRAW_TIMEOUT_SECONDS
        await asyncio.to_thread(bot.save_player, interaction.user.id)
        await interaction.response.edit_message(
            embed=discord.Embed(
                title="Đã tạm rút lui khỏi Gym",
                description="Tiến trình của bạn được giữ trong 1 giờ. Dùng `/gym` để quay lại trước khi hết hạn.",
                color=discord.Color.yellow(),
            ),
            view=None,
        )


async def _handle_gym_turn_result(interaction: discord.Interaction, result: Any) -> None:
    async def _edit(**kwargs):
        if interaction.response.is_done():
            await interaction.edit_original_response(**kwargs)
        else:
            await interaction.response.edit_message(**kwargs)

    user_id = interaction.user.id
    battle = bot.active_battles.get(user_id)
    profile = bot.get_player(user_id)
    run = profile.gym_run if isinstance(profile.gym_run, dict) else None
    meta = bot.gym_battle_meta.get(user_id)

    if battle is None or run is None or meta is None:
        await _edit(
            embed=discord.Embed(title="Gym", description="Không tìm thấy trạng thái gym hiện tại.", color=discord.Color.red()),
            view=None,
        )
        return

    if not result.battle_over:
        embed = battle_status_embed(profile, battle, title="Gym Battle", turn_text=result.text)
        await _edit(embed=embed, view=GymBattleView(user_id))
        return

    bot.active_battles.pop(user_id, None)
    bot.gym_battle_meta.pop(user_id, None)

    all_fainted = all(p.current_hp <= 0 for p in profile.party)
    if all_fainted:
        profile.gym_run = None
        await asyncio.to_thread(bot.save_player, user_id)
        await _edit(
            embed=discord.Embed(
                title="Thất bại trong Gym",
                description=f"{result.text}\n\nTiến trình gym đã reset vì bạn thua trận.",
                color=discord.Color.red(),
            ),
            view=None,
        )
        return

    cleared_index = int(meta.get("battle_index", int(run.get("next_index", 0))))
    run["next_index"] = cleared_index + 1
    battles = run.get("battles", [])

    if int(run["next_index"]) >= len(battles):
        reward_lines = _grant_gym_clear_rewards(profile, run)
        profile.gym_run = None
        await asyncio.to_thread(bot.save_player, user_id)
        await _edit(
            embed=discord.Embed(
                title="Hoàn thành Gym thành công",
                description=result.text + "\n\n" + "\n".join(reward_lines),
                color=discord.Color.green(),
            ),
            view=None,
        )
        return

    current_entry = battles[cleared_index]
    next_entry = battles[int(run["next_index"])]
    trainer_boundary = (
        str(current_entry.get("role")) == "trainer"
        and (
            str(next_entry.get("role")) != "trainer"
            or int(next_entry.get("trainer_no", 0)) != int(current_entry.get("trainer_no", 0))
        )
    )

    if trainer_boundary:
        run["awaiting_choice"] = True
        await asyncio.to_thread(bot.save_player, user_id)
        await _edit(
            embed=discord.Embed(
                title="Đã thắng Trainer trong Gym",
                description=result.text + "\n\nChọn **Tiếp tục** hoặc **Tạm thời rút lui**.",
                color=discord.Color.blurple(),
            ),
            view=GymProgressChoiceView(user_id),
        )
        return

    run["awaiting_choice"] = False
    queued = _queue_next_gym_battle(user_id, intro_text=result.text + "\n\nTiếp tục trận kế tiếp trong cùng lượt gym.")
    await asyncio.to_thread(bot.save_player, user_id)
    if queued is None:
        await _edit(
            embed=discord.Embed(title="Gym", description="Không thể tạo trận tiếp theo.", color=discord.Color.red()),
            view=None,
        )
        return
    embed, view = queued
    await _edit(embed=embed, view=view)


class GymBattleView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=240)
        self.author_id = author_id

        battle = bot.active_battles.get(author_id)
        if battle is not None:
            active = battle.player_active
            all_depleted = all(mv.current_pp <= 0 for mv in active.moves[:4])
            for i, mv in enumerate(active.moves[:4]):
                label, style = _move_button_visual(battle, active, battle.wild, mv, i + 1)
                btn = discord.ui.Button(
                    label=label,
                    style=style,
                    row=i // 2,
                    disabled=mv.current_pp <= 0,
                )
                btn.callback = self._build_move_callback(i)
                self.add_item(btn)

            if all_depleted:
                struggle_btn = discord.ui.Button(label="Struggle", style=discord.ButtonStyle.danger, row=2)
                struggle_btn.callback = self._build_struggle_callback()
                self.add_item(struggle_btn)

        switch_button = discord.ui.Button(label="Pokemon", style=discord.ButtonStyle.secondary, row=2)
        switch_button.callback = self.switch_pokemon
        self.add_item(switch_button)

        is_leader_battle = _is_current_gym_leader_battle(author_id)
        item_button = discord.ui.Button(
            label="Item" if not is_leader_battle else "Item (Leader: cấm)",
            style=discord.ButtonStyle.secondary,
            row=2,
            disabled=is_leader_battle,
        )
        item_button.callback = self.use_item
        self.add_item(item_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    def _build_move_callback(self, move_index: int):
        async def callback(interaction: discord.Interaction):
            battle = bot.active_battles.get(interaction.user.id)
            if not battle:
                await interaction.response.send_message("Không có trận gym đang diễn ra.", ephemeral=True)
                return
            await interaction.response.defer()
            result = battle.run_turn(move_index)
            await _handle_gym_turn_result(interaction, result)
        return callback

    def _build_struggle_callback(self):
        async def callback(interaction: discord.Interaction):
            battle = bot.active_battles.get(interaction.user.id)
            if not battle:
                await interaction.response.send_message("Không có trận gym đang diễn ra.", ephemeral=True)
                return
            await interaction.response.defer()
            result = battle.run_turn(-1)
            await _handle_gym_turn_result(interaction, result)
        return callback

    async def switch_pokemon(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận gym đang diễn ra.", ephemeral=True)
            return
        options = [(idx, pkmn) for idx, pkmn in enumerate(battle.player.party) if idx != battle.player_active_index and pkmn.current_hp > 0]
        if not options:
            await interaction.response.send_message("Không còn Pokémon nào có thể đổi ra sân.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Gym - Chọn Pokémon để đổi"),
            view=GymSwitchPokemonView(interaction.user.id, options),
        )

    async def use_item(self, interaction: discord.Interaction):
        if _is_current_gym_leader_battle(interaction.user.id):
            await interaction.response.send_message("Không thể dùng item khi đang đánh Gym Leader.", ephemeral=True)
            return
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận gym đang diễn ra.", ephemeral=True)
            return
        items = get_available_battle_items(battle.player)
        if not items:
            await interaction.response.send_message("Bạn không có item battle/hồi máu khả dụng.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Gym - Chọn Item"),
            view=GymItemSelectView(interaction.user.id, items),
        )


class GymSwitchPokemonView(discord.ui.View):
    def __init__(self, author_id: int, options: list):
        super().__init__(timeout=60)
        self.author_id = author_id
        for idx, pkmn in options:
            btn = discord.ui.Button(label=f"{pkmn.name} Lv.{pkmn.level} ({pkmn.current_hp}/{pkmn.max_hp} HP)", style=discord.ButtonStyle.primary)
            btn.callback = self._build_callback(idx)
            self.add_item(btn)
        cancel_btn = discord.ui.Button(label="Hủy", style=discord.ButtonStyle.secondary)
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    def _build_callback(self, idx: int):
        async def callback(interaction: discord.Interaction):
            battle = bot.active_battles.get(interaction.user.id)
            if not battle:
                await interaction.response.send_message("Không có trận gym đang diễn ra.", ephemeral=True)
                return
            result = battle.run_switch_turn(idx)
            await _handle_gym_turn_result(interaction, result)
        return callback

    async def cancel(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận gym đang diễn ra.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Gym Battle tiếp tục"),
            view=GymBattleView(interaction.user.id),
        )


class GymItemChoiceSelect(discord.ui.Select):
    def __init__(self, author_id: int, items: list[tuple[str, int]]):
        options = [discord.SelectOption(label=item_name, description=f"Số lượng: {amount}", value=item_name) for item_name, amount in items[:25]]
        super().__init__(placeholder="Chọn Item", min_values=1, max_values=1, options=options)
        self.author_id = author_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không thể thao tác battle của người khác.", ephemeral=True)
            return
        if _is_current_gym_leader_battle(interaction.user.id):
            await interaction.response.send_message("Không thể dùng item khi đang đánh Gym Leader.", ephemeral=True)
            return
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận gym đang diễn ra.", ephemeral=True)
            return
        chosen_item = self.values[0]
        if chosen_item in REVIVE_TARGET_ITEMS:
            fainted_options = [
                (idx, pkmn)
                for idx, pkmn in enumerate(battle.player.party)
                if pkmn.current_hp <= 0
            ]
            if not fainted_options:
                await interaction.response.send_message("Không có Pokémon nào đã gục để hồi sinh.", ephemeral=True)
                return
            items = get_available_battle_items(battle.player)
            await interaction.response.edit_message(
                embed=battle_status_embed(battle.player, battle, title=f"Gym - Chọn Pokémon để dùng {chosen_item}"),
                view=GymReviveTargetSelectView(interaction.user.id, chosen_item, fainted_options, items),
            )
            return
        if chosen_item in PP_MOVE_TARGET_ITEMS:
            move_options = [
                (idx, move)
                for idx, move in enumerate(battle.player_active.moves)
                if move.current_pp < move.max_pp
            ]
            if not move_options:
                await interaction.response.send_message("Không có chiêu nào cần hồi PP.", ephemeral=True)
                return
            items = get_available_battle_items(battle.player)
            await interaction.response.edit_message(
                embed=battle_status_embed(battle.player, battle, title=f"Gym - Chọn chiêu để dùng {chosen_item}"),
                view=GymPPMoveTargetSelectView(interaction.user.id, chosen_item, move_options, items),
            )
            return
        result = battle.run_item_turn(chosen_item)
        await _handle_gym_turn_result(interaction, result)


class GymItemSelectView(discord.ui.View):
    def __init__(self, author_id: int, items: list[tuple[str, int]]):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.add_item(GymItemChoiceSelect(author_id, items))
        cancel = discord.ui.Button(label="Hủy", style=discord.ButtonStyle.secondary)
        cancel.callback = self.cancel
        self.add_item(cancel)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    async def cancel(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận gym đang diễn ra.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Gym Battle tiếp tục"),
            view=GymBattleView(interaction.user.id),
        )


class GymReviveTargetChoiceSelect(discord.ui.Select):
    def __init__(self, author_id: int, item_name: str, options: list[tuple[int, Any]]):
        select_options = [
            discord.SelectOption(
                label=f"{pkmn.name} Lv.{pkmn.level}",
                description=f"Slot {idx + 1} - 0/{pkmn.max_hp} HP",
                value=str(idx),
            )
            for idx, pkmn in options[:25]
        ]
        super().__init__(placeholder=f"Chọn Pokémon để dùng {item_name}", min_values=1, max_values=1, options=select_options)
        self.author_id = author_id
        self.item_name = item_name

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không thể thao tác battle của người khác.", ephemeral=True)
            return
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận gym đang diễn ra.", ephemeral=True)
            return
        target_index = int(self.values[0])
        result = battle.run_item_turn(self.item_name, target_index=target_index)
        await _handle_gym_turn_result(interaction, result)


class GymReviveTargetSelectView(discord.ui.View):
    def __init__(self, author_id: int, item_name: str, options: list[tuple[int, Any]], items: list[tuple[str, int]]):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.items = items
        self.add_item(GymReviveTargetChoiceSelect(author_id, item_name, options))
        cancel = discord.ui.Button(label="Hủy", style=discord.ButtonStyle.secondary)
        cancel.callback = self.cancel
        self.add_item(cancel)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    async def cancel(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận gym đang diễn ra.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Gym - Chọn Item"),
            view=GymItemSelectView(interaction.user.id, self.items),
        )


class GymPPMoveTargetChoiceSelect(discord.ui.Select):
    def __init__(self, author_id: int, item_name: str, options: list[tuple[int, Any]]):
        select_options = [
            discord.SelectOption(
                label=f"{move.name}",
                description=f"PP {move.current_pp}/{move.max_pp}",
                value=str(idx),
            )
            for idx, move in options[:25]
        ]
        super().__init__(placeholder=f"Chọn chiêu để dùng {item_name}", min_values=1, max_values=1, options=select_options)
        self.author_id = author_id
        self.item_name = item_name

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không thể thao tác battle của người khác.", ephemeral=True)
            return
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận gym đang diễn ra.", ephemeral=True)
            return
        move_index = int(self.values[0])
        result = battle.run_item_turn(self.item_name, target_move_index=move_index)
        await _handle_gym_turn_result(interaction, result)


class GymPPMoveTargetSelectView(discord.ui.View):
    def __init__(self, author_id: int, item_name: str, options: list[tuple[int, Any]], items: list[tuple[str, int]]):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.items = items
        self.add_item(GymPPMoveTargetChoiceSelect(author_id, item_name, options))
        cancel = discord.ui.Button(label="Hủy", style=discord.ButtonStyle.secondary)
        cancel.callback = self.cancel
        self.add_item(cancel)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    async def cancel(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận gym đang diễn ra.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Gym - Chọn Item"),
            view=GymItemSelectView(interaction.user.id, self.items),
        )

class SwitchPokemonView(discord.ui.View):
    def __init__(self, author_id: int, options: list):
        super().__init__(timeout=60)
        self.author_id = author_id
        for idx, pkmn in options:
            btn = discord.ui.Button(label=f"{pkmn.name} Lv.{pkmn.level} ({pkmn.current_hp}/{pkmn.max_hp} HP)", style=discord.ButtonStyle.primary)
            btn.callback = self._build_callback(idx)
            self.add_item(btn)
        cancel_btn = discord.ui.Button(label="Hủy", style=discord.ButtonStyle.secondary)
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    def _build_callback(self, idx: int):
        async def callback(interaction: discord.Interaction):
            battle = bot.active_battles.get(interaction.user.id)
            if not battle:
                await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
                return

            result = battle.run_switch_turn(idx)
            await asyncio.to_thread(bot.save_player, interaction.user.id)
            embed = battle_status_embed(battle.player, battle, title="Đã đổi Pokémon", turn_text=result.text)
            if result.battle_over:
                bot.active_battles.pop(interaction.user.id, None)
                await interaction.response.edit_message(embed=embed, view=None)
            else:
                await interaction.response.edit_message(embed=embed, view=BattleView(interaction.user.id))
        return callback

    async def cancel(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Battle tiếp tục"),
            view=BattleView(interaction.user.id),
        )


class ItemChoiceSelect(discord.ui.Select):
    def __init__(self, author_id: int, items: list[tuple[str, int]]):
        options = [
            discord.SelectOption(label=item_name, description=f"Số lượng: {amount}", value=item_name)
            for item_name, amount in items[:25]
        ]
        super().__init__(placeholder="Chọn Item", min_values=1, max_values=1, options=options)
        self.author_id = author_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không thể thao tác battle của người khác.", ephemeral=True)
            return

        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return

        chosen_item = self.values[0]
        if chosen_item in REVIVE_TARGET_ITEMS:
            fainted_options = [
                (idx, pkmn)
                for idx, pkmn in enumerate(battle.player.party)
                if pkmn.current_hp <= 0
            ]
            if not fainted_options:
                await interaction.response.send_message("Không có Pokémon nào đã gục để hồi sinh.", ephemeral=True)
                return
            items = get_available_battle_items(battle.player)
            await interaction.response.edit_message(
                embed=battle_status_embed(battle.player, battle, title=f"Chọn Pokémon để dùng {chosen_item}"),
                view=ReviveTargetSelectView(interaction.user.id, chosen_item, fainted_options, items),
            )
            return
        if chosen_item in PP_MOVE_TARGET_ITEMS:
            move_options = [
                (idx, move)
                for idx, move in enumerate(battle.player_active.moves)
                if move.current_pp < move.max_pp
            ]
            if not move_options:
                await interaction.response.send_message("Không có chiêu nào cần hồi PP.", ephemeral=True)
                return
            items = get_available_battle_items(battle.player)
            await interaction.response.edit_message(
                embed=battle_status_embed(battle.player, battle, title=f"Chọn chiêu để dùng {chosen_item}"),
                view=PPMoveTargetSelectView(interaction.user.id, chosen_item, move_options, items),
            )
            return
        result = battle.run_item_turn(chosen_item)
        await asyncio.to_thread(bot.save_player, interaction.user.id)

        embed = battle_status_embed(
            battle.player,
            battle,
            title=f"Dùng {chosen_item}",
            turn_text=result.text,
        )
        if result.battle_over:
            bot.active_battles.pop(interaction.user.id, None)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.edit_message(embed=embed, view=BattleView(interaction.user.id))


class ItemSelectView(discord.ui.View):
    def __init__(self, author_id: int, items: list[tuple[str, int]]):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.add_item(ItemChoiceSelect(author_id, items))

        cancel = discord.ui.Button(label="Hủy", style=discord.ButtonStyle.secondary)
        cancel.callback = self.cancel
        self.add_item(cancel)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    async def cancel(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Battle tiếp tục"),
            view=BattleView(interaction.user.id),
        )


class ReviveTargetChoiceSelect(discord.ui.Select):
    def __init__(self, author_id: int, item_name: str, options: list[tuple[int, Any]]):
        select_options = [
            discord.SelectOption(
                label=f"{pkmn.name} Lv.{pkmn.level}",
                description=f"Slot {idx + 1} - 0/{pkmn.max_hp} HP",
                value=str(idx),
            )
            for idx, pkmn in options[:25]
        ]
        super().__init__(placeholder=f"Chọn Pokémon để dùng {item_name}", min_values=1, max_values=1, options=select_options)
        self.author_id = author_id
        self.item_name = item_name

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không thể thao tác battle của người khác.", ephemeral=True)
            return

        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return

        target_index = int(self.values[0])
        result = battle.run_item_turn(self.item_name, target_index=target_index)
        await asyncio.to_thread(bot.save_player, interaction.user.id)

        embed = battle_status_embed(
            battle.player,
            battle,
            title=f"Dùng {self.item_name}",
            turn_text=result.text,
        )
        if result.battle_over:
            bot.active_battles.pop(interaction.user.id, None)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.edit_message(embed=embed, view=BattleView(interaction.user.id))


class ReviveTargetSelectView(discord.ui.View):
    def __init__(self, author_id: int, item_name: str, options: list[tuple[int, Any]], items: list[tuple[str, int]]):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.items = items
        self.add_item(ReviveTargetChoiceSelect(author_id, item_name, options))
        cancel = discord.ui.Button(label="Hủy", style=discord.ButtonStyle.secondary)
        cancel.callback = self.cancel
        self.add_item(cancel)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    async def cancel(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Chọn Item để dùng"),
            view=ItemSelectView(interaction.user.id, self.items),
        )


class PPMoveTargetChoiceSelect(discord.ui.Select):
    def __init__(self, author_id: int, item_name: str, options: list[tuple[int, Any]]):
        select_options = [
            discord.SelectOption(
                label=f"{move.name}",
                description=f"PP {move.current_pp}/{move.max_pp}",
                value=str(idx),
            )
            for idx, move in options[:25]
        ]
        super().__init__(placeholder=f"Chọn chiêu để dùng {item_name}", min_values=1, max_values=1, options=select_options)
        self.author_id = author_id
        self.item_name = item_name

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không thể thao tác battle của người khác.", ephemeral=True)
            return

        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return

        move_index = int(self.values[0])
        result = battle.run_item_turn(self.item_name, target_move_index=move_index)
        await asyncio.to_thread(bot.save_player, interaction.user.id)

        embed = battle_status_embed(
            battle.player,
            battle,
            title=f"Dùng {self.item_name}",
            turn_text=result.text,
        )
        if result.battle_over:
            bot.active_battles.pop(interaction.user.id, None)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.edit_message(embed=embed, view=BattleView(interaction.user.id))


class PPMoveTargetSelectView(discord.ui.View):
    def __init__(self, author_id: int, item_name: str, options: list[tuple[int, Any]], items: list[tuple[str, int]]):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.items = items
        self.add_item(PPMoveTargetChoiceSelect(author_id, item_name, options))
        cancel = discord.ui.Button(label="Hủy", style=discord.ButtonStyle.secondary)
        cancel.callback = self.cancel
        self.add_item(cancel)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    async def cancel(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Chọn Item để dùng"),
            view=ItemSelectView(interaction.user.id, self.items),
        )



class BallChoiceSelect(discord.ui.Select):
    def __init__(self, author_id: int, balls: list[tuple[str, int]]):
        options = [
            discord.SelectOption(label=ball_name, description=f"Số lượng: {amount}", value=ball_name)
            for ball_name, amount in balls[:25]
        ]
        super().__init__(placeholder="Chọn loại Poké Ball", min_values=1, max_values=1, options=options)
        self.author_id = author_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không thể thao tác battle của người khác.", ephemeral=True)
            return

        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return

        chosen_ball = self.values[0]
        result = battle.throw_ball(chosen_ball)
        await asyncio.to_thread(bot.save_player, interaction.user.id)

        embed = battle_status_embed(
            battle.player,
            battle,
            title=f"Ném {chosen_ball}",
            turn_text=result.text,
        )
        if result.battle_over:
            bot.active_battles.pop(interaction.user.id, None)
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            await interaction.response.edit_message(embed=embed, view=BattleView(interaction.user.id))


class BallSelectView(discord.ui.View):
    def __init__(self, author_id: int, balls: list[tuple[str, int]]):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.add_item(BallChoiceSelect(author_id, balls))

        cancel = discord.ui.Button(label="Hủy", style=discord.ButtonStyle.secondary)
        cancel.callback = self.cancel
        self.add_item(cancel)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.author_id

    async def cancel(self, interaction: discord.Interaction):
        battle = bot.active_battles.get(interaction.user.id)
        if not battle:
            await interaction.response.send_message("Không có trận đấu đang diễn ra.", ephemeral=True)
            return
        await interaction.response.edit_message(
            embed=battle_status_embed(battle.player, battle, title="Battle tiếp tục"),
            view=BattleView(interaction.user.id),
        )


def battle_status_embed(profile: PlayerProfile, battle: Battle, title: str, turn_text: str | None = None) -> discord.Embed:
    active = battle.player_active
    wild = battle.wild

    embed = discord.Embed(title=title, color=discord.Color.orange())
    embed.add_field(
        name="Pokémon của bạn",
        value=(
            f"{active.name} Lv.{active.level}\n"
            f"HP: {active.current_hp}/{active.max_hp}\n"
            f"Speed: {active.speed}"
        ),
        inline=True,
    )
    embed.add_field(
        name="Pokémon hoang dã",
        value=(
            f"{wild.name} Lv.{wild.level}\n"
            f"HP: {wild.current_hp}/{wild.max_hp}\n"
            f"Speed: {wild.speed}"
        ),
        inline=True,
    )
    balls = get_available_pokeballs(profile)
    if balls:
        ball_text = "\n".join([f"- {name}: {amount}" for name, amount in balls])
    else:
        ball_text = "(không có)"
    embed.add_field(name="Poké Balls", value=ball_text[:1024], inline=False)

    if turn_text:
        def _chunk_log_text(text: str, limit: int = 1024) -> list[str]:
            chunks: list[str] = []
            current = ""
            for raw_line in text.splitlines() or [text]:
                line = raw_line or " "
                candidate = line if not current else f"{current}\n{line}"
                if len(candidate) <= limit:
                    current = candidate
                    continue

                if current:
                    chunks.append(current)
                    current = ""

                while len(line) > limit:
                    chunks.append(line[: limit - 1] + "...")
                    line = line[limit - 1 :]
                current = line

            if current:
                chunks.append(current)
            return chunks or ["(trống)"]

        for idx, chunk in enumerate(_chunk_log_text(turn_text)[:4]):
            field_name = "Log" if idx == 0 else f"Log ({idx + 1})"
            embed.add_field(name=field_name, value=chunk, inline=False)

    return embed


def build_inventory_embed(profile: PlayerProfile) -> discord.Embed:
    categories = {
        "Items": {"Hold items", "General items", "Battle items"},
        "Evolutionary Items": set(),
        "Pokeballs": {"Pokeballs"},
        "Berries": {"Berries"},
        "TMs": {"Machines"},
        "Key Items": {"Key Items"},
    }

    grouped: dict[str, list[tuple[str, int]]] = {k: [] for k in categories}

    evolutionary_items = get_evolutionary_item_names()

    for item_name, amount in profile.inventory.items():
        if amount <= 0:
            continue
        if item_name in evolutionary_items:
            grouped["Evolutionary Items"].append((item_name, amount))
            continue
        if item_name.lower() in MANUAL_KEY_ITEMS_LOWER:
            grouped["Key Items"].append((item_name, amount))
            continue
        item_data = bot.game_data.items_by_name.get(item_name)
        item_type = item_data.get("type") if item_data else "General items"

        placed = False
        for bucket, accepted_types in categories.items():
            if item_type in accepted_types:
                grouped[bucket].append((item_name, amount))
                placed = True
                break
        if not placed:
            grouped["Items"].append((item_name, amount))

    embed = discord.Embed(title="Inventory", color=discord.Color.blue())
    for bucket in ["Items", "Evolutionary Items", "Pokeballs", "Berries", "TMs", "Key Items"]:
        entries = grouped[bucket]
        if entries:
            lines = [f"- {name} x{amount}" for name, amount in sorted(entries)]
            value = "\n".join(lines)
        else:
            value = "(trống)"
        embed.add_field(name=bucket, value=value[:1024], inline=False)

    embed.set_footer(text=f"PokéDollars: {profile.money}")
    return embed


@bot.tree.command(name="start", description="Bắt đầu game Pokémon")
async def start_command(interaction: discord.Interaction):
    profile = bot.get_player(interaction.user.id)
    if ensure_started(profile):
        await interaction.response.send_message("Bạn đã bắt đầu rồi. Dùng `/walk` để chơi tiếp.", ephemeral=True)
        return

    intro = discord.Embed(
        title="Chào mừng đến Discord Pokémon Game",
        description=(
            "Bạn sẽ trở thành huấn luyện viên Pokémon.\n"
            "Ở trang kế tiếp, bạn sẽ chọn gen starter (1-9), rồi chọn Pokémon khởi đầu để nhận vật phẩm đầu game."
        ),
        color=discord.Color.gold(),
    )
    await interaction.response.defer(thinking=False)
    await interaction.edit_original_response(embed=intro, view=StartIntroView(interaction.user.id))


@bot.tree.command(name="walk", description="Đi bộ và gặp 5 Pokémon hoang dã")
async def walk_command(interaction: discord.Interaction):
    profile = bot.get_player(interaction.user.id)
    if not ensure_started(profile):
        await interaction.response.send_message("Bạn cần dùng `/start` trước.", ephemeral=True)
        return

    if interaction.user.id in bot.active_battles:
        await interaction.response.send_message("Bạn đang trong trận đấu. Hãy kết thúc trận hiện tại trước.", ephemeral=True)
        return

    if _cleanup_expired_gym_run(profile):
        await asyncio.to_thread(bot.save_player, interaction.user.id)
    if _is_gym_locked(profile):
        await interaction.response.send_message("Bạn đang tham gia gym. Hãy hoàn tất gym hoặc tạm thời rút lui bằng `/gym`.", ephemeral=True)
        return

    options = _choose_walk_encounters(profile, 5)
    lines = [
        f"{idx + 1}. {p['name']['english']} Lv.{lv} (Type: {', '.join(p.get('type', []))})"
        for idx, (p, lv) in enumerate(options)
    ]
    embed = discord.Embed(
        title="Bạn gặp 5 Pokémon hoang dã",
        description="\n".join(lines),
        color=discord.Color.teal(),
    )
    embed.set_footer(text="Chọn 1 Pokémon để bắt đầu chiến đấu")
    await interaction.response.send_message(embed=embed, view=EncounterSelectView(interaction.user.id, options))


@bot.tree.command(name="gym", description="Tham gia gym theo hệ và grade")
@app_commands.describe(gym_type="Hệ gym (18 hệ)", grade="Độ khó gym từ 1 đến 8")
@app_commands.choices(
    gym_type=[app_commands.Choice(name=t, value=t) for t in GYM_TYPES],
    grade=[app_commands.Choice(name=f"Grade {i}", value=i) for i in range(1, 9)],
)
async def gym_command(
    interaction: discord.Interaction,
    gym_type: Optional[app_commands.Choice[str]] = None,
    grade: Optional[app_commands.Choice[int]] = None,
):
    profile = bot.get_player(interaction.user.id)
    if not ensure_started(profile):
        await interaction.response.send_message("Bạn cần dùng `/start` trước.", ephemeral=True)
        return

    if _cleanup_expired_gym_run(profile):
        await asyncio.to_thread(bot.save_player, interaction.user.id)

    if interaction.user.id in bot.active_battles:
        if interaction.user.id in bot.gym_battle_meta:
            await interaction.response.send_message("Bạn đang ở trong trận gym hiện tại.", ephemeral=True)
        else:
            await interaction.response.send_message("Bạn đang trong trận đấu khác. Hãy kết thúc trước khi vào gym.", ephemeral=True)
        return

    run = profile.gym_run if isinstance(profile.gym_run, dict) else None
    requested_type = gym_type.value if gym_type else None
    requested_grade = int(grade.value) if grade else None

    if run and run.get("state") == "active" and requested_type is None and requested_grade is None:
        if run.get("awaiting_choice"):
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="Gym đang chờ lựa chọn",
                    description="Bạn vừa hoàn thành một trainer. Chọn tiếp tục hoặc tạm rút lui.",
                    color=discord.Color.blurple(),
                ),
                view=GymProgressChoiceView(interaction.user.id),
            )
            return
        queued = _queue_next_gym_battle(interaction.user.id, intro_text="Bạn quay lại gym và tiếp tục trận tiếp theo.")
        if queued is None:
            await interaction.response.send_message("Không thể khởi tạo trận gym tiếp theo.", ephemeral=True)
            return
        await asyncio.to_thread(bot.save_player, interaction.user.id)
        embed, view = queued
        await interaction.response.send_message(embed=embed, view=view)
        return

    if run and run.get("state") == "paused" and requested_type is None and requested_grade is None:
        run["state"] = "active"
        run["paused_until"] = 0
        queued = _queue_next_gym_battle(interaction.user.id, intro_text="Bạn đã quay lại gym trong thời hạn và tiếp tục tiến trình.")
        if queued is None:
            profile.gym_run = None
            await asyncio.to_thread(bot.save_player, interaction.user.id)
            await interaction.response.send_message("Không thể khôi phục trận gym. Tiến trình đã bị hủy.", ephemeral=True)
            return
        await asyncio.to_thread(bot.save_player, interaction.user.id)
        embed, view = queued
        await interaction.response.send_message(embed=embed, view=view)
        return

    if requested_type is None or requested_grade is None:
        await interaction.response.send_message("Hãy chọn đủ `gym_type` và `grade` để bắt đầu gym mới, hoặc dùng `/gym` để tiếp tục tiến trình đang lưu.", ephemeral=True)
        return

    plan = _build_gym_battle_plan(requested_type, requested_grade)
    profile.gym_run = {
        "gym_type": requested_type,
        "grade": requested_grade,
        "state": "active",
        "paused_until": 0,
        "awaiting_choice": False,
        "next_index": 0,
        "battles": plan,
    }
    queued = _queue_next_gym_battle(interaction.user.id, intro_text=f"Bắt đầu Gym hệ {requested_type} - Grade {requested_grade}.")
    if queued is None:
        profile.gym_run = None
        await interaction.response.send_message("Không thể tạo gym với cấu hình này.", ephemeral=True)
        return
    await asyncio.to_thread(bot.save_player, interaction.user.id)
    embed, view = queued
    await interaction.response.send_message(embed=embed, view=view)


@bot.tree.command(name="inventory", description="Mở túi đồ")
async def inventory_command(interaction: discord.Interaction):
    profile = bot.get_player(interaction.user.id)
    if not ensure_started(profile):
        await interaction.response.send_message("Bạn cần dùng `/start` trước.", ephemeral=True)
        return
    await interaction.response.send_message(embed=build_inventory_embed(profile), ephemeral=True)


@bot.tree.command(name="shop", description="Mở shop mua item")
async def shop_command(interaction: discord.Interaction):
    profile = bot.get_player(interaction.user.id)
    if not ensure_started(profile):
        await interaction.response.send_message("Bạn cần dùng `/start` trước.", ephemeral=True)
        return

    embed = _build_shop_embed(profile, SHOP_PAGE_POKEBALL)
    await interaction.response.send_message(
        content="Số lượng hiện tại: x1",
        embed=embed,
        view=ShopView(interaction.user.id, SHOP_PAGE_POKEBALL, quantity=1),
        ephemeral=True,
    )


@bot.tree.command(name="inv", description="Mở túi đồ (alias)")
async def inv_command(interaction: discord.Interaction):
    await inventory_command(interaction)


@bot.tree.command(name="center", description="Hồi đầy HP toàn bộ Pokémon trong party")
async def center_command(interaction: discord.Interaction):
    DAILY_CENTER_LIMIT = 50
    profile = bot.get_player(interaction.user.id)
    if not ensure_started(profile):
        await interaction.response.send_message("Bạn cần dùng `/start` trước.", ephemeral=True)
        return

    if not profile.party:
        await interaction.response.send_message("Party của bạn đang trống.", ephemeral=True)
        return

    if _cleanup_expired_gym_run(profile):
        await asyncio.to_thread(bot.save_player, interaction.user.id)
    if _is_gym_locked(profile):
        await interaction.response.send_message("Bạn đang tham gia gym, không thể dùng Center lúc này. Hãy tạm rút lui bằng `/gym`.", ephemeral=True)
        return

    now = time.localtime()
    today_key = f"{now.tm_year:04d}-{now.tm_mon:02d}-{now.tm_mday:02d}"
    if profile.center_uses_date != today_key:
        profile.center_uses_date = today_key
        profile.center_uses_count = 0

    if profile.center_uses_count >= DAILY_CENTER_LIMIT:
        await interaction.response.send_message('Bạn đã hết "lượt dùng pokemon center" trong hôm nay.', ephemeral=True)
        return

    healed_count = 0
    for pokemon in profile.party:
        if pokemon.current_hp < pokemon.max_hp:
            healed_count += 1
        pokemon.current_hp = pokemon.max_hp

    profile.center_uses_count += 1
    remaining = max(0, DAILY_CENTER_LIMIT - profile.center_uses_count)

    await asyncio.to_thread(bot.save_player, interaction.user.id)

    if healed_count == 0:
        await interaction.response.send_message(
            f"Tất cả Pokémon trong party đã đầy HP sẵn rồi. Còn lại {remaining}/{DAILY_CENTER_LIMIT} lượt hôm nay.",
            ephemeral=True,
        )
        return

    await interaction.response.send_message(
        f"Đã hồi máu tại Pokémon Center cho {healed_count}/{len(profile.party)} Pokémon trong party. Còn lại {remaining}/{DAILY_CENTER_LIMIT} lượt hôm nay.",
        ephemeral=True,
    )


@bot.tree.command(name="c", description="Hồi máu party (alias của /center)")
async def center_alias_command(interaction: discord.Interaction):
    await center_command(interaction)


def _build_pinfo_embed(profile: PlayerProfile, selected_slot: int) -> tuple[discord.Embed, bool, str]:
    index = selected_slot - 1
    pkmn = profile.party[index]
    can_evolve_choices, lock_reason = _collect_evolution_choices(profile, pkmn, context="manual")
    can_evolve_now = bool(can_evolve_choices)

    stats_lines = [
        f"HP: {pkmn.current_hp}/{pkmn.max_hp}",
        f"ATK: {pkmn.attack}",
        f"DEF: {pkmn.defense}",
        f"SP.ATK: {pkmn.sp_attack}",
        f"SP.DEF: {pkmn.sp_defense}",
        f"SPEED: {pkmn.speed}",
    ]

    iv_lines = [
        f"HP {pkmn.ivs.get('HP', 0)} | ATK {pkmn.ivs.get('Attack', 0)} | DEF {pkmn.ivs.get('Defense', 0)}",
        f"SPA {pkmn.ivs.get('Sp. Attack', 0)} | SPD {pkmn.ivs.get('Sp. Defense', 0)} | SPE {pkmn.ivs.get('Speed', 0)}",
    ]
    ev_lines = [
        f"HP {pkmn.evs.get('HP', 0)} | ATK {pkmn.evs.get('Attack', 0)} | DEF {pkmn.evs.get('Defense', 0)}",
        f"SPA {pkmn.evs.get('Sp. Attack', 0)} | SPD {pkmn.evs.get('Sp. Defense', 0)} | SPE {pkmn.evs.get('Speed', 0)}",
    ]

    move_lines = [f"- {mv.name} ({mv.move_type}/{mv.category}, Pow {mv.power}, Acc {mv.accuracy}%)" for mv in pkmn.moves]
    if not move_lines:
        move_lines = ["(không có move)"]

    evolve_state = "✅ Có thể tiến hóa ngay" if can_evolve_now else f"🔒 {lock_reason or 'Chưa đủ điều kiện'}"

    embed = discord.Embed(
        title=f"Pokémon Info - Slot {selected_slot}",
        description=f"**{pkmn.name}** | Lv.{pkmn.level}",
        color=discord.Color.purple(),
    )
    embed.add_field(name="Type", value=", ".join(pkmn.types), inline=True)
    embed.add_field(name="Nature", value=pkmn.nature, inline=True)
    embed.add_field(name="Ability", value=pkmn.ability or "(chưa có)", inline=True)
    embed.add_field(name="Hold Item", value=pkmn.hold_item or "(không có)", inline=True)
    embed.add_field(name="Status", value=pkmn.status or "(không có)", inline=True)
    embed.add_field(name="Happiness", value=str(int(getattr(pkmn, "happiness", 70))), inline=True)

    embed.add_field(name="Stats", value="\n".join(stats_lines), inline=False)
    embed.add_field(name="IV", value="\n".join(iv_lines), inline=False)
    embed.add_field(name="EV", value="\n".join(ev_lines), inline=False)

    embed.add_field(name="EXP hiện có", value=str(pkmn.exp), inline=True)
    embed.add_field(name="EXP cần để tăng cấp", value=str(pkmn.exp_to_next_level()), inline=True)
    embed.add_field(name="Tiến hóa", value=evolve_state, inline=True)

    embed.add_field(name="Moves", value="\n".join(move_lines)[:1024], inline=False)

    if pkmn.image_url:
        embed.set_thumbnail(url=pkmn.image_url)

    return embed, can_evolve_now, (lock_reason or "Chưa đủ điều kiện tiến hóa")


class PinfoEvolutionView(discord.ui.View):
    def __init__(self, author_id: int, slot_index: int, can_evolve: bool):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.slot_index = slot_index

        evolve_btn = discord.ui.Button(
            label="Tiến hóa",
            style=discord.ButtonStyle.success if can_evolve else discord.ButtonStyle.secondary,
            disabled=not can_evolve,
        )
        evolve_btn.callback = self.evolve
        self.add_item(evolve_btn)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("Bạn không thể thao tác Pokémon của người khác.", ephemeral=True)
            return False
        return True

    async def evolve(self, interaction: discord.Interaction):
        profile = bot.get_player(interaction.user.id)
        if not ensure_started(profile):
            await interaction.response.send_message("Bạn cần dùng `/start` trước.", ephemeral=True)
            return
        if self.slot_index < 0 or self.slot_index >= len(profile.party):
            await interaction.response.send_message("Slot Pokémon không còn hợp lệ.", ephemeral=True)
            return

        pkmn = profile.party[self.slot_index]
        changed, message = _try_evolve_pokemon(profile, pkmn, context="manual")
        if not changed:
            await interaction.response.send_message(message, ephemeral=True)
            return

        await asyncio.to_thread(bot.save_player, interaction.user.id)
        embed, can_evolve_now, _ = _build_pinfo_embed(profile, self.slot_index + 1)
        await interaction.response.edit_message(
            content=message,
            embed=embed,
            view=PinfoEvolutionView(self.author_id, self.slot_index, can_evolve_now),
        )


@bot.tree.command(name="pinfo", description="Xem chi tiết Pokémon trong party")
@app_commands.describe(slot="Vị trí Pokémon trong party (1-6), mặc định là 1")
async def pinfo_command(interaction: discord.Interaction, slot: Optional[int] = 1):
    profile = bot.get_player(interaction.user.id)
    if not ensure_started(profile):
        await interaction.response.send_message("Bạn cần dùng `/start` trước.", ephemeral=True)
        return

    if not profile.party:
        await interaction.response.send_message("Party của bạn đang trống.", ephemeral=True)
        return

    selected_slot = 1 if slot is None else slot
    index = selected_slot - 1
    if index < 0 or index >= len(profile.party):
        await interaction.response.send_message("Slot không hợp lệ. Hãy chọn từ 1 đến số Pokémon hiện có trong party.", ephemeral=True)
        return

    embed, can_evolve_now, _ = _build_pinfo_embed(profile, selected_slot)
    view = PinfoEvolutionView(interaction.user.id, index, can_evolve_now)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


def _try_trade_evolution(profile: PlayerProfile, pokemon: PokemonInstance) -> str | None:
    changed, message = _try_evolve_pokemon(profile, pokemon, context="trade")
    if changed:
        return message
    return None


class TradeConfirmView(discord.ui.View):
    def __init__(self, user_a: int, user_b: int, slot_a: int, slot_b: int):
        super().__init__(timeout=180)
        self.user_a = user_a
        self.user_b = user_b
        self.slot_a = slot_a
        self.slot_b = slot_b
        self.accepted: set[int] = set()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in {self.user_a, self.user_b}:
            await interaction.response.send_message("Bạn không nằm trong giao dịch này.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Đồng ý giao dịch", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, _button: discord.ui.Button):
        self.accepted.add(interaction.user.id)
        if self.accepted != {self.user_a, self.user_b}:
            await interaction.response.send_message("Đã ghi nhận xác nhận. Chờ người còn lại đồng ý.", ephemeral=True)
            return

        profile_a = bot.get_player(self.user_a)
        profile_b = bot.get_player(self.user_b)
        if not ensure_started(profile_a) or not ensure_started(profile_b):
            await interaction.response.edit_message(content="Một trong hai người chơi chưa sẵn sàng để trade.", view=None)
            return
        if self.slot_a < 0 or self.slot_a >= len(profile_a.party) or self.slot_b < 0 or self.slot_b >= len(profile_b.party):
            await interaction.response.edit_message(content="Slot trade không còn hợp lệ (party đã thay đổi).", view=None)
            return

        poke_a = profile_a.party[self.slot_a]
        poke_b = profile_b.party[self.slot_b]
        profile_a.party[self.slot_a], profile_b.party[self.slot_b] = poke_b, poke_a

        logs: list[str] = [
            f"Đã trade thành công: {poke_a.name} ↔ {poke_b.name}.",
        ]

        evo_b = _try_trade_evolution(profile_a, profile_a.party[self.slot_a])
        evo_a = _try_trade_evolution(profile_b, profile_b.party[self.slot_b])
        if evo_b:
            logs.append(f"[Người nhận 1] {evo_b}")
        if evo_a:
            logs.append(f"[Người nhận 2] {evo_a}")

        await asyncio.to_thread(bot.save_player, self.user_a)
        await asyncio.to_thread(bot.save_player, self.user_b)
        await interaction.response.edit_message(content="\n".join(logs), view=None)

    @discord.ui.button(label="Hủy", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, _button: discord.ui.Button):
        await interaction.response.edit_message(content="Giao dịch đã bị hủy.", view=None)


@bot.tree.command(name="trade", description="Trao đổi Pokémon giữa 2 người chơi")
@app_commands.describe(
    target="Người chơi muốn trade",
    your_slot="Slot Pokémon của bạn trong party (1-6)",
    target_slot="Slot Pokémon của người kia trong party (1-6)",
)
async def trade_command(interaction: discord.Interaction, target: discord.Member, your_slot: int, target_slot: int):
    if target.bot:
        await interaction.response.send_message("Không thể trade với bot.", ephemeral=True)
        return
    if target.id == interaction.user.id:
        await interaction.response.send_message("Bạn không thể trade với chính mình.", ephemeral=True)
        return

    profile_you = bot.get_player(interaction.user.id)
    profile_target = bot.get_player(target.id)
    if not ensure_started(profile_you):
        await interaction.response.send_message("Bạn cần dùng `/start` trước.", ephemeral=True)
        return
    if not ensure_started(profile_target):
        await interaction.response.send_message("Người chơi kia chưa bắt đầu game.", ephemeral=True)
        return

    your_index = your_slot - 1
    target_index = target_slot - 1
    if your_index < 0 or your_index >= len(profile_you.party):
        await interaction.response.send_message("`your_slot` không hợp lệ.", ephemeral=True)
        return
    if target_index < 0 or target_index >= len(profile_target.party):
        await interaction.response.send_message("`target_slot` không hợp lệ.", ephemeral=True)
        return

    your_pokemon = profile_you.party[your_index]
    target_pokemon = profile_target.party[target_index]
    content = (
        f"Yêu cầu trade từ {interaction.user.mention} tới {target.mention}\n"
        f"- {interaction.user.display_name} đưa: {your_pokemon.name} (slot {your_slot})\n"
        f"- {target.display_name} đưa: {target_pokemon.name} (slot {target_slot})\n"
        "Cả hai bấm **Đồng ý giao dịch** để hoàn tất."
    )
    await interaction.response.send_message(
        content,
        view=TradeConfirmView(interaction.user.id, target.id, your_index, target_index),
    )


@bot.tree.command(name="pc", description="Mở PC-1 để gửi/lấy Pokémon")
@app_commands.describe(action="view/send/take", party_slot="Vị trí trong party (1-6)", pc_slot="Vị trí trong PC (1-n)")
@app_commands.choices(
    action=[
        app_commands.Choice(name="view", value="view"),
        app_commands.Choice(name="send", value="send"),
        app_commands.Choice(name="take", value="take"),
    ]
)
async def pc_command(
    interaction: discord.Interaction,
    action: app_commands.Choice[str],
    party_slot: Optional[int] = None,
    pc_slot: Optional[int] = None,
):
    profile = bot.get_player(interaction.user.id)
    if not ensure_started(profile):
        await interaction.response.send_message("Bạn cần dùng `/start` trước.", ephemeral=True)
        return

    if _cleanup_expired_gym_run(profile):
        await asyncio.to_thread(bot.save_player, interaction.user.id)
    if _is_gym_locked(profile):
        await interaction.response.send_message("Bạn đang tham gia gym, không thể thao tác PC lúc này. Hãy tạm rút lui bằng `/gym`.", ephemeral=True)
        return

    mode = action.value

    if mode == "view":
        embed = discord.Embed(title="PC-1", color=discord.Color.dark_blue())
        embed.set_footer(text=f"Party: {len(profile.party)} | PC: {len(profile.pc)}")

        roster_file = build_pc_roster_image(profile)
        if roster_file is not None:
            embed.set_image(url=f"attachment://{roster_file.filename}")
            await interaction.response.send_message(embed=embed, file=roster_file, ephemeral=True)
            return

        embed.description = "Không thể render ảnh roster."
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if mode == "send":
        if party_slot is None:
            await interaction.response.send_message("Bạn cần nhập `party_slot` để gửi Pokémon.", ephemeral=True)
            return
        index = party_slot - 1
        if index < 0 or index >= len(profile.party):
            await interaction.response.send_message("`party_slot` không hợp lệ.", ephemeral=True)
            return
        if len(profile.party) <= 1:
            await interaction.response.send_message("Party phải còn ít nhất 1 Pokémon.", ephemeral=True)
            return

        moved = profile.party.pop(index)
        profile.pc.append(moved)
        await asyncio.to_thread(bot.save_player, interaction.user.id)
        await interaction.response.send_message(f"Đã gửi {moved.name} từ party vào PC.", ephemeral=True)
        return

    if mode == "take":
        if pc_slot is None:
            await interaction.response.send_message("Bạn cần nhập `pc_slot` để lấy Pokémon.", ephemeral=True)
            return
        if len(profile.party) >= 6:
            await interaction.response.send_message("Party đã đủ 6 Pokémon.", ephemeral=True)
            return

        index = pc_slot - 1
        if index < 0 or index >= len(profile.pc):
            await interaction.response.send_message("`pc_slot` không hợp lệ.", ephemeral=True)
            return

        moved = profile.pc.pop(index)
        profile.party.append(moved)
        await asyncio.to_thread(bot.save_player, interaction.user.id)
        await interaction.response.send_message(f"Đã lấy {moved.name} từ PC ra party.", ephemeral=True)
        return


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    profile = bot.get_player(message.author.id)
    if ensure_started(profile) and profile.party:
        now_ts = int(time.time())
        last_ts = int(getattr(profile, "last_chat_happiness_at", 0) or 0)
        if now_ts - last_ts >= 60:
            lead = profile.party[0]
            gained = add_happiness(lead, 1)
            if gained > 0:
                profile.last_chat_happiness_at = now_ts
                await asyncio.to_thread(bot.save_player, message.author.id)

    await bot.process_commands(message)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} ({bot.user.id})")


def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Thiếu DISCORD_TOKEN trong file .env")

    start_keep_alive()
    bot.run(token)


if __name__ == "__main__":
    main()
