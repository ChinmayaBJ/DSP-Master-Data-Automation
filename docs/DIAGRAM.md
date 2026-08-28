# Version 2 — How It Works (Diagrams)

Space: `HIERARCHY_AUTOMATION` · Tenant: `sdc-analytics-dwc.ap11.hcs.cloud.sap`
All objects built **headlessly by code** (no UI).

---

## 1. End-to-end data model (source → tables → views → SAC)

```mermaid
flowchart LR
    subgraph SRC["Source CDS structures (S/4 model reference)"]
        direction TB
        C1["I_GLAccountInChartOfAccounts<br/><i>GL account master</i>"]
        C2["I_GLAccountText<br/><i>GL account name (by language)</i>"]
        C3["I_GLAccountHierarchyNodeT<br/><i>hierarchy node text</i>"]
        C4["I_GLAccountHierarchyNode<br/><i>hierarchy node structure</i>"]
    end

    subgraph TBL["4 local tables (structure only, empty)"]
        direction TB
        T1["ZT2_GLACCOUNTINCOA<br/><b>ChartOfAccounts, GLAccount</b>"]
        T2["ZT2_GLACCOUNTTEXT<br/><b>ChartOfAccounts, GLAccount, Language</b><br/>GLAccountName"]
        T3["ZT2_GLACCTHIERNODET<br/><b>GLAccountHierarchy, HierarchyNode, Language</b><br/>HierarchyNodeText"]
        T4["ZT2_GLACCTHIERNODE<br/><b>GLAccountHierarchy, HierarchyNode</b><br/>ParentNode, NodeType, NodeValue"]
    end

    subgraph VW["3 views (dimensions, consumption-exposed)"]
        direction TB
        V1["ZV2_GLACCOUNT_NAME<br/><i>LEFT JOIN</i><br/>ChartOfAccounts, GLAccount, GLAccountName"]
        V2["ZV2_GLACCTHIER_NODETEXT<br/><i>projection</i><br/>HierarchyNode, HierarchyNodeText"]
        V3["ZV2_GLACCTHIER_NODE<br/><i>projection</i><br/>GLAccountHierarchy, ParentNode,<br/>NodeType, NodeValue"]
    end

    SAC["SAP Analytics Cloud<br/><i>consumes via OData $metadata</i>"]

    C1 -.models.-> T1
    C2 -.models.-> T2
    C3 -.models.-> T3
    C4 -.models.-> T4

    T1 -->|"A (left)"| V1
    T2 -->|"B (right)"| V1
    T3 --> V2
    T4 --> V3

    V1 --> SAC
    V2 --> SAC
    V3 --> SAC
```

---

## 2. The join view (ZV2_GLACCOUNT_NAME)

```mermaid
flowchart LR
    A["ZT2_GLACCOUNTINCOA (A)<br/>ChartOfAccounts + GLAccount"]
    B["ZT2_GLACCOUNTTEXT (B)<br/>+ Language + GLAccountName"]
    J{{"LEFT JOIN<br/>A.ChartOfAccounts = B.ChartOfAccounts<br/>AND A.GLAccount = B.GLAccount<br/>AND B.Language = 'E'"}}
    OUT["ZV2_GLACCOUNT_NAME<br/>ChartOfAccounts, GLAccount, GLAccountName"]

    A --> J
    B --> J
    J --> OUT
```

Every GL account is kept even when no English text exists (left join); the `Language = 'E'`
predicate stops one-row-per-language multiplication.

---

## 3. How it is deployed (headless toolchain)

```mermaid
flowchart TB
    ENV[".env<br/>OAuth client-credentials"] --> TOK["get_bearer_token()"]
    TOK -->|"ACCESS_TOKEN env"| CLI["@sap/datasphere-cli"]
    CSN["version 2/csn/*.json<br/>(4 tables + 3 views)"] --> PY["project/dsp_cli.py<br/>obj_create / read / list"]
    PY --> CLI
    CLI -->|"objects local-tables create x4"| DSP[("SAP Datasphere<br/>HIERARCHY_AUTOMATION")]
    CLI -->|"objects views create x3"| DSP
    DSP -->|"verify: catalog + $metadata 200"| OK["Deployed & SAC-ready"]
```

**Sequence:** author CSN → create 4 tables → create 3 views (join view after its 2 tables) →
verify deploy status + consumption exposure. Everything is reversible via `delete`.
