"""
Oxtools Tool Template
======================
Copy this entire directory to create a new Python tool:

  cp -r tools/_template tools/my-tool

Then edit tool.py with your logic. That's it!

Directory structure:
  my-tool/
  ├── tool.py              ← Entry point (MANIFEST + run) — YOU EDIT THIS
  ├── requirements.txt     ← Your pip dependencies
  └── (any other files)    ← Helpers, configs, data, etc.
"""

# ─── MANIFEST (required) ─────────────────────────────────────────────
MANIFEST = {
    "id": "my-tool",                    # URL-safe ID (used in /api/tools/{id})
    "name": "My Awesome Tool",          # Human-readable name
    "description": "One-line description of what this tool does",
    "author": "Your Name",
    "version": "1.0.0",
}


# ─── RUN FUNCTION (required) ─────────────────────────────────────────
async def run(data: dict) -> dict:
    """
    Execute the tool.

    Args:
        data: Request body from the frontend form.
              Example: {"query": "user input", "model": "llama-3.3-70b"}

    Returns:
        dict with a "result" key containing the output.
    """
    query = data.get("query", "")

    # ── Your tool logic goes here! ──
    # You can:
    #   - Import helper modules from this same directory
    #   - Use os.getenv("OXLO_API_KEY") for the Oxlo API
    #   - Use any packages listed in requirements.txt
    #   - Return a dict (JSON response) or an async generator (streaming)

    result = f"Processed: {query}"

    return {
        "result": result,
        "metadata": {
            "model_used": "none",
            "processing_time": "0.1s",
        },
    }


# ─── STREAMING EXAMPLE (optional) ────────────────────────────────────
# For long-running tools (AI agents, research, etc.), return an async
# generator instead of a dict. The runner streams it to the frontend.
#
# async def run(data: dict):
#     yield "[step-1] Planning...\n"
#     # ... do work ...
#     yield "[step-2] Searching...\n"
#     # ... do work ...
#     yield "\n---RESULT---\n"
#     yield "Final output here"
