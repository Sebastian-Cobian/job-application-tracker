# Job Application Tracker

A full-stack web application for tracking job applications, built with **MySQL**, **Python / Flask**, and **HTML / CSS**.

Track the companies you're interested in, the jobs they post, the applications you submit (including every interview), and the people you know at each company. A **Job Match** page compares your skills against every saved job and ranks them by match percentage.

## Features

| Page | What it does |
|------|--------------|
| **Dashboard** | Totals for applications, jobs, companies and contacts; response rate; average salary; applications-by-status chart; upcoming interviews; recent applications |
| **Companies** | List / search, detail view (with the company's jobs, contacts and applications), add, edit, delete |
| **Jobs** | List / search / filter by type, detail view, add, edit, delete. Requirements (skills, years of experience, education) are stored in a `JSON` column |
| **Applications** | List / search / filter by status, detail view with an interview timeline, add, edit, delete. Interviews are stored in a `JSON` column |
| **Contacts** | List / search, detail view, add, edit, delete |
| **Job Match** | Enter your skills → see every job ranked by match %, with the skills you have and the skills you're missing |

Other details:

- **Validation** on every form: required fields, max lengths, valid URLs, emails and phone numbers, dates (application date can't be in the future), salary min ≤ max, valid dropdown values, unique company names. Errors are shown at the top of the form and your input is kept.
- **Delete with confirmation**: every delete button asks first and says what related records will also be removed (`ON DELETE CASCADE`).
- **SQL injection safe**: every query uses parameterized placeholders.
- **Responsive layout** that works on laptops and phones.

## Project Structure

```
job-application-tracker/
├── app.py               # Flask routes, form validation, Job Match algorithm
├── database.py          # MySQL connection + all SQL queries (CRUD for each table)
├── schema.sql           # Creates the job_tracker database, 4 tables, and sample data
├── test_job_match.py    # Unit tests for the Job Match algorithm
├── templates/           # Jinja2 HTML templates
│   ├── base.html            # Shared layout + navigation
│   ├── _macros.html         # Reusable pieces (badges, delete button, search bar)
│   ├── dashboard.html
│   ├── companies.html / company_detail.html / company_form.html
│   ├── jobs.html / job_detail.html / job_form.html
│   ├── applications.html / application_detail.html / application_form.html
│   ├── contacts.html / contact_detail.html / contact_form.html
│   ├── job_match.html
│   └── error.html
├── static/
│   └── style.css
├── requirements.txt
├── .env.example         # Template for your database credentials
├── AI_USAGE.md          # GenAI documentation
└── README.md
```

## Database Design

```
companies (1) ──< jobs (1) ──< applications
    │
    └──────< contacts
```

| Table | Key columns | Notes |
|-------|-------------|-------|
| `companies` | `company_id` PK | `company_name` is required and unique |
| `jobs` | `job_id` PK, `company_id` FK → companies | `job_type` ENUM, `requirements` **JSON**, CHECK salary_min ≤ salary_max |
| `applications` | `application_id` PK, `job_id` FK → jobs | `status` ENUM, `cover_letter_sent` BOOLEAN, `interview_data` **JSON** |
| `contacts` | `contact_id` PK, `company_id` FK → companies | |

All foreign keys use `ON DELETE CASCADE`, so deleting a company removes its jobs, contacts and applications.

**JSON formats**

```json
// jobs.requirements
{"skills": ["Python", "SQL", "Flask"], "experience_years": 1, "education": "Bachelor's"}

// applications.interview_data
{"interviews": [{"date": "2026-09-12", "type": "Phone Screen", "interviewer": "Maria Lopez", "notes": "..."}]}
```

## Setup Instructions

### 1. Prerequisites

- **Python 3.9+** — check with `python --version` (or `python3 --version`)
- **MySQL 8.0+** server running locally (MariaDB 10.5+ also works) — check with `mysql --version`
- **Git**

### 2. Clone the repository

```bash
git clone https://github.com/Sebastian-Cobian/job-application-tracker.git
cd job-application-tracker
```

### 3. Create a virtual environment and install dependencies

macOS / Linux:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Windows (PowerShell):

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Create the database

This creates the `job_tracker` database, all 4 tables, and sample data.
(**Warning:** it drops any existing `job_tracker` database first.)

```bash
mysql -u root -p < schema.sql
```

On Windows PowerShell, `<` redirection doesn't work, so use:

```powershell
Get-Content schema.sql | mysql -u root -p
```

Or open `schema.sql` in **MySQL Workbench** and click the ⚡ *Execute* button.

### 5. Configure your database credentials

Copy the example file and put your MySQL password in it:

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Then edit `.env`:

```
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=job_tracker
```

(`.env` is in `.gitignore`, so your password never gets committed. You can also set these as normal environment variables instead.)

### 6. Run the app

```bash
python app.py
```

Open **http://127.0.0.1:5000** in your browser.

### 7. (Optional) Run the tests

```bash
python -m unittest test_job_match.py
```

## Using the Job Match Feature

1. Open **Job Match** in the navigation bar.
2. Type your skills separated by commas, e.g. `Python, SQL, Flask`.
3. Click **Find Matches**.

Each job's score is:

```
match % = (number of the job's required skills you have) / (number of required skills) × 100
```

With the sample data, `Python, SQL, Flask` gives:

```
1. Software Developer at TechCorp – 100% (3/3 skills)
2. Data Analyst at DataCo        –  67% (2/3 skills)   Missing: Tableau
...
```

Matching ignores capitalization and extra spaces, and understands common abbreviations (`JS` → JavaScript, `Postgres` → PostgreSQL, `K8s` → Kubernetes, …). You can also set a minimum match % to hide weak matches. Jobs with no listed skills are skipped.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Access denied for user 'root'@'localhost'` | Wrong password in `.env` — double-check `DB_PASSWORD`. |
| `Unknown database 'job_tracker'` | Run `schema.sql` (step 4). |
| `Can't connect to MySQL server` | Start the MySQL service (Windows: *Services → MySQL80 → Start*; macOS: `brew services start mysql`). |
| `ModuleNotFoundError: No module named 'flask'` | Activate the virtual environment and run `pip install -r requirements.txt`. |
| Port 5000 already in use (common on macOS because of AirPlay) | Run `flask --app app run --port 5001` and open http://127.0.0.1:5001. |
| `mysql` command not found | Use the full path (e.g. `"C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe"`) or run the script in MySQL Workbench. |

## Technologies

- MySQL 8 (JSON columns, ENUMs, foreign keys with cascade, CHECK constraints)
- Python 3, Flask 3, mysql-connector-python
- HTML5, CSS3 (no framework — custom responsive stylesheet), Jinja2 templates
- Git / GitHub
- GenAI assistance — see [AI_USAGE.md](AI_USAGE.md)

## Demo Video

The demo video showing the client (browser), server (Flask terminal) and database (MySQL) is in the repository: **`demo_video.mp4`**
