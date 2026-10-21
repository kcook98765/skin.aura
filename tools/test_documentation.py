"""Offline documentation/notice checks; no Kodi, network or asset changes."""
import re
import unittest
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

from build_omega import ROOT
from omega_common import git
from test_notices import FONT_NOTICES, NOTICE


class DocumentationRegressions(unittest.TestCase):
    def test_readme_keeps_candidate_target_attribution_and_permission_limits(self):
        readme = (ROOT / "README").read_text()
        for phrase in ("2.1.0", "development candidate", "21.3", "5.17.0",
                       "jurialmunkey/skin.aura", "kcook98765/skin.aura",
                       "not an officially validated release", NOTICE,
                       "Attribution and disclosure do not grant missing permissions."):
            self.assertIn(phrase, readme)

    def test_proposal_keeps_exact_historical_refs_and_requires_approval(self):
        proposal = (ROOT / "docs/PUBLICATION.md").read_text()
        for phrase in ("`matrix`", "`main`", "`master`", "`Nexus`",
                       "203aba5117f185a34fef773134d3cf955cbf2c7a",
                       "3d1e74416e8df80bf17eb87ae4de049c40676037",
                       "authorizes no commit", "Historical tags"):
            self.assertIn(phrase, proposal)
        self.assertIn("not themselves GitHub", proposal)
        self.assertIn("do not erase restrictions", (ROOT / "docs/THIRD-PARTY-LICENSE-REVIEW.md").read_text())

    def test_shipped_notice_names_all_existing_font_notices_and_restrictions(self):
        notice = (ROOT / NOTICE).read_text()
        for name in sorted(FONT_NOTICES):
            self.assertIn(name, notice)
        for phrase in ("LICENSE.txt", "not legal advice or a new license",
                       "does not satisfy them or authorize", "iconmonstr.com",
                       "Nasalization", "SF Distant Galaxy", "media/lang/",
                       "499b3044d358c6b26d7be826482df43dc4f15d26"):
            self.assertIn(phrase, notice)

    def test_relative_markdown_links_resolve_in_source_checkout(self):
        documents = [ROOT / "README", *sorted((ROOT / "docs").glob("*.md"))]
        for document in documents:
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", document.read_text()):
                link = urlsplit(target)
                if link.scheme or link.netloc or not link.path:
                    continue
                with self.subTest(document=document.name, target=target):
                    destination = (document.parent / unquote(link.path)).resolve()
                    self.assertTrue(destination.is_relative_to(ROOT))
                    self.assertTrue(destination.is_file())

    def test_notice_is_not_export_ignored_but_development_files_are(self):
        output = git(ROOT, "check-attr", "export-ignore", "--", NOTICE,
                     "docs/PUBLICATION.md", "tools/test_notices.py").decode()
        self.assertIn(NOTICE + ": export-ignore: unspecified", output)
        self.assertIn("docs/PUBLICATION.md: export-ignore: set", output)
        self.assertIn("tools/test_notices.py: export-ignore: set", output)

    def test_manifest_is_unchanged_and_remains_omega_candidate(self):
        data = (ROOT / "addon.xml").read_bytes()
        self.assertEqual(data, git(ROOT, "show", "HEAD:addon.xml"))
        addon = ET.fromstring(data)
        self.assertEqual(addon.get("id"), "skin.aura")
        self.assertEqual(addon.get("version"), "2.1.0")
        self.assertEqual(addon.find("./requires/import[@addon='xbmc.gui']").get("version"), "5.17.0")


if __name__ == "__main__":
    unittest.main()
