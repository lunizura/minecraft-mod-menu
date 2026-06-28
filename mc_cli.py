"""
mc_cli.py - Command-Line Interface for Minecraft Mod Menu & World Editor
Provides quick headless commands for scanning worlds, inspecting players,
injecting god kits, reviving dead players, hardcore revive, weather control,
and managing backups.
"""

from __future__ import annotations
import sys
import os
import argparse
from typing import Optional

from mc_world import WorldSave, scan_all_worlds
from mc_catalog import ATTRIBUTES, GAME_RULES


def find_world(identifier: str) -> Optional[WorldSave]:
    """Find world by exact path, folder name, or matching name."""
    if os.path.isdir(identifier) and os.path.isfile(os.path.join(identifier, "level.dat")):
        w = WorldSave(identifier)
        if w.load():
            return w

    worlds = scan_all_worlds()
    target_lower = identifier.strip().lower()
    for w in worlds:
        if (
            w.world_name.lower() == target_lower
            or w.folder_name.lower() == target_lower
            or os.path.basename(w.world_dir).lower() == target_lower
            or w.display_label.lower() == target_lower
        ):
            return w
    # Partial match
    for w in worlds:
        if target_lower in w.world_name.lower() or target_lower in w.folder_name.lower():
            return w
    return None


def cmd_scan(args):
    worlds = scan_all_worlds()
    print(f"\nDiscovered {len(worlds)} Minecraft Worlds:\n")
    print(f"{'World Name':<25} | {'Folder':<18} | {'Profile':<15} | {'Mode':<10} | {'Ver'}")
    print("-" * 85)
    mode_names = {0: "Survival", 1: "Creative", 2: "Adventure", 3: "Spectator"}
    for w in worlds:
        gm = mode_names.get(w.get_gamemode(), "Unknown")
        ver = "26.x" if w.is_26x else "1.21"
        print(f"{w.world_name:<25} | {w.folder_name:<18} | {w.profile_name:<15} | {gm:<10} | {ver}")
    print()


def cmd_inspect(args):
    w = find_world(args.world)
    if not w:
        print(f"Error: Could not find world matching '{args.world}'")
        sys.exit(1)

    print(f"\n==========================================")
    print(f" World:   {w.world_name} [{w.folder_name}]")
    print(f" Profile: {w.profile_name} ({'Minecraft 26.x' if w.is_26x else 'Legacy 1.20/1.21'})")
    print(f" Path:    {w.world_dir}")
    print(f" Version: DataVersion {w.data_version}")
    print(f"==========================================")
    print(f" Cheats (allowCommands): {w.get_cheats_enabled()}")
    print(f" Difficulty:             {w.get_difficulty()} (Hardcore: {w.get_hardcore()})")
    print(f" Weather:                {w.get_weather()}")
    pos = w.get_player_pos()
    print(f" Player Position:        X: {pos[0]:.2f}, Y: {pos[1]:.2f}, Z: {pos[2]:.2f}")

    vitals = w.get_vitals()
    print(f" Player Vitals:          Health: {vitals['health']:.1f}, Food: {vitals['food']}, XP Level: {vitals['xp_level']}")
    print(f" God Mode (Invulnerable):{w.get_god_mode()}")
    print(f" Survival Flight (mayfly):{w.get_mayfly()}")

    ldl = w.get_last_death_location()
    if ldl:
        print(f" Last Death Location:    X: {ldl['x']}, Y: {ldl['y']}, Z: {ldl['z']} in {ldl['dimension']}")
    else:
        print(f" Last Death Location:    None")

    items = w.get_items(is_ender=False)
    ender_items = w.get_items(is_ender=True)
    print(f" Inventory Items:        {len(items)} slots occupied")
    print(f" Ender Chest Items:      {len(ender_items)} slots occupied")
    effects = w.get_effects()
    print(f" Active Potion Effects:  {len(effects)}")
    print(f" Keep Inventory Rule:    {w.get_game_rule('keep_inventory')}")
    print(f" Daylight Cycle Rule:    {w.get_game_rule('do_daylight_cycle')}")
    print(f" Weather Cycle Rule:     {w.get_game_rule('do_weather_cycle')}")
    print()


def cmd_god(args):
    w = find_world(args.world)
    if not w:
        print(f"Error: Could not find world matching '{args.world}'")
        sys.exit(1)

    enable = not args.disable
    w.set_god_mode(enable)
    w.set_mayfly(enable)
    if enable:
        w.refill_vitals(health=200.0, food=20, saturation=20.0, absorption=40.0)
    w.save_all()
    print(f"God Mode & Survival Flight set to {'ENABLED' if enable else 'DISABLED'} for world '{w.world_name}'")


def cmd_revive(args):
    w = find_world(args.world)
    if not w:
        print(f"Error: Could not find world matching '{args.world}'")
        sys.exit(1)

    w.refill_vitals(health=20.0, food=20, saturation=20.0, absorption=0.0)
    w.save_all()
    print(f"Player revived in world '{w.world_name}' with full health & hunger.")


def cmd_hardcore_revive(args):
    w = find_world(args.world)
    if not w:
        print(f"Error: Could not find world matching '{args.world}'")
        sys.exit(1)

    success = w.hardcore_revive(restore_survival=True, remove_hardcore=args.remove_hardcore)
    if success:
        w.save_all()
        print(f"Hardcore world '{w.world_name}' revived! Restored to Survival mode with full health & god protection.")
    else:
        print(f"Error: Failed to revive world '{w.world_name}'.")
        sys.exit(1)


def cmd_weather(args):
    w = find_world(args.world)
    if not w:
        print(f"Error: Could not find world matching '{args.world}'")
        sys.exit(1)

    w.set_weather(args.type)
    w.save_all()
    print(f"Weather set to '{args.type}' for world '{w.world_name}'.")


def cmd_cheats(args):
    w = find_world(args.world)
    if not w:
        print(f"Error: Could not find world matching '{args.world}'")
        sys.exit(1)

    enable = not args.disable
    w.set_cheats_enabled(enable)
    w.save_all()
    print(f"Commands & cheats set to {'ENABLED' if enable else 'DISABLED'} for world '{w.world_name}'.")


def cmd_kit(args):
    w = find_world(args.world)
    if not w:
        print(f"Error: Could not find world matching '{args.world}'")
        sys.exit(1)

    w.inject_kit(args.kit)
    w.save_all()
    print(f"Kit '{args.kit}' successfully injected into world '{w.world_name}'")


def cmd_tp_death(args):
    w = find_world(args.world)
    if not w:
        print(f"Error: Could not find world matching '{args.world}'")
        sys.exit(1)

    if w.teleport_to_last_death():
        w.save_all()
        ldl = w.get_last_death_location()
        print(f"Player teleported to last death location: {ldl} in world '{w.world_name}'")
    else:
        print("No LastDeathLocation found on this player.")


def main():
    parser = argparse.ArgumentParser(description="Minecraft All-in-One Mod Menu CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # scan
    p_scan = subparsers.add_parser("scan", help="Scan and list all Minecraft worlds")
    p_scan.set_defaults(func=cmd_scan)

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect player and world details")
    p_inspect.add_argument("world", help="World directory path or world name")
    p_inspect.set_defaults(func=cmd_inspect)

    # god
    p_god = subparsers.add_parser("god", help="Enable or disable God Mode & Flight")
    p_god.add_argument("world", help="World directory path or world name")
    p_god.add_argument("--disable", action="store_true", help="Disable god mode")
    p_god.set_defaults(func=cmd_god)

    # revive
    p_revive = subparsers.add_parser("revive", help="Revive dead player with full health")
    p_revive.add_argument("world", help="World directory path or world name")
    p_revive.set_defaults(func=cmd_revive)

    # hardcore-revive
    p_hc = subparsers.add_parser("hardcore-revive", help="Revive dead hardcore player back to survival")
    p_hc.add_argument("world", help="World directory path or world name")
    p_hc.add_argument("--remove-hardcore", action="store_true", help="Remove hardcore restriction from world")
    p_hc.set_defaults(func=cmd_hardcore_revive)

    # weather
    p_weather = subparsers.add_parser("weather", help="Set world weather")
    p_weather.add_argument("world", help="World directory path or world name")
    p_weather.add_argument("type", choices=["clear", "rain", "thunder"], help="Weather type")
    p_weather.set_defaults(func=cmd_weather)

    # cheats
    p_cheats = subparsers.add_parser("cheats", help="Enable or disable in-game cheats")
    p_cheats.add_argument("world", help="World directory path or world name")
    p_cheats.add_argument("--disable", action="store_true", help="Disable cheats")
    p_cheats.set_defaults(func=cmd_cheats)

    # kit
    p_kit = subparsers.add_parser("kit", help="Inject god loadout kit into player inventory")
    p_kit.add_argument("world", help="World directory path or world name")
    p_kit.add_argument("kit", choices=["god_netherite", "builder"], help="Kit name")
    p_kit.set_defaults(func=cmd_kit)

    # tp-death
    p_tp = subparsers.add_parser("tp-death", help="Teleport player to last death coordinates")
    p_tp.add_argument("world", help="World directory path or world name")
    p_tp.set_defaults(func=cmd_tp_death)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
