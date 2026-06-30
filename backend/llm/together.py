"""Together LLM client — AI-assisted contract analysis + redlined revision.

IMPORTANT: the structural verdict is the *verified ORCA machine's*. This module produces only the
(unverified, clearly-labeled "AI-assisted") analysis and proposed revision. It fails loudly when
invoked without a key — it never fabricates an analysis.
"""
import json
import logging
import re

import httpx

from backend.app.config import get_settings
from backend.llm.budget import check_budget, record_usage

logger = logging.getLogger(__name__)


async def _chat(messages: list[dict], max_tokens: int = 2000, temperature: float = 0.022,
                response_json: bool = False) -> str:
    s = get_settings()
    if not s.llm_enabled:
        raise RuntimeError("TOGETHER_API_KEY not set — LLM analysis/revision is disabled")
    await check_budget()  # raises BudgetExceeded → analysis skipped (spend cap)
    payload: dict = {
        "model": s.TOGETHER_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_json:
        payload["response_format"] = {"type": "json_object"}
    async with httpx.AsyncClient(timeout=180) as client:
        r = await client.post(
            f"{s.TOGETHER_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {s.TOGETHER_API_KEY}"},
            json=payload,
        )
        r.raise_for_status()
        resp = r.json()
    await record_usage(int(resp.get("usage", {}).get("total_tokens", 0)))
    return resp["choices"][0]["message"]["content"]


async def analyze_contract(text: str, temperature: float = 0.022) -> dict:
    system = (
        "You are a meticulous document analyst. Analyze the document and respond with JSON only, "
        "using exactly these keys: "
        "summary (string — a succinct plain-language summary of what the document is and says), "
        "aims (string — what the document is trying to achieve), "
        "parties (array of strings), "
        "key_terms (array of objects {term, detail}), "
        "strengths (array of strings), "
        "weaknesses (array of strings), "
        "potential_pitfalls (array of strings — risks or ways this could go wrong in practice), "
        "issues (array of objects {severity: one of high|medium|low, issue, recommendation}), "
        "missing_or_weak_clauses (array of strings), "
        "overall_recommendation (string)."
    )
    content = await _chat(
        [{"role": "system", "content": system},
         {"role": "user", "content": f"Document text:\n\n{text[:60000]}"}],
        response_json=True, max_tokens=3200, temperature=temperature,
    )
    try:
        data = json.loads(content)
    except Exception:  # noqa: BLE001 — model returned non-JSON; keep it visible, don't fabricate
        return {"summary": content[:2000], "aims": "", "parties": [], "key_terms": [],
                "strengths": [], "weaknesses": [], "potential_pitfalls": [],
                "issues": [], "missing_or_weak_clauses": [], "overall_recommendation": "",
                "_parse_note": "model did not return valid JSON; showing raw summary"}
    for key in ("parties", "key_terms", "strengths", "weaknesses",
                "potential_pitfalls", "issues", "missing_or_weak_clauses"):
        data.setdefault(key, [])
    data.setdefault("aims", "")
    return data


_FSM_FORMAT = """Express the lifecycle / process the document describes as a state machine in
ORCA Markdown. Follow this format EXACTLY:

# machine NameInPascalCase

## events
- EVENT_IN_UPPER_SNAKE

## state state_in_snake_case [initial]
> a SHORT 2-5 word label for this state (e.g. "Drafting", "Active license", "Terminated")
- ignore: *

## state terminal_state [final]

## transitions
| Source | Event | Guard | Target | Action |
|---|---|---|---|---|
| state_in_snake_case | EVENT_IN_UPPER_SNAKE | | terminal_state | |

RULES (a verifier will check these):
- The FIRST line MUST be exactly `# machine NameInPascalCase` — include the literal word "machine".
- Exactly ONE state marked [initial]; mark every terminal state [final].
- Every NON-final state must have at least one outgoing transition AND a "- ignore: *" line.
- Every state must be reachable from the initial state.
- Model the document's REAL stages/lifecycle (e.g. a contract: drafting → effective → active →
  renewal/termination; an agreement's obligations as conditional transitions).
- Output ONLY the .orca.md document — no preamble, no explanation, no ``` fences."""


async def extract_state_machine(text: str, temperature: float = 0.033) -> str:
    """Extract the FSM the document itself expresses, as an ORCA .orca.md machine."""
    md = await _chat(
        [{"role": "system", "content": "You are a systems analyst. " + _FSM_FORMAT},
         {"role": "user", "content": f"Document:\n\n{text[:40000]}"}],
        max_tokens=1500, temperature=temperature,
    )
    md = md.strip()
    if md.startswith("```"):  # strip accidental code fences
        md = re.sub(r"^```[a-zA-Z]*\n?", "", md)
        md = re.sub(r"\n?```$", "", md)
    md = md.strip()
    # The model sometimes drops the required "machine" keyword from the header
    # (`# Name` instead of `# machine Name`), which crashes the parser — repair it.
    if not re.match(r"^#\s+machine\b", md, re.IGNORECASE):
        md = re.sub(r"^#\s+", "# machine ", md, count=1)
    return md.strip()


_CHUNK_CHARS = 8000
_MAX_CHUNKS = 12  # bounds cost/latency; ~96k chars covers essentially any real contract


def _split_into_chunks(text: str, max_chars: int = _CHUNK_CHARS) -> list[str]:
    """Greedy split preferring paragraph > line > word boundaries near max_chars."""
    chunks: list[str] = []
    remaining = text.strip()
    while len(remaining) > max_chars:
        window = remaining[:max_chars]
        brk = window.rfind("\n\n")
        if brk < max_chars * 0.5:
            brk = window.rfind("\n")
        if brk < max_chars * 0.5:
            brk = window.rfind(" ")
        if brk < max_chars * 0.5:
            brk = max_chars
        chunks.append(remaining[:brk])
        remaining = remaining[brk:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks or [text]


_REVISE_SYS = (
    "You are an editor producing a REDLINE of ONE SECTION of a longer document. Improve wording, "
    "fix problems, and tighten weak or ambiguous language in this section, preserving its meaning. "
    "Mark EVERY change inline: wrap text you REMOVE in {--double-minus braces--} and text you ADD in "
    "{++double-plus braces++}. Leave unchanged text exactly as-is, with no markers. Use no other "
    "change notation. Output ONLY the redlined section — no preamble, no explanation."
)


async def _revise_chunk(chunk: str, temperature: float = 0.033) -> str:
    return (await _chat(
        [{"role": "system", "content": _REVISE_SYS},
         {"role": "user", "content": chunk}],
        max_tokens=4096, temperature=temperature,
    )).strip()


async def _draft_additions(missing: list, temperature: float = 0.033) -> str:
    if not missing:
        return ""
    system = (
        "Draft formal clauses for each item below as new document language. Wrap EACH drafted clause "
        "entirely in {++double-plus braces++} so it renders as an addition. Output only the clauses."
    )
    user = "Draft additions for:\n- " + "\n- ".join(str(m) for m in missing[:12])
    return (await _chat(
        [{"role": "system", "content": system},
         {"role": "user", "content": user}],
        max_tokens=2400, temperature=temperature,
    )).strip()


async def revise_contract(text: str, analysis: dict, temperature: float = 0.033) -> str:
    # Redline the WHOLE document by chunking it — nothing is truncated to the first few pages.
    chunks = _split_into_chunks(text)
    truncated = len(chunks) > _MAX_CHUNKS
    parts: list[str] = []
    for chunk in chunks[:_MAX_CHUNKS]:
        parts.append(await _revise_chunk(chunk, temperature))
    redline = "\n\n".join(p for p in parts if p)
    if truncated:
        redline += "\n\n{++[Note: the document was very long; this redline covers its first portion.]++}"
    # Always draft the missing/weak clauses as explicit additions so changes aren't deletions-only.
    additions = await _draft_additions(analysis.get("missing_or_weak_clauses") or [], temperature)
    if additions:
        redline += "\n\n" + additions
    return redline.strip()
