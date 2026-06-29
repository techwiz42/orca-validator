"""Together LLM client — AI-assisted contract analysis + redlined revision.

IMPORTANT: the structural verdict is the *verified ORCA machine's*. This module produces only the
(unverified, clearly-labeled "AI-assisted") analysis and proposed revision. It fails loudly when
invoked without a key — it never fabricates an analysis.
"""
import json
import logging

import httpx

from backend.app.config import get_settings

logger = logging.getLogger(__name__)


async def _chat(messages: list[dict], max_tokens: int = 2000, temperature: float = 0.2,
                response_json: bool = False) -> str:
    s = get_settings()
    if not s.llm_enabled:
        raise RuntimeError("TOGETHER_API_KEY not set — LLM analysis/revision is disabled")
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
        return r.json()["choices"][0]["message"]["content"]


async def analyze_contract(text: str) -> dict:
    system = (
        "You are a meticulous contract analyst. Analyze the contract and respond with JSON only, "
        "using exactly these keys: "
        "summary (string), parties (array of strings), "
        "key_terms (array of objects {term, detail}), "
        "issues (array of objects {severity: one of high|medium|low, issue, recommendation}), "
        "missing_or_weak_clauses (array of strings), overall_recommendation (string)."
    )
    content = await _chat(
        [{"role": "system", "content": system},
         {"role": "user", "content": f"Contract text:\n\n{text[:16000]}"}],
        response_json=True, max_tokens=2200,
    )
    try:
        data = json.loads(content)
    except Exception:  # noqa: BLE001 — model returned non-JSON; keep it visible, don't fabricate
        return {"summary": content[:2000], "parties": [], "key_terms": [],
                "issues": [], "missing_or_weak_clauses": [], "overall_recommendation": "",
                "_parse_note": "model did not return valid JSON; showing raw summary"}
    data.setdefault("parties", [])
    data.setdefault("issues", [])
    data.setdefault("missing_or_weak_clauses", [])
    return data


async def revise_contract(text: str, analysis: dict) -> str:
    system = (
        "You are a contract editor. Produce a REVISED version of the contract in Markdown that "
        "fixes the identified issues and adds any missing or weak clauses, preserving the parties "
        "and original intent. Clearly mark changes inline with **[ADDED]** or **[REVISED]** tags. "
        "Output ONLY the revised contract in Markdown — no preamble."
    )
    issues = json.dumps(analysis.get("issues", []))[:3000]
    missing = json.dumps(analysis.get("missing_or_weak_clauses", []))[:1500]
    return (await _chat(
        [{"role": "system", "content": system},
         {"role": "user", "content":
            f"Original contract:\n\n{text[:14000]}\n\n"
            f"Issues to fix (JSON): {issues}\n"
            f"Missing/weak clauses to add (JSON): {missing}"}],
        max_tokens=4000, temperature=0.3,
    )).strip()
