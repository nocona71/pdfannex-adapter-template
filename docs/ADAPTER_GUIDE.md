# Adapter Guide: starting a new adapter from this template

This repository is service-neutral scaffolding for building, testing,
packaging and releasing a `pdfannex` source adapter (Resolver Protocol 1). It
ships a minimal, runnable **fixture** adapter so the template itself is
testable end to end, not as an example of a production integration. Use this
guide to turn the fixture into your own adapter.

## What to rename

Pick a short, lowercase scheme name for your service (for example `s3`,
`sharepoint`, `my-service`) and a package name, conventionally
`pdfannex-<scheme>`. Then replace every occurrence of:

| Placeholder | Meaning | Appears in |
|---|---|---|
| `fixture` | the URI scheme (`pdfannex://fixture/...`) | resolver, `.sty`, tests, `build.lua`, workflows |
| `pdfannex-fixture` | the package/repository-facing name | `build.lua`, `Makefile`, `scripts/package`, workflow artifact and file names, `ctan/` |
| `PDFANNEX_FIXTURE_*` | environment variables read by the resolver | `pdfannex-resolver-fixture` |

A repository-wide case-sensitive search and replace of `fixture`/`Fixture`/
`FIXTURE` is a reasonable starting point; review each hit, since a few (this
guide, the top-level README's explanation of the template itself) should stay
generic or be rewritten for your service. A search and replace only rewrites
file *contents*; also rename the files that encode `fixture` in their own
name: `pdfannex-resolver-fixture`, `pdfannex-fixture.sty`, `test_fixture.py`,
and the files under `ctan/`. `test_fixture.py` in particular is invoked by
filename from the `Makefile`, so a forgotten rename there breaks `make test`
with a "No such file" error that's easy to mistake for something else.

## What to replace with real logic

Everything in `pdfannex-resolver-fixture` **above** the "Protocol plumbing"
marker is specific to the fixture's local-directory "service":

- `parse_source` — turn `pdfannex://<scheme>/<id>[?opt=value]` into whatever
  your service needs to look up a document. Keep returning `nil, code,
  message` for invalid input so the protocol-level error handling is unchanged.
- `fetch_latest` — ask your service for the latest revision identifier.
- `fetch_revision` — download/read one revision to a local file and return its
  path. Validate content you don't trust (the fixture only reads from a local
  path; `pdfannex-docstore`'s equivalent checks for a PDF signature after an
  HTTP download).

Everything below the marker (JSON request/response handling, protocol version
and batch handling, `describe`) is protocol plumbing most adapters can reuse
unchanged.

`adapter-lib.lua` (JSON, file and SHA-256 helpers) has no adapter-specific
code and can be copied as-is.

`conformance.py` is a generic, adapter-agnostic Resolver Protocol 1 checker
driven entirely by command-line arguments (executable, scheme, a source that
resolves, and one that doesn't); it needs no changes.

## Test harness

- `test_fixture.py` — module tests of the resolver alone (protocol plumbing,
  valid/invalid sources, missing documents, batches). A real adapter should
  add equivalent tests for its own service failure modes (authentication,
  timeouts, outages, tampering), following the structure of
  `pdfannex-docstore`'s `test_docstore.py` if your service is HTTP-based.
- `test_integration.py` — the pinned core CLI plus your resolver, building and
  locking a document that mixes plain files and adapter sources.
- `test_package.py` — builds the CTAN/TDS archives with `l3build` and
  installs them (both as a CTAN unpack and as a TDS tree) alongside the pinned
  core release, including a `latexmk` showcase build when `latexmk` is
  available.
- `test_core_dependency.py` — offline checks of the pinned core release
  pin/checksum/caching logic in `core_dependency.py`; this file is generic and
  normally does not need changes.
- `e2e_ctan.py`, `texlive_e2e.py` — used by CI (`ctan-e2e.yml`) to install the
  built CTAN/TDS archives into a clean container, the second via a local
  `tlmgr` repository mirroring a real CTAN install.

Because the fixture reads documents from a plain directory
(`PDFANNEX_FIXTURE_ROOT`), none of these harnesses need to start or stop a
test server. A real network-backed adapter should add one (see
`pdfannex-docstore`'s `docstore_server.py` for a worked HTTP example) and
wire its start/stop into the equivalent test files.

## Core dependency pin

`core_dependency.py` pins an exact released `pdfannex` version, CTAN asset
name and SHA-256 checksum, used by the integration/package/e2e tests and by
CI. It is already generic; update `TAG`, `ASSET` and `SHA256` together when
you want to test against a newer core release. Do not add a source checkout
or `PDFANNEX_HOME` dependency; adapters are released and tested against a
pinned core release, not a core working copy.

## Packaging, CI and releases

`build.lua`, `scripts/package` and `scripts/install-texmfhome-tds.sh` build
and install standalone CTAN/TDS archives once the renames above are done.
`.github/workflows/ci.yml`, `ctan-e2e.yml` and `ctan-release.yml` mirror the
core `pdfannex` repository's own release pipeline; update the artifact and
archive names to match your package name. `release-please.yml` plus
`.release-please-config.json`/`.release-please-manifest.json` drive
independent semantic-versioned releases of your adapter; set `package-name`
to your package.

## What this template deliberately does not include

- A mock network service. The fixture is local-filesystem based so the
  template has no third-party or docstore-specific service baked in.
  Add your own test double for your actual service.
- Any claim that this repository is a fork of, or the `nocona71/pdfannex` or
  `nocona71/pdfannex-docstore` monorepos' continuation. It is an independent,
  from-scratch template; see the top-level [README](../README.md) for how it
  relates to those projects.
