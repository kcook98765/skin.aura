"""Focused Omega 21.3 source contracts; does not execute Kodi or providers."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from check_omega import po_messages

ROOT = Path(__file__).resolve().parents[1]
URL = ("plugin://plugin.video.themoviedb.helper/?info=trending_week&tmdb_type=movie"
       "&widget=true&limit=12&nextpage=false&cacheonly=true&fanarttv=false")
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
        self.assertNotIn("reload=", URL)
        self.assertNotIn("RunScript", URL)

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

    def test_info_only_nonlocal_movie_and_native_fallthrough(self):
        definition = self.widgets.find("include[@name='Widget_Items']/definition")
        clicks = definition.findall("onclick")
        self.assertEqual(len(clicks), 1)
        self.assertEqual(clicks[0].text, "Action(Info)")
        self.assertEqual(clicks[0].get("condition"), MATCH +
                         " + String.IsEqual(Container($PARAM[id]).ListItem.DBType,movie)"
                         " + !Integer.IsGreater(Container($PARAM[id]).ListItem.DBID,0)")
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
