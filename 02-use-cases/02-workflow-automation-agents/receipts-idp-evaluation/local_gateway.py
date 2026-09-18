"""Stage 0: a local stand-in for the receipts AgentCore Gateway.

The receipts pipeline reaches save_expense and human_review through an MCP client
(`gateway.call_tool_sync` in main.py), not through agent tools. This FastMCP server
exposes the same two tools on localhost, so the pipeline runs unchanged with no
deployed Gateway, Lambda targets, DynamoDB table, or Cedar policy.

What it stands in for:
- The save_expense and human_review Lambda targets: writes go to an in-memory dict.
- The Cedar policy BlockExcessiveExpense: a save with total >= 2000 is rejected with a
  "denied by policy" error, which main.py's _is_denied() already recognises.

Run on its own:     python local_gateway.py
Start from a script: url = start_in_background()
"""

import hashlib
import json
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

# Mirrors the Cedar policy BlockExcessiveExpense in agentcore/agentcore.json.
POLICY_THRESHOLD = 2000

# Everything the pipeline wrote, keyed by expenseId. A second write to the same id
# overwrites the first, exactly as `put_item` does in the real save_expense Lambda.
EXPENSES: dict[str, dict[str, Any]] = {}

# Every write in order, so an overwrite is visible at all. EXPENSES alone cannot show one:
# the losing row is gone by the time anyone looks.
WRITE_LOG: list[dict[str, Any]] = []

server = FastMCP("receipts-local-gateway", host=HOST, port=PORT, log_level="WARNING")


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
    rung: str = "",
    source_receipt_s3: str = "",
) -> str:
    """Persist a validated expense record for a user."""
    if total >= POLICY_THRESHOLD:
        raise ToolError(f"Tool call denied by policy BlockExcessiveExpense: total {total} >= {POLICY_THRESHOLD}")

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
        "rung": rung,
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
    rung: str = "",
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
        "rung": rung,
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
