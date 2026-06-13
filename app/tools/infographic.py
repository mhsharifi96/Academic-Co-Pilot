"""
Infographic generator tool.

``generate_infographic`` turns a brief (e.g. a paper abstract or a set of findings)
into an infographic image. It works in two steps:

  1. A chat model condenses the brief into a tight, layout-oriented image prompt
     (title + a few key points + a clean visual style, with minimal on-image text
     since image models render long text poorly).
  2. ``llm_repo.generate_image`` calls the image model and saves a PNG under
     ``output_figures/``.

This tool WRITES a file, so it is listed in ``INTERRUPT_TOOLS`` (gated behind
approval when ``REQUIRE_TOOL_APPROVAL`` is on), like ``compile_paper``.
"""

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import tool

from app.repositories.llm import llm_repo

_PROMPT_SYSTEM = (
    "You are an information designer. Turn the user's brief into a SINGLE concise "
    "prompt for an image-generation model that will render a clean, modern, "
    "professional infographic. Describe: an overall title, 3-6 key points as "
    "labeled visual elements (icons, simple charts, arrows), a coherent color "
    "palette, and a clear layout (e.g. vertical sections or a grid). Keep any "
    "on-image text SHORT (a title and a few short labels) because image models "
    "render long text poorly. Return ONLY the image prompt, one paragraph, no "
    "preamble."
)


@tool
def generate_infographic(brief: str, title: str = "") -> str:
    """
    Generate an infographic IMAGE from a brief (e.g. a paper summary or key
    findings) and save it as a PNG under `output_figures/`.

    Two steps: a model first turns your brief into a clean infographic design
    prompt, then an image model renders it. Returns the saved file path and the
    prompt used. Note: image models render long text imperfectly, so the design
    keeps on-image text short — best for high-level visual summaries.

    Args:
        brief: What the infographic should convey (abstract, findings, key points).
        title: Optional title to feature on the infographic.
    """
    if not brief or not brief.strip():
        return "Nothing to generate: `brief` was empty."

    # 1. Design prompt (cheap default model is fine for this).
    try:
        user = brief if not title else f"Title: {title}\n\nBrief: {brief}"
        image_prompt = llm_repo.complete(
            [SystemMessage(content=_PROMPT_SYSTEM), HumanMessage(content=user)],
            tier="default",
            temperature=0.4,
        ).strip()
    except Exception as e:
        return f"Error building the infographic prompt: {type(e).__name__}: {e}"

    # 2. Render the image.
    try:
        path = llm_repo.generate_image(
            image_prompt,
            size="1024x1024",
            filename=(title or brief)[:60],
        )
    except Exception as e:
        return f"Error generating the infographic image: {type(e).__name__}: {e}"

    return (
        f"Infographic saved to '{path}'.\n\n"
        f"Design prompt used:\n{image_prompt}"
    )
