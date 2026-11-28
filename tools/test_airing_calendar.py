"""Stage 9A source contracts, not Kodi rendering or native date-semantics proof.

Run: python3 -B -m unittest discover -s tools -p 'test_airing_calendar.py' -v
No Kodi/provider imports, deployment, network access or runtime-manifest override.
"""

import ast
import itertools
from pathlib import Path
import re
import unittest
from urllib.parse import parse_qs, urlsplit
import xml.etree.ElementTree as ET

from check_omega import Checks, po_messages, provider_boundary_checks


ROOT = Path(__file__).resolve().parents[1]
WINDOW = "1080i/Custom_1140_AiringCalendar.xml"
TOPBAR = "1080i/Includes_Topbar.xml"
ENABLED = "System.AddonIsEnabled(script.skin.info.service)"
LIBRARY = "Library.HasContent(tvshows)"
UPDATING = "Container(50).IsUpdating"
ROWS = "Integer.IsGreater(Container(50).NumItems,0)"
DAY = "$INFO[Window.Property(Aura.Calendar.Day)]"


def condition(value, state):
    """Only this calendar's boolean grammar; not a Kodi condition evaluator."""
    if not value:
        return True
    atoms = {ENABLED: state.get("enabled", True), LIBRARY: state.get("library", True),
             UPDATING: state.get("updating", False), ROWS: state.get("rows", False)}
    for name, choices in (("Day", ("week", "today", "tomorrow")),
                          ("Retry", ("alternate",))):
        for choice in choices:
            atoms["String.IsEqual(Window.Property(Aura.Calendar.%s),%s)" % (name, choice)] = state.get(name, "") == choice
    for atom, result in atoms.items():
        value = value.replace(atom, str(result))
    value = value.replace("+", " and ").replace("|", " or ")
    value = value.replace("!", " not ").replace("[", "(").replace("]", ")")
    tree = ast.parse(value.strip(), mode="eval")

    def boolean(node):
        if isinstance(node, ast.Constant) and type(node.value) is bool:
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not boolean(node.operand)
        if isinstance(node, ast.BoolOp):
            results = [boolean(child) for child in node.values]
            return all(results) if isinstance(node.op, ast.And) else any(results)
        raise AssertionError("Unmodelled calendar condition: " + ast.dump(node))

    return boolean(tree.body)


class AiringCalendar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.window = ET.parse(ROOT / WINDOW).getroot()
        cls.topbar = ET.parse(ROOT / TOPBAR).getroot()
        cls.variables = {node.get("name"): node for node in cls.topbar.findall("variable")}

    def control(self, number):
        return self.window.find(".//control[@id='%s']" % number)

    def variable(self, name, state):
        for node in self.variables[name].findall("value"):
            if condition(node.get("condition"), state):
                value = (node.text or "").replace(DAY, state.get("Day", ""))
                return re.sub(r"\$VAR\[([^]]+)\]", lambda m: self.variable(m[1], state), value)
        return ""

    def test_all_selected_date_routes_and_both_canonical_retry_orders(self):
        expected = {"week": {"day": ["0"], "days": ["7"]},
                    "today": {"day": ["0"], "days": ["1"]},
                    "tomorrow": {"day": ["1"], "days": ["1"]}}
        expected.update({str(day): {"weekday": [str(day)], "days": ["1"]} for day in range(7)})
        for day, retry in itertools.product(expected, ("normal", "alternate")):
            with self.subTest(day=day, retry=retry):
                url = self.variable("AiringCalendar_Content", {"Day": day, "Retry": retry})
                split = urlsplit(url)
                self.assertEqual((split.scheme, split.netloc, split.path),
                                 ("plugin", "script.skin.info.service", "/"))
                self.assertEqual(parse_qs(split.query), dict(action=["next_aired"], shows=["library"], **expected[day]))
                prefix = ("shows=library&action=next_aired&" if retry == "alternate"
                          else "action=next_aired&shows=library&")
                self.assertTrue(split.query.startswith(prefix))

    def test_disabled_or_empty_library_never_produces_a_request(self):
        for enabled, library, day, retry in itertools.product((False, True), (False, True),
                                                            ("week", "today", "6"), ("normal", "alternate")):
            state = dict(enabled=enabled, library=library, Day=day, Retry=retry)
            self.assertEqual(bool(self.variable("AiringCalendar_Content", state)), enabled and library)

    def test_retry_one_atomic_action_retains_date_and_alternates_urls(self):
        button = self.control(70)
        self.assertEqual([n.text for n in button.findall("onclick")],
                         ["SetProperty(Aura.Calendar.Retry,$VAR[AiringCalendar_RetryNext])"])
        for day in ("week", "today", "tomorrow", *map(str, range(7))):
            state = {"Day": day}
            initial = self.variable("AiringCalendar_Content", state)
            state["Retry"] = self.variable("AiringCalendar_RetryNext", state)
            alternate = self.variable("AiringCalendar_Content", state)
            self.assertNotEqual(initial, alternate)
            self.assertEqual(parse_qs(urlsplit(initial).query), parse_qs(urlsplit(alternate).query))
            state["Retry"] = self.variable("AiringCalendar_RetryNext", state)
            self.assertEqual(self.variable("AiringCalendar_Content", state), initial)
        text = ET.tostring(self.window, encoding="unicode") + ET.tostring(self.topbar, encoding="unicode")
        calendar_variables = "".join(ET.tostring(n, encoding="unicode") for name, n in self.variables.items() if name.startswith("AiringCalendar_"))
        for forbidden in ("cache=", "reload=", "AlarmClock(", "Container.Refresh", "RunScript(", "RunPlugin("):
            self.assertNotIn(forbidden, ET.tostring(self.window, encoding="unicode") + calendar_variables)
        self.assertNotIn("Skin.ToggleSetting(Aura.Calendar", text)

    def test_tabs_select_only_not_focus_and_preserve_original_identity(self):
        tabs = self.control(9000)
        items = tabs.findall("content/item")
        self.assertEqual([n.findtext("property") for n in items], ["week", "today", "tomorrow", *map(str, range(7))])
        self.assertEqual([n.findtext("label") for n in items],
                         ["$LOCALIZE[31921]", "$LOCALIZE[33006]", "$LOCALIZE[33007]",
                          *["$LOCALIZE[%s]" % n for n in range(11, 18)]])
        self.assertEqual(tabs.findall(".//onfocus"), [])
        for item in items:
            self.assertEqual([n.text for n in item.findall("onclick")],
                             ["SetProperty(Aura.Calendar.Day,%s)" % item.findtext("property")])
        self.assertEqual(self.window.get("id"), "1140")
        self.assertEqual(self.window.findtext("defaultcontrol"), "9000")
        self.assertEqual(self.control(50).find("content").attrib, {"browse": "never"})
        self.assertEqual(self.control(50).findtext("content"), "$VAR[AiringCalendar_Content]")

    def test_selection_native_series_exact_id_return_and_never_playback(self):
        clicks = self.control(50).findall("onclick")
        self.assertEqual(len(clicks), 2)
        self.assertEqual(clicks[0].text, "ActivateWindow(videos,videodb://tvshows/titles/$INFO[Container(50).ListItem.Property(tvshowdbid)]/,return)")
        self.assertEqual(clicks[0].get("condition"), ENABLED + " + !Container(50).IsUpdating + Integer.IsGreater(Container(50).ListItem.Property(tvshowdbid),0)")
        self.assertEqual((clicks[1].text, clicks[1].attrib), ("noop", {}))
        # The ID is provider-owned: 2.0.2 assigns VideoLibrary's numeric tvshowid,
        # not external IDs/names. No independent arbitrary-string parser in XML.
        self.assertEqual(self.window.find("onload").get("condition"), "String.IsEmpty(Window.Property(Aura.Calendar.Day))")
        self.assertEqual(self.window.findall("onunload"), [])
        self.assertNotEqual(self.window.find("defaultcontrol").get("always"), "true")
        text = ET.tostring(self.window, encoding="unicode")
        for forbidden in ("PlayMedia(", "PlayerControl(", "Resume", "RunPlugin(", "RunScript(", "FileNameAndPath])"):
            self.assertNotIn(forbidden, text)
        self.assertNotIn("ListItem.Label]", ET.tostring(self.control(50), encoding="unicode"))

    def test_rows_separate_show_episode_numbers_dates_and_schedule_identity(self):
        for layout in ("itemlayout", "focusedlayout"):
            node = self.control(50).find(layout)
            labels = [n.text for n in node.iter("label")]
            self.assertIn("$INFO[ListItem.TVShowTitle]", labels)
            self.assertIn("$INFO[ListItem.Title]", labels)
            self.assertIn("$LOCALIZE[20373] $INFO[ListItem.Season] • $LOCALIZE[20359] $INFO[ListItem.Episode]", labels)
            self.assertIn("$LOCALIZE[31973] • $INFO[ListItem.Property(airday)]$INFO[ListItem.Property(airdate), • ,]", labels)
            self.assertIn("$INFO[ListItem.Art(thumb)]", [n.text for n in node.iter("texture")])
        text = ET.tostring(self.window, encoding="unicode")
        self.assertIn("$INFO[Container(50).ListItem.Plot]", text)
        self.assertIn("$INFO[Container(50).ListItem.Property(airdatelong)]", text)
        self.assertNotIn("airtime", text.lower())
        self.assertNotIn("Premiered", text)

    def test_status_branch_partition_and_localized_neutral_wording(self):
        statuses = {number: self.window.find(".//control[label='$LOCALIZE[%s]']/visible" % number).text
                    for number in (31975, 31978, 31929, 31972)}
        for enabled, library, updating, rows in itertools.product((False, True), repeat=4):
            state = dict(enabled=enabled, library=library, updating=updating, rows=rows)
            shown = {number for number, predicate in statuses.items() if condition(predicate, state)}
            expected = ({31978} if not enabled else {31972} if not library else
                        {31929} if updating else set() if rows else {31975})
            self.assertEqual(shown, expected, state)
        messages, duplicates = po_messages((ROOT / "language/resource.language.en_gb/strings.po").read_bytes())
        self.assertFalse(duplicates)
        self.assertEqual(messages[31975], "No schedule results, or schedule unavailable.")
        self.assertIn("Skin Info Service", messages[31978])
        self.assertIn("do not indicate playable availability", messages[31976])
        self.assertIn("earlier airings", messages[31977])
        for number in range(31972, 31979):
            self.assertTrue(messages[number])
        for ref in re.findall(r"\$LOCALIZE\[(31\d+)\]", ET.tostring(self.window, encoding="unicode")):
            self.assertTrue(messages[int(ref)])
        # Fresh semantic IDs prevent existing en_us/de_de legacy translations
        # from overriding the neutral fallback with the old provider's wording.
        for locale in ("en_us", "de_de"):
            translated, _ = po_messages((ROOT / ("language/resource.language.%s/strings.po" % locale)).read_bytes())
            self.assertFalse(set(range(31972, 31979)) & translated.keys())

    def test_focus_edges_all_states_and_retry_mouse_target(self):
        for enabled, library, updating, rows in itertools.product((False, True), repeat=4):
            state = dict(enabled=enabled, library=library, updating=updating, rows=rows)
            targets = [n.text for n in self.control(9000).findall("ondown") if condition(n.get("condition"), state)]
            expected = "9000" if not enabled or not library else "50" if rows and not updating else "70"
            self.assertEqual(targets, [expected], state)
            self.assertEqual(condition(self.control(70).findtext("visible"), state), enabled and library)
        ids = {n.get("id") for n in self.window.iter("control") if n.get("id")} | {"300"}
        for node in self.window.iter():
            if node.tag in ("onup", "ondown", "onleft", "onright", "onback", "pagecontrol") and (node.text or "").isdigit():
                self.assertIn(node.text, ids)
        self.assertEqual(self.control(50).findtext("onright"), "60")
        self.assertEqual(self.control(60).findtext("onright"), "70")
        self.assertEqual(self.control(70).get("type"), "button")
        self.assertTrue(self.control(70).findtext("label"))

    def test_authored_provider_boundaries_remain_enabled(self):
        checks = Checks()
        provider_boundary_checks(checks, {WINDOW: self.window, TOPBAR: self.topbar})
        self.assertTrue(all(item["passed"] for item in checks.results), checks.results)

    def test_existing_calendar_settings_buttons(self):
        settings = ET.parse(ROOT / "1080i/SkinSettings.xml").getroot()
        for number in (9616, 9814):
            with self.subTest(control=number):
                buttons = settings.findall(".//control[@id='%s']" % number)
                self.assertEqual(len(buttons), 1)
                button = buttons[0]
                self.assertEqual(button.get("type"), "button")
                for tag, expected in (("enable", ENABLED),
                                      ("label", "$LOCALIZE[31920]"),
                                      ("onclick", "ActivateWindow(1140)")):
                    self.assertEqual([(node.text, node.attrib) for node in button.findall(tag)],
                                     [(expected, {})], tag)

    def test_exact_optional_shortcut_and_no_calendar_home_defaults(self):
        overrides = ET.parse(ROOT / "shortcuts/overrides.xml").getroot()
        group = overrides.find("groupings/node[@label='32029']")
        self.assertIsNotNone(group)
        optional = group.findall("shortcut[@label='$LOCALIZE[31920]']")
        self.assertEqual(len(optional), 1)
        shortcut = optional[0]
        self.assertEqual(shortcut.attrib, {"label": "$LOCALIZE[31920]", "type": "32010",
                                          "icon": "special://skin/extras/icons/tvguide.png"})
        self.assertEqual(shortcut.text, "ActivateWindow(1140)")
        self.assertEqual(list(shortcut), [])
        # Only this chooser entry is opt-in. Check Home and every bundled
        # shortcut/default definition without depending on a Git checkout.
        group.remove(shortcut)
        roots = [("shortcuts/overrides.xml", overrides),
                 ("1080i/Home.xml", ET.parse(ROOT / "1080i/Home.xml").getroot())]
        roots.extend((path.relative_to(ROOT).as_posix(), ET.parse(path).getroot())
                     for path in sorted((ROOT / "shortcuts").glob("*.xml"))
                     if path.name != "overrides.xml")
        calendar_reference = re.compile(
            r"calendar|next[_. -]?aired|(?<!\d)1140(?!\d)|(?<!\d)31920(?!\d)", re.I)
        for path, root in roots:
            with self.subTest(path=path):
                self.assertNotRegex(ET.tostring(root, encoding="unicode"), calendar_reference)

    def test_calendar_provider_specific_settings_action(self):
        items = ET.parse(ROOT / "1080i/Includes_Items.xml").getroot()
        includes = items.findall("include[@name='Items_AiringCalendar']")
        self.assertEqual(len(includes), 1)
        settings = includes[0].findall("content/item[label='$LOCALIZE[10140]']")
        self.assertEqual(len(settings), 1)
        self.assertEqual([(node.text, node.attrib) for node in settings[0].findall("onclick")],
                         [("Addon.OpenSettings(script.skin.info.service)", {"condition": ENABLED})])
        self.assertEqual(settings[0].findtext("visible"), "!Skin.HasSetting(global.kioskmode)")

    def test_modified_old_calendar_strings_locale_parity(self):
        locales = {}
        for locale in ("en_gb", "en_us"):
            data = (ROOT / ("language/resource.language.%s/strings.po" % locale)).read_bytes()
            messages, duplicates = po_messages(data)
            self.assertFalse(duplicates, locale)
            # Validate msgid as well as msgstr using the same singular-PO parser.
            source_messages, source_duplicates = po_messages(
                re.sub(rb'(?m)^(msgid|msgstr)(?=\s)',
                       lambda match: b'msgstr' if match[1] == b'msgid' else b'msgid', data))
            self.assertFalse(source_duplicates, locale)
            locales[locale] = (source_messages, messages)
        # These legacy IDs need locale parity, not the fresh IDs' neutral
        # wording (which is independently checked above).
        for number in (31922, 31926, 31927, 31928):
            for field, gb, us in zip(("msgid", "msgstr"), locales["en_gb"], locales["en_us"]):
                with self.subTest(string=number, field=field):
                    self.assertTrue(gb.get(number))
                    self.assertEqual(us.get(number), gb[number])


if __name__ == "__main__":
    unittest.main()
