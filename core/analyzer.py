"""Offline ATS scoring engine - no API key needed."""
import re

from .skills import extract_keywords, extract_job_title, extract_years_required, extract_education

SECTION_PATTERNS = {
    "Experience": r"\b(work\s+)?(professional\s+)?experience\b|\bemployment\b|\bwork\s+history\b",
    "Education": r"\beducation\b|\bacademics?\b|\bqualifications?\b",
    "Skills": r"\b(skills|technical\s+skills|core\s+competenc(y|ies)|technologies|tech\s+stack)\b",
    "Contact": r"([a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,})|(\+?\d[\d\s().-]{7,}\d)",
}

ACTION_VERBS = {
    "led", "built", "developed", "managed", "designed", "improved", "created",
    "delivered", "automated", "launched", "owned", "implemented", "optimized",
    "reduced", "increased", "drove", "migrated", "architected", "shipped",
    "scaled", "mentored", "negotiated", "analyzed", "streamlined", "established",
    "coordinated", "executed", "generated", "trained", "resolved", "maintained",
    "integrated", "refactored", "deployed", "configured", "tested", "planned",
}


def analyze_resume_only(resume_text: str) -> dict:
    """Score general ATS-friendliness of a resume with NO job description."""
    lower = resume_text.lower()
    words = len(resume_text.split())

    bullets = []
    for m in re.finditer(r"(?m)^\s*(?:[•\-*▪◦‣]|[-–]\s+)\s+(.+)", resume_text):
        b = m.group(1).strip()
        if len(b.split()) >= 3:
            bullets.append(b)

    verb_starts = sum(1 for b in bullets if b.split()[0].lower().strip(",.") in ACTION_VERBS)
    quantified = sum(1 for b in bullets if re.search(r"\d|%|[$₹€£]\s?\d|\d+x", b))
    n_bullets = len(bullets)
    verb_ratio = (verb_starts / n_bullets) if n_bullets else 0.0
    quant_ratio = (quantified / n_bullets) if n_bullets else 0.0
    date_count = len(re.findall(r"\b(?:19|20)\d{2}\b", resume_text))

    checks = [
        ("Email address found",
         bool(re.search(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}", lower)), 8,
         "Add a professional email at the top - parsers key off it."),
        ("Phone number found",
         bool(re.search(r"\+?\d[\d\s().-]{7,}\d", resume_text)), 7,
         "Add a phone number in your header."),
        ("Experience section found",
         bool(re.search(SECTION_PATTERNS["Experience"], lower)), 10,
         "Rename/add an 'Experience' or 'Work History' heading."),
        ("Education section found",
         bool(re.search(SECTION_PATTERNS["Education"], lower)), 6,
         "Add an 'Education' heading with degree + year."),
        ("Skills section found",
         bool(re.search(SECTION_PATTERNS["Skills"], lower)), 9,
         "Add a 'Skills' section listing hard skills as plain keywords."),
        ("Uses bullet points", n_bullets >= 5, 10,
         "Convert dense paragraphs into 3-5 bullet points per role."),
        ("Reasonable length (250-1000 words)", 250 <= words <= 1000, 8,
         f"Your resume is {words} words. Aim for ~400-800: one page early-career, two max senior."),
        ("Strong action verbs open most bullets", verb_ratio >= 0.6, 12,
         'Start bullets with verbs like "Built", "Led", "Automated" - avoid "Responsible for".'),
        ("Achievements are quantified", quant_ratio >= 0.3, 12,
         "Add numbers to bullets: %, ₹/$ amounts, time saved, scale (users, requests, team size)."),
        ("Dates present for roles", date_count >= 2, 8,
         "Add start-end years (e.g. 2021 - Present) for every role - ATS parses tenure from these."),
        ("No first-person pronouns", not re.search(r"\b(i|me|my|mine)\b", lower), 4,
         'Remove "I/my/me" - resumes use implied first person.'),
        ("Has a summary/profile section",
         bool(re.search(r"\b(summary|profile|objective|about\s+me)\b", lower)), 4,
         'Add a 2-3 line "Summary" at top with role + years + specialty.'),
        ("Clean text (no table/column artifacts)", "\t\t" not in resume_text, 2,
         "Avoid tables/multi-column layouts - many ATS parsers scramble them."),
    ]

    score = round(sum(w for _, ok, w, _ in checks if ok) / sum(c[2] for c in checks) * 100)
    suggestions = [tip for _, ok, _, tip in checks if not ok]
    if not suggestions:
        suggestions = ["Great baseline! For job-specific matching, use the Resume & JD tab."]

    return {"score": score, "grade": _grade(score), "checks": checks, "suggestions": suggestions}


def analyze(resume_text: str, jd_text: str) -> dict:
    resume_lower = resume_text.lower()
    jd_lower = jd_text.lower()

    keywords = extract_keywords(jd_text)
    matched = {k: w for k, w in keywords.items() if re.search(r"(?<![a-z0-9])" + re.escape(k) + r"(?![a-z0-9])", resume_lower)}
    missing = {k: w for k, w in keywords.items() if k not in matched}

    total_w = sum(keywords.values()) or 1
    matched_w = sum(matched.values())
    keyword_score = round(matched_w / total_w * 100)

    # --- title match ---
    title = extract_job_title(jd_text)
    title_tokens = [t for t in re.findall(r"[a-zA-Z+#]+", title.lower())
                    if t not in {"the", "and", "for", "with", "of", "a", "an", "senior", "jr", "junior"}]
    if title_tokens:
        hits = sum(1 for t in title_tokens if t in resume_lower)
        title_score = round(hits / len(title_tokens) * 100)
    else:
        title_score = 0

    # --- experience ---
    years_needed = extract_years_required(jd_text)
    exp_score, est_years = _experience_check(resume_text, years_needed)

    # --- education ---
    edu_required = extract_education(jd_text)
    edu_hits = [e for e in edu_required if re.search(
        r"bachelor|master|ph\.?d|doctorate|mba|b\.?tech|m\.?tech|\bb\.\s?[e|s]\b|m\.\s?[e|s|c]\b|degree|university|college", resume_lower)]
    edu_score = 100 if not edu_required else (100 if edu_hits else 0)

    # --- formatting ---
    fmt_checks = {
        "Email or phone found": bool(re.search(SECTION_PATTERNS["Contact"], resume_text)),
        **{f"'{s}' section found": bool(re.search(rx, resume_lower)) for s, rx in SECTION_PATTERNS.items() if s != "Contact"},
        "Uses bullet points": bool(re.search(r"(?m)^\s*[•\-*▪◦‣]|\n\s*[-–]\s+\w", resume_text)),
        "Reasonable length (300-1200 words)": 300 <= len(resume_text.split()) <= 1200,
        "No tables/columns artifacts": "\t\t" not in resume_text,
    }
    fmt_score = round(sum(fmt_checks.values()) / len(fmt_checks) * 100)

    breakdown = {
        "Keyword / skill match": (keyword_score, 55),
        "Job-title alignment": (title_score, 10),
        "Experience fit": (exp_score, 15),
        "Education match": (edu_score, 8),
        "Formatting & parseability": (fmt_score, 12),
    }
    score = round(sum(pct * weight for pct, weight in breakdown.values()) / 100)

    suggestions = _build_suggestions(missing, title, title_tokens, title_score,
                                     years_needed, est_years, edu_required, fmt_checks)

    return {
        "score": score,
        "grade": _grade(score),
        "breakdown": breakdown,
        "formatting_checks": fmt_checks,
        "matched_keywords": sorted(matched, key=lambda k: -matched[k]),
        "missing_keywords": sorted(missing, key=lambda k: -missing[k]),
        "job_title": title,
        "years_required": years_needed,
        "years_in_resume": est_years,
        "education_required": edu_required,
        "suggestions": suggestions,
    }


def _experience_check(resume_text, needed):
    """Estimate candidate's experience from date ranges + stated 'X+ years'."""
    text = resume_text.lower()
    stated = re.findall(r"(\d{1,2})\s*\+?\s*years?(?:\s+of)?(?:\s+\w+){0,3}?\s+experience", text)
    if stated:
        best = max(int(s) for s in stated)
        return _score_years(best, needed), f"{best} (stated)"

    year_ranges = re.findall(r"((?:19|20)\d{2})\s*[-–—to]+\s*((?:19|20)\d{2}|present)", text)
    if year_ranges:
        spans, last_end = [], None
        for start_s, end_s in year_ranges:
            start = int(start_s)
            end = 2026 if end_s == "present" else int(end_s)
            if 0 < end - start <= 45:
                spans.append((start, end))
                last_end = max(last_end or end, end)
        if spans:
            merged = _merge_spans(spans)
            total = sum(e - s for s, e in merged)
            return _score_years(total, needed), f"{total} (from dates)"

    return (60 if needed is None else 0), "?"


def _merge_spans(spans):
    spans.sort()
    merged = [spans[0]]
    for s, e in spans[1:]:
        ls, le = merged[-1]
        if s <= le:
            merged[-1] = (ls, max(le, e))
        else:
            merged.append((s, e))
    return merged


def _score_years(actual, needed):
    if actual >= needed:
        return 100
    return max(0, round(actual / needed * 100))


def _grade(score):
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 50:
        return "Needs work"
    return "Poor"


def _build_suggestions(missing, title, title_tokens, title_score, years_needed,
                       est_years, edu_required, fmt_checks):
    tips = []
    top_missing = list(missing)[:8]
    if top_missing:
        tips.append(f"Add these keywords where you honestly can: **{', '.join(top_missing)}**")
    if title and title_score < 67:
        tips.append(f'Your resume never mentions the target role "{title}". Put it in your summary line, e.g. "Senior {title}"')
    if years_needed and est_years != "?":
        try:
            have = int(str(est_years).split()[0])
            if have < years_needed:
                tips.append(f"JD asks for ~{years_needed} yrs; resume shows ~{have}. Consider counting internships/freelance/projects toward it explicitly.")
        except ValueError:
            pass
    if years_needed and est_years == "?":
        tips.append("Could not estimate your experience - add a line like 'X+ years of experience in ...'")
    if edu_required and "Education" in fmt_checks and not fmt_checks["Education"]:
        tips.append(f"Add an Education section - the JD mentions: {', '.join(edu_required)}")
    for check, ok in fmt_checks.items():
        if not ok:
            tips.append(f"Fix formatting: {check}")
    if not tips:
        tips.append("Strong match. Tweak phrasing to mirror the JD's exact wording and apply.")
    return tips[:8]
