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