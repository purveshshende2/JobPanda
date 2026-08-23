"""Skill taxonomy + keyword extraction from job descriptions."""
import re
from collections import Counter

KNOWN_SKILLS = {
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "sql", "bash",
    "html", "css", "matlab", "vba",
    # Frontend
    "react", "next.js", "vue", "angular", "svelte", "redux", "tailwind",
    "bootstrap", "jquery", "webpack", "vite", "graphql", "rest api", "microservices",
    # Backend / frameworks
    "django", "flask", "fastapi", "spring boot", "node.js", "express", ".net",
    "laravel", "rails", "hibernate", "asp.net",
    # Data / AI
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "keras",
    "machine learning", "deep learning", "nlp", "computer vision", "llm",
    "generative ai", "langchain", "openai", "hugging face", "spark", "hadoop",
    "kafka", "airflow", "dbt", "snowflake", "databricks", "etl", "data pipeline",
    "data warehouse", "tableau", "power bi", "looker", "excel", "matplotlib",
    "seaborn", "plotly", "statistics", "a/b testing", "experimentation",
    # Cloud / devops
    "aws", "azure", "gcp", "google cloud", "docker", "kubernetes", "terraform",
    "ansible", "jenkins", "ci/cd", "git", "github actions", "linux", "prometheus",
    "grafana", "elk", "serverless", "lambda", "s3", "ec2", "iam", "vpc",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "sqlite",
    "dynamodb", "oracle", "sql server", "cassandra",
    # Testing
    "pytest", "jest", "selenium", "cypress", "playwright", "unit testing",
    "test automation", "tdd", "junit",
    # Mobile
    "android", "ios", "flutter", "react native", "swiftui",
    # Security
    "cybersecurity", "penetration testing", "siem", "oauth", "encryption",
    "soc 2", "gdpr", "hipaa",
    # Product / business
    "agile", "scrum", "kanban", "jira", "confluence", "product management",
    "roadmap", "stakeholder management", "project management", "okrs", "kpis",
    "business analysis", "requirements gathering", "user stories", "figma",
    "wireframing", "user research", "a/b test", "sql analytics", "market research",
    # Marketing / sales
    "seo", "sem", "google analytics", "content marketing", "email marketing",
    "crm", "salesforce", "hubspot", "lead generation", "copywriting",
    "social media marketing", "paid ads", "b2b", "b2c", "saas",
    # Finance / ops
    "financial modeling", "forecasting", "budgeting", "accounting", "reconciliation",
    "accounts payable", "accounts receivable", "sap", "quickbooks", "procurement",
    "supply chain", "inventory management", "logistics", "vendor management",
    # HR
    "recruiting", "onboarding", "performance management", "hris", "payroll",
    "employee engagement",
    # Soft-ish (still keyword-scannable)
    "leadership", "communication", "problem solving", "teamwork", "mentoring",
    "cross-functional", "time management", "presentation", "negotiation",
}

# words that never make good standalone keywords
STOPWORDS = set(
    """a an and are as at be been but by can for from has have if in into is it
    its of on or our ours out over own that the their them they this to was we
    were will with you your etc via using use used work working works role team
    teams company experience experiences years year strong ability able across
    about above after all also always am any because before being below between
    both do does doing down during each few more most other some such than then
    through too under until up very what when where which while who whom why
    would should could may might must shall get got make made want well help
    helps new like join us our we're you'll day days job jobs position
    candidate candidates requirement requirements responsibility responsibilities
    preferred required plus nice great good excellent must-have opportunity
    benefits salary equal employer diversity race gender color national origin""".split()
)

WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z+#./-]{1,}")
BOUNDARY_SKILLS = {s: re.compile(r"(?<![a-z0-9])" + re.escape(s) + r"(?![a-z0-9])") for s in KNOWN_SKILLS}


def extract_keywords(jd_text: str, top_n: int = 40) -> dict:
    """Return {keyword: weight} found in a job description.

    weight 3 = known skill term, weight 1 = repeated domain phrase.
    """
    jd_lower = jd_text.lower()
    weights = {}

    for skill, rx in BOUNDARY_SKILLS.items():
        hits = len(rx.findall(jd_lower))
        if hits:
            weights[skill] = 2 + min(hits, 2)

    words = [w.lower() for w in WORD_RE.findall(jd_text)]
    words = [w.strip("-.") for w in words]
    words = [
        w for w in words
        if w not in STOPWORDS and len(w) > 2 and not w[0].isdigit() and w not in KNOWN_SKILLS
    ]

    unigrams = Counter(words)
    bigrams = Counter(f"{words[i]} {words[i + 1]}" for i in range(len(words) - 1))

    for phrase, count in bigrams.most_common(60):
        if count < 2 or any(t in STOPWORDS for t in phrase.split()):
            continue
        if any(phrase in k or k in phrase for k in weights):
            continue
        weights[phrase] = 1 + min(count // 2, 2)
    for word, count in unigrams.most_common(40):
        if count < 3:
            continue
        if any(word in k for k in weights):
            continue
        weights[word] = 1

    ranked = dict(sorted(weights.items(), key=lambda kv: -kv[1]))
    return dict(list(ranked.items())[:top_n])


def extract_job_title(jd_text: str) -> str:
    patterns = [
        r"(?:job\s*title|position|role)\s*[:\-]\s*(.+)",
        r"hiring\s+(?:an?\s+)?(.{3,50}?)(?:\n|,|\.|\(|to join)",
        r"^(.{3,60})\s*\|\s*.{0,40}$",
    ]
    first_lines = [l.strip() for l in jd_text.splitlines() if l.strip()][:5]
    for rx in patterns:
        m = re.search(rx, jd_text, re.IGNORECASE | re.MULTILINE)
        if m:
            title = m.group(1).strip().strip("*#").strip()
            if 2 < len(title) < 60:
                return title
    if first_lines:
        guess = re.sub(r"[^\w\s/&+-]", "", first_lines[0])[:60].strip()
        return guess
    return ""


def extract_years_required(jd_text: str):
    years = [int(y) for y in re.findall(r"(\d{1,2})\s*\+?\s*years?", jd_text.lower())]
    return max(years) if years else None


def extract_education(jd_text: str) -> list:
    edu_terms = []
    checks = {
        "bachelor's": r"bachelo?r'?s?(?:\s+(?:of\s+)?(?:science|arts|engineering|technology|degree))?\b|\bbs\b|\bb\.?tech\b|\bbe\b(?=\s+(?:in|tech))",
        "master's": r"master'?s?(?:\s+(?:of\s+)?(?:science|arts|business|engineering|technology|degree))?\b|\bms\b|\bm\.?tech\b|\bmba\b",
        "phd": r"\bph\.?d\b|doctorate",
    }
    for label, rx in checks.items():
        if re.search(rx, jd_text.lower()):
            edu_terms.append(label)
    return edu_terms
