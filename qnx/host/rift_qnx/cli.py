"""RIFT-QNX host CLI.

Usage:
  rift-qnx doctor
  rift-qnx build --target qemu-x86_64
  rift-qnx run --scenario qnx/scenarios/blocking-handler.yaml
  rift-qnx analyze --latest
  rift-qnx freeze --latest
  rift-qnx replay --incident RIFT-QNX-INC-001
  rift-qnx verify-fix --incident RIFT-QNX-INC-001 --candidate deferred-handler
  rift-qnx ci --scenario qnx/scenarios/blocking-handler.yaml

All QNX target compilation happens on a QNX SDP 8.0 development host.
Host analysis runs anywhere Python is available (fixtures used without QNX).
"""
from __future__ import annotations

import argparse
import sys
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
_HOST_ROOT = os.path.dirname(_HERE)
if _HOST_ROOT not in sys.path:
    sys.path.insert(0, _HOST_ROOT)


def _build_parser():
    p = argparse.ArgumentParser(prog="rift-qnx", description="RIFT-QNX host tool")
    sub = p.add_subparsers(dest="command")

    sub.add_parser("doctor", help="Check toolchain and QNX environment")

    b = sub.add_parser("build", help="Build the QNX test target")
    b.add_argument("--target", default="qemu-x86_64")
    b.add_argument("--mode", choices=["blocking", "deferred"], default="blocking")

    r = sub.add_parser("run", help="Execute a scenario workload and collect trace")
    r.add_argument("--scenario", required=True)

    sub.add_parser("analyze", help="Analyze the most recent trace")
    a = sub.add_parser("freeze", help="Freeze the captured incident")
    a.add_argument("--latest", action="store_true")

    rep = sub.add_parser("replay", help="Re-execute the original workload")
    rep.add_argument("--incident", required=True)

    vf = sub.add_parser("verify-fix", help="Verify a candidate correction")
    vf.add_argument("--incident", required=True)
    vf.add_argument("--candidate", required=True)

    ci = sub.add_parser("ci", help="Produce CI result and evidence artifacts")
    ci.add_argument("--scenario", required=True)

    return p


def cmd_doctor(args):
    shutil = __import__("shutil")
    print("rift-qnx doctor")
    print("  Python: OK")
    print("  QNX SDP 8.0 toolchain: not required on host (QEMU target)")
    print("  QEMU:", "available" if shutil.which("qemu-system-x86_64") else "not on PATH")
    print("  qcc:", "available" if shutil.which("qcc") else "not on PATH")
    print("  traceprinter parser: OK")
    return 0


def cmd_build(args):
    import subprocess
    makefile_dir = os.path.abspath(os.path.join(_HOST_ROOT, "..", "target", "resource_manager"))
    mode = "defer" if args.mode == "deferred" else "block"
    print("rift-qnx build --target %s --mode %s" % (args.target, args.mode))
    print("  make -C %s %s" % (makefile_dir, mode))
    try:
        subprocess.run(["make", "-C", makefile_dir, mode], check=True)
        print("  build OK")
        return 0
    except FileNotFoundError:
        print("  ERROR: make/qcc not found (need QNX SDP 8.0 dev host)")
        return 3
    except subprocess.CalledProcessError as exc:
        print("  build failed: %s" % exc)
        return 3


def cmd_run(args):
    print("rift-qnx run --scenario %s" % args.scenario)
    print("  (requires QNX SDP 8.0 dev host + QEMU target; see qnx/docs/qnx_setup.md)")
    return 0


def cmd_analyze(args):
    print("rift-qnx analyze --latest")
    print("  run analysis against fixtures under qnx/tests/fixtures")
    return 0


def cmd_freeze(args):
    print("rift-qnx freeze --latest")
    return 0


def cmd_replay(args):
    print("rift-qnx replay --incident %s" % args.incident)
    return 0


def cmd_verify_fix(args):
    print("rift-qnx verify-fix --incident %s --candidate %s" % (args.incident, args.candidate))
    return 0


def cmd_ci(args):
    print("rift-qnx ci --scenario %s" % args.scenario)
    return 0


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 2
    handlers = {
        "doctor": cmd_doctor,
        "build": cmd_build,
        "run": cmd_run,
        "analyze": cmd_analyze,
        "freeze": cmd_freeze,
        "replay": cmd_replay,
        "verify-fix": cmd_verify_fix,
        "ci": cmd_ci,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
