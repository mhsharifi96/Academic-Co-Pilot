import os
import re
import pandas as pd
import matplotlib.pyplot as plt
from typing import Any, Dict
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_experimental.utilities.python import PythonREPL
from app.core.config import settings

# Ensure output directory exists
OUTPUT_DIR = "output_figures"
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# How many times to run the code in total before giving up: 1 initial attempt
# plus up to 2 LLM-assisted self-healing retries.
MAX_ATTEMPTS = 3

class SecurePythonREPL:
    def __init__(self):
        # Pre-seed the namespace with the common data-analysis libraries so the
        # agent doesn't have to import them every turn.
        import numpy as np
        import networkx as nx
        from wordcloud import WordCloud

        namespace = {
            "__builtins__": __builtins__,
            "pd": pd,
            "np": np,
            "plt": plt,
            "nx": nx,
            "WordCloud": WordCloud,
        }
        # CRITICAL: use the SAME dict for globals and locals. PythonREPL calls
        # exec(code, globals, locals); with two distinct dicts, top-level imports
        # land in `locals` but functions/lambdas/comprehensions resolve free names
        # against `globals` only -> intermittent "NameError: name 'pd' is not
        # defined" inside .apply()/comprehensions even after a successful import.
        self.repl = PythonREPL(_globals=namespace, _locals=namespace)

    def run(self, code: str) -> str:
        # Pre-execution checks or setup can go here
        return self.repl.run(code)

python_repl = SecurePythonREPL()


# PythonREPL.worker returns repr(e) (a single line like
# ``NameError("name 'df' is not defined")``) on failure instead of raising, and
# the captured stdout on success.  Detect the error form so we can retry.
_ERROR_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.]*(Error|Exception|Interrupt|Exit)\b")


def _looks_like_error(output: str) -> bool:
    """True if PythonREPL output is an exception repr / traceback, not real output."""
    if not output or not output.strip():
        return False
    if "Traceback (most recent call last)" in output:
        return True
    return bool(_ERROR_RE.match(output.strip().splitlines()[0]))


def _strip_code_fences(text: str) -> str:
    """Remove ```python ... ``` fences an LLM may wrap the code in."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _repair_code(code: str, error: str) -> str:
    """
    Ask the LLM to fix code that errored in the sandbox.

    Returns corrected, self-contained Python (no markdown fences), or an empty
    string if the repair call itself fails — in which case the caller stops
    retrying.
    """
    try:
        llm = ChatOpenAI(model=settings.OPENAI_MODEL, temperature=0)
        system = (
            "You are a Python debugging assistant for a data-analysis sandbox "
            "(pandas, numpy, matplotlib, networkx, wordcloud pre-imported as pd, "
            "np, plt, nx, WordCloud).\n"
            "The sandbox is effectively STATELESS between tool calls: never assume "
            "a variable such as `df` already exists. The script must be fully "
            "self-contained — re-read any CSV/Excel files with pandas at the top.\n"
            "Plots must be saved with plt.savefig('output_figures/<name>.png'); never "
            "call plt.show(). Always print() the results you want to surface.\n"
            "Given the failing code and its error, return a CORRECTED, complete "
            "script that fixes the error. Return ONLY raw Python code — no markdown "
            "fences, no commentary."
        )
        human = (
            f"Failing code:\n{code}\n\n"
            f"Error it produced:\n{error}\n\n"
            "Return the corrected, self-contained script."
        )
        resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
        content = resp.content if isinstance(resp.content, str) else str(resp.content)
        return _strip_code_fences(content)
    except Exception:
        return ""


@tool
def analytics_sandbox(code: str, feedback: str = None) -> str:
    """
    A secure Python sandbox for data analysis and visualization.
    Use this to execute pandas, matplotlib, and numpy code.

    Pre-imported and ready to use (no import needed): pandas as `pd`, numpy as
    `np`, matplotlib.pyplot as `plt`, networkx as `nx` (graphs/networks), and
    `WordCloud` (from the wordcloud package, for word-cloud images).

    Guidelines:
    - Treat each call as a FRESH environment: do NOT rely on variables (e.g. `df`)
      from a previous call. Write self-contained scripts that re-read any CSV/Excel
      files they need with pd.read_csv(...) at the top.
    - You can read CSV and Excel files generated by other tools.
    - When creating plots, graphs, or word clouds, ALWAYS save them to the
      'output_figures' directory using plt.savefig('output_figures/filename.png').
    - Do not try to show() plots as there is no GUI.
    - Focus on data analysis, summary statistics, and visualization.
    - Always print() the results you want to see.

    If the code raises an error, the sandbox automatically inspects the error and
    retries with corrected code (up to 2 times) before reporting back.

    Args:
        code: The Python code to execute.
        feedback: Extra user considerations or specific constraints for the code execution.
    """
    current_code = code
    errors: list[str] = []

    for attempt in range(1, MAX_ATTEMPTS + 1):
        execution_code = current_code
        if feedback:
            # Prepend feedback as a comment for context in the execution log;
            # its primary use is the agent's prompt context.
            execution_code = f"# User Feedback: {feedback}\n" + current_code

        try:
            output = python_repl.run(execution_code)
        except Exception as e:  # defensive: PythonREPL normally returns repr(e)
            output = f"{type(e).__name__}: {e}"

        if not _looks_like_error(output):
            note = ""
            if attempt > 1:
                note = (
                    f"(Recovered after {attempt} attempts — the code was "
                    "automatically corrected.)\n"
                )
            return f"Execution Result:\n{note}{output}"

        # Error: record it and try to self-heal unless we've run out of attempts.
        errors.append(f"Attempt {attempt} error:\n{output}")
        if attempt < MAX_ATTEMPTS:
            fixed = _repair_code(current_code, output)
            # Stop early if repair failed or produced no real change.
            if not fixed or fixed.strip() == current_code.strip():
                break
            current_code = fixed

    return (
        f"Error executing code after {len(errors)} attempt(s). The sandbox does not "
        "retain variables between calls, so every script must be self-contained "
        "(re-read any CSV/Excel files with pd.read_csv at the top; do not assume a "
        "variable like `df` already exists).\n\n"
        + "\n\n".join(errors)
        + "\n\nPlease rewrite the code as a single self-contained script and try again."
    )
