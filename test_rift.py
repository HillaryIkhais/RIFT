"""REPLAY tests: incident investigation, world freeze, replay, fix verification."""
import shutil
from rift import (Shop, V10, V11, Recorder, investigate, freeze_incident,
                    replay_incident, verify_fix, verify_world,
                    seed_sarah, seed_address, seed_cancel)
from rift.recorder import STORE, verify_run
import rift.recorder as R
import rift.miner as M
import rift.engine as E

STORE_T = ".replay_test"
R.STORE = M.STORE = E.STORE = STORE_T
shutil.rmtree(STORE_T, ignore_errors=True)

REFUND = {"kind": "refund", "customer": "Sarah Chen", "requested_status": "PENDING", "ticket_id": 7}
ADDR = {"kind": "address", "customer": "Sarah Chen", "new_address": "9 Elm St", "ticket_id": 8}
CANCEL = {"kind": "cancel", "customer_id": 42, "ticket_id": 9}


def run_once(seed, task, policy, version="t"):
    shop = Shop()
    shop.restore(seed())
    rec = Recorder(task, version, shop)
    policy(shop, task, rec)
    return rec.finish(shop, "done")


def test_investigate_refund():
    f = investigate(run_once(seed_sarah, REFUND, V10["refund"]))
    assert f["category"] == "WRONG_ENTITY_SELECTION" and f["bad_selection"] == "R91"

def test_investigate_clean():
    assert investigate(run_once(seed_sarah, REFUND, V11["refund"])) is None

def test_investigate_side_effect():
    f = investigate(run_once(seed_address, ADDR, V10["address"]))
    assert f["category"] == "FORBIDDEN_SIDE_EFFECT"

def test_investigate_transition():
    f = investigate(run_once(seed_cancel, CANCEL, V10["cancel"]))
    assert f["category"] == "STATE_TRANSITION_VIOLATION"

def test_freeze_and_verify_world():
    run = run_once(seed_sarah, REFUND, V10["refund"])
    assert verify_run(run)
    frozen = freeze_incident(run, investigate(run))
    assert verify_world(frozen)
    evil = dict(run); evil["events"] = []
    assert not verify_run(evil)

def test_replay_reproduces_and_fix_holds():
    run = run_once(seed_sarah, REFUND, V10["refund"])
    frozen = freeze_incident(run, investigate(run))
    assert replay_incident(frozen, V10["refund"], "v1.0")["failure_reproduced"]
    assert not replay_incident(frozen, V11["refund"], "v1.1")["failure_reproduced"]

def test_replay_refuses_tampered_world():
    run = run_once(seed_sarah, REFUND, V10["refund"])
    frozen = freeze_incident(run, investigate(run))
    frozen["world"]["state"]["refunds"][0]["status"] = "PENDING"
    try:
        replay_incident(frozen, V11["refund"], "v1.1")
        assert False, "should refuse"
    except ValueError:
        pass

def test_verify_fix_blocks_and_approves():
    regs = []
    for seed, task, pol in ((seed_sarah, REFUND, V10["refund"]),
                            (seed_address, ADDR, V10["address"]),
                            (seed_cancel, CANCEL, V10["cancel"])):
        run = run_once(seed, task, pol)
        regs.append(freeze_incident(run, investigate(run)))
    assert verify_fix("v1.0", V10, regs)["verdict"] == "FIX_INCOMPLETE"
    assert verify_fix("v1.1", V11, regs)["verdict"] == "FIX_VERIFIED"


if __name__ == "__main__":
    test_investigate_refund(); test_investigate_clean()
    test_investigate_side_effect(); test_investigate_transition()
    test_freeze_and_verify_world(); test_replay_reproduces_and_fix_holds()
    test_replay_refuses_tampered_world(); test_verify_fix_blocks_and_approves()
    print("tests pass: 8/8")
