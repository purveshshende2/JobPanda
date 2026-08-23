# 🐼 JobPanda: AI Job Application Assistant

Give it your **resume + a job description** and it will:

1. 🔍 **Score your resume against the job (ATS)**: keyword/skill coverage, title alignment, experience fit, education, formatting. Works fully offline.
2. 🔑 **Find missing keywords & skills** the JD expects but your resume lacks.
3. ✍️ **Rewrite/tailor your resume** for that exact job (AI, never invents experience).
4. 📝 **Write a matching cover letter** (AI).
5. 💼 **Search jobs** across boards (Adzuna live search + deep links to LinkedIn/Indeed/Naukri/Glassdoor).

## Quick start

```bash
cd 1
./run.sh            # installs deps + launches UI
```

Or manually:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## How to use

1. **Tab 1**: upload resume (PDF/DOCX/TXT) + paste JD → click *Run ATS Analysis*.
2. **Tab 2**: see score /100, breakdown bars, matched vs missing keywords, fix-list.
3. **Tab 3**: generate a tailored resume, edit inline, download as `.md` or `.docx`.
4. **Tab 4**: generate a matching cover letter, download `.txt`.
5. **Tab 5**: search live jobs for the role.

> ⚠️ Always review AI output for truthfulness. The tool rephrases your real experience; it never fabricates.

## Project layout

```
1/
├── app.py               # Streamlit UI
├── core/
│   ├── parser.py        # PDF/DOCX/TXT text extraction
│   ├── skills.py        # Skill taxonomy + JD keyword extraction
│   ├── analyzer.py      # Offline ATS scoring engine
│   ├── llm.py           # OpenAI-compatible client
│   ├── tailor.py        # Resume rewrite + cover letter prompts
│   └── jobsearch.py     # Adzuna + board deep links
├── sample_data/         # Try it instantly with samples
└── .env.example         # API keys template
```
