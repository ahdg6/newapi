"""Exercise the real export boundary, including exports nested under ignored Git paths."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PrepareTests(unittest.TestCase):
    def run_prepare(self, destination, *args, root=ROOT):
        return subprocess.run([sys.executable, str(root / 'scripts/prepare.py'),
                               str(destination), *args], capture_output=True, text=True)

    def test_nested_export_applies_patch_and_is_repeatable(self):
        (ROOT / '.build').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT / '.build') as temporary:
            parent = Path(temporary)
            sources = []
            for name in ('first', 'second'):
                output = parent / name
                result = self.run_prepare(output, '--source-url',
                    'https://github.com/ahdg6/newapi/releases/tag/build-test-1')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('enforceDSHOIDCRoute', (output / 'middleware/auth.go').read_text())
                self.assertTrue((output / 'middleware/dsh_oidc_test.go').is_file())
                self.assertIn('releases/tag/build-test-1',
                    (output / 'web/src/components/layout/components/footer.tsx').read_text())
                manifest = json.loads((output / 'DSH-BUILD.json').read_text())
                self.assertEqual(len(manifest['upstream']['.']), 40)
                self.assertTrue((output / 'LICENSE').is_file())
                self.assertTrue((output / 'NOTICE').is_file())
                self.assertTrue((output / 'relaykit/go.mod').is_file())
                sources.append((output / 'middleware/dsh_oidc.go').read_bytes())
            self.assertEqual(*sources)
            existing = self.run_prepare(parent / 'first')
            self.assertNotEqual(existing.returncode, 0)
            self.assertIn('FileExistsError', existing.stderr)

    def test_rejected_patch_cannot_report_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'scripts').mkdir()
            (root / 'patches').mkdir()
            (root / 'vendor').mkdir()
            shutil.copy(ROOT / 'scripts/prepare.py', root / 'scripts/prepare.py')
            (root / 'vendor/new-api').symlink_to(ROOT / 'vendor/new-api', target_is_directory=True)
            (root / 'patches/0001-broken.patch').write_text(
                'diff --git a/absent.txt b/absent.txt\n--- a/absent.txt\n+++ b/absent.txt\n'
                '@@ -1 +1 @@\n-old\n+new\n')
            result = self.run_prepare(root / 'output', root=root)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('absent.txt', result.stderr)
            self.assertFalse((root / 'output/DSH-BUILD.json').exists())

    def test_invalid_source_url_rejected_before_export(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'output'
            result = self.run_prepare(output, '--source-url', 'https://example.test/private')
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
