# 论文规范审核 Agent

基于 FastAPI + LLM + MCP 的论文规范审核系统，支持 DOCX 上传、格式检查、参考文献核验（Crossref）、历史审核记录对比等功能。

## 项目结构

```
paper-review-agent/
├── app/                          # 应用核心代码
│   ├── __init__.py
│   ├── agent.py                  # 决策 LLM 工具循环（OpenAI SDK）
│   ├── config.py                 # 配置模块，读取 .env
│   ├── docx_tools.py             # DOCX 文本提取 + 格式检查
│   ├── mcp_client.py             # MCP 协议客户端
│   ├── memory.py                 # MySQL 记忆层（提交人/论文识别、版本管理）
│   ├── skill_runtime.py          # SKILL 运行时（读取规则文件、执行脚本）
│   └── webapp.py                 # FastAPI 服务 + SSE 流式接口
├── mcp_server/
│   └── citation_server.py        # MCP Server：Crossref 查询（DOI/题名/字段比对）
├── skills/
│   ├── format-review/            # 格式检查 SKILL
│   │   ├── SKILL.md
│   │   └── references/format-policy.json   # 页面/字体/章节规则
│   └── citation-review/          # 参考文献审核 SKILL
│       ├── SKILL.md
│       ├── references/review-rules.md       # 审核结论分级
│       └── scripts/recent_ratio.py          # 近五年文献占比计算
├── static/
│   ├── index.html                # 前端页面
│   └── lib/marked.min.js         # Markdown 渲染库
├── resources/
│   ├── 计算机学院本科毕业论文格式规范.md     # 格式规范文档
│   ├── 论文初稿.docx                        # 测试用论文
│   └── 计算机学院本科毕业论文格式规范.docx    # 测试用规范
├── scripts/
│   ├── create_materials.py       # 测试材料生成脚本
│   └── init.sql                  # MySQL 初始化（创建用户、权限）
├── tests/
│   └── test_core.py              # 核心功能测试
├── docker-compose.yml            # MySQL 容器配置
├── requirements.txt              # Python 依赖
├── .env                          # 环境变量（密钥、数据库配置）
└── .gitignore
```

## 架构

```
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

### 数据流

1. 浏览器上传 DOCX
2. FastAPI 读取文件字节
3. `docx_tools` 提取文本和格式证据
4. `memory` 识别提交人和论文题名
5. MySQL 查询最近一版审核记录
6. Agent 合并 SKILL 工具与 MCP 工具
7. 决策 LLM 选择下一项工具
8. 本地工具或 MCP 返回结构化证据
9. Agent 把工具结果写回模型上下文
10. 决策 LLM 继续调用工具或生成报告
11. MySQL 保存报告和新版本号
12. FastAPI 通过 SSE 返回执行事件
13. 浏览器显示执行轨迹和审核意见

## 快速开始

### 前置要求

- Docker（用于运行 MySQL 和 Web 服务）
- LLM API Key（兼容 OpenAI 接口）

### 0. 配置环境变量

复制 `.env.example` 为 `.env`，填写必要信息：

```env
LLM_API_KEY=你的API密钥
LLM_BASE_URL=https://api.deepseek.com/v1     # 或其他兼容接口
LLM_MODEL=deepseek-chat                       # 模型名称

MYSQL_HOST=mysql                              # Docker 内使用服务名
MYSQL_PORT=3306
MYSQL_USER=paper_review_agent
MYSQL_PASSWORD=你的数据库密码
MYSQL_DATABASE=paper_review_agent
MYSQL_ROOT_PASSWORD=你的root密码              # 仅 Docker 部署需要

CROSSREF_MAILTO=你的联系邮箱     # 用于 Crossref API 限流
REVIEW_YEAR=2026
```

### 1. 一键启动（推荐）

```bash
docker compose up -d
```

Docker Compose 会自动：
- 启动 MySQL 8.0（端口 3307）
- 构建并启动 FastAPI Web 服务（端口 8765）
- 等待 MySQL 就绪后再启动 Web 服务

查看启动日志：

```bash
docker compose logs -f
```

服务就绪后，浏览器打开 `http://127.0.0.1:8765`

### 2. 手动启动（开发调试）

如果不需要 Docker 运行 Web 服务，也可以单独启动 MySQL，在本地运行 Python：

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. 生成测试材料（可选）

```bash
python scripts/create_materials.py
```

会在 `resources/` 目录生成 `论文初稿.docx` 和 `计算机学院本科毕业论文格式规范.docx`。

### 5. 启动服务

```bash
python -m uvicorn app.webapp:app --host 127.0.0.1 --port 8765
```

### 6. 使用

浏览器打开 `http://127.0.0.1:8765`

1. 选择 DOCX 文件上传
2. 点击「上传并解析」——系统提取文本和格式证据
3. 点击「开始审核」——LLM 依次调用工具，生成完整报告
4. 执行轨迹实时显示在左侧，最终报告以 Markdown 格式渲染

## 使用示例

### 首次审核

上传 `resources/论文初稿.docx`，系统会：
- 检查页面设置（A4、页边距）
- 检查章节顺序
- 检查标题/正文字体字号
- 逐条核验参考文献（通过 Crossref）
- 计算近五年文献占比
- 生成 Markdown 格式审核报告
- 保存到 MySQL（revision = 1）

### 修改版复审

修改论文后再次上传，系统会：
- 识别同一提交人和论文题名
- 读取历史审核记录
- 重新检查所有项目
- 报告中对比已修正/仍存在的问题
- 保存为新版本（revision = 2）

## 接口说明

| 接口 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 前端页面 |
| `/api/health` | GET | 服务健康检查 |
| `/api/config` | GET | 获取 MCP 工具和 SKILL 列表 |
| `/api/upload-docx` | POST | 上传 DOCX，返回文本和格式检查结果 |
| `/api/review` | POST | 发起审核，返回 SSE 事件流 |

## 测试

```bash
python -m unittest discover -s tests -v
```

三项核心测试：
- `test_extract_text` — DOCX 文本提取
- `test_format_check` — 格式检查（预期发现 2 项不符合）
- `test_identity_stays_stable_after_body_change` — 文档身份识别稳定性

## 核心设计原则

1. 格式规则来自规范文件，不来自模型记忆
2. DOCX 工具和 MCP 提供证据，决策 LLM 组织结论
3. SKILL 规定执行方法，Python 完成实际操作
4. 历史记录用于整改对比，本次材料仍需重新检查
5. 证据不足时保留「无法判断」「未能核实」或「暂缓判断」
6. API Key 和数据库密码只保存在 `.env`，不硬编码在 docker-compose.yml 或 SQL 脚本中
7. 执行轨迹只为实际耗时步骤显示毫秒数

## 常见问题

**MySQL 连接失败** — 确认 Docker 容器已启动：`docker ps | grep paper-review-mysql`

**LLM 接口返回 401** — 检查 `.env` 中的 `LLM_API_KEY`，去掉两端空格

**DOCX 解析失败** — 确认文件扩展名为 `.docx`，不是旧版 `.doc`

**审核报告没有对比历史** — 保持作者姓名/编号和论文题目字段不变，只修改正文内容