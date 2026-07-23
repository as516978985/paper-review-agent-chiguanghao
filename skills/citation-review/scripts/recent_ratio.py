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