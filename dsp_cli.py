"""
Headless wrapper around the SAP Datasphere CLI (`datasphere`).

Key idea: the CLI accepts the SAME OAuth client-credentials access token we
already mint in auth.get_bearer_token() — passed through the ACCESS_TOKEN env
var — so every command runs non-interactively (no passcode / no browser).

Supported modeling-object CRUD (per `datasphere objects <kind> -h`):
    create | update | read | list | delete

Usage (from the project venv):
    venv/Scripts/python dsp_cli.py list   views
    venv/Scripts/python dsp_cli.py read   views ZVDM_TGLACCOUNT
    venv/Scripts/python dsp_cli.py create views --file my_view.json
    venv/Scripts/python dsp_cli.py update views ZVDM_TGLACCOUNT --file my_view.json
    venv/Scripts/python dsp_cli.py delete views ZZ_TEST_CLI_VIEW

Or import and call run_cli(...) / view helpers from other scripts.
"""
import os
import subprocess
import sys

from auth import get_bearer_token, DATASPHERE_BASE_URL

SPACE = os.environ["DSP_SPACE"].strip()
HOST = DATASPHERE_BASE_URL.rstrip("/") + "/"


def _resolve_cli():
    """Locate the datasphere launcher (datasphere.cmd on Windows)."""
    from shutil import which
    for name in ("datasphere.cmd", "datasphere"):
        p = which(name)
        if p:
            return p
    # npm global default location on Windows
    fallback = os.path.expandvars(r"%APPDATA%\npm\datasphere.cmd")
    return fallback if os.path.exists(fallback) else "datasphere"


CLI = _resolve_cli()


def run_cli(args, capture=True, quiet=False):
    """Run a datasphere CLI command headlessly.

    The bearer token is injected via the ACCESS_TOKEN env var (the CLI's
    CONSTANT_CASE convention for --access-token). It is never written to disk.

    quiet=True suppresses printing stdout/stderr (the result is still returned),
    which lets callers do silent existence checks / status handling.
    """
    env = dict(os.environ)
    env["ACCESS_TOKEN"] = get_bearer_token()
    env["HOST"] = HOST

    cmd = [CLI] + args + ["-H", HOST]
    result = subprocess.run(
        cmd,
        env=env,
        capture_output=capture,
        text=True,
        shell=False,
    )
    if capture and not quiet:
        if result.stdout:
            print(result.stdout, end="")
        if result.returncode != 0 and result.stderr:
            print(result.stderr, file=sys.stderr, end="")
    return result


# ---- object helpers -------------------------------------------------------

def obj_list(kind="views", space=SPACE, select="technicalName,status"):
    return run_cli(["objects", kind, "list", "-y", space, "-S", select])


def obj_read(kind, technical_name, space=SPACE):
    return run_cli(["objects", kind, "read", "-y", space, "-f", technical_name])


def obj_create(kind, file_path, space=SPACE, extra=None):
    args = ["objects", kind, "create", "-y", space, "-F", file_path]
    return run_cli(args + (extra or []))


def obj_update(kind, technical_name, file_path, space=SPACE, extra=None):
    args = ["objects", kind, "update", "-y", space, "-i", technical_name, "-F", file_path]
    return run_cli(args + (extra or []))


def obj_delete(kind, technical_name, space=SPACE):
    # -F/--force skips the interactive "are you sure?" confirmation.
    return run_cli(["objects", kind, "delete", "-y", space, "-f", technical_name, "-F"])


# ---- thin CLI entrypoint --------------------------------------------------

def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    op, kind = argv[1], argv[2]
    rest = argv[3:]

    def opt(flag):
        return rest[rest.index(flag) + 1] if flag in rest else None

    if op == "list":
        obj_list(kind)
    elif op == "read":
        obj_read(kind, rest[0])
    elif op == "create":
        obj_create(kind, opt("--file"))
    elif op == "update":
        obj_update(kind, rest[0], opt("--file"))
    elif op == "delete":
        obj_delete(kind, rest[0])
    else:
        print(f"Unknown op: {op}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
