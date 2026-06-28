"""
ui_theme.py - Dark Obsidian Theme & Windows DWM Integration for CustomTkinter
Provides color palettes, fonts, and Windows 11 DWM dark mode attributes.
"""

from __future__ import annotations
import ctypes
from ctypes import c_int, byref, sizeof
import customtkinter as ctk

# Color Palette (Obsidian & Emerald / Amethyst)
BG_MAIN = "#0d1117"
BG_CARD = "#161b22"
BG_CARD_HOVER = "#1c2128"
BORDER_CARD = "#30363d"
INPUT_BG = "#21262d"
INPUT_BORDER = "#38434f"

ACCENT_EMERALD = "#10b981"
ACCENT_EMERALD_HOVER = "#059669"
ACCENT_AMETHYST = "#8b5cf6"
ACCENT_AMETHYST_HOVER = "#7c3aed"
ACCENT_CYAN = "#06b6d4"
ACCENT_GOLD = "#f59e0b"
ACCENT_RED = "#ef4444"
ACCENT_RED_HOVER = "#dc2626"

TEXT_PRIMARY = "#f0f6fc"
TEXT_SECONDARY = "#8b949e"
TEXT_MUTED = "#6e7681"

# Windows DWM constants
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38  # 1=Auto, 2=None, 3=Mica, 4=Acrylic

def apply_windows_dark_mode(hwnd: int) -> None:
    """Applies Windows 11 dark title bar and backdrop via DWM."""
    try:
        dwmapi = ctypes.windll.dwmapi
        dark_flag = c_int(1)
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, byref(dark_flag), sizeof(dark_flag))
        backdrop = c_int(3)  # Mica
        dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_SYSTEMBACKDROP_TYPE, byref(backdrop), sizeof(backdrop))
    except Exception:
        pass


def setup_theme() -> None:
    """Configure CustomTkinter global appearance."""
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
