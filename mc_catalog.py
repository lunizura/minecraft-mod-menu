"""
mc_catalog.py - Minecraft Item, Enchantment, Attribute, Potion, and GameRule Catalog
Provides comprehensive presets and metadata for Minecraft 1.20+ and 26.x.
"""

from __future__ import annotations
from typing import Dict, List, Any, Optional

# ==========================================
# 1. ATTRIBUTES
# ==========================================
ATTRIBUTES: Dict[str, Dict[str, Any]] = {
    "minecraft:max_health": {
        "name": "Max Health",
        "default": 20.0,
        "min": 1.0,
        "max": 200.0,
        "step": 2.0,
        "desc": "Player maximum hearts (20.0 = 10 Hearts, 200.0 = 100 Hearts)",
    },
    "minecraft:movement_speed": {
        "name": "Movement Speed",
        "default": 0.10,
        "min": 0.05,
        "max": 0.60,
        "step": 0.02,
        "desc": "Walking & sprinting velocity multiplier (0.10 = 1x, 0.50 = 5x)",
    },
    "minecraft:attack_damage": {
        "name": "Attack Damage",
        "default": 1.0,
        "min": 1.0,
        "max": 500.0,
        "step": 5.0,
        "desc": "Bare fist and base melee strike strength (500.0 = One-Punch)",
    },
    "minecraft:attack_speed": {
        "name": "Attack Speed",
        "default": 4.0,
        "min": 1.0,
        "max": 40.0,
        "step": 1.0,
        "desc": "Weapon attack cooldown recovery speed (40.0 = Spam-Click)",
    },
    "minecraft:block_interaction_range": {
        "name": "Block Reach Range",
        "default": 4.5,
        "min": 4.5,
        "max": 32.0,
        "step": 0.5,
        "desc": "Distance in blocks for mining and block placement",
    },
    "minecraft:entity_interaction_range": {
        "name": "Entity Reach (Combat)",
        "default": 3.0,
        "min": 3.0,
        "max": 24.0,
        "step": 0.5,
        "desc": "Distance in blocks for hitting and interacting with entities",
    },
    "minecraft:block_break_speed": {
        "name": "Mining Break Speed",
        "default": 1.0,
        "min": 1.0,
        "max": 50.0,
        "step": 1.0,
        "desc": "Haste-like mining speed multiplier on all block types",
    },
    "minecraft:jump_strength": {
        "name": "Jump Strength",
        "default": 0.42,
        "min": 0.42,
        "max": 2.5,
        "step": 0.1,
        "desc": "Vertical jump leap force (0.42 = 1.25 blocks, 2.0 = 15+ blocks)",
    },
    "minecraft:safe_fall_distance": {
        "name": "Safe Fall Distance",
        "default": 3.0,
        "min": 3.0,
        "max": 1000.0,
        "step": 10.0,
        "desc": "Blocks fallen before taking fall damage (1000.0 = Immune)",
    },
    "minecraft:step_height": {
        "name": "Step Height",
        "default": 0.6,
        "min": 0.6,
        "max": 3.0,
        "step": 0.2,
        "desc": "Blocks player walks up without jumping (1.0 = full blocks, 2.0 = fences)",
    },
    "minecraft:scale": {
        "name": "Player Scale",
        "default": 1.0,
        "min": 0.1,
        "max": 8.0,
        "step": 0.1,
        "desc": "Player physical entity height and hitbox scale (0.2 = Ant, 4.0 = Titan)",
    },
    "minecraft:armor": {
        "name": "Innate Armor",
        "default": 0.0,
        "min": 0.0,
        "max": 30.0,
        "step": 2.0,
        "desc": "Natural defense without wearing armor (30.0 = Full Netherite skin)",
    },
    "minecraft:armor_toughness": {
        "name": "Innate Armor Toughness",
        "default": 0.0,
        "min": 0.0,
        "max": 30.0,
        "step": 2.0,
        "desc": "Mitigates heavy boss attacks from piercing armor",
    },
    "minecraft:luck": {
        "name": "Player Luck",
        "default": 0.0,
        "min": 0.0,
        "max": 100.0,
        "step": 5.0,
        "desc": "Increases chance of high-tier loot from fishing and dungeon chests",
    },
    "minecraft:oxygen_bonus": {
        "name": "Oxygen Bonus",
        "default": 0.0,
        "min": 0.0,
        "max": 100.0,
        "step": 5.0,
        "desc": "Extends underwater breath holding timer indefinitely",
    },
    "minecraft:gravity": {
        "name": "Gravity Force",
        "default": 0.08,
        "min": 0.005,
        "max": 0.50,
        "step": 0.01,
        "desc": "Gravity downward acceleration (0.01 = Moon Low-G / Glide, 0.08 = Earth)",
    },
}

# ==========================================
# 2. ENCHANTMENTS
# ==========================================
ENCHANTMENTS: Dict[str, Dict[str, Any]] = {
    "minecraft:sharpness": {"name": "Sharpness", "max_vanilla": 5, "category": "Weapon"},
    "minecraft:smite": {"name": "Smite", "max_vanilla": 5, "category": "Weapon"},
    "minecraft:bane_of_arthropods": {"name": "Bane of Arthropods", "max_vanilla": 5, "category": "Weapon"},
    "minecraft:knockback": {"name": "Knockback", "max_vanilla": 2, "category": "Weapon"},
    "minecraft:fire_aspect": {"name": "Fire Aspect", "max_vanilla": 2, "category": "Weapon"},
    "minecraft:looting": {"name": "Looting", "max_vanilla": 3, "category": "Weapon"},
    "minecraft:sweeping_edge": {"name": "Sweeping Edge", "max_vanilla": 3, "category": "Weapon"},
    "minecraft:unbreaking": {"name": "Unbreaking", "max_vanilla": 3, "category": "Universal"},
    "minecraft:mending": {"name": "Mending", "max_vanilla": 1, "category": "Universal"},
    "minecraft:efficiency": {"name": "Efficiency", "max_vanilla": 5, "category": "Tool"},
    "minecraft:silk_touch": {"name": "Silk Touch", "max_vanilla": 1, "category": "Tool"},
    "minecraft:fortune": {"name": "Fortune", "max_vanilla": 3, "category": "Tool"},
    "minecraft:power": {"name": "Power", "max_vanilla": 5, "category": "Bow"},
    "minecraft:punch": {"name": "Punch", "max_vanilla": 2, "category": "Bow"},
    "minecraft:flame": {"name": "Flame", "max_vanilla": 1, "category": "Bow"},
    "minecraft:infinity": {"name": "Infinity", "max_vanilla": 1, "category": "Bow"},
    "minecraft:luck_of_the_sea": {"name": "Luck of the Sea", "max_vanilla": 3, "category": "Tool"},
    "minecraft:lure": {"name": "Lure", "max_vanilla": 3, "category": "Tool"},
    "minecraft:protection": {"name": "Protection", "max_vanilla": 4, "category": "Armor"},
    "minecraft:fire_protection": {"name": "Fire Protection", "max_vanilla": 4, "category": "Armor"},
    "minecraft:feather_falling": {"name": "Feather Falling", "max_vanilla": 4, "category": "Armor"},
    "minecraft:blast_protection": {"name": "Blast Protection", "max_vanilla": 4, "category": "Armor"},
    "minecraft:projectile_protection": {"name": "Projectile Protection", "max_vanilla": 4, "category": "Armor"},
    "minecraft:respiration": {"name": "Respiration", "max_vanilla": 3, "category": "Armor"},
    "minecraft:aqua_affinity": {"name": "Aqua Affinity", "max_vanilla": 1, "category": "Armor"},
    "minecraft:thorns": {"name": "Thorns", "max_vanilla": 3, "category": "Armor"},
    "minecraft:depth_strider": {"name": "Depth Strider", "max_vanilla": 3, "category": "Armor"},
    "minecraft:frost_walker": {"name": "Frost Walker", "max_vanilla": 2, "category": "Armor"},
    "minecraft:soul_speed": {"name": "Soul Speed", "max_vanilla": 3, "category": "Armor"},
    "minecraft:swift_sneak": {"name": "Swift Sneak", "max_vanilla": 3, "category": "Armor"},
    "minecraft:loyalty": {"name": "Loyalty", "max_vanilla": 3, "category": "Trident"},
    "minecraft:impaling": {"name": "Impaling", "max_vanilla": 5, "category": "Trident"},
    "minecraft:riptide": {"name": "Riptide", "max_vanilla": 3, "category": "Trident"},
    "minecraft:channeling": {"name": "Channeling", "max_vanilla": 1, "category": "Trident"},
    "minecraft:multishot": {"name": "Multishot", "max_vanilla": 1, "category": "Crossbow"},
    "minecraft:quick_charge": {"name": "Quick Charge", "max_vanilla": 3, "category": "Crossbow"},
    "minecraft:piercing": {"name": "Piercing", "max_vanilla": 4, "category": "Crossbow"},
    "minecraft:density": {"name": "Density", "max_vanilla": 5, "category": "Mace"},
    "minecraft:breach": {"name": "Breach", "max_vanilla": 4, "category": "Mace"},
    "minecraft:wind_burst": {"name": "Wind Burst", "max_vanilla": 3, "category": "Mace"},
}

# ==========================================
# 3. POTION EFFECTS
# ==========================================
POTIONS: Dict[str, Dict[str, Any]] = {
    "minecraft:night_vision": {"name": "Night Vision", "desc": "Total visibility in caves and pitch darkness"},
    "minecraft:haste": {"name": "Haste", "desc": "Accelerates mining and attack recovery"},
    "minecraft:resistance": {"name": "Resistance", "desc": "Reduces all incoming damage by 20% per level"},
    "minecraft:regeneration": {"name": "Regeneration", "desc": "Restores hearts continuously"},
    "minecraft:strength": {"name": "Strength", "desc": "Increases melee strike damage output"},
    "minecraft:speed": {"name": "Speed", "desc": "Increases field of view and sprint speed"},
    "minecraft:jump_boost": {"name": "Jump Boost", "desc": "Allows leaping higher and reduces fall damage"},
    "minecraft:water_breathing": {"name": "Water Breathing", "desc": "Prevents drowning underwater"},
    "minecraft:fire_resistance": {"name": "Fire Resistance", "desc": "Complete immunity to fire and lava"},
    "minecraft:conduit_power": {"name": "Conduit Power", "desc": "Underwater vision, haste, and breathing"},
    "minecraft:dolphins_grace": {"name": "Dolphin's Grace", "desc": "Extreme swimming velocity"},
    "minecraft:hero_of_the_village": {"name": "Hero of the Village", "desc": "Extreme discounts on villager trades"},
    "minecraft:luck": {"name": "Luck", "desc": "Increases fishing and loot table quality"},
    "minecraft:saturation": {"name": "Saturation", "desc": "Prevents hunger loss entirely"},
    "minecraft:invisibility": {"name": "Invisibility", "desc": "Hidden from mobs and players"},
    "minecraft:slow_falling": {"name": "Slow Falling", "desc": "Glide smoothly to ground with zero fall damage"},
    "minecraft:absorption": {"name": "Absorption", "desc": "Adds yellow bonus shield hearts"},
}

# ==========================================
# 4. GAME RULES
# ==========================================
GAME_RULES: Dict[str, Dict[str, Any]] = {
    "keep_inventory": {
        "names": ["keep_inventory", "minecraft:keep_inventory", "keepInventory"],
        "name": "Keep Inventory on Death",
        "desc": "Retain all inventory items, armor, and XP levels when dying",
        "default": False,
        "type": "bool",
    },
    "mob_griefing": {
        "names": ["mob_griefing", "minecraft:mob_griefing", "mobGriefing"],
        "name": "Mob Griefing",
        "desc": "Allow Creepers, Endermen, and Ghasts to destroy world blocks",
        "default": True,
        "type": "bool",
    },
    "fall_damage": {
        "names": ["fall_damage", "minecraft:fall_damage", "fallDamage"],
        "name": "Fall Damage",
        "desc": "Take kinetic impact damage when hitting the ground",
        "default": True,
        "type": "bool",
    },
    "fire_damage": {
        "names": ["fire_damage", "minecraft:fire_damage", "fireDamage"],
        "name": "Fire Damage",
        "desc": "Take damage from fire, lava, and burning",
        "default": True,
        "type": "bool",
    },
    "drowning_damage": {
        "names": ["drowning_damage", "minecraft:drowning_damage", "drowningDamage"],
        "name": "Drowning Damage",
        "desc": "Take damage when running out of oxygen underwater",
        "default": True,
        "type": "bool",
    },
    "freeze_damage": {
        "names": ["freeze_damage", "minecraft:freeze_damage", "freezeDamage"],
        "name": "Freeze Damage",
        "desc": "Take freezing damage when caught inside powder snow",
        "default": True,
        "type": "bool",
    },
    "immediate_respawn": {
        "names": ["immediate_respawn", "minecraft:immediate_respawn", "doImmediateRespawn"],
        "name": "Immediate Respawn",
        "desc": "Skip the death screen and instantly respawn",
        "default": False,
        "type": "bool",
    },
    "tnt_explodes": {
        "names": ["tnt_explodes", "minecraft:tnt_explodes", "tntExplodes"],
        "name": "TNT Explodes",
        "desc": "Allow ignited TNT and TNT minecarts to detonate",
        "default": True,
        "type": "bool",
    },
    "do_insomnia": {
        "names": ["minecraft:spawn_phantoms", "spawn_phantoms", "do_insomnia", "minecraft:do_insomnia", "doInsomnia"],
        "name": "Phantom Spawning (Insomnia)",
        "desc": "Spawn Phantoms after player stays awake for 3 in-game days",
        "default": True,
        "type": "bool",
    },
    "spawn_monsters": {
        "names": ["spawn_monsters", "minecraft:spawn_monsters", "doMobSpawning"],
        "name": "Monster Spawning",
        "desc": "Natural hostile mob spawning during the night and in caves",
        "default": True,
        "type": "bool",
    },
    "spawn_wandering_traders": {
        "names": ["spawn_wandering_traders", "minecraft:spawn_wandering_traders", "doTraderSpawning"],
        "name": "Wandering Trader Spawning",
        "desc": "Periodically spawn wandering traders with llamas near players",
        "default": True,
        "type": "bool",
    },
    "do_daylight_cycle": {
        "names": ["minecraft:advance_time", "advance_time", "do_daylight_cycle", "minecraft:do_daylight_cycle", "doDaylightCycle"],
        "name": "Daylight Cycle",
        "desc": "Sun and moon movement and time progression",
        "default": True,
        "type": "bool",
    },
    "do_weather_cycle": {
        "names": ["minecraft:advance_weather", "advance_weather", "do_weather_cycle", "minecraft:do_weather_cycle", "doWeatherCycle"],
        "name": "Weather Cycle",
        "desc": "Dynamic rain, thunder, and clear skies",
        "default": True,
        "type": "bool",
    },
    "pvp": {
        "names": ["minecraft:pvp", "pvp"],
        "name": "Player vs Player (PvP)",
        "desc": "Allow players to attack and damage each other",
        "default": True,
        "type": "bool",
    },
    "natural_regeneration": {
        "names": ["minecraft:natural_health_regeneration", "natural_health_regeneration", "naturalRegeneration"],
        "name": "Natural Health Regeneration",
        "desc": "Regenerate player hearts continuously when hunger bar is satisfied",
        "default": True,
        "type": "bool",
    },
    "show_death_messages": {
        "names": ["show_death_messages", "minecraft:show_death_messages", "showDeathMessages"],
        "name": "Show Death Messages",
        "desc": "Broadcast death causes to in-game chat",
        "default": True,
        "type": "bool",
    },
    "players_sleeping_percentage": {
        "names": ["players_sleeping_percentage", "minecraft:players_sleeping_percentage", "playersSleepingPercentage"],
        "name": "Sleeping Percentage",
        "desc": "Percentage of players required in bed to skip the night (0 = 1 player)",
        "default": 100,
        "type": "int",
    },
}

# ==========================================
# 5. ITEM CATALOG
# ==========================================
ITEMS_CATALOG: List[Dict[str, Any]] = [
    # God Weapons
    {"id": "minecraft:netherite_sword", "name": "Netherite Sword", "cat": "Weapons"},
    {"id": "minecraft:diamond_sword", "name": "Diamond Sword", "cat": "Weapons"},
    {"id": "minecraft:mace", "name": "Mace", "cat": "Weapons"},
    {"id": "minecraft:bow", "name": "Bow", "cat": "Weapons"},
    {"id": "minecraft:crossbow", "name": "Crossbow", "cat": "Weapons"},
    {"id": "minecraft:trident", "name": "Trident", "cat": "Weapons"},
    {"id": "minecraft:wind_charge", "name": "Wind Charge", "cat": "Weapons"},

    # God Tools
    {"id": "minecraft:netherite_pickaxe", "name": "Netherite Pickaxe", "cat": "Tools"},
    {"id": "minecraft:diamond_pickaxe", "name": "Diamond Pickaxe", "cat": "Tools"},
    {"id": "minecraft:netherite_axe", "name": "Netherite Axe", "cat": "Tools"},
    {"id": "minecraft:diamond_axe", "name": "Diamond Axe", "cat": "Tools"},
    {"id": "minecraft:netherite_shovel", "name": "Netherite Shovel", "cat": "Tools"},
    {"id": "minecraft:diamond_shovel", "name": "Diamond Shovel", "cat": "Tools"},
    {"id": "minecraft:netherite_hoe", "name": "Netherite Hoe", "cat": "Tools"},
    {"id": "minecraft:shears", "name": "Shears", "cat": "Tools"},
    {"id": "minecraft:flint_and_steel", "name": "Flint and Steel", "cat": "Tools"},
    {"id": "minecraft:fishing_rod", "name": "Fishing Rod", "cat": "Tools"},

    # God Armor
    {"id": "minecraft:netherite_helmet", "name": "Netherite Helmet", "cat": "Armor"},
    {"id": "minecraft:netherite_chestplate", "name": "Netherite Chestplate", "cat": "Armor"},
    {"id": "minecraft:netherite_leggings", "name": "Netherite Leggings", "cat": "Armor"},
    {"id": "minecraft:netherite_boots", "name": "Netherite Boots", "cat": "Armor"},
    {"id": "minecraft:diamond_helmet", "name": "Diamond Helmet", "cat": "Armor"},
    {"id": "minecraft:diamond_chestplate", "name": "Diamond Chestplate", "cat": "Armor"},
    {"id": "minecraft:diamond_leggings", "name": "Diamond Leggings", "cat": "Armor"},
    {"id": "minecraft:diamond_boots", "name": "Diamond Boots", "cat": "Armor"},
    {"id": "minecraft:elytra", "name": "Elytra Wings", "cat": "Armor"},
    {"id": "minecraft:turtle_helmet", "name": "Turtle Helmet", "cat": "Armor"},
    {"id": "minecraft:shield", "name": "Shield", "cat": "Armor"},

    # Valuables & Consumables
    {"id": "minecraft:enchanted_golden_apple", "name": "Enchanted Golden Apple", "cat": "Valuables"},
    {"id": "minecraft:golden_apple", "name": "Golden Apple", "cat": "Valuables"},
    {"id": "minecraft:totem_of_undying", "name": "Totem of Undying", "cat": "Valuables"},
    {"id": "minecraft:firework_rocket", "name": "Firework Rocket", "cat": "Valuables"},
    {"id": "minecraft:ender_pearl", "name": "Ender Pearl", "cat": "Valuables"},
    {"id": "minecraft:experience_bottle", "name": "Bottle o' Enchanting", "cat": "Valuables"},
    {"id": "minecraft:heavy_core", "name": "Heavy Core", "cat": "Valuables"},
    {"id": "minecraft:netherite_ingot", "name": "Netherite Ingot", "cat": "Valuables"},
    {"id": "minecraft:netherite_block", "name": "Netherite Block", "cat": "Valuables"},
    {"id": "minecraft:diamond", "name": "Diamond", "cat": "Valuables"},
    {"id": "minecraft:diamond_block", "name": "Diamond Block", "cat": "Valuables"},
    {"id": "minecraft:emerald", "name": "Emerald", "cat": "Valuables"},
    {"id": "minecraft:nether_star", "name": "Nether Star", "cat": "Valuables"},
    {"id": "minecraft:beacon", "name": "Beacon", "cat": "Valuables"},

    # Containers & Technical
    {"id": "minecraft:shulker_box", "name": "Shulker Box", "cat": "Utility"},
    {"id": "minecraft:black_shulker_box", "name": "Black Shulker Box", "cat": "Utility"},
    {"id": "minecraft:bundle", "name": "Bundle", "cat": "Utility"},
    {"id": "minecraft:ender_chest", "name": "Ender Chest", "cat": "Utility"},
    {"id": "minecraft:command_block", "name": "Command Block", "cat": "Special"},
    {"id": "minecraft:barrier", "name": "Barrier Block", "cat": "Special"},
    {"id": "minecraft:structure_block", "name": "Structure Block", "cat": "Special"},
    {"id": "minecraft:light", "name": "Light Block", "cat": "Special"},
    {"id": "minecraft:bedrock", "name": "Bedrock", "cat": "Special"},
    {"id": "minecraft:scaffolding", "name": "Scaffolding", "cat": "Building"},
    {"id": "minecraft:obsidian", "name": "Obsidian", "cat": "Building"},
    {"id": "minecraft:crying_obsidian", "name": "Crying Obsidian", "cat": "Building"},
]

def search_items(query: str) -> List[Dict[str, Any]]:
    """Search items catalog by id or friendly name."""
    q = query.strip().lower()
    if not q:
        return ITEMS_CATALOG
    results = []
    for item in ITEMS_CATALOG:
        if q in item["id"].lower() or q in item["name"].lower() or q in item["cat"].lower():
            results.append(item)
    return results

# ==========================================
# 6. GOD-ITEM PRESETS
# ==========================================
ITEM_PRESETS: Dict[str, Dict[str, Any]] = {
    "32k_sword": {
        "name": "32k God Sword",
        "id": "minecraft:netherite_sword",
        "count": 1,
        "unbreakable": True,
        "custom_name": "32k God Sword",
        "lore": "Forged in cosmic fire\nStrikes with absolute lethality",
        "enchantments": {
            "minecraft:sharpness": 255,
            "minecraft:fire_aspect": 5,
            "minecraft:looting": 10,
            "minecraft:knockback": 10,
            "minecraft:unbreaking": 255,
            "minecraft:mending": 1,
        },
    },
    "fortune_pickaxe": {
        "name": "Fortune 255 Pickaxe",
        "id": "minecraft:netherite_pickaxe",
        "count": 1,
        "unbreakable": True,
        "custom_name": "Fortune 255 Pickaxe",
        "lore": "Splits mountains to dust\nYields boundless diamonds",
        "enchantments": {
            "minecraft:efficiency": 255,
            "minecraft:fortune": 255,
            "minecraft:unbreaking": 255,
            "minecraft:mending": 1,
        },
    },
    "cosmic_mace": {
        "name": "Cosmic 255 Mace",
        "id": "minecraft:mace",
        "count": 1,
        "unbreakable": True,
        "custom_name": "Cosmic 255 Mace",
        "lore": "Shatters gravity itself\nInfinite kinetic impact",
        "enchantments": {
            "minecraft:density": 255,
            "minecraft:breach": 255,
            "minecraft:wind_burst": 3,
            "minecraft:unbreaking": 255,
        },
    },
    "god_bow": {
        "name": "Apollo 255 Bow",
        "id": "minecraft:bow",
        "count": 1,
        "unbreakable": True,
        "custom_name": "Apollo 255 Bow",
        "lore": "Shoots solar flares\nNever misses its target",
        "enchantments": {
            "minecraft:power": 255,
            "minecraft:flame": 1,
            "minecraft:infinity": 1,
            "minecraft:punch": 10,
            "minecraft:unbreaking": 255,
        },
    },
    "titan_armor": {
        "name": "Titan Aegis",
        "id": "minecraft:netherite_chestplate",
        "count": 1,
        "unbreakable": True,
        "custom_name": "Titan Aegis",
        "lore": "Impenetrable divine armor\nNullifies all incoming damage",
        "enchantments": {
            "minecraft:protection": 255,
            "minecraft:thorns": 10,
            "minecraft:unbreaking": 255,
        },
    },
}
