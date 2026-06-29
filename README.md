# ⚔️ Minecraft Mod Menu & World Editor

Just a fun little desktop tool I made to mess around with Minecraft Java save files! It gives you a dark-mode mod menu interface where you can forge ridiculous God items (Level 255 Sharpness, Fortune, Density, etc.), fly around in Survival mode, tweak player attributes like size and reach, revive dead Hardcore worlds, and flip world rules on or off without dealing with complex commands or installing in-game mods.

Works seamlessly with both modern **Minecraft 26.x** (multi-file save layout) and **1.20 / 1.21** worlds.

---

## ✨ Cool Features

### 🦸 Player Hacks & God Mode
- **God Mode:** Total invulnerability to mobs, void, lava, and explosions.
- **Survival Creative Flight:** Double-tap Space to fly around smoothly even in pure Survival.
- **Instant Mine & Build:** One-hit break blocks.
- **Vitals & XP Cheats:** Instantly top up health, hunger, +40 Absorption hearts, and give yourself level 1,000 XP.
- **Panic Death Teleporter:** One-click button that teleports you right back to your last death coordinates (and zeroes your fall distance so you land safely).

### 📐 Base Attributes & Morphing
- **Entity Scaling:** Shrink down to an Ant ($0.1\times$) or grow into a Titan ($8.0\times$).
- **Insane Reach:** Break blocks and hit entities from up to 32 blocks away.
- **Super Speed & Attack:** 5x sprint velocity and 500.0 bare-fist strike damage.
- **Step Height:** Walk straight up full blocks without jumping.

### 🔨 God-Item Forge & Ender Chest Editor
- **Container Switch:** Edit your active Player Inventory or your personal Ender Chest.
- **Level 255 Enchantments:** Stack Level 255 Sharpness, Protection, Efficiency, Fortune, Looting, Density, Breach, and Wind Burst onto any item.
- **Custom Lore & Name:** Add custom display names and multi-line colorful lore.
- **1-Click Kits:** Instantly spawn 32k God Netherite gear, Builder Megakits, or 1-click repair all damaged gear to full durability.

### 🧪 Infinite Potion Buffs
- Permanent status effects with zero annoying particle swirl on your screen:
  - Night Vision, Haste V, Strength V, Resistance V, Regeneration V, Speed, Fire Resistance, Water Breathing, and Saturation.

### 🌍 World Controller & Hardcore Revive
- **Hardcore Revive:** If you died in a Hardcore world, this brings you back to life in Survival mode and unfreezes the world without needing external hex editors.
- **Cheats Unlocker:** Enables commands on worlds where cheats were turned off at creation.
- **Instant Weather:** 1-click toggle between Clear Sky, Rain, and Thunderstorms.
- **Gamerule Switchboard:** Toggles for Keep Inventory, Mob Griefing, Fall Damage, Fire Spread, TNT, Phantom spawning, and more.

### 🛡️ Automatic Backups
Before saving any changes, the tool automatically makes a timestamped `.bak` copy inside `.mc_mod_backups/`. If you ever want to revert, just hit the **Backups** button.

---

## 🚀 How to Run It

### Method 1: Desktop App / Shortcut
Double-click **`Minecraft_Mod_Menu.exe`** (or **`Minecraft Mod Menu.lnk`**) right from your desktop.

### Method 2: From Source
```bash
git clone https://github.com/lunizura/minecraft-mod-menu.git
cd minecraft-mod-menu
pip install -r requirements.txt
python app_gui.py
```

### Method 3: Headless CLI (`mc_cli.py`)
If you prefer running quick cheats from terminal:
```bash
# Scan and list all worlds across all launchers
python mc_cli.py scan

# Inspect player coordinates and health
python mc_cli.py inspect "Izu             Lyn"

# Enable god mode and survival flight
python mc_cli.py god "Izu             Lyn"

# Give yourself a full 32k Netherite kit
python mc_cli.py kit "Izu             Lyn" god_netherite

# Revive a dead player or hardcore save
python mc_cli.py revive "Izu             Lyn"
python mc_cli.py hardcore-revive "Izu             Lyn"

# Turn on commands / cheats
python mc_cli.py cheats "Izu             Lyn" on

# Clear the weather
python mc_cli.py weather "Izu             Lyn" clear
```

---

## 🧪 Testing

Ran 17 automated unit tests covering lossless NBT binary round-tripping across all 13 tag types:
```bash
python -m unittest discover tests -v
```

---

## 📜 License

MIT License. Have fun with it!
