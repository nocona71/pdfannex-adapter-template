"""Integration test: plain files and fixture documents joined in one document.

Uses the pinned pdfannex release, downloaded and verified on first use.
Skipped if texlua, pdflatex, pdftotext or the pinned release's tools are
missing. Unlike a real network adapter's integration test, the fixture
resolver needs no test server: it reads `PDFANNEX_FIXTURE_ROOT` directly.
A real adapter's own integration test would instead start/stop its test
service here, as `pdfannex-docstore`'s `test_integration.py` does with an
in-process HTTP mock.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from core_dependency import CLI, CORE, ensure_release

HERE = Path(__file__).resolve().parent
TEX = CORE
NEEDS = all(shutil.which(t) for t in ("texlua", "pdflatex", "pdftotext"))

SRC = r"\documentclass{article}\pagestyle{empty}\begin{document}%s\end{document}"


def sh(cmd, cwd, check=True):
    env = {"PATH": os.environ["PATH"], "HOME": str(cwd),
           "TEXINPUTS": f"{TEX}:{HERE}:"}
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=check, env=env)


def pdf(cwd, name, word):
    (Path(cwd) / f"{name}.tex").write_text(SRC % word)
    sh(["pdflatex", "-interaction=batchmode", f"{name}.tex"], cwd)


def tex(cwd, check=True):
    # No -halt-on-error: the first build reports unresolved URIs but still records every request.
    return sh(["pdflatex", "-interaction=nonstopmode", "host.tex"], cwd, check=check)


def text(cwd):
    return sh(["pdftotext", "host.pdf", "-"], cwd).stdout


@unittest.skipUnless(shutil.which("pdflatex"), "pdflatex missing")
class AdapterStyleTest(unittest.TestCase):
    def test_older_core_without_source_command_fails_clearly(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "pdfannex.sty").write_text(
                r"\ProvidesPackage{pdfannex}[2025/01/01 v0.1.0]" + "\n\\endinput\n")
            (d / "check.tex").write_text(
                r"\documentclass{article}\usepackage{pdfannex-fixture}"
                r"\begin{document}x\end{document}")
            env = {"PATH": os.environ["PATH"], "HOME": str(d),
                   "TEXINPUTS": f"{d}:{HERE}:{TEX}:"}
            run = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "check.tex"],
                cwd=d, env=env, capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("pdfannex 0.2.0 or later is required", run.stdout + run.stderr)


DOC_HOST = r"""\documentclass{article}\usepackage{pdfannex-fixture}
\begin{document}
\includedoc[page-style=empty]{memo}{Memo}
\includeannex[page-style=empty]{pdfannex://fixture/memo?rev=1}{Old memo}
\includeannex[page-style=empty]{a.pdf}{Plain}
\end{document}
"""


@unittest.skipUnless(NEEDS, "TeX tools missing")
class PlainAndFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_release()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.store = self.d / "store" / "memo"
        self.store.mkdir(parents=True)
        for rev, word in ((1, "FIRST"), (2, "SECOND")):
            pdf(self.d, f"r{rev}", word)
            (self.d / f"r{rev}.pdf").rename(self.store / f"{rev}.pdf")
        pdf(self.d, "a", "ALPHA")
        (self.d / "host.tex").write_text(DOC_HOST)
        self.env = dict(os.environ, PATH=f"{HERE}:{os.environ['PATH']}",
                        PDFANNEX_FIXTURE_ROOT=str(self.d / "store"))
        self.run_cli("init")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        return subprocess.run(["texlua", str(CLI), *args], cwd=self.d, env=self.env,
                              capture_output=True, text=True)

    def build(self):
        tex(self.d, check=False)

    def test_alias_pins_revisions_and_detects_updates(self):
        self.build()
        self.assertEqual(self.run_cli("prepare", "host.tex").returncode, 0)
        lock = json.loads((self.d / "pdfannex.lock").read_text())
        self.assertEqual(lock["sources"]["pdfannex://fixture/memo"]["resolved"],
                         "pdfannex://fixture/memo?rev=2")
        # The plain file is locked by the CLI itself, with no adapter involved.
        self.assertIn("pdfannex://file/a.pdf", lock["sources"])
        # A new revision and removed originals must not change the build.
        pdf(self.d, "r3", "THIRD")
        (self.d / "r3.pdf").rename(self.store / "3.pdf")
        status = self.run_cli("status", "host.tex").stdout
        self.assertIn("update-available pdfannex://fixture/memo\n", status)
        self.assertIn("up-to-date", status)
        shutil.rmtree(self.store)
        (self.d / "a.pdf").unlink()
        for aux in ("host.aux", "host.pdf"):
            (self.d / aux).unlink(missing_ok=True)
        self.build()
        out = text(self.d)
        for word in ("SECOND", "FIRST", "ALPHA"):
            self.assertIn(word, out)
        self.assertLess(out.index("SECOND"), out.index("FIRST"))
        self.assertLess(out.index("FIRST"), out.index("ALPHA"))
        self.assertNotIn("THIRD", out)

    def test_tampered_revision_is_rejected_by_the_cli(self):
        self.build()
        self.run_cli("prepare", "host.tex")
        shutil.rmtree(self.d / ".pdfannex/objects")
        pdf(self.d, "evil", "EVIL")
        (self.d / "evil.pdf").replace(self.store / "2.pdf")
        run = self.run_cli("prepare", "host.tex")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("hash mismatch", run.stderr)

    def test_locked_build_needs_neither_resolver_nor_root(self):
        self.build()
        self.run_cli("prepare", "host.tex")
        shutil.rmtree(self.store)
        run = self.run_cli("prepare", "host.tex")
        self.assertEqual(run.returncode, 0, run.stderr)
        (self.d / "a.pdf").unlink()
        (self.d / "host.aux").unlink(missing_ok=True)
        self.build()
        self.assertIn("SECOND", text(self.d))

    def test_removed_root_reports_resource_not_found(self):
        self.build()
        self.run_cli("prepare", "host.tex")
        lock = (self.d / "pdfannex.lock").read_text()
        shutil.rmtree(self.d / ".pdfannex/objects")
        self.env["PDFANNEX_FIXTURE_ROOT"] = str(self.d / "does-not-exist")
        run = self.run_cli("update", "host.tex")
        self.assertIn("resource-not-found", run.stderr)
        self.assertEqual((self.d / "pdfannex.lock").read_text(), lock)

    def test_unknown_option_and_missing_document(self):
        for src in ("pdfannex://fixture/memo?x=1", "pdfannex://fixture/none"):
            (self.d / "host.pdfannex-requests").write_text(src.encode().hex().upper() + "\n")
            run = self.run_cli("prepare", "host.tex")
            self.assertNotEqual(run.returncode, 0, src)


if __name__ == "__main__":
    unittest.main()
