"""Route the site's text "Generate with AI" calls through Google Gemini.

The views call `Groq(...).chat.completions.create(...)` or
`OpenAI(...).chat.completions.create(...)` in ~50 places (descriptions, titles,
suggestions, chatbots). Rather than edit every call site, `install()` wraps
`Completions.create` of both SDKs: when the server has a `GEMINI_API_KEY`, a
plain text chat request is answered by Gemini (REST `generateContent`); if the
key is missing, the request is not plain text (images, tools, streaming), or
Gemini fails, the original Groq/OpenAI call runs exactly as before.

Settings (environment / .env, never in code):
    GEMINI_API_KEY   the key from https://aistudio.google.com (free tier works)
    GEMINI_MODEL     optional, default "gemini-2.5-flash"
"""
import logging
import os
import time
from types import SimpleNamespace

logger = logging.getLogger(__name__)

_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _to_gemini(messages):
    """OpenAI-style messages -> (systemInstruction | None, contents) or None."""
    system_parts, contents = [], []
    for m in messages:
        content = m.get("content")
        if not isinstance(content, str):
            return None  # images / multi-part: leave to the original SDK
        role = m.get("role")
        if role == "system":
            system_parts.append(content)
        else:
            contents.append(
                {
                    "role": "model" if role == "assistant" else "user",
                    "parts": [{"text": content}],
                }
            )
    if not contents:
        return None
    system = {"parts": [{"text": "\n\n".join(system_parts)}]} if system_parts else None
    return system, contents


def gemini_chat(messages, *, temperature=None, max_tokens=None, json_mode=False):
    """Answer [messages] with Gemini; return the text or raise."""
    import requests

    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    converted = _to_gemini(messages)
    if converted is None:
        raise ValueError("not a plain text request")
    system, contents = converted
    model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash").strip()
    body = {"contents": contents}
    if system:
        body["systemInstruction"] = system
    gen = {}
    if temperature is not None:
        gen["temperature"] = temperature
    if max_tokens:
        gen["maxOutputTokens"] = int(max_tokens)
    if json_mode:
        gen["responseMimeType"] = "application/json"
    if gen:
        body["generationConfig"] = gen

    last = None
    for attempt in range(2):
        resp = requests.post(
            _URL.format(model=model),
            params={"key": key},
            json=body,
            timeout=40,
        )
        if resp.status_code in (429, 500, 503) and attempt == 0:
            last = resp
            time.sleep(1.5)
            continue
        resp.raise_for_status()
        data = resp.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(p.get("text", "") for p in parts).strip()
        except (KeyError, IndexError, TypeError):
            raise RuntimeError("Gemini returned no text: %s" % str(data)[:300])
        if not text:
            raise RuntimeError("Gemini returned an empty answer")
        return text
    last.raise_for_status()


def _as_completion(text, model):
    msg = SimpleNamespace(role="assistant", content=text)
    choice = SimpleNamespace(index=0, message=msg, finish_reason="stop")
    return SimpleNamespace(
        id="gemini",
        object="chat.completion",
        model=model,
        choices=[choice],
        usage=None,
    )


def _wrap(original):
    def create(self, *args, **kwargs):
        if os.environ.get("GEMINI_API_KEY", "").strip() and not args:
            messages = kwargs.get("messages")
            plain = (
                isinstance(messages, (list, tuple))
                and not kwargs.get("stream")
                and not kwargs.get("tools")
                and not kwargs.get("functions")
                and not kwargs.get("n", 1) > 1
            )
            if plain:
                fmt = kwargs.get("response_format") or {}
                try:
                    text = gemini_chat(
                        list(messages),
                        temperature=kwargs.get("temperature"),
                        max_tokens=kwargs.get("max_tokens")
                        or kwargs.get("max_completion_tokens"),
                        json_mode=isinstance(fmt, dict)
                        and fmt.get("type") == "json_object",
                    )
                    return _as_completion(text, kwargs.get("model", "gemini"))
                except Exception as exc:  # fall back to Groq / OpenAI
                    logger.warning("Gemini failed (%s); using the original AI client", exc)
        return original(self, *args, **kwargs)

    create._gemini_wrapped = True
    return create


def install():
    """Wrap Groq's and OpenAI's chat `create` (idempotent)."""
    targets = []
    try:
        from groq.resources.chat.completions import Completions as G

        targets.append(G)
    except Exception:  # pragma: no cover - SDK missing
        pass
    try:
        from openai.resources.chat.completions import Completions as O

        targets.append(O)
    except Exception:  # pragma: no cover
        pass
    for cls in targets:
        if not getattr(cls.create, "_gemini_wrapped", False):
            cls.create = _wrap(cls.create)
