from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path


class SkillRuntime:
    def __init__(self, directory: Path, read_tool_name: str, with_ratio: bool = False):
        self.directory = directory.resolve()
        self.read_tool_name = read_tool_name
        self.with_ratio = with_ratio
        raw = (self.directory / "SKILL.md").read_text(encoding="utf-8")
        self.name = self._frontmatter(raw, "name")
        self.description = self._frontmatter(raw, "description")

    @staticmethod
    def _frontmatter(raw: str, key: str) -> str:
        for line in raw.splitlines():
            if line.startswith(f"{key}:"):
                return line.split(":", 1)[1].strip()
        return ""

    def files(self) -> list[str]:
        return sorted(
            str(path.relative_to(self.directory))
            for path in self.directory.rglob("*")
            if path.is_file() and "__pycache__" not in path.parts
        )

    def tools(self) -> list[dict]:
        result = [{
            "type": "function",
            "function": {
                "name": self.read_tool_name,
                "description": f"读取 {self.name} 内的规则文件",
                "parameters": {
                    "type": "object",
                    "properties": {"path": {"type": "string"}},
                    "required": ["path"],
                },
            },
        }]
        if self.with_ratio:
            result.append({
                "type": "function",
                "function": {
                    "name": "run_recent_ratio",
                    "description": "计算近五年文献数量和占比",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "years": {"type": "array", "items": {"type": ["integer", "null"]}},
                            "review_year": {"type": "integer"},
                        },
                        "required": ["years", "review_year"],
                    },
                },
            })
        return result

    async def call(self, name: str, arguments: dict) -> dict:
        if name == self.read_tool_name:
            target = (self.directory / str(arguments.get("path", ""))).resolve()
            try:
                target.relative_to(self.directory)
            except ValueError:
                return {"error": "path_escape"}
            if not target.is_file():
                return {"error": "not_found", "files": self.files()}
            return {"path": str(target.relative_to(self.directory)),
                    "content": target.read_text(encoding="utf-8")[:20000]}

        if name == "run_recent_ratio" and self.with_ratio:
            years = ["NA" if value is None else str(value)
                     for value in arguments.get("years", [])]
            script = self.directory / "scripts" / "recent_ratio.py"
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(script), "--years", *years,
                "--review-year", str(arguments["review_year"]),
                stdout=asyncio.subprocess.PIPE,
            )
            output, _ = await process.communicate()
            return json.loads(output.decode("utf-8"))

        return {"error": "unknown_skill_tool", "name": name}