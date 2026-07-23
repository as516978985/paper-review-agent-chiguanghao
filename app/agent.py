from __future__ import annotations

import json
import time
from typing import Awaitable, Callable

from openai import AsyncOpenAI

from .config import settings
from .mcp_client import McpClient
from .memory import MemoryStore, identify_document
from .skill_runtime import SkillRuntime

Emit = Callable[[dict], Awaitable[None]]

SYSTEM_PROMPT = """角色：论文规范审核 Agent。

严格执行以下要求：
1. 先读取两个 SKILL.md 和需要的规则文件。
2. 调用 inspect_document_format 获取格式证据。
3. 逐条识别参考文献；存在 DOI 时调用 check_citation，不存在 DOI 时调用 search_by_title。
4. 调用 run_recent_ratio 计算近五年占比。
5. 外部查询失败时写"暂缓判断"，没有证据时写"未能核实"。
6. 历史记录只用于整改对比，本次仍重新检查。
7. 输出 Markdown，包含基本信息、格式摘要、问题明细、文献核验、近五年统计、
   优先修改项、与上次审核对比、总体结论和限制说明。
8. 不编造工具结果，不修改原文。
"""


class ReviewAgent:
    def __init__(
        self,
        document_text: str,
        format_analysis: dict,
        review_year: int,
        memory: MemoryStore,
        emit: Emit,
    ):
        self.document_text = document_text
        self.format_analysis = format_analysis
        self.review_year = review_year
        self.memory = memory
        self.emit = emit
        self.format_skill = SkillRuntime(
            settings.format_skill, "read_format_skill_file"
        )
        self.citation_skill = SkillRuntime(
            settings.citation_skill, "read_citation_skill_file", with_ratio=True
        )

    async def run(self) -> str:
        identity = identify_document(self.document_text)

        started = time.perf_counter()
        previous = await self.memory.latest(identity)
        await self.emit({
            "type": "memory_loaded",
            "found": bool(previous),
            "elapsed_ms": round((time.perf_counter() - started) * 1000),
        })

        history = "无历史记录"
        if previous:
            history = (
                f"上次审核版本：{previous['revision_no']}\n"
                f"上次审核时间：{previous['created_at']}\n"
                f"上次意见：\n{previous['report_text'][:12000]}"
            )

        client = AsyncOpenAI(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
        )

        async with McpClient(settings.mcp_server) as mcp:
            tools = [
                *self.format_skill.tools(),
                *self.citation_skill.tools(),
                {
                    "type": "function",
                    "function": {
                        "name": "inspect_document_format",
                        "description": "取得本次 DOCX 的确定性格式检查结果",
                        "parameters": {"type": "object", "properties": {}},
                    },
                },
                *mcp.llm_tools(),
            ]

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"审核年度：{self.review_year}\n\n"
                        f"历史记录：\n{history}\n\n"
                        f"待审文档：\n{self.document_text}"
                    ),
                },
            ]

            for round_no in range(1, 21):
                started = time.perf_counter()
                await self.emit({"type": "llm_started", "round": round_no})
                response = await client.chat.completions.create(
                    model=settings.llm_model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.1,
                )
                message = response.choices[0].message
                await self.emit({
                    "type": "llm_finished",
                    "round": round_no,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000),
                })

                assistant_message = {
                    "role": "assistant",
                    "content": message.content or "",
                }
                if message.tool_calls:
                    assistant_message["tool_calls"] = [
                        call.model_dump() for call in message.tool_calls
                    ]
                messages.append(assistant_message)

                if not message.tool_calls:
                    report = message.content or "模型未返回审核意见。"
                    revision = await self.memory.save(
                        identity,
                        self.document_text,
                        report,
                        self.review_year,
                        settings.llm_model,
                    )
                    await self.emit({"type": "memory_saved", "revision": revision})
                    await self.emit({"type": "completed", "report": report})
                    return report

                for call in message.tool_calls:
                    name = call.function.name
                    try:
                        arguments = json.loads(call.function.arguments or "{}")
                    except json.JSONDecodeError:
                        arguments = {}
                    started = time.perf_counter()
                    await self.emit({"type": "tool_started", "name": name})
                    result = await self._dispatch(name, arguments, mcp)
                    await self.emit({
                        "type": "tool_finished",
                        "name": name,
                        "elapsed_ms": round((time.perf_counter() - started) * 1000),
                    })
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })

        report = "达到最大工具调用轮次，未生成完整报告。"
        await self.emit({"type": "completed", "report": report})
        return report

    async def _dispatch(self, name: str, arguments: dict, mcp: McpClient) -> dict:
        if name == "inspect_document_format":
            return self.format_analysis
        if name in {"read_format_skill_file"}:
            return await self.format_skill.call(name, arguments)
        if name in {"read_citation_skill_file", "run_recent_ratio"}:
            return await self.citation_skill.call(name, arguments)
        if name in {tool["name"] for tool in mcp.tools}:
            return await mcp.call(name, arguments)
        return {"error": "unknown_tool", "name": name}