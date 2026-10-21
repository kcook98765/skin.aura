"""Run with python3 -B -m unittest discover -s tools -p 'test_omega.py' -v."""

import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import stat
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET
import zipfile

from build_omega import build, new_output
from check_omega import Checks, DEFAULT_TYPES, ENGLISH_LOCALES, INFO_BLUR_WINDOWS, LEGACY_DEPENDENCIES, OFFICIAL_MINIMUMS, ROOT, SEEK_COUNTS, STYLE_INCLUDES, check_source, main as check_main, online_toggle_errors, po_messages, provider_boundary_checks, python_expressions, source_providers
from check_official_dependencies import CORE, compare_versions, dependency_closure, main as closure_main
from omega_common import BASELINE_VERSION, DIRECTORIES, FOCUSED_DELTA, GENERATED, OPTIONAL_DOCS, ROOT_FILES, RUNTIME_MANIFEST, RUNTIME_REVIEW_ADDITIONS, VERSION, Source, payload_path, runtime_path


class MemorySource:
    """Isolated byte mutations: never write a runtime skin file."""

    def __init__(self, data, original, baseline=False, changes=(), root=ROOT):
        self.data = data
        self.files = sorted(data)
        self.original_data = original
        self.original_files = set(original)
        self.baseline = baseline
        self.changes = list(changes)
        self.root = Path(root)

    def read(self, name):
        return self.data[name]

    def original(self, name):
        return self.original_data[name]

    def deltas(self):
        return copy.deepcopy(self.changes)

    def provenance(self):
        return {"starting_commit": "203aba5117f185a34fef773134d3cf955cbf2c7a",
                "head": "fixture", "branch": "fixture", "runtime_git_diff": self.deltas(),
                "runtime_manifest": {"kind": "in-memory-test-fixture", "file_count": len(self.files),
                                     "sha256": hashlib.sha256(("\n".join(self.files) + "\n").encode()).hexdigest()},
                "source": "baseline" if self.baseline else "worktree"}


class StaticRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = Source(ROOT)
        cls.data = {name: source.read(name) for name in source.files
                     if Path(name).suffix.lower() in (".xml", ".xsp") or name in ENGLISH_LOCALES
                     or name in RUNTIME_REVIEW_ADDITIONS}
        cls.original = {name: source.original(name) for name in source.original_files
                         if Path(name).suffix.lower() in (".xml", ".xsp") or name in ENGLISH_LOCALES}

    def report(self, mutate=None, changes=(), index_bytes=None):
        data = dict(self.data)
        if mutate:
            mutate(data)
        return check_source(MemorySource(data, self.original, changes=changes), index_bytes)

    def edit(self, data, name, xpath, attribute=None, value=None, remove=False):
        self.assertTrue(name in data, "Migration prerequisite missing: " + name)
        tree = ET.fromstring(data[name])
        matches = tree.findall(xpath)
        self.assertEqual(len(matches), 1, (name, xpath))
        node = matches[0]
        if remove:
            parents = {child: parent for parent in tree.iter() for child in parent}
            parents[node].remove(node)
        elif attribute:
            node.set(attribute, value)
        else:
            node.text = value
        data[name] = ET.tostring(tree, encoding="utf-8")

    def assertFails(self, report, name):
        failed = {item["check"] for item in report["checks"] if not item["passed"]}
        self.assertIn(name, failed, failed)

    def assertPasses(self, report, name):
        result = next(item for item in report["checks"] if item["check"] == name)
        self.assertTrue(result["passed"], result)

    def test_current_source_and_counts(self):
        report = self.report()
        self.assertEqual(report["failures"], 0, [n for n in report["checks"] if not n["passed"]])
        self.assertEqual(report["counts"]["xml"], sum(Path(n).suffix.lower() == ".xml" for n in self.data))
        self.assertEqual(report["counts"]["xsp"], sum(Path(n).suffix.lower() == ".xsp" for n in self.original))
        self.assertEqual(report["seek_by_file"], SEEK_COUNTS)
        self.assertTrue(any("no full Kodi include expansion" in w for w in report["warnings"]))
        self.assertTrue(any("closure NOT CHECKED" in w for w in report["warnings"]))

    def test_baseline_failures_are_real(self):
        report = check_source(Source(ROOT, baseline=True))
        self.assertEqual(report["counts"], {"xml": 128, "xsp": 19, "python_expressions": 32, "seek_expressions": 0})
        for check in ("removed:DisplayAfterSeek", "dependency:xbmc.gui", "dependency:no-cherrypy",
                      "settings:general-slider13", "picker:panel6", "favourites:media-window",
                      "video-manager:list50", "select:secondary8-in-include", "seek:total7", "favourites:heading1"):
            self.assertFails(report, check)
        self.assertGreater(report["failures"], 0)

    def test_manifest_identity_and_dependency_regressions(self):
        for dependency in OFFICIAL_MINIMUMS:
            with self.subTest(dependency=dependency):
                report = self.report(lambda data: self.edit(data, "addon.xml",
                    "./requires/import[@addon='%s']" % dependency, "version", "0.0.1"))
                self.assertFails(report, "dependency:" + dependency)
        for dependency in LEGACY_DEPENDENCIES:
            def legacy(data):
                tree = ET.fromstring(data["addon.xml"])
                ET.SubElement(tree.find("requires"), "import", {"addon": dependency, "version": "2.0.3", "optional": "true"})
                data["addon.xml"] = ET.tostring(tree)
            with self.subTest(removed=dependency):
                self.assertFails(self.report(legacy), "dependency:removed:" + dependency)
        for key in ("id", "name", "provider-name", "version"):
            with self.subTest(identity=key):
                def mutate(data):
                    tree = ET.fromstring(data["addon.xml"])
                    tree.set(key, "changed")
                    data["addon.xml"] = ET.tostring(tree)
                self.assertFails(self.report(mutate), "manifest:identity")
        def stale(data):
            tree = ET.fromstring(data["addon.xml"])
            ET.SubElement(tree.find("requires"), "import", {"addon": "script.module.cherrypy", "version": "12.0.2"})
            data["addon.xml"] = ET.tostring(tree)
        self.assertFails(self.report(stale), "dependency:no-cherrypy")
        report = self.report(lambda data: self.edit(data, "addon.xml",
            "./requires/import[@addon='script.skin.info.service']", "version", "2.0.1"))
        self.assertNotIn("dependency:script.skin.info.service", {
            item["check"] for item in report["checks"] if not item["passed"]})

    def test_removed_token_and_all_runtime_formats_parse(self):
        self.assertFails(self.report(lambda data: data.update({"1080i/DialogSeekBar.xml":
            data["1080i/DialogSeekBar.xml"].replace(b"<controls>", b"<visible>Player.DisplayAfterSeek</visible><controls>", 1)})),
            "removed:DisplayAfterSeek")
        for name in ("1080i/Home.xml", "extras/playlists/RandomMovies.xsp"):
            with self.subTest(name=name):
                self.assertFails(self.report(lambda data: data.update({name: b"<broken>"})), "parse:" + name)

    def test_seek_intervals_missing_and_misplaced_conditions(self):
        for interval in ("0", "-1", "4", "", "3.0"):
            with self.subTest(interval=interval):
                report = self.report(lambda data: data.update({"1080i/DialogSeekBar.xml":
                    data["1080i/DialogSeekBar.xml"].replace(b"Player.HasPerformedSeek(3)",
                        ("Player.HasPerformedSeek(%s)" % interval).encode(), 1)}))
                self.assertFails(report, "seek:no-invalid-interval")
                self.assertFails(report, "seek:total7")
                self.assertFails(report, "seek:count:1080i/DialogSeekBar.xml")
        def move(data):
            data["1080i/DialogSeekBar.xml"] = data["1080i/DialogSeekBar.xml"].replace(
                b"Player.HasPerformedSeek(3)", b"Player.Seeking", 1)
            data["1080i/Includes_OSD.xml"] = data["1080i/Includes_OSD.xml"].replace(
                b"Player.HasPerformedSeek(3)", b"Player.HasPerformedSeek(3) | Player.HasPerformedSeek(3)", 1)
        moved = self.report(move)
        self.assertEqual(moved["counts"]["seek_expressions"], 7)
        self.assertFails(moved, "seek:count:1080i/DialogSeekBar.xml")
        self.assertFails(moved, "seek:count:1080i/Includes_OSD.xml")
        def extra_invalid(data):
            data["1080i/DialogSeekBar.xml"] = data["1080i/DialogSeekBar.xml"].replace(
                b"Player.HasPerformedSeek(3)", b"Player.HasPerformedSeek(3) | Player.HasPerformedSeek(0)", 1)
        self.assertFails(self.report(extra_invalid), "seek:no-invalid-interval")

    def test_settings_templates(self):
        for name in ("SettingsCategory", "DialogSettings", "DialogAddonSettings"):
            with self.subTest(name=name):
                report = self.report(lambda data: self.edit(data, "1080i/" + name + ".xml",
                    ".//control[@id='15']", "type", "button"))
                self.assertFails(report, "settings:colorbutton15:" + name)
        self.assertFails(self.report(lambda data: self.edit(data, "1080i/SettingsCategory.xml",
            ".//control[@id='13']", "type", "slider")), "settings:general-slider13")

    def test_settings_missing_or_conditional_style(self):
        for name in ("SettingsCategory", "DialogSettings", "DialogAddonSettings"):
            for remove in (True, False):
                with self.subTest(name=name, removed=remove):
                    report = self.report(lambda data: self.edit(data, "1080i/" + name + ".xml",
                        ".//control[@id='15']/include", "condition", "false", remove=remove))
                    self.assertFails(report, "settings:style15:" + name)
        self.assertFails(self.report(lambda data: self.edit(data, "1080i/SettingsCategory.xml",
            ".//control[@id='13']/include", remove=True)), "settings:general-slider13-style")

    def test_known_style_gating_and_appearance_changes(self):
        for style, path in STYLE_INCLUDES.items():
            for tag in ("enable", "visible"):
                with self.subTest(style=style, gate=tag):
                    def gate(data):
                        tree = ET.fromstring(data[path])
                        ET.SubElement(tree.find("./include[@name='%s']" % style), tag).text = "false"
                        data[path] = ET.tostring(tree)
                    self.assertFails(self.report(gate), "style-include:baseline:" + style)
        self.assertFails(self.report(lambda data: self.edit(data, "1080i/Includes_Dialog.xml",
            "./include[@name='Dialog_Standard_Right_Buttons']/font", value="invisible_font")),
            "style-include:baseline:Dialog_Standard_Right_Buttons")

    def test_default_styling_and_native_color_swatch(self):
        for kind in (*DEFAULT_TYPES, "colorbutton"):
            with self.subTest(default=kind):
                def gate(data):
                    tree = ET.fromstring(data["1080i/Defaults.xml"])
                    default = tree.find("./default[@type='%s']" % kind)
                    if default is None:
                        default = ET.SubElement(tree, "default", {"type": kind})
                    ET.SubElement(default, "enable").text = "false"
                    data["1080i/Defaults.xml"] = ET.tostring(tree)
                expected = "settings:colorbutton-default" if kind == "colorbutton" else "default-style:baseline:" + kind
                self.assertFails(self.report(gate), expected)
        self.assertFails(self.report(lambda data: self.edit(data, "1080i/Defaults.xml",
            "./default[@type='colorbutton']/colorwidth", value="0")), "settings:colorbutton-default")

    def test_native_picker_contract(self):
        for xpath, attribute, value, expected in (
            (".//control[@id='1']", "type", "button", "picker:header1"),
            (".//control[@id='6']", "type", "list", "picker:panel6"),
            ("defaultcontrol", None, "7", "picker:defaultfocus6"),
            (".//control[@id='7']/label", None, "186", "picker:cancel7"),
            (".//itemlayout//colordiffuse", None, "$INFO[ListItem.Label]", "picker:palette:itemlayout"),
            (".//focusedlayout//colordiffuse", None, "FFFFFFFF", "picker:palette:focusedlayout"),
        ):
            with self.subTest(check=expected):
                self.assertFails(self.report(lambda data: self.edit(data, "1080i/DialogColorPicker.xml",
                    xpath, attribute, value)), expected)
        def script(data):
            data["1080i/DialogColorPicker.xml"] = data["1080i/DialogColorPicker.xml"].replace(
                b"</controls>", b"<onclick>RunScript(ignored)</onclick></controls>")
        self.assertFails(self.report(script), "picker:no-runscript")

    def test_favourites_preserve_entire_original_panel(self):
        for xpath, attribute, value in (
            (".//control[@id='450']/top", None, "91"),
            (".//control[@id='450']/itemlayout", "width", "301"),
            (".//control[@id='450']/focusedlayout", "height", "391"),
        ):
            with self.subTest(xpath=xpath):
                self.assertFails(self.report(lambda data: self.edit(data, "1080i/MyFavourites.xml",
                    xpath, attribute, value)), "favourites:original-panel-appearance")
        for xpath, value, check in (("defaultcontrol", "50", "favourites:defaultfocus450"),
                                   ("views", "50", "favourites:views450")):
            with self.subTest(check=check):
                self.assertFails(self.report(lambda data: self.edit(data, "1080i/MyFavourites.xml",
                    xpath, value=value)), check)

    def test_favourites_heading_missing_or_wrong_type(self):
        for remove in (True, False):
            with self.subTest(removed=remove):
                self.assertFails(self.report(lambda data: self.edit(data, "1080i/MyFavourites.xml",
                    ".//control[@id='1']", "type", "button", remove=remove)), "favourites:heading1")

    def test_each_skinshortcuts_launch_override(self):
        for function in ("ActivateWindow", "activatewindow"):
            for window in ("Favourites", "favourites"):
                action = "%s(%s)" % (function, window)
                for attribute, value in (("version", "20"), (None, "ActivateWindow(Favourites)")):
                    with self.subTest(action=action, attribute=attribute):
                        xpath = "./override[@action='%s']%s" % (action, "/action" if attribute is None else "")
                        self.assertFails(self.report(lambda data: self.edit(data, "shortcuts/overrides.xml",
                            xpath, attribute, value)), "favourites:override:" + action)

    def test_video_manager_ids_types_and_visibility(self):
        for number, kind, expected in ((50, "panel", "list50"), (2, "button", "header2"),
                                      *((number, "label", "button%d" % number) for number in range(21, 29))):
            with self.subTest(number=number):
                self.assertFails(self.report(lambda data: self.edit(data, "1080i/DialogVideoManager.xml",
                    ".//control[@id='%d']" % number, "type", kind)), "video-manager:" + expected)
        for number in (22, 23, 24, 25, 28):
            with self.subTest(visibility=number):
                self.assertFails(self.report(lambda data: self.edit(data, "1080i/DialogVideoManager.xml",
                    ".//control[@id='%d']/visible" % number, value="false")), "video-manager:visibility%d" % number)
        def hide_group(data):
            tree = ET.fromstring(data["1080i/DialogVideoManager.xml"])
            ET.SubElement(tree.find(".//control[@id='9000']"), "visible").text = "false"
            data["1080i/DialogVideoManager.xml"] = ET.tostring(tree)
        self.assertFails(self.report(hide_group), "video-manager:visibility21")

    def test_secondary_action_and_preserved_content(self):
        self.assertFails(self.report(lambda data: self.edit(data, "1080i/Includes_Dialog.xml",
            "./include[@name='Dialog_Select_Standard']//control[@id='8']", remove=True)), "select:secondary8-in-include")
        for name in ("1080i/MyMusicNav.xml", "shortcuts/template.xml", "1080i/Font.xml",
                     "colors/defaults.xml", "media/Textures.xbt", "fonts/Roboto-Regular.ttf"):
            with self.subTest(protected=name):
                self.assertFails(self.report(changes=[{"status": "M", "path": name}]), "preservation:baseline-runtime")

    def test_python_ast_only_and_broken_expressions(self):
        value = "$PYTHON[[']', [1, 2]][0]]suffix$PYTHON['''x]y''']"
        expressions = list(python_expressions(value))
        self.assertEqual(expressions, ["[']', [1, 2]][0]", "'''x]y'''"])
        for expression in expressions:
            ast.parse(expression, mode="eval")
        with self.assertRaisesRegex(ValueError, "Unterminated"):
            list(python_expressions("$PYTHON[[1, 2]"))
        for expression in ("not defined +", "__import__('not_a_real_kodi_module').must_not_execute()"):
            def mutate(data):
                tree = ET.fromstring(data["shortcuts/template.xml"])
                next(node for node in tree.iter() if "$PYTHON[" in node.get("value", "")).set(
                    "value", "$PYTHON[" + expression + "]")
                data["shortcuts/template.xml"] = ET.tostring(tree)
            report = self.report(mutate)
            errors = [item for item in report["checks"] if item["check"].startswith("python:") and not item["passed"]]
            self.assertEqual(bool(errors), expression == "not defined +")

    def test_cli_exit_codes_and_external_report(self):
        with tempfile.TemporaryDirectory(prefix="omega-report-", dir="/tmp") as temporary:
            path = Path(temporary) / "report.json"
            with mock.patch("check_omega.Source", return_value=MemorySource(self.data, self.original)), mock.patch("builtins.print"):
                self.assertEqual(check_main(["--report", str(path)]), 0)
                self.assertEqual(json.loads(path.read_text())["exit_code"], 0)
                self.assertEqual(check_main(["--report", str(path)]), 2)
                broken = dict(self.data)
                broken["addon.xml"] = b"<broken>"
                with mock.patch("check_omega.Source", return_value=MemorySource(broken, self.original)):
                    self.assertEqual(check_main([]), 1)
                self.assertEqual(check_main(["--report", str(ROOT / "tools/not-allowed.json")]), 2)

    def test_required_inventory_and_parse_every_addition(self):
        self.assertFails(self.report(lambda data: data.pop("1080i/Includes_PVR_Omega.xml", None)), "inventory:required-runtime")
        self.assertFails(self.report(lambda data: data.pop("extras/playlists/RandomMovies.xsp")), "inventory:required-runtime")
        self.assertFails(self.report(lambda data: data.update({"1080i/Additional.xml": b"<broken>"})), "parse:1080i/Additional.xml")
        self.assertFails(self.report(lambda data: data.update({"1080i/Includes_NextAired.xml": b"<includes/>"})), "inventory:removed-runtime")

    def test_native_palette_settings_and_exact_palette(self):
        baseline = self.report()
        for number, key in ((9401, "focuscolor.name"), (9402, "gradientcolor.name"), (9403, "overlaycolor.name")):
            self.assertPasses(baseline, "colors:native-palette-only:" + key)
            for bad in ("Skin.SetString(%s,FF000000)" % key,
                        "Skin.SetColor(%s,1)" % key,
                        "Skin.SetColor(%s,1,FF000000,special://skin/extras/colors/colors.xml)" % key,
                        "Skin.SetColor(%s,1,special://skin/extras/colors/colors.xml,$INFO[Skin.String(%s)])" % (key, key)):
                def mutate(data):
                    root = ET.fromstring(data["1080i/SkinSettings.xml"])
                    row = root.find(".//control[@id='%d']" % number)
                    for click in row.findall("onclick"):
                        row.remove(click)
                    ET.SubElement(row, "onclick").text = bad
                    data["1080i/SkinSettings.xml"] = ET.tostring(root)
                with self.subTest(key=key, action=bad):
                    self.assertFails(self.report(mutate), "colors:native-palette-only:" + key)
            def current_setting(data):
                root = ET.fromstring(data["1080i/SkinSettings.xml"])
                row = root.find(".//control[@id='%d']" % number)
                click = next(n for n in row.findall("onclick") if (n.text or "").startswith("Skin.SetColor("))
                click.text = "Skin.SetColor(%s,1,$INFO[Skin.String(%s)],special://skin/extras/colors/colors.xml)" % (key, key)
                data["1080i/SkinSettings.xml"] = ET.tostring(root)
            self.assertPasses(self.report(current_setting), "colors:native-palette-only:" + key)
        self.assertFails(self.report(lambda data: self.edit(data, "extras/colors/colors.xml", "color[@name='ff0385b5']", value="FF0284B2")), "colors:original-palette")
        self.assertFails(self.report(lambda data: data.update({"1080i/script-skin_helper_service-ColorPicker.xml": b"<window/>"})), "colors:no-custom-picker")

    def test_active_legacy_and_innocuous_saved_keys(self):
        def inject(value):
            def mutate(data):
                root = ET.fromstring(data["1080i/Home.xml"])
                ET.SubElement(root, "onload").text = value
                data["1080i/Home.xml"] = ET.tostring(root)
            return mutate
        for value in ("RunScript(script.skin.helper.service)", "plugin://script.skin.helper.widgets/",
                      "$INFO[Window(Home).Property(SkinHelper.ListItem.Rating)]",
                      "$INFO[Window(Home).Property(SkinHelper.EnableAnimatedPosters)]",
                      "Skin.SetNumeric(SkinHelper.AutoCloseVideoOSD)"):
            with self.subTest(value=value):
                self.assertFails(self.report(inject(value)), "migration:no-active-legacy-helper")
        # Check these keys in an isolated Home window so unrelated WIP legacy
        # consumers do not turn this negative test into a false positive.
        def harmless(data):
            data["1080i/Home.xml"] = b'<window><onload>Skin.ToggleSetting(SkinHelper.EnableAnimatedPosters)</onload><onload>Skin.ToggleSetting(SkinHelper.EnableExtraFanart)</onload><!-- RunScript(script.skin.helper.service) --></window>'
        report = self.report(harmless)
        self.assertNotIn("1080i/Home.xml", next(n["detail"] for n in report["checks"] if n["check"] == "migration:no-active-legacy-helper"))

    def test_enrichment_gates_and_backup_mode(self):
        self.assertFails(self.report(lambda data: self.edit(data, "1080i/Includes_Labels.xml", "expression[@name='Aura.ItemOnline']", value="true")), "enrichment:opt-in-expression:Aura.ItemOnline")
        self.assertFails(self.report(lambda data: data.update({"1080i/Includes_Images.xml": data["1080i/Includes_Images.xml"].replace(b"Skin.HasSetting(Aura.OnlineEnrichment)", b"true")})), "enrichment:online-consumers-gated")
        self.assertFails(self.report(lambda data: data.update({"1080i/Includes_Images.xml": data["1080i/Includes_Images.xml"].replace(b"Skin.HasSetting(Aura.OnlineEnrichment)", b"!Skin.HasSetting(Aura.OnlineEnrichment)")})), "enrichment:online-consumers-gated")
        self.assertFails(self.report(lambda data: data.update({"1080i/Startup.xml": data["1080i/Startup.xml"].replace(b"<controls>", b"<onload>Skin.SetBool(TMDbHelper.Service)</onload><controls>", 1)})), "enrichment:online-flags-opt-in")
        for mode in ("backup", "restore"):
            self.assertFails(self.report(lambda data: data.update({"1080i/SkinSettings.xml": data["1080i/SkinSettings.xml"].replace(("mode=" + mode).encode(), ("action=" + mode).encode())})), "backup:mode:" + mode)
        self.assertFails(self.report(lambda data: data.update({"1080i/Startup.xml": data["1080i/Startup.xml"].replace(b"<controls>", b"<onload>Skin.ResetAll()</onload><controls>", 1)})), "startup:no-reset-all")

    def test_calendar_contract_negative_perturbations(self):
        path = "1080i/Custom_1140_AiringCalendar.xml"
        self.assertPasses(self.report(), "calendar:provider-route")
        for xpath, attribute, value, check in (
            (".", "id", "1141", "window1140"),
            ("defaultcontrol", None, "50", "default9000"),
            (".//item/property[.='0']", None, "7", "week-and-weekday-routes"),
            (".//item/label[.='$LOCALIZE[11]']", None, "Monday", "localized-weekdays"),
            (".//control[@id='50']/content", None, "plugin://script.embuary.info/nextaired/today", "provider-route"),
            (".//control[@id='50']/onclick[1]", None, "PlayMedia($INFO[ListItem.FileNameAndPath])", "non-playable-info"),
            (".//control[label='$LOCALIZE[31929]']/visible", None, "false", "loading-state"),
            (".//control[@id='50']/onright", None, "99999", "focus-targets"),
        ):
            with self.subTest(check=check):
                self.assertFails(self.report(lambda data: self.edit(data, path, xpath, attribute, value)), "calendar:" + check)
        self.assertFails(self.report(lambda data: data.update({path: data[path].replace(b"!Integer.IsGreater(Container(50).NumItems,0)", b"false")})), "calendar:empty-state")

    def test_calendar_disabled_guard_variable_prefix_and_noop(self):
        path = "1080i/Custom_1140_AiringCalendar.xml"
        for xpath, attribute, value, remove, check in (
            (".//control[@id='50']/onclick[1]", "condition", "System.AddonIsEnabled(script.embuary.info)", False, "non-playable-info"),
            (".//control[@id='50']/onclick[2]", None, None, True, "non-playable-info"),
            (".//control[@id='50']/onclick[1]", "condition", "System.AddonIsEnabled(script.embuary.info) + String.StartsWith(Container(50).ListItem.FileNameAndPath,plugin://script.embuary.info)", False, "non-playable-info"),
            (".//control[label='$LOCALIZE[31929]']/visible", None, "Container(50).IsUpdating", False, "loading-state"),
            (".//control[label='$LOCALIZE[31928]']/visible", None, "false", False, "disabled-state"),
        ):
            with self.subTest(check=check, xpath=xpath):
                self.assertFails(self.report(lambda data: self.edit(data, path, xpath, attribute, value, remove)), "calendar:" + check)
        for xpath, attribute, value, remove in (
            ("variable[@name='AiringCalendar_Content']", None, None, True),
            ("variable[@name='AiringCalendar_Content']/value[1]", "condition", "System.HasAddon(script.embuary.info)", False),
            ("variable[@name='AiringCalendar_Content']/value[2]", None, "plugin://script.embuary.info/nextaired/week", False),
        ):
            with self.subTest(variable=xpath):
                self.assertFails(self.report(lambda data: self.edit(data, "1080i/Includes_Topbar.xml", xpath, attribute, value, remove)), "calendar:content-enabled-gate")

    def test_enrichment_old_state_transition_and_toggle_order(self):
        row = ET.fromstring(self.data["1080i/SkinSettings.xml"]).find(".//control[@id='9513']")
        self.assertEqual(online_toggle_errors(row), [])
        # Enable conditions must be negative before the final toggle. Requiring
        # positive conditions would leave providers on while the opt-in turns off.
        wrong = copy.deepcopy(row)
        wrong.findall("onclick")[0].set("condition", "Skin.HasSetting(Aura.OnlineEnrichment)")
        self.assertTrue(online_toggle_errors(wrong))
        first_toggle = copy.deepcopy(row)
        click = first_toggle.findall("onclick")[-1]
        first_toggle.remove(click)
        first_toggle.insert(0, click)
        self.assertTrue(online_toggle_errors(first_toggle))
        self.assertFails(self.report(lambda data: self.edit(data, "1080i/SkinSettings.xml",
            ".//control[@id='9513']/onclick[1]", "condition", "Skin.HasSetting(Aura.OnlineEnrichment)")), "enrichment:online-toggle-transition")

    def test_blur_native_source_and_async_identity(self):
        baseline = self.report()
        for name in ("native-source7978", "unblurred-source", "unblurred-frame-probe7975", "current-frame-only", "official-source-contract", "result-identity-guard"):
            self.assertPasses(baseline, "blur:" + name)
        for wrong in ("$INFO[Window(Home).Property(Aura.PrivateBlurSource)]", "$VAR[Global_Background_Image_Var]"):
            self.assertFails(self.report(lambda data: self.edit(data, "1080i/Includes_Object.xml",
                ".//control[@id='7978']/label", value=wrong)), "blur:native-source7978")
        self.assertFails(self.report(lambda data: data.update({"1080i/Includes_Global.xml": data["1080i/Includes_Global.xml"].replace(
            b"String.IsEqual(Window(Home).Property(SkinInfo.Aura.BlurredImage.Original),Control.GetLabel(7978))", b"true")})), "blur:result-identity-guard")
        for action in ("SetProperty(SkinInfo.BlurSourceVar,Global_Background_Image_Var,Home)",
                       "SetProperty(SkinInfo.BlurSourceVar,Global_Background_Image,Home)"):
            self.assertFails(self.report(lambda data: self.edit(data, "1080i/Includes.xml",
                "include[@name='Aura_Services_OnLoad']/onload[.='SetProperty(SkinInfo.BlurSourceVar,Aura_BlurImage,Home)']", value=action)), "blur:official-source-contract")
        self.assertFails(self.report(lambda data: self.edit(data, "1080i/Includes.xml",
            "include[@name='Aura_Services_OnLoad']/onload[.='SetProperty(SkinInfo.BlurPrefix,Aura,Home)']",
            value="SetProperty(SkinInfo.BlurPrefix,Wrong,Home)")), "blur:official-source-contract")

    def test_blur_frame_feedback_and_stale_folder_guards(self):
        path = "1080i/Includes_Global.xml"
        for xpath, value, check in (
            (".//control[@id='7975']/imagepath", "$VAR[Global_Background_Image]", "blur:unblurred-frame-probe7975"),
            ("variable[@name='Aura_BlurImage']/value[last()]", "$VAR[Global_Background_Image_Var]", "blur:current-frame-only"),
            ("variable[@name='Global_Background_Image_Var']/value[1]", "$INFO[Control.GetLabel(7975)]", "blur:unblurred-source"),
        ):
            with self.subTest(check=check):
                self.assertFails(self.report(lambda data: self.edit(data, path, xpath, value=value)), check)
        self.assertFails(self.report(lambda data: self.edit(data, path,
            "variable[@name='Aura_BlurImage']/value[last()]", "condition", "!String.IsEmpty(Control.GetLabel(7975))")), "blur:current-frame-only")
        self.assertFails(self.report(lambda data: data.update({path: data[path].replace(
            b"String.IsEqual(Window(Home).Property(SkinInfo.Aura.BlurredImage.Original),Control.GetLabel(7978))",
            b"String.IsEqual(Window(Home).Property(SkinInfo.Aura.BlurredImage.Original),Control.GetLabel(7975))")})), "blur:result-identity-guard")
        self.assertPasses(self.report(), "background:extra-fanart-current-eligibility")
        self.assertFails(self.report(lambda data: self.edit(data, path,
            "variable[@name='Global_Background_Image_Var']/value[.='$VAR[Aura_ExtraFanartFolder]']", "condition",
            "Integer.IsGreater(Container(7979).NumItems,0) + !Container(7979).IsUpdating")), "background:extra-fanart-current-eligibility")
        self.assertFails(self.report(lambda data: self.edit(data, path,
            "expression[@name='Aura.ExtraFanartEligible']", value="Skin.HasSetting(SkinHelper.EnableExtraFanart)")), "background:extra-fanart-current-eligibility")

    def test_info_dialog_entry_snapshots_are_qualified_and_cleared(self):
        baseline = self.report()
        for name in ("qualified-dialog-priority", "dialog-native-single-image", "dialog-capture-template", "base-shared-identity"):
            self.assertPasses(baseline, "blur:" + name)
        for name, window in INFO_BLUR_WINDOWS:
            path = "1080i/" + name + ".xml"
            self.assertPasses(baseline, "blur:dialog-capture:" + name)
            self.assertPasses(baseline, "blur:dialog-shared-identity:" + name)
            self.assertFails(self.report(lambda data: self.edit(data, path,
                "include[@content='Object_Aura_InfoBlur_OnLoad']", remove=True)), "blur:dialog-capture:" + name)
            self.assertFails(self.report(lambda data: self.edit(data, path,
                "include[@content='Object_Aura_InfoBlur_OnLoad']/param[@name='window']", "value", "Home")), "blur:dialog-capture:" + name)
            self.assertFails(self.report(lambda data: self.edit(data, path,
                "controls/include[.='Object_Aura_BlurSource']", remove=True)), "blur:dialog-shared-identity:" + name)
        for xpath, value, remove in (
            ("include[@name='Object_Aura_InfoBlur_OnLoad']/definition/onload", "SetProperty(Aura.Blur.InfoImage,$VAR[Global_Background_Image],$PARAM[window])", False),
            ("include[@name='Object_Aura_InfoBlur_OnLoad']/definition/onload", "SetProperty(Aura.Blur.InfoImage,$ESCVAR[Aura_InfoBlurNative])", False),
            ("include[@name='Object_Aura_InfoBlur_OnLoad']/definition/onunload", None, True),
        ):
            self.assertFails(self.report(lambda data: self.edit(data, "1080i/Includes_Object.xml", xpath, value=value, remove=remove)), "blur:dialog-capture-template")

    def test_info_dialog_blur_has_no_directory_or_feedback_fallback(self):
        path = "1080i/Includes_Global.xml"
        self.assertFails(self.report(lambda data: self.edit(data, path,
            "variable[@name='Aura_BlurImage']/value[1]", value="$INFO[Window.Property(Aura.Blur.InfoImage)]")), "blur:qualified-dialog-priority")
        self.assertFails(self.report(lambda data: self.edit(data, path,
            "variable[@name='Aura_BlurImage']/value[2]", remove=True)), "blur:qualified-dialog-priority")
        for wrong in ("$VAR[Global_Background_Image_NoFanart]", "$INFO[Window(Home).Property(SkinInfo.Aura.BlurredImage)]"):
            self.assertFails(self.report(lambda data: self.edit(data, path,
                "variable[@name='Aura_InfoBlurNative']/value[last()]", value=wrong)), "blur:dialog-native-single-image")
        self.assertFails(self.report(lambda data: self.edit(data, path,
            "variable[@name='Aura_BlurImage']/value[1]", "condition",
            "Window.IsVisible(DialogAddonInfo.xml) + !String.IsEmpty(Window(addoninformation).Property(Aura.Blur.InfoImage))")), "blur:qualified-dialog-priority")

    def test_addon_info_preserves_everything_except_blur_hooks(self):
        path = "1080i/DialogAddonInfo.xml"
        self.assertIn(path, FOCUSED_DELTA)
        self.assertPasses(self.report(), "preservation:addon-info-blur-additions-only")
        for xpath, value in (("defaultcontrol", "9000"), (".//control[@id='300']/top", "99"),
                             ("onload", "SetFocus(9000)")):
            self.assertFails(self.report(lambda data: self.edit(data, path, xpath, value=value)), "preservation:addon-info-blur-additions-only")

    def test_ratings_only_two_reviewed_labels_may_change(self):
        path = "1080i/Custom_1118_EnableRatings.xml"
        self.assertIn(path, FOCUSED_DELTA)
        self.assertPasses(self.report(), "preservation:ratings-dialog-two-labels-only")
        for xpath, value in ((".//control[@id='9003']/label", "Rotten Tomatoes"),
                             (".//control[@id='9005']/label", "TVDB"),
                             (".//control[@id='9001']/label", "Other awards"),
                             (".//control[@id='9000']/width", "900")):
            with self.subTest(xpath=xpath):
                self.assertFails(self.report(lambda data: self.edit(data, path, xpath, value=value)),
                                 "preservation:ratings-dialog-two-labels-only")

    def test_english_migration_ids_missing_empty_and_duplicate(self):
        baseline = self.report()
        self.assertIn(31920, baseline["localization"]["referenced_migration_ids"])
        for path in ENGLISH_LOCALES:
            self.assertPasses(baseline, "locale:migration-references:" + path)
            self.assertPasses(baseline, "locale:unique-ids:" + path)
            def missing(data):
                data[path], count = re.subn(rb'msgctxt "#31920"\r?\nmsgid [^\r\n]*\r?\nmsgstr [^\r\n]*\r?\n', b"", data[path], count=1)
                self.assertEqual(count, 1)
            report = self.report(missing)
            self.assertFails(report, "locale:migration-references:" + path)
            self.assertIn(31920, report["localization"]["english"][path]["missing_or_empty"])
            self.assertFails(self.report(lambda data: data.update({path: data[path] + b'\nmsgctxt "#31920"\nmsgid "Duplicate"\nmsgstr "Duplicate"\n'})),
                             "locale:unique-ids:" + path)
            def empty(data):
                data[path], count = re.subn(rb'(msgctxt "#31920"\r?\nmsgid [^\r\n]*\r?\n)msgstr [^\r\n]*', rb'\1msgstr ""', data[path], count=1)
                self.assertEqual(count, 1)
            self.assertFails(self.report(empty), "locale:migration-references:" + path)

    def test_actor_native_browser_fallback_and_online_quotes(self):
        baseline = self.report()
        for name in ("online-quoted-query", "offline-literal-native-browsers", "no-async-lock-or-confirmation-panel", "fallback9550-wired",
                     "native-cast50-core-selection", "container50-online-quoted-query", "manual-browser-help"):
            self.assertPasses(baseline, "actor:" + name)
        path = "1080i/Includes_Object.xml"
        for old, new, check in (
            (b"query=$ESCINFO[ListItem.Label,", b"query=$INFO[ListItem.Label,", "online-quoted-query"),
            (b"videodb://movies/actors/", b"videodb://movies/actors/$INFO[ListItem.Label]/", "offline-literal-native-browsers"),
            (b"videodb://tvshows/actors/", b"plugin://script.embuary.helper/?info=getitemsbyactor", "offline-literal-native-browsers"),
            (b"Dialog.Close(movieinformation)", b"noop", "offline-literal-native-browsers"),
        ):
            def mutate(data):
                self.assertIn(old, data[path])
                data[path] = data[path].replace(old, new)
            with self.subTest(check=check):
                self.assertFails(self.report(mutate), "actor:" + check)
        self.assertFails(self.report(lambda data: self.edit(data, path,
            "include[@name='Object_Aura_Actor_OnClick']/onclick[4]", "condition", "!$EXP[Aura.ActorOnline]")), "actor:offline-literal-native-browsers")
        video = "1080i/DialogVideoInfo.xml"
        self.assertFails(self.report(lambda data: data.update({video: data[video].replace(
            b"query=$ESCINFO[Container(50).ListItem.Label,", b"query=$INFO[Container(50).ListItem.Label,")})), "actor:container50-online-quoted-query")
        self.assertFails(self.report(lambda data: self.edit(data, video, ".//control[@id='50']/orientation", value="vertical")), "actor:native-cast50-core-selection")
        self.assertFails(self.report(lambda data: self.edit(data, video,
            ".//include[@content='Object_VideoInfo_CastList']/param[@name='actoronclick'][@value='true']", remove=True)), "actor:fallback9550-wired")

    def test_removed_actor_lock_and_overlay_cannot_return(self):
        path = "1080i/Includes_Object.xml"
        for payload in (b'<include name="Object_Aura_Actor_Workflow"><control type="group" id="7981"/></include>',
                        b'<include name="Fixture"><onclick>SetProperty(Aura.Actor.Encoding,true,Home)</onclick></include>'):
            self.assertFails(self.report(lambda data: data.update({path: data[path].replace(b"</includes>", payload + b"</includes>")})),
                             "actor:no-async-lock-or-confirmation-panel")

    def test_reviewed_official_provider_enabled_boundaries(self):
        baseline = self.report()
        self.assertPasses(baseline, "providers:reviewed-enabled-boundaries")
        self.assertPasses(baseline, "providers:library-routes-enabled")
        for path, addon in (("1080i/Includes_Global.xml", "script.skin.info.service"),
                            ("1080i/Includes_Labels.xml", "script.skin.info.service"),
                            ("1080i/Includes_Object.xml", "script.embuary.info")):
            def mutate(data):
                token = ("System.AddonIsEnabled(%s)" % addon).encode()
                self.assertIn(token, data[path])
                data[path] = data[path].replace(token, ("System.HasAddon(%s)" % addon).encode())
            self.assertFails(self.report(mutate), "providers:reviewed-enabled-boundaries")
        self.assertFails(self.report(lambda data: self.edit(data, "1080i/Includes_Labels.xml",
            "variable[@name='Aura_InfoCast']/value[1]", "condition", "Integer.IsEqual(Container(50).NumItems,0)")), "providers:library-routes-enabled")

    def test_unchanged_api_dependency_floors_use_original_minima(self):
        original = ET.fromstring(self.original["addon.xml"])
        for addon in ("script.globalsearch", "script.image.resource.select", "resource.images.studios.white"):
            floor = original.find("./requires/import[@addon='%s']" % addon).get("version")
            self.assertEqual(OFFICIAL_MINIMUMS[addon], floor)
            self.assertPasses(self.report(), "dependency:" + addon)

    def test_pvr_native_types_grid_and_event_binding(self):
        path = "1080i/Includes_PVR_Omega.xml"
        self.assertTrue(path in self.data, "Pending migration prerequisite: final PVR include name")
        for xpath, attribute, value, check in (
            (".//control[@id='28']", "type", "label", "core-group28:MyPVRGuide"),
            (".//control[@id='50'][@type='epggrid']", "type", "list", "view50:MyPVRGuide"),
            (".//control[@id='50'][@type='epggrid']/height", None, "592", "grid800"),
            (".//control[@id='9311']/onclick[.='Action(Info)']", None, "ActivateWindow(PVRGuideInfo)", "native-Info:MyPVRGuide"),
            (".//control[@id='60']", "type", "button", "scrollbar60:MyPVRGuide"),
        ):
            with self.subTest(check=check):
                self.assertFails(self.report(lambda data: self.edit(data, path, xpath, attribute, value)), "pvr:" + check)
        self.assertFails(self.report(lambda data: data.update({path: data[path].replace(b"$INFO[ListItem.Plot]", b"$INFO[Container(50).ListItem.Plot]")})), "pvr:summary-native-event")
        self.assertFails(self.report(lambda data: self.edit(data, "1080i/DialogPVRInfo.xml", ".//control[@id='7']", "type", "label")), "pvr:dialog-native-buttons")
        self.assertFails(self.report(lambda data: self.edit(data, "1080i/Includes.xml", "include[@file='Includes_PVR_Omega.xml']", remove=True)), "pvr:include-registered")

    def test_delegated_provider_editor_api_regressions(self):
        for path, old, new, check in (
            ("1080i/script-skinshortcuts.xml", b"$ESCINFO[Skin.String(Aura.Shortcuts.Input)]", b"$INFO[Skin.String(Aura.Shortcuts.Input)]", "editor:deferred-escaped-commit:9410"),
            ("1080i/Includes_Labels.xml", b"dbtype=tvshow&amp;dbid=$INFO[Window.Property(Aura.Info.TVShowDBID)]", b"dbtype=tvshow&amp;dbid=$INFO[Window.Property(Aura.Info.DBID)]", "api:similar-parent-show"),
            ("1080i/Includes_Labels.xml", b"&amp;online=true&amp;", b"&amp;online=false&amp;", "api:cast-online-explicit"),
            ("1080i/Includes_Labels.xml", b"tmdb_id=$INFO[Window.Property(Aura.Info.ShowTMDB)]", b"tmdb_id=$INFO[Window.Property(Aura.Info.TMDB)]", "api:cast-parent-external-id"),
            ("1080i/Includes_Object.xml", b"info=jumptoletter&amp;showall=true", b"info=alphabet", "api:embuary-alphabet"),
            ("shortcuts/overrides.xml", b"SkinInfo.Library.Refreshed", b"Wrong.Refresh", "widgets:official-similar-movie"),
            ("shortcuts/template.xml", b"<template>", b"<template changed='yes'>", "preservation:widget-template"),
        ):
            def mutate(data):
                self.assertIn(old, data[path])
                data[path] = data[path].replace(old, new)
            with self.subTest(check=check):
                self.assertPasses(self.report(), check)
                self.assertFails(self.report(mutate), check)

    def test_native_widget_default_negative_perturbation(self):
        self.assertPasses(self.report(), "preservation:native-defaults:widgetdefaultnode")
        self.assertFails(self.report(lambda data: self.edit(data, "shortcuts/overrides.xml",
            "widgetdefaultnode[@labelID='20342']", "path", "videodb://movies/titles/")),
            "preservation:native-defaults:widgetdefaultnode")

    def test_native_animated_posters_preference_preserved(self):
        self.assertPasses(self.report(), "preservation:animated-posters-toggle9501")
        self.assertFails(self.report(lambda data: self.edit(data, "1080i/SkinSettings.xml", ".//control[@id='9501']", remove=True)),
                         "preservation:animated-posters-toggle9501")

    def test_online_info_include_parameter_gate(self):
        self.assertPasses(self.report(), "enrichment:online-consumers-gated")
        def remove_gate(data):
            tree = ET.fromstring(data["1080i/DialogVideoInfo.xml"])
            parent = next(n for n in tree.iter("include") if any("SkinInfo.Online.Awards" in p.get("value", "") for p in n.findall("param")))
            parent.remove(parent.find("param[@name='visible']"))
            data["1080i/DialogVideoInfo.xml"] = ET.tostring(tree)
        self.assertFails(self.report(remove_gate), "enrichment:online-consumers-gated")
        self.assertFails(self.report(lambda data: self.edit(data, "1080i/Includes_Object.xml",
            "include[@name='Object_VideoInfo_InfoSection']/definition/control/visible[.='$PARAM[visible]']", remove=True)),
            "enrichment:info-section-visible-param")


class EnglishCatalogRegressions(unittest.TestCase):
    def test_multiline_unicode_comments_and_duplicate_contexts(self):
        data = '''# Comment
msgid ""
msgstr ""
"Language: en_GB\\n"

msgctxt "#31920"
msgid "Calendar"
msgstr "Airing "
"calendar 雷"

msgctxt "#31921"
msgid "Week"
msgstr "Seven days"
'''.encode()
        messages, duplicates = po_messages(data)
        self.assertEqual(messages, {31920: "Airing calendar 雷", 31921: "Seven days"})
        self.assertEqual(duplicates, [])
        _, duplicates = po_messages(data + b'\nmsgctxt "#31920"\nmsgid "Other"\nmsgstr "Other"\n')
        self.assertEqual(duplicates, [31920])

    def test_invalid_or_unsupported_catalog_syntax_is_not_ignored(self):
        for data in (b'msgctxt "#31920"\nmsgstr "No msgid"\n',
                     b'msgctxt "#31920"\nmsgid "Broken"\nmsgstr "unterminated\n',
                     b'msgctxt "#31920"\nmsgid "Entry"\nmsgstr[0] "Plural"\n'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                po_messages(data)


class ProviderReferenceRegressions(unittest.TestCase):
    def references(self, text, name="1080i/Fixture.xml"):
        return source_providers({name: ET.fromstring(text)})

    def test_style_path_comparisons_are_benign(self):
        active, compatibility = self.references('''<includes>
            <expression name="Style">String.StartsWith(ListItem.Path,plugin://plugin.program.advanced.launcher)</expression>
            <default type="label"><visible>String.StartsWith(Container.FolderPath,plugin://plugin.program.advanced.MAME.launcher)</visible></default>
            <variable name="Style2"><value condition="String.StartsWith(ListItem.Path,plugin://plugin.program.advanced.emulator.launcher)">flags/image.png</value></variable>
        </includes>''')
        self.assertEqual(active, [])
        self.assertEqual(compatibility, [])

    def test_real_content_texture_actions_and_dependency_functions_survive(self):
        active, _ = self.references('''<includes>
            <content>plugin://script.missing.content/path</content>
            <variable name="Route"><value>plugin://script.missing.variable/path</value></variable>
            <texture>resource://resource.images.missing/icon.png</texture>
            <onclick>RunScript(script.missing.action)</onclick>
            <onload>AlarmClock(test,RunPlugin(plugin://script.missing.nested/path),00:01)</onload>
            <include content="Example"><param name="onclick" value="RunScript(script.missing.parameter)"/></include>
            <visible>System.AddonIsEnabled(script.missing.enabled)</visible>
            <label>$ADDON[script.missing.localization 32000]</label>
        </includes>''')
        self.assertEqual({n["addon"] for n in active}, {
            "script.missing.content", "script.missing.variable", "resource.images.missing", "script.missing.action",
            "script.missing.nested", "script.missing.parameter", "script.missing.enabled", "script.missing.localization"})

    def test_compatibility_localization_is_diagnostic_but_action_still_active(self):
        active, compatibility = self.references('''<window><label>$ADDON[service.nextup.notification 30008]</label>
            <onclick>RunScript(script.missing.action)</onclick></window>''', "1080i/script-nextup-notification-NextUpInfo.xml")
        self.assertEqual([n["addon"] for n in compatibility], ["service.nextup.notification"])
        self.assertEqual([n["addon"] for n in active], ["script.missing.action"])

    def test_missing_runscript_fails_independently_of_required_manifest(self):
        source = Source(ROOT)
        original = {name: source.original(name) for name in source.original_files if Path(name).suffix.lower() in (".xml", ".xsp")}
        data = {"addon.xml": b'<addon id="skin.aura"/>',
                "1080i/Home.xml": b'<window><onclick>RunScript(script.missing.action)</onclick></window>'}
        report = check_source(MemorySource(data, original), b"<addons/>")
        result = {n["check"]: n for n in report["checks"]}
        self.assertTrue(result["dependency:official-recursive-closure"]["passed"])
        self.assertFalse(result["dependency:active-providers-official"]["passed"])
        self.assertIn("script.missing.action", result["dependency:active-providers-official"]["detail"])


class EnabledProviderBoundaryRegressions(unittest.TestCase):
    def report(self, entries):
        checks = Checks()
        provider_boundary_checks(checks, {name: ET.fromstring(text) for name, text in entries.items()})
        return {record["check"]: record for record in checks.results}

    def test_all_windows_and_shortcuts_are_scanned(self):
        for name, text in (
            ("1080i/DialogMusicInfo.xml", '<window><control><visible>System.HasAddon(script.skin.info.service)</visible><onclick>RunScript(script.skin.info.service,action=review_artwork)</onclick></control></window>'),
            ("1080i/UnrelatedWindow.xml", '<window><onclick>RunPlugin(plugin://script.embuary.info/nextaired/week)</onclick></window>'),
            ("shortcuts/overrides.xml", '<overrides><node condition="System.HasAddon(script.skin.info.service)"><shortcut>plugin://script.skin.info.service/?action=next_up</shortcut></node></overrides>'),
        ):
            with self.subTest(name=name):
                result = self.report({name: text})
                self.assertFalse(result["providers:all-authored-invocations-enabled"]["passed"])
                self.assertIn(name, result["providers:all-authored-invocations-enabled"]["detail"])

    def test_matching_missing_provider_install_remains_valid(self):
        result = self.report({"1080i/Settings.xml": '''<window>
            <onclick condition="!System.HasAddon(script.embuary.info)">InstallAddon(script.embuary.info)</onclick>
            <onclick condition="System.AddonIsEnabled(script.embuary.info)">Addon.OpenSettings(script.embuary.info)</onclick>
        </window>'''})
        self.assertTrue(all(record["passed"] for record in result.values()))
        result = self.report({"1080i/Settings.xml": '''<window>
            <onclick condition="System.HasAddon(script.embuary.info)">RunScript(script.embuary.info)</onclick>
        </window>'''})
        self.assertFalse(result["providers:reviewed-enabled-boundaries"]["passed"])

    def test_alphabet_gate_requires_every_known_include_callsite(self):
        definition = '<includes><include name="Object_AlphabetStrip"><control><content>plugin://script.embuary.helper/?info=jumptoletter</content></control></include></includes>'
        caller = '<includes><include condition="System.AddonIsEnabled(script.embuary.helper)">Object_AlphabetStrip</include></includes>'
        result = self.report({"1080i/Includes_Object.xml": definition, "1080i/Includes_Topbar.xml": caller})
        self.assertTrue(all(record["passed"] for record in result.values()))
        for wrong in ("System.HasAddon(script.embuary.helper)", "!System.AddonIsEnabled(script.embuary.helper)", "true"):
            result = self.report({"1080i/Includes_Object.xml": definition, "1080i/Includes_Topbar.xml": caller.replace("System.AddonIsEnabled(script.embuary.helper)", wrong)})
            self.assertFalse(result["providers:all-authored-invocations-enabled"]["passed"])
        result = self.report({"1080i/Includes_Object.xml": definition, "1080i/Includes_Topbar.xml": caller,
                              "1080i/Other.xml": '<window><include>Object_AlphabetStrip</include></window>'})
        self.assertFalse(result["providers:all-authored-invocations-enabled"]["passed"])


class OfficialClosureRegressions(unittest.TestCase):
    def closure(self, imports, providers):
        manifest = ET.fromstring('<addon id="skin.aura"><requires>' + imports + '</requires></addon>')
        return dependency_closure(manifest, ('<addons>' + providers + '</addons>').encode())

    def test_transitive_unavailable_and_optional_recorded(self):
        report = self.closure('<import addon="script.test" version="1.0.0"/>',
            '<addon id="script.test" version="2.0.0"><requires><import addon="script.missing" version="3.0.0"/>'
            '<import addon="script.optional" version="1.0.0" optional="true"/></requires></addon>')
        self.assertEqual(report["failures"], [{"parent": "script.test", "addon": "script.missing", "minimum": "3.0.0", "reason": "required provider missing"}])
        self.assertEqual(report["optional_edges"][0]["addon"], "script.optional")
        self.assertEqual(report["optional_edges"][0]["status"], "unavailable")
        self.assertEqual(report["unavailable_optional_edges"], report["optional_edges"])

    def test_available_optional_branches_are_recursively_audited(self):
        report = self.closure('<import addon="script.root" version="1.0.0"/>', '''
            <addon id="script.root" version="1.0.0"><requires><import addon="script.optional" version="1.0.0" optional="true"/></requires></addon>
            <addon id="script.optional" version="1.0.0"><requires><import addon="script.transitive" version="2.0.0"/></requires></addon>
            <addon id="script.transitive" version="2.0.0"><requires><import addon="script.unavailable" version="1.0.0"/></requires></addon>''')
        self.assertEqual(report["failures"], [])
        self.assertTrue(report["required_closure_complete"])
        self.assertFalse(report["published_optional_closure_complete"])
        self.assertEqual(report["optional_edges"][0]["status"], "audited")
        self.assertEqual(report["optional_failures"][0]["parent"], "script.transitive")
        self.assertEqual(report["optional_failures"][0]["addon"], "script.unavailable")
        self.assertIn("script.transitive", report["providers"])

    def test_optional_visit_does_not_suppress_later_required_failure(self):
        report = self.closure('<import addon="script.a" version="1.0.0" optional="true"/><import addon="script.a" version="1.0.0"/>',
            '<addon id="script.a" version="1.0.0"><requires><import addon="script.missing" version="1.0.0"/></requires></addon>')
        self.assertEqual(report["failures"][0]["addon"], "script.missing")
        self.assertEqual(report["optional_failures"][0]["addon"], "script.missing")

    def test_published_optional_version_and_broken_failures_are_explicit(self):
        for provider, status in (
            ('<addon id="script.optional" version="1.0.0"/>', "unsatisfied"),
            ('<addon id="script.optional" version="2.0.0"><extension point="xbmc.addon.metadata"><broken>Broken</broken></extension></addon>', "broken"),
        ):
            report = self.closure('<import addon="script.optional" version="2.0.0" optional="true"/>', provider)
            self.assertEqual(report["failures"], [])
            self.assertTrue(report["optional_failures"])
            self.assertEqual(report["optional_edges"][0]["status"], status)

    def test_old_color_minimum_is_unsatisfied_not_lowered(self):
        report = self.closure('<import addon="script.skin.helper.colorpicker" version="2.0.3"/>',
            '<addon id="script.skin.helper.colorpicker" version="2.0.1"/>')
        self.assertEqual(report["failures"][0]["reason"], "required version/ABI unsatisfied")
        self.assertEqual(report["failures"][0]["minimum"], "2.0.3")

    def test_marked_broken_required_provider_is_failure(self):
        report = self.closure('<import addon="script.broken" version="1.0.0"/>',
            '<addon id="script.broken" version="1.0.0"><extension point="xbmc.addon.metadata"><broken>Unavailable upstream</broken></extension></addon>')
        self.assertIn("marked broken", report["failures"][0]["reason"])

    def test_cli_supplied_index_failures_and_errors(self):
        with tempfile.TemporaryDirectory(prefix="omega-closure-", dir="/tmp") as temporary:
            parent = Path(temporary)
            manifest, index = parent / "addon.xml", parent / "addons.xml"
            manifest.write_text('<addon id="skin.aura"><requires><import addon="script.required" version="1.0.0"/></requires></addon>')
            index.write_text('<addons/>')
            with mock.patch("builtins.print"):
                self.assertEqual(closure_main(["--manifest", str(manifest), "--index", str(index)]), 1)
                index.write_text('<broken>')
                self.assertEqual(closure_main(["--manifest", str(manifest), "--index", str(index)]), 2)
                self.assertEqual(closure_main(["--manifest", str(manifest), "--index", str(parent / "absent.xml")]), 2)

    def test_core_versions_and_abis_not_interpreter_or_stubs(self):
        for addon, minimum in (("xbmc.gui", "5.17.0"), ("xbmc.python", "3.0.1"), ("xbmc.json", "13.5.0"), ("script.module.pil", "1.1.7")):
            with self.subTest(addon=addon):
                self.assertEqual(self.closure('<import addon="%s" version="%s"/>' % (addon, minimum), "")["failures"], [])
        for addon, minimum in (("xbmc.gui", "5.15.0"), ("xbmc.python", "2.26.0"), ("xbmc.json", "99.0.0")):
            self.assertTrue(self.closure('<import addon="%s" version="%s"/>' % (addon, minimum), "")["failures"])
        self.assertEqual(CORE["xbmc.json"][:2], ("13.5.0", "6.0.0"))

    def test_binary_core_abi_floors_and_upper_bounds(self):
        for addon in ("kodi.binary.global.main", "kodi.binary.global.general", "kodi.binary.global.gui",
                      "kodi.binary.global.filesystem", "kodi.binary.global.tools", "kodi.binary.instance.inputstream",
                      "kodi.binary.instance.videocodec"):
            version, abi, _ = CORE[addon]
            with self.subTest(addon=addon):
                self.assertFalse(self.closure('<import addon="%s" version="%s"/>' % (addon, version), "")["failures"])
                self.assertFalse(self.closure('<import addon="%s" version="%s"/>' % (addon, abi), "")["failures"])
                self.assertTrue(self.closure('<import addon="%s" version="0.0.1"/>' % addon, "")["failures"])
                report = self.closure('<import addon="%s" version="99.0.0"/>' % addon, "")
                self.assertTrue(report["failures"])
                self.assertTrue(report["core_evidence"][addon].endswith("addon.xml.in"))
                self.assertTrue(report["binary_version_abi_evidence"].endswith("versions.h"))

    def test_version_order_cycles_and_ambiguous_platforms(self):
        for left, right in (("2.0.9", "2.0.10"), ("1.1.1", "1.1.1+matrix.2"), ("2.0.0~beta1", "2.0.0"), ("1:1.0", "2:0.1")):
            self.assertLess(compare_versions(left, right), 0)
        self.assertEqual(compare_versions("1.01", "1.1"), 0)
        graph = '<addon id="script.a" version="1.0.0"><requires><import addon="script.a" version="1.0.0"/></requires></addon>'
        self.assertFalse(self.closure('<import addon="script.a" version="1.0.0"/>', graph)["failures"])
        graph += '<addon id="script.a" version="1.0.0"><requires><import addon="script.b" version="1.0.0"/></requires></addon>'
        self.assertIn("ambiguous", self.closure('<import addon="script.a" version="1.0.0"/>', graph)["failures"][0]["reason"])

    def test_required_failure_integrates_into_checker(self):
        source = Source(ROOT)
        report = check_source(source, b"<addons/>")
        failed = {n["check"] for n in report["checks"] if not n["passed"]}
        self.assertIn("dependency:official-recursive-closure", failed)
        self.assertTrue(report["official_closure"]["failures"])


class PackagingRegressions(unittest.TestCase):
    def source(self, root, baseline=False):
        data = {name + "/fixture.png": b"runtime bytes\x00\xff" for name in DIRECTORIES}
        data.update({name: b"root bytes" for name in ROOT_FILES
                     if not baseline or name not in RUNTIME_REVIEW_ADDITIONS})
        version = BASELINE_VERSION if baseline else VERSION
        data["addon.xml"] = ('<addon id="skin.aura" name="Aura" provider-name="kcook98765" version="%s"/>' % version).encode()
        return MemorySource(data, {}, baseline=baseline, root=root)

    def test_explicit_runtime_allowlist_and_exclusions(self):
        for name in (GENERATED, "tools/check_omega.py", ".git/config", "unrelated-notes.md",
                     "1080i/__pycache__/cache.pyc", "extras/.cache/file", "media/Thumbs.db",
                      "media/desktop.ini", "media/file.bak", "media/tests/file.xml", "../addon.xml",
                      "resources/evidence/log.xml", "resources/addon_data/settings.xml", "resources/settings.xml",
                      "resources/accounts/token.xml", "resources/userdata/guisettings.xml", "media/TOOLS/helper.xml"):
            with self.subTest(excluded=name):
                self.assertFalse(payload_path(name))
        for name in (*ROOT_FILES, *(directory + "/runtime.png" for directory in DIRECTORIES)):
            self.assertTrue(runtime_path(name), name)
        self.assertTrue(runtime_path("1080i/Settings.xml"))
        self.assertEqual(OPTIONAL_DOCS, ())

    def test_operational_docs_never_enter_inventory_or_payload(self):
        with tempfile.TemporaryDirectory(prefix="omega-docs-", dir=tempfile.gettempdir()) as temporary:
            parent = Path(temporary)
            root = parent / "source"
            root.mkdir()
            source = self.source(root)
            for name, data in source.data.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            (root / "tools").mkdir()
            (root / RUNTIME_MANIFEST).write_text("\n".join(source.files) + "\n")
            records = b"\0".join(b"100644 blob " + b"0" * 40 + b"\t" + name.encode() for name in source.files) + b"\0"

            def inventory():
                with mock.patch("omega_common.git", side_effect=[b"starting", b"head", b"fixture", records]), \
                     mock.patch("omega_common.RUNTIME_MANIFEST_SHA256", hashlib.sha256((root / RUNTIME_MANIFEST).read_bytes()).hexdigest()):
                    return Source(root)

            docs = ("OMEGA.md", "DEPENDENCIES-OMEGA.md", "MIGRATION-DECISIONS.md",
                    "OFFICIAL-DEPENDENCY-RESEARCH.md", "PVR-EPG-DESIGN-RESEARCH.md", "MIGRATION-RESULTS.md")
            self.assertEqual(inventory().files, source.files)
            for name in docs:
                (root / name).write_bytes(("Documentation: " + name).encode())
                self.assertNotIn(name, inventory().files)
                self.assertFalse(payload_path(name))
            selected = inventory()
            # Use a miniature fixture, not an actual final skin build.
            packaged = MemorySource({name: selected.read(name) for name in selected.files}, {}, root=root)
            receipt = build(packaged, parent / "fixture-build")
            with zipfile.ZipFile(parent / "fixture-build" / receipt["zip"]["name"]) as tree:
                self.assertEqual({n.removeprefix("skin.aura/") for n in tree.namelist() if not n.endswith("/")},
                                 set(source.files))
                for name in docs:
                    self.assertNotIn("skin.aura/" + name, tree.namelist())

    def test_deterministic_zip_hash_receipt_modes_crc_and_readback(self):
        with tempfile.TemporaryDirectory(prefix="omega-build-", dir=tempfile.gettempdir()) as temporary:
            parent = Path(temporary)
            source = self.source(parent / "source")
            one = build(source, parent / "one")
            two = build(source, parent / "two")
            self.assertEqual(one, two)
            self.assertEqual((parent / "one" / one["zip"]["name"]).read_bytes(),
                             (parent / "two" / two["zip"]["name"]).read_bytes())
            self.assertTrue(one["zip"]["crc_verified"])
            self.assertTrue(one["zip"]["readback_tree_consistent"])
            self.assertEqual(one["zip"]["name"], "skin.aura-2.1.0-omega-official-local.zip")
            self.assertEqual(one["addon"]["version"], "2.1.0")
            self.assertEqual(set(one["files"]), set(source.files))
            self.assertEqual(json.loads((parent / "one/receipt.json").read_text()), one)
            with zipfile.ZipFile(parent / "one" / one["zip"]["name"]) as tree:
                self.assertIsNone(tree.testzip())
                for info in tree.infolist():
                    self.assertEqual(stat.S_IMODE(info.external_attr >> 16), 0o755 if info.is_dir() else 0o644)
                    self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
            with self.assertRaisesRegex(ValueError, "must not exist"):
                build(source, parent / "one")
            baseline = build(self.source(parent / "source", baseline=True), parent / "baseline")
            self.assertEqual(baseline["zip"]["name"], "skin.aura-2.0.23-omega-baseline-local.zip")

    def test_refuse_files_directories_symlinks_and_missing_parent(self):
        with tempfile.TemporaryDirectory(prefix="omega-output-", dir=tempfile.gettempdir()) as temporary:
            parent = Path(temporary)
            (parent / "file").write_bytes(b"keep")
            (parent / "directory").mkdir()
            (parent / "link").symlink_to(parent / "missing")
            for name in ("file", "directory", "link", "missing/child"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    new_output(parent / name, ROOT)
            self.assertEqual((parent / "file").read_bytes(), b"keep")
            with self.assertRaises(ValueError):
                new_output(ROOT / "tools/never-created", ROOT)

    def test_archive_source_ignores_worktree_bytes(self):
        source = Source(ROOT, baseline=True, archive=True)
        # README and manifest have known worktree changes; compare against actual commit bytes.
        for name in ("README", "addon.xml", "shortcuts/template.xml"):
            self.assertEqual(source.read(name), source.original(name))
        self.assertNotIn("1080i/MyFavourites.xml", source.files)
        self.assertIn("1080i/DialogFavourites.xml", source.files)
        self.assertNotIn(GENERATED, source.files)
        self.assertTrue(set(OPTIONAL_DOCS).isdisjoint(source.files))


if __name__ == "__main__":
    unittest.main()
