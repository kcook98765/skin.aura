"""Stage 8A authored source contracts only, not native/provider acceptance.

Kodi 21.3 audit: GUIInfoManager.cpp TranslateListItem/GetMultiInfoLabel keeps
the requested source; VideoGUIInfo.cpp 175-237 pairs ratings/votes and localizes
Premiered. SIS 2.0.2 script.py 764-833 and dialog/video.py 96-132 implement the
typed title request/focus return. No imports of Kodi, provider code or credentials.
"""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

from test_actor_exploration import DialogContract

ROOT = Path(__file__).resolve().parents[1]
WINDOW = "Window(movieinformation).Property(Aura.Info."


class MovieContract(DialogContract):
    def __init__(self, **changes):
        super().__init__()
        self.includes = ET.parse(ROOT / "1080i/Includes_Labels.xml").getroot()
        self.expressions.update({n.get("name"): n.text
                                 for n in self.includes.findall("expression")})
        self.items = ET.parse(ROOT / "1080i/Includes_Items.xml").getroot().find(
            "include[@name='Items_Info']/content")
        self.item = self.items.find("item[@id='9583']")
        self.active = True
        for key, value in (("DBType", "movie"), ("DBID", "31"), ("TMDB", "123"),
                           ("Category", ""), ("MovieTitle", 'Title, "A" / Ω'),
                           ("MoviePath", "/local/movie.mkv")):
            self.labels[WINDOW + key + ")"] = value
        self.labels.update({"ListItem.DBType": "movie", "ListItem.DBID": "31",
                            "ListItem.UniqueID(tmdb)": "123",
                            "ListItem.Title": 'Title, "A" / Ω',
                            "ListItem.FileNameAndPath": "/local/movie.mkv",
                            "System.AddonVersion(script.skin.info.service)": "2.0.2"})
        self.labels.update(changes)

    def condition(self, text):
        if text == "Window.IsVisible(movieinformation)":
            return self.active
        return super().condition(text)

    def variable(self, name):
        for node in self.includes.find("variable[@name='%s']" % name).findall("value"):
            if self.condition(node.get("condition", "true")):
                return node.text
        return ""

    def details(self):
        if not self.condition(self.item.findtext("visible")):
            return []
        return [n.text for n in self.item.findall("onclick")
                if self.condition(n.get("condition", "true"))]


class MediaInformationTests(unittest.TestCase):
    def test_single_last_top_item_exact_captured_movie_dispatch(self):
        f = MovieContract()
        self.assertIsNotNone(f.item)
        self.assertIs(list(f.items)[-1], f.item)
        self.assertEqual(f.item.findtext("label"), "$LOCALIZE[31954]")
        self.assertEqual(f.details(), [
            "RunScript(script.skin.info.service,action=dialog_video_info,dbtype=movie,"
            "tmdb_id=$INFO[Window(movieinformation).Property(Aura.Info.TMDB)],focus=300)"])
        self.assertEqual(f.item.findtext("visible"), "$EXP[Aura.MovieDetails]")
        self.assertEqual(f.item.find("onclick").get("condition"), "$EXP[Aura.MovieDetails]")
        self.assertEqual(len(f.item.findall("onclick")), 1)
        self.assertEqual([n.tag for n in f.item], ["label", "icon", "onclick", "visible"])
        # Existing native Play/Resume, Set, ratings, art, refresh stay before it.
        actions = [n.text for n in f.items.findall("item/onclick")]
        for action in ("SendClick(8)", "SendClick(7)", "SendClick(10)",
                       "SendClick(12)", "SendClick(6)"):
            self.assertIn(action, actions[:-1])
        movie_set = next(n for n in f.items.findall("item") if n.findtext("label") == "Movie Set")
        self.assertIn("videodb://movies/sets/", movie_set.findall("onclick")[1].text)

    def test_invalid_captured_ids_never_dispatch_even_with_valid_live_ids(self):
        for field in ("DBID", "TMDB"):
            for value in ("", "0", "-1", "not-an-id", "tt123"):
                with self.subTest(field=field, value=value):
                    f = MovieContract(**{WINDOW + field + ")": value})
                    self.assertEqual(f.details(), [])
                    # Keep subject association valid to isolate positive-ID guard.
                    live = "ListItem.DBID" if field == "DBID" else "ListItem.UniqueID(tmdb)"
                    f.labels[live] = value
                    self.assertTrue(f.condition("$EXP[Aura.MovieSubject]"))
                    self.assertEqual(f.details(), [])

    def test_both_discovery_markers_excluded_including_library_matches(self):
        for marker in ("Aura Online Discovery", "Aura Online Discovery TV"):
            for dbid in ("31", "", "0", "-1"):
                f = MovieContract(**{WINDOW + "Category)": marker, WINDOW + "DBID)": dbid,
                                     "ListItem.DBID": dbid})
                self.assertEqual(f.details(), [])
                self.assertEqual(f.variable("Aura_MovieContext"),
                                 "$LOCALIZE[31956]" if dbid == "31" else "$LOCALIZE[31957]")

    def test_native_subject_guard_rejects_changed_focused_or_stale_material(self):
        for field in ("ListItem.DBType", "ListItem.DBID", "ListItem.UniqueID(tmdb)",
                      "ListItem.Title", "ListItem.FileNameAndPath"):
            f = MovieContract(**{field: "different"})
            self.assertFalse(f.condition("$EXP[Aura.MovieSubject]"), field)
            self.assertEqual(f.details(), [])
            self.assertEqual(f.variable("Aura_MovieIMDB"), "")
            self.assertEqual(f.variable("Aura_MovieTMDB"), "")
        for kind in ("tvshow", "episode", "season", "musicvideo", "actor", "set", ""):
            f = MovieContract(**{WINDOW + "DBType)": kind, "ListItem.DBType": kind})
            self.assertFalse(f.condition("$EXP[Aura.MovieSubject]"))
            self.assertEqual(f.details(), [])
        f = MovieContract(**{WINDOW + "MovieTitle)": "", "ListItem.Title": ""})
        self.assertFalse(f.condition("$EXP[Aura.MovieSubject]"))
        f = MovieContract()
        f.active = False
        self.assertEqual(f.details(), [])

    def test_enabled_audited_sis_only_independent_of_enrichment_or_cast(self):
        f = MovieContract()
        expected = f.details()
        f.visible.clear()
        f.settings.update({"Aura.OnlineEnrichment", "VideoInfo.CastList"})
        f.labels.update({"Container(50).ListItem.Label": "Other Person",
                         "Container(9502).ListItem.DBID": "999"})
        self.assertEqual(f.details(), expected)
        f.enabled = False
        self.assertEqual(f.details(), [])
        f.enabled = True
        for version in ("", "2.0.0", "2.0.1", "unknown"):
            f.labels["System.AddonVersion(script.skin.info.service)"] = version
            self.assertEqual(f.details(), [])

    def test_native_source_pairs_missing_zero_votes_and_alias_precedence(self):
        f = MovieContract()
        self.assertEqual(f.variable("Aura_MovieIMDB"), "")
        self.assertEqual(f.variable("Aura_MovieTMDB"), "")
        # A votes-only or unnamed/default rating must not activate a named pair.
        f.labels.update({"ListItem.Rating": "8.5", "ListItem.Votes(imdb)": "23",
                         "ListItem.RatingAndVotes(imdb)": "0 (23 votes)"})
        self.assertEqual(f.variable("Aura_MovieIMDB"), "")
        for source, variable, ident in (("imdb", "Aura_MovieIMDB", 31958),
                                         ("tmdb", "Aura_MovieTMDB", 31959),
                                         ("themoviedb", "Aura_MovieTMDB", 31959)):
            f.labels["ListItem.Rating(%s)" % source] = "7.5"
            self.assertEqual(f.variable(variable), "$LOCALIZE[%s]: $INFO[ListItem.RatingAndVotes(%s)]" %
                             (ident, source))
        # Both aliases stored: exactly one TMDb pair, themoviedb preferred.
        self.assertIn("RatingAndVotes(themoviedb)", f.variable("Aura_MovieTMDB"))
        f.settings.add("Ratings.IMDB")
        f.settings.add("Ratings.TheMovieDB")
        self.assertEqual(f.variable("Aura_MovieIMDB"), "")
        self.assertEqual(f.variable("Aura_MovieTMDB"), "")

    def test_compact_native_premiere_and_source_pair_controls(self):
        f = MovieContract()
        area = f.video.find(".//control[@id='9580']")
        self.assertEqual(area.findtext("visible"), "$EXP[Aura.MovieSubject]")
        self.assertEqual((area.findtext("top"), area.findtext("height")), ("360", "48"))
        self.assertEqual([n.get("id") for n in area.findall("control")], ["9581", "9582"])
        self.assertEqual(area.find("control[@id='9581']/label").text,
                         "$VAR[Aura_MovieContext]$INFO[ListItem.Premiered,   $LOCALIZE[31955]: ,]")
        self.assertEqual(area.find("control[@id='9582']/label").text,
                         "$VAR[Aura_MovieIMDB]$VAR[Aura_MovieTMDB,   ,]")
        for label in area.findall("control"):
            self.assertEqual(label.findtext("right"), "0")
            self.assertEqual(label.findtext("scroll"), "true")
        authored = ET.tostring(area, encoding="unicode")
        for forbidden in ("onclick", "onfocus", "RunScript", "SkinInfo.", "VideoPlayer", "Container("):
            self.assertNotIn(forbidden, authored)
        for name in ("Aura_MovieIMDB", "Aura_MovieTMDB"):
            for value in f.includes.find("variable[@name='%s']" % name):
                source = re.search(r"RatingAndVotes\(([^)]+)\)", value.text)[1]
                self.assertIn("!String.IsEmpty(ListItem.Rating(%s))" % source, value.get("condition"))
                self.assertNotIn("SkinInfo.", value.text + value.get("condition"))

    def test_named_pairs_not_duplicated_and_unrelated_ratings_preserved(self):
        f = MovieContract()
        info = next(n for n in f.video.findall(".//include[@content='Object_Info']")
                    if n.find("param[@name='titleright']") is not None)
        imdb = info.find("param[@name='imdb']").get("value")
        tmdb = info.find("param[@name='tmdb']").get("value")
        self.assertTrue(f.condition(imdb))
        self.assertTrue(f.condition(tmdb))
        f.labels["ListItem.Rating(imdb)"] = "8.2"
        self.assertFalse(f.condition(imdb))
        for alias in ("themoviedb", "tmdb"):
            f.labels["ListItem.Rating(%s)" % alias] = "7.3"
            self.assertFalse(f.condition(tmdb))
            del f.labels["ListItem.Rating(%s)" % alias]
        f.labels["ListItem.DBType"] = "tvshow"
        self.assertTrue(f.condition(imdb))
        self.assertTrue(f.condition(tmdb))
        self.assertIsNone(info.find("param[@name='metacritic']"))
        self.assertIsNone(info.find("param[@name='rottentomatoes']"))
        self.assertEqual(info.find("param[@name='plot_height']").get("value"), "95")

    def test_capture_cleanup_and_localized_strings(self):
        f = MovieContract()
        for prop, label in (("MovieTitle", "Title"), ("MoviePath", "FileNameAndPath")):
            self.assertIn("SetProperty(Aura.Info.%s,$ESCINFO[ListItem.%s],movieinformation)" %
                          (prop, label), [n.text for n in f.video.findall("onload")])
            self.assertIn("ClearProperty(Aura.Info.%s,movieinformation)" % prop,
                          [n.text for n in f.video.findall("onunload")])
        for node in f.video.findall("onload") + f.video.findall("onunload"):
            self.assertNotIn("action=dialog_video_info", node.text)
        english = (ROOT / "language/resource.language.en_gb/strings.po").read_text()
        words = ("Online details (TMDb)", "Release date", "Local library",
                 "Discovery · Not matched to library", "Stored IMDb", "Stored TMDb")
        for ident, text in enumerate(words, 31954):
            self.assertEqual(english.count('msgctxt "#%s"' % ident), 1)
            self.assertIn('msgctxt "#%s"\nmsgid "%s"\nmsgstr "%s"' % (ident, text, text), english)


if __name__ == "__main__":
    unittest.main()
