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

