from __future__ import annotations

import fnmatch
import os
from pathlib import Path
from typing import Annotated, Any, TypedDict


SYSTEM_PROMPT = """You are ChemBrain's backend read agent.

Your job is to inspect the repository and answer questions about the codebase.

Rules:
1. You are read-only. Never suggest that you changed files or executed controls.
2. Use tools to inspect files before answering concrete codebase questions.
3. Be explicit when a requested file does not exist.
4. If asked about MATLAB or `.m` files, verify whether any exist before answering.
5. Keep answers grounded in repository contents, especially `CLAUDE.md` when it is relevant.
"""


class ReadAgentState(TypedDict):
    messages: Annotated[list[Any], list.__add__]
    files_touched: Annotated[list[str], list.__add__]
    final_answer: str | None


class ReadAgent:
    def __init__(self, repo_root: str | None = None, model: str = "gpt-5.5"):
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[1]).resolve()
        self.model_name = model
        self._compiled_graph = None
        self._tools: dict[str, Any] = {}
        self._tool_list: list[Any] = []

    def handle(self, query: str) -> dict[str, Any]:
        self._ensure_runtime()

        messages = [
            self._SystemMessage(content=SYSTEM_PROMPT),
            self._HumanMessage(content=query),
        ]
        result = self._compiled_graph.invoke({
            "messages": messages,
            "files_touched": [],
            "final_answer": None,
        })

        files_touched = sorted({path for path in result.get("files_touched", []) if path})
        return {
            "answer": result.get("final_answer") or "",
            "files_touched": files_touched,
            "model": self.model_name,
        }

    def _ensure_runtime(self) -> None:
        if self._compiled_graph is not None:
            return

        try:
            from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
            from langchain_core.tools import tool
            from langchain_openai import ChatOpenAI
            from langgraph.graph import END, START, StateGraph
        except ImportError as exc:
            raise RuntimeError(
                "ReadAgent requires langchain-core, langchain-openai, and langgraph. "
                "Install the updated requirements first."
            ) from exc

        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required to use the LangGraph read agent.")

        self._AIMessage = AIMessage
        self._HumanMessage = HumanMessage
        self._SystemMessage = SystemMessage
        self._ToolMessage = ToolMessage

        @tool
        def list_repo_files(pattern: str = "*") -> dict[str, Any]:
            """List repository files matching a glob pattern, such as '*.py' or 'agents/*.py'."""
            matched = []
            for path in sorted(self.repo_root.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(self.repo_root).as_posix()
                if any(part in {".git", ".venv", "node_modules", "__pycache__", "dist"} for part in path.parts):
                    continue
                if fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern):
                    matched.append(rel)
                if len(matched) >= 200:
                    break
            return {"pattern": pattern, "matches": matched, "count": len(matched)}

        @tool
        def read_repo_file(path: str, start_line: int = 1, end_line: int = 220) -> dict[str, Any]:
            """Read a text file from the repository and return a numbered line excerpt."""
            safe_path = self._resolve_repo_path(path)
            if not safe_path.exists():
                return {"path": path, "error": "File not found."}
            if not safe_path.is_file():
                return {"path": path, "error": "Path is not a file."}

            try:
                raw = safe_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                return {"path": path, "error": "File is not UTF-8 text."}

            start = max(1, start_line)
            end = max(start, min(end_line, start + 400))
            lines = raw.splitlines()
            excerpt = []
            for line_no in range(start, min(end, len(lines)) + 1):
                excerpt.append(f"{line_no:04d}: {lines[line_no - 1]}")

            return {
                "path": safe_path.relative_to(self.repo_root).as_posix(),
                "start_line": start,
                "end_line": min(end, len(lines)),
                "content": "\n".join(excerpt),
            }

        @tool
        def search_repo_text(query: str) -> dict[str, Any]:
            """Search text across repository files and return matching lines."""
            needle = query.lower().strip()
            results = []

            if not needle:
                return {"query": query, "matches": []}

            for path in sorted(self.repo_root.rglob("*")):
                if not path.is_file():
                    continue
                if any(part in {".git", ".venv", "node_modules", "__pycache__", "dist"} for part in path.parts):
                    continue

                try:
                    lines = path.read_text(encoding="utf-8").splitlines()
                except UnicodeDecodeError:
                    continue

                for idx, line in enumerate(lines, start=1):
                    if needle in line.lower():
                        results.append({
                            "path": path.relative_to(self.repo_root).as_posix(),
                            "line": idx,
                            "text": line.strip(),
                        })
                    if len(results) >= 50:
                        return {"query": query, "matches": results}

            return {"query": query, "matches": results}

        self._tool_list = [list_repo_files, read_repo_file, search_repo_text]
        self._tools = {tool_item.name: tool_item for tool_item in self._tool_list}
        llm = ChatOpenAI(model=self.model_name, temperature=0).bind_tools(self._tool_list)

        def llm_node(state: ReadAgentState) -> dict[str, Any]:
            response = llm.invoke(state["messages"])
            return {"messages": [response]}

        def tool_node(state: ReadAgentState) -> dict[str, Any]:
            last_message = state["messages"][-1]
            tool_messages = []
            files_touched = []

            for call in getattr(last_message, "tool_calls", []):
                tool_name = call["name"]
                tool_args = call.get("args", {})
                tool_impl = self._tools[tool_name]
                try:
                    result = tool_impl.invoke(tool_args)
                except Exception as exc:
                    result = {"error": f"{type(exc).__name__}: {exc}"}

                if isinstance(result, dict) and "path" in result and isinstance(result["path"], str):
                    files_touched.append(result["path"])
                if isinstance(result, dict) and "matches" in result:
                    files_touched.extend(
                        match["path"] for match in result["matches"]
                        if isinstance(match, dict) and isinstance(match.get("path"), str)
                    )

                tool_messages.append(
                    ToolMessage(
                        content=str(result),
                        tool_call_id=call["id"],
                    )
                )

            return {
                "messages": tool_messages,
                "files_touched": files_touched,
            }

        def finalize_node(state: ReadAgentState) -> dict[str, Any]:
            last_message = state["messages"][-1]
            content = getattr(last_message, "content", "")
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                content = "\n".join(part for part in text_parts if part)
            return {"final_answer": content if isinstance(content, str) else str(content)}

        def next_step(state: ReadAgentState) -> str:
            last_message = state["messages"][-1]
            return "tools" if getattr(last_message, "tool_calls", None) else "finalize"

        graph = StateGraph(ReadAgentState)
        graph.add_node("llm", llm_node)
        graph.add_node("tools", tool_node)
        graph.add_node("finalize", finalize_node)
        graph.add_edge(START, "llm")
        graph.add_conditional_edges("llm", next_step, {
            "tools": "tools",
            "finalize": "finalize",
        })
        graph.add_edge("tools", "llm")
        graph.add_edge("finalize", END)

        self._compiled_graph = graph.compile()

    def _resolve_repo_path(self, user_path: str) -> Path:
        candidate = (self.repo_root / user_path).resolve()
        if self.repo_root not in candidate.parents and candidate != self.repo_root:
            raise ValueError(f"Path escapes repository root: {user_path}")
        return candidate
