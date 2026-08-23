"""Multi-board job search via Adzuna API + fallback deep links."""
import urllib.parse

import requests

BOARDS = {
    "LinkedIn": "https://www.linkedin.com/jobs/search/?keywords={q}&location={l}",
    "Indeed": "https://www.indeed.com/jobs?q={q}&l={l}",
    "Naukri": "https://www.naukri.com/{q}-jobs",
    "Glassdoor": "https://www.glassdoor.com/Job/jobs.htm?sc.keyword={q}&locT=&locId=",
}


def board_links(query: str, location: str = "") -> dict:
    q = urllib.parse.quote(query)
    l = urllib.parse.quote(location)
    return {name: url.format(q=q, l=l) for name, url in BOARDS.items()}


def search_adzuna(app_id: str, app_key: str, query: str, location: str = "",
                  country: str = "in", results: int = 15) -> list:
    """Search jobs via Adzuna (free tier). Returns list of job dicts."""
    if not app_id or not app_key:
        return []
    try:
        resp = requests.get(
            f"https://api.adzuna.com/v1/api/jobs/{country}/search/1",
            params={
                "app_id": app_id,
                "app_key": app_key,
                "what": query,
                "where": location,
                "results_per_page": results,
                "content-type": "application/json",
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException:
        return []

    jobs = []
    for r in data.get("results", []):
        jobs.append({
            "title": r.get("title", "").strip(),
            "company": (r.get("company") or {}).get("display_name", ""),
            "location": (r.get("location") or {}).get("display_name", ""),
            "salary": _salary_str(r),
            "url": r.get("redirect_url", ""),
            "description": (r.get("description") or "")[:400],
        })
    return jobs


def _salary_str(r) -> str:
    lo, hi = r.get("salary_min"), r.get("salary_max")
    if not lo and not hi:
        return ""
    cur = r.get("salary_currency") or ""
    if hi and lo and round(lo / 1000) != round(hi / 1000):
        return f"{cur}{round(lo):,} - {cur}{round(hi):,}"
    return f"{cur}{round((lo or hi)):,}+"
