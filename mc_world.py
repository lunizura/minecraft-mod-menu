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
import json
import shutil
import struct
import uuid
import datetime
from pathlib import Path
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
            shutil.copy2(backup_filepath, dest)
            self.load()
            return True
        return False

    def _atomic_save(self, nbt_obj: NBTFile, file_path: str) -> None:
        """Save NBT file safely: backup original first, write to .tmp, then atomic rename."""
        self.create_backup(file_path)
        tmp_path = f"{file_path}.tmp"
        nbt_obj.save(tmp_path, compress=nbt_obj.compressed)
        if os.path.isfile(file_path):
            os.replace(tmp_path, file_path)
        else:
            os.rename(tmp_path, file_path)

    def save_all(self) -> None:
        """Save all modified files (level.dat, player .dat, game_rules.dat, weather.dat)."""
        # 1. Level file
        if self.level_file and self.level_path:
            # Sync embedded Player if present in legacy
            if self.level_data and "Player" in self.level_data and self.player_data and self.player_data != self.level_data["Player"]:
                self.level_data["Player"] = self.player_data
            self._atomic_save(self.level_file, self.level_path)

        # 2. Player file (if separate)
        if self.player_file and self.player_path and self.player_path != self.level_path:
            self._atomic_save(self.player_file, self.player_path)

        # 3. Game rules file (if separate)
        if self.game_rules_file and self.game_rules_path and self.game_rules_path != self.level_path:
            self._atomic_save(self.game_rules_file, self.game_rules_path)

        # 4. Weather file (if separate)
        if self.weather_file and self.weather_path and self.weather_path != self.level_path:
            self._atomic_save(self.weather_file, self.weather_path)

    # ==========================================
    # TAB 1: PLAYER HACKS & VITALS
    # ==========================================

    def _ensure_abilities(self) -> TAG_Compound:
        if not self.player_data:
            raise ValueError("No player data loaded")
        if "abilities" not in self.player_data or not isinstance(self.player_data["abilities"], TAG_Compound):
            self.player_data["abilities"] = TAG_Compound()
        return self.player_data["abilities"]

    def get_god_mode(self) -> bool:
        if not self.player_data:
            return False
        invul = self.player_data.get("Invulnerable")
        ab = self.player_data.get("abilities")
        ab_invul = ab.get("invulnerable") if isinstance(ab, TAG_Compound) else None
        return bool(invul and invul.to_py() == 1) or bool(ab_invul and ab_invul.to_py() == 1)

    def set_god_mode(self, enabled: bool) -> None:
        if not self.player_data:
            return
        val = TAG_Byte(1 if enabled else 0)
        self.player_data["Invulnerable"] = val
        abilities = self._ensure_abilities()
        abilities["invulnerable"] = val
        if enabled:
            # If player was dead, ensure health is restored so god mode is effective
            v = self.get_vitals()
            if v["health"] <= 0.0:
                self.refill_vitals(health=20.0)

    def get_mayfly(self) -> bool:
        if not self.player_data:
            return False
        ab = self.player_data.get("abilities")
        if isinstance(ab, TAG_Compound):
            mf = ab.get("mayfly")
            return bool(mf and mf.to_py() == 1)
        return False

    def set_mayfly(self, enabled: bool) -> None:
        abilities = self._ensure_abilities()
        abilities["mayfly"] = TAG_Byte(1 if enabled else 0)

    def get_flying(self) -> bool:
        if not self.player_data:
            return False
        ab = self.player_data.get("abilities")
        if isinstance(ab, TAG_Compound):
            fl = ab.get("flying")
            return bool(fl and fl.to_py() == 1)
        return False

    def set_flying(self, enabled: bool) -> None:
        abilities = self._ensure_abilities()
        abilities["flying"] = TAG_Byte(1 if enabled else 0)

    def get_instabuild(self) -> bool:
        if not self.player_data:
            return False
        ab = self.player_data.get("abilities")
        if isinstance(ab, TAG_Compound):
            ib = ab.get("instabuild")
            return bool(ib and ib.to_py() == 1)
        return False

    def set_instabuild(self, enabled: bool) -> None:
        abilities = self._ensure_abilities()
        abilities["instabuild"] = TAG_Byte(1 if enabled else 0)

    def get_vitals(self) -> Dict[str, Any]:
        if not self.player_data:
            return {"health": 20.0, "food": 20, "saturation": 20.0, "absorption": 0.0, "xp_level": 0}
        health = float(self.player_data.get("Health", TAG_Float(20.0)).to_py())
        food = int(self.player_data.get("foodLevel", TAG_Int(20)).to_py())
        saturation = float(self.player_data.get("foodSaturationLevel", TAG_Float(20.0)).to_py())
        absorption = float(self.player_data.get("AbsorptionAmount", TAG_Float(0.0)).to_py())
        xp_level = int(self.player_data.get("XpLevel", TAG_Int(0)).to_py())
        return {
            "health": health,
            "food": food,
            "saturation": saturation,
            "absorption": absorption,
            "xp_level": xp_level
        }

    def refill_vitals(self, health: float = 20.0, food: int = 20, saturation: float = 20.0, absorption: float = 0.0) -> None:
        if not self.player_data:
            return
        # If requested health exceeds max_health attribute, bump max_health attribute
        curr_max = self.get_attribute("minecraft:max_health")
        if health > curr_max:
            self.set_attribute("minecraft:max_health", health)

        self.player_data["Health"] = TAG_Float(health)
        self.player_data["foodLevel"] = TAG_Int(food)
        self.player_data["foodSaturationLevel"] = TAG_Float(saturation)
        self.player_data["foodTickTimer"] = TAG_Int(0)
        self.player_data["foodExhaustionLevel"] = TAG_Float(0.0)
        self.player_data["AbsorptionAmount"] = TAG_Float(absorption)

        # Clear injury, fire, death, and air timers
        self.player_data["DeathTime"] = TAG_Short(0)
        self.player_data["HurtTime"] = TAG_Short(0)
        self.player_data["Fire"] = TAG_Short(-20)
        self.player_data["Air"] = TAG_Short(300)
        self.player_data["SleepTimer"] = TAG_Short(0)

        # Clear kinetic fall distance in BOTH modern 26.x (double) and legacy (float) formats!
        self.player_data["fall_distance"] = TAG_Double(0.0)
        self.player_data["FallDistance"] = TAG_Float(0.0)

    def set_xp_level(self, level: int) -> None:
        if not self.player_data:
            return
        self.player_data["XpLevel"] = TAG_Int(level)
        self.player_data["XpP"] = TAG_Float(0.0)
        if level <= 16:
            total = level * level + 6 * level
        elif level <= 31:
            total = int(2.5 * level * level - 40.5 * level + 360)
        else:
            total = int(4.5 * level * level - 162.5 * level + 2220)
        self.player_data["XpTotal"] = TAG_Int(total)

    def get_player_pos(self) -> Tuple[float, float, float]:
        if not self.player_data or "Pos" not in self.player_data:
            return (0.0, 64.0, 0.0)
        pos = self.player_data["Pos"]
        if isinstance(pos, TAG_List) and len(pos) >= 3:
            return (float(pos[0].to_py()), float(pos[1].to_py()), float(pos[2].to_py()))
        return (0.0, 64.0, 0.0)

    def get_last_death_location(self) -> Optional[Dict[str, Any]]:
        if not self.player_data:
            return None
        ldl = self.player_data.get("LastDeathLocation") or self.player_data.get("last_death_location")
        if isinstance(ldl, TAG_Compound):
            pos_tag = ldl.get("pos") or ldl.get("Pos")
            dim_tag = ldl.get("dimension") or ldl.get("Dimension")
            dimension = str(dim_tag.to_py()) if dim_tag else "minecraft:overworld"
            coords = [0, 0, 0]
            if isinstance(pos_tag, TAG_Int_Array):
                coords = pos_tag.to_py()
            elif isinstance(pos_tag, TAG_List):
                coords = [int(v.to_py()) for v in pos_tag]
            if len(coords) >= 3:
                return {"x": coords[0], "y": coords[1], "z": coords[2], "dimension": dimension}
        return None

    def get_world_spawn(self) -> Tuple[float, float, float, str]:
        if not self.level_data:
            return (0.0, 64.0, 0.0, "minecraft:overworld")
        spawn_comp = self.level_data.get("spawn")
        if isinstance(spawn_comp, TAG_Compound):
            pos = spawn_comp.get("pos")
            dim = spawn_comp.get("dimension")
            dim_str = str(dim.to_py()) if dim else "minecraft:overworld"
            if isinstance(pos, TAG_Int_Array) and len(pos) >= 3:
                p = pos.to_py()
                return (float(p[0]), float(p[1]), float(p[2]), dim_str)
        # Legacy
        sx = float(self.level_data.get("SpawnX", TAG_Int(0)).to_py())
        sy = float(self.level_data.get("SpawnY", TAG_Int(64)).to_py())
        sz = float(self.level_data.get("SpawnZ", TAG_Int(0)).to_py())
        return (sx, sy, sz, "minecraft:overworld")

    def teleport_player(self, x: float, y: float, z: float, dimension: Optional[str] = None) -> None:
        if not self.player_data:
            return
        pos_list = TAG_List(TAG_Double.tag_type, [TAG_Double(x), TAG_Double(y), TAG_Double(z)])
        self.player_data["Pos"] = pos_list
        self.player_data["Motion"] = TAG_List(TAG_Double.tag_type, [TAG_Double(0.0), TAG_Double(0.0), TAG_Double(0.0)])
        self.player_data["fall_distance"] = TAG_Double(0.0)
        self.player_data["FallDistance"] = TAG_Float(0.0)
        self.player_data["OnGround"] = TAG_Byte(1)
        if dimension:
            dim_tag = self.player_data.get("Dimension")
            if isinstance(dim_tag, TAG_Int):
                dim_map = {"minecraft:overworld": 0, "minecraft:the_nether": -1, "minecraft:the_end": 1}
                self.player_data["Dimension"] = TAG_Int(dim_map.get(dimension, 0))
            else:
                self.player_data["Dimension"] = TAG_String(dimension)

    def teleport_to_last_death(self) -> bool:
        ldl = self.get_last_death_location()
        if not ldl:
            return False
        # If dead, revive player so they don't load into death screen
        if self.get_vitals()["health"] <= 0.0:
            self.refill_vitals(health=20.0)
        self.teleport_player(float(ldl["x"]) + 0.5, float(ldl["y"]) + 1.0, float(ldl["z"]) + 0.5, ldl.get("dimension"))
        return True

    def teleport_to_spawn(self) -> None:
        sx, sy, sz, dim = self.get_world_spawn()
        self.teleport_player(sx + 0.5, sy + 2.0, sz + 0.5, dim)

    def get_player_dimension(self) -> str:
        """Return the current player dimension as a namespaced string."""
        if not self.player_data or "Dimension" not in self.player_data:
            return "minecraft:overworld"
        dim = self.player_data["Dimension"].to_py()
        if isinstance(dim, int):
            dim_rev = {0: "minecraft:overworld", -1: "minecraft:the_nether", 1: "minecraft:the_end"}
            return dim_rev.get(dim, "minecraft:overworld")
        return str(dim)

    def get_waypoints(self) -> Dict[str, Any]:
        """Load saved waypoints from .mc_waypoints.json inside the world directory."""
        wp_path = Path(self.world_dir) / ".mc_waypoints.json"
        if wp_path.exists():
            try:
                return json.loads(wp_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def set_waypoint(self, name: str, x: float, y: float, z: float, dimension: Optional[str] = None) -> Dict[str, Any]:
        """Save or update a named coordinate waypoint."""
        wp_path = Path(self.world_dir) / ".mc_waypoints.json"
        waypoints = self.get_waypoints()
        dim = dimension or self.get_player_dimension()
        from datetime import datetime
        entry = {
            "name": name.strip(),
            "x": round(float(x), 2),
            "y": round(float(y), 2),
            "z": round(float(z), 2),
            "dimension": dim,
            "created_at": datetime.now().isoformat()
        }
        waypoints[name.strip()] = entry
        wp_path.write_text(json.dumps(waypoints, indent=2), encoding="utf-8")
        return entry

    def delete_waypoint(self, name: str) -> bool:
        """Delete a saved waypoint by name."""
        wp_path = Path(self.world_dir) / ".mc_waypoints.json"
        waypoints = self.get_waypoints()
        if name in waypoints:
            del waypoints[name]
            wp_path.write_text(json.dumps(waypoints, indent=2), encoding="utf-8")
            return True
        return False

    def teleport_to_waypoint(self, name: str) -> bool:
        """Teleport player to a named waypoint."""
        waypoints = self.get_waypoints()
        if name not in waypoints:
            return False
        wp = waypoints[name]
        self.teleport_player(wp["x"], wp["y"], wp["z"], wp.get("dimension"))
        return True

    def export_world_zip(self, output_path: Optional[str] = None) -> str:
        """Export world to a standalone, timestamped ZIP archive."""
        import zipfile
        from datetime import datetime
        if not output_path:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(c for c in self.world_name if c.isalnum() or c in (" ", "-", "_")).strip()
            out_file = Path(self.world_dir).parent / f"{safe_name}_{ts}.zip"
        else:
            out_file = Path(output_path)
        
        out_file.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out_file, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(self.world_dir):
                if ".mc_mod_backups" in root:
                    continue
                for f in files:
                    file_path = Path(root) / f
                    arcname = file_path.relative_to(self.world_dir)
                    zf.write(file_path, arcname)
        return str(out_file)

    # ==========================================
    # TAB 2: BASE ATTRIBUTES MATRIX
    # ==========================================

    def _ensure_attributes(self) -> TAG_List:
        if not self.player_data:
            raise ValueError("No player data loaded")
        key = "attributes" if "attributes" in self.player_data or self.is_26x else "Attributes"
        if key not in self.player_data or not isinstance(self.player_data[key], TAG_List):
            self.player_data[key] = TAG_List(TAG_COMPOUND, [])
        return self.player_data[key]

    def get_attribute(self, attr_id: str) -> float:
        if not self.player_data:
            return ATTRIBUTES.get(attr_id, {}).get("default", 0.0)
        attrs = self.player_data.get("attributes") or self.player_data.get("Attributes")
        if isinstance(attrs, TAG_List):
            for item in attrs:
                if not isinstance(item, TAG_Compound):
                    continue
                # Check modern id and legacy Name
                item_id = str(item.get("id") or item.get("Name") or "")
                if item_id == attr_id or item_id == attr_id.replace("minecraft:", "minecraft:generic.") or item_id == attr_id.replace("minecraft:", "generic."):
                    base = item.get("base") or item.get("Base")
                    if base is not None:
                        return float(base.to_py())
        return ATTRIBUTES.get(attr_id, {}).get("default", 0.0)

    def set_attribute(self, attr_id: str, base_val: float) -> None:
        attrs = self._ensure_attributes()
        found = False
        for item in attrs:
            if not isinstance(item, TAG_Compound):
                continue
            item_id = str(item.get("id") or item.get("Name") or "")
            if item_id == attr_id or item_id == attr_id.replace("minecraft:", "minecraft:generic.") or item_id == attr_id.replace("minecraft:", "generic."):
                if "Base" in item:
                    item["Base"] = TAG_Double(base_val)
                else:
                    item["base"] = TAG_Double(base_val)
                found = True
                break
        if not found:
            new_comp = TAG_Compound()
            new_comp["id"] = TAG_String(attr_id)
            new_comp["base"] = TAG_Double(base_val)
            attrs.append(new_comp)

    def get_all_attributes(self) -> Dict[str, float]:
        res = {}
        for attr_id in ATTRIBUTES.keys():
            res[attr_id] = self.get_attribute(attr_id)
        return res

    def reset_attributes(self) -> None:
        for attr_id, meta in ATTRIBUTES.items():
            self.set_attribute(attr_id, meta["default"])

    # ==========================================
    # TAB 3: GOD-ITEM FORGE, INVENTORY & ENDER CHEST
    # ==========================================

    def _ensure_inventory_list(self, is_ender: bool = False) -> TAG_List:
        if not self.player_data:
            raise ValueError("No player data loaded")
        key = "EnderItems" if is_ender else "Inventory"
        if key not in self.player_data or not isinstance(self.player_data[key], TAG_List):
            self.player_data[key] = TAG_List(TAG_COMPOUND, [])
        return self.player_data[key]

    def get_items(self, is_ender: bool = False) -> List[Dict[str, Any]]:
        """Parse inventory or ender items into high-level dictionaries including lore."""
        if not self.player_data:
            return []
        key = "EnderItems" if is_ender else "Inventory"
        raw_list = self.player_data.get(key)
        if not isinstance(raw_list, TAG_List):
            return []

        results = []
        for it in raw_list:
            if not isinstance(it, TAG_Compound):
                continue
            slot = int(it.get("Slot", TAG_Byte(0)).to_py())
            item_id = str(it.get("id", TAG_String("")).to_py())
            count = int(it.get("count", it.get("Count", TAG_Int(1))).to_py())

            components = it.get("components")
            legacy_tag = it.get("tag")

            damage = 0
            enchantments: Dict[str, int] = {}
            unbreakable = False
            custom_name = ""
            lore: List[str] = []

            if isinstance(components, TAG_Compound):
                # Damage
                dmg_tag = components.get("minecraft:damage")
                if dmg_tag:
                    damage = int(dmg_tag.to_py())
                # Unbreakable
                if "minecraft:unbreakable" in components:
                    unbreakable = True
                # Enchantments
                ench_comp = components.get("minecraft:enchantments")
                if isinstance(ench_comp, TAG_Compound):
                    for eid, elvl in ench_comp.items():
                        enchantments[str(eid)] = int(elvl.to_py())
                # Custom Name
                cn = components.get("minecraft:custom_name")
                if cn:
                    custom_name = str(cn.to_py())
                # Lore
                lore_list = components.get("minecraft:lore")
                if isinstance(lore_list, TAG_List):
                    lore = [str(line.to_py()) for line in lore_list]
            elif isinstance(legacy_tag, TAG_Compound):
                dmg_tag = legacy_tag.get("Damage")
                if dmg_tag:
                    damage = int(dmg_tag.to_py())
                if legacy_tag.get("Unbreakable") and legacy_tag.get("Unbreakable").to_py() == 1:
                    unbreakable = True
                ench_list = legacy_tag.get("Enchantments")
                if isinstance(ench_list, TAG_List):
                    for e in ench_list:
                        if isinstance(e, TAG_Compound):
                            eid = str(e.get("id", ""))
                            elvl = int(e.get("lvl", TAG_Short(1)).to_py())
                            enchantments[eid] = elvl
                display_comp = legacy_tag.get("display")
                if isinstance(display_comp, TAG_Compound):
                    cn = display_comp.get("Name")
                    if cn:
                        custom_name = str(cn.to_py())
                    lore_list = display_comp.get("Lore")
                    if isinstance(lore_list, TAG_List):
                        lore = [str(line.to_py()) for line in lore_list]

            results.append({
                "slot": slot,
                "id": item_id,
                "count": count,
                "damage": damage,
                "unbreakable": unbreakable,
                "enchantments": enchantments,
                "custom_name": custom_name,
                "lore": lore,
                "raw_tag": it
            })
        return sorted(results, key=lambda x: x["slot"])

    def set_item(self, slot: int, item_id: str, count: int = 1,
                 enchantments: Optional[Dict[str, int]] = None,
                 unbreakable: bool = False,
                 damage: int = 0,
                 custom_name: str = "",
                 custom_lore: str = "",
                 is_ender: bool = False) -> None:
        """Create or replace an item in a specific inventory or ender slot supporting components & legacy."""
        inv = self._ensure_inventory_list(is_ender)
        inv.value = [it for it in inv.value if isinstance(it, TAG_Compound) and it.get("Slot", TAG_Byte(-999)).to_py() != slot]

        item_comp = TAG_Compound()
        item_comp["Slot"] = TAG_Byte(slot)
        item_comp["id"] = TAG_String(item_id)

        is_legacy_format = (0 < self.data_version < 3837) and not self.is_26x

        if is_legacy_format:
            item_comp["Count"] = TAG_Byte(min(127, max(1, count)))
            legacy_tag = TAG_Compound()
            has_tag = False

            if damage > 0:
                legacy_tag["Damage"] = TAG_Int(damage)
                has_tag = True

            if unbreakable:
                legacy_tag["Unbreakable"] = TAG_Byte(1)
                has_tag = True

            if enchantments:
                ench_list = TAG_List(TAG_COMPOUND, [])
                for eid, lvl in enchantments.items():
                    if not eid.startswith("minecraft:"):
                        eid = f"minecraft:{eid}"
                    e_comp = TAG_Compound()
                    e_comp["id"] = TAG_String(eid)
                    e_comp["lvl"] = TAG_Short(min(32767, lvl))
                    ench_list.append(e_comp)
                legacy_tag["Enchantments"] = ench_list
                has_tag = True

            display_comp = TAG_Compound()
            has_display = False
            if custom_name:
                display_comp["Name"] = TAG_String(f'{{"text":"{custom_name}"}}')
                has_display = True
            if custom_lore:
                lines = [l.strip() for l in custom_lore.split("\n") if l.strip()]
                if lines:
                    display_comp["Lore"] = TAG_List(TAG_STRING, [TAG_String(f'{{"text":"{line}"}}') for line in lines])
                    has_display = True
            if has_display:
                legacy_tag["display"] = display_comp
                has_tag = True

            if has_tag:
                item_comp["tag"] = legacy_tag
        else:
            # Modern 26.x and 1.20.5+ components
            item_comp["count"] = TAG_Int(count)
            components = TAG_Compound()
            has_components = False

            if damage > 0:
                components["minecraft:damage"] = TAG_Int(damage)
                has_components = True

            if unbreakable:
                components["minecraft:unbreakable"] = TAG_Compound()
                has_components = True

            if enchantments:
                ench_comp = TAG_Compound()
                for eid, lvl in enchantments.items():
                    if not eid.startswith("minecraft:"):
                        eid = f"minecraft:{eid}"
                    ench_comp[eid] = TAG_Int(lvl)
                components["minecraft:enchantments"] = ench_comp
                has_components = True

            if custom_name:
                components["minecraft:custom_name"] = TAG_String(f'{{"text":"{custom_name}"}}')
                has_components = True

            if custom_lore:
                lines = [l.strip() for l in custom_lore.split("\n") if l.strip()]
                if lines:
                    components["minecraft:lore"] = TAG_List(TAG_STRING, [TAG_String(f'{{"text":"{line}"}}') for line in lines])
                    has_components = True

            if count > 64:
                components["minecraft:max_stack_size"] = TAG_Int(99)
                has_components = True

            if has_components:
                item_comp["components"] = components

        inv.append(item_comp)

    def remove_item(self, slot: int, is_ender: bool = False) -> None:
        inv = self._ensure_inventory_list(is_ender)
        inv.value = [it for it in inv.value if isinstance(it, TAG_Compound) and it.get("Slot", TAG_Byte(-999)).to_py() != slot]

    def clear_inventory(self, is_ender: bool = False) -> None:
        inv = self._ensure_inventory_list(is_ender)
        inv.value = []

    def repair_all_items(self) -> int:
        """Reset damage to 0 on all damaged items in inventory and ender chest."""
        repaired = 0
        for is_ender in (False, True):
            inv = self._ensure_inventory_list(is_ender)
            for raw in inv.value:
                if not isinstance(raw, TAG_Compound):
                    continue
                item_repaired = False
                comps = raw.get("components")
                if isinstance(comps, TAG_Compound) and "minecraft:damage" in comps:
                    dmg = comps["minecraft:damage"].to_py()
                    if dmg > 0:
                        comps["minecraft:damage"] = TAG_Int(0)
                        item_repaired = True
                legacy = raw.get("tag")
                if isinstance(legacy, TAG_Compound) and "Damage" in legacy:
                    dmg = legacy["Damage"].to_py()
                    if dmg > 0:
                        legacy["Damage"] = TAG_Int(0)
                        item_repaired = True
                if item_repaired:
                    repaired += 1
        return repaired

    def inject_kit(self, kit_name: str) -> None:
        """Inject complete god-tier kits into player inventory."""
        if kit_name == "god_netherite":
            god_ench_sword = {"minecraft:sharpness": 255, "minecraft:looting": 10, "minecraft:fire_aspect": 5, "minecraft:unbreaking": 255, "minecraft:mending": 1}
            self.set_item(0, "minecraft:netherite_sword", 1, god_ench_sword, unbreakable=True, custom_name="Void Cleaver", custom_lore="Forged from stellar remnants\nStrikes through reality itself")

            god_ench_pick = {"minecraft:efficiency": 255, "minecraft:fortune": 255, "minecraft:unbreaking": 255, "minecraft:mending": 1}
            self.set_item(1, "minecraft:netherite_pickaxe", 1, god_ench_pick, unbreakable=True, custom_name="World Breaker", custom_lore="Shatters bedrock and mountain veins")

            god_ench_axe = {"minecraft:sharpness": 255, "minecraft:efficiency": 255, "minecraft:fortune": 255, "minecraft:unbreaking": 255}
            self.set_item(2, "minecraft:netherite_axe", 1, god_ench_axe, unbreakable=True, custom_name="Executioner")

            god_ench_mace = {"minecraft:density": 255, "minecraft:breach": 255, "minecraft:wind_burst": 3, "minecraft:unbreaking": 255}
            self.set_item(3, "minecraft:mace", 1, god_ench_mace, unbreakable=True, custom_name="Cosmic Hammer", custom_lore="Converts falling momentum to cataclysms")

            god_ench_bow = {"minecraft:power": 255, "minecraft:flame": 1, "minecraft:infinity": 1, "minecraft:punch": 10, "minecraft:unbreaking": 255}
            self.set_item(4, "minecraft:bow", 1, god_ench_bow, unbreakable=True, custom_name="Apollo Whisper")

            self.set_item(5, "minecraft:enchanted_golden_apple", 64)
            self.set_item(6, "minecraft:firework_rocket", 64)
            self.set_item(7, "minecraft:totem_of_undying", 64)
            self.set_item(8, "minecraft:ender_pearl", 64)

            # Armor
            god_ench_helm = {"minecraft:protection": 255, "minecraft:respiration": 10, "minecraft:aqua_affinity": 1, "minecraft:unbreaking": 255}
            self.set_item(103, "minecraft:netherite_helmet", 1, god_ench_helm, unbreakable=True, custom_name="Crown of the Stars")

            god_ench_chest = {"minecraft:protection": 255, "minecraft:thorns": 10, "minecraft:unbreaking": 255}
            self.set_item(102, "minecraft:netherite_chestplate", 1, god_ench_chest, unbreakable=True, custom_name="Aegis of Olympus")

            god_ench_legs = {"minecraft:protection": 255, "minecraft:swift_sneak": 5, "minecraft:unbreaking": 255}
            self.set_item(101, "minecraft:netherite_leggings", 1, god_ench_legs, unbreakable=True, custom_name="Greaves of the Void")

            god_ench_boots = {"minecraft:protection": 255, "minecraft:feather_falling": 255, "minecraft:soul_speed": 5, "minecraft:depth_strider": 5, "minecraft:unbreaking": 255}
            self.set_item(100, "minecraft:netherite_boots", 1, god_ench_boots, unbreakable=True, custom_name="Hermes Striders")

            # Offhand
            self.set_item(-106, "minecraft:totem_of_undying", 1, unbreakable=True, custom_name="Undying Soul")

            # Inventory slots
            self.set_item(9, "minecraft:elytra", 1, {"minecraft:unbreaking": 255, "minecraft:mending": 1}, unbreakable=True, custom_name="Skywalker Wings")
            self.set_item(10, "minecraft:netherite_shovel", 1, {"minecraft:efficiency": 255, "minecraft:silk_touch": 1, "minecraft:unbreaking": 255}, unbreakable=True)
            self.set_item(11, "minecraft:black_shulker_box", 64)
            self.set_item(12, "minecraft:heavy_core", 64)
            self.set_item(13, "minecraft:netherite_block", 64)

        elif kit_name == "builder":
            self.set_item(0, "minecraft:netherite_pickaxe", 1, {"minecraft:efficiency": 255, "minecraft:silk_touch": 1, "minecraft:unbreaking": 255}, unbreakable=True)
            self.set_item(1, "minecraft:netherite_shovel", 1, {"minecraft:efficiency": 255, "minecraft:silk_touch": 1, "minecraft:unbreaking": 255}, unbreakable=True)
            self.set_item(2, "minecraft:scaffolding", 64)
            self.set_item(3, "minecraft:black_shulker_box", 64)
            self.set_item(4, "minecraft:obsidian", 64)
            self.set_item(5, "minecraft:light", 64)
            self.set_item(6, "minecraft:elytra", 1, {"minecraft:unbreaking": 255}, unbreakable=True)
            self.set_item(7, "minecraft:firework_rocket", 64)
            self.set_item(8, "minecraft:enchanted_golden_apple", 64)

    # ==========================================
    # TAB 4: INFINITE POTION EFFECTS
    # ==========================================

    def _ensure_effects_list(self) -> TAG_List:
        if not self.player_data:
            raise ValueError("No player data loaded")
        key = "active_effects" if self.is_26x or "active_effects" in self.player_data or self.data_version >= 3463 else "ActiveEffects"
        if key not in self.player_data or not isinstance(self.player_data[key], TAG_List):
            self.player_data[key] = TAG_List(TAG_COMPOUND, [])
        return self.player_data[key]

    def get_effects(self) -> List[Dict[str, Any]]:
        if not self.player_data:
            return []
        eff_list = None
        if "active_effects" in self.player_data:
            eff_list = self.player_data["active_effects"]
        elif "ActiveEffects" in self.player_data:
            eff_list = self.player_data["ActiveEffects"]

        if not isinstance(eff_list, TAG_List):
            return []

        results = []
        for e in eff_list:
            if not isinstance(e, TAG_Compound):
                continue
            eid = str(e.get("id", e.get("Id", TAG_String(""))).to_py())
            amp = int(e.get("amplifier", e.get("Amplifier", TAG_Byte(0))).to_py())
            dur = int(e.get("duration", e.get("Duration", TAG_Int(0))).to_py())
            amb = bool(e.get("ambient", e.get("Ambient", TAG_Byte(0))).to_py() == 1)
            part = bool(e.get("show_particles", e.get("ShowParticles", TAG_Byte(1))).to_py() == 1)
            results.append({
                "id": eid,
                "amplifier": amp,
                "duration": dur,
                "ambient": amb,
                "show_particles": part
            })
        return results

    def add_effect(self, effect_id: str, amplifier: int = 4, duration: int = -1,
                   ambient: bool = False, show_particles: bool = False) -> None:
        """Add or update an active potion effect."""
        eff_list = self._ensure_effects_list()
        eff_list.value = [e for e in eff_list.value if isinstance(e, TAG_Compound) and str(e.get("id", e.get("Id", TAG_String(""))).to_py()) != effect_id]

        comp = TAG_Compound()
        if self.is_26x or "active_effects" in self.player_data or self.data_version >= 3463:
            comp["id"] = TAG_String(effect_id)
            comp["amplifier"] = TAG_Byte(amplifier)
            comp["duration"] = TAG_Int(duration)
            comp["ambient"] = TAG_Byte(1 if ambient else 0)
            comp["show_particles"] = TAG_Byte(1 if show_particles else 0)
            comp["show_icon"] = TAG_Byte(1)
        else:
            comp["Id"] = TAG_String(effect_id)
            comp["Amplifier"] = TAG_Byte(amplifier)
            comp["Duration"] = TAG_Int(duration)
            comp["Ambient"] = TAG_Byte(1 if ambient else 0)
            comp["ShowParticles"] = TAG_Byte(1 if show_particles else 0)
            comp["ShowIcon"] = TAG_Byte(1)

        eff_list.append(comp)

    def remove_effect(self, effect_id: str) -> None:
        eff_list = self._ensure_effects_list()
        eff_list.value = [e for e in eff_list.value if isinstance(e, TAG_Compound) and str(e.get("id", e.get("Id", TAG_String(""))).to_py()) != effect_id]

    def clear_effects(self) -> None:
        eff_list = self._ensure_effects_list()
        eff_list.value = []

    def inject_god_buffs(self) -> None:
        """Inject core god status buffs with clean screen (zero particles, duration -1)."""
        buffs = [
            ("minecraft:night_vision", 0),
            ("minecraft:haste", 4),
            ("minecraft:resistance", 4),
            ("minecraft:regeneration", 4),
            ("minecraft:strength", 4),
            ("minecraft:speed", 2),
            ("minecraft:fire_resistance", 0),
            ("minecraft:water_breathing", 0),
            ("minecraft:saturation", 4),
            ("minecraft:conduit_power", 0),
            ("minecraft:dolphins_grace", 0),
            ("minecraft:hero_of_the_village", 4),
        ]
        for bid, amp in buffs:
            self.add_effect(bid, amplifier=amp, duration=-1, ambient=False, show_particles=False)

    # ==========================================
    # TAB 5: WORLD CONTROLLER, HARDCORE REVIVE & GAME RULES
    # ==========================================

    def get_gamemode(self) -> int:
        if self.player_data and "playerGameType" in self.player_data:
            pgm = int(self.player_data["playerGameType"].to_py())
            if pgm >= 0:
                return pgm
        if not self.level_data:
            return 0
        return int(self.level_data.get("GameType", TAG_Int(0)).to_py())

    def set_gamemode(self, mode: int) -> None:
        if self.level_data:
            self.level_data["GameType"] = TAG_Int(mode)
        if self.player_data:
            self.player_data["playerGameType"] = TAG_Int(mode)

    def get_cheats_enabled(self) -> bool:
        if not self.level_data:
            return False
        ac = self.level_data.get("allowCommands")
        return bool(ac and ac.to_py() == 1)

    def set_cheats_enabled(self, enabled: bool) -> None:
        if not self.level_data:
            return
        self.level_data["allowCommands"] = TAG_Byte(1 if enabled else 0)

    def get_hardcore(self) -> bool:
        if not self.level_data:
            return False
        diff_settings = self.level_data.get("difficulty_settings")
        if isinstance(diff_settings, TAG_Compound):
            hc = diff_settings.get("hardcore")
            if hc is not None:
                return bool(hc.to_py() == 1)
        hc = self.level_data.get("hardcore")
        return bool(hc and hc.to_py() == 1)

    def set_hardcore(self, enabled: bool) -> None:
        if not self.level_data:
            return
        val = TAG_Byte(1 if enabled else 0)
        self.level_data["hardcore"] = val
        diff_settings = self.level_data.get("difficulty_settings")
        if isinstance(diff_settings, TAG_Compound):
            diff_settings["hardcore"] = val

    def hardcore_revive(self, restore_survival: bool = True, remove_hardcore: bool = False) -> bool:
        """Revive a dead hardcore player, restore survival gamemode, reset death timers, and unlock difficulty."""
        if not self.player_data or not self.level_data:
            return False

        # 1. Restore max vitals & clear death timers
        max_h = max(20.0, self.get_attribute("minecraft:max_health"))
        self.refill_vitals(health=max_h, food=20, saturation=20.0, absorption=0.0)

        # 2. Reset gamemode from Spectator (3) back to Survival (0)
        if restore_survival:
            self.set_gamemode(0)
            self.player_data["playerGameType"] = TAG_Int(0)

        # 3. Handle hardcore flag & unlock difficulty if requested
        if remove_hardcore:
            self.set_hardcore(False)
            diff_settings = self.level_data.get("difficulty_settings")
            if isinstance(diff_settings, TAG_Compound):
                diff_settings["locked"] = TAG_Byte(0)
        else:
            self.set_hardcore(True)

        # 4. Enable god protection & flight
        self.set_god_mode(True)
        self.set_mayfly(True)
        self.set_cheats_enabled(True)

        # 5. Check player location
        pos = self.get_player_pos()
        if pos[1] <= -64.0:
            self.teleport_to_spawn()

        return True

    def get_difficulty(self) -> str:
        if not self.level_data:
            return "normal"
        diff_settings = self.level_data.get("difficulty_settings")
        if isinstance(diff_settings, TAG_Compound):
            d = diff_settings.get("difficulty")
            if d:
                return str(d.to_py()).lower()
        diff_byte = self.level_data.get("Difficulty")
        if diff_byte:
            mapping = {0: "peaceful", 1: "easy", 2: "normal", 3: "hard"}
            return mapping.get(int(diff_byte.to_py()), "normal")
        return "normal"

    def set_difficulty(self, diff_name: str) -> None:
        if not self.level_data:
            return
        diff_lower = diff_name.lower().strip()
        diff_settings = self.level_data.get("difficulty_settings")
        if isinstance(diff_settings, TAG_Compound):
            diff_settings["difficulty"] = TAG_String(diff_lower)
            # Unlock difficulty if player wants to change it
            diff_settings["locked"] = TAG_Byte(0)

        mapping = {"peaceful": 0, "easy": 1, "normal": 2, "hard": 3}
        if diff_lower in mapping:
            self.level_data["Difficulty"] = TAG_Byte(mapping[diff_lower])

    def get_weather(self) -> str:
        """Return current weather state: 'clear', 'rain', or 'thunder'."""
        if self.weather_data:
            thundering = bool(self.weather_data.get("thundering", self.weather_data.get("Thundering", TAG_Byte(0))).to_py() == 1)
            if thundering:
                return "thunder"
            raining = bool(self.weather_data.get("raining", self.weather_data.get("Raining", TAG_Byte(0))).to_py() == 1)
            if raining:
                return "rain"
            return "clear"
        return "clear"

    def set_weather(self, w_type: str) -> None:
        """Set weather to 'clear', 'rain', or 'thunder' across weather.dat and level.dat."""
        w_type = w_type.lower().strip()
        is_rain = w_type in ("rain", "thunder")
        is_thunder = (w_type == "thunder")

        if self.weather_data:
            if "raining" in self.weather_data or self.is_26x:
                self.weather_data["raining"] = TAG_Byte(1 if is_rain else 0)
                self.weather_data["thundering"] = TAG_Byte(1 if is_thunder else 0)
                self.weather_data["rain_time"] = TAG_Int(60000 if is_rain else 0)
                self.weather_data["thunder_time"] = TAG_Int(60000 if is_thunder else 0)
                self.weather_data["clear_weather_time"] = TAG_Int(0 if is_rain else 60000)
            else:
                self.weather_data["raining"] = TAG_Byte(1 if is_rain else 0)
                self.weather_data["thundering"] = TAG_Byte(1 if is_thunder else 0)
                self.weather_data["rainTime"] = TAG_Int(60000 if is_rain else 0)
                self.weather_data["thunderTime"] = TAG_Int(60000 if is_thunder else 0)
                self.weather_data["clearWeatherTime"] = TAG_Int(0 if is_rain else 60000)

        if self.level_data and self.weather_data != self.level_data:
            self.level_data["raining"] = TAG_Byte(1 if is_rain else 0)
            self.level_data["thundering"] = TAG_Byte(1 if is_thunder else 0)

    def get_game_rule(self, rule_key: str) -> Any:
        if not self.game_rules_data:
            return None
        rule_meta = GAME_RULES.get(rule_key)
        candidate_names = rule_meta["names"] if rule_meta else [rule_key, f"minecraft:{rule_key}"]

        for name in candidate_names:
            if name in self.game_rules_data:
                tag = self.game_rules_data[name]
                val = tag.to_py()
                if isinstance(val, str):
                    if val.lower() == "true":
                        return True
                    elif val.lower() == "false":
                        return False
                    try:
                        return int(val)
                    except ValueError:
                        return val
                elif isinstance(val, int):
                    return bool(val) if rule_meta and rule_meta["type"] == "bool" else val
                return val
        return rule_meta["default"] if rule_meta else None

    def set_game_rule(self, rule_key: str, value: Any) -> None:
        if not self.game_rules_data:
            return
        rule_meta = GAME_RULES.get(rule_key)
        candidate_names = rule_meta["names"] if rule_meta else [rule_key, f"minecraft:{rule_key}"]

        # 1. Update existing key if present in game_rules_data
        target_name = None
        for name in candidate_names:
            if name in self.game_rules_data:
                target_name = name
                break

        # 2. If not present, pick the appropriate modern/legacy name
        if not target_name:
            if self.is_26x:
                target_name = next((n for n in candidate_names if n.startswith("minecraft:")), f"minecraft:{rule_key}")
            else:
                target_name = candidate_names[-1] if candidate_names else rule_key

        if isinstance(value, bool):
            if self.is_26x or target_name.startswith("minecraft:"):
                self.game_rules_data[target_name] = TAG_Byte(1 if value else 0)
            else:
                self.game_rules_data[target_name] = TAG_String("true" if value else "false")
        elif isinstance(value, int):
            if self.is_26x or target_name.startswith("minecraft:"):
                self.game_rules_data[target_name] = TAG_Int(value)
            else:
                self.game_rules_data[target_name] = TAG_String(str(value))


def scan_all_worlds() -> List[WorldSave]:
    """Scan all default directories and return list of loaded WorldSave instances with launcher labels."""
    results: List[WorldSave] = []
    seen_paths = set()

    save_roots = get_default_save_dirs()
    for root, prof_name in save_roots:
        if not os.path.isdir(root):
            continue
        try:
            for item in os.listdir(root):
                full_path = os.path.join(root, item)
                if os.path.isdir(full_path) and full_path not in seen_paths:
                    level_file = os.path.join(full_path, "level.dat")
                    if os.path.isfile(level_file):
                        ws = WorldSave(full_path, profile_name=prof_name)
                        if ws.load():
                            results.append(ws)
                            seen_paths.add(full_path)
        except Exception:
            continue

    return results
