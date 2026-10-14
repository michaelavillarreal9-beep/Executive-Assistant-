"""Privacy by minimization [A p.3].

- snippets are at most 200 characters and redacted
- account, routing, policy, license and SSN-like numbers are masked
- amounts are stored as buckets
- legal and financial threads keep a reference only, never the body
"""
import re

SNIPPET_MAX = 200

_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_LABELLED = re.compile(
    r"(?i)\b(acct|account|routing|aba|policy|license|licence|lic|claim|member|card)"
    r"(\s*(?:no\.?|number|#)?\s*[:#]?\s*)([A-Z0-9][A-Z0-9-]{3,})"
)
_LONG_DIGITS = re.compile(r"\b\d[\d -]{6,}\d\b")  # 8+ digit runs: card, account, phone-like
_EMAIL_LOCAL = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
_AMOUNT = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})?")


def mask_numbers(text: str) -> str:
    text = _SSN.sub("[SSN]", text)
    text = _LABELLED.sub(lambda m: f"{m.group(1)}{m.group(2)}[MASKED]", text)
    text = _LONG_DIGITS.sub("[NUMBER]", text)
    return text


def mask_email_addresses(text: str) -> str:
    """Keep the domain (needed for the contact registry [A p.2]), drop the person."""
    return _EMAIL_LOCAL.sub(lambda m: f"[someone]@{m.group(1)}", text)


def amount_bucket(amount: float) -> str:
    """[A p.3]: under $100, $100 to $1k, over $1k."""
    if amount < 100:
        return "UNDER_100"
    if amount <= 1000:
        return "100_TO_1K"
    return "OVER_1K"


def bucket_amounts(text: str) -> str:
    def repl(m):
        value = float(m.group(1).replace(",", ""))
        return f"[AMOUNT:{amount_bucket(value)}]"
    return _AMOUNT.sub(repl, text)


def redact(text: str) -> str:
    return bucket_amounts(mask_email_addresses(mask_numbers(text or "")))


def snippet(text: str, sensitive: bool = False) -> str:
    """A storable snippet. Legal/financial threads keep the reference only [A p.3]."""
    if sensitive:
        return "[REFERENCE ONLY]"
    clean = re.sub(r"\s+", " ", redact(text)).strip()
    if len(clean) <= SNIPPET_MAX:
        return clean
    return clean[: SNIPPET_MAX - 1].rstrip() + "…"
