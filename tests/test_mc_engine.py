"""
test_mc_engine.py - Comprehensive Unit & Integration Tests for Minecraft Mod Menu Engine
Verifies lossless Big-Endian NBT parsing/serialization across all 13 official tag types,
structural tag equality, Minecraft UUID int[4] decoding, multi-player save resolution,
fall distance hazard mitigation, 26.x and legacy gamerules, item forge with lore,
Ender Chest slots, weather control, and hardcore revival.
"""

import os
import shutil
import struct
import tempfile
import unittest
import uuid

from nbt_core import (
    NBTFile, NBTTag,
    TAG_End, TAG_Byte, TAG_Short, TAG_Int, TAG_Long,
    TAG_Float, TAG_Double, TAG_Byte_Array, TAG_String,
    TAG_List, TAG_Compound, TAG_Int_Array, TAG_Long_Array,
    TAG_COMPOUND, TAG_INT, TAG_STRING
)
from mc_catalog import ATTRIBUTES, ENCHANTMENTS, POTIONS, GAME_RULES, ITEM_PRESETS, search_items
from mc_world import WorldSave, scan_all_worlds, decode_mc_uuid


class TestNBTCore(unittest.TestCase):
    """Test pure-Python NBT parser and serializer across all 13 tag types."""

    def test_all_primitive_tags(self):
        root = TAG_Compound()
        root["byte"] = TAG_Byte(120)
        root["byte_neg"] = TAG_Byte(-15)
        root["short"] = TAG_Short(32000)
        root["int"] = TAG_Int(2000000000)
        root["long"] = TAG_Long(9000000000000000000)
        root["float"] = TAG_Float(3.14159)
        root["double"] = TAG_Double(2.718281828459)
        root["string"] = TAG_String("Antigravity Mod Menu")
        root["byte_array"] = TAG_Byte_Array(b"\x00\x01\x02\x03\xFF")
        root["int_array"] = TAG_Int_Array([10, -20, 30, -40])
        root["long_array"] = TAG_Long_Array([10000000000, -20000000000])

        f = NBTFile(root=root, name="TestRoot", compressed=True)
        raw = f.to_bytes()

        # Reload
        reloaded = NBTFile.load(raw)
        self.assertEqual(reloaded.name, "TestRoot")
        self.assertEqual(reloaded["byte"].to_py(), 120)
        self.assertEqual(reloaded["byte_neg"].to_py(), -15)
        self.assertEqual(reloaded["short"].to_py(), 32000)
        self.assertEqual(reloaded["int"].to_py(), 2000000000)
        self.assertEqual(reloaded["long"].to_py(), 9000000000000000000)
        self.assertAlmostEqual(reloaded["float"].to_py(), 3.14159, places=4)
        self.assertAlmostEqual(reloaded["double"].to_py(), 2.718281828459, places=8)
        self.assertEqual(reloaded["string"].to_py(), "Antigravity Mod Menu")
        self.assertEqual(reloaded["byte_array"].to_py(), bytearray(b"\x00\x01\x02\x03\xFF"))
        self.assertEqual(reloaded["int_array"].to_py(), [10, -20, 30, -40])
        self.assertEqual(reloaded["long_array"].to_py(), [10000000000, -20000000000])

    def test_nested_compounds_and_lists(self):
        root = TAG_Compound()
        sub = TAG_Compound()
        sub["level"] = TAG_Int(255)
        sub["active"] = TAG_Byte(1)
        root["sub_compound"] = sub

        str_list = TAG_List(TAG_String.tag_type, [TAG_String("alpha"), TAG_String("beta")])
        root["strings"] = str_list

        empty_list = TAG_List(TAG_End.tag_type, [])
        root["empty"] = empty_list

        f = NBTFile(root=root, name="", compressed=False)
        raw = f.to_bytes()

        reloaded = NBTFile.load(raw)
        self.assertEqual(reloaded.get_val("sub_compound/level"), 255)
        self.assertEqual(reloaded.get_val("sub_compound/active"), 1)
        self.assertEqual(reloaded["strings"].to_py(), ["alpha", "beta"])
        self.assertEqual(len(reloaded["empty"]), 0)

    def test_nbt_tag_equality(self):
        c1 = TAG_Compound({"x": TAG_Int(10), "y": TAG_String("test")})
        c2 = TAG_Compound({"x": TAG_Int(10), "y": TAG_String("test")})
        c3 = TAG_Compound({"x": TAG_Int(20)})
        self.assertEqual(c1, c2)
        self.assertNotEqual(c1, c3)

        l1 = TAG_List(TAG_Int.tag_type, [TAG_Int(1), TAG_Int(2)])
        l2 = TAG_List(TAG_Int.tag_type, [TAG_Int(1), TAG_Int(2)])
        l3 = TAG_List(TAG_Int.tag_type, [TAG_Int(1), TAG_Int(3)])
        self.assertEqual(l1, l2)
        self.assertNotEqual(l1, l3)

    def test_path_navigation(self):
        root = TAG_Compound()
        root.set_path("Data/Player/abilities/mayfly", TAG_Byte(1))
        self.assertEqual(root.get_val("Data/Player/abilities/mayfly"), 1)
        self.assertIsNone(root.get_val("Data/Player/abilities/nonexistent"))


class TestCatalog(unittest.TestCase):
    """Test catalog search, presets, and definitions."""

    def test_catalog_search(self):
        results = search_items("sword")
        self.assertTrue(any(i["id"] == "minecraft:netherite_sword" for i in results))
        self.assertTrue(any(i["id"] == "minecraft:diamond_sword" for i in results))

        mace_res = search_items("mace")
        self.assertTrue(any(i["id"] == "minecraft:mace" for i in mace_res))

    def test_presets_completeness(self):
        self.assertIn("32k_sword", ITEM_PRESETS)
        self.assertIn("fortune_pickaxe", ITEM_PRESETS)
        self.assertIn("cosmic_mace", ITEM_PRESETS)
        self.assertEqual(ITEM_PRESETS["32k_sword"]["enchantments"]["minecraft:sharpness"], 255)
        self.assertEqual(ITEM_PRESETS["fortune_pickaxe"]["enchantments"]["minecraft:fortune"], 255)

    def test_attributes_and_gamerules_completeness(self):
        self.assertIn("minecraft:movement_speed", ATTRIBUTES)
        self.assertIn("minecraft:attack_damage", ATTRIBUTES)
        self.assertIn("minecraft:scale", ATTRIBUTES)
        self.assertIn("minecraft:gravity", ATTRIBUTES)
        self.assertIn("keep_inventory", GAME_RULES)
        self.assertIn("mob_griefing", GAME_RULES)
        self.assertIn("minecraft:advance_time", GAME_RULES["do_daylight_cycle"]["names"])
        self.assertIn("minecraft:advance_weather", GAME_RULES["do_weather_cycle"]["names"])
        self.assertIn("minecraft:spawn_phantoms", GAME_RULES["do_insomnia"]["names"])


class TestWorldController(unittest.TestCase):
    """Test WorldSave controllers using a synthetic 26.x world structure."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="mc_test_world_")
        # Build 26.x world directory layout
        os.makedirs(os.path.join(self.temp_dir, "players", "data"), exist_ok=True)
        os.makedirs(os.path.join(self.temp_dir, "data", "minecraft"), exist_ok=True)

        # Realistic 128-bit UUID stored as int[4]
        self.target_uuid_str = "11111111-2222-3333-4444-555555555555"
        u_bytes = uuid.UUID(self.target_uuid_str).bytes
        u_ints = list(struct.unpack(">4i", u_bytes))

        # 1. Synthetic level.dat with singleplayer_uuid as TAG_Int_Array
        level_root = TAG_Compound()
        level_data = TAG_Compound()
        level_data["LevelName"] = TAG_String("Test Realm")
        level_data["DataVersion"] = TAG_Int(5023)
        level_data["GameType"] = TAG_Int(0)
        level_data["allowCommands"] = TAG_Byte(0)
        level_data["singleplayer_uuid"] = TAG_Int_Array(u_ints)

        diff_comp = TAG_Compound()
        diff_comp["difficulty"] = TAG_String("hard")
        diff_comp["hardcore"] = TAG_Byte(0)
        diff_comp["locked"] = TAG_Byte(1)
        level_data["difficulty_settings"] = diff_comp

        spawn_comp = TAG_Compound()
        spawn_comp["pos"] = TAG_Int_Array([100, 70, -200])
        spawn_comp["dimension"] = TAG_String("minecraft:overworld")
        level_data["spawn"] = spawn_comp

        level_root["Data"] = level_data
        level_file = NBTFile(level_root, name="", compressed=True)
        level_file.save(os.path.join(self.temp_dir, "level.dat"))

        # 2. Plant a dummy player file that sorts FIRST alphabetically (to ensure UUID matching works)
        dummy_player = TAG_Compound({"Health": TAG_Float(1.0)})
        NBTFile(dummy_player, name="", compressed=True).save(
            os.path.join(self.temp_dir, "players", "data", "00000000-0000-0000-0000-000000000000.dat")
        )

        # 3. Target singleplayer player .dat
        player_root = TAG_Compound()
        player_root["Health"] = TAG_Float(10.0)
        player_root["foodLevel"] = TAG_Int(14)
        player_root["foodSaturationLevel"] = TAG_Float(5.0)
        player_root["AbsorptionAmount"] = TAG_Float(0.0)
        player_root["XpLevel"] = TAG_Int(5)
        player_root["Invulnerable"] = TAG_Byte(0)
        player_root["Pos"] = TAG_List(TAG_Double.tag_type, [TAG_Double(105.5), TAG_Double(71.0), TAG_Double(-195.5)])
        # Modern 26.x fall distance
        player_root["fall_distance"] = TAG_Double(45.5)

        abilities = TAG_Compound()
        abilities["invulnerable"] = TAG_Byte(0)
        abilities["mayfly"] = TAG_Byte(0)
        abilities["flying"] = TAG_Byte(0)
        abilities["instabuild"] = TAG_Byte(0)
        player_root["abilities"] = abilities

        ldl = TAG_Compound()
        ldl["pos"] = TAG_Int_Array([50, 64, 1800])
        ldl["dimension"] = TAG_String("minecraft:overworld")
        player_root["LastDeathLocation"] = ldl

        player_root["attributes"] = TAG_List(TAG_COMPOUND, [])
        player_root["Inventory"] = TAG_List(TAG_COMPOUND, [])
        player_root["EnderItems"] = TAG_List(TAG_COMPOUND, [])
        player_root["active_effects"] = TAG_List(TAG_COMPOUND, [])

        player_file = NBTFile(player_root, name="", compressed=True)
        player_file.save(os.path.join(self.temp_dir, "players", "data", f"{self.target_uuid_str}.dat"))

        # 4. Synthetic game_rules.dat with 26.x namespaced rules
        rules_root = TAG_Compound()
        rules_data = TAG_Compound()
        rules_data["minecraft:keep_inventory"] = TAG_Byte(0)
        rules_data["minecraft:mob_griefing"] = TAG_Byte(1)
        rules_data["minecraft:advance_time"] = TAG_Byte(1)
        rules_data["minecraft:advance_weather"] = TAG_Byte(1)
        rules_data["minecraft:spawn_phantoms"] = TAG_Byte(1)
        rules_root["data"] = rules_data
        rules_file = NBTFile(rules_root, name="", compressed=True)
        rules_file.save(os.path.join(self.temp_dir, "data", "minecraft", "game_rules.dat"))

        # 5. Synthetic weather.dat
        weather_root = TAG_Compound()
        weather_data = TAG_Compound()
        weather_data["raining"] = TAG_Byte(0)
        weather_data["thundering"] = TAG_Byte(0)
        weather_data["rain_time"] = TAG_Int(0)
        weather_root["data"] = weather_data
        weather_file = NBTFile(weather_root, name="", compressed=True)
        weather_file.save(os.path.join(self.temp_dir, "data", "minecraft", "weather.dat"))

        self.world = WorldSave(self.temp_dir, profile_name="Vanilla")
        loaded = self.world.load()
        self.assertTrue(loaded, "Failed to load synthetic test world")

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_multi_player_uuid_resolution(self):
        # Must resolve to target_uuid_str rather than 00000000-... which sorted first alphabetically!
        expected_path = os.path.join(self.temp_dir, "players", "data", f"{self.target_uuid_str}.dat")
        self.assertEqual(os.path.abspath(self.world.player_path), os.path.abspath(expected_path))

    def test_player_hacks_and_vitals(self):
        w = self.world
        # God Mode
        self.assertFalse(w.get_god_mode())
        w.set_god_mode(True)
        self.assertTrue(w.get_god_mode())

        # Flight
        self.assertFalse(w.get_mayfly())
        w.set_mayfly(True)
        self.assertTrue(w.get_mayfly())

        # Vitals refill & fall distance fix
        w.refill_vitals(health=200.0, food=20, saturation=20.0, absorption=40.0)
        vitals = w.get_vitals()
        self.assertEqual(vitals["health"], 200.0)
        self.assertEqual(vitals["food"], 20)
        self.assertEqual(vitals["absorption"], 40.0)
        # Ensure 26.x fall distance was reset to zero!
        self.assertEqual(float(w.player_data["fall_distance"].to_py()), 0.0)

        # XP
        w.set_xp_level(100)
        self.assertEqual(w.get_vitals()["xp_level"], 100)

        # Teleport to last death
        success = w.teleport_to_last_death()
        self.assertTrue(success)
        pos = w.get_player_pos()
        self.assertEqual(pos[0], 50.5)
        self.assertEqual(pos[1], 65.0)
        self.assertEqual(pos[2], 1800.5)
        self.assertEqual(float(w.player_data["fall_distance"].to_py()), 0.0)

    def test_attribute_matrix(self):
        w = self.world
        w.set_attribute("minecraft:movement_speed", 0.35)
        self.assertAlmostEqual(w.get_attribute("minecraft:movement_speed"), 0.35)

        w.set_attribute("minecraft:attack_damage", 500.0)
        self.assertEqual(w.get_attribute("minecraft:attack_damage"), 500.0)

        w.set_attribute("minecraft:scale", 2.5)
        self.assertEqual(w.get_attribute("minecraft:scale"), 2.5)

        w.set_attribute("minecraft:gravity", 0.02)
        self.assertAlmostEqual(w.get_attribute("minecraft:gravity"), 0.02)

        attrs = w.get_all_attributes()
        self.assertEqual(attrs["minecraft:attack_damage"], 500.0)

    def test_item_forge_lore_and_ender_chest(self):
        w = self.world
        # Inject kit into inventory
        w.inject_kit("god_netherite")
        items = w.get_items(is_ender=False)
        self.assertGreater(len(items), 5)

        # Check Netherite Sword at slot 0
        sword = next(i for i in items if i["slot"] == 0)
        self.assertEqual(sword["id"], "minecraft:netherite_sword")
        self.assertTrue(sword["unbreakable"])
        self.assertEqual(sword["enchantments"].get("minecraft:sharpness"), 255)
        self.assertEqual(sword["custom_name"], '{"text":"Void Cleaver"}')
        self.assertGreater(len(sword["lore"]), 0)

        # Test Ender Chest Forge & Retrieval
        w.set_item(
            slot=0,
            item_id="minecraft:elytra",
            count=1,
            enchantments={"minecraft:unbreaking": 255, "minecraft:mending": 1},
            unbreakable=True,
            custom_name="Skywalker",
            custom_lore="Wings of the Void\nFlies forever",
            is_ender=True
        )
        ender_items = w.get_items(is_ender=True)
        self.assertEqual(len(ender_items), 1)
        ender_elytra = ender_items[0]
        self.assertEqual(ender_elytra["slot"], 0)
        self.assertEqual(ender_elytra["id"], "minecraft:elytra")
        self.assertTrue(ender_elytra["unbreakable"])
        self.assertEqual(len(ender_elytra["lore"]), 2)

        # Test repair
        w.set_item(slot=5, item_id="minecraft:diamond_pickaxe", count=1, damage=150)
        repaired = w.repair_all_items()
        self.assertGreaterEqual(repaired, 1)

    def test_potion_effects(self):
        w = self.world
        w.inject_god_buffs()
        effects = w.get_effects()
        self.assertGreaterEqual(len(effects), 10)
        haste = next((e for e in effects if e["id"] == "minecraft:haste"), None)
        self.assertIsNotNone(haste)
        self.assertEqual(haste["amplifier"], 4)
        self.assertEqual(haste["duration"], -1)
        self.assertFalse(haste["show_particles"])

    def test_weather_controller(self):
        w = self.world
        self.assertEqual(w.get_weather(), "clear")

        w.set_weather("rain")
        self.assertEqual(w.get_weather(), "rain")

        w.set_weather("thunder")
        self.assertEqual(w.get_weather(), "thunder")

        w.set_weather("clear")
        self.assertEqual(w.get_weather(), "clear")

    def test_26x_gamerules_and_cheats(self):
        w = self.world
        # Cheats unlocker
        self.assertFalse(w.get_cheats_enabled())
        w.set_cheats_enabled(True)
        self.assertTrue(w.get_cheats_enabled())

        # Daylight cycle in 26.x updates advance_time without writing ghost keys
        self.assertEqual(w.get_game_rule("do_daylight_cycle"), True)
        w.set_game_rule("do_daylight_cycle", False)
        self.assertEqual(w.get_game_rule("do_daylight_cycle"), False)
        self.assertEqual(w.game_rules_data["minecraft:advance_time"].to_py(), 0)

        # Weather cycle
        w.set_game_rule("do_weather_cycle", False)
        self.assertEqual(w.game_rules_data["minecraft:advance_weather"].to_py(), 0)

        # Phantom insomnia
        w.set_game_rule("do_insomnia", False)
        self.assertEqual(w.game_rules_data["minecraft:spawn_phantoms"].to_py(), 0)

        # Save and verify reload
        w.save_all()
        w2 = WorldSave(self.temp_dir)
        w2.load()
        self.assertEqual(w2.get_game_rule("do_daylight_cycle"), False)
        self.assertEqual(w2.get_game_rule("do_weather_cycle"), False)
        self.assertEqual(w2.get_game_rule("do_insomnia"), False)

    def test_hardcore_revive(self):
        w = self.world
        # Simulate dead hardcore player
        w.set_hardcore(True)
        w.set_gamemode(3)  # Spectator
        w.player_data["Health"] = TAG_Float(0.0)
        w.player_data["playerGameType"] = TAG_Int(3)

        revived = w.hardcore_revive(restore_survival=True, remove_hardcore=True)
        self.assertTrue(revived)
        self.assertEqual(w.get_gamemode(), 0)  # Survival
        self.assertGreaterEqual(w.get_vitals()["health"], 20.0)
        self.assertTrue(w.get_god_mode())
        self.assertFalse(w.get_hardcore())


class TestLegacySupport(unittest.TestCase):
    """Test compatibility with pre-1.20.5 legacy saves using tag compounds."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="mc_legacy_test_")
        os.makedirs(os.path.join(self.temp_dir, "playerdata"), exist_ok=True)

        level_root = TAG_Compound()
        level_data = TAG_Compound()
        level_data["LevelName"] = TAG_String("Legacy 1.20")
        level_data["DataVersion"] = TAG_Int(3460)  # 1.20.2
        level_data["GameType"] = TAG_Int(0)
        level_data["SpawnX"] = TAG_Int(10)
        level_data["SpawnY"] = TAG_Int(64)
        level_data["SpawnZ"] = TAG_Int(20)

        gr = TAG_Compound()
        gr["keepInventory"] = TAG_String("false")
        level_data["GameRules"] = gr

        level_root["Data"] = level_data
        NBTFile(level_root, name="", compressed=True).save(os.path.join(self.temp_dir, "level.dat"))

        player_root = TAG_Compound()
        player_root["Health"] = TAG_Float(20.0)
        player_root["FallDistance"] = TAG_Float(10.0)
        player_root["Inventory"] = TAG_List(TAG_COMPOUND, [])
        player_root["ActiveEffects"] = TAG_List(TAG_COMPOUND, [])
        NBTFile(player_root, name="", compressed=True).save(
            os.path.join(self.temp_dir, "playerdata", "99999999-8888-7777-6666-555555555555.dat")
        )

        self.world = WorldSave(self.temp_dir)
        self.world.load()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_legacy_item_and_rule_format(self):
        w = self.world
        self.assertFalse(w.is_26x)

        # In legacy, set_item writes Count (byte) and tag (compound)
        w.set_item(
            slot=0,
            item_id="minecraft:diamond_sword",
            count=1,
            enchantments={"sharpness": 5},
            unbreakable=True,
            custom_name="Excalibur"
        )

        items = w.get_items()
        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it["id"], "minecraft:diamond_sword")
        self.assertTrue(it["unbreakable"])
        self.assertIn("minecraft:sharpness", it["enchantments"])

        raw = it["raw_tag"]
        self.assertIn("Count", raw)
        self.assertIn("tag", raw)

        # Legacy game rule
        self.assertFalse(w.get_game_rule("keep_inventory"))
        w.set_game_rule("keep_inventory", True)
        self.assertTrue(w.get_game_rule("keep_inventory"))


class TestRealSaves(unittest.TestCase):
    """Test reading and editing actual real user saves in an isolated sandbox copy."""

    def test_real_izu_lyn_copy(self):
        real_src = r"C:\Users\asus\AppData\Roaming\.minecraft\saves\Izu             Lyn"
        if not os.path.isdir(real_src):
            self.skipTest("Real Izu Lyn save not present on disk")

        temp_dir = tempfile.mkdtemp(prefix="mc_real_test_")
        try:
            shutil.copy2(os.path.join(real_src, "level.dat"), os.path.join(temp_dir, "level.dat"))
            if os.path.isdir(os.path.join(real_src, "players")):
                shutil.copytree(os.path.join(real_src, "players"), os.path.join(temp_dir, "players"))
            if os.path.isdir(os.path.join(real_src, "data")):
                shutil.copytree(os.path.join(real_src, "data"), os.path.join(temp_dir, "data"))

            w = WorldSave(temp_dir, profile_name="Vanilla")
            loaded = w.load()
            self.assertTrue(loaded, f"Failed to load real save copy: {w.load_error}")
            self.assertEqual(w.world_name, "Izu             Lyn")
            self.assertEqual(w.data_version, 5023)
            self.assertTrue(w.is_26x)

            # Test death location extraction
            ldl = w.get_last_death_location()
            self.assertIsNotNone(ldl)
            self.assertEqual(ldl["dimension"], "minecraft:overworld")

            # Player was dead (Health: 0.0)
            v_before = w.get_vitals()
            self.assertEqual(v_before["health"], 0.0)

            # Revive & apply god powers
            w.refill_vitals(health=20.0, food=20, saturation=20.0, absorption=20.0)
            w.set_god_mode(True)
            w.set_mayfly(True)
            w.set_xp_level(100)
            w.inject_kit("god_netherite")
            w.inject_god_buffs()
            w.set_game_rule("keep_inventory", True)
            w.set_game_rule("do_daylight_cycle", True)
            w.set_cheats_enabled(True)
            w.set_weather("clear")

            w.save_all()

            # Reload to verify persistence
            w_reloaded = WorldSave(temp_dir)
            w_reloaded.load()
            self.assertEqual(w_reloaded.get_vitals()["health"], 20.0)
            self.assertEqual(w_reloaded.get_vitals()["xp_level"], 100)
            self.assertTrue(w_reloaded.get_god_mode())
            self.assertTrue(w_reloaded.get_mayfly())
            self.assertTrue(w_reloaded.get_cheats_enabled())
            self.assertEqual(w_reloaded.get_game_rule("keep_inventory"), True)
            self.assertEqual(w_reloaded.get_game_rule("do_daylight_cycle"), True)
            self.assertEqual(w_reloaded.get_weather(), "clear")
            self.assertGreaterEqual(len(w_reloaded.get_items()), 10)
            self.assertGreaterEqual(len(w_reloaded.get_effects()), 10)

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
