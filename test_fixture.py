#!/usr/bin/env python3
"""Module tests of the fixture skeleton adapter, independent of the pdfannex CLI.

The fixture resolver is a minimal, filesystem-backed stand-in for a real
service adapter (see `pdfannex-resolver-fixture`'s own docstring). These
tests cover what any adapter must get right before an integration test:
protocol plumbing (describe, protocol-version checks, malformed requests),
valid and invalid sources, missing documents/revisions, pinned revisions and
batches. A real adapter's equivalent module test would additionally exercise
its service's failure modes (authentication, outages, timeouts, tampering),
the way `pdfannex-docstore`'s `test_docstore.py` does against its mock HTTP
server; this template keeps those out of the generic skeleton.
"""

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from conformance import conform  # noqa: E402

ADAPTER = HERE / "pdfannex-resolver-fixture"
TEXLUA = shutil.which("texlua")
PDF = b"%PDF-1.4\n% fake but PDF-shaped\n"


def call(payload=None, raw=None, env=None):
    data = raw if raw is not None else json.dumps(payload)
    proc = subprocess.run([str(ADAPTER)], input=data, capture_output=True, text=True, env=env)
    out = json.loads(proc.stdout) if proc.stdout else None
    return proc, out


@unittest.skipUnless(TEXLUA, "texlua missing")
class FixtureAdapter(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.env = {"PATH": os.environ["PATH"], "PDFANNEX_FIXTURE_ROOT": str(self.root)}
        self._previous_root = os.environ.get("PDFANNEX_FIXTURE_ROOT")
        os.environ["PDFANNEX_FIXTURE_ROOT"] = str(self.root)

    def tearDown(self):
        if self._previous_root is None:
            os.environ.pop("PDFANNEX_FIXTURE_ROOT", None)
        else:
            os.environ["PDFANNEX_FIXTURE_ROOT"] = self._previous_root
        self.tmp.cleanup()

    def rev(self, doc, n, data):
        folder = self.root / doc
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{n}.pdf").write_bytes(data)

    def test_conformance(self):
        self.rev("memo", 1, PDF + b"one")
        conform(str(ADAPTER), "fixture", "pdfannex://fixture/memo", "pdfannex://fixture/missing")

    def test_describe_lists_the_scheme_and_capabilities(self):
        proc, out = call({"operation": "describe"}, env=self.env)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(out["schemes"], ["fixture"])
        self.assertIn("resolve", out["capabilities"])
        self.assertIn("status", out["capabilities"])

    def test_resolve_picks_the_latest_revision_without_rev(self):
        self.rev("memo", 1, PDF + b"one")
        self.rev("memo", 2, PDF + b"two")
        request = {"protocolVersion": 1, "operation": "resolve",
                   "requests": [{"id": "a", "source": "pdfannex://fixture/memo"}]}
        proc, out = call(request, env=self.env)
        self.assertEqual(proc.returncode, 0)
        result = out["results"][0]
        self.assertEqual(result["resolved"], "pdfannex://fixture/memo?rev=2")
        self.assertTrue(Path(result["artifact"]["path"]).is_file())

    def test_resolve_pins_an_explicit_revision(self):
        self.rev("memo", 1, PDF + b"one")
        self.rev("memo", 2, PDF + b"two")
        request = {"protocolVersion": 1, "operation": "resolve",
                   "requests": [{"id": "a", "source": "pdfannex://fixture/memo?rev=1"}]}
        proc, out = call(request, env=self.env)
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(out["results"][0]["resolved"], "pdfannex://fixture/memo?rev=1")

    def test_missing_document_and_revision_are_reported(self):
        self.rev("memo", 1, PDF)
        request = {"protocolVersion": 1, "operation": "resolve", "requests": [
            {"id": "a", "source": "pdfannex://fixture/missing"},
            {"id": "b", "source": "pdfannex://fixture/memo?rev=9"},
        ]}
        proc, out = call(request, env=self.env)
        self.assertEqual(proc.returncode, 0)
        results = {r["id"]: r for r in out["results"]}
        self.assertEqual(results["a"]["error"]["code"], "resource-not-found")
        self.assertEqual(results["b"]["error"]["code"], "resource-not-found")

    def test_invalid_source_and_unsupported_option_are_rejected(self):
        request = {"protocolVersion": 1, "operation": "resolve", "requests": [
            {"id": "a", "source": "pdfannex://fixture/../etc"},
            {"id": "b", "source": "pdfannex://fixture/memo?bogus=1"},
        ]}
        proc, out = call(request, env=self.env)
        self.assertEqual(proc.returncode, 0)
        results = {r["id"]: r for r in out["results"]}
        self.assertEqual(results["a"]["error"]["code"], "invalid-source")
        self.assertEqual(results["b"]["error"]["code"], "unsupported-source-option")

    def test_status_reports_up_to_date_and_update_available(self):
        self.rev("memo", 1, PDF + b"one")
        resolved = "pdfannex://fixture/memo?rev=1"
        lockedSha256 = hashlib.sha256(PDF + b"one").hexdigest()
        request = {"protocolVersion": 1, "operation": "status", "requests": [
            {"id": "a", "source": "pdfannex://fixture/memo", "resolved": resolved,
             "lockedSha256": lockedSha256}]}
        proc, out = call(request, env=self.env)
        self.assertEqual(out["results"][0]["state"], "up-to-date")

        self.rev("memo", 2, PDF + b"two")
        proc, out = call(request, env=self.env)
        self.assertEqual(out["results"][0]["state"], "update-available")

    def test_batch_requests_are_each_reported_independently(self):
        self.rev("memo", 1, PDF)
        request = {"protocolVersion": 1, "operation": "resolve", "requests": [
            {"id": "ok", "source": "pdfannex://fixture/memo"},
            {"id": "gone", "source": "pdfannex://fixture/missing"},
        ]}
        proc, out = call(request, env=self.env)
        self.assertEqual(proc.returncode, 0, "per-request failures must not fail the process")
        results = {r["id"]: r for r in out["results"]}
        self.assertIn("artifact", results["ok"])
        self.assertIn("error", results["gone"])

    def test_unsupported_protocol_version_is_refused(self):
        request = {"protocolVersion": 99, "operation": "resolve", "requests": []}
        proc, out = call(request, env=self.env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(out["error"]["code"], "unsupported-protocol")

    def test_malformed_json_is_reported(self):
        proc, out = call(raw="{not json", env=self.env)
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(out["error"]["code"], "malformed-request")
        self.assertEqual(proc.stdout.strip().count("\n"), 0,
                         "stdout must carry the protocol response only")


if __name__ == "__main__":
    unittest.main()
