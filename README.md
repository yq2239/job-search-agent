# Smart Job Tracker

Smart Job Tracker is a local-first job-search workspace that keeps its application code separate from every user's private career data.

The repository contains only reusable code, fictional examples, tests, and documentation. Real résumés, career profiles, eligibility requirements, company notes, job records, application decisions, and referrals live in a private state directory outside the Git repository.

```text
Public Git repository                    Private local state
────────────────────────────────────     ────────────────────────────────────
jobtracker/ application code             profile/career.json
examples/state/ fictional templates      profile/requirements.json
tests/                                   profile/matching.json
README.md and AGENTS.md                   data/companies.json
                                         data/jobs.json
                                         resume/resume.md
```

This design lets multiple people use the same public code without sharing personal information. Each person initializes and maintains a separate private state directory.

## What the tracker does

- Stores a structured career profile and target-role preferences.
- Applies hard location, sponsorship, and education requirements.
- Verifies that an official posting is live before saving it.
- Creates deterministic job IDs and prevents duplicate records.
- Preserves status, note, and verification history.
- Provides a private dashboard for filtering and reviewing jobs.
- Supports company-specific knowledge such as title conventions and referrals.

It never submits an application or contacts a recruiter automatically.

## Requirements

- Python 3.11 or newer
- Git
- Internet access when adding or re-verifying postings
- No third-party Python runtime dependencies

Check Python:

```bash
python3 --version
```

## Quick start

Clone the code repository:

```bash
git clone https://github.com/YOUR-USERNAME/job-search-agent.git
cd job-search-agent
```

Create an isolated environment and install the local command:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --editable .
```

On Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
python -m pip install --editable .
```

Initialize private state from the fictional templates:

```bash
python3 -m jobtracker init
```

By default, this creates:

```text
~/.smart-job-tracker/
├── data/
│   ├── companies.json
│   └── jobs.json
├── profile/
│   ├── career.json
│   ├── matching.json
│   └── requirements.json
└── resume/
    └── resume.md
```

The initializer:

- Requires the state directory to be outside the repository.
- Refuses to overwrite a non-empty directory.
- Creates private directory and file permissions where the operating system supports them.
- Copies only fictional examples unless `--from-dir` is explicitly supplied.

Confirm the active state location and validate it:

```bash
python3 -m jobtracker state-path
python3 -m jobtracker validate
```

Then replace the fictional Alex Chen information in the displayed state directory with your own information and start the dashboard:

```bash
python3 -m jobtracker web
```

Open [http://127.0.0.1:8765/](http://127.0.0.1:8765/) if a browser does not open automatically.

## Choosing a private state directory

The state-directory resolver uses this precedence:

1. The global `--state-dir` command-line option.
2. The `JOBTRACKER_STATE_DIR` environment variable.
3. A gitignored `.jobtracker.json` file in the repository root.
4. The default `~/.smart-job-tracker` directory.

### One-command override

The global option must appear before the subcommand:

```bash
python3 -m jobtracker --state-dir /private/path/job-state validate
python3 -m jobtracker --state-dir /private/path/job-state web
```

### Environment variable

```bash
export JOBTRACKER_STATE_DIR="$HOME/Documents/private-job-state"
python3 -m jobtracker validate
```

PowerShell:

```powershell
$env:JOBTRACKER_STATE_DIR = "$HOME\Documents\private-job-state"
python -m jobtracker validate
```

### Local pointer file

Copy the supplied example:

```bash
cp .jobtracker.example.json .jobtracker.json
```

Then edit the ignored `.jobtracker.json`:

```json
{
  "state_dir": "~/.smart-job-tracker"
}
```

Relative paths are resolved from the repository root. `.jobtracker.json` is ignored by Git because even a local path can reveal a username or directory structure.

## Migrating an existing tracker

An older checkout may contain real `data/`, `profile/`, and `resume/` directories inside the repository. Copy them into a new external state directory before deleting or sanitizing anything:

```bash
python3 -m jobtracker \
  --state-dir "$HOME/.smart-job-tracker" \
  init --from-dir /absolute/path/to/old/job-search-agent
```

The source must contain:

```text
data/jobs.json
data/companies.json
profile/career.json
profile/requirements.json
profile/matching.json
resume/resume.md
```

Additional regular files in those three directories, such as a local résumé PDF, are also copied during an explicit migration. The target must be empty, which prevents accidental replacement of an existing search.

After migration:

```bash
python3 -m jobtracker --state-dir "$HOME/.smart-job-tracker" validate
python3 -m jobtracker --state-dir "$HOME/.smart-job-tracker" state-path
```

Verify the private copy before removing any original files.

### Warning about existing Git history

Moving data out of the current working tree does not remove it from older commits. If a private repository previously tracked real candidate information, do **not** simply change that repository to public. Create a new sanitized public repository with fresh Git history after verifying that only fictional data remains.

## Personalizing private state

Edit files under the directory reported by:

```bash
python3 -m jobtracker state-path
```

Never put real candidate information in `examples/state/`; those files are public templates.

### 1. Résumé summary

Edit `resume/resume.md` in private state. Use a concise Markdown representation rather than storing a formatted résumé in the public code repository.

```markdown
# Alex Chen

Senior Analytics Engineer in Seattle, WA

## Summary

Analytics engineer with six years of experience building data models,
experimentation platforms, and executive metrics.

## Experience

### ExampleCo — Senior Analytics Engineer | 2022–Present

- Built trusted product metrics with SQL, dbt, and Snowflake.
- Designed and analyzed online experiments for growth products.
- Mentored analysts and partnered with engineering leaders.

## Skills

- SQL, Python, dbt, Airflow, Snowflake, experimentation, causal inference
```

Do not store government identifiers, immigration receipt numbers, passwords, identity documents, or confidential employer material.

### 2. Career profile

Edit `profile/career.json` in private state. It provides fit context to a person or AI agent.

```json
{
  "candidate": {
    "name": "Alex Chen",
    "headline": "Senior Analytics Engineer focused on experimentation",
    "location": "Seattle, WA",
    "region": "Greater Seattle Area",
    "years_of_experience": "6+",
    "current_employer": "ExampleCo"
  },
  "education": [
    {
      "degree_level": "bachelors",
      "degree": "BS",
      "field": "Statistics",
      "institution": "Example University",
      "end_date": "2019-06"
    }
  ],
  "experiences": [
    {
      "company": "ExampleCo",
      "title": "Senior Analytics Engineer",
      "start_date": "2022-04",
      "end_date": null,
      "current": true,
      "highlights": [
        "Built trusted product metrics with SQL, dbt, and Snowflake.",
        "Designed and analyzed online experiments for growth products."
      ]
    }
  ],
  "skills": {
    "analytics": ["experimentation", "causal inference", "product metrics"],
    "engineering": ["SQL", "Python", "dbt", "Airflow", "Snowflake"]
  },
  "domain_experience": ["consumer technology", "e-commerce"],
  "target_roles": [
    "Senior Analytics Engineer",
    "Senior Data Scientist",
    "Product Data Scientist"
  ],
  "roles_to_avoid": ["new graduate roles", "people-manager roles"],
  "source": "resume/resume.md",
  "notes": "Prefer senior individual-contributor roles."
}
```

Include title and level preferences explicitly. For example, note when general software-engineering roles are poor fits, when staff roles are too senior, or when a company uses an unusual title for your target work.

The tracker does not calculate a fit score directly from this file. The profile guides the human or agent supplying `--fit-score` when adding a job.

### 3. Hard requirements

Edit `profile/requirements.json` in private state. These are true deal-breakers, not mild preferences.

```json
{
  "schema_version": 1,
  "hard_filters": {
    "requires_employer_sponsorship_or_h1b_transfer": true,
    "immigration_context": {
      "current_status": "H-1B",
      "store_receipt_or_case_numbers": false
    },
    "allowed_location_group": "seattle_or_exceptional_us_remote",
    "allowed_locations": [
      "Seattle, WA",
      "Bellevue, WA",
      "Redmond, WA",
      "USA - Remote"
    ],
    "remote_policy": "allow_us_remote_only_for_exceptional_fit",
    "exclude_if_minimum_education_is": ["masters", "phd"],
    "candidate_highest_degree": "bachelors"
  },
  "unknown_fact_policy": "manual_review",
  "never_auto_apply": true
}
```

The current eligibility behavior is:

| Job fact | Result |
|---|---|
| Location matches `allowed_locations` | Continue evaluating |
| Location is outside the list | Ineligible |
| Location is empty, `unknown`, or `not stated` | Pending Review |
| Sponsorship is required and is `does_not_sponsor` | Ineligible |
| Sponsorship is required and is `unknown` | Pending Review |
| Sponsorship is not required | Sponsorship does not affect eligibility |
| Minimum education is excluded | Ineligible |
| Minimum education is `unknown` | Pending Review |
| Every enforced fact passes | Eligible and initially Discovered |

Implementation details:

- Location matching uses strings in `allowed_locations`. Include the exact forms used in job records, such as `New York, NY` or `USA - Remote`.
- `allowed_location_group` and `remote_policy` are guidance for people and agents; automated location eligibility relies on `allowed_locations`.
- Set `requires_employer_sponsorship_or_h1b_transfer` to `false` when sponsorship is not required.
- Never infer eligibility from silence. Record missing education or sponsorship evidence as `unknown`.

### 4. Matching priorities

Edit `profile/matching.json` in private state:

```json
{
  "schema_version": 1,
  "minimum_recommendation_score": 75,
  "weights": {
    "skills_and_experience": 35,
    "responsibility_fit": 25,
    "career_interest": 15,
    "location_preference": 10,
    "compensation": 5,
    "company_interest": 10
  },
  "notes": "Prefer senior IC roles with experimentation ownership."
}
```

Weights are a human/agent rubric rather than an automatic formula. A practical score interpretation is:

- **90–100:** exceptional fit.
- **80–89:** strong fit with a few reasonable gaps.
- **70–79:** plausible fit with meaningful ramp-up.
- **Below 70:** usually omit unless it supports a deliberate transition.

Hard requirements always take priority over fit score.

### 5. Companies and special notes

Edit `data/companies.json` in private state:

```json
{
  "schema_version": 1,
  "companies": [
    {
      "id": "COMP-ACME",
      "name": "Acme",
      "careers_url": "https://careers.example.com/jobs",
      "interest_level": "high",
      "active": true,
      "locations_of_interest": ["Seattle, WA", "USA - Remote"],
      "sponsorship_policy": "verify_per_role",
      "notes": "Prioritize senior experimentation and product analytics roles.",
      "special_notes": [
        {
          "recorded_at": "2026-08-17",
          "scope": "Acme Recommendations team",
          "source_type": "employee_referral",
          "note": "A trusted employee suggested Decision Scientist roles. Verify each posting independently."
        }
      ]
    }
  ]
}
```

Company notes are useful for:

- Unusual titles used for a relevant job family.
- Reliable advice from a trusted employee.
- Company-specific location conventions.
- Roles that are consistently too junior or too senior.
- Domains that look relevant by title but do not match the candidate.

A referral is not evidence of sponsorship, eligibility, or an interview. Verify every job independently.

List configured companies:

```bash
python3 -m jobtracker list-companies
```

New companies receive a generic dashboard icon unless a public logo is added to `jobtracker/web_ui.py`.

## Working with an AI agent

`AGENTS.md` is generic and instructs an agent to resolve private state before reading requirements. A useful request is:

> Run `python3 -m jobtracker state-path`, then read the active career,
> requirements, matching, and company files. Search Acme's official careers
> inventory comprehensively for senior analytics engineering, product data
> science, and experimentation roles. Check pagination and exact job levels.
> Verify each live official posting before adding it with
> `python3 -m jobtracker add-job`. Record concise evidence for location,
> education, sponsorship, seniority, and fit. Do not apply or contact anyone.

For company terminology:

> Acme calls product data scientists “Decision Scientists.” Include that title
> along with data scientist, analytics engineer, experimentation, causal
> inference, and machine learning. Do not rely on title matching alone.

Agents should prefer official career pages and official applicant-tracking-system postings over stale search-engine snippets.

## Adding a job

Always use `add-job`. Do not manually create job IDs or paste records into `jobs.json`.

```bash
python3 -m jobtracker add-job \
  --company "Acme" \
  --title "Senior Product Data Scientist" \
  --location "Seattle, WA" \
  --url "https://careers.example.com/jobs/12345" \
  --source-job-id "12345" \
  --sponsorship unknown \
  --min-education bachelors \
  --fit-score 88 \
  --evidence "Official posting lists Seattle and requires a bachelor's degree plus five years of product analytics, SQL, Python, and experimentation. Sponsorship is not stated."
```

Use the exact title from the official page. The command verifies that the posting is live and contains the expected title and an Apply action before saving it.

| Option | Meaning | Example |
|---|---|---|
| `--company` | Display name | `"Acme"` |
| `--title` | Exact official title | `"Senior Product Data Scientist"` |
| `--location` | Explicit posting location | `"Seattle, WA"` |
| `--url` | Direct official URL | `https://careers.example.com/jobs/12345` |
| `--source-job-id` | ATS or requisition ID | `12345` |
| `--sponsorship` | `sponsors`, `does_not_sponsor`, or `unknown` | `unknown` |
| `--min-education` | Lowest required degree or `unknown` | `bachelors` |
| `--fit-score` | Human/agent score from 0–100 | `88` |
| `--evidence` | Verified facts and uncertainty | Quoted sentence |

Valid education values:

```text
none, high_school, associates, bachelors, masters, phd, unknown
```

Canonical URL and source-ID checks prevent duplicates. Refreshing the same job preserves status and note history.

## Dashboard

Start it with:

```bash
python3 -m jobtracker web
```

Useful alternatives:

```bash
python3 -m jobtracker web --no-open
python3 -m jobtracker web --port 9000
```

The server binds to `127.0.0.1` by default and runs only while its process remains active. Stop it with `Ctrl+C`.

The dashboard provides:

- Status counts and company chips.
- Title, company, location, and evidence search.
- Company and status filters.
- Direct official-posting links.
- Fit scores and eligibility reasons.
- Status changes with append-only history.
- Private append-only job notes.

## Status workflow

| Stored status | Dashboard label | Intended use |
|---|---|---|
| `manual_review` | Pending Review | A required fact is unknown |
| `discovered` | Discovered | Verified and eligible, not personally reviewed |
| `interested` | Interested | Worth pursuing |
| `applied` | Applied | Application submitted by the user |
| `recommended` | Referred | Referral or trusted endorsement recorded |
| `skipped` | Not applying | User decided not to apply |
| `rejected` | Rejected | Employer rejected the application |
| `closed` | Closed | Posting is unavailable |
| `withdrawn` | Withdrawn | User withdrew |

Change status:

```bash
python3 -m jobtracker set-status JOB-ABC123DEF456 interested \
  --note "Strong match; review team and compensation"
```

Record a referral:

```bash
python3 -m jobtracker set-status JOB-ABC123DEF456 recommended \
  --note "Referred by a former teammate"
```

Add a note without changing status:

```bash
python3 -m jobtracker add-note JOB-ABC123DEF456 \
  --note "Hiring manager values experimentation-platform experience."
```

View complete history:

```bash
python3 -m jobtracker history JOB-ABC123DEF456
```

## Recommendations and freshness

List eligible, active, non-terminal jobs at the configured score threshold:

```bash
python3 -m jobtracker recommendations
python3 -m jobtracker recommendations --minimum-score 85
```

Pending Review jobs are intentionally omitted until hard facts are resolved. They remain visible in the dashboard.

Recheck all saved official postings:

```bash
python3 -m jobtracker verify-jobs
```

Verification results are appended to history. Confirmed unavailable postings become Closed without erasing earlier decisions or notes.

## Command reference

```text
python3 -m jobtracker [--state-dir PATH] init [--from-dir PATH]
python3 -m jobtracker [--state-dir PATH] state-path
python3 -m jobtracker [--state-dir PATH] validate
python3 -m jobtracker [--state-dir PATH] list-companies
python3 -m jobtracker [--state-dir PATH] add-job --help
python3 -m jobtracker [--state-dir PATH] recommendations [--minimum-score N]
python3 -m jobtracker [--state-dir PATH] set-status JOB-ID STATUS [--note TEXT]
python3 -m jobtracker [--state-dir PATH] add-note JOB-ID --note TEXT
python3 -m jobtracker [--state-dir PATH] history JOB-ID
python3 -m jobtracker [--state-dir PATH] verify-jobs
python3 -m jobtracker [--state-dir PATH] web [--host HOST] [--port PORT] [--no-open]
```

## Repository map

```text
.jobtracker.example.json   Example pointer to private state
.gitignore                 Prevents local state from being committed
AGENTS.md                  Generic AI-agent safety rules
README.md                  Setup and usage guide
examples/state/            Fictional initialization templates only
jobtracker/
  cli.py                   CLI and private-state integration
  core.py                  Eligibility, IDs, statuses, and notes
  paths.py                 State resolution and safe initialization
  verification.py          Live official-posting verification
  web.py                   Local HTTP server and API
  web_ui.py                Dashboard UI and public company marks
tests/                     Unit and dashboard tests
```

## Troubleshooting

### “State directory is not empty”

`init` will not overwrite existing files. Choose a new directory, or validate and use the existing one. Do not delete an existing state directory unless you have verified a backup.

### “State directory must be outside the public repository”

Choose a path such as `~/.smart-job-tracker` or another private directory. Real state is intentionally prohibited inside the Git checkout.

### The wrong profile is active

Run:

```bash
python3 -m jobtracker state-path
```

Then check, in precedence order, `--state-dir`, `JOBTRACKER_STATE_DIR`, `.jobtracker.json`, and the default directory.

### “Official page did not contain the expected job title”

Copy the exact live title, including level numbers and punctuation. An en dash (`–`) and hyphen (`-`) may differ.

### A job stays in Pending Review

Inspect `eligibility_reasons` in the dashboard or `history`. Do not replace unknown facts without evidence.

### A remote job is ineligible

Add the exact remote label used in the job record, such as `USA - Remote`, to the private `profile/requirements.json`, then refresh the job with `add-job`.

### Dashboard unavailable

Confirm the process is still running. If port 8765 is occupied:

```bash
python3 -m jobtracker web --port 9000
```

## Privacy and backups

- The external state files are plain JSON and Markdown, not encrypted.
- Use full-disk encryption and a trusted private backup.
- Keep the state directory out of cloud folders unless their privacy model is acceptable.
- Do not place credentials or identity documents in state.
- Keep `.jobtracker.json` untracked.
- Review `git status` and `git diff` before every public commit.
- Scan new fixtures and documentation for real names, email addresses, employers, immigration details, referrals, and job decisions.
- Never expose the dashboard on a public network without adding authentication and transport security.

## Development checks

Run after changing code or private state:

```bash
python3 -m jobtracker validate
python3 -m unittest discover -s tests -v
git diff --check
```

The codebase remains intentionally dependency-light so users can inspect exactly how their private job-search data is handled.
