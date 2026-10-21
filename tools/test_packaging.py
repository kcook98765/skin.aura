"""Focused offline packaging hardening; all mutation fixtures live under /tmp.

Run: PYTHONPATH=tools python3 -B -m unittest -v test_packaging test_omega.PackagingRegressions
"""

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import xml.etree.ElementTree as ET
import zipfile

from build_omega import ROOT, build
from omega_common import (
    ADDED_RUNTIME, BASELINE_VERSION, DIRECTORIES, FOCUSED_DELTA, GENERATED,
    REMOVED_RUNTIME, ROOT_FILES, RUNTIME_MANIFEST, RUNTIME_REVIEW_COMMIT,
    RUNTIME_MANIFEST_SHA256, VERSION, Source, git, parse_runtime_manifest, payload_path, runtime_path,
)


class ManifestRegressions(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="aura-packaging-", dir="/tmp")
        self.addCleanup(temporary.cleanup)
        self.parent = Path(temporary.name)
        self.root = self.parent / "source"
        self.root.mkdir()
        self.files = sorted([*ROOT_FILES, *(name + "/fixture.png" for name in DIRECTORIES)])
        for name in self.files:
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"runtime fixture")
        (self.root / "addon.xml").write_text(
            '<addon id="skin.aura" name="Aura" provider-name="kcook98765" version="2.1.0"/>')
        (self.root / "tools").mkdir()
        self.manifest = self.root / RUNTIME_MANIFEST
        self.manifest.write_bytes(self.manifest_bytes())
        self.records = b"\0".join(b"100644 blob " + b"0" * 40 + b"\t" + name.encode()
                                  for name in self.files) + b"\0"

    def manifest_bytes(self, files=None):
        return ("\n".join(self.files if files is None else files) + "\n").encode()

    def source(self):
        # Mock provenance reads only. Inventory and payload reads are real disk IO.
        with mock.patch("omega_common.git", side_effect=[b"starting", b"head", b"fixture", self.records]), \
             mock.patch("omega_common.RUNTIME_MANIFEST_SHA256", hashlib.sha256(self.manifest_bytes()).hexdigest()):
            return Source(self.root)

    def inject(self, name, data=b"must never enter ZIP"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def assertRejectedBeforeOutput(self, expression="unlisted"):
        output = self.parent / "rejected-output"
        with self.assertRaisesRegex(ValueError, expression):
            build(self.source(), output)
        self.assertFalse(output.exists())

    def test_injected_archives_databases_artwork_sources_docs_and_settings(self):
        for name in (
            "media/backup.zip", "extras/state.json", "resources/account.sqlite", "media/source.xcf",
            "1080i/INTERNAL.md", "extras/notes.markdown", "fonts/operator.MD",
            "resources/docs/release.txt", "resources/internal/notes.xml", "resources/settings.xml",
            "resources/guisettings.xml", "shortcuts/generated/settings.xml", GENERATED,
            "resources/accounts/token.xml", "resources/evidence/report.xml", "media/tests/fixture.png",
            "media/.git/config", "media/tools/helper.py", "media/__pycache__/helper.pyc",
        ):
            with self.subTest(name=name):
                path = self.inject(name)
                self.assertRejectedBeforeOutput()
                path.unlink()

    def test_admissible_untracked_and_ignored_files_fail_closed(self):
        for name in ("media/new.png", "1080i/NewWindow.xml", "shortcuts/new.DATA.xml", "extras/report.txt"):
            with self.subTest(name=name):
                self.assertTrue(runtime_path(name))
                path = self.inject(name)
                # Do not consult Git ignore or tracked state at all.
                self.inject(".gitignore", name.encode() + b"\n")
                self.assertRejectedBeforeOutput()
                path.unlink()

    def test_missing_approved_files_and_runtime_directories_are_rejected(self):
        for name in self.files:
            with self.subTest(name=name):
                path = self.root / name
                data = path.read_bytes()
                path.unlink()
                self.assertRejectedBeforeOutput("missing|Missing")
                path.write_bytes(data)
        (self.root / "media/fixture.png").unlink()
        (self.root / "media").rmdir()
        self.assertRejectedBeforeOutput("runtime directory: media")

    def test_manifest_duplicate_traversal_absolute_and_noncanonical_paths(self):
        for name in (
            "../addon.xml", "/addon.xml", "1080i/../addon.xml", "./addon.xml", "media//file.png",
            "media/./file.png", "media/trailing.png/", "media\\file.png", "C:/file.png",
            "media/*.png", "media/a?.png", "media/[ab].png", "media/control\x00.png",
            "media/line\nfeed.png", "", "tools/runtime-files.txt", "OPERATIONS.md",
            "resources/INTERNAL.md", "media/account.json", GENERATED,
        ):
            with self.subTest(name=name):
                self.manifest.write_bytes(self.manifest_bytes(sorted([*self.files, name])))
                self.assertRejectedBeforeOutput("Invalid runtime manifest path")
        self.manifest.write_bytes(self.manifest_bytes(sorted([*self.files, self.files[0]])))
        self.assertRejectedBeforeOutput("Duplicate runtime manifest path")

    def test_manifest_format_and_required_roots_are_not_silently_normalized(self):
        for data in (
            b"", self.manifest_bytes()[:-1], self.manifest_bytes().replace(b"\n", b"\r\n"),
            self.manifest_bytes(list(reversed(self.files))),
            self.manifest_bytes([name for name in self.files if name != "README"]),
            self.manifest_bytes([name for name in self.files if not name.startswith("themes/")]),
            b"\xef\xbb\xbf" + self.manifest_bytes(),
        ):
            with self.subTest(data=data[:50]):
                self.manifest.write_bytes(data)
                self.assertRejectedBeforeOutput("Runtime manifest|Invalid runtime manifest")

    def test_otherwise_valid_manifest_additions_and_removals_need_explicit_approval(self):
        self.inject("media/new.png")
        self.manifest.write_bytes(self.manifest_bytes(sorted([*self.files, "media/new.png"])))
        self.assertRejectedBeforeOutput("digest differs from reviewed approval")
        (self.root / "media/new.png").unlink()
        # Add a second file in the same directory so removal preserves all nine
        # directories. Removing an approved file and its line cannot hide loss.
        self.inject("media/second.png")
        self.files = sorted([*self.files, "media/second.png"])
        (self.root / "media/fixture.png").unlink()
        self.manifest.write_bytes(self.manifest_bytes([n for n in self.files if n != "media/fixture.png"]))
        self.assertRejectedBeforeOutput("digest differs from reviewed approval")

    def test_missing_symlinked_directory_and_nonregular_manifest(self):
        self.manifest.unlink()
        with self.assertRaises(OSError):
            self.source()
        other = self.parent / "other-manifest.txt"
        other.write_bytes(self.manifest_bytes())
        self.manifest.symlink_to(other)
        with self.assertRaises(OSError):
            self.source()
        self.manifest.unlink()
        self.manifest.mkdir()
        with self.assertRaisesRegex(ValueError, "Non-regular"):
            self.source()
        self.manifest.rmdir()
        os.mkfifo(self.manifest)
        with self.assertRaisesRegex(ValueError, "Non-regular"):
            self.source()

    def test_symlinked_files_and_runtime_directories_are_rejected(self):
        target = self.parent / "external.png"
        target.write_bytes(b"external bytes")
        for name in ("README", "media/fixture.png", "media/unlisted.png"):
            with self.subTest(name=name):
                path = self.root / name
                existed = path.exists()
                if existed:
                    data = path.read_bytes()
                    path.unlink()
                path.symlink_to(target)
                self.assertRejectedBeforeOutput("non-regular|Symlinked")
                path.unlink()
                if existed:
                    path.write_bytes(data)
        external = self.parent / "external-directory"
        (self.root / "media").rename(external)
        (self.root / "media").symlink_to(external, target_is_directory=True)
        self.assertRejectedBeforeOutput("runtime directory: media")

    def test_manifest_parent_and_nested_runtime_directory_links_are_rejected(self):
        tools = self.parent / "external-tools"
        (self.root / "tools").rename(tools)
        (self.root / "tools").symlink_to(tools, target_is_directory=True)
        with self.assertRaises(OSError):
            self.source()
        (self.root / "tools").unlink()
        tools.rename(self.root / "tools")
        external = self.parent / "external-assets"
        external.mkdir()
        (self.root / "media/nested").symlink_to(external, target_is_directory=True)
        self.assertRejectedBeforeOutput("Symlinked runtime directory: media/nested")

    def test_nonregular_approved_and_unlisted_files_rejected_without_blocking(self):
        for name in ("media/fixture.png", "media/pipe.png"):
            with self.subTest(name=name):
                path = self.root / name
                if path.exists():
                    path.unlink()
                os.mkfifo(path)
                self.assertRejectedBeforeOutput("non-regular")
                path.unlink()

    def test_read_rechecks_parent_links_and_nonregular_payload_after_selection(self):
        source = self.source()
        external = self.parent / "swapped-directory"
        (self.root / "media").rename(external)
        (self.root / "media").symlink_to(external, target_is_directory=True)
        with self.assertRaises(OSError):
            source.read("media/fixture.png")
        (self.root / "media").unlink()
        external.rename(self.root / "media")
        (self.root / "media/fixture.png").unlink()
        os.mkfifo(self.root / "media/fixture.png")
        with self.assertRaisesRegex(ValueError, "Non-regular"):
            source.read("media/fixture.png")

    def test_root_development_artifacts_are_excluded_and_receipts_bind_manifest(self):
        for name in ("OMEGA.md", "OPERATIONS.md", "tools/test_omega.py", "tests/fixture.xml",
                     ".git/config", "evidence/receipt.json", "accounts/token.json"):
            self.inject(name)
        source = self.source()
        # This test isolates packaging, not real Git diff provenance.
        with mock.patch.object(source, "deltas", return_value=[]):
            first = build(source, self.parent / "one")
            second = build(self.source_with_no_deltas(), self.parent / "two")
        self.assertEqual(first, second)
        self.assertEqual(first["runtime_manifest"], {
            "kind": "reviewed-exact-file-list", "path": RUNTIME_MANIFEST,
            "sha256": hashlib.sha256(self.manifest_bytes()).hexdigest(),
            "reviewed_commit": RUNTIME_REVIEW_COMMIT, "file_count": len(self.files),
        })
        self.assertEqual(json.loads((self.parent / "one/receipt.json").read_text()), first)
        self.assertEqual((self.parent / "one" / first["zip"]["name"]).read_bytes(),
                         (self.parent / "two" / second["zip"]["name"]).read_bytes())
        with zipfile.ZipFile(self.parent / "one" / first["zip"]["name"]) as archive:
            self.assertEqual({n.removeprefix("skin.aura/") for n in archive.namelist() if not n.endswith("/")},
                             set(self.files))

    def source_with_no_deltas(self):
        source = self.source()
        source.deltas = lambda: []
        return source


class ReviewedInventoryRegressions(unittest.TestCase):
    def test_manifest_matches_reviewed_runtime_tree_and_historical_preservation(self):
        source = Source(ROOT)
        reviewed = {name for name in git(ROOT, "ls-tree", "-r", "--name-only", RUNTIME_REVIEW_COMMIT).decode().splitlines()
                    if payload_path(name)}
        self.assertEqual(set(source.files), reviewed)
        self.assertEqual(set(source.files), (source.original_files - REMOVED_RUNTIME) | ADDED_RUNTIME)
        self.assertEqual(parse_runtime_manifest((ROOT / RUNTIME_MANIFEST).read_bytes()), source.files)
        self.assertEqual(source.runtime_manifest["sha256"], RUNTIME_MANIFEST_SHA256)
        self.assertEqual({n for n in source.files if "/" not in n}, set(ROOT_FILES))
        self.assertEqual({n.split("/")[0] for n in source.files if "/" in n}, set(DIRECTORIES))
        self.assertFalse(any(n.lower().endswith((".md", ".markdown")) for n in source.files))
        print("Reviewed runtime manifest: %d exact files; sha256=%s" % (
            len(source.files), source.runtime_manifest["sha256"]))

    def test_baseline_package_version_bytes_and_inventory_are_truthful(self):
        source = Source(ROOT, baseline=True, archive=True)
        self.assertEqual(ET.fromstring(source.read("addon.xml")).get("version"), "2.0.23")
        self.assertEqual(BASELINE_VERSION, "2.0.23")
        self.assertEqual(VERSION, "2.1.0")
        self.assertEqual(source.files, sorted(source.original_files))
        self.assertEqual(source.runtime_manifest["kind"], "historical-git-tree-inventory")
        self.assertEqual(source.runtime_manifest["commit"], source.starting_commit)
        with tempfile.TemporaryDirectory(prefix="aura-historical-build-", dir="/tmp") as temporary:
            output = Path(temporary) / "baseline"
            receipt = build(source, output)
            self.assertEqual(receipt["addon"]["version"], "2.0.23")
            self.assertEqual(receipt["zip"]["name"], "skin.aura-2.0.23-omega-baseline-local.zip")
            with zipfile.ZipFile(output / receipt["zip"]["name"]) as archive:
                self.assertEqual(archive.read("skin.aura/addon.xml"), source.original("addon.xml"))
                self.assertEqual(set(receipt["files"]), source.original_files)
            print("Historical baseline: %d files; version=2.0.23; zip_sha256=%s" % (
                receipt["file_count"], receipt["zip"]["sha256"]))

    def test_changelog_is_reviewed_but_unrelated_preservation_exceptions_are_not_added(self):
        self.assertIn("changelog.txt", FOCUSED_DELTA)
        for name in ("media/DefaultActor.png", "1080i/MyMusicNav.xml", "shortcuts/template.xml"):
            self.assertNotIn(name, FOCUSED_DELTA)

    def test_builder_and_checker_require_release_version_without_relabeling_baseline(self):
        from check_omega import check_source
        from test_omega import MemorySource

        current = Source(ROOT)
        data = {name: current.read(name) for name in current.files
                if Path(name).suffix.lower() in (".xml", ".xsp", ".po")}
        original = {name: current.original(name) for name in current.original_files
                    if Path(name).suffix.lower() in (".xml", ".xsp", ".po")}
        for baseline, expected, wrong in ((False, "2.1.0", "2.0.23"), (True, "2.0.23", "2.1.0")):
            for version in (expected, wrong):
                with self.subTest(baseline=baseline, version=version):
                    fixture_data = dict(original if baseline else data)
                    addon = ET.fromstring(fixture_data["addon.xml"])
                    addon.set("version", version)
                    fixture_data["addon.xml"] = ET.tostring(addon)
                    fixture = MemorySource(fixture_data, original, baseline=baseline)
                    report = check_source(fixture)
                    identity = next(n for n in report["checks"] if n["check"] == "manifest:identity")
                    self.assertEqual(identity["passed"], version == expected)
                    if version == wrong:
                        with tempfile.TemporaryDirectory(prefix="aura-version-reject-", dir="/tmp") as temporary:
                            output = Path(temporary) / "rejected"
                            with self.assertRaisesRegex(ValueError, "identity/version"):
                                build(fixture, output)
                            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
