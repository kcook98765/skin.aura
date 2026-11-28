"""Stage 8A/8B/8C authored source contracts only, not native/provider acceptance.

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
        self.assertEqual(f.item.findtext("visible"), "$EXP[Aura.MovieDetails] | $EXP[Aura.ShowDetails]")
        self.assertEqual(f.item.find("onclick").get("condition"), "$EXP[Aura.MovieDetails]")
        self.assertEqual(len(f.item.findall("onclick")), 2)
        self.assertEqual([n.tag for n in f.item], ["label", "icon", "onclick", "onclick", "visible"])
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
            self.assertFalse(f.condition("$EXP[Aura.MovieDetails]"))
            if kind != "tvshow":  # 8B adds a separately tested, typed show branch.
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


class TVContract(MovieContract):
    def __init__(self, kind="tvshow", **changes):
        super().__init__()
        for field, value in (("DBType", kind), ("Season", "0"), ("Episode", "2")):
            self.labels[WINDOW + field + ")"] = value
            self.labels["ListItem." + field] = value
        self.labels.update(changes)

    def condition(self, text):
        if text == "ListItem.IsResumable":
            return self.labels.get(text) == "true"
        return super().condition(text)

    def progress(self):
        """Bounded INFO-prefix rendering contract, not Kodi runtime execution."""
        text = self.video.find(".//control[@id='9586']/label").text
        text = re.sub(r"\$VAR\[([^]]+)\]", lambda m: self.variable(m[1]), text)
        english = (ROOT / "language/resource.language.en_gb/strings.po").read_text()
        messages = dict(re.findall(r'msgctxt "#(\d+)"\nmsgid "([^"\n]*)"', english))
        text = re.sub(r"\$LOCALIZE\[(\d+)\]", lambda m: messages[m[1]], text)

        def info(match):
            value = self.labels.get(match[1], "")
            return match[2].replace("$COMMA", ",") + str(value) if value != "" else ""

        return re.sub(r"\$INFO\[(ListItem\.Property\([^)]+\)),([^,\]]*),\]", info, text)


class TVInformationTests(unittest.TestCase):
    facts = ("Aura_TVStatus", "Aura_TVAired", "Aura_TVSeason", "Aura_TVEpisode",
             "Aura_TVProgress", "Aura_TVEpisodeState")

    def test_only_show_dispatches_typed_captured_show_id(self):
        f = TVContract()
        self.assertEqual(f.details(), [
            "RunScript(script.skin.info.service,action=dialog_video_info,dbtype=tvshow,"
            "tmdb_id=$INFO[Window(movieinformation).Property(Aura.Info.TMDB)],focus=300)"])
        for kind in ("season", "episode", "musicvideo", "actor", "set", ""):
            f = TVContract(kind)
            f.labels.update({WINDOW + "ShowTMDB)": "456", WINDOW + "TVShowDBID)": "789"})
            self.assertEqual(f.details(), [], kind)
        for field in ("DBID", "TMDB"):
            for value in ("", "0", "-1", "bad", "tt123"):
                f = TVContract(**{WINDOW + field + ")": value})
                self.assertEqual(f.details(), [])
                live = "ListItem.DBID" if field == "DBID" else "ListItem.UniqueID(tmdb)"
                f.labels[live] = value
                self.assertEqual(f.details(), [])

    def test_show_route_requires_audited_enabled_sis_not_enrichment(self):
        f = TVContract()
        expected = f.details()
        f.settings.update({"Aura.OnlineEnrichment", "VideoInfo.CastList"})
        f.visible.clear()
        self.assertEqual(f.details(), expected)
        f.enabled = False
        self.assertEqual(f.details(), [])
        f.enabled = True
        for version in ("", "2.0.0", "2.0.1", "unknown"):
            f.labels["System.AddonVersion(script.skin.info.service)"] = version
            self.assertEqual(f.details(), [])

    def test_native_tv_facts_independent_of_online_ids_sis_and_enrichment(self):
        for kind in ("tvshow", "season", "episode"):
            f = self.populated(kind)
            expected = [f.variable(n) for n in self.facts]
            f.enabled = False
            f.visible.clear()
            f.labels.update({WINDOW + "TMDB)": "", "ListItem.UniqueID(tmdb)": "",
                             "System.AddonVersion(script.skin.info.service)": "",
                             "Container(9502).ListItem.DBID": "999",
                             "Container(50).ListItem.Label": "Different Actor"})
            self.assertEqual([f.variable(n) for n in self.facts], expected)
            self.assertEqual(f.details(), [])
            f.settings.add("Aura.OnlineEnrichment")
            self.assertEqual([f.variable(n) for n in self.facts], expected)

    def populated(self, kind="tvshow", **changes):
        return TVContract(kind, **{
            "ListItem.Status": "Ended", "ListItem.Premiered": "28 November 2026",
            "ListItem.Property(TotalEpisodes)": "12",
            "ListItem.Property(WatchedEpisodes)": "0",
            "ListItem.Property(UnWatchedEpisodes)": "12", "ListItem.PlayCount": "1",
            "ListItem.IsResumable": "true", **changes})

    def test_focus_or_stale_subject_cannot_reattribute_any_tv_facts(self):
        for kind in ("tvshow", "season", "episode"):
            fields = ["DBType", "DBID", "UniqueID(tmdb)", "Title", "FileNameAndPath"]
            if kind != "tvshow":
                fields += ["Season", "Episode"]
            for field in fields:
                f = self.populated(kind, **{"ListItem." + field: "different"})
                self.assertFalse(f.condition("$EXP[Aura.LocalTVSubject]"), (kind, field))
                self.assertEqual(f.details(), [])
                self.assertEqual([f.variable(n) for n in self.facts], [""] * len(self.facts))
            f = self.populated(kind)
            f.active = False
            self.assertFalse(f.condition("$EXP[Aura.LocalTVSubject]"))
        f = self.populated(**{WINDOW + "MovieTitle)": "", "ListItem.Title": ""})
        self.assertFalse(f.condition("$EXP[Aura.LocalTVSubject]"))

    def test_discovery_even_library_match_and_nonlocal_rows_are_quiet(self):
        for kind in ("tvshow", "season", "episode"):
            for marker in ("Aura Online Discovery", "Aura Online Discovery TV", ""):
                for dbid in ("31", "", "0", "-1"):
                    if not marker and dbid == "31":
                        continue
                    f = self.populated(kind, **{WINDOW + "Category)": marker,
                                              WINDOW + "DBID)": dbid, "ListItem.DBID": dbid})
                    self.assertEqual(f.details(), [])
                    self.assertEqual([f.variable(n) for n in self.facts], [""] * len(self.facts))

    def test_status_and_localized_first_air_are_typed_and_missing_quiet(self):
        f = TVContract()
        self.assertEqual(f.variable("Aura_TVStatus"), "")
        self.assertEqual(f.variable("Aura_TVAired"), "")
        for status in ("Unknown", "unknown", "N/A", "None", "0", "-", ""):
            f.labels["ListItem.Status"] = status
            self.assertEqual(f.variable("Aura_TVStatus"), "")
        for status in ("Returning Series", "Ended", "Canceled"):
            f.labels["ListItem.Status"] = status
            self.assertEqual(f.variable("Aura_TVStatus"), "$LOCALIZE[31960]: $INFO[ListItem.Status]")
        for kind in ("tvshow", "episode", "season"):
            f = self.populated(kind)
            # Even a nonempty episode Premiered may be the series date fallback.
            self.assertEqual(f.variable("Aura_TVAired"),
                             "$LOCALIZE[31961]: $INFO[ListItem.Premiered]" if kind == "tvshow" else "")
            if kind != "tvshow":
                self.assertEqual(f.variable("Aura_TVStatus"), "")

    def test_coordinates_known_only_specials_zero_not_show_episode_totals(self):
        for kind in ("tvshow", "season", "episode"):
            for field, variable, minimum in (("Season", "Aura_TVSeason", 0),
                                              ("Episode", "Aura_TVEpisode", 1)):
                # Native LISTITEM_SEASON emits only nonnegative seasons or empty.
                values = ("", "0", "1") if field == "Season" else ("", "-1", "0", "1", "bad")
                for value in values:
                    f = TVContract(kind, **{"ListItem." + field: value, WINDOW + field + ")": value})
                    allowed = (kind in ("season", "episode") if field == "Season" else kind == "episode")
                    known = value.isdigit() and int(value) >= minimum
                    self.assertEqual(bool(f.variable(variable)), allowed and known, (kind, field, value))

    def test_native_integer_counts_render_directly_and_keep_populated_zero(self):
        for kind in ("tvshow", "season"):
            f = TVContract(kind, **{"ListItem.Property(TotalEpisodes)": 3,
                                    "ListItem.Property(WatchedEpisodes)": 1,
                                    "ListItem.Property(UnWatchedEpisodes)": 2})
            self.assertEqual(f.progress(), "Episodes: 3, Watched: 1, Unwatched: 2")
            f.enabled = False
            self.assertEqual(f.progress(), "Episodes: 3, Watched: 1, Unwatched: 2")
            for prop, label in (("TotalEpisodes", "Episodes"), ("WatchedEpisodes", "Watched"),
                                ("UnWatchedEpisodes", "Unwatched")):
                f.labels["ListItem.Property(%s)" % prop] = 0
                self.assertIn(label + ": 0", f.progress())
                f.labels["ListItem.Property(%s)" % prop] = ""
                self.assertNotIn(label + ":", f.progress())
            self.assertEqual(f.progress(), "")
            f.labels["ListItem.Episode"] = "99"
            f.labels["ListItem.Property(NumEpisodes)"] = "99"
            self.assertEqual(f.progress(), "")

    def test_episode_state_positive_native_only_no_unwatched_default_claim(self):
        f = TVContract("episode")
        self.assertEqual(f.variable("Aura_TVEpisodeState"), "")
        for value in ("", "0", "-1", "bad"):
            f.labels["ListItem.PlayCount"] = value
            self.assertEqual(f.variable("Aura_TVEpisodeState"), "")
        f.labels["ListItem.PlayCount"] = "1"
        self.assertEqual(f.variable("Aura_TVEpisodeState"), "$LOCALIZE[31965]")
        self.assertEqual(f.progress(), "Watched")
        f.labels["ListItem.IsResumable"] = "true"
        self.assertEqual(f.variable("Aura_TVEpisodeState"), "$LOCALIZE[31966]")
        self.assertEqual(f.progress(), "Resumable")
        for kind in ("tvshow", "season"):
            self.assertEqual(self.populated(kind).variable("Aura_TVEpisodeState"), "")

    def test_native_play_browse_series_list_and_resume_mechanism_preserved(self):
        f = TVContract()
        play = f.items.find("item")
        self.assertEqual(play.findtext("label"), "$INFO[Control.GetLabel(8)]")
        self.assertEqual([n.text for n in play.findall("onclick")], ["SendClick(8)"])
        self.assertEqual(play.findtext("visible"), "Control.IsEnabled(8) + ![[String.IsEqual(Window.Property(Aura.Info.Category),Aura Online Discovery) | String.IsEqual(Window.Property(Aura.Info.Category),Aura Online Discovery TV)] + !Integer.IsGreater(Window.Property(Aura.Info.DBID),0)]")
        button = f.video.find(".//control[@id='8']")
        self.assertEqual(button.findtext("include"), "Defs_Hidden_Button")
        self.assertEqual(button.findall("onclick"), [])
        # No dedicated Resume 9: core Play retains its default Play/Resume chooser.
        self.assertIsNone(f.video.find(".//control[@id='9']"))
        series = next(n for n in f.items.findall("item") if n.findtext("label") == "Series List")
        self.assertEqual([n.text for n in series.findall("onclick")], ["Dialog.Close(all)",
                         "ActivateWindow(videos,videodb://tvshows/titles/$INFO[ListItem.TvShowDBID]/$INFO[ListItem.Season]/,return)"])
        self.assertEqual(series.findall("onclick")[1].get("condition"), "!String.IsEmpty(ListItem.DBID)")
        self.assertEqual([n.text for n in series.findall("visible")],
                         ["Control.IsEnabled(8)", "String.IsEqual(ListItem.DBType,episode)"])

    def test_compact_read_only_tv_area_and_english_labels(self):
        f = TVContract()
        area = f.video.find(".//control[@id='9584']")
        self.assertEqual(area.findtext("visible"), "$EXP[Aura.LocalTVSubject]")
        self.assertEqual((area.findtext("top"), area.findtext("height")), ("360", "48"))
        self.assertEqual([n.get("id") for n in area.findall("control")], ["9585", "9586"])
        for label in area.findall("control"):
            self.assertEqual(label.findtext("height"), "24")
            self.assertEqual(label.findtext("font"), "font_tiny")
            self.assertEqual(label.findtext("scroll"), "true")
            self.assertEqual(label.findtext("right"), "0")
        self.assertEqual(area.find("control[@id='9585']/label").text,
                         "$VAR[Aura_TVStatus]$VAR[Aura_TVSeason]$VAR[Aura_TVEpisode,   ,]$VAR[Aura_TVAired,   ,]")
        self.assertEqual(area.find("control[@id='9586']/label").text,
                         "$VAR[Aura_TVProgress]$VAR[Aura_TVEpisodeState]")
        authored = ET.tostring(area, encoding="unicode") + "".join(
            ET.tostring(f.includes.find("variable[@name='%s']" % name), encoding="unicode")
            for name in self.facts)
        for forbidden in ("onclick", "onfocus", "RunScript", "SkinInfo.", "VideoPlayer",
                          "NextAired", "NumEpisodes"):
            self.assertNotIn(forbidden, authored)
        self.assertLessEqual(set(re.findall(r"Container\((\d+)\)", authored)), {"9587"})
        english = (ROOT / "language/resource.language.en_gb/strings.po").read_text()
        for ident, text in enumerate(("Status", "First aired", "Season", "Episode", "Episodes",
                                      "Watched", "Resumable", "Unwatched"), 31960):
            self.assertEqual(english.count('msgctxt "#%s"' % ident), 1)
            self.assertIn('msgctxt "#%s"\nmsgid "%s"\nmsgstr "%s"' % (ident, text, text), english)


class LocalTVDetailsTests(unittest.TestCase):
    """SIS 2.0.2 dbid.py 264-337 sets the returned InfoTag's type and DBID.

    properties.py 1086/1088, 1171/1172 omit zero counts; 1232 retains raw
    firstaired. The handler uses local GetXDetails/GetEpisodes and local caches,
    not online.py. These tests evaluate authored XML, never execute SIS/Kodi.
    """
    route = ("plugin://script.skin.info.service/?action=getdetails"
             "&dbid=$INFO[Window(movieinformation).Property(Aura.Info.DBID)]"
             "&dbtype=$INFO[Window(movieinformation).Property(Aura.Info.DBType)]")

    def row(self, kind="episode", **changes):
        return TVContract(kind, **{
            "Container(9587).NumItems": "1", "Container(9587).ListItem.DBID": "31",
            "Container(9587).ListItem.DBType": kind,
            "Container(9587).ListItem.Property(Episode)": "12",
            "Container(9587).ListItem.Property(WatchedEpisodes)": "4",
            "Container(9587).ListItem.Property(FirstAired)": "2020-03-04", **changes})

    def test_series_season_never_request_or_read_sis_counts(self):
        for kind in ("tvshow", "season"):
            f = self.row(kind)
            self.assertEqual(f.variable("Aura_LocalTVDetails"), "")
            self.assertFalse(f.condition("$EXP[Aura.LocalTVDetailsReady]"))
            self.assertEqual(f.progress(), "")

    def test_single_nonfocusable_offscreen_dynamic_container(self):
        f = self.row()
        nodes = f.video.findall(".//control[@id='9587']")
        self.assertEqual(len(nodes), 1)
        node = nodes[0]
        self.assertEqual(node.get("type"), "list")
        self.assertLess(int(node.findtext("left")), -1920)
        self.assertEqual(node.findtext("enable"), "false")
        self.assertEqual((node.findtext("width"), node.findtext("height")), ("1", "1"))
        self.assertEqual(node.findtext("content"), "$VAR[Aura_LocalTVDetails]")
        self.assertEqual(node.find("content").get("browse"), "never")
        self.assertEqual([n.tag for n in node],
                         ["left", "width", "height", "enable", "itemlayout", "focusedlayout", "content"])
        for layout in (node.find("itemlayout"), node.find("focusedlayout")):
            self.assertEqual(layout.attrib, {"width": "1", "height": "1"})
            self.assertEqual(list(layout), [])
        self.assertEqual(f.variable("Aura_LocalTVDetails"), self.route)
        # No navigation, focus, click, timer/reload or lifecycle script dispatch.
        for n in f.video.iter():
            if n.tag.startswith("on") and n.text:
                self.assertNotIn("9587", n.text)
        self.assertEqual(len(f.includes.find("variable[@name='Aura_LocalTVDetails']")), 1)
        authored = ET.tostring(node, encoding="unicode")
        for name in ("Aura_LocalTVDetails", "Aura.LocalTVDetailsRequest", "Aura.LocalTVDetailsReady"):
            authored += ET.tostring(next(n for n in f.includes if n.get("name") == name),
                                    encoding="unicode")
        for forbidden in ("http", "tmdb_id", "RunScript", "SkinInfo.", "Aura.OnlineEnrichment",
                          "Property(DBID)", "reload", "texture", "onfocus", "onclick", "Home",
                          "TVShowDBID", "Skin.HasSetting"):
            self.assertNotIn(forbidden, authored)

    def test_request_is_captured_typed_local_only_not_online_id_or_setting(self):
        for kind in ("episode",):
            f = self.row(kind, **{WINDOW + "TMDB)": "", "ListItem.UniqueID(tmdb)": ""})
            self.assertEqual(f.variable("Aura_LocalTVDetails"), self.route)
            f.settings.add("Aura.OnlineEnrichment")
            self.assertEqual(f.variable("Aura_LocalTVDetails"), self.route)
            f.enabled = False
            self.assertEqual(f.variable("Aura_LocalTVDetails"), "")
            self.assertFalse(f.condition("$EXP[Aura.LocalTVDetailsReady]"))
            f.enabled = True
            f.labels["System.AddonVersion(script.skin.info.service)"] = "2.0.1"
            self.assertEqual(f.variable("Aura_LocalTVDetails"), "")
        for kind in ("tvshow", "season", "movie", "set", "actor", "musicvideo", ""):
            self.assertEqual(self.row(kind).variable("Aura_LocalTVDetails"), "")
        for marker in ("Aura Online Discovery", "Aura Online Discovery TV"):
            for kind in ("tvshow", "season", "episode"):
                f = self.row(kind, **{WINDOW + "Category)": marker})
                self.assertEqual(f.variable("Aura_LocalTVDetails"), "")
                self.assertFalse(f.condition("$EXP[Aura.LocalTVDetailsReady]"))
        for dbid in ("", "0", "-1", "bad"):
            f = self.row(**{WINDOW + "DBID)": dbid, "ListItem.DBID": dbid})
            self.assertEqual(f.variable("Aura_LocalTVDetails"), "")

    def test_returned_row_identity_not_property_dbid_and_never_stale_or_loading(self):
        for kind in ("tvshow", "season", "episode"):
            for field, values in (("DBID", ("", "0", "-1", "32", "bad")),
                                  ("DBType", tuple(x for x in ("", "movie", "actor", "tvshow", "season", "episode")
                                                   if x != kind))):
                for value in values:
                    f = self.row(kind, **{"Container(9587).ListItem." + field: value,
                                          "Container(9587).ListItem.Property(DBID)": "31"})
                    self.assertFalse(f.condition("$EXP[Aura.LocalTVDetailsReady]"))
                    self.assertEqual(f.variable("Aura_TVAired"), "")
            for count in ("", "0", "2"):
                f = self.row(kind, **{"Container(9587).NumItems": count})
                self.assertFalse(f.condition("$EXP[Aura.LocalTVDetailsReady]"))
            f = self.row(kind)
            f.updating.add("9587")
            self.assertFalse(f.condition("$EXP[Aura.LocalTVDetailsReady]"))
            f.updating.clear()
            f.labels["ListItem.DBID"] = "999"  # focus/stale native subject
            self.assertEqual(f.variable("Aura_LocalTVDetails"), "")
            self.assertFalse(f.condition("$EXP[Aura.LocalTVDetailsReady]"))
            f.labels["ListItem.DBID"] = "31"
            f.active = False
            self.assertFalse(f.condition("$EXP[Aura.LocalTVDetailsReady]"))

    def test_no_orphaned_progress_variables_or_native_count_predicates(self):
        f = self.row()
        runtime = "".join(p.read_text() for p in (ROOT / "1080i").glob("*.xml"))
        for name in ("Aura_TVTotal", "Aura_TVWatched", "Aura_TVUnwatched"):
            self.assertNotIn(name, runtime)
        for name in ("Aura_TVProgress", "Aura_TVEpisodeState", "Aura_LocalTVDetails"):
            self.assertIn("$VAR[%s]" % name, runtime)
        progress = f.includes.find("variable[@name='Aura_TVProgress']/value")
        self.assertNotIn("Property(", progress.get("condition"))
        for forbidden in ("Integer.", "Container(", "IsUpdating", "SkinInfo."):
            self.assertNotIn(forbidden, ET.tostring(progress, encoding="unicode"))

    def test_only_exact_episode_uses_actual_raw_firstaired_never_premiered(self):
        f = self.row("episode", **{"ListItem.Premiered": "series premiere",
                                   "Container(9587).ListItem.Premiered": "series premiere"})
        self.assertEqual(f.variable("Aura_TVAired"),
                         "$LOCALIZE[31961]: $INFO[Container(9587).ListItem.Property(FirstAired)]")
        f.labels["Container(9587).ListItem.Property(FirstAired)"] = ""
        self.assertEqual(f.variable("Aura_TVAired"), "")
        f = self.row("tvshow", **{"ListItem.Premiered": "localized series date"})
        self.assertEqual(f.variable("Aura_TVAired"), "$LOCALIZE[31961]: $INFO[ListItem.Premiered]")
        self.assertEqual(self.row("season").variable("Aura_TVAired"), "")


class MusicContract(MovieContract):
    """Evaluate authored gates; core enable flags are inputs, not emulated Kodi.

    Kodi 21.3 GUIDialogMusicInfo.cpp: 394-410 selects artist discography only
    for ID > 0; 506-551 binds songs/discography without skin content; 574-586
    sets native button labels. GUIDialogSongInfo.cpp: 162-191 handles album,
    contributor and Play; 234-272 gates album ID and binds role/name in order.
    MusicGUIInfo.cpp: 303-321 supplies OriginalDate/ReleaseDate, not properties.
    """
    def __init__(self, kind="album", **changes):
        super().__init__()
        self.music = ET.parse(ROOT / "1080i/DialogMusicInfo.xml").getroot()
        self.active_window = "songinformation" if kind == "song" else "musicinformation"
        self.core_enabled = {"8", "12"}
        self.labels.update({"ListItem.DBType": kind, "ListItem.DBID": "31",
                            "ListItem.ReleaseDate": "", "ListItem.OriginalDate": "",
                            "Container(50).NumItems": "2"})
        self.labels.update(changes)

    def condition(self, text):
        if text in ("Window.IsVisible(musicinformation)", "Window.IsVisible(songinformation)"):
            return text == "Window.IsVisible(%s)" % self.active_window
        match = re.fullmatch(r"Control.IsEnabled\((8|12)\)", text)
        if match:
            ident = match[1]
            if self.active_window not in ("musicinformation", "songinformation"):
                return ident in self.core_enabled  # other window's native controls
            enable = self.music.find(".//control[@id='%s']/enable" % ident)
            return ident in self.core_enabled and (enable is None or self.condition(enable.text))
        if text == "Control.IsVisible(50)":
            return self.condition("$EXP[Aura.MusicRows]")
        return super().condition(text)

    def item_visible(self, item):
        return all(self.condition(n.text) for n in item.findall("visible"))


class MusicInformationTests(unittest.TestCase):
    def test_one_core_bound_list_and_native_buttons(self):
        music = ET.parse(ROOT / "1080i/DialogMusicInfo.xml").getroot()
        rows = music.findall(".//control[@id='50']")
        self.assertEqual(len(rows), 1, "Both native music dialogs bind control 50")
        self.assertEqual(rows[0].get("type"), "list")
        self.assertIsNone(rows[0].find("content"))
        for ident in ("8", "12"):
            button = music.find(".//control[@id='%s']" % ident)
            self.assertIsNotNone(button)
            self.assertEqual(button.findall("onclick"), [])
            self.assertEqual(button.findtext("include"), "Defs_Hidden_Button")
        self.assertIsNone(music.find(".//control[@id='12']/visible"))

    def test_native_rows_not_replaced_reordered_filtered_or_scripted(self):
        f = MusicContract()
        rows = f.music.find(".//control[@id='50']")
        self.assertEqual(rows.findtext("visible"), "$EXP[Aura.MusicRows]")
        self.assertEqual(rows.findtext("orientation"), "horizontal")
        self.assertEqual(rows.findtext("height"), "100")
        self.assertEqual([n.tag for n in rows], [
            "top", "right", "height", "orientation", "scrolltime", "visible",
            "onup", "ondown", "onback", "itemlayout", "focusedlayout"])
        # No XML content, sort/filter, row onclick, selection proxy or local-ID
        # invention: core indexes the same unmodified contributor/discography rows.
        authored = ET.tostring(rows, encoding="unicode")
        detail = f.includes.find("variable[@name='Aura_MusicRowDetail']")
        authored += ET.tostring(detail, encoding="unicode")
        for forbidden in ("onclick", "onfocus", "onunfocus", "content", "sort",
                          "filter", "RunScript", "PlayMedia", "ActivateWindow",
                          "DBID", "Property(", "Container(50).ListItem", "31956"):
            self.assertNotIn(forbidden, authored)
        for layout_name in ("itemlayout", "focusedlayout"):
            layout = rows.find(layout_name)
            self.assertEqual(layout.attrib, {"width": "420", "height": "96"})
            self.assertEqual([n.findtext("label") for n in layout.findall("control[@type='label']")],
                             ["$INFO[ListItem.Label]", "$VAR[Aura_MusicRowDetail]"])
        self.assertEqual(rows.find("focusedlayout/control[@type='image']/texture").get("colordiffuse"),
                         "$VAR[ColorHighlight]")
        for kind, expected in (("song", "$INFO[ListItem.Artist]$INFO[ListItem.Duration, · ,]"),
                                ("album", "$INFO[ListItem.Year]"),
                                ("artist", "$INFO[ListItem.Label2]")):
            # These are ROW types: song contributor rows are typed artist.
            f.labels["ListItem.DBType"] = kind
            self.assertEqual(f.variable("Aura_MusicRowDetail"), expected)

    def test_context_only_for_actual_rows_and_native_music_types(self):
        for kind, ident in (("artist", 31968), ("album", 31969), ("song", 31970)):
            f = MusicContract(kind)
            self.assertEqual(f.variable("Aura_MusicContext"), "$LOCALIZE[%s]" % ident)
            item = next(n for n in f.items if n.findtext("label") == "$VAR[Aura_MusicContext]")
            self.assertEqual([n.text for n in item.findall("onclick")], ["SetFocus(50)"])
            area = f.music.find(".//control[@description='Native music context']")
            self.assertEqual(area.findtext("visible"), item.findtext("visible"))
            self.assertEqual(area.findtext("height"), "170")
            self.assertTrue(f.item_visible(item))
            for count in ("", "0", "-1", "bad"):
                f.labels["Container(50).NumItems"] = count
                self.assertFalse(f.item_visible(item), (kind, count))
            f.labels["Container(50).NumItems"] = "1"
            # Imported discography remains readable even without local IDs. No
            # availability claim or replacement action is inferred from row presence.
            for dbid in ("", "0", "-1", "27"):
                f.labels["Container(50).ListItem.DBID"] = dbid
                self.assertTrue(f.item_visible(item))
            f.active_window = "movieinformation"
            self.assertFalse(f.item_visible(item))
        for kind in ("movie", "tvshow", "episode", "musicvideo", "actor", "", "set"):
            f = MusicContract(kind)
            self.assertFalse(f.condition("$EXP[Aura.MusicInfo]"), kind)
            self.assertFalse(f.condition("$EXP[Aura.MusicRows]"), kind)

    def test_native_play_is_typed_positive_subject_not_selected_row(self):
        for kind in ("artist", "album", "song", "musicvideo", "movie", ""):
            for dbid in ("", "0", "-1", "bad", "31"):
                f = MusicContract(kind, **{"ListItem.DBID": dbid,
                                         "Container(50).ListItem.DBID": "99",
                                         "Container(50).ListItem.DBType": "album"})
                expected = kind in ("album", "song") and dbid == "31"
                self.assertEqual(f.condition("Control.IsEnabled(8)"), expected, (kind, dbid))
                play = f.items.find("item")
                self.assertEqual(f.item_visible(play), expected, (kind, dbid))
                self.assertEqual([n.text for n in play.findall("onclick")], ["SendClick(8)"])
                f.core_enabled.clear()
                self.assertFalse(f.item_visible(play))
        f = MusicContract()
        f.active_window = "movieinformation"
        self.assertFalse(f.condition("$EXP[Aura.MusicPlayable]"))

    def test_context_12_is_native_navigation_not_fanart_or_kiosk_management(self):
        for kind in ("artist", "album", "song", "musicvideo", "movie", ""):
            f = MusicContract(kind)
            items = [n for n in f.items if n.findtext("onclick") == "SendClick(12)"]
            self.assertEqual(len(items), 2)  # mutually exclusive video art / music navigation
            video, music = items
            self.assertFalse(f.item_visible(video))
            self.assertEqual(music.findtext("label"), "$INFO[Control.GetLabel(12)]")
            self.assertEqual(music.findtext("icon"), "special://skin/extras/icons/infobubble.png")
            for kiosk in (False, True):
                f.settings = {"global.kioskmode"} if kiosk else set()
                self.assertEqual(f.item_visible(music), kind in ("album", "song"), (kind, kiosk))
            # Song core disables 12 for unknown/nonpositive album IDs. The skin
            # must honor that flag, not guess an album from selected contributor.
            f.core_enabled.discard("12")
            f.labels["Container(50).ListItem.DBID"] = "99"
            self.assertFalse(f.item_visible(music))
            self.assertEqual(music.find("onclick").attrib, {})
        f = MusicContract()
        button = f.music.find(".//control[@id='12']")
        self.assertEqual(button.findtext("label"), "21891")  # SongInfo overrides to 10523
        self.assertIsNone(button.find("enable"))  # never override core's album-ID decision
        f.active_window = "movieinformation"
        self.assertTrue(f.item_visible(video))  # video art's original kiosk guard remains
        f.settings.add("global.kioskmode")
        self.assertFalse(f.item_visible(video))

    def test_native_dates_missing_equal_distinct_partial_and_unrelated_types(self):
        for kind in ("artist", "album", "song", "musicvideo", "movie", ""):
            for release, original in (("", ""), ("2020", ""), ("", "1999"),
                                       ("2020", "2020"), ("2020-06", "1999"),
                                       ("28 November 2026", "1 January 2000")):
                f = MusicContract(kind, **{"ListItem.ReleaseDate": release,
                                         "ListItem.OriginalDate": original,
                                         "ListItem.Year": "wrong date",
                                         "ListItem.Property(Album_ReleaseDate)": "wrong date",
                                         "Container(50).ListItem.ReleaseDate": "wrong date"})
                supported = kind in ("album", "song")
                self.assertEqual(f.variable("Aura_MusicReleaseDate"),
                                 "$LOCALIZE[31955]: $INFO[ListItem.ReleaseDate]"
                                 if supported and release else "")
                self.assertEqual(f.variable("Aura_MusicOriginalDate"),
                                 "$LOCALIZE[31971]: $INFO[ListItem.OriginalDate]"
                                 if supported and original and original != release else "")
                f.active_window = "movieinformation"
                self.assertEqual(f.variable("Aura_MusicReleaseDate"), "")
                self.assertEqual(f.variable("Aura_MusicOriginalDate"), "")
        f = MusicContract()
        dates = f.music.find(".//control[@description='Native music dates']")
        self.assertEqual(dates.findtext("height"), "48")
        self.assertEqual(dates.findtext("control/label"),
                         "$VAR[Aura_MusicReleaseDate]$VAR[Aura_MusicOriginalDate,   ,]")
        self.assertEqual(dates.findtext("control/scroll"), "true")
        self.assertFalse(f.condition(dates.findtext("visible")))

    def test_focus_and_existing_layout_and_local_fallback_contracts(self):
        f = MusicContract()
        self.assertEqual(f.music.findtext("defaultcontrol"), "300")
        self.assertEqual(f.music.findtext(".//control[@id='300']/ondown"), "9601")
        rows = f.music.find(".//control[@id='50']")
        self.assertEqual((rows.findtext("onup"), rows.findtext("ondown"), rows.findtext("onback")),
                         ("300", "9503", "300"))
        # Native Left/Right, mouse Select, keyboard Select, context and paging
        # remain unhandled by the skin. No forced close or Play on row selection.
        for event in ("onleft", "onright", "onclick", "oninfo", "oncontextmenu"):
            self.assertIsNone(rows.find(event))
        management = f.music.find(".//control[@id='9503']")
        self.assertEqual([(n.get("condition"), n.text) for n in management.findall("onup")],
                         [("Control.IsVisible(50)", "50"), ("!Control.IsVisible(50)", "300")])
        self.assertEqual(management.findtext("ondown"), "SetFocus(300)")
        hero = f.music.find(".//control[@id='9000']/control")
        self.assertEqual(hero.findtext("height"), "380")
        self.assertEqual(hero.find(".//include[@content='Object_Info']/param[@name='plot_height']").get("value"),
                         "170")
        properties = [n.get("value") for n in f.music.findall(".//param[@name='label2']")]
        self.assertIn("ListItem.Property(Album_Label)", properties)
        for ident in ("6", "7", "10"):
            button = f.music.find(".//control[@id='%s']" % ident)
            self.assertEqual(button.findtext("include"), "Defs_Hidden_Button")
            self.assertEqual(button.findall("onclick"), [])
            self.assertIsNone(button.find("enable"))
        plot = f.includes.find("variable[@name='Label_Plot']")
        plot_text = ET.tostring(plot, encoding="unicode")
        self.assertIn("ListItem.Property(Artist_Description)", plot_text)
        self.assertIn("ListItem.Property(Album_Description)", plot_text)
        self.assertIn("$VAR[Image_Poster]", ET.tostring(hero, encoding="unicode"))
        self.assertIn("$VAR[Image_DiscArt]", ET.tostring(f.music, encoding="unicode"))

    def test_compilations_keep_track_artists_and_native_context_without_name_guessing(self):
        f = MusicContract("album", **{"ListItem.Artist": "Various Artists",
                                     "ListItem.AlbumArtist": "Various Artists"})
        self.assertTrue(f.condition("$EXP[Aura.MusicRows]"))
        self.assertTrue(f.condition("$EXP[Aura.MusicPlayable]"))
        self.assertTrue(f.condition("$EXP[Aura.MusicContextAction]"))
        self.assertEqual(f.variable("Aura_MusicContext"), "$LOCALIZE[31969]")
        # Inside the row layout, the native song's own artist wins; do not
        # substitute albumartist, first album artist, Home properties or a search.
        f.labels.update({"ListItem.DBType": "song", "ListItem.Artist": "Track Artist",
                         "ListItem.AlbumArtist": "Various Artists"})
        self.assertEqual(f.variable("Aura_MusicRowDetail"),
                         "$INFO[ListItem.Artist]$INFO[ListItem.Duration, · ,]")
        context = f.music.find(".//control[@id='12']")
        self.assertEqual(context.findall("onclick"), [])  # first credited album artist is core's decision
        self.assertEqual(f.music.findall("onload"), [])
        self.assertEqual(f.music.findall("onunload"), [])
        controls = [n.get("id") for n in f.music.findall(".//control[@id]")]
        self.assertEqual(len(controls), len(set(controls)))
        self.assertEqual(set(controls), {"300", "9560", "9000", "50", "9503", "9003",
                                         "6", "7", "8", "10", "12", "9001", "9011"})

    def test_new_music_nodes_have_no_provider_lifecycle_or_settings(self):
        f = MusicContract()
        authored = "".join(ET.tostring(n, encoding="unicode") for n in f.includes
                           if n.get("name", "").startswith(("Aura.Music", "Aura_Music")))
        for node in f.music.findall(".//control[@description='Native music dates']") + f.music.findall(
                ".//control[@description='Native music context']"):
            authored += ET.tostring(node, encoding="unicode")
        for forbidden in ("RunScript", "RunPlugin", "plugin://", "http", "SkinInfo.",
                          "Window(Home)", "Skin.HasSetting", "System.Addon", "onload", "onfocus"):
            self.assertNotIn(forbidden, authored)
        # Existing explicit artwork review/download remains gated and unchanged.
        for ident, action in (("9001", "review_artwork"), ("9011", "download_artwork")):
            button = f.music.find(".//control[@id='%s']" % ident)
            self.assertEqual(button.findtext("onclick"),
                             "RunScript(script.skin.info.service,action=%s,dbtype=$INFO[ListItem.DBType],"
                             "dbid=$INFO[ListItem.DBID])" % action)
            self.assertEqual(button.find("onclick").get("condition"),
                             "System.AddonIsEnabled(script.skin.info.service) + Skin.HasSetting(Aura.OnlineEnrichment) + "
                             "Integer.IsGreater(ListItem.DBID,0) + [String.IsEqual(ListItem.DBType,artist) | "
                             "String.IsEqual(ListItem.DBType,album)]")
        english = (ROOT / "language/resource.language.en_gb/strings.po").read_text()
        for ident, text in enumerate(("Discography", "Album tracks", "Song contributors",
                                      "Original release date"), 31968):
            self.assertEqual(english.count('msgctxt "#%s"' % ident), 1)
            self.assertIn('msgctxt "#%s"\nmsgid "%s"\nmsgstr "%s"' % (ident, text, text), english)


if __name__ == "__main__":
    unittest.main()
