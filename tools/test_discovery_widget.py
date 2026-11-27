"""Focused Omega 21.3 source contracts; does not execute Kodi or providers."""
from pathlib import Path
import unittest
from urllib.parse import parse_qsl, urlsplit
import xml.etree.ElementTree as ET

from check_omega import po_messages

ROOT = Path(__file__).resolve().parents[1]
URL = ("plugin://plugin.video.themoviedb.helper/?info=trending_week&tmdb_type=movie"
       "&widget=true&limit=12&nextpage=false&cacheonly=true&fanarttv=false"
       "&plugin_category=Aura%20Online%20Discovery&reload=0")
MATCH = "String.IsEqual($PARAM[content]," + URL + ")"
EMPTY = (MATCH + " + !Integer.IsGreater(Container($PARAM[id]).NumItems,0)"
         " + !Container($PARAM[id]).IsUpdating")


class DiscoveryWidget(unittest.TestCase):
    def setUp(self):
        self.overrides = ET.parse(ROOT / "shortcuts/overrides.xml").getroot()
        self.widgets = ET.parse(ROOT / "1080i/Includes_Widgets.xml").getroot()

    def test_exact_guard_and_literal_route(self):
        group = self.overrides.find("widget-groupings")
        node = group[-1]
        self.assertEqual(node.attrib, {"label": "$LOCALIZE[31942]", "condition":
                         "System.AddonIsEnabled(plugin.video.themoviedb.helper)"})
        self.assertEqual(len(node), 1)
        leaf = node[0]
        self.assertEqual(leaf.text, URL)
        self.assertEqual(leaf.attrib, dict(widget="AuraDiscoverTrendingMovies",
                         label="$LOCALIZE[31943]", widgetName="$LOCALIZE[31943]",
                         icon="DefaultMovies.png", widgetType="movies", widgetTarget="videos"))
        messages, duplicates = po_messages((ROOT / "language/resource.language.en_gb/strings.po").read_bytes())
        self.assertFalse(duplicates)
        self.assertEqual([messages[i] for i in (31942, 31943, 31944)], [
            "Online Discovery (TMDb)", "Trending Movies (Online, TMDb)",
            "Unavailable or no results. Check your connection."])

    def test_no_implicit_assignment_or_monitor(self):
        # One route in picker only; existing provider integrations are not hooks
        # for this opt-in source. Templates/defaults/settings remain independent.
        for parent in self.overrides:
            if parent.tag != "widget-groupings":
                self.assertNotIn("trending_week", ET.tostring(parent, encoding="unicode"))
                self.assertNotIn("AuraDiscover", ET.tostring(parent, encoding="unicode"))
        for folder in ("1080i", "shortcuts", "resources"):
            for path in (ROOT / folder).rglob("*.xml"):
                if path.name in {"overrides.xml", "Includes_Widgets.xml"}:
                    continue
                text = path.read_text()
                self.assertNotIn("trending_week", text, str(path))
                self.assertNotIn("AuraDiscoverTrendingMovies", text, str(path))
        self.assertEqual(len(self.overrides.findall(".//shortcut[@widget='AuraDiscoverTrendingMovies']")), 1)
        self.assertNotIn("RunScript", URL)

    def test_assignment_reload_is_literal_and_inert(self):
        path = self.overrides.find(".//shortcut[@widget='AuraDiscoverTrendingMovies']").text
        # Shortcuts 2.0.3 preserves paths already containing reload= rather than
        # appending its variable library-refresh trigger. No Kodi execution.
        self.assertTrue(path.endswith("&reload=0"))
        self.assertEqual([(key, value) for key, value in parse_qsl(urlsplit(path).query)
                          if key == "reload"], [("reload", "0")])
        self.assertNotIn("$INFO[", path)
        self.assertNotIn("$VAR[", path)
        self.assertNotIn("$", path)

    def test_category_fingerprint_is_unique_and_all_uri_guards_follow_it(self):
        self.assertIn("plugin_category=Aura%20Online%20Discovery&reload=0", URL)
        self.assertEqual(dict(parse_qsl(urlsplit(URL).query))["plugin_category"],
                         "Aura Online Discovery")
        guards = []
        for node in self.widgets.iter():
            for text in [node.text or "", *node.attrib.values()]:
                if "info=trending_week" in text:
                    self.assertIn(MATCH, text)
                    guards.append(text)
        self.assertEqual(len(guards), 3)
        routes = [n.text for n in self.overrides.iter()
                  if "plugin_category=" in (n.text or "")]
        self.assertEqual(routes, [URL])
        for other in (URL.replace("&plugin_category=Aura%20Online%20Discovery", ""),
                      URL.replace("trending_week", "popular"),
                      URL.replace("tmdb_type=movie", "tmdb_type=tv"),
                      URL.replace("Aura%20Online%20Discovery", "Other%20Widget")):
            self.assertNotEqual(other, URL)

    def test_info_subject_category_lifecycle_and_stock_play(self):
        dialog = ET.parse(ROOT / "1080i/DialogVideoInfo.xml").getroot()
        self.assertEqual([n.text for n in dialog.findall("onload")
                          if "Aura.Info.Category" in (n.text or "")],
                         ["SetProperty(Aura.Info.Category,$INFO[ListItem.Property(widget)])"])
        self.assertEqual([n.text for n in dialog.findall("onunload")
                          if "Aura.Info.Category" in (n.text or "")],
                         ["ClearProperty(Aura.Info.Category)"])
        self.assertIn("SetProperty(Aura.Info.DBID,$INFO[ListItem.DBID])",
                      [n.text for n in dialog.findall("onload")])
        self.assertIn("ClearProperty(Aura.Info.DBID)",
                      [n.text for n in dialog.findall("onunload")])
        stock = dialog.find(".//control[@id='8']")
        self.assertEqual(stock.findtext("description"), "Play")
        self.assertEqual(stock.findtext("include"), "Defs_Hidden_Button")
        self.assertFalse(stock.findall("visible"))
        self.assertFalse(stock.findall("enable"))

    def test_visible_play_gate_is_subject_scoped_not_focused_item_or_player(self):
        items = ET.parse(ROOT / "1080i/Includes_Items.xml").getroot()
        play = items.find("include[@name='Items_Info']/content/item")
        self.assertEqual(play.findtext("onclick"), "SendClick(8)")
        enabled = "Control.IsEnabled(8)"
        tagged = "String.IsEqual(Window.Property(Aura.Info.Category),Aura Online Discovery)"
        local = "Integer.IsGreater(Window.Property(Aura.Info.DBID),0)"
        gate = play.findtext("visible")
        self.assertEqual(gate, enabled + " + ![" + tagged + " + !" + local + "]")
        # Bounded Boolean translation of this exact source expression only;
        # not a Kodi condition evaluator or native visibility acceptance.
        for category in ("Aura Online Discovery", "", "Trending Movies", "Other Widget"):
            for dbid in ("", "-1", "0", "1", "42"):
                positive = bool(dbid) and int(dbid) > 0
                for stock_enabled in (False, True):
                    with self.subTest(category=category, dbid=dbid, enabled=stock_enabled):
                        expression = gate.replace(enabled, str(stock_enabled)).replace(
                            tagged, str(category == "Aura Online Discovery")).replace(local, str(positive))
                        expression = expression.replace("+", " and ").replace("!", " not ").replace(
                            "[", "(").replace("]", ")")
                        self.assertEqual(eval(expression, {"__builtins__": {}}),
                                         stock_enabled and (category != "Aura Online Discovery" or positive))

    def test_empty_state_reuses_header_and_is_row_scoped(self):
        widget = self.widgets.find("include[@name='Widget']/definition")
        header = widget.find("control")
        self.assertEqual(header.findall("visible")[1].text,
                         "Integer.IsGreater(Container($PARAM[id]).NumItems,0) | "
                         "Container($PARAM[id]).IsUpdating | " + MATCH)
        label = self.widgets.find("include[@name='Widget_Label']/definition")
        status = [c for c in label.findall(".//control")
                  if c.findtext("label") == "$LOCALIZE[31944]"]
        self.assertEqual(len(status), 1)
        self.assertEqual(status[0].findtext("visible"), EMPTY)
        labels = label.findall("control/control[@type='label']")
        title, based_on = labels[:2]
        self.assertEqual(title.attrib, {"type": "label"})
        self.assertEqual([(c.tag, c.text, c.attrib) for c in title], [
            ("left", "2", {}), ("textcolor", "main_fg_100", {}),
            ("label", "$PARAM[label]", {}),
            ("include", "Statusbar_Menubar_Items", {})])
        self.assertEqual(based_on.attrib, {"type": "label"})
        self.assertEqual([(c.tag, c.text, c.attrib) for c in based_on], [
            ("left", "-16", {}), ("textcolor", "main_fg_100", {}),
            ("label", "$INFO[Container($PARAM[id]).ListItem.Property(BasedOnLabel), ,]", {}),
            ("include", "Statusbar_Menubar_Items", {}),
            ("visible", "!String.IsEmpty(Container($PARAM[id]).ListItem.Property(BasedOnLabel))", {})])
        # Original grouplist, two images and six labels, plus one status label.
        self.assertEqual(len(label.findall(".//control")), 10)
        self.assertEqual(status[0].attrib, {"type": "label"})
        self.assertIs(labels[2], status[0])
        self.assertFalse(status[0].findall("onclick"))

    def test_home_targeted_info_only_nonlocal_movie_and_native_fallthrough(self):
        definition = self.widgets.find("include[@name='Widget_Items']/definition")
        clicks = definition.findall("onclick")
        self.assertEqual(len(clicks), 1)
        self.assertEqual(clicks[0].text, "Action(Info,home)")
        tagged = "String.IsEqual(ListItem.Property(widget),Aura Online Discovery)"
        movie = "String.IsEqual(ListItem.DBType,movie)"
        local = "Integer.IsGreater(ListItem.DBID,0)"
        condition = clicks[0].get("condition")
        self.assertEqual(condition, tagged + " + " + movie + " + !" + local)
        # OnClick checks without an item, then ExecuteActions checks with the
        # clicked CFileItem. Neither pass may depend on another container.
        self.assertNotIn("Container(", condition)
        self.assertNotIn("$PARAM[", condition)
        # Bounded source-expression scope, not native condition evaluation.
        for category in ("Aura Online Discovery", "", "Trending Movies", "Other Widget"):
            for dbtype in ("movie", "tvshow", "episode", ""):
                for dbid in ("", "-1", "0", "1", "42"):
                    with self.subTest(category=category, dbtype=dbtype, dbid=dbid):
                        positive = bool(dbid) and int(dbid) > 0
                        expression = condition.replace(
                            tagged, str(category == "Aura Online Discovery")).replace(
                            movie, str(dbtype == "movie")).replace(local, str(positive))
                        expression = expression.replace("+", " and ").replace("!", " not ")
                        self.assertEqual(eval(expression, {"__builtins__": {}}),
                                         category == "Aura Online Discovery"
                                         and dbtype == "movie" and not positive)
        self.assertFalse(self.widgets.findall("include[@name='Widget_Submenu']//onclick"))

    def test_bounded_show_more_keeps_user_limit(self):
        content = self.widgets.find("include[@name='Widget_ContentInclude']")
        self.assertEqual(content.find("content").get("limit"), "$PARAM[limit]")
        self.assertEqual(content.find("content").text, "$PARAM[widgetContent]")
        self.assertIn("!" + MATCH, [v.text for v in content.findall("content/item/visible")])
        limit = self.widgets.find("include[@name='Widget_Items']//include[@content='Widget_ContentInclude']/param[@name='limit']")
        self.assertEqual(limit.get("value"), "$VAR[Label_WidgetItemLimit]")


if __name__ == "__main__":
    unittest.main()
