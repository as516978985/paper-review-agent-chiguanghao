# 论文规范审核 Agent 开发练习手册

从空目录开始构建一个论文规范审核 Agent。完成环境安装、格式规则、SKILL、MCP、决策 LLM、MySQL 记忆、DOCX 检查、Web 接口和页面开发，最终形成可以独立运行的完整应用。

---

## 目标

完成以下流程：

1. 上传 DOCX 文件；
2. 提取正文、表格和排版属性；
3. 按院系规范检查纸张、页边距、章节顺序、字体、字号、缩进和行距；
4. 读取格式检查 SKILL 和参考文献审核 SKILL；
5. 通过 MCP 查询 Crossref，核验 DOI、题名、作者和年份；
6. 由决策 LLM 自主选择工具并生成审核意见；
7. 使用 MySQL 保存同一提交人、同一论文的历次审核记录；
8. 再次提交修改版时，对比已修正、仍存在和新增问题；
9. 通过网页查看执行轨迹、MCP、SKILL 和最终报告。

成功标准：从空目录完成全部文件后，上传 DOCX 能够生成格式检查结果和参考文献审核意见；再次上传同一论文的修改版后，能够读取历史记录并保存新版本。

---

## 架构说明

```text
浏览器
  │ 上传 DOCX、发起审核、显示执行轨迹
  ▼
FastAPI Web 服务
  │
  ├── DOCX 确定性检查
  │     页面、章节、字体、字号、缩进、行距
  │
  ├── 两个 SKILL
  │     格式检查流程、文献审核流程、报告要求
  │
  ├── citation-check MCP
  │     DOI 查询、题名检索、字段比对
  │
  ├── 决策 LLM
  │     选择工具、读取证据、生成报告
  │
  └── MySQL 记忆
        历史意见、文档哈希、审核版本
```

---

## 需要安装的内容

| 软件或服务 | 要求 | 用途 | 获取方式 |
|---|---:|---|---|
| Python | 3.10+ | 运行 Agent、MCP 和 Web 服务 | https://www.python.org/downloads/ |
| Visual Studio Code | 稳定版 | 编辑 Python、JSON、Markdown 和 HTML | https://code.visualstudio.com/ |
| MySQL | 8.0+ | 保存历史审核记录 | https://dev.mysql.com/downloads/mysql/ |
| Git | 2.40+ | 本地版本管理 | https://git-scm.com/downloads |
| Chrome 或 Edge | 当前版本 | 使用网页和开发者工具 | 官方网站 |
| LLM API Key | 有效密钥 | 调用支持工具调用的决策模型 | 模型服务商控制台 |

Windows 使用 PowerShell 执行命令。macOS 和 Linux 使用终端执行命令。

---

## 1. 安装 Python

### 1.1 Windows 安装

1. 访问 https://www.python.org/downloads/
2. 下载 Python 3.12 的 64 位安装程序。
3. 运行安装程序。
4. 勾选 **Add python.exe to PATH**。
5. 点击 **Install Now**。
6. 安装完成后重新打开 PowerShell。
7. 执行：

```powershell
python --version
python -m pip --version
```

两条命令均应显示版本号，Python 版本不得低于 3.10。

### 1.2 macOS 安装

```bash
brew install python@3.12
python3 --version
python3 -m pip --version
```

未安装 Homebrew 时，使用 Python 官方安装包。

---

## 2. 安装 Visual Studio Code

1. 访问 https://code.visualstudio.com/
2. 下载对应操作系统的安装包。
3. 使用默认选项完成安装。
4. 安装 Python、Pylance、Markdown All in One 三个扩展。
5. Windows 安装时勾选 **Add to PATH**。
6. 重新打开 PowerShell，执行：

```powershell
code --version
```

---

## 3. 安装 Git

1. 访问 https://git-scm.com/downloads
2. 下载对应操作系统的安装包。
3. 使用默认选项完成安装。
4. 重新打开 PowerShell，执行：

```powershell
git --version
```

---

## 4. 安装 MySQL

### 4.1 Windows 安装

1. 访问 https://dev.mysql.com/downloads/installer/
2. 下载 MySQL Installer Community。
3. 运行安装程序，选择 **Server only**。
4. 安装 MySQL Server 8.0。
5. 保留端口 `3306`。
6. 设置 `root` 密码并妥善保存。
7. 将 MySQL 配置为 Windows 服务。
8. 完成安装并启动服务。

### 4.2 macOS 安装

```bash
brew install mysql
brew services start mysql
mysql_secure_installation
```

### 4.3 创建数据库和账号

```powershell
mysql -u root -p
```

输入 `root` 密码后执行：

```sql
CREATE DATABASE paper_review_agent
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

CREATE USER 'paper_review_agent'@'localhost'
  IDENTIFIED BY 'PaperReview_2026';

GRANT SELECT, INSERT, UPDATE, CREATE, INDEX
  ON paper_review_agent.*
  TO 'paper_review_agent'@'localhost';

FLUSH PRIVILEGES;
EXIT;
```

正式使用时替换示例密码。

---

## 5. 创建项目目录

Windows PowerShell 执行：

```powershell
mkdir -Force $HOME\paper-review-agent
cd $HOME\paper-review-agent

mkdir app
mkdir skills
mkdir skills\format-review
mkdir skills\format-review\references
mkdir skills\citation-review
mkdir skills\citation-review\references
mkdir skills\citation-review\scripts
mkdir mcp_server
mkdir resources
mkdir scripts
mkdir static
mkdir tests

New-Item app\__init__.py -ItemType File
```

macOS 或 Linux 执行：

```bash
mkdir -p "$HOME/paper-review-agent"/{app,mcp_server,resources,scripts,static,tests}
mkdir -p "$HOME/paper-review-agent/skills/format-review/references"
mkdir -p "$HOME/paper-review-agent/skills/citation-review/references"
mkdir -p "$HOME/paper-review-agent/skills/citation-review/scripts"
cd "$HOME/paper-review-agent"
touch app/__init__.py
```

使用 VS Code 打开目录：

```powershell
code .
```

---

## 6. 创建虚拟环境

Windows PowerShell 执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

PowerShell 阻止脚本执行时，先执行：

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

macOS 或 Linux 执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

升级 pip：

```powershell
python -m pip install --upgrade pip
```

命令行开头出现 `(.venv)` 后继续。

---

## 7. 创建依赖文件

创建文件：

```powershell
notepad requirements.txt
```

macOS 使用：

```bash
code requirements.txt
```

写入：

```text
mcp>=1.12,<2
requests>=2.32,<3
openai>=1.50,<2
fastapi>=0.115,<1
uvicorn>=0.30,<1
python-docx>=1.1,<2
PyMySQL>=1.1,<2
python-dotenv>=1.0,<2
python-multipart>=0.0.9,<1
```

保存后安装：

```powershell
python -m pip install -r requirements.txt
```

执行导入检查：

```powershell
python -c "import fastapi, mcp, openai, pymysql, requests, docx; print('依赖安装完成')"
```

---

## 8. 创建环境变量

创建文件：

```powershell
notepad .env
```

写入：

```env
LLM_API_KEY=替换为实际密钥
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=paper_review_agent
MYSQL_PASSWORD=PaperReview_2026
MYSQL_DATABASE=paper_review_agent

CROSSREF_MAILTO=替换为联系邮箱
REVIEW_YEAR=2026
```

创建 `.gitignore`：

```powershell
notepad .gitignore
```

写入：

```gitignore
.env
.venv/
__pycache__/
*.pyc
*.log
```

API Key 和数据库密码只保存在 `.env`。

---

## 9. 编写院系格式规范

先建立可阅读的规范文档，再建立供程序读取的 JSON 规则。

### 9.1 创建规范说明

创建文件：

```powershell
notepad resources\计算机学院本科毕业论文格式规范.md
```

写入：

```markdown
# 计算机学院本科毕业论文格式规范

## 一、页面设置

1. 使用 A4 纸张，宽 21.0 cm，高 29.7 cm。
2. 上页边距 2.5 cm，下页边距 2.5 cm。
3. 左页边距 3.0 cm，右页边距 2.5 cm。

## 二、字体与段落

1. 论文题目使用黑体，18 pt，加粗。
2. 一级标题使用黑体，16 pt，加粗。
3. 二级标题使用黑体，14 pt，加粗。
4. 正文使用宋体，12 pt。
5. 正文首行缩进约 0.74 cm，行距为 1.5 倍。

## 三、章节顺序

依次设置摘要、关键词、ABSTRACT、目录、绪论、系统设计、结论、参考文献、致谢。

## 四、参考文献

1. 每条文献保留作者、题名、来源和年份。
2. 存在 DOI 时写明 DOI。
3. 按 GB/T 7714 的对应文献类型整理著录字段。
4. 近五年文献比例不得低于 50%。

## 五、复核要求

无法从 DOCX 属性稳定取得的项目标记为“无法判断”，保留人工复核入口。
```

### 9.2 创建机器可读规则

创建文件：

```powershell
notepad skills\format-review\references\format-policy.json
```

写入：

```json
{
  "policy_id": "CS-THESIS-FMT-2026-01",
  "page": {
    "width_cm": 21.0,
    "height_cm": 29.7,
    "top_margin_cm": 2.5,
    "bottom_margin_cm": 2.5,
    "left_margin_cm": 3.0,
    "right_margin_cm": 2.5,
    "tolerance_cm": 0.2
  },
  "typography": {
    "title": {"font": "黑体", "size_pt": 18.0, "bold": true},
    "body": {
      "font": "宋体",
      "size_pt": 12.0,
      "first_line_indent_cm": 0.74,
      "line_spacing": 1.5
    }
  },
  "required_sections": [
    "摘要",
    "关键词",
    "ABSTRACT",
    "目录",
    "绪论",
    "系统设计",
    "结论",
    "参考文献",
    "致谢"
  ],
  "recent_reference_ratio": 0.5
}
```

执行语法检查：

```powershell
python -m json.tool skills/format-review/references/format-policy.json
```

---

## 10. 编写格式检查 SKILL

创建文件：

```powershell
notepad skills\format-review\SKILL.md
```

写入：

```markdown
---
name: format-review
description: 检查 DOCX 论文的页面设置、章节顺序、字体、字号、缩进和行距。
---

# 论文格式检查

## 执行流程

1. 读取 `references/format-policy.json`。
2. 调用 `inspect_document_format` 获取 DOCX 的实际属性。
3. 按页面设置、章节结构和正文样式逐项判定。
4. 每项保留规则值、实际值、状态和位置证据。
5. 将问题分为必须修改、建议修改和无法判断。

## 判定边界

- 只有取得实际属性时才判定符合或不符合。
- 缺少字号、字体、页边距或行距证据时标记 `unknown`。
- 不根据视觉印象或模型记忆推断格式。
- 不修改原文，只输出证据和修改意见。

## 输出要求

- 写明规则编号。
- 汇总检查项总数、符合、不符合和无法判断数量。
- 字号使用 pt，长度使用 cm。
- 章节问题列出缺失项和实际顺序。
```

---

## 11. 编写参考文献审核 SKILL

### 11.1 创建审核规则

创建文件：

```powershell
notepad skills\citation-review\references\review-rules.md
```

写入：

```markdown
# 参考文献审核规则

## 结论分级

- 已核实：外部数据源存在记录，题名、作者和年份等关键字段一致。
- 未能核实：未取得足够外部证据，不直接认定记录不存在。
- 字段错配：标识符存在，但提交字段与登记字段不一致。
- 暂缓判断：网络失败、超时或外部服务不可用。

## 近五年口径

审核年度和向前四个年度组成近五年区间。审核年度为 2026 时，统计区间为 2022 至 2026。

## 总体结论

- 通过：格式和文献均无必须修改项。
- 修改后通过：存在可以明确修正的问题。
- 不通过：关键章节缺失、文献证据严重不足或字段错配较多。
```

### 11.2 创建 SKILL 主文件

创建文件：

```powershell
notepad skills\citation-review\SKILL.md
```

写入：

```markdown
---
name: citation-review
description: 逐条核验论文参考文献，检查真实性、字段一致性和近五年占比。
---

# 参考文献审核

## 执行流程

1. 读取 `references/review-rules.md`。
2. 从文档中识别完整参考文献列表，保留每条原文。
3. 存在 DOI 时调用 `check_citation`。
4. 不存在 DOI 时调用 `search_by_title`。
5. 记录数据源、登记题名、作者、年份和字段差异。
6. 调用 `run_recent_ratio` 计算近五年数量与占比。
7. 汇总格式问题、文献证据、优先修改项和总体结论。
8. 存在历史记录时，对比已修正、仍存在、新增和无法判断。

## 证据约束

- 不把模型回忆写成外部查询结果。
- 查询无结果时写“未能核实”。
- 网络失败时写“暂缓判断”。
- 历史意见不能替代本次重新检查。

## 输出结构

1. 基本信息
2. 格式检查摘要
3. 格式问题明细
4. 参考文献逐条核验
5. 近五年统计
6. 优先修改项
7. 与上次审核对比
8. 总体结论
9. 限制说明
```

### 11.3 创建近五年统计脚本

创建文件：

```powershell
notepad skills\citation-review\scripts\recent_ratio.py
```

写入：

```python
from __future__ import annotations

import argparse
import json


def calculate(years: list[int | None], review_year: int) -> dict:
    start_year = review_year - 4
    recent = [year for year in years if year and start_year <= year <= review_year]
    total = len(years)
    ratio = len(recent) / total if total else 0.0
    return {
        "review_year": review_year,
        "window": [start_year, review_year],
        "total": total,
        "recent_count": len(recent),
        "recent_ratio": round(ratio * 100, 1),
        "meets_threshold": bool(total and ratio >= 0.5),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--years", nargs="+", required=True)
    parser.add_argument("--review-year", type=int, required=True)
    args = parser.parse_args()
    years = [None if value == "NA" else int(value) for value in args.years]
    print(json.dumps(calculate(years, args.review_year), ensure_ascii=False))


if __name__ == "__main__":
    main()
```

执行验证：

```powershell
python skills/citation-review/scripts/recent_ratio.py --years 2026 2024 2021 NA 2023 --review-year 2026
```

预期结果中 `window` 为 `[2022, 2026]`，`recent_count` 为 `3`。

---

## 12. 编写配置模块

创建文件：

```powershell
notepad app\config.py
```

写入：

```python
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


class Settings:
    llm_api_key = os.getenv("LLM_API_KEY", "")
    llm_base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    llm_model = os.getenv("LLM_MODEL", "deepseek-chat")

    mysql_host = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user = os.getenv("MYSQL_USER", "paper_review_agent")
    mysql_password = os.getenv("MYSQL_PASSWORD", "")
    mysql_database = os.getenv("MYSQL_DATABASE", "paper_review_agent")

    crossref_mailto = os.getenv("CROSSREF_MAILTO", "")
    review_year = int(os.getenv("REVIEW_YEAR", "2026"))

    format_skill = ROOT / "skills" / "format-review"
    citation_skill = ROOT / "skills" / "citation-review"
    format_policy = format_skill / "references" / "format-policy.json"
    mcp_server = ROOT / "mcp_server" / "citation_server.py"
    static_dir = ROOT / "static"


settings = Settings()
```

执行检查：

```powershell
python -c "from app.config import settings; print(settings.llm_model); print(settings.format_policy.exists())"
```

第二行应显示 `True`。

---

## 13. 编写 DOCX 工具

创建文件：

```powershell
notepad app\docx_tools.py
```

写入：

```python
from __future__ import annotations

import json
from collections import Counter
from io import BytesIO
from pathlib import Path
from typing import Any

from docx import Document


def extract_text(data: bytes) -> str:
    document = Document(BytesIO(data))
    blocks = [p.text.strip() for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                blocks.append("\t".join(cells))
    return "\n".join(blocks)


def _cm(value: Any) -> float | None:
    return round(value.cm, 2) if value is not None else None


def _finding(
    findings: list[dict],
    item: str,
    expected: Any,
    actual: Any,
    status: str,
    evidence: str,
) -> None:
    findings.append({
        "item": item,
        "expected": expected,
        "actual": actual,
        "status": status,
        "evidence": evidence,
    })


def _compare_number(actual: float | None, expected: float, tolerance: float) -> str:
    if actual is None:
        return "unknown"
    return "pass" if abs(actual - expected) <= tolerance else "fail"


def _font_name(run) -> str | None:
    if run.font.name:
        return run.font.name
    rpr = run._element.rPr
    if rpr is not None and rpr.rFonts is not None:
        return rpr.rFonts.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia")
    return None


def _paragraph_style(paragraph) -> dict:
    runs = [run for run in paragraph.runs if run.text.strip()]
    names = [_font_name(run) for run in runs if _font_name(run)]
    sizes = [round(run.font.size.pt, 1) for run in runs if run.font.size]
    bolds = [run.bold for run in runs if run.bold is not None]
    return {
        "font": Counter(names).most_common(1)[0][0] if names else None,
        "size_pt": Counter(sizes).most_common(1)[0][0] if sizes else None,
        "bold": Counter(bolds).most_common(1)[0][0] if bolds else None,
        "first_line_indent_cm": _cm(paragraph.paragraph_format.first_line_indent),
        "line_spacing": paragraph.paragraph_format.line_spacing,
    }


def inspect_document(data: bytes, policy_path: Path) -> dict:
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    document = Document(BytesIO(data))
    paragraphs = [p for p in document.paragraphs if p.text.strip()]
    text = "\n".join(p.text.strip() for p in paragraphs)
    findings: list[dict] = []

    section = document.sections[0]
    page = policy["page"]
    page_values = {
        "纸张宽度": _cm(section.page_width),
        "纸张高度": _cm(section.page_height),
        "上页边距": _cm(section.top_margin),
        "下页边距": _cm(section.bottom_margin),
        "左页边距": _cm(section.left_margin),
        "右页边距": _cm(section.right_margin),
    }
    expected_values = {
        "纸张宽度": page["width_cm"],
        "纸张高度": page["height_cm"],
        "上页边距": page["top_margin_cm"],
        "下页边距": page["bottom_margin_cm"],
        "左页边距": page["left_margin_cm"],
        "右页边距": page["right_margin_cm"],
    }
    for item, actual in page_values.items():
        expected = expected_values[item]
        _finding(
            findings, item, expected, actual,
            _compare_number(actual, expected, page["tolerance_cm"]),
            "文档第一个节的页面设置",
        )

    positions = []
    for name in policy["required_sections"]:
        position = text.lower().find(name.lower())
        positions.append(position)
        _finding(
            findings,
            f"章节：{name}",
            "存在",
            "存在" if position >= 0 else "缺失",
            "pass" if position >= 0 else "fail",
            f"全文检索位置 {position}",
        )
    existing = [value for value in positions if value >= 0]
    order_ok = len(existing) == len(positions) and existing == sorted(existing)
    _finding(
        findings, "章节顺序", policy["required_sections"],
        "按要求排列" if order_ok else "存在缺失或顺序错误",
        "pass" if order_ok else "fail", "按全文位置比较",
    )

    if paragraphs:
        actual = _paragraph_style(paragraphs[0])
        expected = policy["typography"]["title"]
        title_ok = (
            actual["font"] == expected["font"]
            and actual["size_pt"] == expected["size_pt"]
            and actual["bold"] is expected["bold"]
        )
        known = all(actual[key] is not None for key in ("font", "size_pt", "bold"))
        _finding(
            findings, "论文题目样式", expected, actual,
            "pass" if title_ok else "fail" if known else "unknown",
            f"首个非空段落：{paragraphs[0].text[:40]}",
        )

    body_candidates = [
        p for p in paragraphs
        if len(p.text.strip()) >= 30 and not p.style.name.lower().startswith("heading")
    ]
    if body_candidates:
        actual = _paragraph_style(body_candidates[0])
        expected = policy["typography"]["body"]
        known = actual["font"] is not None and actual["size_pt"] is not None
        font_ok = actual["font"] == expected["font"]
        size_ok = actual["size_pt"] == expected["size_pt"]
        _finding(
            findings, "正文样式", expected, actual,
            "pass" if known and font_ok and size_ok else "fail" if known else "unknown",
            f"正文样本：{body_candidates[0].text[:40]}",
        )
    else:
        _finding(findings, "正文样式", policy["typography"]["body"], None,
                 "unknown", "没有长度达到 30 字符的正文段落")

    counts = Counter(item["status"] for item in findings)
    return {
        "policy_id": policy["policy_id"],
        "summary": {
            "total": len(findings),
            "pass": counts["pass"],
            "fail": counts["fail"],
            "unknown": counts["unknown"],
        },
        "findings": findings,
    }
```

该工具只输出证据，不生成自然语言结论。

---

## 14. 编写 SKILL 运行时

创建文件：

```powershell
notepad app\skill_runtime.py
```

写入：

```python
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
```

执行清单检查：

```powershell
python -c "from app.config import settings; from app.skill_runtime import SkillRuntime; s=SkillRuntime(settings.format_skill,'read_format_skill_file'); print(s.name); print(s.files())"
```

---

## 15. 编写 citation-check MCP Server

创建文件：

```powershell
notepad mcp_server\citation_server.py
```

写入：

```python
from __future__ import annotations

import os
import re
import unicodedata
from datetime import date
from difflib import SequenceMatcher
from urllib.parse import quote

import requests
from mcp.server.fastmcp import FastMCP

SERVER_NAME = "citation-check"
CROSSREF = "https://api.crossref.org/works"
DOI_PATTERN = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)

mcp = FastMCP(SERVER_NAME)
session = requests.Session()
mailto = os.getenv("CROSSREF_MAILTO", "")
session.headers["User-Agent"] = f"PaperReviewAgent/1.0 mailto:{mailto}"


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(re.findall(r"[\w\u4e00-\u9fff]+", value))


def similarity(left: str, right: str) -> float:
    return round(SequenceMatcher(None, normalize(left), normalize(right)).ratio(), 3)


def metadata(message: dict) -> dict:
    authors = []
    for author in message.get("author") or []:
        name = " ".join(filter(None, [author.get("given"), author.get("family")]))
        if name:
            authors.append(name)
    date_parts = (message.get("issued") or {}).get("date-parts") or []
    year = date_parts[0][0] if date_parts and date_parts[0] else None
    return {
        "exists": True,
        "doi": message.get("DOI", "").lower(),
        "title": (message.get("title") or [""])[0],
        "authors": authors,
        "year": year,
        "source": "Crossref",
        "checked_at": date.today().isoformat(),
    }


@mcp.tool()
def ping() -> dict:
    """返回 MCP Server 状态。"""
    return {"ok": True, "server": SERVER_NAME}


@mcp.tool()
def verify_doi(doi: str) -> dict:
    """查询 DOI 的 Crossref 登记信息。"""
    value = doi.strip().removeprefix("https://doi.org/").rstrip(".,;").lower()
    if not DOI_PATTERN.fullmatch(value):
        return {"error": "invalid_doi", "doi": value}
    try:
        response = session.get(f"{CROSSREF}/{quote(value, safe='')}", timeout=10)
        if response.status_code == 404:
            return {"exists": False, "doi": value, "source": "Crossref"}
        response.raise_for_status()
        return metadata(response.json()["message"])
    except requests.RequestException as exc:
        return {"error": "network_failure", "detail": str(exc), "doi": value}


@mcp.tool()
def search_by_title(title: str, limit: int = 3) -> dict:
    """按题名查询候选记录，不直接给出真实性结论。"""
    query = title.strip()
    if len(query) < 4:
        return {"error": "title_too_short"}
    try:
        response = session.get(
            CROSSREF,
            params={"query.title": query, "rows": max(1, min(limit, 5))},
            timeout=10,
        )
        response.raise_for_status()
        candidates = []
        for item in response.json()["message"]["items"]:
            record = metadata(item)
            record["title_similarity"] = similarity(query, record["title"])
            candidates.append(record)
        candidates.sort(key=lambda item: item["title_similarity"], reverse=True)
        return {"query": query, "candidates": candidates}
    except requests.RequestException as exc:
        return {"error": "network_failure", "detail": str(exc)}


@mcp.tool()
def check_citation(citation: str, doi: str = "", title: str = "") -> dict:
    """核验一条参考文献并比对题名。"""
    found = doi.strip()
    if not found:
        match = DOI_PATTERN.search(citation)
        found = match.group(0) if match else ""
    if found:
        record = verify_doi(found)
        if record.get("error") or not record.get("exists"):
            return {"verdict": "unverified", "record": record}
        score = similarity(title, record["title"]) if title else None
        verdict = "verified" if score is None or score >= 0.8 else "mismatch"
        return {"verdict": verdict, "title_similarity": score, "record": record}
    if title:
        result = search_by_title(title)
        candidates = result.get("candidates") or []
        best = candidates[0] if candidates else None
        verdict = "verified" if best and best["title_similarity"] >= 0.9 else "unverified"
        return {"verdict": verdict, "best_candidate": best, "search": result}
    return {"verdict": "unverified", "detail": "缺少 DOI 和题名"}


if __name__ == "__main__":
    mcp.run(transport="stdio")
```

`ping` 只检查服务状态。`verify_doi`、`search_by_title` 和 `check_citation` 提供可复核证据。

---

## 16. 编写 MCP 客户端

创建文件：

```powershell
notepad app\mcp_client.py
```

写入：

```python
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
```

执行 MCP 检查：

```powershell
@'
import asyncio
from app.config import settings
from app.mcp_client import McpClient

async def main():
    async with McpClient(settings.mcp_server) as client:
        print([tool["name"] for tool in client.tools])
        print(await client.call("ping", {}))

asyncio.run(main())
'@ | python -
```

预期输出包含 `ping`、`verify_doi`、`search_by_title` 和 `check_citation`。

---

## 17. 编写 MySQL 记忆层

创建文件：

```powershell
notepad app\memory.py
```

写入：

```python
from __future__ import annotations

import asyncio
import hashlib
import re
import unicodedata
from dataclasses import dataclass

import pymysql
from pymysql.cursors import DictCursor


def normalize(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).strip().lower()
    return re.sub(r"[\s\W_]+", "", value)


def field(text: str, *labels: str) -> str:
    choices = "|".join(re.escape(label) for label in labels)
    pattern = re.compile(rf"^({choices})\s*[：:\t ]+\s*(.+)\s*$", re.M)
    match = pattern.search(text)
    return match.group(2).strip() if match else ""


@dataclass(frozen=True)
class DocumentIdentity:
    author_key: str
    author_name: str
    author_id: str
    paper_key: str
    paper_title: str
    document_hash: str

    @property
    def rememberable(self) -> bool:
        return bool(self.author_key and self.paper_key)


def identify_document(text: str) -> DocumentIdentity:
    author_name = field(text, "作者姓名", "提交人", "作者")
    author_id = field(text, "作者编号", "编号")
    paper_title = field(text, "论文题目", "题目", "材料题名")
    author_value = normalize(author_id or author_name)
    title_value = normalize(paper_title)
    return DocumentIdentity(
        author_key=hashlib.sha256(author_value.encode()).hexdigest() if author_value else "",
        author_name=author_name,
        author_id=author_id,
        paper_key=hashlib.sha256(title_value.encode()).hexdigest() if title_value else "",
        paper_title=paper_title,
        document_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
    )


class MemoryStore:
    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        self.arguments = {
            "host": host,
            "port": port,
            "user": user,
            "password": password,
            "database": database,
            "charset": "utf8mb4",
            "autocommit": True,
            "cursorclass": DictCursor,
        }

    def connect(self):
        return pymysql.connect(**self.arguments)

    async def initialize(self) -> dict:
        return await asyncio.to_thread(self._initialize)

    def _initialize(self) -> dict:
        sql = """
        CREATE TABLE IF NOT EXISTS review_history (
            id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
            author_key CHAR(64) NOT NULL,
            author_id VARCHAR(64),
            author_name VARCHAR(128),
            paper_key CHAR(64) NOT NULL,
            paper_title VARCHAR(512) NOT NULL,
            revision_no INT NOT NULL,
            document_hash CHAR(64) NOT NULL,
            document_text LONGTEXT NOT NULL,
            report_text LONGTEXT NOT NULL,
            review_year SMALLINT NOT NULL,
            model_name VARCHAR(128) NOT NULL,
            created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
            KEY idx_author_paper (author_key, paper_key, created_at)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(sql)
            cursor.execute("SELECT COUNT(*) AS count FROM review_history")
            return {"ok": True, "records": cursor.fetchone()["count"]}

    async def latest(self, identity: DocumentIdentity) -> dict | None:
        if not identity.rememberable:
            return None
        return await asyncio.to_thread(self._latest, identity)

    def _latest(self, identity: DocumentIdentity) -> dict | None:
        sql = """
        SELECT * FROM review_history
        WHERE author_key=%s AND paper_key=%s
        ORDER BY revision_no DESC LIMIT 1
        """
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(sql, (identity.author_key, identity.paper_key))
            return cursor.fetchone()

    async def save(
        self,
        identity: DocumentIdentity,
        document_text: str,
        report_text: str,
        review_year: int,
        model_name: str,
    ) -> int | None:
        if not identity.rememberable:
            return None
        return await asyncio.to_thread(
            self._save, identity, document_text, report_text, review_year, model_name
        )

    def _save(self, identity, document_text, report_text, review_year, model_name) -> int:
        with self.connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                "SELECT COALESCE(MAX(revision_no), 0) AS value FROM review_history "
                "WHERE author_key=%s AND paper_key=%s",
                (identity.author_key, identity.paper_key),
            )
            revision = int(cursor.fetchone()["value"]) + 1
            cursor.execute(
                """
                INSERT INTO review_history (
                    author_key, author_id, author_name, paper_key, paper_title,
                    revision_no, document_hash, document_text, report_text,
                    review_year, model_name
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    identity.author_key, identity.author_id, identity.author_name,
                    identity.paper_key, identity.paper_title, revision,
                    identity.document_hash, document_text, report_text,
                    review_year, model_name,
                ),
            )
            return revision
```

记忆键由提交人编号或姓名和论文题名共同组成。正文修改后 `document_hash` 变化，材料身份保持不变。

---

## 18. 编写 Agent 工具循环

创建文件：

```powershell
notepad app\agent.py
```

写入：

```python
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
5. 外部查询失败时写“暂缓判断”，没有证据时写“未能核实”。
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
```

工具循环的停止条件是模型不再返回工具调用。达到 20 轮后强制停止，避免无限循环。

---

## 19. 编写 FastAPI 服务

创建文件：

```powershell
notepad app\webapp.py
```

写入：

```python
from __future__ import annotations

import asyncio
import json

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .agent import ReviewAgent
from .config import settings
from .docx_tools import extract_text, inspect_document
from .mcp_client import McpClient
from .memory import MemoryStore
from .skill_runtime import SkillRuntime

memory = MemoryStore(
    settings.mysql_host,
    settings.mysql_port,
    settings.mysql_user,
    settings.mysql_password,
    settings.mysql_database,
)
memory_health = {"ok": False}
mcp_tools: list[dict] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global memory_health, mcp_tools
    try:
        memory_health = await memory.initialize()
    except Exception as exc:
        memory_health = {"ok": False, "detail": str(exc)}
    try:
        async with McpClient(settings.mcp_server) as client:
            mcp_tools = client.tools
    except Exception as exc:
        mcp_tools = [{"name": "连接失败", "description": str(exc)}]
    yield


app = FastAPI(title="论文规范审核 Agent", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(settings.static_dir / "index.html")


@app.get("/api/health")
async def health() -> JSONResponse:
    ok = bool(memory_health.get("ok")) and bool(mcp_tools)
    return JSONResponse({
        "status": "ok" if ok else "degraded",
        "model": settings.llm_model,
        "memory": memory_health,
        "mcp_tools": [item["name"] for item in mcp_tools],
    })


@app.get("/api/config")
async def config() -> JSONResponse:
    format_skill = SkillRuntime(settings.format_skill, "read_format_skill_file")
    citation_skill = SkillRuntime(
        settings.citation_skill, "read_citation_skill_file", with_ratio=True
    )
    return JSONResponse({
        "model": settings.llm_model,
        "mcp_tools": mcp_tools,
        "skills": [
            {"name": format_skill.name, "files": format_skill.files()},
            {"name": citation_skill.name, "files": citation_skill.files()},
        ],
        "memory": memory_health,
    })


@app.post("/api/upload-docx")
async def upload_docx(file: UploadFile) -> JSONResponse:
    if not file.filename or not file.filename.lower().endswith(".docx"):
        return JSONResponse({"error": "只接收 DOCX 文件"}, status_code=400)
    data = await file.read()
    if len(data) > 10 * 1024 * 1024:
        return JSONResponse({"error": "文件不得超过 10 MB"}, status_code=400)
    try:
        text = extract_text(data)
        analysis = inspect_document(data, settings.format_policy)
        return JSONResponse({
            "filename": file.filename,
            "text": text,
            "format_analysis": analysis,
        })
    except Exception as exc:
        return JSONResponse({"error": f"DOCX 解析失败：{exc}"}, status_code=400)


@app.post("/api/review")
async def review(request: Request) -> StreamingResponse:
    payload = await request.json()
    document_text = str(payload.get("text", ""))
    format_analysis = payload.get("format_analysis") or {}
    review_year = int(payload.get("review_year") or settings.review_year)

    async def stream():
        queue: asyncio.Queue = asyncio.Queue()

        async def emit(event: dict) -> None:
            await queue.put(event)

        async def work() -> None:
            try:
                agent = ReviewAgent(
                    document_text, format_analysis, review_year, memory, emit
                )
                await agent.run()
            except Exception as exc:
                await emit({"type": "error", "detail": str(exc)})
            finally:
                await queue.put(None)

        task = asyncio.create_task(work())
        while True:
            event = await queue.get()
            if event is None:
                break
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        await task

    return StreamingResponse(stream(), media_type="text/event-stream")
```

---

## 20. 编写网页界面

创建文件：

```powershell
notepad static\index.html
```

写入：

```html
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>论文规范审核 Agent</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; font-family: Arial, "Microsoft YaHei", sans-serif; color: #1f2937; background: #f5f7fa; }
    header { padding: 22px 30px; background: #fff; border-bottom: 1px solid #dfe3e8; }
    header h1 { margin: 0 0 8px; font-size: 24px; }
    #status { color: #64748b; font-size: 14px; }
    main { display: grid; grid-template-columns: 340px 1fr; gap: 20px; padding: 20px; max-width: 1400px; margin: auto; }
    .panel { background: #fff; border: 1px solid #dfe3e8; border-radius: 10px; padding: 18px; }
    h2 { margin: 0 0 14px; font-size: 18px; }
    h3 { margin: 20px 0 10px; font-size: 15px; }
    input, button { width: 100%; padding: 10px; margin: 6px 0; font: inherit; }
    input { border: 1px solid #cbd5e1; border-radius: 6px; }
    button { border: 0; border-radius: 6px; background: #1f4e79; color: #fff; cursor: pointer; }
    button:disabled { opacity: .5; cursor: not-allowed; }
    .hint { color: #64748b; font-size: 13px; line-height: 1.6; }
    .trace { border: 1px solid #e2e8f0; border-radius: 7px; padding: 10px; margin: 8px 0; background: #fafafa; }
    .trace small { color: #64748b; }
    .capability { padding: 8px 0; border-bottom: 1px solid #eef1f4; font-size: 13px; }
    pre { white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.65; font-family: inherit; }
    #report { min-height: 260px; }
    @media (max-width: 900px) { main { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <header>
    <h1>论文规范审核 Agent</h1>
    <div id="status">正在读取服务状态</div>
  </header>
  <main>
    <section class="panel">
      <h2>提交材料</h2>
      <input id="file" type="file" accept=".docx">
      <label for="year">审核年度</label>
      <input id="year" type="number" value="2026">
      <div class="hint">近五年：审核年度及前 4 年</div>
      <button id="upload">上传并解析</button>
      <button id="review" disabled>开始审核</button>
      <div id="fileInfo" class="hint">请选择 DOCX 文件</div>

      <h3>MCP 工具</h3>
      <div id="mcp"></div>
      <h3>SKILL</h3>
      <div id="skills"></div>
    </section>

    <section>
      <div class="panel">
        <h2>执行轨迹</h2>
        <div id="trace" class="hint">尚未开始</div>
      </div>
      <div class="panel" style="margin-top:20px">
        <h2>审核意见</h2>
        <pre id="report">等待审核结果</pre>
      </div>
    </section>
  </main>

  <script>
    const state = { text: "", formatAnalysis: null };
    const $ = id => document.getElementById(id);

    async function loadConfig() {
      const config = await fetch("/api/config").then(response => response.json());
      let mysqlState = "异常";
      if (config.memory.ok) mysqlState = "正常";
      $("status").textContent = `决策 LLM（${config.model}） · MySQL ${mysqlState}`;
      $("mcp").innerHTML = config.mcp_tools.map(tool =>
        `<div class="capability"><b>${tool.name}</b><br>${tool.description || ""}</div>`
      ).join("");
      $("skills").innerHTML = config.skills.map(skill =>
        `<div class="capability"><b>${skill.name}</b><br>${skill.files.join("、")}</div>`
      ).join("");
    }

    $("upload").onclick = async () => {
      const file = $("file").files[0];
      if (!file) {
        $("fileInfo").textContent = "请选择 DOCX 文件";
        return;
      }
      const form = new FormData();
      form.append("file", file);
      $("fileInfo").textContent = "正在解析";
      const response = await fetch("/api/upload-docx", { method: "POST", body: form });
      const data = await response.json();
      if (!response.ok) {
        $("fileInfo").textContent = data.error;
        return;
      }
      state.text = data.text;
      state.formatAnalysis = data.format_analysis;
      const summary = data.format_analysis.summary;
      $("fileInfo").textContent = `${data.filename} · ${summary.total} 项检查 · ${summary.fail} 项不符合`;
      $("review").disabled = false;
    };

    function addTrace(event) {
      if ($("trace").classList.contains("hint")) {
        $("trace").classList.remove("hint");
        $("trace").innerHTML = "";
      }
      let elapsed = "";
      if (event.elapsed_ms !== undefined) elapsed = `<small>${event.elapsed_ms} ms</small>`;
      const title = event.name || event.type;
      $("trace").insertAdjacentHTML("beforeend", `<div class="trace">${title} ${elapsed}</div>`);
    }

    $("review").onclick = async () => {
      $("review").disabled = true;
      $("trace").className = "";
      $("trace").innerHTML = "";
      $("report").textContent = "正在审核";
      const response = await fetch("/api/review", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: state.text,
          format_analysis: state.formatAnalysis,
          review_year: Number($("year").value),
        }),
      });
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const result = await reader.read();
        if (result.done) break;
        buffer += decoder.decode(result.value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop();
        for (const block of blocks) {
          const line = block.split("\n").find(value => value.startsWith("data: "));
          if (!line) continue;
          const event = JSON.parse(line.slice(6));
          addTrace(event);
          if (event.type === "completed") $("report").textContent = event.report;
          if (event.type === "error") $("report").textContent = event.detail;
        }
      }
      $("review").disabled = false;
    };

    loadConfig();
  </script>
</body>
</html>
```

执行轨迹卡片使用完整边框，不设置侧边高亮。只有存在实际耗时时才显示毫秒数。

---

## 21. 创建练习材料生成脚本

创建文件：

```powershell
notepad scripts\create_materials.py
```

写入：

```python
from pathlib import Path

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

ROOT = Path(__file__).resolve().parent.parent
RESOURCE_DIR = ROOT / "resources"
RESOURCE_DIR.mkdir(exist_ok=True)


def set_run(run, font: str, size: float, bold: bool = False) -> None:
    run.font.name = font
    run._element.get_or_add_rPr().rFonts.set(qn("w:eastAsia"), font)
    run.font.size = Pt(size)
    run.bold = bold


def create_specification() -> None:
    document = Document()
    title = document.add_paragraph()
    set_run(title.add_run("计算机学院本科毕业论文格式规范"), "黑体", 18, True)
    sections = {
        "一、页面设置": [
            "使用 A4 纸张，宽 21.0 cm，高 29.7 cm。",
            "页边距为上 2.5 cm、下 2.5 cm、左 3.0 cm、右 2.5 cm。",
        ],
        "二、字体与段落": [
            "论文题目使用黑体 18 pt 并加粗。",
            "一级标题使用黑体 16 pt 并加粗。",
            "正文使用宋体 12 pt，首行缩进约 0.74 cm，1.5 倍行距。",
        ],
        "三、章节顺序": [
            "依次设置摘要、关键词、ABSTRACT、目录、绪论、系统设计、结论、参考文献、致谢。"
        ],
        "四、参考文献": [
            "保留作者、题名、来源、年份和 DOI 等可复核字段。",
            "近五年文献比例不得低于 50%。",
        ],
    }
    for heading, rows in sections.items():
        paragraph = document.add_paragraph()
        set_run(paragraph.add_run(heading), "黑体", 16, True)
        for row in rows:
            paragraph = document.add_paragraph(row)
            for run in paragraph.runs:
                set_run(run, "宋体", 12)
    document.save(RESOURCE_DIR / "计算机学院本科毕业论文格式规范.docx")


def create_paper() -> None:
    document = Document()
    section = document.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.5)
    section.bottom_margin = Cm(2.5)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.5)

    title_text = "面向高校课程的多智能体辅助系统设计与实现"
    title = document.add_paragraph()
    set_run(title.add_run(title_text), "宋体", 16, True)
    document.add_paragraph("作者姓名：张晨")
    document.add_paragraph("作者编号：2026230417")
    document.add_paragraph(f"论文题目：{title_text}")

    content = [
        ("摘要", "本文围绕多智能体协作、课程资源检索和过程评价开展系统设计，并完成主要功能验证。"),
        ("关键词", "多智能体；工具调用；知识检索；过程评价"),
        ("ABSTRACT", "This paper designs a multi-agent support system for course activities."),
        ("目录", "1 绪论\n2 系统设计\n3 结论"),
        ("绪论", "相关应用需要把模型决策、外部工具和业务规则组合为可追踪的处理流程。"),
        ("系统设计", "系统由任务编排、工具调用、知识检索和结果展示四个模块组成，各模块通过明确接口协作。"),
        ("结论", "系统完成了核心流程验证，后续可继续补充评价指标和权限控制。"),
    ]
    for heading, body in content:
        paragraph = document.add_paragraph()
        set_run(paragraph.add_run(heading), "黑体", 16, True)
        paragraph = document.add_paragraph(body)
        paragraph.paragraph_format.first_line_indent = Cm(0.74)
        paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
        for run in paragraph.runs:
            set_run(run, "宋体", 12)

    heading = document.add_paragraph()
    set_run(heading.add_run("参考文献"), "黑体", 16, True)
    references = [
        "[1] Vaswani A, et al. Attention Is All You Need. 2017.",
        "[2] Brown T B, et al. Language Models are Few-Shot Learners. 2020.",
        "[3] Lewis P, et al. Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks. 2020.",
        "[4] Yao S, et al. ReAct: Synergizing Reasoning and Acting in Language Models. 2023.",
        "[5] Park J S, et al. Generative Agents: Interactive Simulacra of Human Behavior. 2023. DOI:10.1145/3586183.3606763.",
        "[6] Wu Q, et al. AutoGen: Enabling Next-Gen LLM Applications. 2024.",
    ]
    for value in references:
        paragraph = document.add_paragraph(value)
        for run in paragraph.runs:
            set_run(run, "宋体", 12)

    heading = document.add_paragraph()
    set_run(heading.add_run("致谢"), "黑体", 16, True)
    document.add_paragraph("感谢在资料整理和系统测试过程中提供的支持。")
    document.save(RESOURCE_DIR / "论文初稿.docx")


create_specification()
create_paper()
print("已生成格式规范和论文初稿")
```

执行：

```powershell
python scripts/create_materials.py
```

`resources` 目录中应出现：

```text
计算机学院本科毕业论文格式规范.docx
论文初稿.docx
计算机学院本科毕业论文格式规范.md
```

先打开格式规范，再打开论文初稿。初稿题目故意使用宋体 16 pt，用于产生可明确复核的格式问题。

---

## 22. 创建自动化测试

创建文件：

```powershell
notepad tests\test_core.py
```

写入：

```python
import unittest

from app.config import settings
from app.docx_tools import extract_text, inspect_document
from app.memory import identify_document


class CoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.path = settings.static_dir.parent / "resources" / "论文初稿.docx"
        cls.data = cls.path.read_bytes()

    def test_extract_text(self):
        text = extract_text(self.data)
        self.assertIn("作者编号：2026230417", text)
        self.assertIn("参考文献", text)

    def test_format_check(self):
        result = inspect_document(self.data, settings.format_policy)
        self.assertGreater(result["summary"]["total"], 10)
        self.assertGreater(result["summary"]["fail"], 0)

    def test_identity_stays_stable_after_body_change(self):
        text = extract_text(self.data)
        first = identify_document(text)
        second = identify_document(text.replace("核心流程验证", "完整流程验证"))
        self.assertTrue(first.rememberable)
        self.assertEqual(first.author_key, second.author_key)
        self.assertEqual(first.paper_key, second.paper_key)
        self.assertNotEqual(first.document_hash, second.document_hash)


if __name__ == "__main__":
    unittest.main()
```

执行：

```powershell
python -m unittest discover -s tests -v
```

三项测试均应显示 `ok`。

---

## 23. 验证模型连接

执行：

```powershell
@'
import asyncio
from openai import AsyncOpenAI
from app.config import settings

async def main():
    client = AsyncOpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)
    response = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[{"role": "user", "content": "只输出 OK"}],
    )
    print(response.choices[0].message.content)

asyncio.run(main())
'@ | python -
```

预期输出包含 `OK`。

---

## 24. 启动应用

确认 MySQL 已启动，执行：

```powershell
python -m uvicorn app.webapp:app --host 127.0.0.1 --port 8765
```

浏览器访问：

```text
http://127.0.0.1:8765
```

页面右上状态应显示决策模型名称和 MySQL 状态。

另开 PowerShell 执行：

```powershell
Invoke-RestMethod http://127.0.0.1:8765/api/health | ConvertTo-Json -Depth 5
```

`status` 应为 `ok`，MCP 工具列表应包含四个工具。

---

## 25. 完成第一次审核

1. 打开 `http://127.0.0.1:8765`。
2. 选择 `resources/论文初稿.docx`。
3. 点击“上传并解析”。
4. 确认页面显示格式检查项数量和不符合数量。
5. 将审核年度填写为 2026。
6. 点击“开始审核”。
7. 等待执行轨迹完成。

执行轨迹应包含：

```text
memory_loaded
llm_started
read_format_skill_file
inspect_document_format
read_citation_skill_file
check_citation 或 search_by_title
run_recent_ratio
memory_saved
completed
```

最终报告至少包含格式检查、参考文献核验、近五年统计、优先修改项和总体结论。

---

## 26. 验证 MySQL 记录

连接数据库：

```powershell
mysql -u paper_review_agent -p paper_review_agent
```

执行：

```sql
SELECT id, author_name, paper_title, revision_no, review_year, model_name, created_at
FROM review_history
ORDER BY id DESC
LIMIT 10;
```

第一次审核的 `revision_no` 应为 `1`。

---

## 27. 完成修改版复审

复制文件：

```powershell
Copy-Item resources\论文初稿.docx resources\论文修改版.docx
```

使用 Word 打开 `resources/论文修改版.docx`，完成以下修改：

1. 将题目字体改为黑体；
2. 将题目字号改为 18 pt；
3. 保持作者姓名、作者编号和论文题目字段不变；
4. 修改一段正文；
5. 保存并关闭。

返回网页，上传修改版并再次审核。

执行轨迹中的 `memory_loaded` 应显示已找到历史记录。报告应包含已修正、仍存在、新增和无法判断四类对比结果。

执行数据库查询：

```sql
SELECT revision_no, document_hash, created_at
FROM review_history
ORDER BY id DESC
LIMIT 2;
```

最新版本号应为 `2`，两次记录的 `document_hash` 应不同。

---

## 28. 初始化本地 Git 版本管理

执行：

```powershell
git init
git branch -M main
git add .
git status --short
```

确认输出中不包含 `.env` 和 `.venv`，再执行：

```powershell
git commit -m "完成论文规范审核 Agent"
```

---

## 29. 部署到 Linux 服务器

### 29.1 检查本地项目

```powershell
python -m unittest discover -s tests -v
```

### 29.2 上传项目

在本地 PowerShell 创建部署压缩包。排除虚拟环境、密钥和缓存：

```powershell
tar -czf paper-review-agent.tar.gz `
  --exclude=paper-review-agent/.venv `
  --exclude=paper-review-agent/.env `
  --exclude=*/__pycache__ `
  -C $HOME paper-review-agent

scp paper-review-agent.tar.gz root@服务器地址:/root/
```

部署压缩包不得包含 `.env`。

### 29.3 安装服务器环境

登录服务器：

```powershell
ssh root@服务器地址
```

Ubuntu 或 Debian 执行：

```bash
apt update
apt install -y python3 python3-venv python3-pip mysql-client
mkdir -p /opt
tar -xzf /root/paper-review-agent.tar.gz -C /opt
cd /opt/paper-review-agent
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

### 29.4 配置服务器环境变量

```bash
nano /opt/paper-review-agent/.env
chmod 600 /opt/paper-review-agent/.env
```

填写服务器使用的 LLM 和 MySQL 配置。

### 29.5 创建 systemd 服务

```bash
nano /etc/systemd/system/paper-review-agent.service
```

写入：

```ini
[Unit]
Description=Paper Review Agent
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/paper-review-agent
EnvironmentFile=/opt/paper-review-agent/.env
ExecStart=/opt/paper-review-agent/.venv/bin/python -m uvicorn app.webapp:app --host 0.0.0.0 --port 8080
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
systemctl daemon-reload
systemctl enable --now paper-review-agent
systemctl status paper-review-agent --no-pager
```

检查接口：

```bash
curl http://127.0.0.1:8080/api/health
```

查看日志：

```bash
journalctl -u paper-review-agent -n 100 --no-pager
```

---

## 30. 常见问题

### 30.1 `python` 命令不存在

重新运行 Python 安装程序，勾选 **Add python.exe to PATH**，再重新打开 PowerShell。

### 30.2 PowerShell 无法激活虚拟环境

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
.\.venv\Scripts\Activate.ps1
```

### 30.3 出现 `ModuleNotFoundError`

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 30.4 模型接口返回 401

检查 `.env` 中的 `LLM_API_KEY`，去掉密钥两端的引号和空格，重新启动服务。

### 30.5 模型接口返回 404

检查 `LLM_BASE_URL` 和 `LLM_MODEL`，保持模型名称与服务商提供的名称一致。

### 30.6 MCP 启动后没有输出

stdio MCP Server 启动后会等待客户端连接，不提供网页。按 `Ctrl+C` 停止后，通过第 16 节的客户端脚本验证。

### 30.7 Crossref 请求超时

检查网络和代理。报告中保留“暂缓判断”，不得把超时解释为文献不存在。

### 30.8 DOCX 解析失败

确认文件扩展名为 `.docx`，使用 Word 重新另存为 DOCX。旧版 `.doc` 文件不能直接解析。

### 30.9 格式项目显示 `unknown`

确认格式是否写在段落样式或主题字体中。无法取得稳定属性时保留 `unknown`，交由人工复核。

### 30.10 MySQL 连接被拒绝

Windows 执行：

```powershell
Get-Service MySQL*
```

macOS 执行：

```bash
brew services list
```

Linux 执行：

```bash
systemctl status mysql --no-pager
```

继续检查 `.env` 中的主机、端口、账号、密码和数据库名。

### 30.11 复审没有读取历史记录

保持作者编号或作者姓名和论文题目字段不变，只修改正文、格式或参考文献。

### 30.12 页面没有实时轨迹

检查 `/api/review` 的响应类型，确认值为 `text/event-stream`。使用反向代理时关闭 SSE 缓冲。

---

## 31. 完成标准

- [ ] Python、VS Code、Git 和 MySQL 安装完成；
- [ ] 从空目录创建全部项目文件；
- [ ] 虚拟环境和 Python 依赖安装完成；
- [ ] `.env` 配置完成且未被 Git 跟踪；
- [ ] 院系格式规范 Markdown 和 DOCX 已生成；
- [ ] 格式规则 JSON 语法正确；
- [ ] 两个 SKILL 可以读取；
- [ ] 近五年统计脚本运行正常；
- [ ] MCP 客户端列出四个工具；
- [ ] DOCX 文本提取和格式检查测试通过；
- [ ] 决策 LLM 最小请求成功；
- [ ] MySQL 自动创建审核记录表；
- [ ] 网页显示 MCP 和 SKILL 列表；
- [ ] 第一次审核生成完整报告；
- [ ] 修改版复审读取历史记录；
- [ ] 第二次审核保存为新版本；
- [ ] 全部自动化测试通过；
- [ ] Linux 服务健康检查正常。

---

## 附录 A：最终目录结构

```text
paper-review-agent/
├── app/
│   ├── __init__.py
│   ├── agent.py
│   ├── config.py
│   ├── docx_tools.py
│   ├── mcp_client.py
│   ├── memory.py
│   ├── skill_runtime.py
│   └── webapp.py
├── mcp_server/
│   └── citation_server.py
├── resources/
│   ├── 计算机学院本科毕业论文格式规范.md
│   ├── 计算机学院本科毕业论文格式规范.docx
│   └── 论文初稿.docx
├── scripts/
│   └── create_materials.py
├── skills/
│   ├── format-review/
│   │   ├── SKILL.md
│   │   └── references/format-policy.json
│   └── citation-review/
│       ├── SKILL.md
│       ├── references/review-rules.md
│       └── scripts/recent_ratio.py
├── static/
│   └── index.html
├── tests/
│   └── test_core.py
├── .env
├── .gitignore
└── requirements.txt
```

---

## 附录 B：一次完整审核的数据流

```text
1. 浏览器上传 DOCX
2. FastAPI 读取文件字节
3. docx_tools 提取文本和格式证据
4. memory 识别提交人和论文题名
5. MySQL 查询最近一版审核记录
6. Agent 合并 SKILL 工具与 MCP 工具
7. 决策 LLM 选择下一项工具
8. 本地工具或 MCP 返回结构化证据
9. Agent 把工具结果写回模型上下文
10. 决策 LLM 继续调用工具或生成报告
11. MySQL 保存报告和新版本号
12. FastAPI 通过 SSE 返回执行事件
13. 浏览器显示执行轨迹和审核意见
```

---

## 附录 C：核心设计原则

1. 格式规则来自规范文件，不来自模型记忆。
2. DOCX 工具和 MCP 提供证据，决策 LLM 组织结论。
3. SKILL 规定执行方法，Python 完成实际操作。
4. 历史记录用于整改对比，本次材料仍需重新检查。
5. 证据不足时保留“无法判断”“未能核实”或“暂缓判断”。
6. API Key 和数据库密码只保存在 `.env`。
7. 执行轨迹只为实际耗时步骤显示毫秒数。
