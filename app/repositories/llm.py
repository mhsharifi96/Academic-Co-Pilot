"""
Central LLM / image-generation repository.

This is the ONE place the rest of the app should go through to talk to a language
model or an image model.  Today it is backed by OpenAI (chat via LangChain's
``ChatOpenAI``, images via the ``openai`` SDK).  To switch provider in the future
— or to route a tier to a different vendor — change this file only; callers keep
using ``llm_repo.complete(...)`` / ``llm_repo.generate_image(...)`` unchanged.

Two model "tiers" are exposed so cheap, high-volume work and expensive, high-stakes
work can use different models:

  - ``"default"``  -> ``settings.OPENAI_MODEL``   (the agents' everyday model)
  - ``"powerful"`` -> ``settings.POWERFUL_MODEL`` (e.g. gpt-5.5; used by the
    reference checker and the humanizer, which need stronger reasoning)

NOTE: the existing agent/tool code still constructs ``ChatOpenAI`` directly; this
repository is currently used by the newer tools.  New code should prefer it.
"""

import os
import base64
import re
from typing import Any, List, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings

Tier = Literal["default", "powerful"]

# Generated images are written here (shared with the analytics sandbox).
OUTPUT_DIR = "output_figures"


def _slugify(text: str, default: str = "image") -> str:
    """Filesystem-safe slug for an output filename."""
    slug = re.sub(r"[^a-z0-9]+", "_", (text or "").lower()).strip("_")
    return (slug[:60] or default)


class LLMRepository:
    """Provider-agnostic access to chat and image models."""

    def model_name(self, tier: Tier = "default") -> str:
        """Resolve a tier to a concrete model name from settings."""
        return settings.POWERFUL_MODEL if tier == "powerful" else settings.OPENAI_MODEL

    def get_chat_model(
        self,
        tier: Tier = "default",
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> BaseChatModel:
        """
        Return a chat model for ``tier``.  Swap the provider here (e.g. to
        ``ChatAnthropic``) to migrate every caller at once.
        """
        return ChatOpenAI(
            model=self.model_name(tier),
            api_key=settings.OPENAI_API_KEY,
            temperature=temperature,
            **kwargs,
        )

    def complete(
        self,
        messages: List[BaseMessage],
        tier: Tier = "default",
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> str:
        """
        Invoke a chat model with a list of messages and return the text content.

        Mirrors the ``.invoke([SystemMessage, HumanMessage]) -> .content`` pattern
        used throughout the tools, but routed through the repository so the model
        choice lives in one place.
        """
        model = self.get_chat_model(tier=tier, temperature=temperature, **kwargs)
        resp = model.invoke(messages)
        content = resp.content
        return content if isinstance(content, str) else str(content)

    def generate_image(
        self,
        prompt: str,
        *,
        size: str = "1024x1024",
        filename: str | None = None,
    ) -> str:
        """
        Generate an image from ``prompt`` and save it as a PNG under
        ``output_figures/``.  Returns the saved file path.

        Backed by the OpenAI Images API (``settings.IMAGE_MODEL``, default
        ``gpt-image-1``).  Raises on failure — callers (tools) should catch and
        convert to a friendly error string so the agent never crashes.
        """
        # Imported lazily so importing this module doesn't require the openai SDK
        # until image generation is actually used.
        from openai import OpenAI

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        result = client.images.generate(
            model=settings.IMAGE_MODEL,
            prompt=prompt,
            size=size,
            n=1,
        )
        b64 = result.data[0].b64_json
        if not b64:
            raise RuntimeError("Image API returned no image data.")
        image_bytes = base64.b64decode(b64)

        name = _slugify(filename or prompt)
        path = os.path.join(OUTPUT_DIR, f"{name}.png")
        with open(path, "wb") as f:
            f.write(image_bytes)
        return path


# Module-level singleton used across the app.
llm_repo = LLMRepository()
