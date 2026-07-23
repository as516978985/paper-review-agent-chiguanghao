from __future__ import annotations

import json
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class McpClient:
    def __init__(self, server_path: Path):
        self.server_path = server_path
        self.session = None
        self.tools: list[dict] = []

    async def __aenter__(self):
        parameters = StdioServerParameters(
            command=sys.executable,
            args=[str(self.server_path)],
        )
        self.transport = stdio_client(parameters)
        read, write = await self.transport.__aenter__()
        self.session_context = ClientSession(read, write)
        self.session = await self.session_context.__aenter__()
        await self.session.initialize()
        listed = await self.session.list_tools()
        self.tools = [{
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema or {"type": "object"},
        } for tool in listed.tools]
        return self

    async def __aexit__(self, *args):
        await self.session_context.__aexit__(*args)
        await self.transport.__aexit__(*args)

    def llm_tools(self) -> list[dict]:
        return [{
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool["description"],
                "parameters": tool["parameters"],
            },
        } for tool in self.tools]

    async def call(self, name: str, arguments: dict) -> dict:
        result = await self.session.call_tool(name, arguments)
        structured = getattr(result, "structuredContent", None)
        if structured:
            return structured
        texts = [part.text for part in result.content if getattr(part, "type", "") == "text"]
        raw = "\n".join(texts)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"text": raw}