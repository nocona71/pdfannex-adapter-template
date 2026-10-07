"""End-to-end test of installed core and fixture CTAN archives."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PDF_SOURCE = r"\documentclass{article}\pagestyle{empty}\begin{document}%s\end{document}"
HOST_SOURCE = r"""\documentclass{article}\usepackage{pdfannex-fixture}
\begin{document}
\includedoc[page-style=empty]{memo}{Memo}
\includeannex[page-style=empty]{plain.pdf}{Plain}
\end{document}
"""


def run(command, cwd, env, check=True):
    return subprocess.run(
        command, cwd=cwd, env=env, capture_output=True, text=True, check=check
    )


def make_pdf(work, name, text, env):
    (work / f"{name}.tex").write_text(PDF_SOURCE % text, encoding="utf-8")
    run(["pdflatex", "-interaction=batchmode", f"{name}.tex"], work, env)


def install_archive(archive, destination):
    destination.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive) as package:
        for member in package.infolist():
            target = (destination / member.filename).resolve()
            if destination.resolve() not in target.parents:
                raise RuntimeError(f"archive member escapes its destination: {member.filename}")
        package.extractall(destination)


def exercise(core_archive, adapter_archive):
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        home = work / "home"
        texmf = home / "texmf"
        bindir = work / "bin"
        unpacked = work / "archives"
        home.mkdir()
        bindir.mkdir()
        install_archive(core_archive, unpacked)
        install_archive(adapter_archive, unpacked)

        core = unpacked / "pdfannex"
        adapter = unpacked / "pdfannex-fixture"
        for source, relative in (
            (core / "pdfannex.sty", "tex/latex/pdfannex/pdfannex.sty"),
            (adapter / "pdfannex-fixture.sty",
             "tex/latex/pdfannex-fixture/pdfannex-fixture.sty"),
            (adapter / "pdfannex-resolver-fixture",
             "scripts/pdfannex-fixture/pdfannex-resolver-fixture"),
            (adapter / "adapter-lib.lua", "scripts/pdfannex-fixture/adapter-lib.lua"),
        ):
            target = texmf / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

        core_scripts = texmf / "scripts/pdfannex"
        core_scripts.mkdir(parents=True, exist_ok=True)
        for script in (core / "scripts/pdfannex").iterdir():
            shutil.copy2(script, core_scripts / script.name)

        cli = core_scripts / "pdfannex"
        resolver = texmf / "scripts/pdfannex-fixture/pdfannex-resolver-fixture"
        for script in (cli, resolver):
            script.chmod(script.stat().st_mode | 0o111)
            (bindir / script.name).symlink_to(script)

        env = dict(
            os.environ,
            HOME=str(home),
            TEXMFHOME=str(texmf),
            TEXMFVAR=str(home / "texmf-var"),
            TEXMFCONFIG=str(home / "texmf-config"),
            PATH=f"{bindir}:{os.environ['PATH']}",
        )
        env.pop("TEXINPUTS", None)
        for name, path in (
            ("pdfannex.sty", texmf / "tex/latex/pdfannex/pdfannex.sty"),
            ("pdfannex-fixture.sty",
             texmf / "tex/latex/pdfannex-fixture/pdfannex-fixture.sty"),
        ):
            found = run(["kpsewhich", name], work, env).stdout.strip()
            if found != str(path):
                raise RuntimeError(f"{name} resolved to {found!r}, expected {str(path)!r}")

        store = work / "store/memo"
        store.mkdir(parents=True)
        make_pdf(work, "rev1", "FIRST", env)
        (work / "rev1.pdf").rename(store / "1.pdf")
        make_pdf(work, "rev2", "LATEST", env)
        (work / "rev2.pdf").rename(store / "2.pdf")
        make_pdf(work, "plain", "ALPHA", env)
        (work / "host.tex").write_text(HOST_SOURCE, encoding="utf-8")

        # The fixture resolver reads documents directly from this directory;
        # a real adapter would instead point at a running test service.
        env["PDFANNEX_FIXTURE_ROOT"] = str(work / "store")
        run([str(bindir / "pdfannex"), "init"], work, env)
        run(["pdflatex", "-interaction=nonstopmode", "host.tex"], work, env, check=False)
        prepared = run([str(bindir / "pdfannex"), "prepare", "host.tex"], work, env)
        if prepared.returncode:
            raise RuntimeError(prepared.stderr)
        lock = json.loads((work / "pdfannex.lock").read_text(encoding="utf-8"))
        if lock["sources"]["pdfannex://fixture/memo"]["resolved"] != (
            "pdfannex://fixture/memo?rev=2"
        ):
            raise RuntimeError("adapter did not lock the latest document revision")
        if "pdfannex://file/plain.pdf" not in lock["sources"]:
            raise RuntimeError("CLI did not lock the local PDF source")

        shutil.rmtree(work / "store")
        (work / "plain.pdf").unlink()
        (work / "host.aux").unlink(missing_ok=True)
        (work / "host.pdf").unlink(missing_ok=True)
        run(["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "host.tex"], work, env)
        run([str(bindir / "pdfannex"), "verify", "host.tex"], work, env)
        text = run(["pdftotext", "host.pdf", "-"], work, env).stdout
        for expected in ("LATEST", "ALPHA"):
            if expected not in text:
                raise RuntimeError(f"locked rebuild output is missing {expected!r}")


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: e2e_ctan.py <pdfannex-ctan.zip> <pdfannex-fixture-ctan.zip>")
    exercise(Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve())
    print("OK: core and fixture CTAN archives pass the installed locked-build test")


if __name__ == "__main__":
    main()
