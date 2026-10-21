"""Run only these static regressions: python3 -B -m unittest discover -s tools -p 'test_confirmation.py' -v."""

import copy
import unittest
from urllib.parse import parse_qsl
import xml.etree.ElementTree as ET

from check_omega import Checks, ROOT, confirmation_checks, control, direct_native, signature
from omega_common import FOCUSED_DELTA, Source


class ConfirmationRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Source(ROOT)
        cls.roots = {name: ET.fromstring(cls.source.read(name)) for name in (
            "1080i/DialogConfirm.xml", "1080i/Home.xml", "1080i/script-skinshortcuts.xml", "1080i/Includes.xml",
        )}

    @classmethod
    def original_xml(cls, name):
        return ET.fromstring(cls.source.original(name))

    def results(self, roots=None):
        checks = Checks()
        confirmation_checks(checks, self.roots if roots is None else roots, self.original_xml)
        return {n["check"]: n["passed"] for n in checks.results}

    def test_generic_confirmation_preserves_entire_native_dialog(self):
        self.assertTrue(all(self.results().values()), self.results())
        self.assertIn("1080i/DialogConfirm.xml", FOCUSED_DELTA)
        dialog = self.roots["1080i/DialogConfirm.xml"]
        original = self.original_xml("1080i/DialogConfirm.xml")
        hooks = original.findall("onunload")
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0].attrib, {"condition": "!Skin.HasSetting(WidgetsInit)"})
        self.assertEqual(hooks[0].text, "RunScript(script.skinshortcuts,type=manage&group=mainmenu)")
        original.remove(hooks[0])
        self.assertEqual(signature(dialog), signature(original))
        self.assertEqual(dialog.findall("onunload"), [])
        self.assertEqual(dialog.findall("defaultcontrol"), [])  # Native default focus remains unspecified.
        for number, description in ((10, "No"), (11, "Yes")):
            button = control(dialog, number, "button")
            self.assertTrue(direct_native(button))
            self.assertEqual(button.findtext("description"), description)
        # Whole-dialog comparison must reject unrelated appearance/native changes.
        for xpath, value in ((".//control[@id='10']/width", "321"),
                             (".//control[@id='11']/texturefocus", "other.png"),
                             (".//control[@type='grouplist']/itemgap", "31")):
            with self.subTest(xpath=xpath):
                roots = copy.deepcopy(self.roots)
                roots["1080i/DialogConfirm.xml"].find(xpath).text = value
                self.assertFalse(self.results(roots)["confirmation:original-minus-exact-hook"])

    def test_home_initializes_before_unchanged_build_and_controls(self):
        home = self.roots["1080i/Home.xml"]
        original = self.original_xml("1080i/Home.xml")
        init, build = home.findall("onload")[:2]
        self.assertEqual(init.text, "Skin.SetBool(WidgetsInit)")
        self.assertEqual(init.attrib, {"condition": "!Skin.HasSetting(WidgetsInit)"})
        self.assertEqual(signature(build), signature(original.find("onload")))
        self.assertEqual(dict(parse_qsl(build.text[len("RunScript(script.skinshortcuts,"):-1])), {
            "type": "buildxml", "mainmenuID": "300", "mode": "single", "group": "mainmenu|powermenu",
        })
        self.assertEqual(signature(home.find("controls")), signature(original.find("controls")))
        self.assertEqual(home.findtext("defaultcontrol"), "4000")
        for mutation, expected in (("late", "home:widgets-init-before-buildxml"),
                                   ("unconditional", "home:widgets-init-before-buildxml"),
                                   ("commas", "home:unchanged-buildxml-arguments"),
                                   ("focus", "home:original-controls-and-focus4000"),
                                   ("controls", "home:original-controls-and-focus4000")):
            with self.subTest(mutation=mutation):
                roots = copy.deepcopy(self.roots)
                fixture = roots["1080i/Home.xml"]
                first, second = fixture.findall("onload")[:2]
                if mutation == "late":
                    fixture.remove(first)
                    fixture.insert(list(fixture).index(second) + 1, first)
                elif mutation == "unconditional":
                    first.attrib.clear()
                elif mutation == "commas":
                    second.text = second.text.replace("&", ",")
                elif mutation == "focus":
                    fixture.find("defaultcontrol").text = "300"
                else:
                    fixture.find(".//control[@id='4000']/width").text = "2"
                self.assertFalse(self.results(roots)[expected])

    def test_first_home_disables_old_warmup_without_forcing_or_resetting(self):
        self.assertTrue(self.results()["confirmation:no-forced-editor-dialog-or-menu-reset"])
        self.assertTrue(self.results()["editor:original-widgets-init-warmup-guard"])
        # Closed two-state fixture, not a Kodi condition evaluator: first Home sets
        # the flag before buildxml; later editor entry cannot close/toggle it.
        for initialized in (False, True):
            with self.subTest(initialized=initialized):
                events = []
                for node in self.roots["1080i/Home.xml"].findall("onload")[:2]:
                    if node.get("condition") == "!Skin.HasSetting(WidgetsInit)":
                        if not initialized:
                            self.assertEqual(node.text, "Skin.SetBool(WidgetsInit)")
                            initialized = True
                    else:
                        events.append(("buildxml", initialized))
                self.assertEqual(events, [("buildxml", True)])
                for tag in ("onload", "onunload"):
                    warmup = self.roots["1080i/script-skinshortcuts.xml"].find(
                        tag + "[@condition='!Skin.HasSetting(WidgetsInit)']")
                    self.assertIsNotNone(warmup)
                    self.assertFalse(not initialized, "Old editor warmup must be ineligible after first Home")
        for action in ("RunScript(script.skinshortcuts,type=manage&group=mainmenu)",
                       "ActivateWindow(1117)", "Dialog.YesNo(test)",
                       "RunScript(script.skinshortcuts,type=resetall)", "Skin.ResetAll()", "Skin.Reset(WidgetsInit)"):
            with self.subTest(action=action):
                roots = copy.deepcopy(self.roots)
                ET.SubElement(roots["1080i/Home.xml"], "onload").text = action
                self.assertFalse(self.results(roots)["confirmation:no-forced-editor-dialog-or-menu-reset"])
        roots = copy.deepcopy(self.roots)
        roots["1080i/script-skinshortcuts.xml"].find("onload").attrib.clear()
        self.assertFalse(self.results(roots)["editor:original-widgets-init-warmup-guard"])

    def test_restoring_exact_old_unload_hook_fails_guard(self):
        roots = copy.deepcopy(self.roots)
        hook = self.original_xml("1080i/DialogConfirm.xml").find("onunload")
        roots["1080i/DialogConfirm.xml"].insert(0, hook)
        results = self.results(roots)
        self.assertFalse(results["confirmation:no-editor-onunload"])
        self.assertFalse(results["confirmation:original-minus-exact-hook"])
        self.assertFalse(results["confirmation:no-forced-editor-dialog-or-menu-reset"])


if __name__ == "__main__":
    unittest.main()
