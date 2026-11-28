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
        }
        self.labels.update(changes)
        self.visible = {"50"}
        self.updating = set()
        self.settings = set()
        self.enabled = True

    def condition(self, text):
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
                return left.lower() == match[3].lower()
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
            return self.condition("$EXP[Aura.PersonAction]") if match[1] == "9551" else match[1] in self.visible
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
        for ident, wording in ((31950, "Online cast (TMDb)"), (31951, "Online person (TMDb)")):
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
                             "name=$ESCINFO[Container(50).ListItem.Label],"
                             "role=$ESCINFO[Container(50).ListItem.Label2],"
                             "auto_search=false,separator=,focus=50)")

    def test_actual_9550_exact_id_precedes_context_and_ignores_missing_title_ids(self):
        f = DialogContract(**{"Window.Property(Aura.Info.TMDB)": ""}).fallback("456")
        self.assertEqual(len(f.actions()), 1)
        self.assertIn("person_id=$INFO[Container(9550).ListItem.Property(person_id)]", f.actions()[0])
        self.assertIn("name=$ESCINFO[Container(9550).ListItem.Label]", f.actions()[0])
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
            for part in ("name=$ESCINFO[Container(9550).ListItem.Label]",
                         "role=$ESCINFO[Container(9550).ListItem.Label2]", "focus=9550"):
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
                self.assertEqual(row.findtext("visible"), "$EXP[Aura.PersonAction]")
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
                         [("Control.IsVisible(9551)", "9551"), (None, "9501")])
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
            self.assertIn("RunScript(script.skin.info.service,action=dialog_", n.text)
        for action in f.button.findall("onclick")[1:]:
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
        for control in ("50", "9551"):
            self.assertIsNone(f.video.find(".//control[@id='%s']/onfocus" % control))

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

    def test_public_labels_use_unique_english_fallback_and_standard_focus_color(self):
        f = DialogContract()
        labels = f.objects.find("variable[@name='Aura_PersonLabel']")
        self.assertEqual([n.text for n in labels.findall("value")],
                         ["$LOCALIZE[31950]", "$LOCALIZE[31951]"])
        english = (ROOT / "language/resource.language.en_gb/strings.po").read_text()
        for ident, wording in ((31950, "Online cast (TMDb)"), (31951, "Online person (TMDb)")):
            self.assertEqual(english.count('msgctxt "#%s"' % ident), 1)
            self.assertIn('msgctxt "#%s"\nmsgid "%s"\nmsgstr "%s"' % (ident, wording, wording), english)
        self.assertIsNone(f.button.find("focusedcolor"))


if __name__ == "__main__":
    unittest.main()
