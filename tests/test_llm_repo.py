"""
Offline unit tests for the LLM repository's pure logic
(app/repositories/llm). No network — we only check tier->model resolution and the
filename slug helper, not actual model/image calls.
"""

from app.core.config import settings
from app.repositories.llm import llm_repo, _slugify


def test_model_name_resolves_tiers():
    orig_default, orig_power = settings.OPENAI_MODEL, settings.POWERFUL_MODEL
    try:
        settings.OPENAI_MODEL = "cheap-model"
        settings.POWERFUL_MODEL = "power-model"
        assert llm_repo.model_name("default") == "cheap-model"
        assert llm_repo.model_name("powerful") == "power-model"
        # Unknown/blank tier falls back to default.
        assert llm_repo.model_name() == "cheap-model"
    finally:
        settings.OPENAI_MODEL, settings.POWERFUL_MODEL = orig_default, orig_power


def test_slugify_filenames():
    assert _slugify("Hello, World!") == "hello_world"
    assert _slugify("  Spaces  and---dashes  ") == "spaces_and_dashes"
    assert _slugify("") == "image"
    assert _slugify("", default="fallback") == "fallback"
    assert len(_slugify("x" * 200)) <= 60
