# pdfannex-fixture

A minimal, filesystem-backed reference adapter ("fixture") for the
`pdfannex` LaTeX package, built from
[pdfannex-adapter-template](https://github.com/nocona71/pdfannex-adapter-template).
It provides `\includedoc[options]{id}{title}` for including documents stored
as `<PDFANNEX_FIXTURE_ROOT>/<id>/<rev>.pdf`.

**This is a template skeleton, not a production adapter.** It exists so the
template repository is runnable and testable end to end. It does not
integrate with any real document-store product and has no network,
authentication or fault-injection logic. Start a new adapter by copying this
template and replacing the fixture's resolver logic (`parse_source`,
`fetch_latest`, `fetch_revision` in `pdfannex-resolver-fixture`) with calls
to your real service.

## Requirements

- `pdfannex` dated 2026/05/01 or later (version 0.2.0 or later).
- `texlua`, provided by TeX Live, to run the resolver.

## Installation and use

Install `pdfannex` and `pdfannex-fixture`. Make sure the TeX distribution
makes the `pdfannex-resolver-fixture` script available on `PATH`; otherwise
add its scripts directory.

```latex
\usepackage{pdfannex-fixture}
...
\includedoc[label=memo]{memo}{Project memo}
```

Set `PDFANNEX_FIXTURE_ROOT` to a directory containing `<id>/<rev>.pdf` files.
The resolver implements `pdfannex://fixture/<id>[?rev=<n>]`. Without `rev`,
it pins the latest revision during `prepare`.

For the protocol details and test harness, see the
[pdfannex-adapter-template repository](https://github.com/nocona71/pdfannex-adapter-template).

## License

This package is distributed under the LaTeX Project Public License 1.3c or
later. See `LICENSE`.
