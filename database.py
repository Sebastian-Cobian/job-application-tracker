"""
database.py - MySQL connection and data-access functions for the Job Tracker.

All SQL lives in this file so app.py only deals with HTTP / templates.
Every query uses parameterized placeholders (%s) to prevent SQL injection.
"""

import json
import os

import mysql.connector
from mysql.connector import Error  # noqa: F401  (re-exported for app.py)

try:  # optional: load settings from a .env file if python-dotenv is installed
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "job_tracker"),
}

JOB_TYPES = ["Full-time", "Part-time", "Contract", "Internship"]
APPLICATION_STATUSES = ["Applied", "Screening", "Interview", "Offer", "Rejected", "Withdrawn"]


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
def get_db():
    """Open a new MySQL connection using DB_CONFIG."""
    return mysql.connector.connect(**DB_CONFIG)


def query_all(sql, params=()):
    """Run a SELECT and return a list of dict rows."""
    conn = get_db()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        return cursor.fetchall()
    finally:
        conn.close()


def query_one(sql, params=()):
    """Run a SELECT and return a single dict row (or None)."""
    rows = query_all(sql, params)
    return rows[0] if rows else None


def execute(sql, params=()):
    """Run INSERT/UPDATE/DELETE, commit, and return lastrowid (for inserts)."""
    conn = get_db()
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def parse_json(value, default):
    """JSON columns come back as str (or bytes on some drivers); convert to Python."""
    if value is None or value == "":
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, (bytes, bytearray)):
        value = value.decode("utf-8")
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _like(term):
    return f"%{term}%"


# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------
def get_companies(search=""):
    sql = """
        SELECT c.*,
               (SELECT COUNT(*) FROM jobs j WHERE j.company_id = c.company_id)     AS job_count,
               (SELECT COUNT(*) FROM contacts ct WHERE ct.company_id = c.company_id) AS contact_count
        FROM companies c
    """
    params = ()
    if search:
        sql += " WHERE c.company_name LIKE %s OR c.industry LIKE %s OR c.city LIKE %s OR c.state LIKE %s"
        params = (_like(search),) * 4
    sql += " ORDER BY c.company_name"
    return query_all(sql, params)


def get_company(company_id):
    return query_one("SELECT * FROM companies WHERE company_id = %s", (company_id,))


def company_name_exists(name, exclude_id=None):
    sql = "SELECT company_id FROM companies WHERE LOWER(company_name) = LOWER(%s)"
    params = [name]
    if exclude_id:
        sql += " AND company_id <> %s"
        params.append(exclude_id)
    return query_one(sql, tuple(params)) is not None


def add_company(data):
    return execute(
        """INSERT INTO companies (company_name, industry, website, city, state, notes)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (data["company_name"], data["industry"], data["website"],
         data["city"], data["state"], data["notes"]),
    )


def update_company(company_id, data):
    execute(
        """UPDATE companies
           SET company_name=%s, industry=%s, website=%s, city=%s, state=%s, notes=%s
           WHERE company_id=%s""",
        (data["company_name"], data["industry"], data["website"],
         data["city"], data["state"], data["notes"], company_id),
    )


def delete_company(company_id):
    # jobs, contacts (and through jobs, applications) are removed by ON DELETE CASCADE
    execute("DELETE FROM companies WHERE company_id = %s", (company_id,))


def get_company_dependents(company_id):
    """Counts of rows that will be cascade-deleted with a company."""
    return query_one(
        """SELECT
             (SELECT COUNT(*) FROM jobs WHERE company_id = %s) AS jobs,
             (SELECT COUNT(*) FROM contacts WHERE company_id = %s) AS contacts,
             (SELECT COUNT(*) FROM applications a JOIN jobs j ON a.job_id = j.job_id
               WHERE j.company_id = %s) AS applications""",
        (company_id, company_id, company_id),
    )


def get_company_choices():
    return query_all("SELECT company_id, company_name FROM companies ORDER BY company_name")


# ---------------------------------------------------------------------------
# Jobs
# ---------------------------------------------------------------------------
def _decorate_job(job):
    if job:
        job["requirements"] = parse_json(job.get("requirements"), {})
        job["skills"] = job["requirements"].get("skills", []) if isinstance(job["requirements"], dict) else []
    return job


def get_jobs(search="", job_type="", company_id=None):
    sql = """
        SELECT j.*, c.company_name,
               (SELECT COUNT(*) FROM applications a WHERE a.job_id = j.job_id) AS application_count
        FROM jobs j
        JOIN companies c ON j.company_id = c.company_id
        WHERE 1=1
    """
    params = []
    if search:
        sql += " AND (j.job_title LIKE %s OR c.company_name LIKE %s)"
        params += [_like(search), _like(search)]
    if job_type:
        sql += " AND j.job_type = %s"
        params.append(job_type)
    if company_id:
        sql += " AND j.company_id = %s"
        params.append(company_id)
    sql += " ORDER BY j.date_posted DESC, j.job_id DESC"
    return [_decorate_job(j) for j in query_all(sql, tuple(params))]


def get_job(job_id):
    job = query_one(
        """SELECT j.*, c.company_name FROM jobs j
           JOIN companies c ON j.company_id = c.company_id
           WHERE j.job_id = %s""",
        (job_id,),
    )
    return _decorate_job(job)


def add_job(data):
    return execute(
        """INSERT INTO jobs (company_id, job_title, job_type, salary_min, salary_max,
                             job_url, date_posted, requirements)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
        (data["company_id"], data["job_title"], data["job_type"], data["salary_min"],
         data["salary_max"], data["job_url"], data["date_posted"],
         json.dumps(data["requirements"])),
    )


def update_job(job_id, data):
    execute(
        """UPDATE jobs SET company_id=%s, job_title=%s, job_type=%s, salary_min=%s,
                  salary_max=%s, job_url=%s, date_posted=%s, requirements=%s
           WHERE job_id=%s""",
        (data["company_id"], data["job_title"], data["job_type"], data["salary_min"],
         data["salary_max"], data["job_url"], data["date_posted"],
         json.dumps(data["requirements"]), job_id),
    )


def delete_job(job_id):
    execute("DELETE FROM jobs WHERE job_id = %s", (job_id,))


def get_job_choices():
    return query_all(
        """SELECT j.job_id, j.job_title, c.company_name FROM jobs j
           JOIN companies c ON j.company_id = c.company_id
           ORDER BY c.company_name, j.job_title"""
    )


# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
def _decorate_application(app_row):
    if app_row:
        data = parse_json(app_row.get("interview_data"), {})
        if not isinstance(data, dict):
            data = {}
        app_row["interviews"] = data.get("interviews", []) or []
        app_row["cover_letter_sent"] = bool(app_row.get("cover_letter_sent"))
    return app_row


APPLICATION_SELECT = """
    SELECT a.*, j.job_title, j.job_type, j.company_id, c.company_name
    FROM applications a
    JOIN jobs j      ON a.job_id = j.job_id
    JOIN companies c ON j.company_id = c.company_id
"""


def get_applications(search="", status="", job_id=None):
    sql = APPLICATION_SELECT + " WHERE 1=1"
    params = []
    if search:
        sql += " AND (j.job_title LIKE %s OR c.company_name LIKE %s OR a.resume_version LIKE %s)"
        params += [_like(search)] * 3
    if status:
        sql += " AND a.status = %s"
        params.append(status)
    if job_id:
        sql += " AND a.job_id = %s"
        params.append(job_id)
    sql += " ORDER BY a.application_date DESC, a.application_id DESC"
    return [_decorate_application(a) for a in query_all(sql, tuple(params))]


def get_applications_for_company(company_id):
    sql = APPLICATION_SELECT + " WHERE j.company_id = %s ORDER BY a.application_date DESC"
    return [_decorate_application(a) for a in query_all(sql, (company_id,))]


def get_application(application_id):
    return _decorate_application(
        query_one(APPLICATION_SELECT + " WHERE a.application_id = %s", (application_id,))
    )


def add_application(data):
    return execute(
        """INSERT INTO applications (job_id, application_date, status, resume_version,
                                     cover_letter_sent, interview_data)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (data["job_id"], data["application_date"], data["status"], data["resume_version"],
         data["cover_letter_sent"], json.dumps({"interviews": data["interviews"]})),
    )


def update_application(application_id, data):
    execute(
        """UPDATE applications SET job_id=%s, application_date=%s, status=%s,
                  resume_version=%s, cover_letter_sent=%s, interview_data=%s
           WHERE application_id=%s""",
        (data["job_id"], data["application_date"], data["status"], data["resume_version"],
         data["cover_letter_sent"], json.dumps({"interviews": data["interviews"]}),
         application_id),
    )


def delete_application(application_id):
    execute("DELETE FROM applications WHERE application_id = %s", (application_id,))


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------
def get_contacts(search="", company_id=None):
    sql = """
        SELECT ct.*, c.company_name FROM contacts ct
        JOIN companies c ON ct.company_id = c.company_id
        WHERE 1=1
    """
    params = []
    if search:
        sql += " AND (ct.contact_name LIKE %s OR ct.title LIKE %s OR c.company_name LIKE %s OR ct.email LIKE %s)"
        params += [_like(search)] * 4
    if company_id:
        sql += " AND ct.company_id = %s"
        params.append(company_id)
    sql += " ORDER BY ct.contact_name"
    return query_all(sql, tuple(params))


def get_contact(contact_id):
    return query_one(
        """SELECT ct.*, c.company_name FROM contacts ct
           JOIN companies c ON ct.company_id = c.company_id
           WHERE ct.contact_id = %s""",
        (contact_id,),
    )


def add_contact(data):
    return execute(
        """INSERT INTO contacts (company_id, contact_name, title, email, phone, linkedin_url, notes)
           VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (data["company_id"], data["contact_name"], data["title"], data["email"],
         data["phone"], data["linkedin_url"], data["notes"]),
    )


def update_contact(contact_id, data):
    execute(
        """UPDATE contacts SET company_id=%s, contact_name=%s, title=%s, email=%s,
                  phone=%s, linkedin_url=%s, notes=%s
           WHERE contact_id=%s""",
        (data["company_id"], data["contact_name"], data["title"], data["email"],
         data["phone"], data["linkedin_url"], data["notes"], contact_id),
    )


def delete_contact(contact_id):
    execute("DELETE FROM contacts WHERE contact_id = %s", (contact_id,))


# ---------------------------------------------------------------------------
# Dashboard statistics
# ---------------------------------------------------------------------------
def get_dashboard_stats():
    counts = query_one(
        """SELECT
             (SELECT COUNT(*) FROM companies)    AS companies,
             (SELECT COUNT(*) FROM jobs)         AS jobs,
             (SELECT COUNT(*) FROM applications) AS applications,
             (SELECT COUNT(*) FROM contacts)     AS contacts,
             (SELECT ROUND(AVG((salary_min + salary_max) / 2))
                FROM jobs WHERE salary_min IS NOT NULL AND salary_max IS NOT NULL) AS avg_salary"""
    )
    status_rows = query_all("SELECT status, COUNT(*) AS total FROM applications GROUP BY status")
    by_status = {s: 0 for s in APPLICATION_STATUSES}
    for row in status_rows:
        by_status[row["status"]] = row["total"]

    total = counts["applications"] or 0
    responded = total - by_status["Applied"]
    counts["response_rate"] = round(responded * 100 / total) if total else 0
    counts["active"] = by_status["Applied"] + by_status["Screening"] + by_status["Interview"]
    counts["offers"] = by_status["Offer"]
    return counts, by_status


def get_recent_applications(limit=5):
    sql = APPLICATION_SELECT + " ORDER BY a.application_date DESC, a.application_id DESC LIMIT %s"
    return [_decorate_application(a) for a in query_all(sql, (limit,))]


def get_jobs_by_type():
    return query_all("SELECT job_type, COUNT(*) AS total FROM jobs GROUP BY job_type ORDER BY total DESC")
