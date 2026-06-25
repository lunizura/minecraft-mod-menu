"""
mc_world.py - Minecraft World Scanner, Backup Manager & High-Level State Controller
Fully compatible with Minecraft 26.x (separate players/data, game_rules.dat, weather.dat)
and legacy 1.20 / 1.21 (playerdata and embedded level.dat structures).
Includes automatic timestamped safety backups, atomic file writes, UUID decoders,
custom lore support, Ender Chest management, hardcore revival, and weather control.
"""

from __future__ import annotations
import os
import glob
import shutil
import struct
import uuid
import datetime
from typing import Dict, List, Any, Optional, Tuple

from nbt_core import (
    NBTFile, NBTTag,
    TAG_Byte, TAG_Short, TAG_Int, TAG_Long, TAG_Float, TAG_Double,
    TAG_String, TAG_List, TAG_Compound, TAG_Int_Array, TAG_Long_Array,
    TAG_COMPOUND, TAG_STRING
)
from mc_catalog import ATTRIBUTES, ENCHANTMENTS, POTIONS, GAME_RULES


def decode_mc_uuid(uuid_val: Any) -> Optional[str]:
    """
    Convert Minecraft UUID representation (Int Array of 4 ints, string, or list)
    to a standard dashed UUID string (e.g. df9443dd-24ca-41c0-bcb5-b38e7c1c8492).
    """
    if uuid_val is None:
        return None
    if hasattr(uuid_val, "to_py"):
        uuid_val = uuid_val.to_py()
    if isinstance(uuid_val, str):
        clean = uuid_val.strip().lower()
        if len(clean) in (32, 36):
            try:
                return str(uuid.UUID(clean))
            except ValueError:
                return clean
        return clean
    if isinstance(uuid_val, (list, tuple)) and len(uuid_val) == 4:
        try:
            raw = struct.pack(">4i", *[int(x) for x in uuid_val])
            return str(uuid.UUID(bytes=raw))
        except Exception:
            pass
    return None


def get_default_save_dirs() -> List[Tuple[str, str]]:
    """
    Find default Minecraft and ModrinthApp save root directories on Windows.
    Returns list of (save_path, launcher_profile_label) tuples.
    """
    dirs: List[Tuple[str, str]] = []
    appdata = os.environ.get("APPDATA")
    if appdata:
        # Vanilla / standard .minecraft
        vanilla = os.path.join(appdata, ".minecraft", "saves")
        if os.path.isdir(vanilla):
            dirs.append((vanilla, "Vanilla"))

        # ModrinthApp profiles
        modrinth_glob = os.path.join(appdata, "ModrinthApp", "profiles", "*", "saves")
        for p in glob.glob(modrinth_glob):
            if os.path.isdir(p):
                parts = p.split(os.sep)
                prof_name = "Modrinth"
                try:
                    p_idx = parts.index("profiles")
                    prof_name = f"Modrinth: {parts[p_idx + 1]}"
                except Exception:
                    pass
                if not any(d[0] == p for d in dirs):
                    dirs.append((p, prof_name))

        # CurseForge instances if present
        curse_glob = os.path.join(appdata, "CurseForge", "minecraft", "Instances", "*", "saves")
        for p in glob.glob(curse_glob):
            if os.path.isdir(p):
                parts = p.split(os.sep)
                prof_name = "CurseForge"
                try:
                    p_idx = parts.index("Instances")
                    prof_name = f"CurseForge: {parts[p_idx + 1]}"
                except Exception:
                    pass
                if not any(d[0] == p for d in dirs):
                    dirs.append((p, prof_name))

        # PrismLauncher / MultiMC if present
        prism_glob = os.path.join(appdata, "PrismLauncher", "instances", "*", ".minecraft", "saves")
        for p in glob.glob(prism_glob):
            if os.path.isdir(p):
                parts = p.split(os.sep)
                prof_name = "PrismLauncher"
                try:
                    p_idx = parts.index("instances")
                    prof_name = f"Prism: {parts[p_idx + 1]}"
                except Exception:
                    pass
                if not any(d[0] == p for d in dirs):
                    dirs.append((p, prof_name))

    return dirs


class WorldSave:
    """Represents a discovered Minecraft world save with full read/write controller methods."""

    def __init__(self, world_dir: str, profile_name: str = "Vanilla"):
        self.world_dir = os.path.abspath(world_dir)
        self.profile_name = profile_name
        self.folder_name = os.path.basename(self.world_dir)
        self.world_name = self.folder_name

        self.level_path = os.path.join(self.world_dir, "level.dat")
        self.level_file: Optional[NBTFile] = None
        self.level_data: Optional[TAG_Compound] = None

        self.player_path: Optional[str] = None
        self.player_file: Optional[NBTFile] = None
        self.player_data: Optional[TAG_Compound] = None

        self.game_rules_path: Optional[str] = None
        self.game_rules_file: Optional[NBTFile] = None
        self.game_rules_data: Optional[TAG_Compound] = None

        self.weather_path: Optional[str] = None
        self.weather_file: Optional[NBTFile] = None
        self.weather_data: Optional[TAG_Compound] = None

        self.is_26x: bool = False
        self.data_version: int = 0
        self.load_error: Optional[str] = None
        self.display_label: str = f"{self.world_name} [{self.folder_name}] - {self.profile_name}"

        self.backup_dir = os.path.join(self.world_dir, ".mc_mod_backups")

    def load(self) -> bool:
        """Load level.dat, player data, game rules, and weather files."""
        if not os.path.isfile(self.level_path):
            self.load_error = f"Missing level.dat in {self.world_dir}"
            return False

        try:
            self.level_file = NBTFile.load(self.level_path)
            self.level_data = self.level_file.root.get("Data")
            if not isinstance(self.level_data, TAG_Compound):
                self.load_error = "Invalid level.dat: missing Data compound"
                return False

            self.world_name = str(self.level_data.get("LevelName", self.folder_name))
            self.data_version = int(self.level_data.get("DataVersion", 0))

            # Detect Minecraft 26.x vs legacy
            players_dir = os.path.join(self.world_dir, "players", "data")
            legacy_playerdata_dir = os.path.join(self.world_dir, "playerdata")
            rules_26x_path = os.path.join(self.world_dir, "data", "minecraft", "game_rules.dat")
            weather_26x_path = os.path.join(self.world_dir, "data", "minecraft", "weather.dat")

            if os.path.isdir(players_dir) or os.path.isfile(rules_26x_path) or self.data_version >= 4500:
                self.is_26x = True

            # 1. Resolve Singleplayer Player File using decoded UUID
            sp_uuid_raw = self.level_data.get("singleplayer_uuid")
            sp_uuid_str = decode_mc_uuid(sp_uuid_raw)

            target_player_path: Optional[str] = None

            if os.path.isdir(players_dir):
                if sp_uuid_str:
                    candidate = os.path.join(players_dir, f"{sp_uuid_str}.dat")
                    if os.path.isfile(candidate):
                        target_player_path = candidate
                if not target_player_path:
                    files = [f for f in os.listdir(players_dir) if f.endswith(".dat") and not f.endswith("_old.dat")]
                    if files:
                        # Sort by modification time (most recently played first)
                        files.sort(key=lambda x: os.path.getmtime(os.path.join(players_dir, x)), reverse=True)
                        target_player_path = os.path.join(players_dir, files[0])
            elif os.path.isdir(legacy_playerdata_dir):
                if sp_uuid_str:
                    candidate = os.path.join(legacy_playerdata_dir, f"{sp_uuid_str}.dat")
                    if os.path.isfile(candidate):
                        target_player_path = candidate
                if not target_player_path:
                    files = [f for f in os.listdir(legacy_playerdata_dir) if f.endswith(".dat") and not f.endswith("_old.dat")]
                    if files:
                        files.sort(key=lambda x: os.path.getmtime(os.path.join(legacy_playerdata_dir, x)), reverse=True)
                        target_player_path = os.path.join(legacy_playerdata_dir, files[0])

            if target_player_path and os.path.isfile(target_player_path):
                self.player_path = target_player_path
                self.player_file = NBTFile.load(target_player_path)
                self.player_data = self.player_file.root
            elif "Player" in self.level_data and isinstance(self.level_data["Player"], TAG_Compound):
                # Embedded player in legacy level.dat
                self.player_path = self.level_path
                self.player_file = self.level_file
                self.player_data = self.level_data["Player"]

            # 2. Resolve Game Rules
            if os.path.isfile(rules_26x_path):
                self.game_rules_path = rules_26x_path
                self.game_rules_file = NBTFile.load(rules_26x_path)
                if "data" in self.game_rules_file.root and isinstance(self.game_rules_file.root["data"], TAG_Compound):
                    self.game_rules_data = self.game_rules_file.root["data"]
                else:
                    self.game_rules_data = self.game_rules_file.root
            elif "GameRules" in self.level_data and isinstance(self.level_data["GameRules"], TAG_Compound):
                self.game_rules_path = self.level_path
                self.game_rules_file = self.level_file
                self.game_rules_data = self.level_data["GameRules"]

            # 3. Resolve Weather
            if os.path.isfile(weather_26x_path):
                self.weather_path = weather_26x_path
                self.weather_file = NBTFile.load(weather_26x_path)
                if "data" in self.weather_file.root and isinstance(self.weather_file.root["data"], TAG_Compound):
                    self.weather_data = self.weather_file.root["data"]
                else:
                    self.weather_data = self.weather_file.root
            else:
                self.weather_path = self.level_path
                self.weather_file = self.level_file
                self.weather_data = self.level_data

            ver_label = "26.x" if self.is_26x else "1.20/1.21"
            self.display_label = f"{self.world_name} [{self.folder_name}] - {self.profile_name} ({ver_label})"
            return True
        except Exception as e:
            self.load_error = f"Error loading world: {str(e)}"
            return False

    def create_backup(self, target_filepath: str) -> str:
        """Create a timestamped backup before writing to any .dat file."""
        os.makedirs(self.backup_dir, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        base_name = os.path.basename(target_filepath)
        backup_name = f"{base_name}.{timestamp}.bak"
        backup_path = os.path.join(self.backup_dir, backup_name)
        if os.path.isfile(target_filepath):
            shutil.copy2(target_filepath, backup_path)
        return backup_path

    def list_backups(self) -> List[Dict[str, Any]]:
        """List all available backups in the world backup directory."""
        if not os.path.isdir(self.backup_dir):
            return []
        items = []
        for fname in sorted(os.listdir(self.backup_dir), reverse=True):
            if fname.endswith(".bak"):
                full_path = os.path.join(self.backup_dir, fname)
                mtime = os.path.getmtime(full_path)
                dt = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                items.append({
                    "filename": fname,
                    "path": full_path,
                    "date": dt,
                    "size": os.path.getsize(full_path)
                })
        return items

    def restore_backup(self, backup_filepath: str) -> bool:
        """Restore a backup file to its original target."""
        if not os.path.isfile(backup_filepath):
            return False
        base = os.path.basename(backup_filepath)
        # Formatted like level.dat.20261019_153000_123456.bak
        parts = base.split(".")
        if len(parts) >= 3 and parts[-1] == "bak":
            orig_name = f"{parts[0]}.{parts[1]}"
            if orig_name == "level.dat":
                dest = self.level_path
            elif orig_name == "game_rules.dat" and self.game_rules_path:
                dest = self.game_rules_path
            elif orig_name == "weather.dat" and self.weather_path:
                dest = self.weather_path
            elif self.player_path and os.path.basename(self.player_path) == orig_name:
                dest = self.player_path
            elif self.is_26x and orig_name.endswith(".dat"):
                dest = os.path.join(self.world_dir, "players", "data", orig_name)
            else:
                dest = os.path.join(self.world_dir, "playerdata", orig_name)

            os.makedirs(os.path.dirname(dest), exist_ok=True)

