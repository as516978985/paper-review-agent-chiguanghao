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
    return " ".join(re.findall(r"[\w一-鿿]+", value))


def similarity(left: str, right: str) -> float:
    return round(SequenceMatcher(None, normalize(left), normalize(right)).ratio(), 3)


def _extract_surnames(authors_str: str) -> list[str]:
    """从作者字符串中提取姓氏用于匹配。"""
    parts = re.split(r"[;。；、,，\s]+", authors_str.strip())
    surnames = []
    for part in parts:
        part = part.strip().rstrip(".,")
        if not part or len(part) < 2:
            continue
        tokens = part.split()
        surnames.append(tokens[-1])  # 取最后一个词作为姓氏
    return surnames


def _author_score(query_authors: str, record_authors: list[str]) -> float:
    """计算查询作者与登记作者的匹配得分（0.0 ~ 1.0）。

    策略：提取姓氏做匹配，只要有一个查询姓氏匹配到任一登记作者姓氏就视为匹配。
    匹配得分 = (匹配数 / 查询姓氏数) * 0.8，最高 0.8。
    无作者信息时返回 0.5 中性值。
    """
    if not query_authors or not record_authors:
        return 0.5
    query_surnames = _extract_surnames(query_authors)
    record_surnames = []
    for name in record_authors:
        tokens = name.split()
        if tokens:
            record_surnames.append(tokens[-1].rstrip(".,"))

    if not query_surnames or not record_surnames:
        return 0.5

    # 规范化姓氏
    qs_list = [s.rstrip(".,").lower() for s in query_surnames]
    rs_list = [s.rstrip(".,").lower() for s in record_surnames]

    matches = 0
    for qs in qs_list:
        for rs in rs_list:
            if qs == rs or rs.startswith(qs) or qs.startswith(rs):
                matches += 1
                break

    if matches == 0:
        return 0.0
    # 分数 = 匹配比例 * 0.8，确保单作者匹配时得分合理
    ratio = matches / len(qs_list) if qs_list else 0
    return min(ratio * 0.8, 0.8)


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
def search_by_title(title: str, author: str = "", limit: int = 5) -> dict:
    """按题名和作者查询候选记录，返回按综合相似度排序的列表。

    同时提供 author 参数可以显著提高匹配准确率。
    """
    query = title.strip()
    if len(query) < 4:
        return {"error": "title_too_short"}

    # 使用 bibliographic 搜索，将题名和作者合并为一条查询字符串
    # 这比分开传 query.title 和 query.author 更准确
    search_query = query
    if author.strip():
        search_query = f"{query} {author.strip()}"
    params = {"query.bibliographic": search_query, "rows": max(1, min(limit, 10))}

    try:
        response = session.get(CROSSREF, params=params, timeout=10)
        response.raise_for_status()
        candidates = []
        for item in response.json()["message"]["items"]:
            record = metadata(item)
            title_sim = similarity(query, record["title"])
            author_sim = _author_score(author, record["authors"])
            # 综合得分：题名权重 0.6，作者权重 0.4
            combined = round(title_sim * 0.6 + author_sim * 0.4, 3)
            record["title_similarity"] = title_sim
            record["author_similarity"] = author_sim
            record["combined_score"] = combined
            candidates.append(record)

        candidates.sort(key=lambda item: item["combined_score"], reverse=True)
        return {
            "query": {"title": query, "author": author.strip()},
            "candidates": candidates,
        }
    except requests.RequestException as exc:
        return {"error": "network_failure", "detail": str(exc)}


@mcp.tool()
def check_citation(
    citation: str,
    doi: str = "",
    title: str = "",
    author: str = "",
) -> dict:
    """核验一条参考文献并比对题名和作者。

    推荐同时提供 title 和 author 参数以获得最准确的核验结果。
    """
    found = doi.strip()
    if not found:
        match = DOI_PATTERN.search(citation)
        found = match.group(0) if match else ""

    # 有 DOI：直接查 DOI，再比对题名和作者
    if found:
        record = verify_doi(found)
        if record.get("error") or not record.get("exists"):
            return {"verdict": "unverified", "record": record}

        title_sim = similarity(title, record["title"]) if title else None
        author_sim = _author_score(author, record["authors"]) if author else None

        # 综合判定
        reasons = []
        if title_sim is not None and title_sim < 0.8:
            reasons.append("题名不匹配")
        if author_sim is not None and author_sim < 0.5:
            reasons.append("作者不匹配")

        if not reasons:
            verdict = "verified"
        elif title_sim is not None and title_sim >= 0.8:
            # 题名匹配但作者不匹配 → 可能是同名不同作者
            verdict = "mismatch"
        else:
            verdict = "mismatch"

        result = {
            "verdict": verdict,
            "title_similarity": title_sim,
            "author_similarity": author_sim,
            "record": record,
        }
        if reasons:
            result["mismatch_reasons"] = reasons
        return result

    # 无 DOI：用题名+作者搜索
    if title:
        result = search_by_title(title, author=author)
        candidates = result.get("candidates") or []
        best = candidates[0] if candidates else None

        if best:
            cs = best.get("combined_score", 0)
            # 综合得分 >= 0.7 视为已核实
            if cs >= 0.7:
                return {
                    "verdict": "verified",
                    "combined_score": cs,
                    "best_candidate": best,
                    "search": result,
                }
            else:
                # 得分低时用 fallback：不加作者再搜一次
                if author:
                    fallback = search_by_title(title, author="")
                    fb_candidates = fallback.get("candidates") or []
                    fb_best = fb_candidates[0] if fb_candidates else None
                    if fb_best and fb_best.get("combined_score", 0) > cs:
                        return {
                            "verdict": "unverified",
                            "combined_score": fb_best.get("combined_score", 0),
                            "best_candidate": fb_best,
                            "search_with_author": result,
                            "search_fallback": fallback,
                            "note": "带作者的搜索未找到高匹配结果，此为不加作者的搜索结果",
                        }
                return {
                    "verdict": "unverified",
                    "combined_score": cs,
                    "best_candidate": best,
                    "search": result,
                }
        return {"verdict": "unverified", "search": result}

    return {"verdict": "unverified", "detail": "缺少 DOI 和题名"}


if __name__ == "__main__":
    mcp.run(transport="stdio")