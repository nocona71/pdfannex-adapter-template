# pdfannex-adapter-template

Service-neutral scaffolding for creating, testing, packaging and releasing a
[`pdfannex`](https://github.com/nocona71/pdfannex) source adapter (Resolver
Protocol 1). Use this as a GitHub template repository to start a new adapter:
click "Use this template" (or `gh repo create --template`), then follow
[`docs/ADAPTER_GUIDE.md`](docs/ADAPTER_GUIDE.md) to replace the bundled
fixture adapter with your own service's resolver logic.

This repository is independent, from-scratch scaffolding. It is not a GitHub
fork of, and does not claim to be a continuation of,
[`nocona71/pdfannex`](https://github.com/nocona71/pdfannex) or
[`nocona71/pdfannex-docstore`](https://github.com/nocona71/pdfannex-docstore).
`pdfannex-docstore` remains the first complete, independently released
reference adapter, with its own resolver, mock HTTP service, fixtures and
package identity; it keeps using its own packaging/CI/release setup rather
than depending on this template at runtime. Patterns and configuration shared
between the two repositories (devcontainer, protocol conformance checks,
CTAN/TDS packaging, the pinned-core-release dependency mechanism, CI and
Release Please workflows) were extracted and generalized here independently;
this repository has no build- or runtime dependency on either of them.

## What's in here

| Path | Purpose |
|---|---|
| `pdfannex-resolver-fixture` | **Skeleton adapter.** A texlua executable speaking Resolver Protocol 1, backed by a plain local directory instead of a real service. Not a production adapter — see below. |
| `adapter-lib.lua` | Minimal JSON, file and SHA-256 helpers (reusable, copy along with a new adapter) |
| `pdfannex-fixture.sty` | Companion LaTeX package registering the fixture source with `pdfannex` |
| `conformance.py` | Generic Resolver Protocol 1 conformance check for any resolver executable |
| `test_fixture.py` | Module tests of the fixture resolver alone (`make test`) |
| `test_integration.py` | Plain files and fixture documents in one document, built with the pinned released `pdfannex` package and CLI |
| `core_dependency.py` | Pinned core release, SHA-256 verification, download cache and CTAN-to-TDS layout (generic; no adapter-specific code) |
| `test_package.py` | CTAN/TDS archive checks and isolated TDS/CTAN install, locked-build tests (`make test-fast`) |
| `e2e_ctan.py`, `texlive_e2e.py` | End-to-end install tests for the released core and built adapter CTAN/TDS archives, the latter via a local `tlmgr` repository |
| `build.lua`, `ctan/` | Standalone `l3build` configuration and user-facing package docs |
| `.devcontainer/` | Development container with TeX Live, Python, shellcheck and `actionlint` |
| `.github/actions/test/action.yml` | Composite test action invoked by this repo's own CI |
| `.github/workflows/` | CI (unit tests, packaging, install/e2e), independent Release Please versioning, and CTAN/TDS release workflows |
| `docs/ADAPTER_GUIDE.md` | What to rename and replace when starting a new adapter from this template |
| `docs/manual-native-texlive-sanity-check.md` | Manual, persistent-user-tree install walkthrough |

## The fixture adapter is a skeleton, not a real service integration

`pdfannex-resolver-fixture` resolves `pdfannex://fixture/<id>[?rev=<n>]`
sources from a plain directory tree
(`$PDFANNEX_FIXTURE_ROOT/<id>/<rev>.pdf`), configured by the single
environment variable `PDFANNEX_FIXTURE_ROOT`. It exists so this template is
runnable and testable with no third-party dependency: `make test` exercises
the protocol, an integration build against the pinned core release, and the
CTAN/TDS packaging, all without a mock server or network service. It is
**not** a production adapter: it has no authentication, network access or
fault injection. If you need a worked example of an HTTP-backed adapter with
those concerns, see
[`pdfannex-docstore`](https://github.com/nocona71/pdfannex-docstore).

## Getting started with a new adapter

1. Create a new repository from this template.
2. Read [`docs/ADAPTER_GUIDE.md`](docs/ADAPTER_GUIDE.md) and rename
   `fixture`/`pdfannex-fixture`/`PDFANNEX_FIXTURE_*` throughout to your
   service's scheme and package name.
3. Replace the local-directory logic in `pdfannex-resolver-fixture`
   (`parse_source`, `fetch_latest`, `fetch_revision`) with calls to your real
   service; keep the protocol plumbing below the marker in that file.
4. Add your own test double for your service and extend `test_fixture.py`,
   `test_integration.py`, `test_package.py` with its failure modes, following
   `pdfannex-docstore` as a reference if your service is HTTP-based.
5. Run `make test` (needs the tools listed in `.github/workflows/ci.yml` /
   the devcontainer) and `make package` before your first release.

## Requirements

`texlua` (TeX Live) to run the resolver and conformance checks. Python 3 for
the test suite. `l3build` to build the CTAN/TDS archives
(`make package`/`test_package.py`). `shellcheck` lints the shell scripts as
part of `make test`. The devcontainer installs all of these plus `latexmk`,
`poppler-utils` and `actionlint`.

Integration/e2e tests use a pinned released core package, not a source
checkout of `pdfannex` — see `core_dependency.py`. The release tag, CTAN
asset name and SHA-256 checksum are pinned there; update all three together
when bumping the test dependency. No core checkout or `PDFANNEX_HOME` is
needed. The release is cached under `build/dependencies/`; the first run
needs public GitHub access, but subsequent runs use the verified cache.
Download or checksum errors fail the tests rather than silently skipping
them.

Run `make test-fast` for the quicker package/core-dependency checks (always
includes the adapter-archive checks when `l3build` is available, and the
installed-package/locked-rebuild checks when the full TeX/curl toolchain is
present too). Run `make test` for the full suite, including module and
integration tests and `shellcheck`.

## Packaging and release

Build the CTAN/TDS package with `make package`. The CTAN archive is
`pdfannex-fixture-ctan.zip`; the TDS archive is
`build/distrib/tds/pdfannex-fixture.tds.zip`, alongside the generic
`scripts/install-texmfhome-tds.sh` installer. `.github/workflows/ci.yml` runs
`make test`, builds both archives and runs `ctan-e2e.yml` against them.
`.github/workflows/release-please.yml` drives independent, semantic-versioned
releases (configured in `.release-please-config.json` /
`.release-please-manifest.json`); a successful release triggers
`ctan-release.yml` to attach versioned archives to the GitHub release, then
`ctan-e2e.yml` again against the published release.

## License

Distributed under the LaTeX Project Public License 1.3c or later; see
[`LICENSE`](LICENSE). This template was extracted from and inspired by
[`nocona71/pdfannex-docstore`](https://github.com/nocona71/pdfannex-docstore)
(itself extracted from `nocona71/pdfannex`); see that repository's history
for original authorship of the patterns generalized here.
