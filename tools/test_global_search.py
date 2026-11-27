"""Offline Omega/Global Search 9.0.7 contracts; no Kodi or external fixtures.

Run: python3 -m unittest discover -s tools -p 'test_global_search.py' -v
Bounded include substitution checks authored XML, not Kodi rendering/focus.
"""

import copy
from pathlib import Path
import re
import unittest
from urllib.parse import parse_qsl
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DIALOG = "Custom_1141_SearchCategories.xml"
VIDEO = "Window.IsVisible(MyVideoNav.xml)"
MUSIC = "Window.IsVisible(MyMusicNav.xml)"
# Exact upstream defs.py Kodi IDs, except generic Actors (344) deliberately
# replaces upstream's add-on-local Movie actors / TV actors labels (32221/32222).
ROWS = {
    VIDEO: [("342", "movies=true"), ("20343", "tvshows=true"),
            ("20360", "episodes=true"), ("344", "actors=true&tvactors=true"),
            ("20348", "directors=true"), ("20389", "musicvideos=true")],
    MUSIC: [("133", "artists=true"), ("132", "albums=true"), ("134", "songs=true")],
}
ORIGINAL_SEARCH = b'''            <!-- Search -->
            <item>
                <label>$LOCALIZE[137]</label>
                <icon>special://skin/extras/icons/search.png</icon>
                <onclick condition="!System.HasAddon(script.globalsearch)">SendClick(8)</onclick>
                <onclick condition="System.HasAddon(script.globalsearch)">SetFocus(50)</onclick>
                <onclick condition="System.HasAddon(script.globalsearch)">RunScript(script.globalsearch)</onclick>
                <visible>Control.IsEnabled(8)</visible>
            </item>'''


def xml(name):
    return ET.parse(ROOT / "1080i" / name).getroot()


def actions(item):
    return [(node.get("condition"), node.text) for node in item.findall("onclick")]


class GlobalSearchRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = xml("Includes_Items.xml")
        cls.content = cls.items.find("include[@name='Items_View']/content")
        cls.dialog = xml(DIALOG)
        cls.listing = cls.dialog.find(".//control[@id='9000']")
        cls.pattern = cls.items.find("include[@name='SearchCategories_Row']")

    def item(self, label):
        found = [item for item in self.content.findall("item")
                 if item.findtext("label") == "$LOCALIZE[" + label + "]"]
        self.assertEqual(len(found), 1)
        return found[0]

    def calls(self, context=None):
        calls = self.listing.findall("include[@content='SearchCategories_Row']")
        return [call for call in calls if context is None or call.get("condition") == context]

    def row(self, call):
        self.assertIsNone(call.get("file"), "Use the shared definition, not a window file as includes")
        params = {node.get("name"): node.get("value") for node in call.findall("param")}
        self.assertEqual(set(params), {"id", "label", "query"})
        self.assertEqual(len(call.findall("param")), 3)
        row = copy.deepcopy(self.pattern.find("definition/control"))
        # Only expand this small template, never evaluate Kodi conditions/actions.
        for node in row.iter():
            for name, value in params.items():
                if node.text:
                    node.text = node.text.replace("$PARAM[" + name + "]", value)
                for key, attribute in list(node.attrib.items()):
                    node.set(key, attribute.replace("$PARAM[" + name + "]", value))
        self.assertNotIn("$PARAM[", ET.tostring(row, encoding="unicode"))
        return row

    def test_original_search_is_byte_for_byte_unchanged(self):
        raw = (ROOT / "1080i/Includes_Items.xml").read_bytes()
        self.assertEqual(raw.count(ORIGINAL_SEARCH), 1)
        self.assertEqual(actions(self.item("137")), [
            ("!System.HasAddon(script.globalsearch)", "SendClick(8)"),
            ("System.HasAddon(script.globalsearch)", "SetFocus(50)"),
            ("System.HasAddon(script.globalsearch)", "RunScript(script.globalsearch)"),
        ])

    def test_single_category_entry_is_adjacent_to_search_before_filter(self):
        children = list(self.content)
        index = children.index(self.item("137"))
        self.assertIs(children[index + 1], self.item("31933"))
        self.assertIn("SendClick(19)", [text for _, text in actions(children[index + 2])])
        self.assertIsNone(self.items.find("include[@name='Items_ScopedSearch']"))

    def test_launcher_is_limited_to_actual_library_windows_and_enabled_search(self):
        item = self.item("31933")
        self.assertEqual(actions(item), [(None, "SetFocus(300)"), (None, "ActivateWindow(1141)")])
        self.assertEqual([node.text for node in item.findall("visible")], [
            VIDEO + " | " + MUSIC, "Control.IsEnabled(8)",
            "System.AddonIsEnabled(script.globalsearch)",
        ])
        icon = item.findtext("icon")
        self.assertEqual(icon, "special://skin/extras/icons/playlist2.png")
        self.assertNotEqual(icon, self.item("137").findtext("icon"))
        self.assertTrue((ROOT / icon.replace("special://skin/", "")).is_file())

    def test_unused_window_id_and_modal_default_focus(self):
        owners = [path.name for path in (ROOT / "1080i").glob("*.xml")
                  if ET.parse(path).getroot().get("id") == "1141"]
        self.assertEqual(owners, [DIALOG])
        self.assertEqual(self.dialog.get("type"), "dialog")
        self.assertEqual(self.dialog.findtext("defaultcontrol"), "9000")
        self.assertEqual(self.dialog.find("defaultcontrol").get("always"), "true")
        # No unload/onload window jumps, scripts, settings writes or focus races.
        self.assertEqual([node.tag for node in self.dialog],
                         ["defaultcontrol", "controls"])

    def test_shared_row_definition_is_loaded_from_an_includes_root(self):
        self.assertEqual(self.items.tag, "includes")
        self.assertIsNotNone(self.pattern)
        self.assertIsNotNone(xml("Includes.xml").find("include[@file='Includes_Items.xml']"))
        self.assertEqual(self.dialog.findall(".//include[@name]"), [])
        self.assertEqual(self.dialog.findall(".//include[@file]"), [])
        definitions = []
        consumers = []
        for path in (ROOT / "1080i").glob("*.xml"):
            root = ET.parse(path).getroot()
            definitions.extend(path.name for _ in root.findall(".//include[@name='SearchCategories_Row']"))
            consumers.extend(path.name for _ in root.findall(".//include[@content='SearchCategories_Row']"))
        self.assertEqual(definitions, ["Includes_Items.xml"])
        self.assertEqual(consumers, [DIALOG] * 9)

    def test_rows_have_exact_order_labels_and_one_argument_maps(self):
        self.assertEqual(len(self.calls()), 9)
        for context, expected in ROWS.items():
            actual = []
            for call in self.calls(context):
                row = self.row(call)
                invocation = actions(row)[1][1]
                prefix = "RunScript(script.globalsearch,"
                self.assertTrue(invocation.startswith(prefix) and invocation.endswith(")"))
                argument = invocation[len(prefix):-1]
                self.assertNotIn(",", argument, "All flags must be in ONE argument")
                self.assertTrue(all(value == "true" for _, value in parse_qsl(argument)))
                actual.append((row.findtext("label"), argument))
            self.assertEqual(actual, [("$LOCALIZE[" + label + "]", query)
                                      for label, query in expected])

    def test_actor_grouping_is_one_row_two_flags_not_two_launchers(self):
        actors = [self.row(call) for call in self.calls()
                  if "actors=true" in call.find("param[@name='query']").get("value")]
        self.assertEqual(len(actors), 1)
        self.assertEqual(actors[0].findtext("label"), "$LOCALIZE[344]")
        self.assertEqual(actions(actors[0])[-1][1],
                         "RunScript(script.globalsearch,actors=true&tvactors=true)")
        self.assertIn("actors=true&amp;tvactors=true", (ROOT / "1080i" / DIALOG).read_text())

    def test_shared_row_template_closes_before_launch_without_preference_writes(self):
        self.assertEqual({node.get("name") for node in self.pattern.findall("param")},
                         {"id", "label", "query"})
        self.assertEqual([node.tag for node in self.pattern.find("definition")], ["control"])
        for call in self.calls():
            row = self.row(call)
            self.assertEqual(row.get("type"), "button")
            self.assertEqual(row.findtext("include"), "Dialog_Standard_ListButton")
            self.assertEqual([node.tag for node in row],
                             ["width", "label", "include", "onclick", "onclick"])
            self.assertEqual(actions(row)[0], (None, "Dialog.Close(1141,true)"))
            self.assertIsNone(actions(row)[1][0])
        scoped = []
        for path in sorted((ROOT / "1080i").glob("*.xml")):
            for node in ET.parse(path).iter():
                if node.text and "RunScript(script.globalsearch," in node.text:
                    scoped.append((path.name, node.tag, node.text.strip()))
        self.assertEqual(scoped, [("Includes_Items.xml", "onclick", "RunScript(script.globalsearch,$PARAM[query])")])

    def test_picker_uses_standard_aura_styles_and_compact_context_heights(self):
        group = self.dialog.find("controls/control")
        styles = group.findall("include[@content='Dialog_Standard_Group']")
        self.assertEqual([(node.get("condition"), node.find("param[@name='height']").get("value"))
                          for node in styles], [(VIDEO, "556"), (MUSIC, "334")])
        self.assertTrue(all(node.find("param[@name='width']").get("value") == "640"
                            for node in styles))
        header = group.find("control[@type='label']")
        self.assertEqual(header.findtext("label"), "$LOCALIZE[31933]")
        self.assertEqual(header.findtext("include"), "Dialog_Standard_Header")
        shared = xml("Includes_Dialog.xml")
        for name in ("Dialog_Standard_Group", "Dialog_Standard_Header", "Dialog_Standard_ListButton"):
            self.assertIsNotNone(shared.find("include[@name='" + name + "']"))

    def test_picker_uses_normal_grouplist_mouse_remote_keyboard_focus(self):
        self.assertEqual(self.listing.get("type"), "grouplist")
        self.assertEqual(self.listing.findtext("orientation"), "vertical")
        for direction in ("onup", "ondown", "onleft", "onright"):
            self.assertEqual(self.listing.findtext(direction), "9000")
        ids = [self.row(call).get("id") for call in self.calls()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertNotIn("9000", ids)
        # Back is the standard dialog dismissal, not ActivateWindow/PreviousMenu.
        self.assertEqual(self.dialog.findall(".//onback"), [])
        for context, rows in ROWS.items():
            height = 556 if context == VIDEO else 334
            self.assertEqual(len(rows) * 66 + (len(rows) - 1) * 8, height - 100 - 20)

    def test_both_origins_keep_native_search_and_focus_targets(self):
        for name in ("MyVideoNav.xml", "MyMusicNav.xml"):
            window = xml(name)
            self.assertEqual(window.findtext("defaultcontrol"), "50")
            self.assertEqual(window.findtext("menucontrol"), "300")
            native = window.find(".//control[@id='8']")
            self.assertEqual(native.get("type"), "button")
            self.assertEqual(native.findtext("label"), "137")
            self.assertEqual(native.findall("onclick"), [], "Keep Kodi's native search handler")
        views = xml("Includes_View.xml")
        self.assertIn("50", views.findtext("include[@name='View_ViewIDs']/views").split(","))
        self.assertIsNotNone(xml("Includes_View_List.xml").find(
            "include[@name='View_List_Default']/.//control[@id='50']"))

    def test_launcher_keeps_existing_topbar_navigation(self):
        menu = xml("Includes_Topbar.xml")
        listing = menu.find("include[@name='Topbar_Menu']/control[@id='300']")
        self.assertEqual(listing.get("type"), "list")
        self.assertEqual(listing.findtext("include"), "Topbar_Menu_Layout")
        condition = listing.find("include[.='Items_View']").get("condition")
        for context in (VIDEO, MUSIC):
            self.assertIn(context, condition)
        layout = menu.find("include[@name='Topbar_Menu_Layout']/definition")
        self.assertEqual(layout.findtext("orientation"), "horizontal")
        for direction in ("onup", "ondown"):
            self.assertIn("50", [node.text for node in layout.findall(direction)])
        for item in (self.item("137"), self.item("31933")):
            self.assertIsNone(item.get("id"))
            for tag in ("onup", "ondown", "onleft", "onright", "onfocus", "control"):
                self.assertEqual(item.findall(tag), [], "Use existing list hit areas")

    def test_repurposed_localized_title_has_no_unused_movie_label(self):
        english = (ROOT / "language/resource.language.en_gb/strings.po").read_text(encoding="utf-8")
        self.assertEqual(re.findall(r'^msgctxt "#31933"\s+msgid "([^"]*)"', english, re.M),
                         ["Search by category"])
        self.assertNotIn('msgid "Search movies"', english)


if __name__ == "__main__":
    unittest.main()
