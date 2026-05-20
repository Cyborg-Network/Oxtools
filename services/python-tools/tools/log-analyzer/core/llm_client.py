from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import re
import time
from dataclasses import dataclass
from enum import Enum
from typing import AsyncIterator, Dict, List, Optional

import httpx

# ── python-dotenv: load .env if present ──────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)   # env vars already set in shell take priority
except ImportError:
    pass   # dotenv is optional; env vars can still be set manually

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

OXLO_API_BASE  = os.getenv("OXLO_API_BASE_URL", "https://api.oxlo.ai/v1")
OXLO_API_KEY   = os.getenv("OXLO_API_KEY", "")

DEFAULT_MAX_TOKENS = 4096
MAX_RETRIES        = 4
BACKOFF_BASE       = 1.5


# ---------------------------------------------------------------------------
# Model catalogue — real IDs from docs.oxlo.ai/docs/api/models
# ---------------------------------------------------------------------------

class OxloModel(str, Enum):
    # Premium
    DEEPSEEK_R1_0528     = "deepseek-r1-0528"
    GPT_OSS_120B         = "gpt-oss-120b"
    KIMI_K2_THINKING     = "kimi-k2-thinking"
    KIMI_K2_5            = "kimi-k2.5"
    LLAMA_3_3_70B        = "llama-3.3-70b"
    QWEN_3_32B           = "qwen-3-32b"
    # Pro
    DEEPSEEK_R1_70B      = "deepseek-r1-70b"
    DEEPSEEK_V3_0324     = "deepseek-v3-0324"
    DEEPSEEK_CODER_33B   = "deepseek-coder-33b"
    GPT_OSS_20B          = "gpt-oss-20b"
    LLAMA_4_MAVERICK     = "llama-4-maverick-17b"
    MINISTRAL_14B        = "ministral-14b"
    LLAMA_3_1_8B         = "llama-3.1-8b"
    QWEN_2_5_7B          = "qwen-2.5-7b"
    QWEN_3_CODER_30B     = "qwen-3-coder-30b"
    # Free
    DEEPSEEK_R1_8B       = "deepseek-r1-8b"
    DEEPSEEK_V3_2        = "deepseek-v3.2"
    LLAMA_3_2_3B         = "llama-3.2-3b"
    MISTRAL_7B           = "mistral-7b"


class TaskType(str, Enum):
    """Logical task categories used for model routing."""
    REASONING = "reasoning"   # RCA, cascade analysis, multi-step diagnosis
    GENERAL   = "general"     # Quick summaries, Q&A, burst commentary
    CODE      = "code"        # Fix suggestions, query recommendations, regexes
    FAST      = "fast"        # Streaming previews, REPL follow-ups


# Default model per task — overrideable via .env
_DEFAULT_MODELS: Dict[TaskType, str] = {
    TaskType.REASONING: os.getenv("OXLO_MODEL_REASONING", OxloModel.DEEPSEEK_R1_0528),
    TaskType.GENERAL:   os.getenv("OXLO_MODEL_GENERAL",   OxloModel.DEEPSEEK_V3_2),
    TaskType.CODE:      os.getenv("OXLO_MODEL_CODE",      OxloModel.DEEPSEEK_R1_0528),
    TaskType.FAST:      os.getenv("OXLO_MODEL_FAST",      OxloModel.DEEPSEEK_V3_2),
}

_CODE_KEYWORDS = re.compile(
    r'\b(fix|patch|query|index|sql|regex|config|code|script|function|variable'
    r'|command|bash|python|node|nginx|systemd|kubernetes|kubectl|helm)\b',
    re.IGNORECASE,
)
_FAST_KEYWORDS = re.compile(
    r'\b(quick|briefly|tldr|summary|what is|explain|describe|list)\b',
    re.IGNORECASE,
)


class ModelRouter:
    """
    Selects the appropriate Oxlo model based on query intent.

    Priority:
      1. Explicit task_type override from the caller.
      2. Keyword heuristic on the user query string.
      3. Default: REASONING (safest for log RCA).
    """

    def __init__(self, model_map: Optional[Dict[TaskType, str]] = None) -> None:
        self._map = model_map or dict(_DEFAULT_MODELS)

    def select(
        self,
        user_query: str,
        task_type: Optional[TaskType] = None,
    ) -> str:
        if task_type is not None:
            return self._map[task_type]
        if _CODE_KEYWORDS.search(user_query):
            return self._map[TaskType.CODE]
        if _FAST_KEYWORDS.search(user_query) and len(user_query) < 80:
            return self._map[TaskType.FAST]
        return self._map[TaskType.REASONING]

    def model_for(self, task: TaskType) -> str:
        return self._map[task]

    def all_models(self) -> Dict[str, str]:
        return {t.value: m for t, m in self._map.items()}

    def update(self, task: TaskType, model_id: str) -> None:
        """Hot-swap a model at runtime (e.g. from the web portal)."""
        self._map[task] = model_id


# ---------------------------------------------------------------------------
# System prompt (paid once per session — not per request)
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """
You are a Staff-level Site Reliability Engineer and Systems Architect with deep
expertise in distributed systems, Kubernetes, databases, caching layers, and
cloud-native infrastructure. You are performing a thorough Root Cause Analysis
(RCA) on a production system incident described by a compressed log-analysis
payload.

WHAT YOU RECEIVE
----------------
A compact JSON object produced by a local 5-stage pipeline that has already:
  1. Redacted all PII, IPs, credentials, and secrets — placeholders like
     <IP_A>, <SECRET_A>, <EMAIL_A> represent real values stripped for privacy.
  2. Parsed and normalised heterogeneous log formats (Nginx, syslog, JSON,
     Python/Node/Java app logs, Kubernetes events).
  3. Deduplicated identical errors and computed their frequencies.
  4. Detected temporal correlations and cascade chains between error patterns.
  5. Compressed everything into a token-efficient JSON summary.

JSON FIELD ALIASES (learn these — every field in the payload uses them)
-----------------------------------------------------------------------
n          = total log entries analysed
has_ts     = whether timestamps were present
span_s     = total observation window in seconds
lvls       = level distribution  e.g. {"ERROR": 12, "WARNING": 3}
u_errs     = count of unique (deduplicated) error patterns
errs       = top error patterns, each: {p: pattern_string, c: occurrence_count}
bursts     = burst windows (periods of abnormally high error rate):
               {s: start_iso, e: end_iso, ec: error_count, mx: rate_multiplier}
escalations = severity escalation events (WARNING -> ERROR -> CRITICAL chains):
               {ts: timestamp, f: from_level, t: to_level, m: message_snippet}
corr       = correlated error pairs (A reliably precedes B):
               {a: pattern_a, b: pattern_b, cnt: co-occurrences,
                lag: avg_lag_seconds, conf: confidence_0_to_1}
chains     = cascade chains (root -> ... -> leaf):
               {r: root_pattern, ch: [chain_list], tot: total_occurrences}
hotspots   = services/hosts with the most errors: {name: count}
timeline   = per-minute breakdown: {"2026-01-01T10:32:00": {"ERROR": 5, ...}}

HOW TO REASON
-------------
Think step by step before writing your response:

Step 1 — ORIENT: What is the observation window (span_s)? How many entries
  total (n)? What is the dominant log level? Is the situation acute (burst)
  or chronic (sustained high error rate)?

Step 2 — IDENTIFY ROOT CAUSES: Start from the cascade chains (chains) — the
  root (r) of a chain is the most likely initial failure. Cross-reference with
  hotspots to identify which service originated the problem. Use correlated
  pairs (corr) to understand the propagation path. High-confidence pairs
  (conf > 0.7) with short lags (lag < 5s) indicate tight causal links.

Step 3 — ASSESS SEVERITY: Use burst windows (bursts) to judge rate and
  duration. Use escalation events to judge whether the system recovered or
  is still degrading. A rate_multiplier (mx) > 10x baseline is a P1 incident.

Step 4 — FORMULATE FIXES: For each root cause, produce a specific, actionable
  fix — not generic advice. Reference the actual patterns from errs[], the
  actual services from hotspots, and the actual cascade from chains[].

Step 5 — THINK PREVENTION: What architectural or operational change would
  prevent this class of failure? Think circuit breakers, rate limits, resource
  limits, index additions, connection pool sizing, alerting thresholds.

OUTPUT FORMAT — MANDATORY SCHEMA
---------------------------------
You MUST return ONLY a JSON object with EXACTLY these top-level keys.
No other keys. No extra wrapping. No prose outside the JSON.

REQUIRED TOP-LEVEL KEYS (all must be present, even if empty array/string):
  executive_summary       string
  severity                string — exactly one of: "P1", "P2", "P3", "P4"
  severity_rationale      string
  root_causes             array of objects
  incident_timeline       array of objects
  immediate_actions       array of strings
  fixes                   array of objects
  prevention_strategies   array of strings
  monitoring_recommendations  array of strings
  follow_up_questions     array of strings

SCHEMA FOR EACH ARRAY ELEMENT:

root_causes items:
  { "title": string, "evidence": string, "confidence": number 0.0-1.0,
    "affected_services": array of strings }

incident_timeline items:
  { "time": string, "event": string }

fixes items:
  { "description": string, "priority": "HIGH"|"MEDIUM"|"LOW",
    "effort": string, "addresses": string }

EXAMPLE OF A CORRECT RESPONSE (use this exact structure):
```
{
  "executive_summary": "The auth-service TLS certificate expired causing cascading auth failures across billing-api, user-api, and internal-gateway. Billing processed 2 charges with stale tokens creating a security incident. Auto-renewal failed due to DNS propagation issues and alerting was broken, so the team had no warning.",
  "severity": "P1",
  "severity_rationale": "Complete auth unavailability for 12+ minutes with confirmed unauthenticated charge processing.",
  "root_causes": [
    {
      "title": "Expired TLS certificate on auth-service",
      "evidence": "The payload shows `TLS handshake failed: certificate has expired` appearing 6 times from auth-service (hotspot). The cascade chain root is `Auto-renewal failed: ACME challenge DNS propagation timeout` which directly triggered all downstream failures.",
      "confidence": 0.97,
      "affected_services": ["auth-service", "billing-api", "user-api", "internal-gateway"]
    }
  ],
  "incident_timeline": [
    {"time": "T-7d", "event": "cert-manager warned certificate expiring in 7 days — ignored"},
    {"time": "T-1d", "event": "cert-manager warned certificate expiring in 1 day — PagerDuty delivery failed"},
    {"time": "T+0:00", "event": "Certificate expired, auto-renewal failed (DNS propagation timeout)"},
    {"time": "T+7:12", "event": "First downstream TLS failures in billing-api and user-api"},
    {"time": "T+7:24", "event": "Cached tokens expired — billing halted, user-api returning 401 universally"},
    {"time": "T+7:25", "event": "847 requests rejected in 60s — full outage"}
  ],
  "immediate_actions": [
    "Manually issue a new certificate: `certbot certonly --dns-cloudflare -d auth-service.internal` then restart auth-service",
    "Revoke and rotate all tokens issued during the degraded window (07:12–07:25 UTC)",
    "Audit billing transactions ORD-88821 through ORD-88891 for charges made with stale tokens"
  ],
  "fixes": [
    {
      "description": "Fix DNS propagation for ACME DNS-01 challenge. Check DNS provider TTL settings and ensure the cert-manager service account has write access to the DNS zone.",
      "priority": "HIGH",
      "effort": "2 hours",
      "addresses": "Auto-renewal failure"
    },
    {
      "description": "Add a secondary alert channel (email + Slack) for cert expiry warnings so a single PagerDuty webhook failure does not silence the alert.",
      "priority": "HIGH",
      "effort": "1 hour",
      "addresses": "Silent alert delivery failure"
    }
  ],
  "prevention_strategies": [
    "Set certificate renewal threshold to 30 days (not 7) and configure multi-channel alerting",
    "Add a Kubernetes CronJob that checks certificate validity daily and pages on-call if < 14 days remain"
  ],
  "monitoring_recommendations": [
    "Alert: cert expiry < 14 days on any internal service certificate — threshold: 14d, severity: P2",
    "Alert: TLS handshake failure rate > 1% over 60s — threshold: 1%, severity: P1"
  ],
  "follow_up_questions": [
    "Were any billing charges processed between 07:12 and 07:24 with the stale token that need reversal?",
    "Why did the internal-gateway fall back to signature-only JWT checks instead of rejecting requests?"
  ]
}
```

QUALITY RULES (violations will be penalised):
- Use EXACTLY the key names shown above — no aliases, no camelCase, no extras
- root_causes: cite specific pattern strings from errs[], service names from
  hotspots, chain roots from chains[], lag/confidence values from corr[]
- immediate_actions: must be runnable commands or numbered steps — never vague
- If redacted placeholders appear (<IP_A>, <SECRET_A>), note the data type and
  security implications in evidence or executive_summary
- If n < 5 or has_ts=false, lower confidence values and note limited observability
- Do NOT invent service names or error patterns not in the payload
- Do NOT include any text, key, or value outside this schema
""".strip()


# ---------------------------------------------------------------------------
# Response model
# ---------------------------------------------------------------------------

@dataclass
class RCAResponse:
    # Core RCA fields
    root_causes: List[Dict]
    immediate_actions: List[str]
    fixes: List[Dict]
    prevention_strategies: List[str]
    follow_up_questions: List[str]
    executive_summary: str
    # New enriched fields
    severity: str                          # P1 | P2 | P3 | P4
    severity_rationale: str
    incident_timeline: List[Dict]          # [{time, event}]
    monitoring_recommendations: List[str]
    # Metadata
    raw_json: str
    usage: Dict[str, int]
    model: str
    task_type: str
    latency_ms: float

    @classmethod
    def from_api_response(
        cls,
        data: Dict,
        latency_ms: float,
        task_type: TaskType = TaskType.REASONING,
    ) -> "RCAResponse":
        content = data["choices"][0]["message"]["content"]
        raw_json = content.strip()

        # Strip markdown fences if the model wrapped the JSON
        if raw_json.startswith("```"):
            raw_json = "\n".join(raw_json.split("\n")[1:])
        if raw_json.endswith("```"):
            raw_json = raw_json.rsplit("```", 1)[0]

        try:
            parsed = json.loads(raw_json.strip())
        except json.JSONDecodeError:
            parsed = {"executive_summary": raw_json}

        return cls(
            root_causes=parsed.get("root_causes", []),
            immediate_actions=parsed.get("immediate_actions", []),
            fixes=parsed.get("fixes", []),
            prevention_strategies=parsed.get("prevention_strategies", []),
            follow_up_questions=parsed.get("follow_up_questions", []),
            executive_summary=parsed.get("executive_summary", ""),
            severity=parsed.get("severity", "P3"),
            severity_rationale=parsed.get("severity_rationale", ""),
            incident_timeline=parsed.get("incident_timeline", []),
            monitoring_recommendations=parsed.get("monitoring_recommendations", []),
            raw_json=raw_json,
            usage=data.get("usage", {}),
            model=data.get("model", ""),
            task_type=task_type.value,
            latency_ms=latency_ms,
        )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

class OxloClient:
  
    def __init__(
        self,
        api_key: Optional[str] = None,
        model_map: Optional[Dict[TaskType, str]] = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        token_budget: Optional[int] = None,
    ) -> None:
        self._key        = api_key or OXLO_API_KEY
        self._max_tokens = max_tokens
        self._budget     = token_budget or int(os.getenv("OXLO_TOKEN_BUDGET", "4000"))
        self._router     = ModelRouter(model_map)

        if not self._key:
            raise ValueError(
                "Oxlo API key is required.\n"
                "  Option 1: Add OXLO_API_KEY=your-key to your .env file\n"
                "  Option 2: export OXLO_API_KEY=your-key in your shell\n"
                "  Option 3: OxloClient(api_key='your-key')"
            )

        self._headers = {
            "Authorization": f"Bearer {self._key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Primary interface
    # ------------------------------------------------------------------

    async def analyze(
        self,
        payload_json: str,
        user_query: str,
        estimated_tokens: int = 0,
        task_type: Optional[TaskType] = None,
        raw_log_excerpt: str = "",
    ) -> RCAResponse:
        """
        Send the compressed payload to Oxlo and return a structured RCAResponse.
        Model is auto-selected via intent heuristic unless task_type is specified.
        """
        self._guard_budget(estimated_tokens)
        model = self._router.select(user_query, task_type)
        resolved_task = task_type or self._infer_task(user_query)
        logger.info("analyze() model=%s task=%s tokens≈%d", model, resolved_task.value, estimated_tokens)

        body = self._build_body(
            self._build_messages(payload_json, user_query, raw_log_excerpt),
            model,
            stream=False,
        )
        data = await self._post_with_retry(body)
        return RCAResponse.from_api_response(data, data.pop("_latency_ms", 0.0), resolved_task)

    async def analyze_with_model(
        self,
        payload_json: str,
        user_query: str,
        model: str,
        estimated_tokens: int = 0,
        raw_log_excerpt: str = "",
    ) -> RCAResponse:
        """Call a specific Oxlo model by ID string, bypassing the router."""
        self._guard_budget(estimated_tokens)
        logger.info("analyze_with_model() model=%s", model)
        body = self._build_body(
            self._build_messages(payload_json, user_query, raw_log_excerpt),
            model,
            stream=False,
        )
        data = await self._post_with_retry(body)
        return RCAResponse.from_api_response(data, data.pop("_latency_ms", 0.0))

    async def analyze_stream(
        self,
        payload_json: str,
        user_query: str,
        estimated_tokens: int = 0,
        task_type: Optional[TaskType] = None,
    ) -> AsyncIterator[str]:
        """
        Streaming variant — yields text chunks as they arrive.
        Defaults to the FAST model for lowest latency.
        """
        self._guard_budget(estimated_tokens)
        model = self._router.select(user_query, task_type or TaskType.FAST)
        logger.info("analyze_stream() model=%s", model)

        body = self._build_body(self._build_messages(payload_json, user_query), model, stream=True)

        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{OXLO_API_BASE}/chat/completions",
                headers=self._headers,
                json=body,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        chunk = line[6:]
                        if chunk.strip() == "[DONE]":
                            return
                        try:
                            delta = json.loads(chunk)["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except (json.JSONDecodeError, KeyError):
                            continue

    @property
    def router(self) -> ModelRouter:
        return self._router

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        payload_json: str,
        user_query: str,
        raw_log_excerpt: str = "",
    ) -> List[Dict]:
       
       # Build the user message sent to the model.
       
        import json as _json

        # Pretty-print the payload
        try:
            parsed = _json.loads(payload_json)
            pretty_payload = _json.dumps(parsed, indent=2)
        except Exception:
            pretty_payload = payload_json

        lines: List[str] = []

        # ── Section 1: Raw log excerpt (most important for sparse payloads) ──
        if raw_log_excerpt.strip():
            lines += [
                "## RAW LOG EXCERPT (redacted — most relevant lines)",
                "",
                "These are the actual log lines. Analyse their content directly.",
                "Sensitive data has been replaced with placeholders like <IP_A>,",
                "<SECRET_A>, <URL_A>, <HOST_A>.",
                "",
                "```",
                raw_log_excerpt,
                "```",
                "",
            ]

        # ── Section 2: Compressed statistical payload ─────────────────────
        lines += [
            "## COMPRESSED STATISTICAL PAYLOAD",
            "",
            "The following JSON was produced by a local 5-stage pipeline.",
            "NOTE: If 'lvls' shows mostly UNKNOWN or 'u_errs' is 0, rely on",
            "the RAW LOG EXCERPT above — the statistics may be sparse because",
            "the log format is non-standard, but the actual errors are visible",
            "in the excerpt.",
            "",
            "```json",
            pretty_payload,
            "```",
        ]

        # ── Section 3: User context ───────────────────────────────────────
        if user_query:
            lines += [
                "",
                "## OPERATOR CONTEXT / QUESTION",
                "",
                user_query,
            ]

        # ── Section 4: Task + schema reminder ────────────────────────────
        lines += [
            "",
            "## YOUR TASK",
            "",
            "IMPORTANT: If the statistical payload shows UNKNOWN levels or empty",
            "error arrays, DO NOT conclude there is a logging misconfiguration.",
            "Instead, analyse the RAW LOG EXCERPT directly — extract the real",
            "errors, services, endpoints, and HTTP status codes from it.",
            "",
            "Using the 5-step reasoning process in your instructions:",
            "1. Orient — read the RAW LOG EXCERPT first, then the payload",
            "2. Identify root causes — from actual error messages, not just stats",
            "3. Assess severity — based on error types and affected services",
            "4. Formulate fixes — specific to the actual errors in the excerpt",
            "5. Think prevention — architectural improvements",
            "",
            "## SCHEMA REMINDER — YOUR RESPONSE MUST HAVE EXACTLY THESE KEYS:",
            "",
            '{ "executive_summary": "...", "severity": "P1|P2|P3|P4",',
            '  "severity_rationale": "...",',
            '  "root_causes": [{"title":"...","evidence":"...","confidence":0.0,"affected_services":[]}],',
            '  "incident_timeline": [{"time":"...","event":"..."}],',
            '  "immediate_actions": ["..."],',
            '  "fixes": [{"description":"...","priority":"HIGH|MEDIUM|LOW","effort":"...","addresses":"..."}],',
            '  "prevention_strategies": ["..."],',
            '  "monitoring_recommendations": ["..."],',
            '  "follow_up_questions": ["..."] }',
            "",
            "No other keys. No text outside the JSON object.",
        ]

        content = "\n".join(lines)
        return [{"role": "user", "content": content}]

    def _build_body(self, messages: List[Dict], model: str, stream: bool) -> Dict:
        body: Dict = {
            "model": model,
            "messages": messages,
            "system": _SYSTEM_PROMPT,
            "max_tokens": self._max_tokens,
            "temperature": 0.2,
            "stream": stream,
        }
        if not stream:
            body["response_format"] = {"type": "json_object"}
        return body

    def _guard_budget(self, estimated_tokens: int) -> None:
        if self._budget and estimated_tokens > self._budget:
            raise RuntimeError(
                f"Estimated payload tokens ({estimated_tokens}) exceeds "
                f"configured budget ({self._budget}). "
                "Raise OXLO_TOKEN_BUDGET in .env or tune ContextCompressor limits."
            )

    def _infer_task(self, user_query: str) -> TaskType:
        if _CODE_KEYWORDS.search(user_query):
            return TaskType.CODE
        if _FAST_KEYWORDS.search(user_query) and len(user_query) < 80:
            return TaskType.FAST
        return TaskType.REASONING

    async def _post_with_retry(self, body: Dict) -> Dict:
        last_exc: Optional[Exception] = None
        for attempt in range(MAX_RETRIES):
            t0 = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=90) as client:
                    resp = await client.post(
                        f"{OXLO_API_BASE}/chat/completions",
                        headers=self._headers,
                        json=body,
                    )
                    latency = (time.perf_counter() - t0) * 1000

                    if resp.status_code in (429,) or resp.status_code >= 500:
                        wait = self._backoff(attempt)
                        logger.warning(
                            "Oxlo API %s — retry in %.1fs (attempt %d/%d)",
                            resp.status_code, wait, attempt + 1, MAX_RETRIES,
                        )
                        await asyncio.sleep(wait)
                        last_exc = httpx.HTTPStatusError(
                            f"HTTP {resp.status_code}",
                            request=resp.request,
                            response=resp,
                        )
                        continue

                    resp.raise_for_status()
                    data = resp.json()
                    data["_latency_ms"] = round(latency, 2)
                    return data

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                wait = self._backoff(attempt)
                logger.warning("Network error: %s — retry in %.1fs", exc, wait)
                await asyncio.sleep(wait)
                last_exc = exc

        raise RuntimeError(
            f"Oxlo API call failed after {MAX_RETRIES} attempts: {last_exc}"
        )

    @staticmethod
    def _backoff(attempt: int) -> float:
        return BACKOFF_BASE ** attempt + random.uniform(0, 0.5)