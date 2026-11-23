#!/usr/bin/env python3
"""Source-only Repair B checks, not a Kodi renderer or native acceptance test.

Kodi 21.3 GUIIncludes.cpp:470-485 merges defaults without overwriting passed
values, substitutes a copied definition, then expands its nested includes.
GUIInfoLabel.cpp:170-204 scans the INPUT only: replacement text is not rescanned.
Consequently these inputs use literal defaults, not defaults containing $PARAM.
Only the two flag includes and their pathname badge predicates are
expanded here. Visibility settings, UI reachability and InfoLabel providers are
not emulated. --source-root allows checking retained original XML separately.
"""

import argparse
import copy
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
PARAM = re.compile(r"\$PARAM\[([^\[\]]+)\]")


def substitute(text, params):
    # re.sub does not rescan replacements, just like the pinned input/output loop.
    return PARAM.sub(lambda match: params.get(match[1], ""), text)


def expand(definition, passed):
    params = {p.get("name"): p.get("default", "")
              for p in definition.findall("param")}
    params.update(passed)
    body = copy.deepcopy(definition.find("definition"))
    for node in body.iter():
        node.attrib.update({key: substitute(value, params)
                            for key, value in node.attrib.items()})
        if node.text:
            node.text = substitute(node.text, params)
    return body


def values(call):
    return {p.get("name"): p.get("value", p.text or "")
            for p in call.findall("param")}


def predicates(body):
    images = body.findall(".//control[@type='image']")
    def visible(ending):
        found = [image.findtext("visible") for image in images
                 if (image.findtext("texture") or "").endswith(ending)]
        assert len(found) == 1, (ending, found)
        return found[0]
    return (visible("resolution/,.png]"), visible("/other/4K.png"),
            visible("/other/HDR.png"))


def path_result(expressions, labels):
    """Evaluate only the fixed StartsWith/Contains operands, not Kodi conditions."""
    resolution, uhd, hdr = expressions
    path, prefix = re.findall(r"String.StartsWith\(([^,]+),([^\)]+)\)", resolution)[0]
    def contains(expression):
        terms = re.findall(r"String.Contains\(([^,]+),([^\)]+)\)", expression)
        assert terms, expression
        return any(word.casefold() in labels.get(label, "").casefold()
                   for label, word in terms)
    return (not labels.get(path, "").casefold().startswith(prefix.casefold()),
            contains(uhd), contains(hdr))


def filename_badges(body, labels):
    """The actual filename-only image predicates; separate visible tags AND."""
    result = {}
    for image in body.findall(".//control[@type='image']"):
        conditions = image.findall("visible")
        if not conditions or not all("String.Contains(" in (node.text or "")
                                     for node in conditions):
            continue
        states = []
        for node in conditions:
            expression = node.text
            terms = re.findall(r"String.Contains\(([^,]+),([^\)]+)\)", expression)
            assert terms, expression
            state = any(word.casefold() in labels.get(label, "").casefold()
                        for label, word in terms)
            states.append(not state if expression.startswith("!") else state)
        texture = image.findtext("texture").rsplit("/", 1)[1]
        result[texture] = all(states)
    return result


class PlayerPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        obj = ET.parse(ROOT / "1080i/Includes_Object.xml").getroot()
        cls.flags = obj.find("include[@name='Object_Flags']")
        cls.content = obj.find("include[@name='Object_Flags_Content']")
        cls.osd = ET.parse(ROOT / "1080i/Includes_OSD.xml").getroot()

    def flows(self, passed):
        wrapper = expand(self.flags, passed)
        calls = wrapper.findall("include[@content='Object_Flags_Content']")
        self.assertEqual(len(calls), 2)  # monochrome and colour branches
        return [expand(self.content, values(call)) for call in calls]

    def test_one_pass_substitution(self):
        self.assertEqual(substitute("$PARAM[path]", {
            "path": "$PARAM[source]Path", "source": "ListItem."
        }), "$PARAM[source]Path")
        self.assertEqual(substitute("$PARAM[container]$PARAM[source]Path", {
            "container": "Container(50).", "source": "ListItem."
        }), "Container(50).ListItem.Path")

    def test_literal_defaults_and_forwarding(self):
        for definition in (self.flags, self.content):
            for name, default in (("path", "ListItem.Path"),
                                  ("filename", "ListItem.FileNameAndPath")):
                with self.subTest(include=definition.get("name"), param=name):
                    param = definition.find(f"param[@name='{name}']")
                    self.assertIsNotNone(param)
                    self.assertEqual(param.get("default"), default)
        for call in self.flags.findall("definition/include"):
            self.assertEqual(values(call).get("path"), "$PARAM[path]")
            self.assertEqual(values(call).get("filename"), "$PARAM[filename]")

    def test_existing_generic_callers(self):
        count = 0
        for file in sorted((ROOT / "1080i").glob("*.xml")):
            if file.name == "Includes_OSD.xml":
                continue
            for call in ET.parse(file).findall(".//include[@content='Object_Flags']"):
                count += 1
                passed = values(call)
                self.assertNotIn("path", passed)
                self.assertNotIn("filename", passed)
                self.assertEqual(passed.get("source", "ListItem."), "ListItem.")
                container = passed.get("container", "")
                for body in self.flows(passed):
                    expressions = predicates(body)
                    self.assertIn(f"String.StartsWith({container}ListItem.Path,", expressions[0])
                    self.assertIn(f"String.Contains({container}ListItem.FileNameAndPath,", expressions[1])
        self.assertEqual(count, 5)

    def test_listitem_and_container_defaults(self):
        for container in ("", "Container(50).", "Container(9000)."):
            for direct in (False, True):
                bodies = ([expand(self.content, {"container": container})] if direct
                          else self.flows({"container": container}))
                for body in bodies:
                    expressions = predicates(body)
                    self.assertIn(f"String.StartsWith({container}ListItem.Path,", expressions[0])
                    self.assertNotIn("$PARAM[", "".join(expressions))
                    for path, filename, expected in (
                        ("/library/", "library.2160p.HDR.mkv", (True, True, True)),
                        ("videodb://movies/sets/1/", "plain.mkv", (False, False, False)),
                    ):
                        with self.subTest(container=container, direct=direct, filename=filename):
                            self.assertEqual(path_result(expressions, {
                                container + "ListItem.Path": path,
                                container + "ListItem.FileNameAndPath": filename,
                                "Player.FilenameAndPath": "opposite.UHD.HDR.mkv",
                            }), expected)

    def test_four_osd_callers_and_current_player(self):
        total = 0
        for name in ("OSD_Music_Info", "OSD_Video_Seekbar"):
            calls = self.osd.findall(f"include[@name='{name}']//include[@content='Object_Flags']")
            self.assertEqual(len(calls), 2)
            for call in calls:
                total += 1
                passed = values(call)
                with self.subTest(osd=name, condition=call.get("condition")):
                    self.assertEqual(passed.get("source"), "VideoPlayer.")
                    self.assertEqual(passed.get("path"), "Player.Folderpath")
                    self.assertEqual(passed.get("filename"), "Player.FilenameAndPath")
                for body in self.flows(passed):
                    expressions = predicates(body)
                    self.assertIn("String.StartsWith(Player.Folderpath,", expressions[0])
                    self.assertIn("VideoPlayer.VideoResolution", expressions[0])
                    self.assertNotIn("$PARAM[", "".join(expressions))
                    # Both directions: selected library item must not control player badges.
                    for filename, selected, expected in (
                        ("movie.2160p.HDR.mkv", "plain.mkv", (True, True, True)),
                        ("clip.UHD.mkv", "selected.HDR.mkv", (True, True, False)),
                        ("clip.UltraHD.mkv", "plain.mkv", (True, True, False)),
                        ("clip.Ultra-HD.mkv", "plain.mkv", (True, True, False)),
                        ("clip.4K.mkv", "plain.mkv", (True, True, False)),
                        ("clip.HDR.mkv", "selected.UHD.mkv", (True, False, True)),
                        ("plain.1080p.mkv", "selected.UHD.HDR.mkv", (True, False, False)),
                    ):
                        with self.subTest(osd=name, filename=filename, selected=selected):
                            self.assertEqual(path_result(expressions, {
                                "Player.Folderpath": "/playing/",
                                "Player.FilenameAndPath": "/playing/" + filename,
                                "ListItem.Path": "videodb://movies/sets/9/",
                                "ListItem.FileNameAndPath": "/selected/" + selected,
                                # Unsupported VideoPlayer path labels intentionally absent.
                            }), expected)
        self.assertEqual(total, 4)

    def test_reverted_binding_negative_control(self):
        call = self.osd.find(".//include[@content='Object_Flags']")
        body = self.flows(values(call))[0]
        good = predicates(body)
        labels = {"Player.Folderpath": "videodb://movies/sets/1/",
                  "Player.FilenameAndPath": "/playing/clip.2160p.HDR.mkv"}
        self.assertEqual(path_result(good, labels), (False, True, True))
        reverted = tuple(expression.replace("Player.Folderpath", "VideoPlayer.Path")
                         .replace("Player.FilenameAndPath", "VideoPlayer.FileNameAndPath")
                         for expression in good)
        self.assertEqual(path_result(reverted, labels), (True, False, False))
        self.assertNotEqual(path_result(good, labels), path_result(reverted, labels))

    def test_all_filename_badges_and_no_source_derived_paths(self):
        source = ET.tostring(self.content, encoding="unicode")
        self.assertNotIn("$PARAM[source]Path", source)
        self.assertNotIn("$PARAM[source]FileNameAndPath", source)
        badges = {"4K.png", "HDR.png", "atmos.png", "dtsx.png", "bluray.png",
                  "dvd.png", "hdtv.png", "web-dl.png"}
        cases = (
            ("plain.mkv", set()),
            ("2160p.HDR.atmos.dtsx.bluray.mkv", {"4K.png", "HDR.png", "atmos.png", "dtsx.png"}),
            ("UHD.bluray.mkv", {"4K.png"}),
            ("UltraHD.bluray.mkv", {"4K.png"}),
            ("Ultra-HD.bluray.mkv", {"4K.png"}),
            ("4K.bluray.mkv", {"4K.png"}),
            ("bluray.mkv", {"bluray.png"}),
            ("blu-ray.mkv", {"bluray.png"}),
            ("bdrip.mkv", {"bluray.png"}),
            ("bd25.mkv", {"bluray.png"}),
            ("bd50.mkv", {"bluray.png"}),
            ("bdmv.mkv", {"bluray.png"}),
            ("dts-x.mkv", {"dtsx.png"}),
            ("dts:x.mkv", {"dtsx.png"}),
            ("dvd.hdtv.web-dl.mkv", {"dvd.png", "hdtv.png", "web-dl.png"}),
            ("pdtv.webdl.mkv", {"hdtv.png", "web-dl.png"}),
            ("dsr.WEBRip.mkv", {"hdtv.png", "web-dl.png"}),
        )
        calls = [values(call) for call in self.osd.findall(".//include[@content='Object_Flags']")]
        calls += [{"container": container} for container in ("", "Container(50).")]
        for passed in calls:
            player = passed.get("source") == "VideoPlayer."
            selected_label = passed.get("container", "") + "ListItem.FileNameAndPath"
            target_label = "Player.FilenameAndPath" if player else selected_label
            opposite_label = selected_label if player else "Player.FilenameAndPath"
            for body in self.flows(passed):
                for filename, expected in cases:
                    # Opposite item intentionally has the inverse badge set in key cases.
                    opposite = "plain.mkv" if expected else "2160p.HDR.atmos.dtsx.dvd.hdtv.web-dl.mkv"
                    with self.subTest(passed=passed, filename=filename):
                        actual = filename_badges(body, {target_label: filename, opposite_label: opposite})
                        self.assertEqual(set(actual), badges)
                        self.assertEqual({badge for badge, shown in actual.items() if shown}, expected)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    args, remaining = parser.parse_known_args()
    ROOT = args.source_root.resolve()
    unittest.main(argv=[__file__, *remaining])
