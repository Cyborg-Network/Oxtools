"""
Oxtools Unified Python Tool Runner
====================================
A single FastAPI service that auto-discovers and runs ALL Python tools.

Tool Structure:
  services/python-tools/tools/
  ├── my-tool/
  │   ├── tool.py            ← Entry point (must have MANIFEST + run)
  │   ├── helpers.py         ← Any supporting files
  │   ├── prompts/           ← Any subdirectories
  │   └── requirements.txt   ← This tool's pip deps
  └── another-tool/
      ├── tool.py
      └── requirements.txt

Contributors:
  1. Create a directory: tools/my-tool/
  2. Add tool.py with MANIFEST dict + async run(data) function
  3. Add requirements.txt for pip deps
  4. Register in Next.js frontend
  5. Done! No Docker knowledge needed.

The runner auto-discovers all tools/{name}/tool.py at startup.
"""

import os
import sys
import json
import time
import logging
import importlib
import importlib.util
import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
)
logger = logging.getLogger("tool-runner")


# ---------------------------------------------------------------------------
# Tool Registry
# ---------------------------------------------------------------------------

class ToolRegistry:
    """
    Discovers and manages Python tools from the tools/ directory.

    Each tool is a DIRECTORY containing at minimum a tool.py file with:
      - MANIFEST: dict with {id, name, description, ...}
      - async def run(request_data: dict) -> dict | AsyncGenerator

    Contributors can add any number of supporting files, subdirectories,
    configs, etc. inside their tool directory.
    """

    def __init__(self, tools_dir: str):
        self.tools_dir = Path(tools_dir)
        self.tools: dict[str, dict[str, Any]] = {}

    def discover(self):
        """Scan tools/ for directories containing tool.py."""
        if not self.tools_dir.exists():
            logger.warning(f"Tools directory not found: {self.tools_dir}")
            return

        for tool_dir in sorted(self.tools_dir.iterdir()):
            # Skip files and hidden/underscore dirs
            if not tool_dir.is_dir():
                continue
            if tool_dir.name.startswith(("_", ".")):
                continue

            entry_point = tool_dir / "tool.py"
            if not entry_point.exists():
                logger.warning(f"Skipping {tool_dir.name}/: no tool.py found")
                continue

            self._load_tool(tool_dir, entry_point)

        logger.info(f"═══ Tool discovery complete: {len(self.tools)} tools loaded ═══")

    def _load_tool(self, tool_dir: Path, entry_point: Path):
        """Load a single tool from its directory."""
        tool_name = tool_dir.name
        module_name = f"tools.{tool_name}.tool"

        try:
            # Add the tool directory to sys.path so it can import its own modules
            tool_path = str(tool_dir)
            if tool_path not in sys.path:
                sys.path.insert(0, tool_path)

            # Also add parent tools/ dir for cross-tool imports
            tools_path = str(self.tools_dir)
            if tools_path not in sys.path:
                sys.path.insert(0, tools_path)

            # Load the module from file path directly
            spec = importlib.util.spec_from_file_location(module_name, str(entry_point))
            if spec is None or spec.loader is None:
                logger.error(f"✗ Cannot load {tool_name}/tool.py: invalid module spec")
                return

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Validate required interface
            if not hasattr(module, "MANIFEST"):
                logger.warning(f"✗ {tool_name}/tool.py: missing MANIFEST dict")
                return
            if not hasattr(module, "run"):
                logger.warning(f"✗ {tool_name}/tool.py: missing run() function")
                return

            manifest = module.MANIFEST
            tool_id = manifest.get("id", tool_name)

            self.tools[tool_id] = {
                "id": tool_id,
                "module": module,
                "manifest": manifest,
                "directory": str(tool_dir),
                "entry_point": str(entry_point),
            }

            logger.info(f"  ✓ {tool_id} — {manifest.get('name', tool_name)}")

        except Exception as e:
            logger.error(f"  ✗ {tool_name}: {e}")
            logger.debug(traceback.format_exc())

    def get_tool(self, tool_id: str) -> dict | None:
        return self.tools.get(tool_id)

    def list_tools(self) -> list[dict]:
        return [
            {
                "id": t["id"],
                "name": t["manifest"].get("name", t["id"]),
                "description": t["manifest"].get("description", ""),
                "author": t["manifest"].get("author", "Community"),
                "version": t["manifest"].get("version", "1.0.0"),
            }
            for t in self.tools.values()
        ]


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

TOOLS_DIR = os.getenv("TOOLS_DIR", "/app/tools")
registry = ToolRegistry(TOOLS_DIR)

app = FastAPI(
    title="Oxtools Python Tool Runner",
    description="Unified service that auto-discovers and runs all Python tools",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Discover all tools on startup."""
    logger.info(f"Scanning for tools in: {TOOLS_DIR}")
    registry.discover()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "python-tool-runner",
        "version": "2.0.0",
        "tools_loaded": len(registry.tools),
        "tool_ids": list(registry.tools.keys()),
    }


@app.get("/api/tools")
async def list_tools():
    return {"tools": registry.list_tools()}


@app.post("/api/tools/{tool_id}")
async def run_tool(tool_id: str, request: Request):
    """Execute a Python tool by ID."""
    tool = registry.get_tool(tool_id)
    if not tool:
        raise HTTPException(
            status_code=404,
            detail=f"Tool '{tool_id}' not found. Available: {list(registry.tools.keys())}"
        )

    try:
        body = await request.json()
    except Exception:
        body = {}

    try:
        start = time.time()
        logger.info(f"[{tool_id}] Executing...")

        result = await tool["module"].run(body)

        # Async generator → stream response with keepalive
        if hasattr(result, "__aiter__"):
            async def stream():
                import asyncio
                async for chunk in result:
                    if isinstance(chunk, dict):
                        yield json.dumps(chunk) + "\n"
                    else:
                        yield str(chunk)

            async def stream_with_keepalive():
                """Wrap stream with keepalive pings to prevent timeout."""
                import asyncio
                queue = asyncio.Queue()

                async def producer():
                    try:
                        logger.info(f"[Producer] Task started")
                        async for chunk in result:
                            if isinstance(chunk, dict):
                                await queue.put(json.dumps(chunk) + "\n")
                            else:
                                await queue.put(str(chunk))
                        logger.info(f"[Producer] LangGraph generator finished normally!")
                    except asyncio.CancelledError:
                        logger.error(f"[Producer] Task was CANCELLED!")
                        raise
                    except Exception as e:
                        logger.error(f"Stream producer error: {e}")
                    except BaseException as e:
                        logger.error(f"[Producer] BaseException: {e}")
                        raise
                    finally:
                        logger.info(f"[Producer] Task exiting, sending EOF")
                        await queue.put(None)  # EOF marker

                # Start the producer in the background
                producer_task = asyncio.create_task(producer())
                
                # CRITICAL: Keep a strong reference in a GLOBAL scope.
                # Previously, storing it on the queue created a reference cycle
                # (queue -> task -> producer coroutine -> queue) which Python's
                # cyclic garbage collector would silently destroy!
                if not hasattr(app, "_active_tasks"):
                    app._active_tasks = set()
                app._active_tasks.add(producer_task)
                producer_task.add_done_callback(app._active_tasks.discard)

                get_task = None
                while True:
                    try:
                        if get_task is None:
                            get_task = asyncio.create_task(queue.get())
                            
                        # Wait for either the queue item or the timeout
                        done, pending = await asyncio.wait(
                            [get_task], 
                            timeout=10.0,
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        
                        if get_task in done:
                            chunk = get_task.result()
                            get_task = None  # Reset for next iteration
                            
                            if chunk is None:
                                logger.info("[Stream] Received EOF from queue, breaking loop")
                                break
                            yield chunk
                        else:
                            # Timeout occurred, get_task is still pending
                            logger.info("[Stream] Keepalive timeout, yielding dot")
                            yield ".\n"
                    except asyncio.CancelledError:
                        logger.error("[Stream] stream_with_keepalive was CANCELLED by Starlette!")
                        raise
                    except Exception as e:
                        logger.error(f"[Stream] Unexpected error in stream loop: {e}")
                        break
                
                logger.info("[Stream] stream_with_keepalive completely finished")
                
                logger.info("Exited stream_with_keepalive loop.")

            return StreamingResponse(
                stream_with_keepalive(),
                media_type="text/plain",
                headers={
                    "X-Content-Type-Options": "nosniff",
                    "X-Accel-Buffering": "no",
                    "Cache-Control": "no-cache",
                },
            )

        elapsed = time.time() - start
        logger.info(f"[{tool_id}] Completed in {elapsed:.1f}s")

        if isinstance(result, dict):
            return JSONResponse(result)
        return JSONResponse({"result": str(result)})

    except Exception as e:
        logger.error(f"[{tool_id}] Error: {e}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    # reload=True ensures that changes to Python files in the mounted volume
    # automatically restart the server without needing to restart Docker!
    uvicorn.run("runner:app", host="0.0.0.0", port=9080, reload=True)
