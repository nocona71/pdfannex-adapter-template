"""Fetch the pinned core release used by adapter integration tests."""

import hashlib
from pathlib import Path
import subprocess
import tempfile
import zipfile

from e2e_ctan import install_archive

HERE = Path(__file__).resolve().parent
TAG = "pdfannex-v0.5.1"
ASSET = "pdfannex-ctan-v0.5.1.zip"
SHA256 = "2fac723fc71395347be83a8a7729888de1328abb0f5521225b8679619c0d89bf"
URL = f"https://github.com/nocona71/pdfannex/releases/download/{TAG}/{ASSET}"
CACHE = HERE / "build" / "dependencies" / TAG
CTAN_ARCHIVE = CACHE / ASSET
TDS_ARCHIVE = CACHE / "pdfannex.tds.zip"
CORE = CACHE / "pdfannex"
CLI = CORE / "scripts" / "pdfannex" / "pdfannex"


def verify_archive(path):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != SHA256:
        raise RuntimeError(f"SHA-256 mismatch for {path}: expected {SHA256}, got {digest}")


def tds_path(name):
    prefix = "pdfannex/"
    if not name.startswith(prefix):
        raise RuntimeError(f"unexpected core release member: {name}")
    relative = name[len(prefix):]
    if relative.startswith("scripts/pdfannex/"):
        return relative
    if relative == "pdfannex.sty":
        return f"tex/latex/pdfannex/{relative}"
    if relative == "pdfannex.1":
        return f"doc/man/man1/{relative}"
    return f"doc/latex/pdfannex/{relative}"


def ensure_release():
    CACHE.mkdir(parents=True, exist_ok=True)
    if not CTAN_ARCHIVE.is_file():
        with tempfile.TemporaryDirectory(dir=CACHE) as tmp:
            downloaded = Path(tmp) / ASSET
            subprocess.run(
                ["curl", "--fail", "--location", "--retry", "3",
                 "--output", str(downloaded), URL],
                check=True,
            )
            verify_archive(downloaded)
            downloaded.replace(CTAN_ARCHIVE)
    verify_archive(CTAN_ARCHIVE)
    install_archive(CTAN_ARCHIVE, CACHE)
    with zipfile.ZipFile(CTAN_ARCHIVE) as source:
        with zipfile.ZipFile(TDS_ARCHIVE, "w", zipfile.ZIP_DEFLATED) as target:
            for member in source.infolist():
                if member.is_dir():
                    continue
                installed = zipfile.ZipInfo(tds_path(member.filename))
                installed.external_attr = member.external_attr
                target.writestr(installed, source.read(member))
    for required in (CLI, CORE / "pdfannex.sty", CORE / "scripts/pdfannex/pdfannex_latexmkrc"):
        if not required.is_file():
            raise RuntimeError(f"required file missing from pinned release: {required}")
    return TDS_ARCHIVE


if __name__ == "__main__":
    ensure_release()
    print(f"Ready: {TAG} ({CTAN_ARCHIVE})")
