"""Stage 7A authored XML contracts, not Kodi rendering or provider execution.

The bounded evaluator fails closed on unknown syntax. It exercises the actual
XML gates/actions with synthetic labels; no Kodi imports, network or settings IO.
"""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def split_top(text, separator):
    depth = 0
    start = 0
    result = []
    for i, char in enumerate(text):
        if depth == 0 and text.startswith(separator, i):
            result.append(text[start:i])
            start = i + len(separator)
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
    return result + [text[start:]]


class DialogContract:
    def __init__(self, **changes):
        self.video = ET.parse(ROOT / "1080i/DialogVideoInfo.xml").getroot()
        self.objects = ET.parse(ROOT / "1080i/Includes_Object.xml").getroot()
        self.expressions = {n.get("name"): n.text for n in self.objects.findall("expression")}
        self.button = self.video.find(".//control[@id='9551']")
        self.labels = {
            "Window.Property(Aura.Info.DBType)": "movie",
            "Window.Property(Aura.Info.DBID)": "31",
            "Window.Property(Aura.Info.TMDB)": "123",
            "Window.Property(Aura.Info.IMDB)": "",
            "Window.Property(Aura.Info.Category)": "",
            "Container(50).NumItems": "6",
            "Container(50).ListItem.Label": 'O’Name, "Jr." \\ / Ω',
            "Container(50).ListItem.Label2": 'Role, "A" \\ / B',
            "Container(9550).NumItems": "0",
            "Container(50).Position": "2",
            "Window(movieinformation).Property(Aura.Info.DBID)": "31",
            "Window(movieinformation).Property(Aura.Info.Cast50.DBID)": "31",
            "Window(movieinformation).Property(Aura.Info.Cast50.Position)": "2",
            "Window(movieinformation).Property(Aura.Info.Cast50.Name)": 'O’Name, "Jr." \\ / Ω',
            "Window(movieinformation).Property(Aura.Info.Cast50.Role)": 'Role, "A" \\ / B',
        }
        self.labels.update(changes)
        self.visible = {"50"}
        self.updating = set()
        self.settings = set()
        self.enabled = True

    def condition(self, text):
        if text in ("true", "false"):
            return text == "true"
        parts = split_top(text, " | ")
        if len(parts) > 1:
            return any(self.condition(p) for p in parts)
        parts = split_top(text, " + ")
        if len(parts) > 1:
            return all(self.condition(p) for p in parts)
        if text.startswith("!"):
            return not self.condition(text[1:])
        if text.startswith("[") and text.endswith("]"):
            return self.condition(text[1:-1])
        match = re.fullmatch(r"\$EXP\[(.+)\]", text)
        if match:
            return self.condition(self.expressions[match[1]])
        match = re.fullmatch(r"(String.IsEqual|String.StartsWith|Integer.IsGreater)\((.*),([^,]*)\)", text)
        if match:
            left = self.labels.get(match[2], "")
            if match[1] == "String.IsEqual":
                return left.lower() == self.labels.get(match[3], match[3]).lower()
            if match[1] == "String.StartsWith":
                return left.lower().startswith(match[3].lower())
            try:
                return int(left) > int(match[3])
            except ValueError:
                return False
        match = re.fullmatch(r"String.IsEmpty\((.*)\)", text)
        if match:
            return not self.labels.get(match[1], "")
        match = re.fullmatch(r"Control.IsVisible\((\d+)\)", text)
        if match:
            action = {"9551": "Aura.PersonAction", "9553": "Aura.DirectorAction", "9554": "Aura.WriterAction"}.get(match[1])
            return self.condition("$EXP[%s]" % action) if action else match[1] in self.visible
        match = re.fullmatch(r"Container\((\d+)\).IsUpdating", text)
        if match:
            return match[1] in self.updating
        match = re.fullmatch(r"Skin.HasSetting\((.+)\)", text)
        if match:
            return match[1] in self.settings
        if text == "System.AddonIsEnabled(script.skin.info.service)":
            return self.enabled
        raise AssertionError("Unsupported fixture condition: " + text)

    def actions(self):
        return [n.text for n in self.button.findall("onclick") if self.condition(n.get("condition"))]

    def fallback(self, person_id="0"):
        self.visible = {"9550"}
        self.labels.update({"Container(50).NumItems": "0", "Container(9550).NumItems": "6",
                            "Container(9550).ListItem.Label": "Selected Person",
                            "Container(9550).ListItem.Label2": "Selected Role",
                            "Container(9550).ListItem.Property(person_id)": person_id})
        return self


class ActorExplorationTests(unittest.TestCase):
    def test_public_labels_use_unique_english_fallback_and_standard_focus_color(self):
        f = DialogContract()
        values = f.objects.find("variable[@name='Aura_PersonLabel']").findall("value")
        self.assertEqual([(n.get("condition"), n.text) for n in values],
                         [("$EXP[Aura.PersonDiscovery]", "$LOCALIZE[31950]"),
                          (None, "$LOCALIZE[31951]")])
        english = (ROOT / "language/resource.language.en_gb/strings.po").read_text()
        for ident, wording in ((31950, "Online cast & crew (TMDb)"), (31951, "Online person (TMDb)")):
            self.assertEqual(english.count('msgctxt "#%s"' % ident), 1)
            self.assertIn('msgctxt "#%s"\nmsgid "%s"\nmsgstr "%s"' %
                          (ident, wording, wording), english)
        self.assertIsNone(f.button.find("focusedcolor"))

    def test_local_movie_tv_episode_use_captured_dbid_and_typed_context(self):
        for kind in ("movie", "tvshow", "episode"):
            f = DialogContract(**{"Window.Property(Aura.Info.DBType)": kind})
            # Focused ListItem deliberately differs from the native dialog subject.
            f.labels.update({"ListItem.DBID": "999", "ListItem.DBType": "actor"})
            actions = f.actions()
            self.assertEqual(len(actions), 1)
            self.assertEqual(actions[0], "RunScript(script.skin.info.service,action=dialog_actor_info,"
                             "dbid=$INFO[Window.Property(Aura.Info.DBID)],"
                             "dbtype=$INFO[Window.Property(Aura.Info.DBType)],"
                             "$ESCINFO[Window(movieinformation).Property(Aura.Info.Cast50.Name),name=],"
                             "$ESCINFO[Window(movieinformation).Property(Aura.Info.Cast50.Role),role=],"
                             "auto_search=false,separator=,focus=50)")

    def test_actual_9550_exact_id_precedes_context_and_ignores_missing_title_ids(self):
        f = DialogContract(**{"Window.Property(Aura.Info.TMDB)": ""}).fallback("456")
        self.assertEqual(len(f.actions()), 1)
        self.assertIn("person_id=$INFO[Container(9550).ListItem.Property(person_id)]", f.actions()[0])
        self.assertIn("$ESCINFO[Container(9550).ListItem.Label,name=]", f.actions()[0])
        self.assertIn("focus=9550", f.actions()[0])
        self.assertNotIn("dbid=", f.actions()[0])
        # An invisible stale fallback card must never override the native selection.
        f.visible = {"50"}
        f.labels["Container(50).NumItems"] = "6"
        self.assertEqual(f.actions(), [])  # no title identifier for native context

    def test_nonpositive_or_missing_fallback_person_id_uses_context(self):
        for pid in ("", "0", "-1", "not-an-id"):
            f = DialogContract().fallback(pid)
            self.assertEqual(len(f.actions()), 1)
            self.assertIn("dbid=$INFO[Window.Property(Aura.Info.DBID)]", f.actions()[0])
            for part in ("$ESCINFO[Container(9550).ListItem.Label,name=]",
                         "$ESCINFO[Container(9550).ListItem.Label2,role=]", "focus=9550"):
                self.assertIn(part, f.actions()[0])
            self.assertNotIn("person_id=", f.actions()[0])

    def test_discovery_is_typed_exact_title_even_without_cast_or_with_local_match(self):
        for kind, marker in (("movie", "Aura Online Discovery"), ("tvshow", "Aura Online Discovery TV")):
            for dbid in ("", "0", "-1", "42"):
                f = DialogContract(**{"Window.Property(Aura.Info.Category)": marker,
                                      "Window.Property(Aura.Info.DBType)": kind,
                                      "Window.Property(Aura.Info.DBID)": dbid})
                f.visible.clear()
                f.labels["Container(50).NumItems"] = "0"
                self.assertEqual(f.actions(), ["RunScript(script.skin.info.service,action=dialog_video_info,"
                                               "dbtype=$INFO[Window.Property(Aura.Info.DBType)],"
                                               "tmdb_id=$INFO[Window.Property(Aura.Info.TMDB)],focus=9551)"])
                f.fallback("456")
                self.assertEqual(len(f.actions()), 1)
                self.assertIn("action=dialog_video_info", f.actions()[0])
                row = f.video.find(".//control[@id='9552']")
                self.assertEqual(row.findtext("visible"), "$EXP[Aura.CreditsAction]")
                self.assertIsNotNone(row.find("control[@id='9551']"))
                self.assertIsNone(f.video.find(".//control[@id='9500']//control[@id='9551']"))

    def test_missing_invalid_discovery_id_hides_without_name_or_imdb_guess(self):
        for tmdb in ("", "0", "-1", "tt123", "bad"):
            f = DialogContract(**{"Window.Property(Aura.Info.Category)": "Aura Online Discovery",
                                  "Window.Property(Aura.Info.TMDB)": tmdb,
                                  "Window.Property(Aura.Info.IMDB)": "tt1234567"}).fallback("456")
            self.assertEqual(f.actions(), [])

    def test_supported_native_identifiers_and_missing_data_return_path(self):
        for kind in ("movie", "tvshow"):
            for tmdb, imdb, expected in (("123", "", True), ("", "tt1234567", True),
                                         ("", "", False), ("-1", "123", False)):
                f = DialogContract(**{"Window.Property(Aura.Info.DBType)": kind,
                                      "Window.Property(Aura.Info.TMDB)": tmdb,
                                      "Window.Property(Aura.Info.IMDB)": imdb})
                self.assertEqual(bool(f.actions()), expected)
        for dbid in ("", "0", "-2", "bad"):
            f = DialogContract(**{"Window.Property(Aura.Info.DBID)": dbid})
            self.assertEqual(f.actions(), [])
        for kind in ("season", "set", "musicvideo", "actor", ""):
            f = DialogContract(**{"Window.Property(Aura.Info.DBType)": kind}).fallback("456")
            self.assertEqual(f.actions(), [])

    def test_episode_uses_actual_episode_dbid_not_any_tmdb_or_show_dbid(self):
        f = DialogContract(**{"Window.Property(Aura.Info.DBType)": "episode",
                              "Window.Property(Aura.Info.TMDB)": "",
                              "Window.Property(Aura.Info.TVShowDBID)": "987"})
        self.assertEqual(len(f.actions()), 1)
        for forbidden in ("tmdb_id=", "TVShowDBID", "ShowTMDB", "season=", "episode="):
            self.assertNotIn(forbidden, f.actions()[0])
        f.labels["Window.Property(Aura.Info.DBID)"] = "0"
        self.assertEqual(f.actions(), [])

    def test_explicit_action_independent_of_enrichment_but_legacy_select_is_opt_in(self):
        f = DialogContract().fallback("456")
        before = f.actions()
        self.assertFalse(f.condition("$EXP[Aura.ActorOnline]"))
        f.settings.add("Aura.OnlineEnrichment")
        self.assertTrue(f.condition("$EXP[Aura.ActorOnline]"))
        self.assertEqual(before, f.actions())
        include = f.objects.find("include[@name='Object_Aura_Actor_OnClick']")
        self.assertEqual(include.findtext("onclick"), "SendClick(9551)")
        self.assertNotIn("script.embuary", ET.tostring(include, encoding="unicode"))
        self.assertEqual([n.text for n in include.findall("onclick")][1:], [
            "Dialog.Close(movieinformation)",
            "ActivateWindow(Videos,videodb://tvshows/actors/,return)",
            "ActivateWindow(Videos,videodb://movies/actors/,return)"])
        legacy = f.video.find(".//control[@id='9958']")
        self.assertEqual([n.text for n in legacy.findall("onclick")], ["SendClick(9551)"])
        self.assertEqual(legacy.findtext("visible"), "$EXP[Aura.ActorOnline]")

    def test_disabled_hidden_empty_and_loading_contexts_have_no_action(self):
        f = DialogContract()
        f.enabled = False
        self.assertEqual(f.actions(), [])
        f.enabled = True
        f.settings.add("VideoInfo.CastList")
        self.assertEqual(f.actions(), [])
        f.settings.clear()
        f.updating.add("50")
        self.assertEqual(f.actions(), [])
        f.fallback("456")
        f.updating.add("9550")
        self.assertEqual(f.actions(), [])
        f.updating.clear()
        f.labels["Container(9550).NumItems"] = "0"
        self.assertEqual(f.actions(), [])

    def test_up_back_and_sis_return_keep_selected_cast_card_not_index_zero(self):
        for native in (True, False, None):
            f = DialogContract()
            f.visible = {"50"} if native is True else {"9550"} if native is False else set()
            for event in ("onup", "onback"):
                self.assertEqual([n.text for n in f.button.findall(event) if f.condition(n.get("condition"))],
                                 ["50" if native is True else "9550" if native is False else "9570"])
        f = DialogContract()
        self.assertEqual(f.video.findtext(".//control[@id='50']/ondown"), "SetFocus($VAR[Aura_PersonDown])")
        values = f.objects.find("variable[@name='Aura_PersonDown']").findall("value")
        self.assertEqual([(n.get("condition"), n.text) for n in values],
                         [("Control.IsVisible(9551)", "9551"), ("Control.IsVisible(9553)", "9553"),
                          ("Control.IsVisible(9554)", "9554"), (None, "9501")])
        for n in f.button:
            self.assertNotIn("SetFocus(50,", n.text or "")
            self.assertNotIn("SetFocus(9550,", n.text or "")

    def test_native_cards_roles_art_and_core_select_are_preserved(self):
        f = DialogContract()
        native = f.video.find(".//control[@id='50']")
        self.assertIsNone(native.find("onclick"))
        self.assertIsNone(native.find("content"))
        self.assertEqual(native.findtext("orientation"), "horizontal")
        self.assertEqual(native.find("include[@content='View_Actor_Layout']/param[@name='artTexture']").get("value"),
                         "$INFO[ListItem.Icon]")
        wrapper = f.video.find(".//include[@content='Object_VideoInfo_CastList']/param[@name='id'][@value='9550']/..")
        self.assertEqual(wrapper.find("param[@name='fallbackimage']").get("value"), "DefaultActor.png")
        layout = ET.parse(ROOT / "1080i/Includes_View.xml").find("include[@name='View_Actor_Layout']")
        for kind in ("itemlayout", "focusedlayout"):
            labels = [n.text for n in layout.findall("definition/" + kind + "//label")]
            self.assertIn("$INFO[ListItem.Label]", labels)
            self.assertIn("$PARAM[label2]", labels)
        select = f.video.find(".//control[@id='9959']")
        self.assertEqual([n.text for n in select.findall("onclick")],
                         ["SetFocus(50)", "Select", "SetFocus(9950)"])

    def test_no_open_focus_requests_no_global_guesses_no_new_provider_ui(self):
        f = DialogContract()
        for n in [*f.video.findall("onload"), *f.video.findall(".//onfocus")]:
            self.assertNotIn("dialog_actor_info", n.text or "")
            self.assertNotIn("dialog_video_info", n.text or "")
        self.assertIsNone(f.button.find("onfocus"))
        for n in f.button.findall("onclick"):
            self.assertNotIn("query=", n.text)
            self.assertNotIn("Skin.Set", n.text)
            self.assertNotIn("name=$INFO", n.text)
            self.assertNotIn("role=$INFO", n.text)
            self.assertNotIn("name=$ESCINFO", n.text)
            self.assertNotIn("role=$ESCINFO", n.text)
            self.assertTrue(n.text == "SetFocus(50)" or
                            n.text.startswith("RunScript(script.skin.info.service,action=dialog_"))
        for action in f.button.findall("onclick")[2:]:
            self.assertIn("auto_search=false,separator=", action.text)
        self.assertEqual(len(f.video.findall(".//control[@id='9551']")), 1)
        self.assertFalse(list((ROOT / "1080i").glob("*skin-info-service*")))

    def test_subject_captures_survive_cast_focus_and_are_cleared_on_exit(self):
        f = DialogContract()
        for field, label in (("DBID", "ListItem.DBID"), ("DBType", "ListItem.DBType"),
                             ("Category", "ListItem.Property(widget)"), ("TMDB", "ListItem.UniqueID(tmdb)")):
            self.assertIn("SetProperty(Aura.Info.%s,$INFO[%s])" % (field, label),
                          [n.text for n in f.video.findall("onload")])
            self.assertIn("ClearProperty(Aura.Info.%s)" % field,
                          [n.text for n in f.video.findall("onunload")])
        self.assertIsNone(f.video.find(".//control[@id='9551']/onfocus"))

    def test_native_selection_captured_on_focus_and_blur_cleared_for_each_title(self):
        f = DialogContract()
        expected = [
            "SetProperty(Aura.Info.Cast50.Name,$ESCINFO[Container(50).ListItem.Label],movieinformation)",
            "SetProperty(Aura.Info.Cast50.Role,$ESCINFO[Container(50).ListItem.Label2],movieinformation)",
            "SetProperty(Aura.Info.Cast50.Position,$INFO[Container(50).Position],movieinformation)",
            "SetProperty(Aura.Info.Cast50.DBID,$INFO[Window(movieinformation).Property(Aura.Info.DBID)],movieinformation)",
        ]
        native = f.video.find(".//control[@id='50']")
        for event in ("onfocus", "onunfocus"):
            self.assertEqual([n.text for n in native.findall(event)], expected)
        for field in ("Name", "Role", "Position", "DBID"):
            for event in ("onload", "onunload"):
                self.assertIn("ClearProperty(Aura.Info.Cast50.%s,movieinformation)" % field,
                              [n.text for n in f.video.findall(event)])
        route = next(n.text for n in f.button.findall("onclick") if "focus=50)" in n.text)
        self.assertNotIn("$ESCINFO[Container(50)", route)

    def test_missing_stale_or_changed_snapshot_returns_cast_without_provider_request(self):
        for key, value in (("Name", ""), ("Name", "Stale Person"), ("Role", "Wrong Role"),
                           ("Position", "1"), ("DBID", "6")):
            f = DialogContract()
            f.labels["Window(movieinformation).Property(Aura.Info.Cast50.%s)" % key] = value
            self.assertEqual(f.actions(), ["SetFocus(50)"], (key, value))
        f = DialogContract()
        # Mouse/keyboard re-enter cast, scroll, then leave: blur snapshots the
        # actual final card, not the card selected on the first focus event.
        f.labels["Container(50).ListItem.Label"] = 'Robert Downey Jr., "RDJ"'
        self.assertEqual(f.actions(), ["SetFocus(50)"])
        f.labels["Window(movieinformation).Property(Aura.Info.Cast50.Name)"] = f.labels["Container(50).ListItem.Label"]
        self.assertEqual(len(f.actions()), 1)
        self.assertIn("action=dialog_actor_info", f.actions()[0])

    def test_play_ratings_artwork_and_original_explicit_tools_stay_native_or_gated(self):
        f = DialogContract()
        for control, description in (("8", "Play"), ("10", "Artwork (Get Thumb)"), ("7", "Userrating")):
            node = f.video.find(".//control[@id='%s']" % control)
            self.assertEqual(node.findtext("description"), description)
            self.assertIsNone(node.find("onclick"))
        for control, action in (("9001", "review_artwork"), ("9011", "download_artwork")):
            node = f.video.find(".//control[@id='%s']" % control)
            self.assertIn("Skin.HasSetting(Aura.OnlineEnrichment)", node.find("onclick").get("condition"))
            self.assertIn("action=" + action, node.findtext("onclick"))
            self.assertIn("Skin.HasSetting(Aura.OnlineEnrichment)", node.findtext("visible"))

    def test_negative_controls_detect_global_search_and_wrong_identity(self):
        f = DialogContract()
        f.expressions["Aura.PersonContext"] = "Integer.IsGreater(Window.Property(Aura.Info.DBID),0)"
        f.labels["Window.Property(Aura.Info.DBType)"] = "season"
        # LibraryType in the outer gate still prevents unsupported titles.
        self.assertEqual(f.actions(), [])
        f.expressions["Aura.PersonLibraryType"] = f.expressions["Aura.PersonContext"]
        self.assertEqual(len(f.actions()), 1)  # bad gate would now leak a season route
        f = DialogContract().fallback("456")
        f.expressions["Aura.PersonExact"] = "Integer.IsGreater(Container(9550).ListItem.Property(person_id),0)"
        f.visible = {"50"}
        f.labels["Container(50).NumItems"] = "6"
        self.assertIn("person_id=", f.actions()[0])  # stale hidden-card identity leak


class CrewActionTests(unittest.TestCase):
    """Stage 7B source contracts; the provider picker is not executed here."""

    def fixture(self, **changes):
        f = DialogContract(**changes)
        f.labels.update({"Window(movieinformation).Property(Aura.Info.Director)": "Native Director",
                         "Window(movieinformation).Property(Aura.Info.Writer)": "Native Writer"})
        return f

    def button(self, f, ident):
        return f.video.find(".//control[@id='%s']" % ident)

    def actions(self, f, ident):
        return [n.text for n in self.button(f, ident).findall("onclick") if f.condition(n.get("condition"))]

    def test_exact_typed_movie_roles_no_name_guess_and_correct_return_origin(self):
        f = self.fixture()
        for ident, role in ((9553, "director"), (9554, "writer")):
            node = self.button(f, ident)
            self.assertTrue(f.condition(node.findtext("visible")))
            self.assertEqual(self.actions(f, ident), [
                "RunScript(script.skin.info.service,action=dialog_actor_info,crew=%s,dbtype=movie,"
                "tmdb_id=$INFO[Window.Property(Aura.Info.TMDB)],auto_search=false,focus=%s)" % (role, ident)])
            for forbidden in ("name=", "query=", "person_id=", "dbid=", "imdb_id=", "ListItem."):
                self.assertNotIn(forbidden, self.actions(f, ident)[0])

    def test_role_specific_empty_credits_hide_only_that_action(self):
        for missing, other in (("Director", 9554), ("Writer", 9553)):
            f = self.fixture()
            f.labels["Window(movieinformation).Property(Aura.Info.%s)" % missing] = ""
            self.assertEqual(self.actions(f, 9553 if missing == "Director" else 9554), [])
            self.assertEqual(len(self.actions(f, other)), 1)
        f.labels["Window(movieinformation).Property(Aura.Info.Director)"] = ""
        self.assertEqual(self.actions(f, 9553), [])
        self.assertEqual(self.actions(f, 9554), [])

    def test_unsupported_types_and_nonpositive_or_missing_identity_never_dispatch(self):
        for kind in ("tvshow", "episode", "season", "set", "musicvideo", "actor", ""):
            f = self.fixture(**{"Window.Property(Aura.Info.DBType)": kind})
            self.assertEqual(self.actions(f, 9553) + self.actions(f, 9554), [])
        for field in ("DBID", "TMDB"):
            for value in ("", "0", "-1", "bad", "tt12345"):
                f = self.fixture(**{"Window.Property(Aura.Info.%s)" % field: value,
                                    "Window.Property(Aura.Info.IMDB)": "tt12345"})
                self.assertEqual(self.actions(f, 9553) + self.actions(f, 9554), [], (field, value))

    def test_discovery_keeps_one_exact_title_view_for_extended_crew(self):
        for marker, kind in (("Aura Online Discovery", "movie"), ("Aura Online Discovery TV", "tvshow")):
            f = self.fixture(**{"Window.Property(Aura.Info.Category)": marker,
                                "Window.Property(Aura.Info.DBType)": kind})
            self.assertEqual(self.actions(f, 9553) + self.actions(f, 9554), [])
            self.assertEqual(len(f.actions()), 1)
            self.assertIn("action=dialog_video_info", f.actions()[0])

    def test_independent_explicit_consent_and_existing_visibility_settings(self):
        f = self.fixture()
        before = [self.actions(f, ident) for ident in (9553, 9554)]
        f.settings.add("Aura.OnlineEnrichment")
        self.assertEqual(before, [self.actions(f, ident) for ident in (9553, 9554)])
        f.enabled = False
        self.assertEqual(self.actions(f, 9553) + self.actions(f, 9554), [])
        f.enabled = True
        f.settings.add("VideoInfo.CastList")
        self.assertEqual(self.actions(f, 9553) + self.actions(f, 9554), [])

    def test_crew_can_be_reached_without_any_native_cast(self):
        f = self.fixture()
        f.visible.clear()
        f.labels["Container(50).NumItems"] = "0"
        self.assertEqual(f.actions(), [])
        self.assertTrue(f.condition("$EXP[Aura.CreditsAction]"))
        self.assertEqual(len(self.actions(f, 9553)), 1)
        top = f.video.find(".//control[@id='300']")
        self.assertEqual([n.text for n in top.findall("ondown") if f.condition(n.get("condition"))],
                         ["SetFocus($VAR[Aura_PersonDown])"])

    def test_credits_snapshotted_before_focus_and_cleared_on_unload(self):
        f = self.fixture()
        for field in ("Director", "Writer"):
            self.assertIn("SetProperty(Aura.Info.%s,$ESCINFO[ListItem.%s],movieinformation)" % (field, field),
                          [n.text for n in f.video.findall("onload")])
            self.assertIn("ClearProperty(Aura.Info.%s,movieinformation)" % field,
                          [n.text for n in f.video.findall("onunload")])
        # Moving to a cast or Similar card cannot replace the captured title or
        # availability gate with that focused item's media identity/credits.
        before = self.actions(f, 9553)
        f.labels.update({"ListItem.DBType": "tvshow", "ListItem.UniqueID(tmdb)": "999",
                         "ListItem.Director": "", "ListItem.Writer": ""})
        self.assertEqual(self.actions(f, 9553), before)
        for n in [*f.video.findall("onload"), *f.video.findall(".//onfocus"), *f.video.findall(".//onunfocus")]:
            self.assertNotIn("crew=", n.text or "")
        for ident in (9553, 9554):
            self.assertIsNone(self.button(f, ident).find("onfocus"))

    def test_horizontal_navigation_skips_every_combination_of_hidden_actions(self):
        ids = (9551, 9553, 9554)
        for bits in range(8):
            f = self.fixture()
            visible = {ident for i, ident in enumerate(ids) if bits & (1 << i)}
            for ident, action in zip(ids, ("Aura.PersonAction", "Aura.DirectorAction", "Aura.WriterAction")):
                f.expressions[action] = "true" if ident in visible else "false"
            values = f.objects.find("variable[@name='Aura_PersonDown']").findall("value")
            entry = next(n.text for n in values if n.get("condition") is None or f.condition(n.get("condition")))
            self.assertEqual(entry, str(min(visible)) if visible else "9501")
            self.assertEqual(f.condition("$EXP[Aura.CreditsAction]"), bool(visible))
            for ident in visible:
                for direction in ("onleft", "onright"):
                    dest = [n.text for n in self.button(f, ident).findall(direction) if f.condition(n.get("condition"))]
                    self.assertEqual(len(dest), 1)
                    self.assertIn(int(dest[0]), visible)
                    if len(visible) > 1:
                        self.assertNotEqual(dest[0], str(ident))

    def test_up_back_preserve_cast_selection_and_no_cast_returns_to_top(self):
        for cast in ({"50"}, {"9550"}, set()):
            f = self.fixture()
            f.visible = cast
            for ident in (9553, 9554):
                for event in ("onup", "onback"):
                    self.assertEqual([n.text for n in self.button(f, ident).findall(event)
                                      if f.condition(n.get("condition"))],
                                     ["50" if "50" in cast else "9550" if "9550" in cast else "9570"])

    def test_localized_compact_controls_use_existing_row_and_unique_ids(self):
        f = self.fixture()
        row = f.video.find(".//control[@id='9552']")
        self.assertEqual(row.findtext("height"), "60")
        english = (ROOT / "language/resource.language.en_gb/strings.po").read_text()
        ids = [n.get("id") for n in f.video.findall(".//control") if n.get("id")]
        self.assertEqual(len(ids), len(set(ids)))
        for ident, loc, wording in ((9553, 31952, "Online directors (TMDb)"),
                                    (9554, 31953, "Online writers (TMDb)")):
            button = row.find("control[@id='%s']" % ident)
            self.assertEqual(button.findtext("label"), "$LOCALIZE[%s]" % loc)
            self.assertEqual(button.findtext("height"), "40")
            self.assertEqual(button.findtext("width"), "360")
            self.assertIsNone(button.find("focusedcolor"))
            self.assertEqual(english.count('msgctxt "#%s"' % loc), 1)
            self.assertIn('msgctxt "#%s"\nmsgid "%s"\nmsgstr "%s"' % (loc, wording, wording), english)


if __name__ == "__main__":
    unittest.main()
