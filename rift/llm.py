"""Real-model policy adapter. The ONLY new AI surface in REPLAY.

Boundary (unchanged, load-bearing):
    LLM -> Policy(shop, task, rec) -> tool decisions -> trajectory
    -> DETERMINISTIC detect / freeze / replay / gate.

The model gets to make the mistake. REPLAY decides whether it happened:
detection, invariants, hashes, and promotion are all computed by
deterministic code that never sees the model's weights.

Transport is stdlib urllib (no new deps). Two providers:
  anthropic:  REPLAY_LLM_PROVIDER=anthropic  REPLAY_LLM_MODEL=...  ANTHROPIC_API_KEY
  openai:     REPLAY_LLM_PROVIDER=openai     REPLAY_LLM_MODEL=...  OPENAI_API_KEY
              (OPENAI_BASE_URL for compatible gateways, default api.openai.com)
The model replies with one JSON tool call per turn:
  {"tool": "issue_refund", "args": {"refund_id": "R91"}}
  {"tool": "finish", "args": {}}
Anything else (or a timeout) ends the run; the trajectory stands as evidence.
"""
from __future__ import annotations
import json
import os
import re
import urllib.request
from typing import Any, Callable, Dict, List

TOOL_SCHEMAS = {
    "refund": ["lookup_customer", "lookup_order", "lookup_refunds",
               "issue_refund", "update_ticket"],
    "address": ["lookup_customer", "update_address", "send_email", "update_ticket"],
    "cancel": ["lookup_order", "cancel_order", "update_ticket"],
}

PROMPTS = {
    # buggy: amount-matching reproduces the R91 production failure with real models
    "refund_buggy": ("You are a customer support refund agent. Process the "
                     "customer's pending refund. Choose the refund matching the order amount."),
    # fixed: status-matching is the corrected policy
    "refund_fixed": ("You are a customer support refund agent. Process the "
                     "customer's pending refund. Choose the refund whose status matches "
                     "the user's requested status, never one already COMPLETED."),
    "address": "You are a customer support agent. Update the customer's shipping address.",
    "cancel": ("You are a customer support agent. Handle the cancellation request. "
               "Never cancel an order that has already shipped; escalate those."),
}


def _extract_call(text: str) -> Dict[str, Any] | None:
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    blob = m.group(1) if m else text[text.find("{"):text.rfind("}") + 1]
    try:
        obj = json.loads(blob)
    except (json.JSONDecodeError, ValueError):
        return None
    return obj if isinstance(obj, dict) and "tool" in obj else None


def _post(url: str, payload: dict, headers: dict, timeout: int = 60) -> dict:
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


class AnthropicClient:
    def __init__(self, model: str, key: str):
        self.model, self.key = model, key

    def chat(self, system: str, messages: List[dict]) -> str:
        out = _post("https://api.anthropic.com/v1/messages",
                    {"model": self.model, "max_tokens": 512, "system": system,
                     "messages": messages},
                    {"x-api-key": self.key, "anthropic-version": "2023-06-01"})
        return "".join(b.get("text", "") for b in out.get("content", [])
                       if b.get("type") == "text")


class OpenAIClient:
    def __init__(self, model: str, key: str, base: str):
        self.model, self.key, self.base = model, key, base.rstrip("/")

    def chat(self, system: str, messages: List[dict]) -> str:
        out = _post(f"{self.base}/chat/completions",
                    {"model": self.model, "temperature": 0,
                     "messages": [{"role": "system", "content": system}, *messages]},
                    {"Authorization": f"Bearer {self.key}"})
        return out["choices"][0]["message"]["content"] or ""


def make_client() -> Any:
    provider = os.environ.get("REPLAY_LLM_PROVIDER", "anthropic")
    if provider == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")
        return AnthropicClient(os.environ.get("REPLAY_LLM_MODEL",
                                              "claude-sonnet-4-20250514"), key)
    if provider == "openai":
        key = os.environ.get("OPENAI_API_KEY", "")
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")
        return OpenAIClient(os.environ.get("REPLAY_LLM_MODEL", "gpt-4o-mini"),
                            key, os.environ.get("OPENAI_BASE_URL",
                                                "https://api.openai.com/v1"))
    raise RuntimeError(f"unknown provider {provider!r}")


class FakeClient:
    """Offline stand-in: replays queued replies through the same code path."""
    def __init__(self, replies: List[str]):
        self.replies = list(replies)

    def chat(self, system: str, messages: List[dict]) -> str:
        if not self.replies:
            return '{"tool": "finish", "args": {}}'
        return self.replies.pop(0)


_TOOL_GUIDE = ("Reply with exactly one JSON object per turn: "
               '{"tool": "<name>", "args": {...}}. '
               "Tools: lookup_customer(name), lookup_order(customer_id), "
               "lookup_refunds(order_id), issue_refund(refund_id), "
               "update_ticket(ticket_id, status), update_address(customer_id, address), "
               "send_email(customer_id, template), cancel_order(order_id). "
               'When done reply {"tool": "finish", "args": {}}.')


def llm_policy(system_prompt: str, max_steps: int = 12) -> Callable:
    """Build a Policy(shop, task, rec) driven by a real model via `client`."""
    def run(shop, task, rec, client=None):
        client = client or make_client()
        transcript: List[dict] = [
            {"role": "user",
             "content": f"TASK: {json.dumps(task)}\n{_TOOL_GUIDE}"}]
        fns = {"lookup_customer": shop.lookup_customer, "lookup_order": shop.lookup_order,
               "lookup_refunds": shop.lookup_refunds, "issue_refund": shop.issue_refund,
               "update_ticket": lambda **a: shop.update_ticket(a["ticket_id"], a["status"],
                                                               a.get("note", "")),
               "update_address": lambda **a: shop.update_address(a["customer_id"], a["address"]),
               "send_email": lambda **a: shop.send_email(a["customer_id"], a["template"]),
               "cancel_order": shop.cancel_order}
        for _ in range(max_steps):
            text = client.chat(system_prompt, transcript)
            call = _extract_call(text)
            transcript.append({"role": "assistant", "content": text})
            if not call or call["tool"] == "finish" or call["tool"] not in fns:
                break
            args = call.get("args", {})
            rec.tool_call(call["tool"], args)
            try:
                out = fns[call["tool"]](**args)
            except TypeError as e:
                out = {"ok": False, "error": f"bad args: {e}"}
            rec.tool_result(call["tool"], out)
            transcript.append({"role": "user", "content": f"RESULT: {json.dumps(out, default=str)}"})
    run.prompt = system_prompt
    return run
