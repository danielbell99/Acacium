# Acacium Board Paper Intelligence

An evidence-first interview prototype that extracts cautious workforce signals from selected public
NHS board-paper reports. Every candidate retains its original document, physical page and source
excerpt. The shortlist is a prioritisation aid, not evidence of a tender, purchase decision or current
commercial eligibility.

## Local run

```sh
conda activate acacium
just bootstrap
just down-all
just dev
```

Open `http://localhost:5173`. The API runs on loopback port `8000`; Vite proxies `/api` to it.
Port `1000` is reserved by this Mac's local policy and needs the planned administrator-installed
loopback proxy before it can become the public development address.

## Included local inputs

The ignored `data/documents/` directory contains the three preserved public board packs used for
the demonstration. Their filenames, hashes, source URLs and 105 declared physical pages in scope
are tracked in `config/source-manifest.json`. The editable Azure design diagram is versioned at
`docs/architecture/acacium-azure-solution-architecture.drawio`.

Original PDFs, derived runtime data, credentials and model artefacts are intentionally excluded from
Git. The front end only consumes the FastAPI API; it never reads the source PDFs directly.

## Quality checks

```sh
make qa
make test-integration
uv run pip-audit
just qa
```
