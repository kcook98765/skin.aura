"""Preserve original Aura Omega resources; static checks are not rights approval."""
import io
from pathlib import Path
import tarfile
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from omega_common import Source, RESTORED_OMEGA_COMMIT, RESTORED_DOCUMENTATION, RUNTIME_REVIEW_REMOVALS, git
from build_omega import build

ROOT = Path(__file__).resolve().parents[1]


def original_runtime():
    names = git(ROOT, 'show', RESTORED_OMEGA_COMMIT + ':tools/runtime-files.txt').decode().splitlines()
    with tarfile.open(fileobj=io.BytesIO(git(ROOT,'archive','--format=tar',RESTORED_OMEGA_COMMIT))) as archive:
        return {n:archive.extractfile(n).read() for n in names}


class AlphaDistribution(unittest.TestCase):
    def test_original_runtime_resources_and_behavior_are_preserved(self):
        original = original_runtime();source = Source(ROOT)
        self.assertEqual(len(original),1802)
        self.assertFalse(RUNTIME_REVIEW_REMOVALS)
        self.assertTrue(set(original) <= set(source.files))
        self.assertEqual(set(source.files)-set(original),{
            'fonts/Apache-2.0.txt','fonts/Roboto-Regular-LineSpacingMod-NOTICE.txt',
            'resources/ICONMONSTR-LICENSE.txt','resources/LEGACY-ASSET-NOTICES.txt'})
        for name,data in original.items():
            if name not in RESTORED_DOCUMENTATION:
                self.assertEqual(source.read(name),data,name)
        for name in RESTORED_DOCUMENTATION:
            self.assertIn(name,original)

    def test_original_font_roles_and_screenshots_remain(self):
        source = Source(ROOT)
        for node in ET.parse(ROOT/'1080i/Font.xml').iter('filename'):
            if node.text not in {'Arial.ttf','teletext.ttf'}:
                self.assertIn('fonts/'+node.text,source.files)
        manifest = ET.parse(ROOT/'addon.xml')
        self.assertEqual([n.text for n in manifest.findall('.//screenshot')],
                         ['resources/screenshot-%02d.jpg'%n for n in range(1,6)])
        self.assertEqual(manifest.find("requires/import[@addon='xbmc.gui']").get('version'),'5.17.0')

    def test_canonical_archive_has_exact_restored_inventory(self):
        with tempfile.TemporaryDirectory(prefix='aura-restored-test-',dir='/tmp') as parent:
            output = Path(parent)/'build';receipt=build(Source(ROOT),output)
            self.assertEqual(receipt['zip']['name'],'skin.aura-2.1.0.zip')
            with zipfile.ZipFile(output/receipt['zip']['name']) as archive:
                self.assertEqual(len(archive.infolist()),1806)
                self.assertFalse(any(n.is_dir() for n in archive.infolist()))

    def test_original_licenses_and_font_notices_are_preserved(self):
        source = Source(ROOT);original=original_runtime()
        notices=[n for n in original if n.startswith('fonts/') and n.endswith(('.txt','.pdf'))]
        self.assertEqual(len(notices),10)
        for name in ['LICENSE.txt',*notices]:
            self.assertEqual(source.read(name),original[name],name)
        self.assertIn('herbert@knavs.net',source.read('resources/LEGACY-ASSET-NOTICES.txt').decode())


if __name__ == '__main__':
    unittest.main()
