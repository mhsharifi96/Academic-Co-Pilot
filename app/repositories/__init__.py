"""Repositories: provider-agnostic seams for external services (LLM, images)."""

from app.repositories.llm import LLMRepository, llm_repo

__all__ = ["LLMRepository", "llm_repo"]
