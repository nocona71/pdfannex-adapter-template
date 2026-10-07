"""Offline checks for the pinned release dependency."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import core_dependency as dependency


class CoreDependency(unittest.TestCase):
    def test_checksum_mismatch_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / "release.zip"
            archive.write_bytes(b"not the pinned release")
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                dependency.verify_archive(archive)

    def test_release_files_are_mapped_to_tds(self):
        for source, target in (
            ("pdfannex/pdfannex.sty", "tex/latex/pdfannex/pdfannex.sty"),
            ("pdfannex/scripts/pdfannex/pdfannex", "scripts/pdfannex/pdfannex"),
            ("pdfannex/pdfannex.1", "doc/man/man1/pdfannex.1"),
            ("pdfannex/README.md", "doc/latex/pdfannex/README.md"),
        ):
            with self.subTest(source=source):
                self.assertEqual(dependency.tds_path(source), target)
        with self.assertRaisesRegex(RuntimeError, "unexpected core release member"):
            dependency.tds_path("other/package.sty")

    def test_download_failure_is_not_skipped_or_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            archive = cache / "release.zip"
            with (
                patch.multiple(dependency, CACHE=cache, CTAN_ARCHIVE=archive),
                patch.object(
                    dependency.subprocess, "run",
                    side_effect=dependency.subprocess.CalledProcessError(22, "curl"),
                ),
            ):
                with self.assertRaises(dependency.subprocess.CalledProcessError):
                    dependency.ensure_release()
                self.assertFalse(archive.exists())

    def test_corrupted_cache_fails_without_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            archive = cache / "release.zip"
            archive.write_bytes(b"corrupt")
            with (
                patch.multiple(dependency, CACHE=cache, CTAN_ARCHIVE=archive),
                patch.object(dependency.subprocess, "run") as download,
            ):
                with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                    dependency.ensure_release()
                download.assert_not_called()

    def test_verified_cached_release_needs_no_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = Path(tmp)
            archive = cache / "release.zip"
            core = cache / "pdfannex"
            cli = core / "scripts/pdfannex/pdfannex"
            with zipfile.ZipFile(archive, "w") as package:
                for name in ("pdfannex.sty", "scripts/pdfannex/pdfannex",
                             "scripts/pdfannex/pdfannex_latexmkrc"):
                    package.writestr(f"pdfannex/{name}", "fixture")
            with (
                patch.multiple(dependency, CACHE=cache, CTAN_ARCHIVE=archive,
                               TDS_ARCHIVE=cache / "pdfannex.tds.zip", CORE=core, CLI=cli),
                patch.object(dependency, "SHA256",
                             dependency.hashlib.sha256(archive.read_bytes()).hexdigest()),
                patch.object(dependency.subprocess, "run") as download,
            ):
                installed = dependency.ensure_release()
                download.assert_not_called()
                self.assertTrue(cli.is_file())
                with zipfile.ZipFile(installed) as package:
                    self.assertIn("tex/latex/pdfannex/pdfannex.sty", package.namelist())


if __name__ == "__main__":
    unittest.main()
