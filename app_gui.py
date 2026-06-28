"""
app_gui.py - Modern Minecraft All-in-One Mod Menu & World Editor GUI
Built with CustomTkinter and dark obsidian glassmorphism.
Supports Minecraft 26.x and legacy 1.20 / 1.21 worlds.
Includes God-Item Forge, Inventory/EnderChest Editor, Attribute Matrix,
Infinite Potions, Hardcore Revive, Cheats Unlocker, and Weather Control.
"""

from __future__ import annotations
import os
import sys
import queue
import threading
from typing import Dict, List, Any, Optional

import customtkinter as ctk
from tkinter import messagebox

from nbt_core import NBTFile
from mc_catalog import (
    ATTRIBUTES, ENCHANTMENTS, POTIONS, GAME_RULES, ITEMS_CATALOG,
    ITEM_PRESETS, search_items
)
from mc_world import WorldSave, scan_all_worlds
import ui_theme


class MinecraftModMenuApp(ctk.CTk):
    """Main Minecraft Mod Menu Desktop Window."""

    def __init__(self):
        super().__init__()

        ui_theme.setup_theme()

        self.title("Minecraft All-in-One Mod Menu | external Desktop Editor")
        self.geometry("1120x760")
        self.minsize(1000, 700)
        self.configure(fg_color=ui_theme.BG_MAIN)

        self.msg_queue: queue.Queue = queue.Queue()
        self.worlds: List[WorldSave] = []
        self.world_map: Dict[str, WorldSave] = {}
        self.active_world: Optional[WorldSave] = None

        # Data-binding states
        self.attr_sliders: Dict[str, ctk.CTkSlider] = {}
        self.attr_labels: Dict[str, ctk.CTkLabel] = {}
        self.gamerule_switches: Dict[str, ctk.CTkSwitch] = {}
        self.current_container: str = "inv"  # "inv" or "ender"

        self._build_top_bar()
        self._build_tabs()
        self._build_status_bar()

        # Apply Windows 11 DWM Mica / dark title bar
        self.after(100, self._apply_dwm)
        self.after(50, self._process_queue)

        # Initial background scan
        self.refresh_worlds()

    def _apply_dwm(self):
        try:
            hwnd = self.winfo_id()
            ui_theme.apply_windows_dark_mode(hwnd)
        except Exception:
            pass

    def _process_queue(self):
        try:
            while not self.msg_queue.empty():
                msg_type, payload = self.msg_queue.get_nowait()
                if msg_type == "scan_done":
                    self._on_scan_completed(payload)
                elif msg_type == "save_done":
                    self._on_save_completed(payload)
                elif msg_type == "status":
                    self.set_status(payload)
                elif msg_type == "error":
                    self.save_btn.configure(state="normal")
                    self.refresh_btn.configure(state="normal")
                    self.set_status(f"Error: {payload}", is_error=True)
                    messagebox.showerror("Error", payload)
        finally:
            self.after(50, self._process_queue)

    def set_status(self, text: str, is_error: bool = False):
        color = ui_theme.ACCENT_RED if is_error else ui_theme.TEXT_SECONDARY
        self.status_lbl.configure(text=text, text_color=color)

    # ==========================================
    # UI CONSTRUCTION
    # ==========================================

    def _build_top_bar(self):
        self.top_frame = ctk.CTkFrame(self, fg_color=ui_theme.BG_CARD, corner_radius=10, border_width=1, border_color=ui_theme.BORDER_CARD)
        self.top_frame.pack(fill="x", padx=16, pady=(14, 8))

        # Title & Badge
        title_box = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        title_box.pack(side="left", padx=14, pady=10)

        title_lbl = ctk.CTkLabel(title_box, text="MINECRAFT MOD MENU", font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"), text_color=ui_theme.TEXT_PRIMARY)
        title_lbl.pack(side="left")

        badge_lbl = ctk.CTkLabel(title_box, text=" 26.x & 1.21 ", fg_color=ui_theme.ACCENT_AMETHYST, text_color="#ffffff", corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"))
        badge_lbl.pack(side="left", padx=8)

        # World Selector Dropdown
        world_box = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        world_box.pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(world_box, text="Target Save:", font=ctk.CTkFont(size=12), text_color=ui_theme.TEXT_SECONDARY).pack(side="left", padx=4)

        self.world_combo = ctk.CTkComboBox(
            world_box,
            values=["Scanning saves..."],
            width=320,
            command=self._on_world_selected,
            fg_color=ui_theme.INPUT_BG,
            border_color=ui_theme.INPUT_BORDER,
            button_color=ui_theme.ACCENT_EMERALD,
            button_hover_color=ui_theme.ACCENT_EMERALD_HOVER
        )
        self.world_combo.pack(side="left", padx=4)

        # Refresh Button
        self.refresh_btn = ctk.CTkButton(
            self.top_frame,
            text="Rescan",
            width=70,
            height=30,
            command=self.refresh_worlds,
            fg_color=ui_theme.INPUT_BG,
            hover_color=ui_theme.BG_CARD_HOVER,
            border_width=1,
            border_color=ui_theme.BORDER_CARD
        )
        self.refresh_btn.pack(side="left", padx=4)

        # Save Button
        self.save_btn = ctk.CTkButton(
            self.top_frame,
            text="Save to World",
            width=130,
            height=32,
            font=ctk.CTkFont(weight="bold"),
            command=self.save_active_world,
            fg_color=ui_theme.ACCENT_EMERALD,
            hover_color=ui_theme.ACCENT_EMERALD_HOVER,
            text_color="#ffffff"
        )
        self.save_btn.pack(side="right", padx=12, pady=10)

        # Backups button
        self.backup_btn = ctk.CTkButton(
            self.top_frame,
            text="Backups",
            width=80,
            height=32,
            command=self._show_backups_modal,
            fg_color=ui_theme.INPUT_BG,
            hover_color=ui_theme.BG_CARD_HOVER,
            border_width=1,
            border_color=ui_theme.BORDER_CARD
        )
        self.backup_btn.pack(side="right", padx=4, pady=10)

    def _build_tabs(self):
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=ui_theme.BG_CARD,
            segmented_button_fg_color=ui_theme.INPUT_BG,
            segmented_button_selected_color=ui_theme.ACCENT_EMERALD,
            segmented_button_selected_hover_color=ui_theme.ACCENT_EMERALD_HOVER,
            segmented_button_unselected_hover_color=ui_theme.BG_CARD_HOVER,
            text_color=ui_theme.TEXT_PRIMARY
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self.tab_player = self.tabview.add("Player Hacks & Vitals")
        self.tab_attrs = self.tabview.add("Attribute Matrix")
        self.tab_items = self.tabview.add("God-Item Forge")
        self.tab_potions = self.tabview.add("Infinite Buffs")
        self.tab_world = self.tabview.add("World & Rules")

        self._init_tab_player()
        self._init_tab_attrs()
        self._init_tab_items()
        self._init_tab_potions()
        self._init_tab_world()

    def _build_status_bar(self):
        status_frame = ctk.CTkFrame(self, fg_color="transparent", height=24)
        status_frame.pack(fill="x", padx=20, pady=(0, 6))

        self.status_lbl = ctk.CTkLabel(status_frame, text="Initializing...", font=ctk.CTkFont(size=11), text_color=ui_theme.TEXT_SECONDARY)
        self.status_lbl.pack(side="left")

        self.save_info_lbl = ctk.CTkLabel(status_frame, text="Auto-Backups: Active", font=ctk.CTkFont(size=11), text_color=ui_theme.ACCENT_EMERALD)
        self.save_info_lbl.pack(side="right")

    # ==========================================
    # TAB 1: PLAYER HACKS & VITALS
    # ==========================================

    def _init_tab_player(self):
        scroll = ctk.CTkScrollableFrame(self.tab_player, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        # 1. Toggles Row Card
        toggles_card = ctk.CTkFrame(scroll, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD)
        toggles_card.pack(fill="x", pady=6, padx=4)

        ctk.CTkLabel(toggles_card, text="CORE HACKS & ABILITIES", font=ctk.CTkFont(size=13, weight="bold"), text_color=ui_theme.TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(10, 6))

        toggles_grid = ctk.CTkFrame(toggles_card, fg_color="transparent")
        toggles_grid.pack(fill="x", padx=14, pady=(0, 12))

        self.switch_god = ctk.CTkSwitch(toggles_grid, text="God Mode (Invulnerable)", progress_color=ui_theme.ACCENT_EMERALD, font=ctk.CTkFont(weight="bold"))
        self.switch_god.grid(row=0, column=0, padx=12, pady=6, sticky="w")

        self.switch_flight = ctk.CTkSwitch(toggles_grid, text="Survival Creative Flight (mayfly)", progress_color=ui_theme.ACCENT_EMERALD, font=ctk.CTkFont(weight="bold"))
        self.switch_flight.grid(row=0, column=1, padx=12, pady=6, sticky="w")

        self.switch_flying = ctk.CTkSwitch(toggles_grid, text="Currently Flying in Air", progress_color=ui_theme.ACCENT_CYAN)
        self.switch_flying.grid(row=1, column=0, padx=12, pady=6, sticky="w")

        self.switch_instabuild = ctk.CTkSwitch(toggles_grid, text="Instant Mine & Build (instabuild)", progress_color=ui_theme.ACCENT_CYAN)
        self.switch_instabuild.grid(row=1, column=1, padx=12, pady=6, sticky="w")

        # 2. Vitals & XP Card
        vitals_card = ctk.CTkFrame(scroll, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD)
        vitals_card.pack(fill="x", pady=6, padx=4)

        ctk.CTkLabel(vitals_card, text="VITALS, HEARTS & XP LEVEL", font=ctk.CTkFont(size=13, weight="bold"), text_color=ui_theme.TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(10, 6))

        v_actions = ctk.CTkFrame(vitals_card, fg_color="transparent")
        v_actions.pack(fill="x", padx=14, pady=6)

        ctk.CTkButton(v_actions, text="Max Health & Full Hunger", width=190, fg_color=ui_theme.ACCENT_EMERALD, hover_color=ui_theme.ACCENT_EMERALD_HOVER, command=self._action_max_vitals).pack(side="left", padx=4)
        ctk.CTkButton(v_actions, text="+40 Golden Hearts (Absorption)", width=220, fg_color=ui_theme.ACCENT_GOLD, hover_color="#d97706", text_color="#111827", command=self._action_golden_hearts).pack(side="left", padx=4)
        ctk.CTkButton(v_actions, text="Revive if Dead (Reset Timers)", width=210, fg_color=ui_theme.ACCENT_AMETHYST, hover_color=ui_theme.ACCENT_AMETHYST_HOVER, command=self._action_revive_player).pack(side="left", padx=4)

        # XP Level Row
        xp_frame = ctk.CTkFrame(vitals_card, fg_color="transparent")
        xp_frame.pack(fill="x", padx=14, pady=(10, 14))

        ctk.CTkLabel(xp_frame, text="Inject XP Level:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=4)
        for lvl in [30, 100, 1000, 10000]:
            ctk.CTkButton(xp_frame, text=f"Lvl {lvl:,}", width=80, height=26, fg_color=ui_theme.INPUT_BG, hover_color=ui_theme.BG_CARD_HOVER, border_width=1, border_color=ui_theme.BORDER_CARD, command=lambda l=lvl: self._action_set_xp(l)).pack(side="left", padx=4)

        self.custom_xp_entry = ctk.CTkEntry(xp_frame, width=80, height=26, placeholder_text="Custom", fg_color=ui_theme.INPUT_BG)
        self.custom_xp_entry.pack(side="left", padx=(10, 4))
        ctk.CTkButton(xp_frame, text="Set", width=50, height=26, command=self._action_set_custom_xp).pack(side="left")

        # 3. Teleport & Death Recovery Card
        tp_card = ctk.CTkFrame(scroll, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD)
        tp_card.pack(fill="x", pady=6, padx=4)

        ctk.CTkLabel(tp_card, text="TELEPORT & DEATH RECOVERY", font=ctk.CTkFont(size=13, weight="bold"), text_color=ui_theme.TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(10, 4))

        self.death_info_lbl = ctk.CTkLabel(tp_card, text="Last Death: None recorded", font=ctk.CTkFont(size=12), text_color=ui_theme.TEXT_SECONDARY)
        self.death_info_lbl.pack(anchor="w", padx=14, pady=2)

        tp_btns = ctk.CTkFrame(tp_card, fg_color="transparent")
        tp_btns.pack(fill="x", padx=14, pady=8)

        self.tp_death_btn = ctk.CTkButton(tp_btns, text="Teleport to Last Death Coordinates", fg_color=ui_theme.ACCENT_CYAN, hover_color="#0891b2", text_color="#111827", font=ctk.CTkFont(weight="bold"), command=self._action_tp_death)
        self.tp_death_btn.pack(side="left", padx=4)

        ctk.CTkButton(tp_btns, text="Teleport to World Spawn (+2 Blocks)", fg_color=ui_theme.INPUT_BG, hover_color=ui_theme.BG_CARD_HOVER, border_width=1, border_color=ui_theme.BORDER_CARD, command=self._action_tp_spawn).pack(side="left", padx=8)

        # Custom Teleport Row
        custom_tp = ctk.CTkFrame(tp_card, fg_color="transparent")
        custom_tp.pack(fill="x", padx=14, pady=(4, 14))

        ctk.CTkLabel(custom_tp, text="Target X:").pack(side="left", padx=2)
        self.tp_x_entry = ctk.CTkEntry(custom_tp, width=80, fg_color=ui_theme.INPUT_BG)
        self.tp_x_entry.pack(side="left", padx=4)

        ctk.CTkLabel(custom_tp, text="Y:").pack(side="left", padx=2)
        self.tp_y_entry = ctk.CTkEntry(custom_tp, width=70, fg_color=ui_theme.INPUT_BG)
        self.tp_y_entry.pack(side="left", padx=4)

        ctk.CTkLabel(custom_tp, text="Z:").pack(side="left", padx=2)
        self.tp_z_entry = ctk.CTkEntry(custom_tp, width=80, fg_color=ui_theme.INPUT_BG)
        self.tp_z_entry.pack(side="left", padx=4)

        ctk.CTkLabel(custom_tp, text="Dim:").pack(side="left", padx=(8, 2))
        self.tp_dim_combo = ctk.CTkComboBox(custom_tp, values=["minecraft:overworld", "minecraft:the_nether", "minecraft:the_end"], width=170, fg_color=ui_theme.INPUT_BG)
        self.tp_dim_combo.set("minecraft:overworld")
        self.tp_dim_combo.pack(side="left", padx=4)

        ctk.CTkButton(custom_tp, text="Teleport Now", width=100, fg_color=ui_theme.ACCENT_EMERALD, hover_color=ui_theme.ACCENT_EMERALD_HOVER, command=self._action_custom_tp).pack(side="left", padx=8)

    # ==========================================
    # TAB 2: BASE ATTRIBUTE MATRIX
    # ==========================================

    def _init_tab_attrs(self):
        container = ctk.CTkFrame(self.tab_attrs, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=8, pady=8)

        # Presets Bar
        preset_bar = ctk.CTkFrame(container, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD)
        preset_bar.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(preset_bar, text="Attribute Presets:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=12, pady=8)

        ctk.CTkButton(preset_bar, text="Super Soldier", width=110, height=28, fg_color=ui_theme.ACCENT_EMERALD, hover_color=ui_theme.ACCENT_EMERALD_HOVER, command=lambda: self._apply_attr_preset("super_soldier")).pack(side="left", padx=4)
        ctk.CTkButton(preset_bar, text="Giant Morph (3.5x)", width=130, height=28, fg_color=ui_theme.ACCENT_AMETHYST, hover_color=ui_theme.ACCENT_AMETHYST_HOVER, command=lambda: self._apply_attr_preset("giant")).pack(side="left", padx=4)
        ctk.CTkButton(preset_bar, text="Ant Morph (0.2x)", width=120, height=28, fg_color=ui_theme.ACCENT_CYAN, hover_color="#0891b2", text_color="#111827", command=lambda: self._apply_attr_preset("ant")).pack(side="left", padx=4)
        ctk.CTkButton(preset_bar, text="Reset to Vanilla Defaults", width=170, height=28, fg_color=ui_theme.INPUT_BG, hover_color=ui_theme.BG_CARD_HOVER, border_width=1, border_color=ui_theme.BORDER_CARD, command=self._reset_all_attrs).pack(side="right", padx=12)

        # Scrollable attributes list
        scroll = ctk.CTkScrollableFrame(container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        for attr_id, meta in ATTRIBUTES.items():
            card = ctk.CTkFrame(scroll, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD)
            card.pack(fill="x", pady=4, padx=2)

            info_row = ctk.CTkFrame(card, fg_color="transparent")
            info_row.pack(fill="x", padx=12, pady=(8, 2))

            name_lbl = ctk.CTkLabel(info_row, text=meta["name"], font=ctk.CTkFont(size=13, weight="bold"), text_color=ui_theme.TEXT_PRIMARY)
            name_lbl.pack(side="left")

            desc_lbl = ctk.CTkLabel(info_row, text=f"({meta['desc']})", font=ctk.CTkFont(size=11), text_color=ui_theme.TEXT_MUTED)
            desc_lbl.pack(side="left", padx=8)

            val_lbl = ctk.CTkLabel(info_row, text=f"{meta['default']:.2f}", font=ctk.CTkFont(size=13, weight="bold"), text_color=ui_theme.ACCENT_EMERALD)
            val_lbl.pack(side="right")
            self.attr_labels[attr_id] = val_lbl

            ctrl_row = ctk.CTkFrame(card, fg_color="transparent")
            ctrl_row.pack(fill="x", padx=12, pady=(0, 8))

            num_steps = max(1, int((meta["max"] - meta["min"]) / meta["step"]))
            slider = ctk.CTkSlider(
                ctrl_row,
                from_=meta["min"],
                to=meta["max"],
                number_of_steps=num_steps,
                progress_color=ui_theme.ACCENT_EMERALD,
                button_color=ui_theme.ACCENT_EMERALD,
                button_hover_color=ui_theme.ACCENT_EMERALD_HOVER,
                command=lambda val, aid=attr_id: self._on_attr_slider_changed(aid, val)
            )
            slider.set(meta["default"])
            slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
            self.attr_sliders[attr_id] = slider

            ctk.CTkButton(
                ctrl_row,
                text="Default",
                width=60,
                height=22,
                fg_color=ui_theme.INPUT_BG,
                hover_color=ui_theme.BG_CARD_HOVER,
                font=ctk.CTkFont(size=11),
                command=lambda aid=attr_id, defval=meta["default"]: self._set_attr_single(aid, defval)
            ).pack(side="right")

    def _on_attr_slider_changed(self, attr_id: str, value: float):
        self.attr_labels[attr_id].configure(text=f"{value:.2f}")
        if self.active_world:
            self.active_world.set_attribute(attr_id, float(value))

    def _set_attr_single(self, attr_id: str, value: float):
        self.attr_sliders[attr_id].set(value)
        self.attr_labels[attr_id].configure(text=f"{value:.2f}")
        if self.active_world:
            self.active_world.set_attribute(attr_id, float(value))

    # ==========================================
    # TAB 3: GOD-ITEM FORGE, INVENTORY & ENDER CHEST
    # ==========================================

    def _init_tab_items(self):
        container = ctk.CTkFrame(self.tab_items, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=8, pady=8)

        # Quick Kits Top Bar
        kit_bar = ctk.CTkFrame(container, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD)
        kit_bar.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(kit_bar, text="One-Click God Kits:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=12, pady=8)

        ctk.CTkButton(kit_bar, text="Full God Netherite Kit (32k / Lvl 255)", fg_color=ui_theme.ACCENT_EMERALD, hover_color=ui_theme.ACCENT_EMERALD_HOVER, command=self._action_kit_netherite).pack(side="left", padx=4)
        ctk.CTkButton(kit_bar, text="Builder Megakit", fg_color=ui_theme.ACCENT_AMETHYST, hover_color=ui_theme.ACCENT_AMETHYST_HOVER, command=self._action_kit_builder).pack(side="left", padx=4)
        ctk.CTkButton(kit_bar, text="Repair All Items (0 Damage)", fg_color=ui_theme.ACCENT_CYAN, hover_color="#0891b2", text_color="#111827", command=self._action_repair_items).pack(side="left", padx=4)
        ctk.CTkButton(kit_bar, text="Clear Active Container", fg_color=ui_theme.ACCENT_RED, hover_color=ui_theme.ACCENT_RED_HOVER, command=self._action_clear_items).pack(side="right", padx=12)

        # Main Forge Split: Left is Item Creator Form, Right is Container Slot Viewer
        split_frame = ctk.CTkFrame(container, fg_color="transparent")
        split_frame.pack(fill="both", expand=True)

        # Left: Forge Form
        forge_frame = ctk.CTkFrame(split_frame, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD)
        forge_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))

        ctk.CTkLabel(forge_frame, text="GOD-ITEM FORGE & SPAWNER", font=ctk.CTkFont(size=13, weight="bold"), text_color=ui_theme.TEXT_PRIMARY).pack(anchor="w", padx=12, pady=(10, 4))

        form_scroll = ctk.CTkScrollableFrame(forge_frame, fg_color="transparent")
        form_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Quick Item Presets Row
        preset_box = ctk.CTkFrame(form_scroll, fg_color="transparent")
        preset_box.pack(fill="x", pady=(2, 4))
        ctk.CTkLabel(preset_box, text="Item Presets:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(0, 4))
        for pkey, pmeta in ITEM_PRESETS.items():
            ctk.CTkButton(
                preset_box,
                text=pmeta["name"].split(" ")[0],
                width=65,
                height=22,
                font=ctk.CTkFont(size=10),
                fg_color=ui_theme.INPUT_BG,
                hover_color=ui_theme.BG_CARD_HOVER,
                border_width=1,
                border_color=ui_theme.BORDER_CARD,
                command=lambda k=pkey: self._apply_item_preset(k)
            ).pack(side="left", padx=2)

        # Item Search Bar
        ctk.CTkLabel(form_scroll, text="Search & Select Item:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(4, 2))
        self.item_search_entry = ctk.CTkEntry(form_scroll, placeholder_text="Filter items (e.g. sword, mace, apple)...", fg_color=ui_theme.INPUT_BG)
        self.item_search_entry.pack(fill="x", pady=(0, 4))
        self.item_search_entry.bind("<KeyRelease>", self._on_item_search_changed)

        item_names = [f"{i['name']} ({i['id']})" for i in ITEMS_CATALOG]
        self.item_select_combo = ctk.CTkComboBox(form_scroll, values=item_names, width=320, fg_color=ui_theme.INPUT_BG)
        self.item_select_combo.set(item_names[0])
        self.item_select_combo.pack(fill="x", pady=2)

        # Target Slot & Stack Count
        row1 = ctk.CTkFrame(form_scroll, fg_color="transparent")
        row1.pack(fill="x", pady=6)

        ctk.CTkLabel(row1, text="Target Slot (0-35, 100-103):").pack(side="left", padx=(0, 4))
        self.slot_entry = ctk.CTkEntry(row1, width=60, fg_color=ui_theme.INPUT_BG)
        self.slot_entry.insert(0, "0")
        self.slot_entry.pack(side="left", padx=4)

        ctk.CTkLabel(row1, text="Count:").pack(side="left", padx=(8, 4))
        self.count_entry = ctk.CTkEntry(row1, width=60, fg_color=ui_theme.INPUT_BG)
        self.count_entry.insert(0, "1")
        self.count_entry.pack(side="left", padx=4)

        self.unbreakable_chk = ctk.CTkCheckBox(row1, text="Unbreakable", fg_color=ui_theme.ACCENT_EMERALD)
        self.unbreakable_chk.select()
        self.unbreakable_chk.pack(side="left", padx=10)

        # Custom Display Name
        ctk.CTkLabel(form_scroll, text="Custom Display Name:").pack(anchor="w", pady=(4, 2))
        self.custom_name_entry = ctk.CTkEntry(form_scroll, placeholder_text="e.g. Void Slicer 32k", fg_color=ui_theme.INPUT_BG)
        self.custom_name_entry.pack(fill="x", pady=2)

        # Custom Lore
        ctk.CTkLabel(form_scroll, text="Custom Lore (separated by '|' or lines):").pack(anchor="w", pady=(4, 2))
        self.custom_lore_entry = ctk.CTkEntry(form_scroll, placeholder_text="e.g. Forged in cosmic fire | Absolute destruction", fg_color=ui_theme.INPUT_BG)
        self.custom_lore_entry.pack(fill="x", pady=2)

        # Enchantment Pickers
        ctk.CTkLabel(form_scroll, text="God Enchantments (Level 255):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(8, 4))
        self.ench_vars: Dict[str, ctk.CTkCheckBox] = {}

        ench_grid = ctk.CTkFrame(form_scroll, fg_color="transparent")
        ench_grid.pack(fill="x", pady=2)

        popular_enchants = [
            ("Sharpness", "minecraft:sharpness"),
            ("Efficiency", "minecraft:efficiency"),
            ("Fortune", "minecraft:fortune"),
            ("Looting", "minecraft:looting"),
            ("Protection", "minecraft:protection"),
            ("Unbreaking", "minecraft:unbreaking"),
            ("Mending", "minecraft:mending"),
            ("Power", "minecraft:power"),
            ("Density", "minecraft:density"),
            ("Breach", "minecraft:breach"),
            ("Feather Falling", "minecraft:feather_falling"),
            ("Fire Aspect", "minecraft:fire_aspect"),
        ]
        for idx, (lbl, eid) in enumerate(popular_enchants):
            cb = ctk.CTkCheckBox(ench_grid, text=f"{lbl} 255", font=ctk.CTkFont(size=11), fg_color=ui_theme.ACCENT_EMERALD)
            cb.grid(row=idx // 2, column=idx % 2, padx=6, pady=4, sticky="w")
            self.ench_vars[eid] = cb

        # Forge Button
        ctk.CTkButton(
            form_scroll,
            text="Inject Forged Item into Target Slot",
            height=34,
            font=ctk.CTkFont(weight="bold"),
            fg_color=ui_theme.ACCENT_EMERALD,
            hover_color=ui_theme.ACCENT_EMERALD_HOVER,
            command=self._action_forge_item
        ).pack(fill="x", pady=(12, 6))

        # Right: Container Slot Viewer (Inventory vs Ender Chest)
        view_frame = ctk.CTkFrame(split_frame, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD, width=420)
        view_frame.pack(side="right", fill="both", expand=True)

        view_header = ctk.CTkFrame(view_frame, fg_color="transparent")
        view_header.pack(fill="x", padx=12, pady=(10, 4))

        ctk.CTkLabel(view_header, text="CONTAINER VIEWER", font=ctk.CTkFont(size=13, weight="bold"), text_color=ui_theme.TEXT_PRIMARY).pack(side="left")

        # Container Segmented Button (Inventory vs Ender Chest)
        self.container_seg = ctk.CTkSegmentedButton(
            view_frame,
            values=["Player Inventory", "Ender Chest"],
            command=self._on_container_type_changed,
            fg_color=ui_theme.INPUT_BG,
            selected_color=ui_theme.ACCENT_EMERALD,
            selected_hover_color=ui_theme.ACCENT_EMERALD_HOVER
        )
        self.container_seg.set("Player Inventory")
        self.container_seg.pack(fill="x", padx=12, pady=(4, 6))

        self.inv_list_scroll = ctk.CTkScrollableFrame(view_frame, fg_color="transparent")
        self.inv_list_scroll.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _on_item_search_changed(self, event=None):
        query = self.item_search_entry.get().strip()
        matched = search_items(query)
        names = [f"{i['name']} ({i['id']})" for i in matched]
        if names:
            self.item_select_combo.configure(values=names)
            self.item_select_combo.set(names[0])
        else:
            self.item_select_combo.configure(values=["No items match"])

    def _apply_item_preset(self, preset_key: str):
        preset = ITEM_PRESETS.get(preset_key)
        if not preset:
            return

        # Select item in combobox
        target_name = f"{preset['id'].replace('minecraft:', '').replace('_', ' ').title()} ({preset['id']})"
        for opt in self.item_select_combo.cget("values"):
            if preset["id"] in opt:
                self.item_select_combo.set(opt)
                break

        self.count_entry.delete(0, "end")
        self.count_entry.insert(0, str(preset["count"]))

        if preset.get("unbreakable"):
            self.unbreakable_chk.select()
        else:
            self.unbreakable_chk.deselect()

        self.custom_name_entry.delete(0, "end")
        self.custom_name_entry.insert(0, preset.get("custom_name", ""))

        self.custom_lore_entry.delete(0, "end")
        self.custom_lore_entry.insert(0, preset.get("lore", "").replace("\n", " | "))

        # Set enchantment checkboxes
        penchs = preset.get("enchantments", {})
        for eid, cb in self.ench_vars.items():
            if eid in penchs:
                cb.select()
            else:
                cb.deselect()

        self.set_status(f"Loaded item preset: {preset['name']}.")

    def _on_container_type_changed(self, value: str):
        self.current_container = "ender" if value == "Ender Chest" else "inv"
        self._refresh_inventory_viewer()

    # ==========================================
    # TAB 4: INFINITE POTION EFFECTS
    # ==========================================

    def _init_tab_potions(self):
        container = ctk.CTkFrame(self.tab_potions, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=8, pady=8)

        # Quick Buffs Top Card
        buff_bar = ctk.CTkFrame(container, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD)
        buff_bar.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(buff_bar, text="One-Click God Status:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=12, pady=8)

        ctk.CTkButton(
            buff_bar,
            text="Inject All God Buffs (Clean Screen: Zero Particles)",
            font=ctk.CTkFont(weight="bold"),
            fg_color=ui_theme.ACCENT_EMERALD,
            hover_color=ui_theme.ACCENT_EMERALD_HOVER,
            command=self._action_god_buffs
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            buff_bar,
            text="Clear All Status Effects",
            fg_color=ui_theme.ACCENT_RED,
            hover_color=ui_theme.ACCENT_RED_HOVER,
            command=self._action_clear_potions
        ).pack(side="right", padx=12)

        # Potion Selection Matrix
        scroll = ctk.CTkScrollableFrame(container, fg_color="transparent")
        scroll.pack(fill="both", expand=True)

        for pid, meta in POTIONS.items():
            card = ctk.CTkFrame(scroll, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD)
            card.pack(fill="x", pady=4, padx=2)

            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", padx=12, pady=8)

            ctk.CTkLabel(left, text=meta["name"], font=ctk.CTkFont(size=13, weight="bold"), text_color=ui_theme.TEXT_PRIMARY).pack(anchor="w")
            ctk.CTkLabel(left, text=meta["desc"], font=ctk.CTkFont(size=11), text_color=ui_theme.TEXT_MUTED).pack(anchor="w")

            right = ctk.CTkFrame(card, fg_color="transparent")
            right.pack(side="right", padx=12, pady=8)

            ctk.CTkButton(
                right,
                text="Apply Infinite (Lvl 5)",
                width=150,
                height=28,
                fg_color=ui_theme.ACCENT_EMERALD,
                hover_color=ui_theme.ACCENT_EMERALD_HOVER,
                command=lambda p=pid: self._action_apply_single_potion(p, 4)
            ).pack(side="left", padx=4)

            ctk.CTkButton(
                right,
                text="Remove",
                width=70,
                height=28,
                fg_color=ui_theme.INPUT_BG,
                hover_color=ui_theme.BG_CARD_HOVER,
                border_width=1,
                border_color=ui_theme.BORDER_CARD,
                command=lambda p=pid: self._action_remove_single_potion(p)
            ).pack(side="left", padx=4)

    # ==========================================
    # TAB 5: WORLD CONTROLLER & GAME RULES
    # ==========================================

    def _init_tab_world(self):
        scroll = ctk.CTkScrollableFrame(self.tab_world, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=8, pady=8)

        # 1. World State Card
        world_card = ctk.CTkFrame(scroll, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD)
        world_card.pack(fill="x", pady=6, padx=4)

        ctk.CTkLabel(world_card, text="WORLD MODE & CHEATS CONTROLLER", font=ctk.CTkFont(size=13, weight="bold"), text_color=ui_theme.TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(10, 6))

        mode_row = ctk.CTkFrame(world_card, fg_color="transparent")
        mode_row.pack(fill="x", padx=14, pady=6)

        ctk.CTkLabel(mode_row, text="Game Mode:").pack(side="left", padx=(0, 6))
        self.gamemode_combo = ctk.CTkComboBox(mode_row, values=["Survival", "Creative", "Adventure", "Spectator"], width=130, fg_color=ui_theme.INPUT_BG, command=self._on_gamemode_changed)
        self.gamemode_combo.pack(side="left", padx=4)

        ctk.CTkLabel(mode_row, text="Difficulty:").pack(side="left", padx=(16, 6))
        self.diff_combo = ctk.CTkComboBox(mode_row, values=["peaceful", "easy", "normal", "hard"], width=120, fg_color=ui_theme.INPUT_BG, command=self._on_diff_changed)
        self.diff_combo.pack(side="left", padx=4)

        toggles_row = ctk.CTkFrame(world_card, fg_color="transparent")
        toggles_row.pack(fill="x", padx=14, pady=(6, 14))

        self.switch_cheats = ctk.CTkSwitch(toggles_row, text="Allow Commands / Cheats (allowCommands: 1b)", progress_color=ui_theme.ACCENT_EMERALD, font=ctk.CTkFont(weight="bold"), command=self._on_cheats_toggled)
        self.switch_cheats.pack(side="left", padx=(0, 20))

        self.switch_hardcore = ctk.CTkSwitch(toggles_row, text="Hardcore Mode", progress_color=ui_theme.ACCENT_RED, command=self._on_hardcore_toggled)
        self.switch_hardcore.pack(side="left")

        # 2. Hardcore Revive & Cheats Unlocker Action Bar
        revive_card = ctk.CTkFrame(scroll, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD)
        revive_card.pack(fill="x", pady=6, padx=4)

        ctk.CTkLabel(revive_card, text="HARDCORE REVIVE & EMERGENCY CHEATS UNLOCKER", font=ctk.CTkFont(size=13, weight="bold"), text_color=ui_theme.TEXT_PRIMARY).pack(anchor="w", padx=14, pady=(10, 4))

        revive_row = ctk.CTkFrame(revive_card, fg_color="transparent")
        revive_row.pack(fill="x", padx=14, pady=(4, 12))

        ctk.CTkButton(
            revive_row,
            text="Hardcore Revive (Restore Survival, Full Health & God Mode)",
            font=ctk.CTkFont(weight="bold"),
            fg_color=ui_theme.ACCENT_AMETHYST,
            hover_color=ui_theme.ACCENT_AMETHYST_HOVER,
            command=self._action_hardcore_revive
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            revive_row,
            text="Unlock Cheats & Commands (allowCommands: 1b)",
            fg_color=ui_theme.ACCENT_EMERALD,
            hover_color=ui_theme.ACCENT_EMERALD_HOVER,
            command=self._action_unlock_cheats
        ).pack(side="left", padx=8)

        # 3. Weather Controller Card
        weather_card = ctk.CTkFrame(scroll, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD)
        weather_card.pack(fill="x", pady=6, padx=4)

        weather_top = ctk.CTkFrame(weather_card, fg_color="transparent")
        weather_top.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(weather_top, text="WEATHER CONTROLLER (weather.dat / level.dat)", font=ctk.CTkFont(size=13, weight="bold"), text_color=ui_theme.TEXT_PRIMARY).pack(side="left")
        self.weather_status_lbl = ctk.CTkLabel(weather_top, text="Current: Clear Sky", font=ctk.CTkFont(size=12), text_color=ui_theme.ACCENT_CYAN)
        self.weather_status_lbl.pack(side="right")

        weather_btns = ctk.CTkFrame(weather_card, fg_color="transparent")
        weather_btns.pack(fill="x", padx=14, pady=(4, 12))

        ctk.CTkButton(weather_btns, text="Clear Sky", width=120, fg_color=ui_theme.ACCENT_CYAN, hover_color="#0891b2", text_color="#111827", command=lambda: self._set_weather("clear")).pack(side="left", padx=4)
        ctk.CTkButton(weather_btns, text="Rain", width=100, fg_color=ui_theme.INPUT_BG, hover_color=ui_theme.BG_CARD_HOVER, border_width=1, border_color=ui_theme.BORDER_CARD, command=lambda: self._set_weather("rain")).pack(side="left", padx=4)
        ctk.CTkButton(weather_btns, text="Thunderstorm", width=130, fg_color=ui_theme.ACCENT_AMETHYST, hover_color=ui_theme.ACCENT_AMETHYST_HOVER, command=lambda: self._set_weather("thunder")).pack(side="left", padx=4)

        # 4. Game Rules Switchboard Card
        rules_card = ctk.CTkFrame(scroll, fg_color=ui_theme.BG_MAIN, corner_radius=8, border_width=1, border_color=ui_theme.BORDER_CARD)
        rules_card.pack(fill="x", pady=6, padx=4)

        rules_top = ctk.CTkFrame(rules_card, fg_color="transparent")
        rules_top.pack(fill="x", padx=14, pady=(10, 4))

        ctk.CTkLabel(rules_top, text="GAME RULES SWITCHBOARD", font=ctk.CTkFont(size=13, weight="bold"), text_color=ui_theme.TEXT_PRIMARY).pack(side="left")

        ctk.CTkButton(rules_top, text="Enable Safe Exploration Preset", height=24, fg_color=ui_theme.ACCENT_EMERALD, hover_color=ui_theme.ACCENT_EMERALD_HOVER, command=self._action_safe_rules_preset).pack(side="right")

        rules_grid = ctk.CTkFrame(rules_card, fg_color="transparent")
        rules_grid.pack(fill="x", padx=14, pady=(4, 14))

        for idx, (rk, meta) in enumerate(GAME_RULES.items()):
            if meta["type"] == "bool":
                sw = ctk.CTkSwitch(
                    rules_grid,
                    text=meta["name"],
                    progress_color=ui_theme.ACCENT_EMERALD,
                    command=lambda k=rk: self._on_gamerule_toggled(k)
                )
                sw.grid(row=idx // 2, column=idx % 2, padx=12, pady=6, sticky="w")
                self.gamerule_switches[rk] = sw

    # ==========================================
    # DATA LOADING & SYNC
    # ==========================================

    def refresh_worlds(self):
        self.refresh_btn.configure(state="disabled")
        self.set_status("Scanning for Minecraft worlds...")
        threading.Thread(target=self._worker_scan_worlds, daemon=True).start()

    def _worker_scan_worlds(self):
        try:
            worlds = scan_all_worlds()
            self.msg_queue.put(("scan_done", worlds))
        except Exception as e:
            self.msg_queue.put(("error", f"Scan failed: {str(e)}"))

    def _on_scan_completed(self, worlds: List[WorldSave]):
        self.refresh_btn.configure(state="normal")
        self.worlds = worlds
        if not worlds:
            self.world_combo.configure(values=["No saves found"])
            self.set_status("No Minecraft worlds found in standard save directories.")
            return

        self.world_map = {w.display_label: w for w in worlds}
        display_names = list(self.world_map.keys())

        self.world_combo.configure(values=display_names)
        self.world_combo.set(display_names[0])
        self._load_world_into_ui(worlds[0])
        self.set_status(f"Discovered {len(worlds)} saves. Loaded: {worlds[0].world_name}")

    def _on_world_selected(self, choice: str):
        target = self.world_map.get(choice)
        if target:
            self._load_world_into_ui(target)
            self.set_status(f"Loaded world: {target.world_name}")

    def _load_world_into_ui(self, w: WorldSave):
        self.active_world = w

        # Tab 1: Hacks & Vitals
        if w.get_god_mode():
            self.switch_god.select()
        else:
            self.switch_god.deselect()

        if w.get_mayfly():
            self.switch_flight.select()
        else:
            self.switch_flight.deselect()

        if w.get_flying():
            self.switch_flying.select()
        else:
            self.switch_flying.deselect()

        if w.get_instabuild():
            self.switch_instabuild.select()
        else:
            self.switch_instabuild.deselect()

        # Death location
        ldl = w.get_last_death_location()
        if ldl:
            self.death_info_lbl.configure(text=f"Last Death Location: X: {ldl['x']}, Y: {ldl['y']}, Z: {ldl['z']} in {ldl['dimension']}", text_color=ui_theme.ACCENT_CYAN)
        else:
            self.death_info_lbl.configure(text="Last Death Location: None recorded", text_color=ui_theme.TEXT_SECONDARY)

        # Tab 2: Attributes
        for attr_id, slider in self.attr_sliders.items():
            val = w.get_attribute(attr_id)
            slider.set(val)
            if attr_id in self.attr_labels:
                self.attr_labels[attr_id].configure(text=f"{val:.2f}")

        # Tab 3: Inventory / Ender items
        self._refresh_inventory_viewer()

        # Tab 5: World, Cheats & Weather
        gm = w.get_gamemode()
        gm_names = ["Survival", "Creative", "Adventure", "Spectator"]
        if 0 <= gm < len(gm_names):
            self.gamemode_combo.set(gm_names[gm])

        self.diff_combo.set(w.get_difficulty())

        if w.get_cheats_enabled():
            self.switch_cheats.select()
        else:
            self.switch_cheats.deselect()

        if w.get_hardcore():
            self.switch_hardcore.select()
        else:
            self.switch_hardcore.deselect()

        # Weather label
        cw = w.get_weather()
        self.weather_status_lbl.configure(text=f"Current: {cw.capitalize()}")

        # Rules
        for rk, sw in self.gamerule_switches.items():
            rule_val = w.get_game_rule(rk)
            if rule_val is True:
                sw.select()
            else:
                sw.deselect()

    def _refresh_inventory_viewer(self):
        for widget in self.inv_list_scroll.winfo_children():
            widget.destroy()

        if not self.active_world:
            return

        is_ender = (self.current_container == "ender")
        items = self.active_world.get_items(is_ender=is_ender)
        cont_name = "Ender Chest" if is_ender else "Inventory"

        if not items:
            ctk.CTkLabel(self.inv_list_scroll, text=f"{cont_name} is empty", text_color=ui_theme.TEXT_MUTED).pack(pady=10)
            return

        for it in items:
            row = ctk.CTkFrame(self.inv_list_scroll, fg_color=ui_theme.INPUT_BG, corner_radius=6)
            row.pack(fill="x", pady=2, padx=2)

            slot_str = f"Slot {it['slot']}:"
            ctk.CTkLabel(row, text=slot_str, width=60, font=ctk.CTkFont(weight="bold"), text_color=ui_theme.ACCENT_EMERALD).pack(side="left", padx=4)

            name = it["id"].replace("minecraft:", "").replace("_", " ").title()
            if it["custom_name"]:
                name = f"{name} ({it['custom_name']})"
            ctk.CTkLabel(row, text=name, font=ctk.CTkFont(weight="bold")).pack(side="left", padx=4)

            ctk.CTkLabel(row, text=f"x{it['count']}", text_color=ui_theme.TEXT_SECONDARY).pack(side="left", padx=4)

            if it["unbreakable"]:
                ctk.CTkLabel(row, text="[Unbreakable]", font=ctk.CTkFont(size=10), text_color=ui_theme.ACCENT_CYAN).pack(side="left", padx=2)

            if it["enchantments"]:
                ench_count = len(it["enchantments"])
                ctk.CTkLabel(row, text=f"[{ench_count} Enchants]", font=ctk.CTkFont(size=10), text_color=ui_theme.ACCENT_AMETHYST).pack(side="left", padx=2)

            if it["lore"]:
                ctk.CTkLabel(row, text=f"[Lore: {len(it['lore'])}L]", font=ctk.CTkFont(size=10), text_color=ui_theme.ACCENT_GOLD).pack(side="left", padx=2)

            ctk.CTkButton(
                row,
                text="Del",
                width=36,
                height=22,
                fg_color=ui_theme.ACCENT_RED,
                hover_color=ui_theme.ACCENT_RED_HOVER,
                command=lambda s=it["slot"]: self._action_delete_slot(s)
            ).pack(side="right", padx=4, pady=2)

    def _sync_ui_to_world(self):
        """Read UI elements and apply values into active WorldSave instance."""
        if not self.active_world:
            return
        w = self.active_world

        # Tab 1: Hacks
        w.set_god_mode(bool(self.switch_god.get()))
        w.set_mayfly(bool(self.switch_flight.get()))
        w.set_flying(bool(self.switch_flying.get()))
        w.set_instabuild(bool(self.switch_instabuild.get()))

        # Tab 5: Gamemode, Difficulty, Cheats & Hardcore
        gm_map = {"Survival": 0, "Creative": 1, "Adventure": 2, "Spectator": 3}
        gm_val = gm_map.get(self.gamemode_combo.get(), 0)
        w.set_gamemode(gm_val)
        w.set_difficulty(self.diff_combo.get())
        w.set_cheats_enabled(bool(self.switch_cheats.get()))
        w.set_hardcore(bool(self.switch_hardcore.get()))

        # Game Rules
        for rk, sw in self.gamerule_switches.items():
            w.set_game_rule(rk, bool(sw.get()))

    def save_active_world(self):
        if not self.active_world:
            messagebox.showwarning("No World", "Please select a world save first.")
            return

        self._sync_ui_to_world()
        self.save_btn.configure(state="disabled")
        self.set_status(f"Saving world '{self.active_world.world_name}' (creating safety backup)...")
        threading.Thread(target=self._worker_save_world, daemon=True).start()

    def _worker_save_world(self):
        try:
            if self.active_world:
                self.active_world.save_all()
                self.msg_queue.put(("save_done", self.active_world.world_name))
        except Exception as e:
            self.msg_queue.put(("error", f"Save failed: {str(e)}"))

    def _on_save_completed(self, world_name: str):
        self.save_btn.configure(state="normal")
        self.set_status(f"World '{world_name}' saved successfully. Safety backup archived.")
        messagebox.showinfo("Saved", f"Changes successfully written to '{world_name}'.\nAn automatic safety backup was archived in .mc_mod_backups.")

    # ==========================================
    # ACTION HANDLERS
    # ==========================================

    def _action_max_vitals(self):
        if not self.active_world:
            return
        max_h = max(20.0, self.active_world.get_attribute("minecraft:max_health"))
        self.active_world.refill_vitals(health=max_h, food=20, saturation=20.0, absorption=0.0)
        self.set_status(f"Refilled health to {max_h:.1f} and hunger to maximum.")
        messagebox.showinfo("Vitals Restored", f"Health restored to {max_h:.1f} and Food to maximum.")

    def _action_golden_hearts(self):
        if not self.active_world:
            return
        curr_h = max(20.0, self.active_world.get_vitals()["health"])
        self.active_world.refill_vitals(health=curr_h, food=20, saturation=20.0, absorption=40.0)
        self.set_status("Added +40 Absorption Golden Hearts.")

    def _action_revive_player(self):
        if not self.active_world:
            return
        max_h = max(20.0, self.active_world.get_attribute("minecraft:max_health"))
        self.active_world.refill_vitals(health=max_h, food=20, saturation=20.0, absorption=0.0)
        self.switch_god.select()
        self.active_world.set_god_mode(True)
        self.set_status("Revived player with full health, reset death timers, and enabled God Mode.")
        messagebox.showinfo("Player Revived", "Player revived from death with full health and god protection.")

    def _action_set_xp(self, level: int):
        if not self.active_world:
            return
        self.active_world.set_xp_level(level)
        self.set_status(f"Player XP level set to {level:,}.")

    def _action_set_custom_xp(self):
        val = self.custom_xp_entry.get().strip()
        try:
            lvl = int(val)
            self._action_set_xp(lvl)
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid integer for XP level.")

    def _action_tp_death(self):
        if not self.active_world:
            return
        if self.active_world.teleport_to_last_death():
            ldl = self.active_world.get_last_death_location()
            self.set_status(f"Player coordinates updated to last death: {ldl['x']}, {ldl['y']}, {ldl['z']}")
            messagebox.showinfo("Teleported", f"Teleported player to Last Death Location:\nX: {ldl['x']}, Y: {ldl['y'] + 1}, Z: {ldl['z']}\nClick 'Save to World' to commit changes.")
        else:
            messagebox.showwarning("No Death Record", "No LastDeathLocation found on this player.")

    def _action_tp_spawn(self):
        if not self.active_world:
            return
        self.active_world.teleport_to_spawn()
        sx, sy, sz, dim = self.active_world.get_world_spawn()
        self.set_status(f"Teleported player to world spawn: {sx:.1f}, {sy + 2:.1f}, {sz:.1f}")
        messagebox.showinfo("Teleported", f"Teleported player to World Spawn:\nX: {sx:.1f}, Y: {sy + 2:.1f}, Z: {sz:.1f}\nClick 'Save to World' to commit.")

    def _action_custom_tp(self):
        if not self.active_world:
            return
        try:
            x = float(self.tp_x_entry.get().strip())
            y = float(self.tp_y_entry.get().strip())
            z = float(self.tp_z_entry.get().strip())
            dim = self.tp_dim_combo.get().strip()
            self.active_world.teleport_player(x, y, z, dim)
            self.set_status(f"Teleported to ({x}, {y}, {z}) in {dim}.")
            messagebox.showinfo("Teleported", f"Coordinates set to ({x}, {y}, {z}).\nClick 'Save to World' to commit.")
        except ValueError:
            messagebox.showerror("Invalid Coords", "Please enter valid numeric coordinates for X, Y, and Z.")

    def _apply_attr_preset(self, preset_name: str):
        if not self.active_world:
            return
        if preset_name == "super_soldier":
            self._set_attr_single("minecraft:max_health", 200.0)
            self._set_attr_single("minecraft:movement_speed", 0.35)
            self._set_attr_single("minecraft:attack_damage", 500.0)
            self._set_attr_single("minecraft:attack_speed", 40.0)
            self._set_attr_single("minecraft:block_interaction_range", 16.0)
            self._set_attr_single("minecraft:entity_interaction_range", 12.0)
            self._set_attr_single("minecraft:block_break_speed", 25.0)
            self._set_attr_single("minecraft:safe_fall_distance", 1000.0)
            self._set_attr_single("minecraft:step_height", 1.5)
            self._set_attr_single("minecraft:scale", 1.0)
            self.set_status("Applied Super Soldier attribute matrix (Speed, Reach, One-Punch).")
        elif preset_name == "giant":
            self._set_attr_single("minecraft:scale", 3.5)
            self._set_attr_single("minecraft:max_health", 150.0)
            self._set_attr_single("minecraft:step_height", 3.0)
            self._set_attr_single("minecraft:block_interaction_range", 20.0)
            self._set_attr_single("minecraft:entity_interaction_range", 18.0)
            self._set_attr_single("minecraft:attack_damage", 150.0)
            self.set_status("Applied Giant Morph preset (Scale 3.5x).")
        elif preset_name == "ant":
            self._set_attr_single("minecraft:scale", 0.20)
            self._set_attr_single("minecraft:movement_speed", 0.45)
            self._set_attr_single("minecraft:step_height", 1.0)
            self.set_status("Applied Ant Morph preset (Scale 0.2x).")

    def _reset_all_attrs(self):
        if not self.active_world:
            return
        self.active_world.reset_attributes()
        for aid, meta in ATTRIBUTES.items():
            self._set_attr_single(aid, meta["default"])
        self.set_status("Reset all player attributes to vanilla default values.")

    def _action_kit_netherite(self):
        if not self.active_world:
            return
        self.active_world.inject_kit("god_netherite")
        self._refresh_inventory_viewer()
        self.set_status("Injected Full God Netherite Kit (Level 255 Enchants).")
        messagebox.showinfo("Kit Injected", "Full God Netherite Kit with Level 255 enchantments injected into inventory.")

    def _action_kit_builder(self):
        if not self.active_world:
            return
        self.active_world.inject_kit("builder")
        self._refresh_inventory_viewer()
        self.set_status("Injected Builder Megakit into inventory.")

    def _action_repair_items(self):
        if not self.active_world:
            return
        count = self.active_world.repair_all_items()
        self._refresh_inventory_viewer()
        self.set_status(f"Repaired {count} damaged items across inventory and ender chest.")
        messagebox.showinfo("Repaired", f"Repaired {count} items to full durability.")

    def _action_clear_items(self):
        if not self.active_world:
            return
        is_ender = (self.current_container == "ender")
        cont_name = "Ender Chest" if is_ender else "Inventory"
        if messagebox.askyesno(f"Clear {cont_name}", f"Are you sure you want to clear all items from {cont_name}?"):
            self.active_world.clear_inventory(is_ender=is_ender)
            self._refresh_inventory_viewer()
            self.set_status(f"Cleared all items from {cont_name}.")

    def _action_delete_slot(self, slot: int):
        if not self.active_world:
            return
        is_ender = (self.current_container == "ender")
        self.active_world.remove_item(slot, is_ender=is_ender)
        self._refresh_inventory_viewer()
        self.set_status(f"Removed item from Slot {slot}.")

    def _action_forge_item(self):
        if not self.active_world:
            return
        try:
            slot = int(self.slot_entry.get().strip())
            count = int(self.count_entry.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Input", "Slot and Count must be valid integers.")
            return

        choice = self.item_select_combo.get()
        item_id = "minecraft:netherite_sword"
        if "(" in choice and ")" in choice:
            item_id = choice.split("(")[-1].replace(")", "").strip()

        unbreakable = bool(self.unbreakable_chk.get())
        cname = self.custom_name_entry.get().strip()
        clore_raw = self.custom_lore_entry.get().strip()
        clore = clore_raw.replace("|", "\n")

        enchants: Dict[str, int] = {}
        for eid, cb in self.ench_vars.items():
            if cb.get():
                enchants[eid] = 255

        is_ender = (self.current_container == "ender")

        self.active_world.set_item(
            slot=slot,
            item_id=item_id,
            count=count,
            enchantments=enchants if enchants else None,
            unbreakable=unbreakable,
            custom_name=cname,
            custom_lore=clore,
            is_ender=is_ender
        )
        self._refresh_inventory_viewer()
        target_dest = "Ender Chest" if is_ender else "Inventory"
        self.set_status(f"Forged {item_id} into {target_dest} Slot {slot}.")
        messagebox.showinfo("Item Forged", f"Item successfully placed into {target_dest} Slot {slot}.\nClick 'Save to World' to commit changes.")

    def _action_god_buffs(self):
        if not self.active_world:
            return
        self.active_world.inject_god_buffs()
        self.set_status("Injected 12 permanent god status buffs (clean screen, zero particles).")
        messagebox.showinfo("God Buffs Injected", "12 Permanent Potion Buffs applied with zero particles.")

    def _action_apply_single_potion(self, pid: str, amp: int):
        if not self.active_world:
            return
        self.active_world.add_effect(pid, amplifier=amp, duration=-1, ambient=False, show_particles=False)
        self.set_status(f"Applied infinite buff {pid} (Lvl {amp + 1}).")

    def _action_remove_single_potion(self, pid: str):
        if not self.active_world:
            return
        self.active_world.remove_effect(pid)
        self.set_status(f"Removed buff {pid}.")

    def _action_clear_potions(self):
        if not self.active_world:
            return
        self.active_world.clear_effects()
        self.set_status("Cleared all active potion effects.")

    def _on_gamemode_changed(self, choice: str):
        if not self.active_world:
            return
        mapping = {"Survival": 0, "Creative": 1, "Adventure": 2, "Spectator": 3}
        if choice in mapping:
            self.active_world.set_gamemode(mapping[choice])
            self.set_status(f"World mode changed to {choice}.")

    def _on_diff_changed(self, choice: str):
        if not self.active_world:
            return
        self.active_world.set_difficulty(choice)
        self.set_status(f"World difficulty set to {choice}.")

    def _on_cheats_toggled(self):
        if not self.active_world:
            return
        val = bool(self.switch_cheats.get())
        self.active_world.set_cheats_enabled(val)
        self.set_status(f"Allow Commands (Cheats) set to {val}.")

    def _on_hardcore_toggled(self):
        if not self.active_world:
            return
        val = bool(self.switch_hardcore.get())
        self.active_world.set_hardcore(val)
        self.set_status(f"Hardcore mode set to {val}.")

    def _action_hardcore_revive(self):
        if not self.active_world:
            return
        success = self.active_world.hardcore_revive(restore_survival=True, remove_hardcore=False)
        if success:
            self.gamemode_combo.set("Survival")
            self.switch_god.select()
            self.switch_flight.select()
            self.switch_cheats.select()
            self.set_status("Hardcore world revived! Player restored to Survival mode with full health & god protection.")
            messagebox.showinfo("Hardcore Revive", "Hardcore player revived successfully!\nGamemode set to Survival with full health and god protection.\nClick 'Save to World' to commit changes.")
        else:
            messagebox.showerror("Error", "Failed to revive hardcore world.")

    def _action_unlock_cheats(self):
        if not self.active_world:
            return
        self.active_world.set_cheats_enabled(True)
        self.switch_cheats.select()
        self.set_status("Cheats & commands unlocked (allowCommands: 1b).")
        messagebox.showinfo("Cheats Unlocked", "In-game commands & cheats unlocked.\nClick 'Save to World' to commit.")

    def _set_weather(self, w_type: str):
        if not self.active_world:
            return
        self.active_world.set_weather(w_type)
        self.weather_status_lbl.configure(text=f"Current: {w_type.capitalize()}")
        self.set_status(f"Weather set to {w_type.capitalize()}.")

    def _on_gamerule_toggled(self, rule_key: str):
        if not self.active_world or rule_key not in self.gamerule_switches:
            return
        val = bool(self.gamerule_switches[rule_key].get())
        self.active_world.set_game_rule(rule_key, val)
        self.set_status(f"Game rule '{rule_key}' set to {val}.")

    def _action_safe_rules_preset(self):
        if not self.active_world:
            return
        safe_rules = {
            "keep_inventory": True,
            "mob_griefing": False,
            "fall_damage": False,
            "fire_damage": False,
            "drowning_damage": False,
            "freeze_damage": False,
            "do_insomnia": False,
            "immediate_respawn": True,
            "natural_regeneration": True,
        }
        for rk, val in safe_rules.items():
            self.active_world.set_game_rule(rk, val)
            if rk in self.gamerule_switches:
                if val:
                    self.gamerule_switches[rk].select()
                else:
                    self.gamerule_switches[rk].deselect()
        self.set_status("Applied Safe Exploration game rules preset.")

    def _show_backups_modal(self):
        if not self.active_world:
            messagebox.showwarning("No World", "Please select a world first.")
            return

        backups = self.active_world.list_backups()
        if not backups:
            messagebox.showinfo("No Backups", f"No backups created yet for '{self.active_world.world_name}'.\nBackups are automatically archived before every save.")
            return

        modal = ctk.CTkToplevel(self)
        modal.title(f"Archived Backups: {self.active_world.world_name}")
        modal.geometry("620x420")
        modal.configure(fg_color=ui_theme.BG_MAIN)
        modal.transient(self)
        modal.grab_set()

        ctk.CTkLabel(modal, text=f"Safety Backups for '{self.active_world.world_name}'", font=ctk.CTkFont(size=14, weight="bold")).pack(pady=12)

        scroll = ctk.CTkScrollableFrame(modal, fg_color=ui_theme.BG_CARD)
        scroll.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        for b in backups:
            row = ctk.CTkFrame(scroll, fg_color=ui_theme.INPUT_BG)
            row.pack(fill="x", pady=4, padx=4)

            ctk.CTkLabel(row, text=b["filename"], font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=8, pady=6)
            ctk.CTkLabel(row, text=b["date"], font=ctk.CTkFont(size=11), text_color=ui_theme.TEXT_SECONDARY).pack(side="left", padx=8)

            ctk.CTkButton(
                row,
                text="Restore This Backup",
                height=26,
                fg_color=ui_theme.ACCENT_AMETHYST,
                hover_color=ui_theme.ACCENT_AMETHYST_HOVER,
                command=lambda bp=b["path"], m=modal: self._restore_backup_and_close(bp, m)
            ).pack(side="right", padx=8, pady=4)

    def _restore_backup_and_close(self, backup_path: str, modal: ctk.CTkToplevel):
        if not self.active_world:
            return
        if messagebox.askyesno("Confirm Restore", f"Are you sure you want to restore {os.path.basename(backup_path)}?\nThis will overwrite current save files."):
            success = self.active_world.restore_backup(backup_path)
            if success:
                self._load_world_into_ui(self.active_world)
                modal.destroy()
                messagebox.showinfo("Restored", "Backup restored successfully.")
                self.set_status("Backup restored successfully.")
            else:
                messagebox.showerror("Error", "Failed to restore backup.")


def main():
    app = MinecraftModMenuApp()
    app.mainloop()


if __name__ == "__main__":
    main()
