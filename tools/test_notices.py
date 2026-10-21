"""Focused offline notice packaging regressions; no asset or license edits."""

import hashlib
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

from build_omega import ROOT, build
from check_omega import check_source
from omega_common import FOCUSED_DELTA, ROOT_FILES, Source, parse_runtime_manifest
from test_omega import MemorySource

NOTICE = "THIRD-PARTY-NOTICES.txt"
FONT_NOTICES = frozenset("fonts/lyrics/" + name for name in (
    "BOXING License.txt", "Exo2 License.txt", "Fredoka One_license.txt",
    "Geomancy License.txt", "Luckiest Guy_LICENSE.txt", "Poller One_licence.txt",
    "Ranchers-Regular_license.txt", "SF Distant Galaxy_Readme.txt",
    "Theboldfont License.txt", "nasalization_license.pdf",
))


class NoticeRegressions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Source(ROOT)
        # Keep explicit fixture membership: MemorySource must never invent a
        # missing notice, or an omission regression would give a false pass.
        cls.data = {name: cls.source.read(name) for name in cls.source.files
                    if Path(name).suffix.lower() in (".xml", ".xsp", ".po") or name == NOTICE}
        cls.original = {name: cls.source.original(name) for name in cls.source.original_files
                        if Path(name).suffix.lower() in (".xml", ".xsp", ".po")}

    def test_candidate_packages_notice_verbatim_and_preserves_all_supplied_licenses(self):
        source = self.source
        self.assertIn(NOTICE, source.files)
        self.assertEqual(len(source.files), 1802)
        supplied = {name for name in source.original_files
                    if name.startswith("fonts/") and Path(name).suffix.lower() in (".txt", ".pdf")}
        self.assertEqual(supplied, FONT_NOTICES)
        self.assertTrue((supplied | {"LICENSE.txt"}).isdisjoint(FOCUSED_DELTA))
        with tempfile.TemporaryDirectory(prefix="aura-notices-", dir=tempfile.gettempdir()) as temporary:
            output = Path(temporary) / "candidate"
            receipt = build(source, output)
            self.assertEqual(receipt["file_count"], 1802)
            self.assertEqual(receipt["addon"]["version"], "2.1.0")
            with zipfile.ZipFile(output / receipt["zip"]["name"]) as archive:
                notice = (ROOT / NOTICE).read_bytes()
                self.assertEqual(archive.read("skin.aura/" + NOTICE), notice)
                self.assertEqual((output / "skin.aura" / NOTICE).read_bytes(), notice)
                self.assertEqual(receipt["files"][NOTICE]["sha256"], hashlib.sha256(notice).hexdigest())
                addon = ET.fromstring(archive.read("skin.aura/addon.xml"))
                self.assertEqual(addon.get("version"), "2.1.0")
                self.assertIn(b"development candidate", notice)
                for name in sorted(supplied | {"LICENSE.txt"}):
                    with self.subTest(preserved=name):
                        original = source.original(name)
                        self.assertEqual(source.read(name), original)
                        self.assertEqual(archive.read("skin.aura/" + name), original)
                        self.assertEqual((output / "skin.aura" / name).read_bytes(), original)
                        self.assertEqual(receipt["files"][name]["sha256"], hashlib.sha256(original).hexdigest())
                self.assertEqual({name.removeprefix("skin.aura/") for name in archive.namelist()
                                  if not name.endswith("/")}, set(source.files))
                self.assertFalse(any(name.startswith(("docs/", "tools/", ".local/", "private/"))
                                     for name in receipt["files"]))
            print("Candidate notices: 1802 files; version=2.1.0; notice verbatim; "
                  "10 supplied font notices + LICENSE.txt byte-identical to 203aba5")

    def test_candidate_checker_requires_notice_without_changing_baseline_notice_requirement(self):
        fixture = dict(self.data)
        # Explicitly provide it even in a pre-change source; missing below must
        # be rejected by the checker, not concealed by fixture defaults.
        fixture[NOTICE] = (ROOT / NOTICE).read_bytes()
        report = check_source(MemorySource(fixture, self.original))
        required = next(n for n in report["checks"] if n["check"] == "inventory:required-runtime")
        self.assertTrue(required["passed"], required)
        fixture.pop(NOTICE)
        report = check_source(MemorySource(fixture, self.original))
        required = next(n for n in report["checks"] if n["check"] == "inventory:required-runtime")
        self.assertFalse(required["passed"], required)
        self.assertEqual(required["detail"], NOTICE)
        report = check_source(MemorySource(self.original, self.original, baseline=True))
        required = next(n for n in report["checks"] if n["check"] == "inventory:required-runtime")
        self.assertNotIn(NOTICE, required["detail"])

    def test_candidate_manifest_cannot_omit_notice_even_if_pin_were_recomputed(self):
        self.assertIn(NOTICE, ROOT_FILES)
        manifest = (ROOT / "tools/runtime-files.txt").read_bytes()
        without_notice = b"".join(line for line in manifest.splitlines(keepends=True)
                                  if line != NOTICE.encode() + b"\n")
        with self.assertRaisesRegex(ValueError, "all.*root files"):
            parse_runtime_manifest(without_notice)


if __name__ == "__main__":
    unittest.main()
