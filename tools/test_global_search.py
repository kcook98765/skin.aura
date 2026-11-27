"""Offline Omega skin contracts; no Kodi imports, external fixtures or Git baseline.

Run: python3 -m unittest discover -s tools -p 'test_global_search.py' -v
These inspect authored XML, not Kodi's condition evaluator or rendered focus.
"""

import copy
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


def xml(name):
    return ET.parse(ROOT / "1080i" / name).getroot()


def actions(item):
    return [(node.get("condition"), node.text) for node in item.findall("onclick")]


class GlobalSearchRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.items = xml("Includes_Items.xml")
        cls.content = cls.items.find("include[@name='Items_View']/content")

    def original_search(self):
        found = [item for item in self.content.findall("item")
                 if item.findtext("label") == "$LOCALIZE[137]"]
        self.assertEqual(len(found), 1)
        return found[0]

    def scoped_call(self):
        calls = self.content.findall("include[@content='Items_ScopedSearch']")
        self.assertEqual(len(calls), 1, "Only the movie category is added")
        return calls[0]

    def scoped_item(self, use_icon_default=False):
        call = self.scoped_call()
        pattern = self.items.find("include[@name='Items_ScopedSearch']")
        self.assertIsNotNone(pattern, "Scoped search needs a reusable item include")
        params = {node.get("name"): node.get("value") for node in call.findall("param")}
        self.assertEqual(set(params), {"label", "category", "icon"})
        self.assertEqual({node.get("name") for node in pattern.findall("param")}, set(params))
        self.assertEqual(pattern.find("param[@name='icon']").get("default"),
                         "special://skin/extras/icons/search.png")
        if use_icon_default:
            del params["icon"]
        params = {**{node.get("name"): node.get("default")
                     for node in pattern.findall("param") if node.get("default") is not None},
                  **params}
        definition = pattern.find("definition")
        self.assertIsNotNone(definition)
        self.assertEqual([node.tag for node in definition], ["item"])
        # Bounded substitution for this include only, not a Kodi include engine.
        item = copy.deepcopy(definition.find("item"))
        for node in item.iter():
            if node.text:
                for name, value in params.items():
                    node.text = node.text.replace("$PARAM[" + name + "]", value)
                self.assertNotIn("$PARAM[", node.text)
        return item

    def test_original_search_keeps_no_arguments_fallback_and_focus_order(self):
        item = self.original_search()
        self.assertEqual(actions(item), [
            ("!System.HasAddon(script.globalsearch)", "SendClick(8)"),
            ("System.HasAddon(script.globalsearch)", "SetFocus(50)"),
            ("System.HasAddon(script.globalsearch)", "RunScript(script.globalsearch)"),
        ])
        self.assertEqual([node.text for node in item.findall("visible")], ["Control.IsEnabled(8)"])
        self.assertEqual(item.findtext("icon"), "special://skin/extras/icons/search.png")

    def test_movie_search_is_immediately_after_search_before_filter(self):
        children = list(self.content)
        index = children.index(self.original_search())
        self.assertIs(children[index + 1], self.scoped_call())
        self.assertIn("SendClick(19)", [text for _, text in actions(children[index + 2])])

    def test_scoped_invocation_matches_global_search_907_contract(self):
        item = self.scoped_item()
        # 9.0.7 accepts a category map as ONE script argument; only lower-case
        # 'true' enables a category. No searchstring means its native keyboard.
        self.assertEqual(actions(item), [
            (None, "SetFocus(50)"),
            (None, "RunScript(script.globalsearch,movies=true)"),
        ])
        self.assertEqual(item.findtext("icon"), "special://skin/extras/icons/film.png")
        self.assertNotEqual(item.findtext("icon"), self.original_search().findtext("icon"))
        self.assertEqual(self.scoped_item(use_icon_default=True).findtext("icon"),
                         self.original_search().findtext("icon"))
        self.assertEqual({node.text for node in item.findall("visible")}, {
            "Window.IsVisible(MyVideoNav.xml)", "Control.IsEnabled(8)",
            "System.AddonIsEnabled(script.globalsearch)",
        })
        # The template must parameterize the category, not hard-code movies.
        pattern = self.items.find("include[@name='Items_ScopedSearch']")
        self.assertEqual(pattern.findtext("definition/item/label"), "$PARAM[label]")
        self.assertEqual(pattern.findtext("definition/item/icon"), "$PARAM[icon]")
        self.assertEqual(pattern.findall(".//onclick")[-1].text,
                         "RunScript(script.globalsearch,$PARAM[category]=true)")

    def test_only_new_pattern_adds_scoped_global_search_invocation(self):
        scoped = []
        for path in sorted((ROOT / "1080i").glob("*.xml")):
            for node in ET.parse(path).iter():
                if node.text and "RunScript(script.globalsearch," in node.text:
                    scoped.append((path.name, node.tag, node.text.strip()))
        self.assertEqual(scoped, [("Includes_Items.xml", "onclick",
                                  "RunScript(script.globalsearch,$PARAM[category]=true)")])
        calls = self.items.findall(".//include[@content='Items_ScopedSearch']")
        self.assertEqual(calls, [self.scoped_call()])

    def test_omega_native_search_and_focus_targets_remain_available(self):
        window = xml("MyVideoNav.xml")
        self.assertEqual(window.findtext("defaultcontrol"), "50")
        self.assertEqual(window.findtext("menucontrol"), "300")
        native = window.find(".//control[@id='8']")
        self.assertIsNotNone(native)
        self.assertEqual(native.get("type"), "button")
        self.assertEqual(native.findtext("label"), "137")
        self.assertEqual(native.findall("onclick"), [], "Keep Kodi's native search handler")
        views = xml("Includes_View.xml")
        self.assertIn("50", views.findtext("include[@name='View_ViewIDs']/views").split(","))
        lists = xml("Includes_View_List.xml")
        self.assertEqual(lists.findtext("include[@name='View_List']/definition/include"),
                         "View_List_Default")
        self.assertIsNotNone(lists.find("include[@name='View_List_Default']/.//control[@id='50']"))

    def test_scoped_item_reuses_keyboard_remote_and_mouse_list_navigation(self):
        menu = xml("Includes_Topbar.xml")
        listing = menu.find("include[@name='Topbar_Menu']/control[@id='300']")
        self.assertEqual(listing.get("type"), "list")
        self.assertEqual(listing.findtext("include"), "Topbar_Menu_Layout")
        self.assertIsNotNone(xml("Includes.xml").find("include[@file='Includes_Items.xml']"))
        view_include = listing.find("include[.='Items_View']")
        self.assertIn("Window.IsVisible(MyVideoNav.xml)", view_include.get("condition"))
        layout = menu.find("include[@name='Topbar_Menu_Layout']/definition")
        self.assertEqual(layout.findtext("orientation"), "horizontal")
        for direction in ("onup", "ondown"):
            self.assertIn("50", [node.text for node in layout.findall(direction)])
        self.assertEqual(layout.find("itemlayout").get("width"),
                         layout.find("focusedlayout").get("width"))
        for name in ("itemlayout", "focusedlayout"):
            self.assertTrue(any(node.text == "$INFO[ListItem.Icon]"
                                for node in layout.find(name).iter("texture")))
        self.assertTrue(any(node.text == "$INFO[Container(300).ListItem.Label]"
                            for node in menu.iter("label")))
        for item in (self.original_search(), self.scoped_item()):
            self.assertIsNone(item.get("id"))
            for tag in ("onup", "ondown", "onleft", "onright", "onfocus", "control"):
                self.assertEqual(item.findall(tag), [], "Use existing list focus/hit areas")

    def test_movie_label_is_localized_once(self):
        label = self.scoped_item().findtext("label")
        match = re.fullmatch(r"\$LOCALIZE\[(\d+)\]", label)
        self.assertIsNotNone(match)
        english = (ROOT / "language/resource.language.en_gb/strings.po").read_text(encoding="utf-8")
        entries = re.findall(r'^msgctxt "#' + match[1] + r'"\s+msgid "([^"]*)"', english, re.M)
        self.assertEqual(entries, ["Search movies"])
        self.assertTrue((ROOT / self.scoped_item().findtext("icon").replace("special://skin/", "")).is_file())


if __name__ == "__main__":
    unittest.main()
