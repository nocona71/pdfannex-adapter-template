#!/usr/bin/env python3
"""Conformance checks for a Resolver Protocol 1 executable (spec/08).

usage: conformance.py EXECUTABLE SCHEME GOOD_SOURCE MISSING_SOURCE

Run with the working directory set to a project where GOOD_SOURCE resolves to a
readable file and MISSING_SOURCE does not exist.
"""

import json
import subprocess
import sys


def call(exe, payload, raw=None):
    data = raw if raw is not None else json.dumps(payload)
    proc = subprocess.run([exe], input=data, capture_output=True, text=True)
    return proc, json.loads(proc.stdout)


def check(cond, message):
    if not cond:
        raise AssertionError(message)


def conform(exe, scheme, good, missing):
    proc, out = call(exe, {"operation": "describe"})
    check(proc.returncode == 0, "describe must exit 0")
    check(1 in out["protocolVersions"], "describe must list protocol version 1")
    check(scheme in out["schemes"], "describe must list the handled scheme")
    check("resolve" in out["capabilities"], "resolve capability is mandatory")

    request = {"protocolVersion": 1, "operation": "resolve", "requests": [
        {"id": "ok", "source": good}, {"id": "gone", "source": missing}]}
    proc, out = call(exe, request)
    check(proc.returncode == 0, "per-request failures must not fail the process")
    results = {r["id"]: r for r in out["results"]}
    check("path" in results["ok"]["artifact"], "success needs artifact.path")
    check("resolved" in results["ok"], "success needs a resolved locator")
    check(results["gone"]["error"]["code"] == "resource-not-found", "missing resource")

    request["protocolVersion"] = 99
    proc, out = call(exe, request)
    check(proc.returncode != 0 and out["error"]["code"] == "unsupported-protocol",
          "unknown protocol version must be refused")

    proc, out = call(exe, None, raw="{not json")
    check(proc.returncode != 0 and out["error"]["code"] == "malformed-request",
          "malformed JSON must be reported as malformed-request")
    check(proc.stdout.strip().count("\n") == 0, "stdout carries the protocol response only")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    conform(*sys.argv[1:])
    print("conformance ok")
