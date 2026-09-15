"""DELTA CLI: delta inspect / replay / explain. Usage:
  python3 cli.py inspect exec_0001
  python3 cli.py replay exec_0001 [--tamper]
  python3 cli.py explain exec_0001
"""
from __future__ import annotations
import sys
from delta import explain_exec, inspect_exec, replay_exec


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    cmd, exec_id = argv[1], argv[2]
    if cmd == "inspect":
        print(inspect_exec(exec_id))
    elif cmd == "explain":
        print(explain_exec(exec_id))
    elif cmd == "replay":
        tamper = None
        if "--tamper" in argv:
            tamper = lambda a: next(iter(a.values())).__setitem__("risk", 91) \
                if "risk" in next(iter(a.values())) else None
        ev = replay_exec(exec_id, tamper=tamper)
        print(f"REPLAY {exec_id} -> {ev.verdict.value}")
        for line in ev.evidence:
            print(f"  - {line}")
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
