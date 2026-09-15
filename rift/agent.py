"""Scripted agent policies. Deliberately NOT an LLM: the version-change demo must
be deterministic and reliable on stage. Each policy emits tool_call/tool_result
events through the recorder so trajectories look exactly like a real agent run.

v1.0 (buggy): picks a refund by AMOUNT -> grabs R91 (already COMPLETED).
v1.1 (fixed): picks a refund by STATUS -> grabs R92 (PENDING).
An LLM policy could be dropped in behind the same `Policy` signature; the
detector and evaluator below would not change.
"""
from __future__ import annotations
from typing import Callable, Dict


def _call(rec, shop, tool: str, args: dict, fn: Callable):
    rec.tool_call(tool, args)
    out = fn()
    rec.tool_result(tool, out)
    return out


# ---------- refund task ----------
def refund_v10(shop, task, rec):
    c = _call(rec, shop, "lookup_customer", {"name": task["customer"]},
              lambda: shop.lookup_customer(task["customer"]))
    o = _call(rec, shop, "lookup_order", {"customer_id": c["id"]},
              lambda: shop.lookup_order(c["id"]))
    rs = _call(rec, shop, "lookup_refunds", {"order_id": o["id"]},
               lambda: shop.lookup_refunds(o["id"]))
    pick = next(r for r in rs if r["amount_cents"] == o["amount_cents"])  # BUG: ignores status
    _call(rec, shop, "issue_refund", {"refund_id": pick["id"]},
          lambda: shop.issue_refund(pick["id"]))
    _call(rec, shop, "update_ticket", {"ticket_id": task["ticket_id"], "status": "RESOLVED"},
          lambda: shop.update_ticket(task["ticket_id"], "RESOLVED", "refund processed"))


def refund_v11(shop, task, rec):
    c = _call(rec, shop, "lookup_customer", {"name": task["customer"]},
              lambda: shop.lookup_customer(task["customer"]))
    o = _call(rec, shop, "lookup_order", {"customer_id": c["id"]},
              lambda: shop.lookup_order(c["id"]))
    rs = _call(rec, shop, "lookup_refunds", {"order_id": o["id"]},
               lambda: shop.lookup_refunds(o["id"]))
    pick = next(r for r in rs if r["status"] == task["requested_status"])  # FIX: match status
    _call(rec, shop, "issue_refund", {"refund_id": pick["id"]},
          lambda: shop.issue_refund(pick["id"]))
    _call(rec, shop, "update_ticket", {"ticket_id": task["ticket_id"], "status": "RESOLVED"},
          lambda: shop.update_ticket(task["ticket_id"], "RESOLVED", "refund processed"))


# ---------- address task ----------
def address_bad(shop, task, rec):
    c = _call(rec, shop, "lookup_customer", {"name": task["customer"]},
              lambda: shop.lookup_customer(task["customer"]))
    _call(rec, shop, "update_address", {"customer_id": c["id"], "address": task["new_address"]},
          lambda: shop.update_address(c["id"], task["new_address"]))
    _call(rec, shop, "send_email", {"customer_id": c["id"], "template": "promo_20pct"},
          lambda: shop.send_email(c["id"], "promo_20pct"))  # BUG: unauthorized side effect


def address_good(shop, task, rec):
    c = _call(rec, shop, "lookup_customer", {"name": task["customer"]},
              lambda: shop.lookup_customer(task["customer"]))
    _call(rec, shop, "update_address", {"customer_id": c["id"], "address": task["new_address"]},
          lambda: shop.update_address(c["id"], task["new_address"]))
    _call(rec, shop, "update_ticket", {"ticket_id": task["ticket_id"], "status": "RESOLVED"},
          lambda: shop.update_ticket(task["ticket_id"], "RESOLVED", "address updated"))


# ---------- cancel task ----------
def cancel_bad(shop, task, rec):
    o = _call(rec, shop, "lookup_order", {"customer_id": task["customer_id"]},
              lambda: shop.lookup_order(task["customer_id"]))
    _call(rec, shop, "cancel_order", {"order_id": o["id"]},
          lambda: shop.cancel_order(o["id"]))  # BUG: cancels a SHIPPED order


def cancel_good(shop, task, rec):
    o = _call(rec, shop, "lookup_order", {"customer_id": task["customer_id"]},
              lambda: shop.lookup_order(task["customer_id"]))
    _call(rec, shop, "update_ticket", {"ticket_id": task["ticket_id"], "status": "ESCALATED"},
          lambda: shop.update_ticket(task["ticket_id"], "ESCALATED",
                                     "shipped order -> refund request, not cancellation"))


V10 = {"refund": refund_v10, "address": address_bad, "cancel": cancel_bad}
V11 = {"refund": refund_v11, "address": address_good, "cancel": cancel_good}
