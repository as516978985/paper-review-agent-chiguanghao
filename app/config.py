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