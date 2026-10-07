# Manual native TeX Live sanity check

Use the TDS release artifacts to install the core package and this fixture
adapter into your host TeX Live user's tree, then compile a custom document.
This is a persistent, unprivileged user-tree install, unlike `texlive_e2e.py`,
which uses an isolated temporary tree and TeX Live's package manager
(`tlmgr`) instead.

The artifacts are TDS ZIPs, not TeX Live package-manager containers. The
installer beside each ZIP writes into `TEXMFHOME`, records the installed paths,
and runs `mktexlsr`. It refuses to overwrite files already in the user tree.
If you previously extracted a TDS ZIP manually, remove or back up those old
package files first, or test in a clean separate user tree; the installer
cannot safely claim files that it did not install.

## Download the TDS artifacts

The core dependency is pinned to `pdfannex-v0.5.1`. This release supplies a
CTAN archive, not a separate TDS artifact. From this repository checkout,
use the checksum-verifying helper to assemble a TDS layout from the released
files. This adapter's own artifacts are attached to a release of this
repository; `gh` resolves "latest" automatically when no tag is given.

```bash
mkdir -p /tmp/pdfannex-artifacts/core /tmp/pdfannex-artifacts/fixture
make core-dependency
python3 - <<'PY'
import shutil
from core_dependency import TDS_ARCHIVE
shutil.copy2(TDS_ARCHIVE, "/tmp/pdfannex-artifacts/core/pdfannex.tds.zip")
shutil.copy2("scripts/install-texmfhome-tds.sh", "/tmp/pdfannex-artifacts/core/")
PY
gh release download --repo nocona71/pdfannex-adapter-template \
  --pattern '*.tds.zip' --pattern 'install-texmfhome-tds.sh' \
  --dir /tmp/pdfannex-artifacts/fixture
```

(A real adapter would publish its own releases under its own repository and
substitute that name above.)

## Install and uninstall

Install both TDS archives without `sudo`:

```bash
CORE="/tmp/pdfannex-artifacts/core"
FIXTURE="/tmp/pdfannex-artifacts/fixture"
bash "$CORE/install-texmfhome-tds.sh" install "$CORE"/pdfannex.tds.zip
bash "$FIXTURE/install-texmfhome-tds.sh" install "$FIXTURE"/pdfannex-fixture.tds.zip
kpsewhich pdfannex.sty
kpsewhich pdfannex-fixture.sty
kpsewhich -format=texmfscripts pdfannex_latexmkrc
```

The script defaults to the `TEXMFHOME` reported by `kpsewhich`. To use a
different user tree, pass it as the third argument to `install`. To remove the
packages later, use the matching script and archive name:

```bash
bash "$FIXTURE/install-texmfhome-tds.sh" uninstall "$FIXTURE"/pdfannex-fixture.tds.zip
bash "$CORE/install-texmfhome-tds.sh" uninstall "$CORE"/pdfannex.tds.zip
```

Uninstall removes only paths recorded for that archive; unrelated files and
non-empty directories are left in place. Uninstall the adapter before the core
package when removing both.

## Build a custom document

Create a directory for the fixture's documents and export the same
configuration in the shell that runs `latexmk` (a real network adapter would
instead require its service's own credentials/URL):

```bash
mkdir -p /tmp/fixture-store/memo
# a real PDF is required; this is just an example
cp some.pdf /tmp/fixture-store/memo/1.pdf
export PDFANNEX_FIXTURE_ROOT=/tmp/fixture-store
```

Enable the optional project-local latexmk integration as described in
[pdfannex's latexmk integration guide](https://github.com/nocona71/pdfannex/blob/main/docs/latexmk-integration.md).
Then run the normal single command:

```bash
latexmk -lualatex project.tex
```

The first run initializes the lock, resolves the local and fixture PDFs after
the discovery pass, and reruns LuaLaTeX until references converge. A
subsequent locked build uses the stored artifacts without reading
`PDFANNEX_FIXTURE_ROOT` again. This repository's [README](../README.md)
documents the fixture layout and resolver setup; `texlive_e2e.py` and
`test_package.py` automate an equivalent check end to end.
