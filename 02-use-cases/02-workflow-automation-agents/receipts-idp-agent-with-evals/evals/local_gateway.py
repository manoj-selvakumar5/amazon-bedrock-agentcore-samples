"""Stage 0: a local stand-in for the receipts AgentCore Gateway.

The receipts pipeline reaches save_expense and human_review through an MCP client
(`gateway.call_tool_sync` in main.py), not through agent tools. This FastMCP server
exposes the same tools on localhost, so the pipeline and the chat assistant run unchanged
with no deployed Gateway, Lambda targets, DynamoDB tables, or Cedar policy.

What it stands in for:
- The save_expense and human_review Lambda targets: writes go to an in-memory dict.
- The get_user_profile, get_recent_expenses and lookup_merchant read targets the chat
  assistant uses, reading the same dict plus seeded profiles.
- The Cedar policy BlockExcessiveExpense: a save with total_cents >= 200000, or with no
  total_cents at all, is rejected with a "denied by policy" error, which main.py's
  _is_denied() already recognises.

Run on its own:     python local_gateway.py
Start from a script: url = start_in_background()
"""

import hashlib
import json
import re
import socket
import threading
import time
from datetime import datetime, timezone
from typing import Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

HOST = "127.0.0.1"
PORT = 8765
URL = f"http://{HOST}:{PORT}/mcp"

# Mirrors the Cedar policy BlockExcessiveExpense in agentcore/agentcore.json, in cents.
POLICY_THRESHOLD_CENTS = 200000

# Set False to run as if the policy were detached or in log-only mode, so the control
# monitor can be seen catching a control that is not there.
POLICY_ENABLED = True

# Everything the pipeline wrote, keyed by expenseId. A second write to the same id
# overwrites the first, exactly as `put_item` does in the real save_expense Lambda.
EXPENSES: dict[str, dict[str, Any]] = {}

# Every write in order, so an overwrite is visible at all. EXPENSES alone cannot show one:
# the losing row is gone by the time anyone looks.
WRITE_LOG: list[dict[str, Any]] = []

# User profiles for get_user_profile, keyed by userId, filled by seed().
PROFILES: dict[str, dict[str, Any]] = {}

server = FastMCP("receipts-local-gateway", host=HOST, port=PORT, log_level="WARNING")


def seed(profiles: list[dict[str, Any]], expenses: list[dict[str, Any]]) -> None:
    """Load profiles and expense rows as the tables would hold them, for a chat run."""
    for profile in profiles:
        PROFILES[profile["userId"]] = profile
    for row in expenses:
        EXPENSES[row["expenseId"]] = row


def _expense_id(user_id: str, merchant: str, date: str, total: Any) -> str:
    """Same content hash as lambdas/save_expense/handler.py, so duplicates collide the same way."""
    raw = f"{user_id}|{merchant}|{date}|{total}".lower()
    return "exp-" + hashlib.sha256(raw.encode()).hexdigest()[:16]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@server.tool()
def save_expense(
    user_id: str,
    merchant: str,
    total: float,
    total_cents: int | None = None,
    merchant_address: str = "",
    transaction_date: str = "",
    currency: str = "USD",
    subtotal: float | None = None,
    tax: float | None = None,
    tip: float | None = None,
    payment_method: str = "",
    line_items: list[Any] | None = None,
    category: str = "",
    status: str = "processed",
    source_receipt_s3: str = "",
) -> str:
    """Persist a validated expense record for a user."""
    if POLICY_ENABLED and (total_cents is None or total_cents >= POLICY_THRESHOLD_CENTS):
        raise ToolError(
            f"Tool call denied by policy BlockExcessiveExpense: total_cents {total_cents} "
            f"is missing or >= {POLICY_THRESHOLD_CENTS}"
        )

    expense_id = _expense_id(user_id, merchant, transaction_date, total)
    EXPENSES[expense_id] = {
        "tool": "save_expense",
        "userId": user_id,
        "expenseId": expense_id,
        "merchant": merchant,
        "merchantAddress": merchant_address,
        "transactionDate": transaction_date,
        "currency": currency,
        "subtotal": subtotal,
        "tax": tax,
        "tip": tip,
        "total": total,
        "paymentMethod": payment_method,
        "lineItems": line_items or [],
        "category": category,
        "status": status,
        "sourceReceiptS3": source_receipt_s3,
        "createdAt": _now(),
    }
    WRITE_LOG.append(
        {
            "tool": "save_expense",
            "expenseId": expense_id,
            "sourceReceiptS3": source_receipt_s3,
            "merchant": merchant,
            "transactionDate": transaction_date,
            "total": total,
        }
    )
    return json.dumps({"recorded": True, "userId": user_id, "expenseId": expense_id, "status": status})


@server.tool()
def human_review(
    user_id: str,
    reason: str,
    merchant: str = "",
    transaction_date: str = "",
    currency: str = "USD",
    total: float | None = None,
    category: str = "",
    line_items: list[Any] | None = None,
    source_receipt_s3: str = "",
) -> str:
    """Record an expense as pending human review instead of auto-saving it."""
    expense_id = _expense_id(user_id, merchant, transaction_date, total)
    EXPENSES[expense_id] = {
        "tool": "human_review",
        "userId": user_id,
        "expenseId": expense_id,
        "merchant": merchant,
        "transactionDate": transaction_date,
        "currency": currency,
        "total": total,
        "category": category,
        "lineItems": line_items or [],
        "status": "needs_review",
        "reviewReason": reason,
        "sourceReceiptS3": source_receipt_s3,
        "createdAt": _now(),
    }
    WRITE_LOG.append(
        {
            "tool": "human_review",
            "expenseId": expense_id,
            "sourceReceiptS3": source_receipt_s3,
            "merchant": merchant,
            "transactionDate": transaction_date,
            "total": total,
        }
    )
    return json.dumps({"recorded": True, "userId": user_id, "expenseId": expense_id, "status": "needs_review"})


@server.tool()
def get_user_profile(user_id: str) -> str:
    """Read a user's expense profile (cost center, default category, preferred currency, reimbursement policy) by user id."""
    profile = PROFILES.get(user_id)
    if not profile:
        return json.dumps({"error": f"User {user_id} not found"})
    return json.dumps(profile, default=str)


@server.tool()
def get_recent_expenses(user_id: str, limit: int = 20) -> str:
    """List a user's most recent expenses (newest first) so you can detect a likely duplicate before saving a new one."""
    limit = max(1, min(int(limit), 100))
    # Same order as the Lambda: descending on the expenseId sort key. The id is a content
    # hash, so despite "newest first" this is not date order, locally or deployed.
    rows = sorted((r for r in EXPENSES.values() if r.get("userId") == user_id), key=lambda r: r["expenseId"], reverse=True)
    items = [{k: v for k, v in r.items() if k != "tool"} for r in rows[:limit]]
    return json.dumps({"userId": user_id, "count": len(items), "expenses": items}, default=str)


@server.tool()
def lookup_merchant(name: str) -> str:
    """Normalize a raw merchant name from a receipt against the merchant catalog. Returns the canonical merchant if known, otherwise a cleaned passthrough you can still use."""
    # No catalog locally: the Lambda's own fallback when the Merchants table has no entry.
    key = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return json.dumps({"matched": False, "merchant": {"merchantKey": key, "displayName": name.strip()}})


def _port_open() -> bool:
    try:
        with socket.create_connection((HOST, PORT), timeout=0.2):
            return True
    except OSError:
        return False


def start_in_background(timeout: float = 10.0) -> str:
    """Start the server on a daemon thread and return its MCP URL once it accepts connections."""
    if _port_open():
        raise RuntimeError(f"port {PORT} is already in use; stop the other process or change PORT")

    threading.Thread(target=server.run, kwargs={"transport": "streamable-http"}, daemon=True).start()

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _port_open():
            return URL
        time.sleep(0.1)
    raise RuntimeError(f"local gateway did not start on {HOST}:{PORT} within {timeout}s")


if __name__ == "__main__":
    print(f"Local receipts gateway on {URL}")
    server.run(transport="streamable-http")
