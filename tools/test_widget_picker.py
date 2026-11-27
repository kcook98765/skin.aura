"""Stage 5 taxonomy and saved-binding regressions (Kodi Omega / Shortcuts 2.0.3).

Static only: no Kodi imports, provider execution or profile changes.
"""

from collections import Counter
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from check_omega import po_messages


ROOT = Path(__file__).resolve().parents[1]
GUARD = "System.AddonIsEnabled(script.skin.info.service)"

# Stage 4 native binding fixture: ID, label ID, icon, exact saved path.
# An @ suffix abbreviates only the fixture's special://skin playlist prefix.
NATIVE = """
NewMovies|31185|DefaultRecentlyAddedMovies.png|@NewMovies
RecentMovies|31190|DefaultMusicRecentlyPlayed.png|@RecentMovies
RandomMovies|31200|DefaultMovies.png|@RandomMovies
InProgressMovies|31216|special://skin/extras/icons/timer.png|@InProgressMovies
TopRatedMovies|31225|DefaultMusicTop100Albums.png|@TopRatedMovies
Top250Movies|31276|DefaultMusicTop100Albums.png|@Top250Movies
UnwatchedMovies|31278|DefaultMovies.png|@UnwatchedMovies
MovieNodes|31296|special://skin/extras/icons/title.png|library://video/movies/
MovieGenres|31257|DefaultGenre.png|library://video/movies/genres.xml
MovieSets|31260|DefaultSets.png|videodb://movies/sets/
NewTvShows|31367|DefaultRecentlyAddedMovies.png|@NewShows
RecentTvShows|31194|DefaultMusicRecentlyPlayed.png|@RecentTvShows
InProgress|31196|special://skin/extras/icons/timer.png|library://video/tvshows/inprogressshows.xml
RandomTvShows|31233|DefaultTVShows.png|@RandomTvShows
TopRatedTvShows|31222|DefaultMusicTop100Albums.png|@TopRatedTvShows
TvShowNodes|31297|special://skin/extras/icons/title.png|library://video/tvshows/
TvShowGenres|31274|DefaultGenre.png|library://video/tvshows/genres.xml
NewEpisodes|31214|DefaultRecentlyAddedMovies.png|@NewEpisodes
Recent Episodes|31198|DefaultMusicRecentlyPlayed.png|@RecentEpisodes
RandomEpisodes|31202|DefaultTVShows.png|@RandomEpisodes
UnwatchedEpisodes|31283|DefaultTVShows.png|@UnwatchedEpisodes
InProgressEpisodes|31218|special://skin/extras/icons/timer.png|@InProgressEpisodes
TopRatedEpisodes|31230|DefaultMusicTop100Albums.png|@TopRatedEpisodes
NewAlbums|31238|DefaultMusicRecentlyAdded.png|musicdb://recentlyaddedalbums/
RecentAlbums|31242|DefaultMusicRecentlyPlayed.png|musicdb://recentlyplayedalbums/
TopAlbums|31243|DefaultMusicTop100Albums.png|musicdb://top100/albums/
RandomAlbums|31187|DefaultMusicAlbums.png|@RandomAlbums
RandomArtists|31295|DefaultMusicArtists.png|@RandomArtists
MusicNodes|31300|special://skin/extras/icons/title.png|library://music/
LastPlayedChannels|31381|DefaultAddonPVRClient.png|pvr://channels/tv/*?view=lastplayed
AllChannels|19287|DefaultAddonPVRClient.png|pvr://channels/tv/*
ActiveRecordings|31382|DefaultAddonPVRClient.png|pvr://recordings/tv/active?view=flat
GroupedActiveRecordings|31383|DefaultAddonPVRClient.png|pvr://recordings/tv/active?view=grouped
DeletedRecordings|19184|DefaultAddonPVRClient.png|pvr://recordings/tv/deleted?view=flat
GroupedDeletedRecordings|31384|DefaultAddonPVRClient.png|pvr://recordings/tv/deleted?view=grouped
Timers|19040|DefaultAddonPVRClient.png|pvr://timers/tv/timers
VideoSources|31159|DefaultVideo.png|sources://video/
MusicSources|31302|DefaultMusicSongs.png|sources://music/
PictureSources|31304|DefaultPicture.png|sources://pictures/
"""

CATEGORIES = [
    ("$LOCALIZE[31935]", "InProgressMovies InProgress InProgressEpisodes SkinInfoNextUp SkinInfoNextUpFavourites"),
    ("$LOCALIZE[31936]", "NewMovies NewTvShows NewEpisodes AuraRecentEpisodesGrouped"),
    ("$LOCALIZE[342]", "RecentMovies RandomMovies TopRatedMovies Top250Movies UnwatchedMovies MovieGenres MovieSets"),
    ("$LOCALIZE[31937]", ["RecentTvShows", "RandomTvShows", "TopRatedTvShows", "TvShowGenres",
                           "Recent Episodes", "RandomEpisodes", "UnwatchedEpisodes", "TopRatedEpisodes"]),
    ("$LOCALIZE[31938]", "AuraSimilarMovies AuraSimilarTVShows SkinInfoRecommendedMovies SkinInfoRecommendedTVShows"),
    ("$LOCALIZE[249]", "NewAlbums RecentAlbums TopAlbums RandomAlbums RandomArtists"),
    ("$LOCALIZE[31939]", "LastPlayedChannels AllChannels ActiveRecordings GroupedActiveRecordings DeletedRecordings GroupedDeletedRecordings Timers"),
    ("$LOCALIZE[31940]", "MovieNodes TvShowNodes MusicNodes"),
    ("32040", ""),
    ("24001", "addon addon addon addon addon"),
    ("$LOCALIZE[31942]", "AuraDiscoverTrendingMovies"),
]


class WidgetPicker(unittest.TestCase):
    def setUp(self):
        self.root = ET.parse(ROOT / "shortcuts/overrides.xml").getroot()
        self.group = self.root.find("widget-groupings")
        self.leaves = self.group.findall(".//shortcut")

    def test_exact_categories_and_direct_choices(self):
        self.assertEqual([n.tag for n in self.group], ["node"] * 11)
        self.assertEqual([n.get("label") for n in self.group], [r[0] for r in CATEGORIES])
        for node, (label, widgets) in zip(self.group, CATEGORIES):
            expected = widgets.split() if isinstance(widgets, str) else widgets
            self.assertEqual([n.get("widget") for n in node.findall("shortcut")], expected, label)
        # No provider browsing or dynamic sorting in curated headings.
        for node in list(self.group)[:7]:
            self.assertTrue(all(n.tag == "shortcut" for n in node))

    def test_retained_count_unique_paths_and_native_bindings(self):
        historical = [n for n in self.leaves if n.get("widget") != "AuraDiscoverTrendingMovies"]
        self.assertEqual(len(historical), 51)
        self.assertEqual(len({n.text for n in historical}), 51)
        self.assertEqual(len(self.leaves), 52)
        for row in NATIVE.strip().splitlines():
            widget, label, icon, path = row.split("|")
            if path.startswith("@"):
                path = "special://skin/extras/playlists/" + path[1:] + ".xsp"
            target = ("music" if widget in {"NewAlbums", "RecentAlbums", "TopAlbums",
                      "RandomAlbums", "RandomArtists", "MusicNodes", "MusicSources"}
                      else "pictures" if widget == "PictureSources"
                      else "pvr" if path.startswith("pvr:") else "video")
            matches = [n for n in self.leaves if n.get("widget") == widget]
            self.assertEqual(len(matches), 1, widget)
            item = matches[0]
            attrs = dict(widget=widget, label="$LOCALIZE[%s]" % label,
                         icon=icon, widgetTarget=target)
            if widget == "NewTvShows":
                attrs.update(label="$LOCALIZE[31941]", widgetName="$LOCALIZE[31367]")
            self.assertEqual(item.attrib, attrs, widget)
            self.assertEqual(item.text.encode("utf-8"), path.encode("utf-8"), widget)

    def test_provider_visibility_and_reachability_without_provider(self):
        def visible_leaves(node, enabled):
            if node.get("condition") in {GUARD, "System.AddonIsEnabled(plugin.video.themoviedb.helper)"} and not enabled:
                return []
            if node.tag == "shortcut":
                return [node]
            return [leaf for child in node for leaf in visible_leaves(child, enabled)]

        providers = [n for n in self.leaves if n.text.startswith("plugin://script.skin.info.service/")]
        self.assertEqual(len(providers), 7)
        self.assertEqual(visible_leaves(self.group, True), self.leaves)
        self.assertEqual(visible_leaves(self.group, False), [n for n in self.leaves if n not in providers and n.get("widget") != "AuraDiscoverTrendingMovies"])
        self.assertEqual(self.group[4].attrib, dict(label="$LOCALIZE[31938]", condition=GUARD))
        for index in (0, 1):
            self.assertNotIn("condition", self.group[index].attrib)
        self.assertEqual(Counter(n.get("condition") for n in self.group.iter() if n.get("condition")),
                         Counter({GUARD: 4, "System.Platform.Android": 1,
                                  "System.AddonIsEnabled(plugin.video.themoviedb.helper)": 1}))

    def test_native_content_and_source_hierarchy(self):
        library = self.group[7]
        self.assertEqual([n.get("label") for n in library.findall("node")],
                         ["32030", "32031", "32020", "$LOCALIZE[14224]"])
        for label, content, source in (("32030", "video", "videosources"),
                                       ("32031", "music", "musicsources")):
            node = library.find("node[@label='%s']" % label)
            self.assertEqual([n.text for n in node.findall("content")], [content])
            self.assertEqual([n.text for n in node.findall("node[@label='32075']/content")], [source])
        self.assertEqual(library.find("node[@label='32020']/content").text, "picturesources")
        files = library.find("node[@label='$LOCALIZE[14224]']")
        self.assertEqual(files.find("content").text, "widgets")
        self.assertEqual([n.get("widget") for n in files.findall("shortcut")],
                         ["VideoSources", "MusicSources", "PictureSources"])
        playlists = self.group[8]
        self.assertEqual([n.get("label") for n in playlists], ["32030", "32031"])
        self.assertEqual([n.text for n in playlists.findall("node/content")],
                         ["playlist-video", "playlist-audio"])
        self.assertEqual(Counter(n.text for n in self.group.iter("content")), Counter([
            "video", "videosources", "music", "musicsources", "picturesources", "widgets",
            "playlist-video", "playlist-audio", "addon-video", "addon-audio", "addon-image",
            "addon-program-plugin"]))

    def test_original_addon_children_and_fixed_list_bindings(self):
        addons = self.group[9]
        self.assertEqual([(n.get("label"), n.find("content").text) for n in addons.findall("node")],
                         [("32010", "addon-video"), ("32011", "addon-audio"),
                          ("32012", "addon-image"), ("32009", "addon-program-plugin")])
        expected = [
            ("10001", "32021", "DefaultAddonProgram.png", "program", "programs", "addons://sources/executable/"),
            ("20244", "32021", "DefaultAddonProgram.png", "program", "programs", "androidapp://sources/apps/"),
            ("1037", "32014", "DefaultAddonVideo.png", "video", "video", "addons://sources/video/"),
            ("1038", "32019", "DefaultAddonMusic.png", "music", "music", "addons://sources/audio/"),
            ("1039", "32020", "DefaultAddonPicture.png", "picture", "pictures", "addons://sources/image/"),
        ]
        for item, (label, kind, icon, widget_type, target, path) in zip(addons.findall("shortcut"), expected):
            attrs = dict(label=label, type=kind, icon=icon, widget="addon",
                         widgetType=widget_type, widgetTarget=target)
            if label == "20244":
                attrs["condition"] = "System.Platform.Android"
            self.assertEqual(item.attrib, attrs)
            self.assertEqual(item.text.encode(), path.encode())

    def test_labels_and_original_default_bindings(self):
        messages, duplicates = po_messages((ROOT / "language/resource.language.en_gb/strings.po").read_bytes())
        self.assertEqual(duplicates, [])
        self.assertEqual([messages[n] for n in range(31935, 31942)], [
            "Continue Watching & Next Up", "Recently Added Video", "TV Shows & Episodes",
            "Local Recommendations", "Live TV & Recordings", "Library & Sources",
            "Recent Shows with Unwatched Episodes"])
        expected = [
            ("20342", "20386", "videodb://recentlyaddedmovies/", "videos", "RecentMovies"),
            ("tvshows", "20387", "videodb://recentlyaddedepisodes/", "videos", "RecentEpisodes"),
            ("2", "359", "musicdb://recentlyaddedalbums/", "music", "RecentAlbums"),
            ("31103", "19023", "pvr://channels/tv/*?view=lastplayed", "pvr", "TVChannels"),
            ("24001", "1037", "addons://sources/video", "videos", "VideoAddons"),
        ]
        self.assertEqual([(n.get("labelID"), n.get("label"), n.get("path"), n.get("target"), n.text)
                          for n in self.root.findall("widgetdefaultnode")], expected)
        # All authored property defaults, not just the TV path checked in Stage 4.
        props = {}
        for label, name1, path1, target, name2, path2 in [
            ("20342", "31200", "special://skin/extras/playlists/RandomMovies.xsp", "videos", "135", "library://video/movies/genres.xml"),
            ("tvshows", "626", "library://video/tvshows/inprogressshows.xml", "videos", "135", "library://video/tvshows/genres.xml"),
            ("2", "517", "library://music/recentlyplayedalbums.xml", "music", "135", "library://music/genres.xml"),
            ("24001", "1038", "addons://sources/audio", "music", "1043", "addons://sources/executable"),
        ]:
            for slot, name, path in ((1, name1, path1), (2, name2, path2)):
                for key, value in (("widgetName", "$LOCALIZE[%s]" % name), ("widgetPath", path),
                                   ("widgetTarget", "programs" if label == "24001" and slot == 2 else target)):
                    props[(label, "%s.Widget%s" % (key, slot))] = value
        props[("tvshows", "widgetAspect")] = "$LOCALIZE[31038]"
        for suffix in ("", ".Widget1", ".Widget2"):
            props[("24001", "WidgetSort" + suffix)] = "lastused"
            props[("24001", "WidgetDirection" + suffix)] = "descending"
        actual = self.root.findall("propertydefault")
        self.assertEqual(len(actual), len(props))
        self.assertEqual({(n.get("labelID"), n.get("property")): n.text for n in actual}, props)
        self.assertEqual([(n.attrib, n.text) for n in self.root.findall("widgetdefault")],
                         [({"labelID": "5"}, "Settings"), ({"labelID": "33060"}, "Weather")])


if __name__ == "__main__":
    unittest.main()
