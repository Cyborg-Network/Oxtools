import os
import time
from openai import OpenAI
from config import logger


def _call_api(
    client: OpenAI,
    model: str,
    messages: list[dict],
    max_tokens: int,
    temperature: float = 0.0,
    attempt_limit: int = 3,
) -> str:
    """
    NEW #10: timeout raised to 600s per attempt.
    The judge with full HTML context can take 4-5 minutes to respond.
    Total max wait = 3 attempts × 600s + 2 × 8s backoff = ~30 minutes worst case.
    That is acceptable for maximum fidelity.
    """
    import httpx
    last_exc: Exception = RuntimeError("No attempts made")

    for attempt in range(attempt_limit):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=float(os.getenv("OXLO_API_TIMEOUT", "600.0")),  # NEW #10: was 180s
            )
            return resp.choices[0].message.content or ""

        except Exception as exc:
            last_exc = exc
            err_str = str(exc).lower()
            is_rate    = "429" in err_str
            is_server  = any(c in err_str for c in ("500", "502", "503", "504"))
            is_timeout = "timeout" in err_str or isinstance(exc, httpx.TimeoutException)

            if (is_rate or is_server or is_timeout) and attempt < attempt_limit - 1:
                wait = 4 ** (attempt + 1)  # 4s, 16s
                logger.warning(
                    "[%s] attempt %d failed (%s...), retry in %ds",
                    model, attempt + 1, err_str[:80], wait
                )
                time.sleep(wait)
            else:
                break

    raise RuntimeError(f"[{model}] failed after {attempt_limit} attempts: {last_exc}")
