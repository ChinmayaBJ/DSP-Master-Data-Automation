"""
One-command, idempotent deploy of the Version 2 GL-Account master-data model.

Deploys, in dependency order:
    4 local tables (structure only)  ->  3 consumption views (dimensions)

For each object it checks whether the object already exists in the space:
    - not there  -> create
    - already there -> update (syncs the tenant to the CSN file)
So it is safe to run repeatedly, on a clean space or an already-populated one.

Auth is headless: the OAuth client-credentials token from .env is injected into
the SAP Datasphere CLI via the ACCESS_TOKEN env var (no browser / no passcode).

Usage (from this folder, with the venv active):
    python deploy.py            # create-or-update all 7 objects
    python deploy.py --verify   # then read each view back to confirm status
"""
import sys
from pathlib import Path

from dsp_cli import run_cli, obj_read, SPACE

CSN_DIR = Path(__file__).parent / "csn"

# Local tables first (the join view depends on the first two).
TABLES = [
    "ZT2_GLACCOUNTINCOA",
    "ZT2_GLACCOUNTTEXT",
    "ZT2_GLACCTHIERNODET",
    "ZT2_GLACCTHIERNODE",
]

# Views after their source tables exist.
VIEWS = [
    "ZV2_GLACCOUNT_NAME",       # LEFT JOIN: ZT2_GLACCOUNTINCOA + ZT2_GLACCOUNTTEXT
    "ZV2_GLACCTHIER_NODETEXT",  # projection: ZT2_GLACCTHIERNODET
    "ZV2_GLACCTHIER_NODE",      # projection: ZT2_GLACCTHIERNODE
]


def _exists(kind, name):
    """True if the object is already present in the space (silent check)."""
    r = run_cli(["objects", kind, "read", "-y", SPACE, "-f", name], quiet=True)
    return r.returncode == 0


def _create(kind, csn):
    return run_cli(["objects", kind, "create", "-y", SPACE, "-F", str(csn)], quiet=True)


def _update(kind, name, csn):
    return run_cli(["objects", kind, "update", "-y", SPACE, "-i", name, "-F", str(csn)], quiet=True)


def _sync(kind, names):
    ok = True
    for name in names:
        csn = CSN_DIR / f"{name}.json"
        if not csn.exists():
            print(f"  ! missing CSN file: {csn.name}")
            ok = False
            continue

        if _exists(kind, name):
            result = _update(kind, name, csn)
            action = "updated"
        else:
            result = _create(kind, csn)
            action = "created"

        if result.returncode == 0:
            print(f"  {action:>7}  {name}")
        else:
            print(f"  FAILED   {name}")
            if result.stderr:
                # surface just the last, most useful stderr line
                print("           " + result.stderr.strip().splitlines()[-1])
            ok = False
    return ok


def main(argv):
    print("== Version 2 deploy (idempotent create-or-update) ==")
    print("Step 1/2  local tables")
    tables_ok = _sync("local-tables", TABLES)

    print("Step 2/2  views")
    views_ok = _sync("views", VIEWS)

    if "--verify" in argv:
        print("\n== Verify (reading views back) ==")
        for name in VIEWS:
            print(f"  reading view: {name}")
            obj_read("views", name)

    if tables_ok and views_ok:
        print("\nDone: 4 tables + 3 views are in sync with csn/.")
        return 0
    print("\nCompleted with errors (see FAILED lines above).")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
