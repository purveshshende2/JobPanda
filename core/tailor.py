"""AI resume tailoring + cover letter generation."""
from .skills import extract_keywords

TAILOR_SYSTEM = """You are an expert resume writer and ATS optimization specialist.
Rules you MUST follow:
1. NEVER invent employers, job titles, dates, degrees, certifications, or metrics.
2. Only rephrase, reorder, and re-emphasize what the candidate actually did.
3. Mirror the exact terminology the job description uses (e.g. if JD says "built CI/CD pipelines", don't write "automation workflows").
4. Weave in missing keywords ONLY where they truthfully describe the candidate's existing experience.
5. Use strong action verbs, quantify wherever the source resume already implies numbers.
6. Keep it one page friendly: concise bullets, max 5 per role.
Output clean plain-text/markdown resume only - no commentary before or after."""

COVER_LETTER_SYSTEM = """You are an expert cover letter writer.
Rules:
1. NEVER invent experience the candidate does not have.
2. Sound human, confident, specific - no cliches like "I am writing to apply for".
3. Reference 2-3 concrete things from the candidate's real background that map to the JD's top requirements.
4. 250-320 words, 3-4 short paragraphs. Output only the letter text."""

DEEP_REVIEW_SYSTEM = """You are a senior technical recruiter and ATS expert performing a deep qualitative resume review.
Rules you MUST follow:
1. Quote the EXACT bullet or phrase you are critiquing - never critique vaguely.
2. NEVER invent experience, metrics, or skills for the candidate. Suggest rewrites only using facts present in their resume.
3. Be brutally honest but constructive. Rank issues by impact on getting interviews.
4. Output clean markdown only, in exactly these sections:
## Weakest bullets (fix these first)
For each of the 5-8 weakest bullets: quote it, one line why it's weak, then "→ Better:" with a truthful rewrite.
## Semantic keyword gaps
JD requirements that ARE likely true of the candidate but phrased differently (e.g. "K8s" vs "Kubernetes"). Give exact swap suggestions.
## Missing impact signals
Where numbers/metrics are implied but absent. Suggest what to quantify - mark anything they must fill in as [YOUR NUMBER].
## Verdict
2-3 sentences: biggest strength, biggest risk, top action."""


def deep_review(client, resume_text: str, jd_text: str, score: int, missing_keywords: list) -> str:
    user = f"""## ALGORITHMIC ATS RESULT (context - do not repeat it)
Score: {score}/100
Missing keywords detected: {', '.join(missing_keywords[:20]) if missing_keywords else 'none'}

## JOB DESCRIPTION
{jd_text}

## RESUME
{resume_text}

Give the deep review now."""
    return client.chat(DEEP_REVIEW_SYSTEM, user, temperature=0.3)


def tailor_resume(client, resume_text: str, jd_text: str) -> str:
    keywords = list(extract_keywords(jd_text, top_n=25).keys())
    user = f"""## JOB DESCRIPTION
{jd_text}

## KEYWORDS TO PRIORITIZE (mirror these terms where truthful)
{', '.join(keywords)}

## CANDIDATE'S CURRENT RESUME
{resume_text}

Rewrite this resume tailored to the job above. Return the full rewritten resume in markdown."""
    return client.chat(TAILOR_SYSTEM, user)


def cover_letter(client, resume_text: str, jd_text: str, company: str = "", role: str = "") -> str:
    user = f"""## JOB DESCRIPTION
{jd_text}

## COMPANY: {company or '(infer from JD)'}
## ROLE: {role or '(infer from JD)'}

## CANDIDATE'S RESUME
{resume_text}

Write a tailored cover letter."""
    return client.chat(COVER_LETTER_SYSTEM, user, temperature=0.7)
