# --- MOVE PRIORITY EFFECTS ---
def calculate_move_priority(pokemon, move, field):
    """
    Tính toán độ ưu tiên của move, có thể bị ảnh hưởng bởi các ability
    """
    priority = getattr(move, 'priority', 0)
    # Prankster: tăng priority cho status move
    if pokemon.has_ability('Prankster') and getattr(move, 'is_status', False):
        priority += 1
    # Gale Wings: tăng priority cho Flying-type move khi HP đầy
    if pokemon.has_ability('Gale Wings') and move.move_type == 'Flying' and pokemon.current_hp == pokemon.max_hp:
        priority += 1
    # Triage: tăng priority cho healing move
    if pokemon.has_ability('Triage') and getattr(move, 'is_healing', False):
        priority += 3
    # Queenly Majesty/Dazzling: chặn move ưu tiên của foe
    if field.foe.has_ability('Queenly Majesty') or field.foe.has_ability('Dazzling'):
        if priority > 0:
            priority = 0
    return priority
# --- FIELD TRAP EFFECTS (ENTRY HAZARDS) ---
def apply_spikes_effect(field, foe):
    """
    Khi foe switch in, nhận damage từ Spikes (1, 2, 3 lớp)
    """
    if getattr(field, 'spikes', 0) > 0:
        layers = min(field.spikes, 3)
        damage_percent = [0, 0.125, 0.166, 0.25][layers]
        foe.take_percent_damage(damage_percent)
    return True

def apply_toxic_spikes_effect(field, foe):
    """
    Khi foe switch in, bị dính poison hoặc toxic nếu không phải Flying/Steel/Poison
    """
    if getattr(field, 'toxic_spikes', 0) > 0 and not foe.is_type(['Flying', 'Steel', 'Poison']):
        if field.toxic_spikes == 2:
            foe.status = 'tox'
        else:
            foe.status = 'psn'
    return True

def apply_stealth_rock_effect(field, foe):
    """
    Khi foe switch in, nhận damage dựa trên hệ từ Stealth Rock
    """
    if getattr(field, 'stealth_rock', False):
        multiplier = foe.get_rock_weakness_multiplier()
        foe.take_percent_damage(0.125 * multiplier)
    return True

def apply_sticky_web_effect(field, foe):
    """
    Khi foe switch in, bị giảm Speed nếu không phải Flying/Levitate
    """
    if getattr(field, 'sticky_web', False) and not foe.is_type(['Flying']) and not foe.has_ability('Levitate'):
        foe.speed = max(1, int(foe.speed * 0.67))
    return True
def apply_harsh_sunlight_effects(pokemon, field):
    """
    Áp dụng hiệu ứng Harsh Sunlight (Desolate Land) lên pokemon trong thực chiến
    field.weather: 'Harsh Sunlight'
    """
    if field.weather == 'Harsh Sunlight':
        if 'Fire' in pokemon.types:
            pokemon.move_power_boost('Fire', 1.5)
        if 'Water' in pokemon.types:
            pokemon.move_power_boost('Water', 0.0)  # Water moves vô hiệu hóa
        pokemon.disable_move_type('Water')
    return True
# --- ENVIRONMENT & TERRAIN EFFECTS ---
def apply_weather_effects(pokemon, field):
    """
    Áp dụng hiệu ứng thời tiết lên pokemon trong thực chiến
    field.weather: 'Rain', 'Sun', 'Sand', 'Snow', 'Heavy Rain', None
    """
    if field.weather == 'Rain':
        if 'Water' in pokemon.types:
            pokemon.move_power_boost('Water', 1.5)
        if 'Fire' in pokemon.types:
            pokemon.move_power_boost('Fire', 0.5)
    elif field.weather == 'Sun':
        if 'Fire' in pokemon.types:
            pokemon.move_power_boost('Fire', 1.5)
        if 'Water' in pokemon.types:
            pokemon.move_power_boost('Water', 0.5)
    elif field.weather == 'Sand':
        if 'Rock' in pokemon.types:
            pokemon.sp_defense_boost(1.5)
        if pokemon.is_grounded:
            pokemon.take_damage(1, reason='Sandstorm')
    elif field.weather == 'Snow':
        if 'Ice' in pokemon.types:
            pokemon.defense_boost(1.5)
        if pokemon.is_grounded:
            pokemon.take_damage(1, reason='Snow')
    # Heavy Rain: disables Water moves, boosts Thunder
    elif field.weather == 'Heavy Rain':
        pokemon.disable_move_type('Fire')
        pokemon.move_power_boost('Thunder', 2.0)
    return True

def apply_terrain_effects(pokemon, field):
    """
    Áp dụng hiệu ứng terrain lên pokemon trong thực chiến
    field.terrain: 'Electric', 'Grassy', 'Psychic', 'Misty', None
    """
    if field.terrain == 'Electric':
        if pokemon.is_grounded:
            pokemon.move_power_boost('Electric', 1.3)
            pokemon.cannot_sleep = True
    elif field.terrain == 'Grassy':
        if pokemon.is_grounded:
            pokemon.heal_percent(1/16)
            pokemon.move_power_boost('Grass', 1.3)
    elif field.terrain == 'Psychic':
        if pokemon.is_grounded:
            pokemon.move_power_boost('Psychic', 1.3)
            pokemon.block_priority_moves = True
    elif field.terrain == 'Misty':
        if pokemon.is_grounded:
            pokemon.immune_status = True
            pokemon.move_power_boost('Dragon', 0.5)
    return True
# --- FINAL ABILITIES FROM IMAGE (STUBS) ---
def unaware_effect(pokemon, foe):
    # Bỏ qua mọi thay đổi chỉ số của foe
    foe.stat_changes = {k: 0 for k in foe.stat_changes}
    return True

def unnerve_effect(pokemon, foe):
    # Ngăn foe dùng berry
    foe.can_use_berry = False
    return True

def unseen_fist_effect(pokemon, move, foe):
    # Move contact đánh xuyên Protect/Detect
    if getattr(move, 'is_contact', False):
        foe.ignore_protect = True
    return True

def victory_star_effect(pokemon, ally):
    # Tăng accuracy cho cả team
    pokemon.accuracy += 1
    ally.accuracy += 1
    return True

def wandering_spirit_effect(pokemon, foe, move):
    # Khi contact, đổi ability với foe
    if getattr(move, 'is_contact', False):
        pokemon.ability, foe.ability = foe.ability, pokemon.ability
    return True

def water_bubble_effect(pokemon, move):
    # Giảm damage Fire, tăng power Water, miễn nhiễm burn
    if move.move_type == 'Fire':
        move.power = int(move.power * 0.5)
    if move.move_type == 'Water':
        move.power = int(move.power * 2)
    pokemon.immune_burn = True
    return move

def white_smoke_effect(pokemon, foe):
    # Ngăn foe giảm chỉ số
    foe.can_lower_stats = False
    return True

def wimp_out_effect(pokemon):
    # Switch out khi HP < 50%
    if pokemon.current_hp < pokemon.max_hp // 2:
        pokemon.should_switch = True
    return True

def wind_power_effect(pokemon, event):
    # Khi bị đánh bởi move gió, tăng power move Electric tiếp theo
    if event == 'hit_by_wind':
        pokemon.electric_boost = True
    return True

def wind_rider_effect(pokemon, move):
    # Không nhận damage từ move gió, tăng Attack khi bị đánh
    if getattr(move, 'is_wind', False):
        move.power = 0
        pokemon.attack += 1
    return True

def wonder_skin_effect(pokemon, foe_move):
    # Status move của foe dễ trượt
    if getattr(foe_move, 'is_status', False):
        foe_move.accuracy = int(foe_move.accuracy * 0.5)
    return foe_move

def zero_to_hero_effect(pokemon, event):
    # Khi switch out, đổi form thành Hero
    if event == 'switch_out':
        pokemon.form = 'Hero'
    return pokemon.form

# --- FINAL ABILITIES FROM IMAGE (STUBS) ---
def sweet_veil_effect(pokemon, ally):
    # Miễn nhiễm sleep cho cả team
    pokemon.immune_sleep = True
    ally.immune_sleep = True
    return True

def symbiosis_effect(pokemon, ally):
    # Chuyển item cho đồng đội khi ally mất item
    if getattr(ally, 'hold_item', None) is None and getattr(pokemon, 'hold_item', None):
        ally.hold_item = pokemon.hold_item
        pokemon.hold_item = None
    return True

def tangled_feet_effect(pokemon):
    # Nếu bị confuse, tăng evasion
    if getattr(pokemon, 'status', None) == 'confusion':
        pokemon.evasion += 1
    return True

def tangling_hair_effect(move, attacker):
    # Khi contact, giảm Speed attacker
    if getattr(move, 'is_contact', False):
        attacker.speed = max(1, int(attacker.speed * 0.75))
    return True

def telepathy_effect(pokemon, ally_move):
    # Né tránh move của đồng đội
    if getattr(ally_move, 'is_damaging', False):
        ally_move.ignore_user = True
    return True

def tera_shell_effect(pokemon, current_hp, move, type_multiplier):
    # Nếu HP đầy, giảm damage move siêu hiệu quả
    if current_hp == pokemon.max_hp and type_multiplier > 1:
        move.power = int(move.power * 0.5)
    return move

def tera_shift_effect(pokemon):
    # Đổi form thành Terastal
    pokemon.form = 'Terastal'
    return pokemon.form

def terraform_zero_effect(field):
    # Vô hiệu hóa mọi hiệu ứng thời tiết và terrain
    field.weather = None
    field.terrain = None
    return True

def thermal_exchange_effect(pokemon, move):
    # Khi bị đánh bởi Fire, tăng Attack, không bị burn
    if move.move_type == 'Fire':
        pokemon.attack += 1
        pokemon.immune_burn = True
    return True

def tough_claws_effect(pokemon, move):
    # Tăng power move contact
    if getattr(move, 'is_contact', False):
        move.power = int(move.power * 1.3)
    return move

def toxic_boost_effect(pokemon, move):
    # Nếu bị poison, tăng power move Physical
    if getattr(pokemon, 'status', None) in ['psn', 'tox'] and move.category == 'Physical':
        move.power = int(move.power * 1.5)
    return move

def toxic_chain_effect(pokemon, foe, move):
    # Khi đánh trúng, có thể gây bad poison
    import random
    if random.random() < 0.3:
        foe.status = 'tox'
    return True

def toxic_debris_effect(field, move):
    # Khi bị đánh Physical, rải poison spikes
    if move.category == 'Physical':
        field.poison_spikes = True
    return True

def trace_effect(pokemon, foe):
    # Copy ability của foe khi vào sân
    pokemon.ability = foe.ability
    return True

def transistor_effect(pokemon, move):
    # Tăng power move Electric
    if move.move_type == 'Electric':
        move.power = int(move.power * 1.5)
    return move

def triage_effect(pokemon, move):
    # Ưu tiên cho move hồi phục
    if getattr(move, 'is_healing', False):
        move.priority += 3
    return move

def truant_effect(pokemon, turn_count):
    # Không tấn công ở turn chẵn
    if turn_count % 2 == 0:
        pokemon.can_attack = False
    else:
        pokemon.can_attack = True
    return True

# --- FINAL ABILITIES FROM IMAGE (STUBS) ---
def stakeout_effect(pokemon, foe, event):
    # Gây double damage cho foe vừa switch in
    if event == 'foe_switch_in':
        pokemon.damage_multiplier = 2.0
    return True

def stall_effect(pokemon):
    # Luôn đi cuối cùng
    pokemon.priority = -7
    return True

def stalwart_effect(pokemon, move):
    # Bỏ qua hiệu ứng hút đòn
    move.ignore_redirection = True
    return move

def stamina_effect(pokemon, event):
    # Khi bị đánh, tăng Defense
    if event == 'hit':
        pokemon.defense += 1
    return True

def steam_engine_effect(pokemon, move):
    # Khi bị đánh bởi Fire/Water, tăng Speed nhiều
    if move.move_type in ['Fire', 'Water']:
        pokemon.speed += 3
    return True

def steelworker_effect(pokemon, move):
    # Tăng power move Steel
    if move.move_type == 'Steel':
        move.power = int(move.power * 1.5)
    return move

def steely_spirit_effect(pokemon, ally_move):
    # Tăng power move Steel của đồng đội
    if ally_move.move_type == 'Steel':
        ally_move.power = int(ally_move.power * 1.5)
    return ally_move

def stench_effect(pokemon, foe, move):
    # Có thể gây flinch cho foe
    import random
    if random.random() < 0.1:
        foe.flinched = True
    return True

def sticky_hold_effect(pokemon):
    # Không bị cướp item
    pokemon.immune_item_theft = True
    return True

def strong_jaw_effect(pokemon, move):
    # Tăng power move cắn
    if getattr(move, 'is_bite', False):
        move.power = int(move.power * 1.5)
    return move

def sturdy_effect(pokemon, event):
    # Không bị KO với 1 hit khi HP đầy
    if event == 'first_hit' and pokemon.current_hp == pokemon.max_hp:
        pokemon.survive_one_hit = True
    return True

def suction_cups_effect(pokemon):
    # Không bị ép switch
    pokemon.cannot_be_forced_out = True
    return True

def super_luck_effect(pokemon, move):
    # Tăng tỉ lệ crit
    move.crit_rate = min(1.0, getattr(move, 'crit_rate', 0.0625) * 2)
    return move

def supersweet_syrup_effect(pokemon, foe):
    # Giảm né tránh của foe khi vào sân
    foe.evasion = max(1, int(getattr(foe, 'evasion', 1) * 0.5))
    return True

def supreme_overlord_effect(pokemon, fainted_count):
    # Tăng Attack/Sp. Atk cho mỗi đồng đội đã faint
    pokemon.attack += fainted_count
    pokemon.sp_attack += fainted_count
    return True

def swarm_effect(pokemon, move):
    # Tăng power move Bug khi HP thấp
    if move.move_type == 'Bug' and pokemon.current_hp <= pokemon.max_hp // 3:
        move.power = int(move.power * 1.5)
    return move

# --- FINAL ABILITIES FROM IMAGE (STUBS) ---
def rocky_payload_effect(pokemon, move):
    # Tăng power move Rock
    if move.move_type == 'Rock':
        move.power = int(move.power * 1.5)
    return move

def run_away_effect(pokemon):
    # Luôn chạy trốn thành công khỏi wild battle
    pokemon.can_always_escape = True
    return True

def sand_force_effect(pokemon, move, weather):
    # Tăng power move Steel/Rock/Ground khi Sandstorm
    if weather == 'Sand' and move.move_type in ['Steel', 'Rock', 'Ground']:
        move.power = int(move.power * 1.3)
    return move

def sand_spit_effect(field, event):
    # Khi bị đánh, tạo Sandstorm
    if event == 'hit':
        field.weather = 'Sand'
    return field.weather

def screen_cleaner_effect(field):
    # Xóa Light Screen, Reflect, Aurora Veil
    field.light_screen = False
    field.reflect = False
    field.aurora_veil = False
    return True

def seed_sower_effect(field, event):
    # Khi bị đánh, tạo Grassy Terrain
    if event == 'hit':
        field.terrain = 'Grassy'
    return field.terrain

def serene_grace_effect(pokemon, move):
    # Tăng tỉ lệ secondary effect
    if hasattr(move, 'secondary_chance'):
        move.secondary_chance = min(1.0, move.secondary_chance * 2)
    return move

def shadow_tag_effect(pokemon, foe):
    # Ngăn foe chạy trốn
    foe.can_escape = False
    return True

def sharpness_effect(pokemon, move):
    # Tăng power move cắt/chém
    if getattr(move, 'is_slicing', False):
        move.power = int(move.power * 1.5)
    return move

def shell_armor_effect(pokemon):
    # Không bị dính crit
    pokemon.immune_crit = True
    return True

def skill_link_effect(pokemon, move):
    # Multi-strike move luôn đánh 5 lần
    if getattr(move, 'is_multi_strike', False):
        move.hits = 5
    return move

def slow_start_effect(pokemon, turn_count):
    # 5 turn đầu giảm Attack/Speed 1/2
    if turn_count <= 5:
        return 0.5
    return 1.0

def sniper_effect(pokemon, move):
    # Crit tăng x2.25 thay vì x1.5
    if getattr(move, 'is_crit', False):
        move.crit_multiplier = 2.25
    return move

# --- FINAL ABILITIES FROM IMAGE (STUBS) ---
def pressure_effect(pokemon, foe_move):
    # Tăng số PP tiêu hao của foe_move
    foe_move.pp_cost += 1
    return True

def primordial_sea_effect(field):
    # Gọi mưa lớn khi vào sân
    field.weather = 'Heavy Rain'
    return field.weather

def propeller_tail_effect(pokemon, move):
    # Bỏ qua các hiệu ứng hút đòn
    move.ignore_redirection = True
    return move

def protean_effect(pokemon, move):
    # Đổi hệ thành hệ của move vừa dùng
    pokemon.types = [move.move_type]
    return pokemon.types

def protosynthesis_effect(pokemon, weather, item):
    # Tăng chỉ số mạnh nhất khi trời nắng hoặc cầm Booster Energy
    if weather == 'Sun' or item == 'Booster Energy':
        stat = max(pokemon.stats, key=lambda k: pokemon.stats[k])
        pokemon.stats[stat] += 1
    return True

def psychic_surge_effect(field):
    # Tạo Psychic Terrain khi vào sân
    field.terrain = 'Psychic'
    return field.terrain

def purifying_salt_effect(pokemon, move):
    # Miễn nhiễm status, giảm damage Ghost
    if getattr(move, 'is_status', False):
        return False
    if move.move_type == 'Ghost':
        move.power = int(move.power * 0.5)
    return move

def quark_drive_effect(pokemon, terrain, item):
    # Tăng chỉ số mạnh nhất khi Electric Terrain hoặc cầm Booster Energy
    if terrain == 'Electric' or item == 'Booster Energy':
        stat = max(pokemon.stats, key=lambda k: pokemon.stats[k])
        pokemon.stats[stat] += 1
    return True

def queenly_majesty_effect(pokemon, foe_move):
    # Ngăn foe dùng move ưu tiên
    if foe_move.priority > 0:
        foe_move.disabled = True
    return True

def quick_draw_effect(pokemon, move):
    # Có cơ hội ưu tiên move
    import random
    if random.random() < 0.3:
        move.priority += 1
    return move

def rattled_effect(pokemon, move):
    # Khi bị Bug/Ghost/Dark, tăng Speed
    if move.move_type in ['Bug', 'Ghost', 'Dark']:
        pokemon.speed += 1
    return True

def receiver_effect(pokemon, fainted_ally):
    # Nhận ability của đồng đội vừa faint
    pokemon.ability = fainted_ally.ability
    return True

def reckless_effect(pokemon, move):
    # Tăng power move có recoil
    if getattr(move, 'has_recoil', False):
        move.power = int(move.power * 1.2)
    return move

def refrigerate_effect(pokemon, move):
    # Biến Normal thành Ice, tăng power
    if move.move_type == 'Normal':
        move.move_type = 'Ice'
        move.power = int(move.power * 1.2)
    return move

def rivalry_effect(pokemon, foe):
    # Tăng damage nếu cùng giới, giảm nếu khác giới
    if pokemon.gender == foe.gender:
        pokemon.damage_multiplier = 1.25
    else:
        pokemon.damage_multiplier = 0.75
    return True

def rock_head_effect(pokemon, move):
    # Không nhận damage recoil
    if getattr(move, 'has_recoil', False):
        move.no_recoil = True
    return move

# --- FINAL BATCH OF ABILITIES FROM IMAGE (STUBS) ---
def neuroforce_effect(pokemon, move, type_multiplier):
    # Tăng power move siêu hiệu quả
    if type_multiplier > 1:
        move.power = int(move.power * 1.25)
    return move

def neutralizing_gas_effect(field):
    # Vô hiệu hóa mọi ability trên sân
    field.abilities_suppressed = True
    return True

def normalize_effect(pokemon, move):
    # Tất cả move thành Normal
    move.move_type = 'Normal'
    return move

def opportunist_effect(pokemon, foe, stat, amount):
    # Copy stat boost của foe
    pokemon.stats[stat] += amount
    return True

def orichalcum_pulse_effect(field, pokemon):
    # Gọi nắng mạnh, tăng Attack khi nắng
    field.weather = 'Harsh Sunlight'
    if field.weather == 'Harsh Sunlight':
        pokemon.attack += 1
    return True

def overcoat_effect(pokemon):
    # Miễn nhiễm damage thời tiết
    pokemon.immune_weather = True
    return True

def overgrow_effect(pokemon, move):
    # Tăng power move Grass khi HP thấp
    if move.move_type == 'Grass' and pokemon.current_hp <= pokemon.max_hp // 3:
        move.power = int(move.power * 1.5)
    return move

def parental_bond_effect(pokemon, move):
    # Đánh 2 lần
    move.hits = 2
    return move

def pastel_veil_effect(pokemon, ally):
    # Miễn nhiễm poison cho cả team
    pokemon.immune_poison = True
    ally.immune_poison = True
    return True

def perish_body_effect(pokemon, attacker, move):
    # Khi bị contact, cả 2 sẽ faint sau 3 turn nếu không switch
    if getattr(move, 'is_contact', False):
        pokemon.perish_count = 3
        attacker.perish_count = 3
    return True

def pickpocket_effect(pokemon, attacker):
    # Bị đánh contact thì cướp item attacker
    if getattr(attacker, 'hold_item', None):
        pokemon.hold_item = attacker.hold_item
        attacker.hold_item = None
    return True

def pickup_effect(pokemon, field):
    # Nhặt item sau trận
    if getattr(field, 'item_on_ground', None):
        pokemon.hold_item = field.item_on_ground
        field.item_on_ground = None
    return True

def pixilate_effect(pokemon, move):
    # Biến Normal thành Fairy, tăng power
    if move.move_type == 'Normal':
        move.move_type = 'Fairy'
        move.power = int(move.power * 1.2)
    return move

def plus_effect(pokemon, ally):
    # Tăng Sp. Atk nếu ally có Plus/Minus
    if getattr(ally, 'ability', '') in ['Plus', 'Minus']:
        pokemon.sp_attack += 1
    return True

def poison_point_effect(pokemon, attacker, move):
    # Khi bị contact, 30% gây poison attacker
    import random
    if getattr(move, 'is_contact', False) and random.random() < 0.3:
        attacker.status = 'psn'
    return True

def poison_puppeteer_effect(pokemon, foe):
    # Nếu foe bị poison, sẽ bị confuse
    if getattr(foe, 'status', None) in ['psn', 'tox']:
        foe.status2 = 'confusion'
    return True

def poison_touch_effect(pokemon, foe, move):
    # Khi contact, 30% gây poison foe
    import random
    if getattr(move, 'is_contact', False) and random.random() < 0.3:
        foe.status = 'psn'
    return True

def power_construct_effect(pokemon):
    # Khi HP < 50%, đổi form
    if pokemon.current_hp < pokemon.max_hp // 2:
        pokemon.form = 'Complete'
    return pokemon.form

def power_of_alchemy_effect(pokemon, fainted_ally):
    # Copy ability của đồng đội vừa faint
    pokemon.ability = fainted_ally.ability
    return True

def power_spot_effect(pokemon, ally_move):
    # Tăng power move của đồng đội
    ally_move.power = int(ally_move.power * 1.3)
    return ally_move

def prankster_effect(pokemon, move):
    # Ưu tiên cho move status
    if getattr(move, 'is_status', False):
        move.priority += 1
    return move

# --- EVEN MORE ABILITIES FROM IMAGE (STUBS) ---
def liquid_ooze_effect(pokemon, attacker, move):
    # Gây damage cho attacker khi dùng move hút máu
    if getattr(move, 'is_drain', False):
        attacker.current_hp -= move.drain_amount
    return True

def liquid_voice_effect(pokemon, move):
    # Biến move sound thành Water
    if getattr(move, 'is_sound', False):
        move.move_type = 'Water'
    return move

def long_reach_effect(pokemon, move):
    # Không bị coi là contact
    move.is_contact = False
    return move

def magic_bounce_effect(pokemon, move):
    # Phản lại move status
    if getattr(move, 'is_status', False):
        move.reflected = True
    return move

def magician_effect(pokemon, foe, move):
    # Cướp item của foe khi đánh trúng
    if getattr(move, 'hit', False) and foe.hold_item:
        pokemon.hold_item = foe.hold_item
        foe.hold_item = None
    return True

def magnet_pull_effect(pokemon, foe):
    # Ngăn Steel-type foe chạy trốn
    if 'Steel' in getattr(foe, 'types', []):
        foe.can_escape = False
    return True

def mega_launcher_effect(pokemon, move):
    # Tăng power move aura/pulse
    if getattr(move, 'is_aura_or_pulse', False):
        move.power = int(move.power * 1.5)
    return move

def merciless_effect(pokemon, foe):
    # Nếu foe bị poison, luôn crit
    if getattr(foe, 'status', None) in ['psn', 'tox']:
        pokemon.always_crit = True
    return True

def mimicry_effect(pokemon, terrain):
    # Đổi hệ theo terrain
    if terrain:
        pokemon.types = [terrain]
    return pokemon.types

def minds_eye_effect(pokemon, move):
    # Bỏ qua né tránh, Normal/Fighting đánh trúng Ghost
    move.ignore_evasion = True
    if move.move_type in ['Normal', 'Fighting']:
        move.can_hit_ghost = True
    return move

def minus_effect(pokemon, ally):
    # Tăng Sp. Atk nếu ally có Plus/Minus
    if getattr(ally, 'ability', '') in ['Plus', 'Minus']:
        pokemon.sp_attack += 1
    return True

def mirror_armor_effect(pokemon, foe, stat, amount):
    # Phản lại giảm chỉ số
    foe.stats[stat] -= amount
    return True

def misty_surge_effect(field):
    # Tạo Misty Terrain khi vào sân
    field.terrain = 'Misty'
    return field.terrain

def mycelium_might_effect(pokemon, move):
    # Status move luôn đi sau, không bị ảnh hưởng bởi ability foe
    if getattr(move, 'is_status', False):
        move.priority = -7
        move.ignore_ability = True
    return move

# --- MORE ABILITIES FROM IMAGE (STUBS) ---
def hyper_cutter_effect(pokemon, foe):
    # Ngăn đối thủ giảm Attack
    foe.can_lower_attack = False
    return True

def illuminate_effect(pokemon):
    # Tăng tỉ lệ gặp wild Pokémon
    pokemon.encounter_rate = getattr(pokemon, 'encounter_rate', 1.0) * 2
    return True

def illusion_effect(pokemon, party):
    # Hóa trang thành Pokémon cuối cùng còn sống trong party
    for p in reversed(party):
        if p.is_alive:
            pokemon.disguise_as = p.species
            break
    return True

def imposter_effect(pokemon, foe):
    # Biến thành foe khi vào sân
    pokemon.transform(foe)
    return True

def infiltrator_effect(pokemon, foe):
    # Bỏ qua barrier của foe
    foe.barrier_ignored = True
    return True

def innards_out_effect(pokemon, attacker):
    # Gây damage bằng lượng HP còn lại khi bị KO
    if pokemon.current_hp == 0:
        attacker.current_hp -= pokemon.last_hp
    return True

def inner_focus_effect(pokemon):
    # Không bị flinch
    pokemon.immune_flinch = True
    return True

def intrepid_sword_effect(pokemon):
    # Tăng Attack khi vào sân
    pokemon.attack += 1
    return True

def iron_fist_effect(pokemon, move):
    # Tăng power move đấm
    if getattr(move, 'is_punch', False):
        move.power = int(move.power * 1.2)
    return move

def justified_effect(pokemon, move):
    # Tăng Attack khi bị move Dark
    if move.move_type == 'Dark':
        pokemon.attack += 1
    return True

def keen_eye_effect(pokemon, foe):
    # Ngăn đối thủ giảm accuracy
    foe.can_lower_accuracy = False
    return True

def klutz_effect(pokemon):
    # Không thể dùng item
    pokemon.can_use_item = False
    return True

def libero_effect(pokemon, move):
    # Đổi hệ thành hệ của move vừa dùng
    pokemon.types = [move.move_type]
    return pokemon.types

def light_metal_effect(pokemon):
    # Giảm nửa trọng lượng
    pokemon.weight = pokemon.weight // 2
    return pokemon.weight

def lingering_aroma_effect(attacker, defender, move):
    # Khi contact, attacker bị đổi ability thành Lingering Aroma
    if getattr(move, 'is_contact', False):
        attacker.ability = 'Lingering Aroma'
    return True

# --- FINAL ABILITIES FROM IMAGE (STUBS) ---
def full_metal_body_effect(pokemon, foe):
    # Ngăn đối thủ giảm chỉ số
    foe.can_lower_stats = False
    return True

def gale_wings_effect(pokemon, move):
    # Ưu tiên move Flying khi HP đầy
    if move.move_type == 'Flying' and pokemon.current_hp == pokemon.max_hp:
        move.priority += 1
    return move

def galvanize_effect(pokemon, move):
    # Biến Normal thành Electric, tăng power
    if move.move_type == 'Normal':
        move.move_type = 'Electric'
        move.power = int(move.power * 1.2)
    return move

def gluttony_effect(pokemon, berry):
    # Ăn berry sớm hơn
    if berry and pokemon.current_hp <= pokemon.max_hp // 2:
        pokemon.consume_berry(berry)
    return True

def good_as_gold_effect(pokemon, status):
    # Miễn nhiễm mọi status
    if status:
        return False
    return True

def gorilla_tactics_effect(pokemon):
    # Tăng Attack, chỉ dùng move đầu tiên
    pokemon.attack = int(pokemon.attack * 1.5)
    pokemon.locked_move = True
    return True

def grass_pelt_effect(pokemon, terrain):
    # Tăng Defense khi Grassy Terrain
    if terrain == 'Grassy':
        pokemon.defense += 1
    return True

def grassy_surge_effect(field):
    # Tạo Grassy Terrain khi vào sân
    field.terrain = 'Grassy'
    return field.terrain

def guard_dog_effect(pokemon, event):
    # Tăng Attack khi bị intimidate, không bị ép switch
    if event == 'intimidated':
        pokemon.attack += 1
    pokemon.cannot_be_forced_out = True
    return True

def gulp_missile_effect(pokemon, event):
    # Trả lại sát thương khi dùng Dive/Surf
    if event == 'return_from_dive':
        pokemon.counter_attack = True
    return True

def hadron_engine_effect(pokemon, field):
    # Tạo Electric Terrain, tăng Sp. Atk
    field.terrain = 'Electric'
    pokemon.sp_attack += 1
    return True

def heavy_metal_effect(pokemon):
    # Gấp đôi trọng lượng
    pokemon.weight = pokemon.weight * 2
    return pokemon.weight

def honey_gather_effect(pokemon):
    # Có thể nhặt Honey sau trận
    pokemon.has_honey = True
    return True

def hospitality_effect(pokemon, ally):
    # Hồi HP cho đồng đội khi vào sân
    ally.current_hp = min(ally.max_hp, ally.current_hp + ally.max_hp // 4)
    return True

def hunger_switch_effect(pokemon):
    # Đổi form mỗi turn
    pokemon.form = 'Full Belly' if getattr(pokemon, 'form', None) == 'Hangry' else 'Hangry'
    return pokemon.form

# --- EVEN MORE ABILITIES FROM IMAGE (STUBS) ---
def dragons_maw_effect(pokemon, move):
    # Tăng power move Dragon
    if move.move_type == 'Dragon':
        move.power = int(move.power * 1.5)
    return move

def early_bird_effect(pokemon):
    # Tỉnh ngủ nhanh hơn
    if getattr(pokemon, 'status', None) == 'slp':
        pokemon.sleep_turns = max(0, pokemon.sleep_turns - 1)
    return True

def earth_eater_effect(pokemon, move):
    # Heal khi bị move Ground
    if move.move_type == 'Ground':
        pokemon.current_hp = min(pokemon.max_hp, pokemon.current_hp + pokemon.max_hp // 4)
    return True

def electric_surge_effect(field):
    # Tạo Electric Terrain khi vào sân
    field.terrain = 'Electric'
    return field.terrain

def electromorphosis_effect(pokemon, event):
    # Đòn Electric tiếp theo x2 power khi bị đánh
    if event == 'hit':
        pokemon.electric_boost = True
    return True

def embody_aspect_effect(pokemon, form):
    # Tăng chỉ số theo form
    if form == 'Attack':
        pokemon.attack += 1
    elif form == 'Defense':
        pokemon.defense += 1
    elif form == 'Sp. Atk':
        pokemon.sp_attack += 1
    elif form == 'Speed':
        pokemon.speed += 1
    return True

def emergency_exit_effect(pokemon):
    # Switch out khi HP < 50%
    if pokemon.current_hp < pokemon.max_hp // 2:
        pokemon.should_switch = True
    return True

def fairy_aura_effect(pokemon, move):
    # Tăng power move Fairy cho tất cả
    if move.move_type == 'Fairy':
        move.power = int(move.power * 1.33)
    return move

def flare_boost_effect(pokemon, move):
    # Tăng Sp. Atk khi bị burn
    if getattr(pokemon, 'status', None) == 'brn' and move.category == 'Special':
        move.power = int(move.power * 1.5)
    return move

def flower_gift_effect(pokemon, weather):
    # Tăng chỉ số cho đồng đội khi trời nắng
    if weather == 'Sun':
        pokemon.attack += 1
        pokemon.sp_defense += 1
    return True

def forewarn_effect(pokemon, foe_moves):
    # Biết move mạnh nhất của đối thủ
    if foe_moves:
        pokemon.known_move = max(foe_moves, key=lambda m: m.power)
    return True

def friend_guard_effect(pokemon, ally):
    # Giảm damage cho đồng đội
    ally.damage_taken = int(ally.damage_taken * 0.75)
    return True

def frisk_effect(pokemon, foe):
    # Kiểm tra item của đối thủ
    pokemon.seen_item = getattr(foe, 'hold_item', None)
    return True

# --- MORE ABILITIES FROM IMAGE (STUBS) ---
def clear_body_effect(pokemon, foe):
    # Ngăn đối thủ giảm chỉ số
    foe.can_lower_stats = False
    return True

def color_change_effect(pokemon, move):
    # Đổi hệ thành hệ của move vừa nhận
    pokemon.types = [move.move_type]
    return pokemon.types

def commander_effect(pokemon, ally):
    # Vào miệng DonDozo nếu có trên sân
    if ally.species == 'Dondozo':
        pokemon.is_commander = True
    return True

def compound_eyes_effect(pokemon):
    # Tăng accuracy
    pokemon.accuracy = int(pokemon.accuracy * 1.3)
    return pokemon.accuracy

def contrary_effect(pokemon, stat, amount):
    # Đảo ngược hiệu ứng tăng/giảm chỉ số
    pokemon.stats[stat] -= amount
    return True

def corrosion_effect(pokemon, target):
    # Có thể gây poison cho Steel/Poison
    if target.type in ['Steel', 'Poison']:
        target.status = 'psn'
    return True

def costar_effect(pokemon, ally):
    # Sao chép chỉ số của đồng đội khi vào sân
    pokemon.stats = ally.stats.copy()
    return True

def cotton_down_effect(pokemon, foe):
    # Khi bị đánh, giảm Speed của foe
    foe.speed = max(1, int(foe.speed * 0.67))
    return True

def cud_chew_effect(pokemon, berry):
    # Ăn lại berry lần 2
    if berry:
        pokemon.berry_queue.append(berry)
    return True

def curious_medicine_effect(pokemon, ally):
    # Reset stat changes của đồng đội khi vào sân
    ally.stat_changes = {k: 0 for k in ally.stat_changes}
    return True

def damp_effect(pokemon, foe_move):
    # Ngăn dùng move tự nổ
    if getattr(foe_move, 'is_self_destruct', False):
        foe_move.disabled = True
    return True

def dancer_effect(pokemon, foe_move):
    # Sao chép move Dance của đối thủ
    if getattr(foe_move, 'is_dance', False):
        pokemon.copied_move = foe_move.name
    return True

def dark_aura_effect(pokemon, move):
    # Tăng power move Dark cho tất cả
    if move.move_type == 'Dark':
        move.power = int(move.power * 1.33)
    return move

def dazzling_effect(pokemon, foe_move):
    # Ngăn move ưu tiên
    if foe_move.priority > 0:
        foe_move.disabled = True
    return True

def defeatist_effect(pokemon):
    # Khi HP < 50%, giảm Atk/SpA
    if pokemon.current_hp < pokemon.max_hp // 2:
        pokemon.attack = int(pokemon.attack * 0.5)
        pokemon.sp_attack = int(pokemon.sp_attack * 0.5)
    return True

def delta_stream_effect(weather):
    # Tạo gió mạnh, giảm damage move siêu hiệu quả Flying
    if weather == 'Delta Stream':
        return 'Strong Winds'
    return weather

def desolate_land_effect(weather):
    # Tạo nắng cực mạnh
    if weather == 'Desolate Land':
        return 'Harsh Sunlight'
    return weather

def disguise_effect(pokemon, event):
    # Tránh sát thương lần đầu
    if event == 'first_hit' and not getattr(pokemon, 'disguise_broken', False):
        pokemon.disguise_broken = True
        return True
    return False

# --- ABILITIES FROM IMAGE (STUBS) ---
def aerilate_effect(pokemon, move):
    # Biến Normal thành Flying, tăng power
    if move.move_type == 'Normal':
        move.move_type = 'Flying'
        move.power = int(move.power * 1.2)
    return move

def analytic_effect(pokemon, move, is_last):
    # Nếu đánh cuối cùng, tăng power
    if is_last:
        move.power = int(move.power * 1.3)
    return move

def anger_point_effect(pokemon, event):
    # Nếu bị crit, max Attack
    if event == 'critical_hit':
        pokemon.attack = pokemon.max_attack
    return True

def anger_shell_effect(pokemon, hp_drop):
    # Khi HP < 50%, tăng Atk/SpA/Speed, giảm Def/SpD
    if hp_drop and pokemon.current_hp < pokemon.max_hp // 2:
        pokemon.attack += 1
        pokemon.sp_attack += 1
        pokemon.speed += 1
        pokemon.defense = max(1, pokemon.defense - 1)
        pokemon.sp_defense = max(1, pokemon.sp_defense - 1)
    return True

def anticipation_effect(pokemon, foe_moves):
    # Phát hiện move nguy hiểm
    for move in foe_moves:
        if move.is_super_effective or move.is_ohko:
            pokemon.warned = True
            break
    return getattr(pokemon, 'warned', False)

def arena_trap_effect(pokemon, foe):
    # Ngăn foe chạy trốn
    foe.can_escape = False
    return True

def armor_tail_effect(pokemon, foe_move):
    # Ngăn dùng move ưu tiên
    if foe_move.priority > 0:
        foe_move.disabled = True
    return True

def aroma_veil_effect(pokemon, ally_moves):
    # Bảo vệ đồng đội khỏi các hiệu ứng hạn chế lựa chọn
    for move in ally_moves:
        if move.is_choice_limited:
            move.disabled = True
    return True

def aura_break_effect(pokemon, move):
    # Giảm hiệu ứng Aura (Fairy/Dark)
    if move.move_type in ['Fairy', 'Dark']:
        move.power = int(move.power * 0.75)
    return move

def ball_fetch_effect(pokemon, event):
    # Nhặt lại Poké Ball khi ném trượt
    if event == 'failed_throw':
        pokemon.has_ball = True
    return True

def battery_effect(pokemon, ally_move):
    # Tăng power move Special của đồng đội
    if ally_move.category == 'Special':
        ally_move.power = int(ally_move.power * 1.3)
    return ally_move

def battle_armor_effect(pokemon):
    # Không bị dính crit
    pokemon.immune_crit = True
    return True

def berserk_effect(pokemon, hp_drop):
    # Khi HP < 50%, tăng Sp. Atk
    if hp_drop and pokemon.current_hp < pokemon.max_hp // 2:
        pokemon.sp_attack += 1
    return True

def big_pecks_effect(pokemon):
    # Không bị giảm Defense
    pokemon.immune_def_down = True
    return True

def bulletproof_effect(pokemon, move):
    # Miễn nhiễm move bóng/bomb
    if getattr(move, 'is_ball_or_bomb', False):
        move.disabled = True
    return True

# --- COMBINED/FORM ABILITIES ---
def as_one_effect(pokemon, event, target=None):
    # As One: Kết hợp hiệu ứng Grim Neigh (Spectrier) hoặc Chilling Neigh (Glastrier) và Unnerve
    if pokemon.species == 'Spectrier':
        grim_neigh_boost(pokemon)
    elif pokemon.species == 'Glastrier':
        chilling_neigh_boost(pokemon)
    # Unnerve: đối thủ không dùng berry
    if target:
        target.can_use_berry = False
    return True

def comatose_effect(pokemon):
    # Luôn ở trạng thái sleep, vẫn dùng move
    pokemon.status = 'slp'
    pokemon.can_attack_while_sleep = True
    return True

def schooling_effect(pokemon):
    # Thay đổi form khi HP > 50%
    if pokemon.current_hp > pokemon.max_hp // 2:
        pokemon.form = 'School'
    else:
        pokemon.form = 'Solo'
    return pokemon.form

def battle_bond_effect(pokemon, event):
    # Khi KO đối thủ, chuyển thành Ash-Greninja
    if event == 'KO':
        pokemon.form = 'Ash-Greninja'
    return pokemon.form

def rks_system_effect(pokemon, held_item):
    # Thay đổi hệ theo item (Memory)
    if held_item and 'Memory' in held_item:
        pokemon.types = [held_item.replace(' Memory', '')]
    return pokemon.types

def multitype_effect(pokemon, held_item):
    # Thay đổi hệ theo item (Plate)
    if held_item and 'Plate' in held_item:
        pokemon.types = [held_item.replace(' Plate', '')]
    return pokemon.types

def ice_face_effect(pokemon, move):
    # Chặn move vật lý lần đầu, sau đó đổi form
    if move.category == 'Physical' and not getattr(pokemon, 'ice_face_broken', False):
        pokemon.ice_face_broken = True
        return True
    return False

def zen_mode_effect(pokemon):
    # Khi HP < 50%, đổi form
    if pokemon.current_hp < pokemon.max_hp // 2:
        pokemon.form = 'Zen'
    else:
        pokemon.form = 'Normal'
    return pokemon.form

def shields_down_effect(pokemon):
    # Khi HP < 50%, đổi form
    if pokemon.current_hp < pokemon.max_hp // 2:
        pokemon.form = 'Core'
    else:
        pokemon.form = 'Meteor'
    return pokemon.form

def stance_change_effect(pokemon, move):
    # Đổi form giữa Shield và Blade khi dùng move
    if move.name in ['King’s Shield', 'Protect']:
        pokemon.form = 'Shield'
    else:
        pokemon.form = 'Blade'
    return pokemon.form

# --- PALDEA RUIN ABILITIES ---
def tablets_of_ruin_effect(defender):
    # Giảm Defense của đối thủ x0.75
    defender.defense = int(defender.defense * 0.75)
    return defender.defense

def sword_of_ruin_effect(defender):
    # Giảm Defense của đối thủ x0.75
    defender.defense = int(defender.defense * 0.75)
    return defender.defense

def vessel_of_ruin_effect(defender):
    # Giảm Sp. Atk của đối thủ x0.75
    defender.sp_attack = int(defender.sp_attack * 0.75)
    return defender.sp_attack

def beads_of_ruin_effect(defender):
    # Giảm Sp. Def của đối thủ x0.75
    defender.sp_defense = int(defender.sp_defense * 0.75)
    return defender.sp_defense

# --- STAT BOOST ABILITIES ---
def beast_boost_stat(pokemon, stat):
    # Khi KO đối thủ, tăng chỉ số mạnh nhất
    pokemon.stats[stat] += 1
    return True

def moxie_boost(pokemon):
    # Khi KO đối thủ, tăng Attack
    pokemon.attack += 1
    return True

def chilling_neigh_boost(pokemon):
    # Khi KO đối thủ, tăng Attack
    pokemon.attack += 1
    return True

def grim_neigh_boost(pokemon):
    # Khi KO đối thủ, tăng Sp. Atk
    pokemon.sp_attack += 1
    return True

def soul_heart_boost(pokemon):
    # Khi KO đối thủ, tăng Sp. Atk
    pokemon.sp_attack += 1
    return True

def competitive_boost(pokemon):
    # Khi bị giảm stats, tăng Sp. Atk +2
    pokemon.sp_attack += 2
    return True

def defiant_boost(pokemon):
    # Khi bị giảm stats, tăng Attack +2
    pokemon.attack += 2
    return True

def download_boost(pokemon, foe_def, foe_spdef):
    # Tăng Attack nếu foe Sp. Def thấp, ngược lại tăng Sp. Atk
    if foe_def < foe_spdef:
        pokemon.attack += 1
    else:
        pokemon.sp_attack += 1
    return True

def moody_boost(pokemon):
    # Mỗi turn tăng 1 chỉ số ngẫu nhiên, giảm 1 chỉ số khác
    import random
    stats = list(pokemon.stats.keys())
    up = random.choice(stats)
    down = random.choice([s for s in stats if s != up])
    pokemon.stats[up] += 2
    pokemon.stats[down] = max(1, pokemon.stats[down] - 1)
    return True

def simple_boost(pokemon, stat, amount):
    # Tăng gấp đôi hiệu quả boost
    pokemon.stats[stat] += amount * 2
    return True

# --- DAMAGE DEALING ABILITIES ---
def bad_dreams_damage(target):
    # Gây sát thương 1/8 max HP mỗi turn nếu target bị sleep
    if getattr(target, 'status', None) == 'slp':
        return int(target.max_hp // 8)
    return 0

def rough_skin_damage(attacker):
    # Gây sát thương 1/8 max HP cho attacker khi bị đánh contact
    return int(attacker.max_hp // 8)

def iron_barbs_damage(attacker):
    # Gây sát thương 1/8 max HP cho attacker khi bị đánh contact
    return int(attacker.max_hp // 8)

def aftermath_damage(attacker):
    # Gây sát thương 1/4 max HP cho attacker khi KO
    return int(attacker.max_hp // 4)

# --- WEATHER NEGATION ABILITIES ---
def cloud_nine_negate_weather():
    # Vô hiệu hóa mọi hiệu ứng thời tiết
    return None

def air_lock_negate_weather():
    # Vô hiệu hóa mọi hiệu ứng thời tiết
    return None

# --- WEATHER ABILITIES ---
def drizzle_weather():
    # Gọi mưa khi vào trận
    return 'Rain'

def drought_weather():
    # Gọi nắng khi vào trận
    return 'Sun'

def sand_stream_weather():
    # Gọi Sandstorm khi vào trận
    return 'Sand'

def snow_warning_weather():
    # Gọi Hail/Snow khi vào trận
    return 'Snow'

def forecast_weather(pokemon, weather):
    # Thay đổi hệ theo thời tiết
    if weather == 'Rain':
        pokemon.types = ['Water']
    elif weather == 'Sun':
        pokemon.types = ['Fire']
    elif weather in ['Hail', 'Snow']:
        pokemon.types = ['Ice']
    return pokemon.types

# --- STATUS ABILITIES ---
def synchronize_status(pokemon, status, target):
    # Khi bị status, truyền status cho đối thủ
    if status in ['brn', 'psn', 'tox', 'par', 'slp']:
        target.status = status
        return True
    return False

def poison_heal_heal(pokemon):
    # Nếu bị poison/toxic, heal 1/8 max HP mỗi turn
    if getattr(pokemon, 'status', None) in ['psn', 'tox']:
        return int(pokemon.max_hp // 8)
    return 0

def flame_body_status(move, attacker):
    # 30% gây burn khi bị đánh contact
    import random
    if getattr(move, 'is_contact', False) and random.random() < 0.3:
        attacker.status = 'brn'
        return True
    return False

def effect_spore_status(move, attacker):
    # 10% gây sleep, poison, paralyze khi bị đánh contact
    import random
    if getattr(move, 'is_contact', False):
        r = random.random()
        if r < 0.1:
            attacker.status = 'slp'
            return True
        elif r < 0.2:
            attacker.status = 'psn'
            return True
        elif r < 0.3:
            attacker.status = 'par'
            return True
    return False

def static_status(move, attacker):
    # 30% gây paralyze khi bị đánh contact
    import random
    if getattr(move, 'is_contact', False) and random.random() < 0.3:
        attacker.status = 'par'
        return True
    return False

def cute_charm_status(move, attacker, defender):
    # 30% gây attract khi bị đánh contact khác giới
    import random
    if getattr(move, 'is_contact', False) and attacker.gender != defender.gender and random.random() < 0.3:
        attacker.status = 'attract'
        return True
    return False

def cursed_body_status(move, attacker):
    # 30% disable move khi bị đánh contact
    import random
    if getattr(move, 'is_contact', False) and random.random() < 0.3:
        move.disabled = True
        return True
    return False

def mummy_status(move, attacker):
    # Khi bị đánh contact, attacker bị đổi ability thành Mummy
    if getattr(move, 'is_contact', False):
        attacker.ability = 'Mummy'
        return True
    return False

def gooey_status(move, attacker):
    # Khi bị đánh contact, attacker bị giảm Speed
    if getattr(move, 'is_contact', False):
        attacker.speed = max(1, int(attacker.speed * 0.75))
        return True
    return False

def no_guard_accuracy(move):
    # Tất cả move đều luôn trúng
    return 100
# --- ABILITIES THAT BREAK IMMUNITY ---
def mold_breaker_ignore_immunity(attacker, defender, move):
    # Move của attacker bỏ qua mọi ability miễn nhiễm của defender
    return True
# --- IMMUNITY ABILITIES ---
def immunity_status(pokemon, status):
    # Miễn nhiễm poison
    if status in ['psn', 'tox']:
        return False
    return True

def water_veil_status(pokemon, status):
    # Miễn nhiễm burn
    if status == 'brn':
        return False
    return True

def limber_status(pokemon, status):
    # Miễn nhiễm paralyze
    if status == 'par':
        return False
    return True

def insomnia_status(pokemon, status):
    # Miễn nhiễm sleep
    if status == 'slp':
        return False
    return True

def vital_spirit_status(pokemon, status):
    # Miễn nhiễm sleep
    if status == 'slp':
        return False
    return True

def own_tempo_status(pokemon, status):
    # Miễn nhiễm confusion
    if status == 'confusion':
        return False
    return True

def oblivious_status(pokemon, status):
    # Miễn nhiễm attract/taunt
    if status in ['attract', 'taunt']:
        return False
    return True

def cloud_nine_weather(weather):
    # Bỏ qua hiệu ứng thời tiết
    return None

def air_lock_weather(weather):
    # Bỏ qua hiệu ứng thời tiết
    return None

def magma_armor_status(pokemon, status):
    # Miễn nhiễm freeze
    if status == 'frz':
        return False
    return True

def sand_veil_accuracy(move, weather):
    # Miễn nhiễm sandstorm, tăng né tránh
    if weather == 'Sand':
        return int(move.accuracy * 0.8)
    return move.accuracy

def snow_cloak_accuracy(move, weather):
    # Miễn nhiễm hail/snow, tăng né tránh
    if weather in ['Hail', 'Snow']:
        return int(move.accuracy * 0.8)
    return move.accuracy

def flower_veil_status(pokemon, status):
    # Miễn nhiễm status cho hệ Grass
    if 'Grass' in getattr(pokemon, 'types', []):
        return False
    return True

def leaf_guard_status(pokemon, status, weather):
    # Miễn nhiễm status khi trời nắng
    if weather == 'Sun':
        return False
    return True

def shield_dust_secondary(move):
    # Miễn nhiễm secondary effect
    if getattr(move, 'has_secondary', False):
        return False
    return True

def overcoat_status(pokemon, status, move):
    # Miễn nhiễm powder, weather, sound
    if getattr(move, 'is_powder', False) or getattr(move, 'is_sound', False):
        return False
    return True

def soundproof_status(pokemon, move):
    # Miễn nhiễm move sound-based
    if getattr(move, 'is_sound', False):
        return False
    return True

def sap_sipper_status(pokemon, move):
    # Miễn nhiễm move Grass, tăng Attack
    if move.move_type == 'Grass':
        return False
    return True

def lightning_rod_status(pokemon, move):
    # Miễn nhiễm move Electric, tăng Sp. Atk
    if move.move_type == 'Electric':
        return False
    return True

def motor_drive_status(pokemon, move):
    # Miễn nhiễm move Electric, tăng Speed
    if move.move_type == 'Electric':
        return False
    return True

def storm_drain_status(pokemon, move):
    # Miễn nhiễm move Water, tăng Sp. Atk
    if move.move_type == 'Water':
        return False
    return True

def flash_fire_status(pokemon, move):
    # Miễn nhiễm move Fire, tăng power Fire
    if move.move_type == 'Fire':
        return False
    return True

def thick_fat_status(pokemon, move):
    # Miễn nhiễm move Fire/Ice, giảm damage
    if move.move_type in ['Fire', 'Ice']:
        return False
    return True

def wonder_guard_status(pokemon, move, type_multiplier):
    # Chỉ nhận damage từ move siêu hiệu quả
    if type_multiplier <= 1:
        return False
    return True

# --- RECOVERY ABILITIES ---
def regenerator_heal(pokemon, on_switch_out):
    # Heal 1/3 max HP khi switch out
    if on_switch_out:
        return int(pokemon.max_hp // 3)
    return 0

def water_absorb_heal(pokemon, move):
    # Heal 1/4 max HP khi bị move Water
    if move.move_type == 'Water':
        return int(pokemon.max_hp // 4)
    return 0

def volt_absorb_heal(pokemon, move):
    # Heal 1/4 max HP khi bị move Electric
    if move.move_type == 'Electric':
        return int(pokemon.max_hp // 4)
    return 0

def dry_skin_heal(pokemon, move, weather):
    # Heal 1/8 max HP khi trời mưa, move Water; mất 1/8 khi trời nắng, move Fire
    if weather == 'Rain':
        return int(pokemon.max_hp // 8)
    if move.move_type == 'Water':
        return int(pokemon.max_hp // 4)
    if weather == 'Sun' or move.move_type == 'Fire':
        return -int(pokemon.max_hp // 8)
    return 0

def ice_body_heal(pokemon, weather):
    # Heal 1/16 max HP khi trời Hail/Snow
    if weather in ['Hail', 'Snow']:
        return int(pokemon.max_hp // 16)
    return 0

def rain_dish_heal(pokemon, weather):
    # Heal 1/16 max HP khi trời mưa
    if weather == 'Rain':
        return int(pokemon.max_hp // 16)
    return 0

def harvest_berry(pokemon, consumed_berry, weather):
    # 50% (100% nếu trời nắng) hồi lại berry đã dùng
    import random
    if consumed_berry:
        chance = 1.0 if weather == 'Sun' else 0.5
        if random.random() < chance:
            return consumed_berry
    return None

def healer_cure(pokemon, ally):
    # 30% cure status cho đồng đội mỗi turn
    import random
    if random.random() < 0.3:
        ally.status = None
        return True
    return False

def hydration_cure(pokemon, weather):
    # Cure status khi trời mưa
    if weather == 'Rain':
        pokemon.status = None
        return True
    return False

def natural_cure_cure(pokemon, on_switch_out):
    # Cure status khi switch out
    if on_switch_out:
        pokemon.status = None
        return True
    return False

def shed_skin_cure(pokemon):
    # 33% cure status mỗi turn
    import random
    if random.random() < 0.33:
        pokemon.status = None
        return True
    return False

def cheek_pouch_heal(pokemon, consumed_berry):
    # Heal 1/3 max HP khi ăn berry
    if consumed_berry:
        return int(pokemon.max_hp // 3)
    return 0

def ripen_berry_effect(berry_effect):
    # Gấp đôi hiệu quả berry
    return berry_effect * 2

def magic_guard_heal(pokemon, source):
    # Chỉ nhận heal từ move, không nhận damage từ effect khác
    if source == 'move':
        return True
    return False

# --- DEFENSE MODIFIER ABILITIES ---
def marvel_scale_defense(pokemon, base_def):
    # Defense x1.5 nếu bị status
    if getattr(pokemon, 'status', None) in ['brn', 'psn', 'tox', 'par', 'slp', 'frz']:
        return int(base_def * 1.5)
    return base_def

def multiscale_damage_multiplier(pokemon, current_hp, max_hp, type_multiplier):
    # Nếu HP đầy, giảm damage x0.5
    if current_hp == max_hp:
        return type_multiplier * 0.5
    return type_multiplier

def fur_coat_defense(base_def):
    # Defense x2
    return int(base_def * 2)

def ice_scales_spdef(base_spdef):
    # Sp. Def x2
    return int(base_spdef * 2)

def dauntless_shield_defense(base_def, on_switch_in):
    # Defense +1 khi switch in
    if on_switch_in:
        return base_def + 1
    return base_def

def fluffy_damage_multiplier(move, type_multiplier):
    # Nếu move là contact, giảm damage x0.5; nếu là Fire, tăng x2
    if getattr(move, 'is_contact', False):
        type_multiplier *= 0.5
    if move.move_type == 'Fire':
        type_multiplier *= 2
    return type_multiplier

def shadow_shield_damage_multiplier(current_hp, max_hp, type_multiplier):
    # Nếu HP đầy, giảm damage x0.5
    if current_hp == max_hp:
        return type_multiplier * 0.5
    return type_multiplier

def weak_armor_defense(base_def, on_physical_hit):
    # Khi bị đánh vật lý, giảm Def, tăng Speed
    if on_physical_hit:
        return max(1, base_def - 1)
    return base_def

def heatproof_damage_multiplier(move, type_multiplier):
    # Nếu move là Fire, giảm damage x0.5
    if move.move_type == 'Fire':
        return type_multiplier * 0.5
    return type_multiplier

def water_compaction_defense(base_def, on_water_hit):
    # Khi bị đánh bởi move Water, tăng Def +2
    if on_water_hit:
        return base_def + 2
    return base_def

def well_baked_body_defense(base_def, on_fire_hit):
    # Khi bị đánh bởi move Fire, tăng Def +2
    if on_fire_hit:
        return base_def + 2
    return base_def

# --- SPEED MODIFIER ABILITIES ---
def chlorophyll_speed(pokemon, weather):
    # Double Speed in Sun
    if weather == 'Sun':
        return 2.0
    return 1.0

def sand_rush_speed(pokemon, weather):
    # Double Speed in Sandstorm
    if weather == 'Sand':
        return 2.0
    return 1.0

def slush_rush_speed(pokemon, weather):
    # Double Speed in Hail/Snow
    if weather in ['Hail', 'Snow']:
        return 2.0
    return 1.0

def quick_feet_speed(pokemon):
    # Speed x1.5 nếu bị status (burn, poison, paralyze, sleep, freeze)
    if getattr(pokemon, 'status', None) in ['brn', 'psn', 'tox', 'par', 'slp', 'frz']:
        return 1.5
    return 1.0

def unburden_speed(pokemon):
    # Double Speed nếu không cầm item
    if getattr(pokemon, 'hold_item', None) is None:
        return 2.0
    return 1.0

def speed_boost_speed(pokemon, turn_count):
    # Speed tăng mỗi turn (x1.5 mỗi turn, demo)
    return 1.0 + 0.5 * max(0, turn_count - 1)

def surge_surfer_speed(pokemon, terrain):
    # Double Speed nếu Electric Terrain
    if terrain == 'Electric':
        return 2.0
    return 1.0

# --- DAMAGE MODIFIER ABILITIES ---
def adaptability_stab(attacker, move, base_stab):
    # STAB = 2.0 (thay vì 1.5)
    if move.move_type in getattr(attacker, 'types', []):
        return 2.0
    return base_stab

def sheer_force_boost(attacker, move, base_power):
    # +30% power nếu move có secondary effect, nhưng bỏ secondary effect
    if getattr(move, 'has_secondary', False):
        return int(base_power * 1.3)
    return base_power

def guts_boost(attacker, move, base_atk):
    # Attack x1.5 nếu bị status (burn, poison, paralyze, sleep, freeze)
    if getattr(attacker, 'status', None) in ['brn', 'psn', 'tox', 'par', 'slp', 'frz'] and move.category == 'Physical':
        return int(base_atk * 1.5)
    return base_atk

def huge_power_boost(attacker, move, base_atk):
    # Attack x2
    if move.category == 'Physical':
        return int(base_atk * 2)
    return base_atk

def solar_power_boost(attacker, move, base_spa, weather):
    # Sp. Atk x1.5 khi trời nắng
    if weather == 'Sun' and move.category == 'Special':
        return int(base_spa * 1.5)
    return base_spa

def hustle_boost(attacker, move, base_atk):
    # Attack x1.5 nhưng accuracy x0.8 cho Physical
    if move.category == 'Physical':
        return int(base_atk * 1.5)
    return base_atk

def tinted_lens_multiplier(move, type_multiplier):
    # Nếu move không hiệu quả (type_multiplier < 1), x2 damage
    if type_multiplier < 1:
        return type_multiplier * 2
    return type_multiplier

def technician_boost(move, base_power):
    # Nếu power <= 60, x1.5
    if base_power <= 60:
        return int(base_power * 1.5)
    return base_power

def filter_solidrock_prismarmor_multiplier(move, type_multiplier):
    # Nếu move siêu hiệu quả (type_multiplier > 1), giảm damage x0.75
    if type_multiplier > 1:
        return type_multiplier * 0.75
    return type_multiplier

def thick_fat_multiplier(move, type_multiplier):
    # Nếu move là Fire/Ice, giảm damage x0.5
    if move.move_type in ['Fire', 'Ice']:
        return type_multiplier * 0.5
    return type_multiplier

def water_bubble_multiplier(move, type_multiplier):
    # Nếu move là Fire, giảm damage x0.5
    if move.move_type == 'Fire':
        return type_multiplier * 0.5
    return type_multiplier

def punk_rock_multiplier(move, base_power, is_user):
    # Nếu move là sound-based, x1.3 (user) hoặc x0.5 (target)
    if getattr(move, 'is_sound', False):
        return int(base_power * (1.3 if is_user else 0.5))
    return base_power


# Load abilities.json safely: only extract name, rating, num, flags
import os, re
ABILITIES_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'abilities.json')
ABILITIES = {}
with open(ABILITIES_PATH, encoding='utf-8') as f:
    raw = f.read()
    # Remove comments and export
    raw = re.sub(r'/\*.*?\*/', '', raw, flags=re.DOTALL)
    raw = re.sub(r'export const Abilities:.*?=\s*', '', raw)
    raw = raw.strip()
    # Only keep main object content
    start = raw.find('{')
    end = raw.rfind('}')
    raw = raw[start+1:end]
    # Split by ability blocks
    abilities = re.split(r'\n\s*([a-zA-Z0-9_]+):\s*{', '\n' + raw)
    for i in range(1, len(abilities), 2):
        key = abilities[i]
        block = abilities[i+1]
        # Extract fields
        name = re.search(r'name:\s*"([^"]+)"', block)
        rating = re.search(r'rating:\s*([\d\.]+)', block)
        num = re.search(r'num:\s*(\d+)', block)
        flags = re.search(r'flags:\s*({[^}]*})', block)
        ABILITIES[key] = {
            'name': name.group(1) if name else key,
            'rating': float(rating.group(1)) if rating else None,
            'num': int(num.group(1)) if num else None,
            'flags': flags.group(1) if flags else '{}',
        }

# Map ability names to a stub effect function
# (All abilities return 1.0/no effect by default, except Blaze/Intimidate for demo)

# Default: no effect
def default_ability(*args, **kwargs):
    return 1.0

# Blaze: Fire moves x1.5 when HP <= 1/3
def blaze_boost(attacker, move):
    if move.move_type == 'Fire' and attacker.current_hp <= attacker.max_hp // 3:
        return 1.5
    return 1.0

# Torrent: Water moves x1.5 when HP <= 1/3
def torrent_boost(attacker, move):
    if move.move_type == 'Water' and attacker.current_hp <= attacker.max_hp // 3:
        return 1.5
    return 1.0

# Intimidate: Lower foe's Attack on switch-in
def intimidate_on_switch_in(defender):
    defender.attack = max(1, int(defender.attack * 2 / 3))

# Swift Swim: Double Speed in rain (pass weather as arg)
def swift_swim_speed(pokemon, weather):
    if weather == 'Rain':
        return 2.0
    return 1.0

def blaze_boost(attacker, move):
    if move.move_type == 'Fire' and attacker.current_hp <= attacker.max_hp // 3:
        return 1.5
    return 1.0

def intimidate_on_switch_in(defender):
    defender.attack = max(1, int(defender.attack * 2 / 3))


# Map all abilities to their effect function (expandable)
ABILITY_EFFECTS = {}
for ab_key, ab_data in ABILITIES.items():
    name = ab_data.get('name', ab_key)
    # --- DAMAGE MODIFIERS ---
    if name == 'Blaze':
        ABILITY_EFFECTS[name] = blaze_boost
    elif name == 'Torrent':
        ABILITY_EFFECTS[name] = torrent_boost
    elif name == 'Intimidate':
        ABILITY_EFFECTS[name] = intimidate_on_switch_in
    elif name == 'Swift Swim':
        ABILITY_EFFECTS[name] = swift_swim_speed
    elif name == 'Chlorophyll':
        ABILITY_EFFECTS[name] = chlorophyll_speed
    elif name == 'Sand Rush':
        ABILITY_EFFECTS[name] = sand_rush_speed
    elif name == 'Slush Rush':
        ABILITY_EFFECTS[name] = slush_rush_speed
    elif name == 'Quick Feet':
        ABILITY_EFFECTS[name] = quick_feet_speed
    elif name == 'Unburden':
        ABILITY_EFFECTS[name] = unburden_speed
    elif name == 'Speed Boost':
        ABILITY_EFFECTS[name] = speed_boost_speed
    elif name == 'Surge Surfer':
        ABILITY_EFFECTS[name] = surge_surfer_speed
    # --- DEFENSE MODIFIERS ---
    elif name == 'Marvel Scale':
        ABILITY_EFFECTS[name] = marvel_scale_defense
    elif name == 'Multiscale':
        ABILITY_EFFECTS[name] = multiscale_damage_multiplier
    elif name == 'Fur Coat':
        ABILITY_EFFECTS[name] = fur_coat_defense
    elif name == 'Ice Scales':
        ABILITY_EFFECTS[name] = ice_scales_spdef
    elif name == 'Dauntless Shield':
        ABILITY_EFFECTS[name] = dauntless_shield_defense
    elif name == 'Fluffy':
        ABILITY_EFFECTS[name] = fluffy_damage_multiplier
    elif name == 'Shadow Shield':
        ABILITY_EFFECTS[name] = shadow_shield_damage_multiplier
    elif name == 'Weak Armor':
        ABILITY_EFFECTS[name] = weak_armor_defense
    elif name == 'Heatproof':
        ABILITY_EFFECTS[name] = heatproof_damage_multiplier
    elif name == 'Water Compaction':
        ABILITY_EFFECTS[name] = water_compaction_defense
    elif name == 'Well-Baked Body':
        ABILITY_EFFECTS[name] = well_baked_body_defense
    # --- RECOVERY ABILITIES ---
    elif name == 'Regenerator':
        ABILITY_EFFECTS[name] = regenerator_heal
    elif name == 'Water Absorb':
        ABILITY_EFFECTS[name] = water_absorb_heal
    elif name == 'Volt Absorb':
        ABILITY_EFFECTS[name] = volt_absorb_heal
    elif name == 'Dry Skin':
        ABILITY_EFFECTS[name] = dry_skin_heal
    elif name == 'Ice Body':
        ABILITY_EFFECTS[name] = ice_body_heal
    elif name == 'Rain Dish':
        ABILITY_EFFECTS[name] = rain_dish_heal
    elif name == 'Harvest':
        ABILITY_EFFECTS[name] = harvest_berry
    elif name == 'Healer':
        ABILITY_EFFECTS[name] = healer_cure
    elif name == 'Hydration':
        ABILITY_EFFECTS[name] = hydration_cure
    elif name == 'Natural Cure':
        ABILITY_EFFECTS[name] = natural_cure_cure
    elif name == 'Shed Skin':
        ABILITY_EFFECTS[name] = shed_skin_cure
    elif name == 'Cheek Pouch':
        ABILITY_EFFECTS[name] = cheek_pouch_heal
    elif name == 'Ripen':
        ABILITY_EFFECTS[name] = ripen_berry_effect
    elif name == 'Magic Guard':
        ABILITY_EFFECTS[name] = magic_guard_heal
    # --- IMMUNITY ABILITIES ---
    elif name == 'Immunity':
        ABILITY_EFFECTS[name] = immunity_status
    elif name == 'Water Veil':
        ABILITY_EFFECTS[name] = water_veil_status
    elif name == 'Limber':
        ABILITY_EFFECTS[name] = limber_status
    elif name == 'Insomnia':
        ABILITY_EFFECTS[name] = insomnia_status
    elif name == 'Vital Spirit':
        ABILITY_EFFECTS[name] = vital_spirit_status
    elif name == 'Own Tempo':
        ABILITY_EFFECTS[name] = own_tempo_status
    elif name == 'Oblivious':
        ABILITY_EFFECTS[name] = oblivious_status
    elif name == 'Cloud Nine':
        ABILITY_EFFECTS[name] = cloud_nine_negate_weather
    elif name == 'Air Lock':
        ABILITY_EFFECTS[name] = air_lock_negate_weather
    elif name == 'Magma Armor':
        ABILITY_EFFECTS[name] = magma_armor_status
    elif name == 'Sand Veil':
        ABILITY_EFFECTS[name] = sand_veil_accuracy
    elif name == 'Snow Cloak':
        ABILITY_EFFECTS[name] = snow_cloak_accuracy
    elif name == 'Flower Veil':
        ABILITY_EFFECTS[name] = flower_veil_status
    elif name == 'Leaf Guard':
        ABILITY_EFFECTS[name] = leaf_guard_status
    elif name == 'Shield Dust':
        ABILITY_EFFECTS[name] = shield_dust_secondary
    elif name == 'Overcoat':
        ABILITY_EFFECTS[name] = overcoat_status
    elif name == 'Soundproof':
        ABILITY_EFFECTS[name] = soundproof_status
    elif name == 'Sap Sipper':
        ABILITY_EFFECTS[name] = sap_sipper_status
    elif name == 'Lightning Rod':
        ABILITY_EFFECTS[name] = lightning_rod_status
    elif name == 'Motor Drive':
        ABILITY_EFFECTS[name] = motor_drive_status
    elif name == 'Storm Drain':
        ABILITY_EFFECTS[name] = storm_drain_status
    elif name == 'Flash Fire':
        ABILITY_EFFECTS[name] = flash_fire_status
    elif name == 'Thick Fat':
        ABILITY_EFFECTS[name] = thick_fat_status
    elif name == 'Wonder Guard':
        ABILITY_EFFECTS[name] = wonder_guard_status
    elif name == 'Adaptability':
        ABILITY_EFFECTS[name] = adaptability_stab
    elif name == 'Sheer Force':
        ABILITY_EFFECTS[name] = sheer_force_boost
    elif name == 'Guts':
        ABILITY_EFFECTS[name] = guts_boost
    elif name in ['Huge Power', 'Pure Power']:
        ABILITY_EFFECTS[name] = huge_power_boost
    elif name == 'Solar Power':
        ABILITY_EFFECTS[name] = solar_power_boost
    elif name == 'Hustle':
        ABILITY_EFFECTS[name] = hustle_boost
    elif name == 'Tinted Lens':
        ABILITY_EFFECTS[name] = tinted_lens_multiplier
    elif name == 'Technician':
        ABILITY_EFFECTS[name] = technician_boost
    elif name in ['Filter', 'Solid Rock', 'Prism Armor']:
        ABILITY_EFFECTS[name] = filter_solidrock_prismarmor_multiplier
    elif name == 'Thick Fat':
        ABILITY_EFFECTS[name] = thick_fat_multiplier
    elif name == 'Water Bubble':
        ABILITY_EFFECTS[name] = water_bubble_multiplier
    elif name == 'Punk Rock':
        ABILITY_EFFECTS[name] = punk_rock_multiplier
    elif name in ['Mold Breaker', 'Teravolt', 'Turboblaze']:
        ABILITY_EFFECTS[name] = mold_breaker_ignore_immunity
    elif name == 'Synchronize':
        ABILITY_EFFECTS[name] = synchronize_status
    elif name == 'Poison Heal':
        ABILITY_EFFECTS[name] = poison_heal_heal
    elif name == 'Flame Body':
        ABILITY_EFFECTS[name] = flame_body_status
    elif name == 'Effect Spore':
        ABILITY_EFFECTS[name] = effect_spore_status
    elif name == 'Static':
        ABILITY_EFFECTS[name] = static_status
    elif name == 'Cute Charm':
        ABILITY_EFFECTS[name] = cute_charm_status
    elif name == 'Cursed Body':
        ABILITY_EFFECTS[name] = cursed_body_status
    elif name == 'Mummy':
        ABILITY_EFFECTS[name] = mummy_status
    elif name == 'Gooey':
        ABILITY_EFFECTS[name] = gooey_status
    elif name == 'No Guard':
        ABILITY_EFFECTS[name] = no_guard_accuracy
    elif name == 'Drizzle':
        ABILITY_EFFECTS[name] = drizzle_weather
    elif name == 'Drought':
        ABILITY_EFFECTS[name] = drought_weather
    elif name == 'Sand Stream':
        ABILITY_EFFECTS[name] = sand_stream_weather
    elif name == 'Snow Warning':
        ABILITY_EFFECTS[name] = snow_warning_weather
    elif name == 'Forecast':
        ABILITY_EFFECTS[name] = forecast_weather
    elif name == 'Bad Dreams':
        ABILITY_EFFECTS[name] = bad_dreams_damage
    elif name == 'Rough Skin':
        ABILITY_EFFECTS[name] = rough_skin_damage
    elif name == 'Iron Barbs':
        ABILITY_EFFECTS[name] = iron_barbs_damage
    elif name == 'Aftermath':
        ABILITY_EFFECTS[name] = aftermath_damage
    elif name == 'Beast Boost':
        ABILITY_EFFECTS[name] = beast_boost_stat
    elif name == 'Moxie':
        ABILITY_EFFECTS[name] = moxie_boost
    elif name == 'Chilling Neigh':
        ABILITY_EFFECTS[name] = chilling_neigh_boost
    elif name == 'Grim Neigh':
        ABILITY_EFFECTS[name] = grim_neigh_boost
    elif name == 'Soul-Heart':
        ABILITY_EFFECTS[name] = soul_heart_boost
    elif name == 'Competitive':
        ABILITY_EFFECTS[name] = competitive_boost
    elif name == 'Defiant':
        ABILITY_EFFECTS[name] = defiant_boost
    elif name == 'Download':
        ABILITY_EFFECTS[name] = download_boost
    elif name == 'Moody':
        ABILITY_EFFECTS[name] = moody_boost
    elif name == 'Simple':
        ABILITY_EFFECTS[name] = simple_boost
    elif name == 'Tablets of Ruin':
        ABILITY_EFFECTS[name] = tablets_of_ruin_effect
    elif name == 'Sword of Ruin':
        ABILITY_EFFECTS[name] = sword_of_ruin_effect
    elif name == 'Vessel of Ruin':
        ABILITY_EFFECTS[name] = vessel_of_ruin_effect
    elif name == 'Beads of Ruin':
        ABILITY_EFFECTS[name] = beads_of_ruin_effect
    elif name == 'As One':
        ABILITY_EFFECTS[name] = as_one_effect
    elif name == 'comatose':
        ABILITY_EFFECTS[name] = comatose_effect
    elif name == 'Schooling':
        ABILITY_EFFECTS[name] = schooling_effect
    elif name == 'Battle Bond':
        ABILITY_EFFECTS[name] = battle_bond_effect
    elif name == 'RKS System':
        ABILITY_EFFECTS[name] = rks_system_effect
    elif name == 'Multitype':
        ABILITY_EFFECTS[name] = multitype_effect
    elif name == 'Ice Face':
        ABILITY_EFFECTS[name] = ice_face_effect
    elif name == 'Zen Mode':
        ABILITY_EFFECTS[name] = zen_mode_effect
    elif name == 'Shields Down':
        ABILITY_EFFECTS[name] = shields_down_effect
    elif name == 'Stance Change':
        ABILITY_EFFECTS[name] = stance_change_effect
    elif name == 'Aerilate':
        ABILITY_EFFECTS[name] = aerilate_effect
    elif name == 'Analytic':
        ABILITY_EFFECTS[name] = analytic_effect
    elif name == 'Anger Point':
        ABILITY_EFFECTS[name] = anger_point_effect
    elif name == 'Anger Shell':
        ABILITY_EFFECTS[name] = anger_shell_effect
    elif name == 'Anticipation':
        ABILITY_EFFECTS[name] = anticipation_effect
    elif name == 'Arena Trap':
        ABILITY_EFFECTS[name] = arena_trap_effect
    elif name == 'Armor Tail':
        ABILITY_EFFECTS[name] = armor_tail_effect
    elif name == 'Aroma Veil':
        ABILITY_EFFECTS[name] = aroma_veil_effect
    elif name == 'Aura Break':
        ABILITY_EFFECTS[name] = aura_break_effect
    elif name == 'Ball Fetch':
        ABILITY_EFFECTS[name] = ball_fetch_effect
    elif name == 'Battery':
        ABILITY_EFFECTS[name] = battery_effect
    elif name == 'Battle Armor':
        ABILITY_EFFECTS[name] = battle_armor_effect
    elif name == 'Berserk':
        ABILITY_EFFECTS[name] = berserk_effect
    elif name == 'Big Pecks':
        ABILITY_EFFECTS[name] = big_pecks_effect
    elif name == 'Bulletproof':
        ABILITY_EFFECTS[name] = bulletproof_effect
    elif name == 'Clear Body':
        ABILITY_EFFECTS[name] = clear_body_effect
    elif name == 'Color Change':
        ABILITY_EFFECTS[name] = color_change_effect
    elif name == 'Commander':
        ABILITY_EFFECTS[name] = commander_effect
    elif name == 'Compound Eyes':
        ABILITY_EFFECTS[name] = compound_eyes_effect
    elif name == 'Contrary':
        ABILITY_EFFECTS[name] = contrary_effect
    elif name == 'Corrosion':
        ABILITY_EFFECTS[name] = corrosion_effect
    elif name == 'Costar':
        ABILITY_EFFECTS[name] = costar_effect
    elif name == 'Cotton Down':
        ABILITY_EFFECTS[name] = cotton_down_effect
    elif name == 'Cud Chew':
        ABILITY_EFFECTS[name] = cud_chew_effect
    elif name == 'Curious Medicine':
        ABILITY_EFFECTS[name] = curious_medicine_effect
    elif name == 'Damp':
        ABILITY_EFFECTS[name] = damp_effect
    elif name == 'Dancer':
        ABILITY_EFFECTS[name] = dancer_effect
    elif name == 'Dark Aura':
        ABILITY_EFFECTS[name] = dark_aura_effect
    elif name == 'Dazzling':
        ABILITY_EFFECTS[name] = dazzling_effect
    elif name == 'Defeatist':
        ABILITY_EFFECTS[name] = defeatist_effect
    elif name == 'Delta Stream':
        ABILITY_EFFECTS[name] = delta_stream_effect
    elif name == 'Desolate Land':
        ABILITY_EFFECTS[name] = desolate_land_effect
    elif name == 'Disguise':
        ABILITY_EFFECTS[name] = disguise_effect
    elif name == "Dragon's Maw":
        ABILITY_EFFECTS[name] = dragons_maw_effect
    elif name == 'Early Bird':
        ABILITY_EFFECTS[name] = early_bird_effect
    elif name == 'Earth Eater':
        ABILITY_EFFECTS[name] = earth_eater_effect
    elif name == 'Electric Surge':
        ABILITY_EFFECTS[name] = electric_surge_effect
    elif name == 'Electromorphosis':
        ABILITY_EFFECTS[name] = electromorphosis_effect
    elif name == 'Embody Aspect':
        ABILITY_EFFECTS[name] = embody_aspect_effect
    elif name == 'Emergency Exit':
        ABILITY_EFFECTS[name] = emergency_exit_effect
    elif name == 'Fairy Aura':
        ABILITY_EFFECTS[name] = fairy_aura_effect
    elif name == 'Flare Boost':
        ABILITY_EFFECTS[name] = flare_boost_effect
    elif name == 'Flower Gift':
        ABILITY_EFFECTS[name] = flower_gift_effect
    elif name == 'Forewarn':
        ABILITY_EFFECTS[name] = forewarn_effect
    elif name == 'Friend Guard':
        ABILITY_EFFECTS[name] = friend_guard_effect
    elif name == 'Frisk':
        ABILITY_EFFECTS[name] = frisk_effect
    elif name == 'Full Metal Body':
        ABILITY_EFFECTS[name] = full_metal_body_effect
    elif name == 'Gale Wings':
        ABILITY_EFFECTS[name] = gale_wings_effect
    elif name == 'Galvanize':
        ABILITY_EFFECTS[name] = galvanize_effect
    elif name == 'Gluttony':
        ABILITY_EFFECTS[name] = gluttony_effect
    elif name == 'Good as Gold':
        ABILITY_EFFECTS[name] = good_as_gold_effect
    elif name == 'Gorilla Tactics':
        ABILITY_EFFECTS[name] = gorilla_tactics_effect
    elif name == 'Grass Pelt':
        ABILITY_EFFECTS[name] = grass_pelt_effect
    elif name == 'Grassy Surge':
        ABILITY_EFFECTS[name] = grassy_surge_effect
    elif name == 'Guard Dog':
        ABILITY_EFFECTS[name] = guard_dog_effect
    elif name == 'Gulp Missile':
        ABILITY_EFFECTS[name] = gulp_missile_effect
    elif name == 'Hadron Engine':
        ABILITY_EFFECTS[name] = hadron_engine_effect
    elif name == 'Heavy Metal':
        ABILITY_EFFECTS[name] = heavy_metal_effect
    elif name == 'Honey Gather':
        ABILITY_EFFECTS[name] = honey_gather_effect
    elif name == 'Hospitality':
        ABILITY_EFFECTS[name] = hospitality_effect
    elif name == 'Hunger Switch':
        ABILITY_EFFECTS[name] = hunger_switch_effect
    elif name == 'Hyper Cutter':
        ABILITY_EFFECTS[name] = hyper_cutter_effect
    elif name == 'Illuminate':
        ABILITY_EFFECTS[name] = illuminate_effect
    elif name == 'Illusion':
        ABILITY_EFFECTS[name] = illusion_effect
    elif name == 'Imposter':
        ABILITY_EFFECTS[name] = imposter_effect
    elif name == 'Infiltrator':
        ABILITY_EFFECTS[name] = infiltrator_effect
    elif name == 'Innards Out':
        ABILITY_EFFECTS[name] = innards_out_effect
    elif name == 'Inner Focus':
        ABILITY_EFFECTS[name] = inner_focus_effect
    elif name == 'Intrepid Sword':
        ABILITY_EFFECTS[name] = intrepid_sword_effect
    elif name == 'Iron Fist':
        ABILITY_EFFECTS[name] = iron_fist_effect
    elif name == 'Justified':
        ABILITY_EFFECTS[name] = justified_effect
    elif name == 'Keen Eye':
        ABILITY_EFFECTS[name] = keen_eye_effect
    elif name == 'Klutz':
        ABILITY_EFFECTS[name] = klutz_effect
    elif name == 'Libero':
        ABILITY_EFFECTS[name] = libero_effect
    elif name == 'Light Metal':
        ABILITY_EFFECTS[name] = light_metal_effect
    elif name == 'Limber':
        ABILITY_EFFECTS[name] = limber_status
    elif name == 'Lingering Aroma':
        ABILITY_EFFECTS[name] = lingering_aroma_effect
    elif name == 'Liquid Ooze':
        ABILITY_EFFECTS[name] = liquid_ooze_effect
    elif name == 'Liquid Voice':
        ABILITY_EFFECTS[name] = liquid_voice_effect
    elif name == 'Long Reach':
        ABILITY_EFFECTS[name] = long_reach_effect
    elif name == 'Magic Bounce':
        ABILITY_EFFECTS[name] = magic_bounce_effect
    elif name == 'Magician':
        ABILITY_EFFECTS[name] = magician_effect
    elif name == 'Magnet Pull':
        ABILITY_EFFECTS[name] = magnet_pull_effect
    elif name == 'Mega Launcher':
        ABILITY_EFFECTS[name] = mega_launcher_effect
    elif name == 'Merciless':
        ABILITY_EFFECTS[name] = merciless_effect
    elif name == 'Mimicry':
        ABILITY_EFFECTS[name] = mimicry_effect
    elif name == "Mind's Eye":
        ABILITY_EFFECTS[name] = minds_eye_effect
    elif name == 'Minus':
        ABILITY_EFFECTS[name] = minus_effect
    elif name == 'Mirror Armor':
        ABILITY_EFFECTS[name] = mirror_armor_effect
    elif name == 'Misty Surge':
        ABILITY_EFFECTS[name] = misty_surge_effect
    elif name == 'Mycelium Might':
        ABILITY_EFFECTS[name] = mycelium_might_effect
    elif name == 'Neuroforce':
        ABILITY_EFFECTS[name] = neuroforce_effect
    elif name == 'Neutralizing Gas':
        ABILITY_EFFECTS[name] = neutralizing_gas_effect
    elif name == 'Normalize':
        ABILITY_EFFECTS[name] = normalize_effect
    elif name == 'Opportunist':
        ABILITY_EFFECTS[name] = opportunist_effect
    elif name == 'Orichalcum Pulse':
        ABILITY_EFFECTS[name] = orichalcum_pulse_effect
    elif name == 'Overcoat':
        ABILITY_EFFECTS[name] = overcoat_effect
    elif name == 'Overgrow':
        ABILITY_EFFECTS[name] = overgrow_effect
    elif name == 'Parental Bond':
        ABILITY_EFFECTS[name] = parental_bond_effect
    elif name == 'Pastel Veil':
        ABILITY_EFFECTS[name] = pastel_veil_effect
    elif name == 'Perish Body':
        ABILITY_EFFECTS[name] = perish_body_effect
    elif name == 'Pickpocket':
        ABILITY_EFFECTS[name] = pickpocket_effect
    elif name == 'Pickup':
        ABILITY_EFFECTS[name] = pickup_effect
    elif name == 'Pixilate':
        ABILITY_EFFECTS[name] = pixilate_effect
    elif name == 'Plus':
        ABILITY_EFFECTS[name] = plus_effect
    elif name == 'Poison Point':
        ABILITY_EFFECTS[name] = poison_point_effect
    elif name == 'Poison Puppeteer':
        ABILITY_EFFECTS[name] = poison_puppeteer_effect
    elif name == 'Poison Touch':
        ABILITY_EFFECTS[name] = poison_touch_effect
    elif name == 'Power Construct':
        ABILITY_EFFECTS[name] = power_construct_effect
    elif name == 'Power of Alchemy':
        ABILITY_EFFECTS[name] = power_of_alchemy_effect
    elif name == 'Power Spot':
        ABILITY_EFFECTS[name] = power_spot_effect
    elif name == 'Prankster':
        ABILITY_EFFECTS[name] = prankster_effect
    elif name == 'Pressure':
        ABILITY_EFFECTS[name] = pressure_effect
    elif name == 'Primordial Sea':
        ABILITY_EFFECTS[name] = primordial_sea_effect
    elif name == 'Propeller Tail':
        ABILITY_EFFECTS[name] = propeller_tail_effect
    elif name == 'Protean':
        ABILITY_EFFECTS[name] = protean_effect
    elif name == 'Protosynthesis':
        ABILITY_EFFECTS[name] = protosynthesis_effect
    elif name == 'Psychic Surge':
        ABILITY_EFFECTS[name] = psychic_surge_effect
    elif name == 'Purifying Salt':
        ABILITY_EFFECTS[name] = purifying_salt_effect
    elif name == 'Quark Drive':
        ABILITY_EFFECTS[name] = quark_drive_effect
    elif name == 'Queenly Majesty':
        ABILITY_EFFECTS[name] = queenly_majesty_effect
    elif name == 'Quick Draw':
        ABILITY_EFFECTS[name] = quick_draw_effect
    elif name == 'Rattled':
        ABILITY_EFFECTS[name] = rattled_effect
    elif name == 'Receiver':
        ABILITY_EFFECTS[name] = receiver_effect
    elif name == 'Reckless':
        ABILITY_EFFECTS[name] = reckless_effect
    elif name == 'Refrigerate':
        ABILITY_EFFECTS[name] = refrigerate_effect
    elif name == 'Rivalry':
        ABILITY_EFFECTS[name] = rivalry_effect
    elif name == 'Rock Head':
        ABILITY_EFFECTS[name] = rock_head_effect
    elif name == 'Rocky Payload':
        ABILITY_EFFECTS[name] = rocky_payload_effect
    elif name == 'Run Away':
        ABILITY_EFFECTS[name] = run_away_effect
    elif name == 'Sand Force':
        ABILITY_EFFECTS[name] = sand_force_effect
    elif name == 'Sand Spit':
        ABILITY_EFFECTS[name] = sand_spit_effect
    elif name == 'Screen Cleaner':
        ABILITY_EFFECTS[name] = screen_cleaner_effect
    elif name == 'Seed Sower':
        ABILITY_EFFECTS[name] = seed_sower_effect
    elif name == 'Serene Grace':
        ABILITY_EFFECTS[name] = serene_grace_effect
    elif name == 'Shadow Tag':
        ABILITY_EFFECTS[name] = shadow_tag_effect
    elif name == 'Sharpness':
        ABILITY_EFFECTS[name] = sharpness_effect
    elif name == 'Shell Armor':
        ABILITY_EFFECTS[name] = shell_armor_effect
    elif name == 'Skill Link':
        ABILITY_EFFECTS[name] = skill_link_effect
    elif name == 'Slow Start':
        ABILITY_EFFECTS[name] = slow_start_effect
    elif name == 'Sniper':
        ABILITY_EFFECTS[name] = sniper_effect
    elif name == 'Stakeout':
        ABILITY_EFFECTS[name] = stakeout_effect
    elif name == 'Stall':
        ABILITY_EFFECTS[name] = stall_effect
    elif name == 'Stalwart':
        ABILITY_EFFECTS[name] = stalwart_effect
    elif name == 'Stamina':
        ABILITY_EFFECTS[name] = stamina_effect
    elif name == 'Steam Engine':
        ABILITY_EFFECTS[name] = steam_engine_effect
    elif name == 'Steelworker':
        ABILITY_EFFECTS[name] = steelworker_effect
    elif name == 'Steely Spirit':
        ABILITY_EFFECTS[name] = steely_spirit_effect
    elif name == 'Stench':
        ABILITY_EFFECTS[name] = stench_effect
    elif name == 'Sticky Hold':
        ABILITY_EFFECTS[name] = sticky_hold_effect
    elif name == 'Strong Jaw':
        ABILITY_EFFECTS[name] = strong_jaw_effect
    elif name == 'Sturdy':
        ABILITY_EFFECTS[name] = sturdy_effect
    elif name == 'Suction Cups':
        ABILITY_EFFECTS[name] = suction_cups_effect
    elif name == 'Super Luck':
        ABILITY_EFFECTS[name] = super_luck_effect
    elif name == 'Supersweet Syrup':
        ABILITY_EFFECTS[name] = supersweet_syrup_effect
    elif name == 'Supreme Overlord':
        ABILITY_EFFECTS[name] = supreme_overlord_effect
    elif name == 'Swarm':
        ABILITY_EFFECTS[name] = swarm_effect
    elif name == 'Sweet Veil':
        ABILITY_EFFECTS[name] = sweet_veil_effect
    elif name == 'Symbiosis':
        ABILITY_EFFECTS[name] = symbiosis_effect
    elif name == 'Tangled Feet':
        ABILITY_EFFECTS[name] = tangled_feet_effect
    elif name == 'Tangling Hair':
        ABILITY_EFFECTS[name] = tangling_hair_effect
    elif name == 'Telepathy':
        ABILITY_EFFECTS[name] = telepathy_effect
    elif name == 'Tera Shell':
        ABILITY_EFFECTS[name] = tera_shell_effect
    elif name == 'Tera Shift':
        ABILITY_EFFECTS[name] = tera_shift_effect
    elif name == 'Terraform Zero':
        ABILITY_EFFECTS[name] = terraform_zero_effect
    elif name == 'Thermal Exchange':
        ABILITY_EFFECTS[name] = thermal_exchange_effect
    elif name == 'Tough Claws':
        ABILITY_EFFECTS[name] = tough_claws_effect
    elif name == 'Toxic Boost':
        ABILITY_EFFECTS[name] = toxic_boost_effect
    elif name == 'Toxic Chain':
        ABILITY_EFFECTS[name] = toxic_chain_effect
    elif name == 'Toxic Debris':
        ABILITY_EFFECTS[name] = toxic_debris_effect
    elif name == 'Trace':
        ABILITY_EFFECTS[name] = trace_effect
    elif name == 'Transistor':
        ABILITY_EFFECTS[name] = transistor_effect
    elif name == 'Triage':
        ABILITY_EFFECTS[name] = triage_effect
    elif name == 'Truant':
        ABILITY_EFFECTS[name] = truant_effect
    elif name == 'Unaware':
        ABILITY_EFFECTS[name] = unaware_effect
    elif name == 'Unnerve':
        ABILITY_EFFECTS[name] = unnerve_effect
    elif name == 'Unseen Fist':
        ABILITY_EFFECTS[name] = unseen_fist_effect
    elif name == 'Victory Star':
        ABILITY_EFFECTS[name] = victory_star_effect
    elif name == 'Wandering Spirit':
        ABILITY_EFFECTS[name] = wandering_spirit_effect
    elif name == 'Water Bubble':
        ABILITY_EFFECTS[name] = water_bubble_effect
    elif name == 'White Smoke':
        ABILITY_EFFECTS[name] = white_smoke_effect
    elif name == 'Wimp Out':
        ABILITY_EFFECTS[name] = wimp_out_effect
    elif name == 'Wind Power':
        ABILITY_EFFECTS[name] = wind_power_effect
    elif name == 'Wind Rider':
        ABILITY_EFFECTS[name] = wind_rider_effect
    elif name == 'Wonder Skin':
        ABILITY_EFFECTS[name] = wonder_skin_effect
    elif name == 'Zero to Hero':
        ABILITY_EFFECTS[name] = zero_to_hero_effect
    else:
        ABILITY_EFFECTS[name] = default_ability

def get_ability_effect(ability_name):
    return ABILITY_EFFECTS.get(ability_name, default_ability)
