"""Focused alpha asset/reference and notice checks; no runtime execution."""
from pathlib import Path
import tempfile
import zipfile
import unittest
import xml.etree.ElementTree as ET
from omega_common import Source, RUNTIME_REVIEW_REMOVALS
from build_omega import build

ROOT = Path(__file__).resolve().parents[1]


class AlphaDistribution(unittest.TestCase):
    def test_every_font_role_resolves_to_an_included_font(self):
        files = set(Source(ROOT).files)
        for node in ET.parse(ROOT / '1080i/Font.xml').iter('filename'):
            # Kodi GUIFontManager supplies the unchanged Unicode Arial fallback
            # from special://xbmc/media/Fonts; it is not a bundled third-party font.
            if node.text not in {'Arial.ttf', 'teletext.ttf'}:
                self.assertTrue('fonts/' + node.text in files, node.text)

    def test_restricted_assets_and_legacy_media_references_are_absent(self):
        source = Source(ROOT)
        self.assertEqual(len(RUNTIME_REVIEW_REMOVALS), 506)
        self.assertTrue(set(source.files).isdisjoint(RUNTIME_REVIEW_REMOVALS))
        for name in source.files:
            if name.endswith('.xml'):
                text = source.read(name).decode('utf-8-sig')
                for obsolete in ('lang/eng.png', 'skin/extras/backgrounds/viewmodes/', 'skin/extras/defaulticons/'):
                    self.assertNotIn(obsolete, text, name)
        manifest = ET.parse(ROOT / 'addon.xml')
        self.assertFalse(manifest.findall('.//screenshot'))
        self.assertIsNotNone(manifest.find("extension[@point='xbmc.gui.skin']"))
        self.assertEqual(manifest.find("requires/import[@addon='xbmc.gui']").get('version'), '5.17.0')

    def test_production_archive_has_no_directory_entries(self):
        with tempfile.TemporaryDirectory(prefix='aura-alpha-test-', dir='/tmp') as folder:
            output = Path(folder) / 'build'
            receipt = build(Source(ROOT), output)
            self.assertEqual(receipt['zip']['name'], 'skin.aura-2.1.0.zip')
            with zipfile.ZipFile(output / receipt['zip']['name']) as archive:
                self.assertEqual(len(archive.infolist()), 1300)
                self.assertFalse(any(info.is_dir() for info in archive.infolist()))

    def test_original_licenses_and_all_ten_font_notices_are_preserved(self):
        source = Source(ROOT)
        self.assertEqual(source.read('LICENSE.txt'), source.original('LICENSE.txt'))
        notices = [name for name in source.original_files if name.startswith('fonts/') and name.endswith(('.txt', '.pdf'))]
        self.assertEqual(len(notices), 10)
        for name in notices:
            self.assertEqual(source.read(name), source.original(name), name)
        self.assertIn('application', source.read('resources/ICONMONSTR-LICENSE.txt').decode())
        self.assertIn('Free for opensource non-profitable projects. For anything else contact herbert@knavs.net',
                      source.read('resources/LEGACY-ASSET-NOTICES.txt').decode())


if __name__ == '__main__':
    unittest.main()
