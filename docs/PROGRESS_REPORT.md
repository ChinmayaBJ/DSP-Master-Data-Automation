# Version 2 — Code-Driven Master Data Model in SAP Datasphere

**Project:** Master Data AI Agent
**Space:** `HIERARCHY_AUTOMATION`
**Tenant:** `https://sdc-analytics-dwc.ap11.hcs.cloud.sap`
**Date:** 2026-08-28
**Status:** ✅ Complete & verified

---

## 1. Executive Summary

We built a small GL-Account master-data model in SAP Datasphere **entirely through code** — no
manual work in the Datasphere UI. Starting from a hand-drawn design (4 source structures → 3
consumption views), we programmatically created **4 local tables** and **3 views** and confirmed all
three views are **exposed for consumption in SAP Analytics Cloud (SAC)**.

The exercise proves that the full modeling lifecycle (define tables → build views with joins and
projections → expose for BI consumption) can be automated and version-controlled, using only an
OAuth service credential and the SAP Datasphere CLI. This is the foundation the "Master Data AI
Agent" needs: the agent can generate and deploy Datasphere objects without a human operating the UI.

---

## 2. Problem Statement

**Initial ask (from the design diagram):**

> Take 4 source CDS structures, create *empty* tables for each (columns only, no data), then apply
> the operations shown in the diagram to end with **3 views in Datasphere, ready for consumption in
> SAC**. Do it by code, avoid the UI.

The design specified:

| # | Source structure | Purpose |
|---|------------------|---------|
| 1 | `I_GLAccountInChartOfAccounts` | GL account master (Chart of Accounts + GL Account) |
| 2 | `I_GLAccountText` | GL account name / description (language-dependent) |
| 3 | `I_GLAccountHierarchyNodeT` | Hierarchy node **text** |
| 4 | `I_GLAccountHierarchyNode` | Hierarchy node **structure** (parent/child) |

And three target views:

| View | Operation | Output |
|------|-----------|--------|
| GL Account with Name | **LEFT JOIN** master ⟕ text | ChartOfAccounts, GLAccount, GLAccountName |
| Hierarchy Node Text | projection | HierarchyNode, HierarchyNodeText |
| Hierarchy Node | projection | GLAccountHierarchy, ParentNode, NodeType, NodeValue |

**Underlying business goal:** demonstrate that Datasphere master-data objects can be built,
modified, and exposed for analytics *programmatically*, so the process is repeatable, auditable, and
automatable by the AI agent.

---

## 3. Approach & Methods

### 3.1 Headless (no-UI, no-passcode) tooling

All objects were created with the official **`@sap/datasphere-cli`**, driven from Python
([dsp_cli.py](../dsp_cli.py)). Authentication uses the project's existing **OAuth
client-credentials** service token (from `.env`), injected into the CLI via the `ACCESS_TOKEN`
environment variable — so every command runs non-interactively (no browser, no passcode). The token
is passed transiently in memory and never written to disk.

> **Why the CLI and not the REST API?** Datasphere's consumption/catalog REST API is **read-only**.
> The supported *write* path for modeling objects is the CLI's `objects <kind> create|update|read|
> list|delete` commands. This was established and proven in v1 of the project.

### 3.2 "Read-as-template" for correctness

Rather than guessing the required object definition (CSN — Core Schema Notation) format, we **read an
existing, working object from the live tenant** and used its exact structure as the template:

- Read an existing local table → confirmed the table CSN shape.
- Read the existing working dimension view (`ZVDM_TGLACCOUNT`, already consumed by SAC) → copied its
  exact "dimension" annotations so our new views would be SAC-consumable in the same way.

This eliminates trial-and-error and guarantees the definitions match what the tenant accepts.

### 3.3 Design decisions (agreed before building)

| Decision | Choice made | Rationale |
|----------|-------------|-----------|
| Table column scope | **Lean** — keys + only the fields the views use | Source tables are structural stand-ins; no need for the full S/4 column set |
| Join semantics (View 1) | Join on **ChartOfAccounts + GLAccount** with a **Language filter** (`'E'`) in the ON clause | Text is language-dependent; correct keys + left-join semantics avoid duplicate/way-off rows |
| Naming & space | Same space `HIERARCHY_AUTOMATION`; tables `ZT2_*`, views `ZV2_*` | Keeps v2 objects grouped and distinct from v1 |
| Consumption modeling | Expose the 3 views as **dimensions** (`ANALYTICAL_DIMENSION` + consumption flag) | These are master/text/hierarchy data (no measures); dimensions are the right SAC pattern |

### 3.4 Source-column research

The four sources are standard SAP S/4HANA CDS views. Their standard columns were researched
(master/text views map cleanly to tables SKA1/SKAT; hierarchy element names are pattern-based and
flagged as assumptions — see §7). Because scope was "lean", only the keys and view-referenced fields
were modeled.

### 3.5 Build sequence

1. Author 7 CSN JSON definition files (4 tables + 3 views) under `version 2/csn/`.
2. Create the 4 local tables (`objects local-tables create`).
3. Create the 3 views (`objects views create`) — join view first depends on tables 1 & 2.
4. Verify deployment status and SAC consumption exposure.

All operations are **reversible** (`delete`); nothing destructive was performed.

---

## 4. What Was Built

CSN definition files live in [csn/](../csn/).

**Local tables (empty — structure only):**

| Technical name | Label | Columns (keys in **bold**) |
|----------------|-------|----------------------------|
| `ZT2_GLACCOUNTINCOA` | GL Account in Chart of Accounts (source) | **ChartOfAccounts**, **GLAccount** |
| `ZT2_GLACCOUNTTEXT` | GL Account Text (source) | **ChartOfAccounts**, **GLAccount**, **Language**, GLAccountName |
| `ZT2_GLACCTHIERNODET` | GL Account Hierarchy Node Text (source) | **GLAccountHierarchy**, **HierarchyNode**, **Language**, HierarchyNodeText |
| `ZT2_GLACCTHIERNODE` | GL Account Hierarchy Node (source) | **GLAccountHierarchy**, **HierarchyNode**, ParentNode, NodeType, NodeValue |

**Views (dimensions, exposed for consumption):**

| Technical name | Label | Operation | Output columns |
|----------------|-------|-----------|----------------|
| `ZV2_GLACCOUNT_NAME` | GL Account with Name | **LEFT JOIN** `ZT2_GLACCOUNTINCOA` ⟕ `ZT2_GLACCOUNTTEXT` on ChartOfAccounts + GLAccount, Language = 'E' | ChartOfAccounts, GLAccount, GLAccountName |
| `ZV2_GLACCTHIER_NODETEXT` | GL Account Hierarchy Node Text | projection from `ZT2_GLACCTHIERNODET` | HierarchyNode, HierarchyNodeText |
| `ZV2_GLACCTHIER_NODE` | GL Account Hierarchy Node | projection from `ZT2_GLACCTHIERNODE` | GLAccountHierarchy, ParentNode, NodeType, NodeValue |

**Generated SQL of the join view (as rendered by Datasphere):**

```sql
SELECT
    A."ChartOfAccounts",
    A."GLAccount",
    B."GLAccountName"
FROM "ZT2_GLACCOUNTINCOA" AS A
LEFT JOIN "ZT2_GLACCOUNTTEXT" AS B
    ON  A."ChartOfAccounts" = B."ChartOfAccounts"
    AND A."GLAccount"       = B."GLAccount"
    AND B."Language"        = 'E';
```

---

## 5. Results & Verification

Every object was verified against the live tenant after creation:

| Object | Type | Deploy status | In SAC consumption catalog | `$metadata` (OData schema) |
|--------|------|---------------|----------------------------|-----------------------------|
| `ZT2_GLACCOUNTINCOA` | local table | ✅ Deployed | — (source) | — |
| `ZT2_GLACCOUNTTEXT` | local table | ✅ Deployed | — (source) | — |
| `ZT2_GLACCTHIERNODET` | local table | ✅ Deployed | — (source) | — |
| `ZT2_GLACCTHIERNODE` | local table | ✅ Deployed | — (source) | — |
| `ZV2_GLACCOUNT_NAME` | view (JOIN) | ✅ Deployed | ✅ Yes | ✅ 200 |
| `ZV2_GLACCTHIER_NODETEXT` | view | ✅ Deployed | ✅ Yes | ✅ 200 |
| `ZV2_GLACCTHIER_NODE` | view | ✅ Deployed | ✅ Yes | ✅ 200 |

**Interpretation:** all 7 objects deployed successfully; all 3 views are visible in the Datasphere
Data Builder and are **ready to be added as data sources / dimensions in SAC**. Because the source
tables are intentionally empty, consumption queries currently return 0 rows — but the OData
`$metadata` already publishes the full column structure to SAC, which is the "consumption-ready"
milestone requested.

---

## 6. Key Technical Challenge Solved

Midway, **every CLI command started failing** (`config cache init` returned HTTP 401 on the
`dwaas-core/api/v1/discovery` endpoint; list/read/create failed with generic errors).

**Root cause:** the CLI keeps a local credential cache
(`~/.@sap/datasphere-cli/.cache/secrets.json`) containing a short-lived access token. Once that
cached token expired, the CLI ignored our fresh environment token and instead tried to *refresh* the
stale one — but no refresh token existed, so it failed.

**Diagnosis:** we confirmed the OAuth service token itself was still valid by calling the same
endpoints directly over REST (all returned HTTP 200). Since REST worked but the CLI did not, the
fault was isolated to the CLI's stale cache.

**Fix:** move the stale cache file aside (backed up, not read/exposed) so the CLI re-mints from our
current environment token, then re-run `config cache init`. All commands worked immediately after.
This fix is documented in the project's knowledge base for the future.

---

## 7. Assumptions & Limitations

- **Empty tables by design.** The 4 source tables hold structure only (no data). Downstream views
  therefore return no rows until data is loaded (via replication/data flows or an import).
- **Hierarchy field names are inferred.** The GL master and text views map cleanly to SAP standard
  tables (SKA1 / SKAT), so those columns are high-confidence. The hierarchy views'
  element names (`GLAccountHierarchy`, `ParentNode`, `NodeType`, `NodeValue`) are pattern-based
  inferences from the SAP reuse-hierarchy framework and should be confirmed against the live S/4
  system if these tables will later be fed from real sources.
- **Language filter value.** The join uses `Language = 'E'` (SAP internal single-char key). If the
  eventual source uses ISO `'EN'` or another convention, this one predicate should be updated.
- **No graphical layout authored.** Code-created views have no saved canvas diagram; they open and
  function normally in the Data Builder (SQL view), which is expected for a code-first workflow.
- **Not modeled (out of current scope):** analytic models (fact/measure cubes), a formal external
  parent-child SAC hierarchy on the hierarchy view, and source-system connections/data loading.

---

## 8. Reproducibility

Everything is file-based and repeatable:

- Object definitions: [csn/](../csn/) (7 JSON files, version-controllable).
- Deployment tool: [dsp_cli.py](../dsp_cli.py) (headless CLI wrapper) + [deploy.py](../deploy.py) (one-command deploy).
- Auth: OAuth client-credentials from `.env` (no interactive login).

To recreate the model in a clean space, run the create commands for the 4 tables then the 3 views
(join view after its two tables). To tear down, run the equivalent `delete` commands.

---

## 9. Business Value / Why This Matters

- **Automatable:** the Master Data AI Agent can now generate and deploy Datasphere models
  end-to-end without a human in the UI.
- **Auditable & versioned:** object definitions are plain JSON in source control — reviewable and
  diff-able like code.
- **Repeatable across environments:** the same definitions deploy to any space/tenant with a valid
  service credential.
- **Proven consumption path:** output views are confirmed available to SAC, closing the loop from
  raw structure to BI-ready dimension.


---

## Appendix A — Glossary

- **CSN (Core Schema Notation):** SAP's JSON format describing entities, columns, and queries;
  the input format for creating Datasphere objects by code.
- **Local table:** a table that physically stores data inside a Datasphere space.
- **View:** a query (projection/join/etc.) over tables or other views.
- **Dimension (ANALYTICAL_DIMENSION):** a master-data object (attributes/texts, no measures) that
  BI tools like SAC use to slice/label data.
- **Consumption exposure:** an object flagged so it is published via Datasphere's OData consumption
  API, which SAC reads.
- **Client-credentials OAuth:** a service-to-service login using a client ID/secret (no user
  interaction) — how the automation authenticates.
