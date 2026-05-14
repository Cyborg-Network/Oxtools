import os

import httpx

OXLO_BASE_URL = os.getenv("OXLO_BASE_URL", "https://api.oxlo.ai/v1")
OXLO_API_KEY = os.getenv("OXLO_API_KEY", "")
_CLIENT: httpx.AsyncClient | None = None


class OxloError(RuntimeError):
    pass


def _get_client() -> httpx.AsyncClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = httpx.AsyncClient()
    return _CLIENT


async def call_oxlo_chat(
    model: str,
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 2048,
    temperature: float = 0.3,
) -> str:
    if not OXLO_API_KEY:
        raise OxloError("OXLO_API_KEY not configured")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    client = _get_client()
    resp = await client.post(
        f"{OXLO_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {OXLO_API_KEY}"},
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    return data["choices"][0]["message"]["content"].strip()
