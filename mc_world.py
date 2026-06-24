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

