# Version 2 — Code-Driven GL-Account Master-Data Model in SAP Datasphere

Build a small GL-account master-data model in **SAP Datasphere entirely by code** — no manual work
in the Datasphere UI. From 4 source structures, it deploys **4 local tables** and **3 views**, all
exposed for consumption in **SAP Analytics Cloud (SAC)**.

Authentication is fully **headless**: an OAuth *client-credentials* service token (from `.env`) is
injected into the SAP Datasphere CLI, so every command runs non-interactively (no browser, no
passcode).

## What gets deployed

```
4 source CDS structures  →  4 local tables (empty, structure only)  →  3 views (dimensions)  →  SAC
```

| Object | Type | Operation |
|--------|------|-----------|
| `ZT2_GLACCOUNTINCOA` | local table | GL account master (keys: ChartOfAccounts, GLAccount) |
| `ZT2_GLACCOUNTTEXT` | local table | GL account text (adds Language, GLAccountName) |
| `ZT2_GLACCTHIERNODET` | local table | Hierarchy node text |
| `ZT2_GLACCTHIERNODE` | local table | Hierarchy node structure (parent/child) |
| `ZV2_GLACCOUNT_NAME` | view | **LEFT JOIN** master ⟕ text (Language = 'E') |
| `ZV2_GLACCTHIER_NODETEXT` | view | projection of node + text |
| `ZV2_GLACCTHIER_NODE` | view | projection of the hierarchy structure |

See [docs/DIAGRAM.md](docs/DIAGRAM.md) for the full flow diagrams.

## Repository layout

```
version-2/
├── README.md            ← you are here
├── deploy.py            ← one-command deploy (4 tables + 3 views, in order)
├── dsp_cli.py           ← headless wrapper around @sap/datasphere-cli
├── auth.py              ← mints the OAuth client-credentials token from .env
├── requirements.txt
├── .env.example         ← copy to .env and fill in your tenant details
├── csn/                 ← the 7 object definitions (CSN / Core Schema Notation JSON)
│   ├── ZT2_*.json       (4 local tables)
│   └── ZV2_*.json       (3 views)
└── docs/
    ├── PLAN.md          ← original design & decisions
    ├── PROGRESS_REPORT.md
    ├── DIAGRAM.md       ← Mermaid architecture diagrams
    └── md_to_docx.py    ← optional: render PROGRESS_REPORT.md → .docx
```

## Prerequisites

1. **Node + the SAP Datasphere CLI** (used under the hood):
   ```bash
   npm install -g @sap/datasphere-cli
   ```
2. **Python 3.9+** and the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. A Datasphere **OAuth client** (client-credentials) with access to your space.

## Setup — create your `.env`

This repo does **not** ship a `.env` (it holds secrets and is gitignored). You must create your own
before deploying. `deploy.py` / `auth.py` automatically load the file named **`.env` in this
`version-2/` folder** (the same folder as `deploy.py`).

```bash
cp .env.example .env      # then edit .env and fill in your own values
```

Fill in every value in `.env`:

| Variable | What it is |
|----------|-----------|
| `DSP_TOKEN_URL` | Your tenant's OAuth token endpoint (from the Datasphere OAuth client) |
| `DSP_CLIENT_ID` | OAuth client-credentials client ID |
| `DSP_CLIENT_SECRET` | OAuth client-credentials client secret |
| `DSP_BASE_URL` | Your Datasphere tenant base URL |
| `DSP_SPACE` | The space to deploy into |

> ⚠️ Never commit `.env` — it contains your client secret. It is already listed in `.gitignore`.
> The file must sit in this folder; a `.env` elsewhere (e.g. a parent project) will **not** be picked up.

## Deploy

```bash
python deploy.py            # create-or-update all 4 tables + 3 views
python deploy.py --verify   # then read each view back to confirm status
```

`deploy.py` is **idempotent**: for each object it checks whether it already exists in the space and
either **creates** it (first run / clean space) or **updates** it (syncs the tenant to the CSN
file). Safe to run repeatedly.

## Using the CLI wrapper directly

```bash
python dsp_cli.py list   views
python dsp_cli.py read   views ZV2_GLACCOUNT_NAME
python dsp_cli.py create local-tables --file csn/ZT2_GLACCOUNTINCOA.json
python dsp_cli.py delete views ZV2_GLACCOUNT_NAME
```

## Notes

- The 4 local tables are created **empty** (structure only). Consumption queries return 0 rows until
  data is loaded (CSV import, data/replication flows, etc.); the OData `$metadata` already publishes
  the full column structure to SAC.
- All objects are reversible via `delete`. Nothing destructive is performed on deploy.
