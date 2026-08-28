# Version 2 Plan — 4 source tables → 3 consumption-ready views

## Goal (as I understand the diagram)

Build, **entirely by code** (headless CLI + `.env` client-credentials token, no UI), a small
model in SAP Datasphere consisting of:

- **4 empty local tables** — one per source CDS view, holding *structure only* (column names +
  types, **no data**). Column sets based on the *normal* columns those standard S/4 CDS views have,
  with emphasis on the fields called out in the diagram's FIELDS column.
- **3 views** built on top of those tables, applying the operations drawn in the diagram, each
  **exposed for consumption** so SAP Analytics Cloud (SAC) can consume them.

Everything reuses the proven pipeline from v1: `project/dsp_cli.py` →
`objects local-tables create` and `objects views create`, token injected via `ACCESS_TOKEN`.

---

## The 4 source CDS → 4 empty local tables

| # | Source CDS view              | Role                                  |
|---|------------------------------|---------------------------------------|
| 1 | `I_GLAccountInChartOfAccounts` | GL account master (COA + GL account)  |
| 2 | `I_GLAccountText` / `I_GLAccountTextRawData` | GL account name/text (language-dependent) |
| 3 | `I_GLAccountHierarchyNodeT`  | Hierarchy node **text**               |
| 4 | `I_GLAccountHierarchyNode`   | Hierarchy node **structure** (parent/child) |

I will research (in progress) the real technical column names & types for each, then create a
local table per source. **Empty = structure only, zero rows.** (These stand in for what would
normally be replicated/remote tables from S/4.)

---

## The 3 views (operations from the diagram)

**View 1 — GL Account + Name (LEFT JOIN)**
- Diagram SQL: `select A.GLAccount, A.ChartOfAccounts, B.GLAccountName from I_GLAccountInChartOfAccounts as A LEFT JOIN I_GLAccountTextRawData as B on A.GLAccount = B.GLAccount`
- Interpretation: **LEFT JOIN** master (table 1, A) to text (table 2, B) so every GL account keeps
  its row even when no text exists; project **ChartOfAccounts, GLAccount, GLAccountName**.
- Note on join key (see clarifying Q2): text is normally keyed on **ChartOfAccounts + GLAccount +
  Language**, so a correct join usually needs COA in the `on` and a **Language filter** — otherwise
  you get row multiplication (one row per language). The diagram shows only `GLAccount = GLAccount`.

**View 2 — Hierarchy node text (projection)**
- `select HierarchyNode, HierarchyNodeText from I_GLAccountHierarchyNodeT`
- Straight projection of the node + its text.

**View 3 — Hierarchy node structure (projection)**
- `select ParentNode, GLAccountHierarchy, NodeType, NodeValue from I_GLAccountHierarchyNode`
- Straight projection of the parent/child hierarchy columns. ("hierarchy name" in the diagram =
  `GLAccountHierarchy`.)

---

## How each object is defined (CSN)

- **Local table** CSN: `{"definitions":{"<NAME>":{"kind":"entity","elements":{...keys+cols...}}}}`
  (no `query` block — it's a persisted table).
- **View** CSN: same as v1's proven shape — `kind:"entity"`, `elements`, a `query.SELECT`
  (`from`/`join`/`on`/`columns`), plus consumption/semantic annotations:
  - `@EndUserText.label`
  - `@DataWarehouse.consumption.external: true`  ← makes it visible to SAC/consumption API
  - `@ObjectModel.modelingPattern: {"#":"ANALYTICAL_DIMENSION"}` for the master/text views
    (dimension-style), so SAC treats them as dimensions.

---

## Execution steps

1. **Finalize columns** from CDS research (agent running now).
2. Write CSN JSON files under `version 2/` (4 table files + 3 view files).
3. `dsp_cli.py create local-tables` ×4  →  verify with `list` / `read`.
4. `dsp_cli.py create views` ×3 (in dependency order; View 1 needs tables 1 & 2)  →  verify.
5. Confirm each view is consumption-exposed (query the relational consumption OData endpoint like
   we did for `ZVDM_TGLACCOUNT`), so it's ready for SAC.
6. All objects reversible (`delete`) — nothing destructive.

---

## Decisions (confirmed)

1. **Table column scope** → **Lean**: keys + the fields the 3 views actually use.
2. **View 1 join** → **Correct join**: on `ChartOfAccounts + GLAccount` with a **Language filter**
   (e.g. `E`/`EN`) to avoid per-language row multiplication.
3. **Space & naming** → same space **`HIERARCHY_AUTOMATION`**; tables prefixed **`ZT2_*`**, views
   prefixed **`ZV2_*`**.
4. **Consumption for SAC** → **expose the 3 views as dimensions** (`@DataWarehouse.consumption.external`
   + `ANALYTICAL_DIMENSION` pattern). No analytic model / external hierarchy for now.

### Proposed technical names

| Object | Technical name |
|--------|----------------|
| Table 1 (GL acct in COA) | `ZT2_GLACCOUNTINCOA` |
| Table 2 (GL acct text)   | `ZT2_GLACCOUNTTEXT` |
| Table 3 (hier node text) | `ZT2_GLACCTHIERNODET` |
| Table 4 (hier node)      | `ZT2_GLACCTHIERNODE` |
| View 1 (GL acct + name)  | `ZV2_GLACCOUNT_NAME` |
| View 2 (hier node text)  | `ZV2_GLACCTHIER_NODETEXT` |
| View 3 (hier node struct)| `ZV2_GLACCTHIER_NODE` |

---

## RESULT — ✅ built & verified (2026-08-28)

All objects created headlessly via `project/dsp_cli.py` in space `HIERARCHY_AUTOMATION`; CSN files
live in `version 2/csn/`.

| Object | Type | Status | SAC-exposed |
|--------|------|--------|-------------|
| `ZT2_GLACCOUNTINCOA` | local table | Deployed | — (source) |
| `ZT2_GLACCOUNTTEXT` | local table | Deployed | — (source) |
| `ZT2_GLACCTHIERNODET` | local table | Deployed | — (source) |
| `ZT2_GLACCTHIERNODE` | local table | Deployed | — (source) |
| `ZV2_GLACCOUNT_NAME` | view (LEFT JOIN) | Deployed | ✅ catalog + `$metadata` 200 |
| `ZV2_GLACCTHIER_NODETEXT` | view (projection) | Deployed | ✅ catalog + `$metadata` 200 |
| `ZV2_GLACCTHIER_NODE` | view (projection) | Deployed | ✅ catalog + `$metadata` 200 |

Notes:
- Tables are **empty** (structure only) as requested, so consumption queries return 0 rows until
  data is loaded; `$metadata` already exposes all columns to SAC.
- Fixed a blocker first: the CLI had a **stale cached token** (`~/.@sap/datasphere-cli/.cache/secrets.json`)
  causing every command to fail with a 401 on `config cache init`; backed it up so the CLI re-mints
  from our `ACCESS_TOKEN` env. (Documented in memory.)
- Everything is reversible via `dsp_cli.py delete`.
