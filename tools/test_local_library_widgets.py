"""Static route/selection regressions; no provider imports or Kodi execution."""

from pathlib import Path
import unittest
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

from check_omega import po_messages


ROOT = Path(__file__).resolve().parents[1]
REFRESH = "$INFO[Window(Home).Property(SkinInfo.Library.Refreshed)]"
PROVIDER = "plugin://script.skin.info.service/?action="
GUARD = "System.AddonIsEnabled(script.skin.info.service)"
NEW_IDS = ("AuraRecentEpisodesGrouped", "SkinInfoNextUpFavourites")


class LocalLibraryWidgets(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse(ROOT / "shortcuts/overrides.xml").getroot()
        self.group = self.root.find("widget-groupings")
        self.parents = {child: parent for parent in self.group.iter() for child in parent}

    def shortcut(self, widget):
        matches = self.root.findall(".//shortcut[@widget='%s']" % widget)
        self.assertEqual(len(matches), 1, widget)
        parent = matches[0]
        guarded = False
        while parent is not self.group:
            guarded |= parent.get("condition") == GUARD
            parent = self.parents[parent]
        self.assertTrue(guarded, widget)
        return matches[0]

    def binding_attributes(self, item):
        # A provider may inherit the guard or carry it on its own shortcut.
        return {key: value for key, value in item.attrib.items() if key != "condition"}

    def test_grouped_real_route_and_mixed_row_content_metadata(self):
        item = self.shortcut(NEW_IDS[0])
        self.assertEqual(self.binding_attributes(item), {
            "widget": NEW_IDS[0], "label": "$LOCALIZE[31934]",
            "icon": "DefaultRecentlyAddedEpisodes.png",
            "widgetType": "tvshows", "widgetTarget": "videos"})
        self.assertEqual(item.text, PROVIDER + "recent_episodes_grouped&include_watched=true"
                         "&limit=25")
        self.assertEqual(parse_qs(urlsplit(item.text).query), {
            "action": ["recent_episodes_grouped"], "include_watched": ["true"],
            "limit": ["25"]})

    def test_favourites_real_route_and_episode_metadata(self):
        item = self.shortcut(NEW_IDS[1])
        self.assertEqual(self.binding_attributes(item), {
            "widget": NEW_IDS[1], "label": "$ADDON[script.skin.info.service 32685]",
            "icon": "DefaultInProgressShows.png",
            "widgetType": "episodes", "widgetTarget": "videos"})
        self.assertEqual(item.text, PROVIDER + "next_up_favourites&limit=25")
        self.assertEqual(parse_qs(urlsplit(item.text).query), {
            "action": ["next_up_favourites"], "limit": ["25"]})

    def test_existing_curated_choices_preserved_with_guards(self):
        expected = [
            ("AuraSimilarMovies", "$LOCALIZE[31924]", "DefaultMovies.png", "movies",
             "similar&dbtype=movie&dbid=$INFO[Container(9986).ListItem.DBID]"),
            ("AuraSimilarTVShows", "$LOCALIZE[31925]", "DefaultTVShows.png", "tvshows",
             "similar&dbtype=tvshow&dbid=$INFO[Container(9987).ListItem.DBID]"),
            ("SkinInfoRecommendedMovies", "$ADDON[script.skin.info.service 32623]",
             "DefaultMovies.png", "movies", "recommended&dbtype=movie"),
            ("SkinInfoRecommendedTVShows", "$ADDON[script.skin.info.service 32624]",
             "DefaultTVShows.png", "tvshows", "recommended&dbtype=tvshow"),
            ("SkinInfoNextUp", "$ADDON[script.skin.info.service 32620]",
             "DefaultInProgressShows.png", "episodes", "next_up"),
        ]
        for widget, label, icon, kind, action in expected:
            with self.subTest(widget=widget):
                item = self.shortcut(widget)
                self.assertEqual(self.binding_attributes(item), dict(widget=widget, label=label, icon=icon,
                                                  widgetType=kind, widgetTarget="videos"))
                self.assertEqual(item.text, PROVIDER + action + "&limit=25&reload=" + REFRESH)

    def test_fresh_local_label_unique_and_nonempty(self):
        catalog = ROOT / "language/resource.language.en_gb/strings.po"
        messages, duplicates = po_messages(catalog.read_bytes())
        self.assertEqual(duplicates, [])
        self.assertEqual(messages[31933], "Search by category")
        self.assertEqual(messages[31934], "Recently Added Episodes (Grouped)")
        references = [n for n in self.root.iter() if n.get("label") == "$LOCALIZE[31934]"]
        self.assertEqual(references, [self.shortcut(NEW_IDS[0])])

    def test_native_neighbouring_choices_keep_saved_ids_and_paths(self):
        expected = {
            "NewTvShows": "NewShows", "RecentTvShows": "RecentTvShows",
            "RandomTvShows": "RandomTvShows", "TopRatedTvShows": "TopRatedTvShows",
            "NewEpisodes": "NewEpisodes", "Recent Episodes": "RecentEpisodes",
            "RandomEpisodes": "RandomEpisodes", "UnwatchedEpisodes": "UnwatchedEpisodes",
            "InProgressEpisodes": "InProgressEpisodes", "TopRatedEpisodes": "TopRatedEpisodes",
        }
        for widget, playlist in expected.items():
            with self.subTest(widget=widget):
                items = self.group.findall(".//shortcut[@widget='%s']" % widget)
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0].text, "special://skin/extras/playlists/" + playlist + ".xsp")
                self.assertEqual(items[0].get("widgetTarget"), "video")
        progress = self.root.find(".//shortcut[@widget='InProgress']")
        self.assertEqual(progress.text, "library://video/tvshows/inprogressshows.xml")

    def test_native_default_not_switched_to_either_new_choice(self):
        default = self.root.find("widgetdefaultnode[@labelID='tvshows']")
        self.assertEqual(default.text, "RecentEpisodes")
        self.assertEqual(default.attrib, dict(labelID="tvshows", label="20387",
                         path="videodb://recentlyaddedepisodes/", target="videos"))
        self.assertEqual(self.root.find("propertydefault[@labelID='tvshows']"
                         "[@property='widgetPath.Widget1']").text,
                         "library://video/tvshows/inprogressshows.xml")


if __name__ == "__main__":
    unittest.main()
