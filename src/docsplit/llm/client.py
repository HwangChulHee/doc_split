"""OpenAI client wrapper: prompt-file templating, disk cache, JSON output.

- Cache key = sha256(prompt file hash + model + rendered input) so editing a
  prompt or model invalidates only the affected calls. Cache lives under
  outputs/llm_cache/ (gitignored).
- Retries: up to 2 backoff retries on transient API errors; one re-request on
  invalid JSON, then the failure is recorded and raised.
- Usage (calls/tokens, cache hits) is aggregated per stage into llm_usage.json.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

PROMPT_DIR = Path(__file__).parent / "prompts"
DEFAULT_MODEL = "gpt-5.4-mini"
TRANSIENT_RETRIES = 2


class LLMDisabled(RuntimeError):
    pass


def render_prompt(prompt_name: str, variables: dict[str, str]) -> tuple[str, str]:
    """Load prompts/<name>.md and substitute <<var>> placeholders.

    Returns (rendered_text, prompt_file_sha256).
    """
    raw = (PROMPT_DIR / f"{prompt_name}.md").read_text(encoding="utf-8")
    file_hash = hashlib.sha256(raw.encode()).hexdigest()
    rendered = raw
    for key, val in variables.items():
        rendered = rendered.replace(f"<<{key}>>", val)
    return rendered, file_hash


class LLMClient:
    def __init__(
        self,
        cache_dir: Path,
        usage_path: Path,
        model: str = DEFAULT_MODEL,
        enabled: bool = True,
    ) -> None:
        self.model = model
        self.enabled = enabled
        self.cache_dir = cache_dir
        self.usage_path = usage_path
        self.this_run: dict[str, dict] = {}
        self._client = None
        if enabled:
            load_dotenv()
            if not os.environ.get("OPENAI_API_KEY"):
                raise LLMDisabled(
                    "OPENAI_API_KEY가 없습니다. .env에 키를 넣거나 --no-llm으로 실행하세요 "
                    "(--no-llm: [1] 판정까지 수행, DEFER_LLM은 미판정, [3][4]는 SKIPPED)."
                )
            from openai import OpenAI

            self._client = OpenAI()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ── usage accounting ──────────────────────────────────────
    # Two scopes: ``this_run`` (reset every process) and ``cumulative`` (grows
    # across runs). Reports quote this run so a cached re-run reads as 0 calls.
    @staticmethod
    def _blank_stage() -> dict:
        return {"calls": 0, "cache_hits": 0, "prompt_tokens": 0, "completion_tokens": 0}

    def _record_usage(self, stage: str, cached: bool, usage: dict | None) -> None:
        data = {}
        if self.usage_path.exists():
            data = json.loads(self.usage_path.read_text(encoding="utf-8"))
        cumulative = data.get("cumulative", {})

        for scope in (self.this_run, cumulative):
            st = scope.setdefault(stage, self._blank_stage())
            if cached:
                st["cache_hits"] += 1
            else:
                st["calls"] += 1
                if usage:
                    st["prompt_tokens"] += usage.get("prompt_tokens", 0)
                    st["completion_tokens"] += usage.get("completion_tokens", 0)

        self.usage_path.parent.mkdir(parents=True, exist_ok=True)
        self.usage_path.write_text(
            json.dumps(
                {"model": self.model, "this_run": self.this_run, "cumulative": cumulative},
                indent=2, ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    # ── main entry ────────────────────────────────────────────
    def complete_json(self, stage: str, prompt_name: str, variables: dict[str, str]) -> dict:
        """Render the prompt, call the model (or cache), return parsed JSON."""
        if not self.enabled:
            raise LLMDisabled("LLM 비활성 상태에서 complete_json이 호출되었습니다 (--no-llm).")

        rendered, file_hash = render_prompt(prompt_name, variables)
        key = hashlib.sha256(f"{file_hash}:{self.model}:{rendered}".encode()).hexdigest()
        cache_file = self.cache_dir / f"{key}.json"

        if cache_file.exists():
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            self._record_usage(stage, cached=True, usage=None)
            return cached["parsed"]

        text, usage = self._call(rendered)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            text, usage2 = self._call(rendered)  # one re-request on bad JSON
            usage = {k: usage.get(k, 0) + usage2.get(k, 0) for k in set(usage) | set(usage2)}
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError as e:
                self._record_usage(stage, cached=False, usage=usage)
                raise RuntimeError(f"LLM JSON 파싱 2회 실패 (stage={stage}): {text[:200]}") from e

        cache_file.write_text(
            json.dumps({"parsed": parsed, "usage": usage, "model": self.model}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._record_usage(stage, cached=False, usage=usage)
        return parsed

    def complete_json_vision(
        self, stage: str, prompt_name: str, variables: dict[str, str], image_png: bytes
    ) -> dict:
        """Same contract as complete_json, with one page image attached.

        The image hash joins the cache key, so re-rendering the same page at the
        same dpi is a cache hit while a different render is not.
        """
        if not self.enabled:
            raise LLMDisabled("LLM 비활성 상태에서 complete_json_vision이 호출되었습니다 (--no-llm).")

        rendered, file_hash = render_prompt(prompt_name, variables)
        image_hash = hashlib.sha256(image_png).hexdigest()
        key = hashlib.sha256(
            f"{file_hash}:{self.model}:vision:{image_hash}:{rendered}".encode()
        ).hexdigest()
        cache_file = self.cache_dir / f"{key}.json"

        if cache_file.exists():
            cached = json.loads(cache_file.read_text(encoding="utf-8"))
            self._record_usage(stage, cached=True, usage=None)
            return cached["parsed"]

        text, usage = self._call(rendered, image_png=image_png)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            self._record_usage(stage, cached=False, usage=usage)
            raise RuntimeError(f"VLM JSON 파싱 실패 (stage={stage}): {text[:200]}") from e

        cache_file.write_text(
            json.dumps({"parsed": parsed, "usage": usage, "model": self.model},
                       ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self._record_usage(stage, cached=False, usage=usage)
        return parsed

    def _call(self, prompt: str, image_png: bytes | None = None) -> tuple[str, dict]:
        from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError

        content: str | list = prompt
        if image_png is not None:
            data_uri = "data:image/png;base64," + base64.b64encode(image_png).decode()
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": data_uri}},
            ]

        last_err: Exception | None = None
        for attempt in range(TRANSIENT_RETRIES + 1):
            try:
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": content}],
                    response_format={"type": "json_object"},
                )
                usage = {
                    "prompt_tokens": resp.usage.prompt_tokens if resp.usage else 0,
                    "completion_tokens": resp.usage.completion_tokens if resp.usage else 0,
                }
                return resp.choices[0].message.content or "", usage
            except (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError) as e:
                last_err = e
                time.sleep(2 * (attempt + 1))
        raise RuntimeError(f"LLM 호출이 재시도 후에도 실패: {last_err}") from last_err
