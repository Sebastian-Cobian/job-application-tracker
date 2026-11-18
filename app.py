"""
app.py - Flask application for the Job Application Tracker.

Run:  python app.py   (then open http://127.0.0.1:5000)
"""

import os
import re
from datetime import date, datetime

from flask import Flask, abort, flash, redirect, render_template, request, url_for

import database as db

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-change-me")


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
PHONE_RE = re.compile(r"^[0-9+().\-\s]{7,20}$")
URL_RE = re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.IGNORECASE)


class FormValidator:
    """Collects cleaned values and error messages for one submitted form."""

    def __init__(self, form):
        self.form = form
        self.errors = []
        self.data = {}

    def text(self, field, label, max_len, required=False):
        value = (self.form.get(field) or "").strip()
        if required and not value:
            self.errors.append(f"{label} is required.")
        elif len(value) > max_len:
            self.errors.append(f"{label} must be {max_len} characters or fewer.")
        self.data[field] = value or None
        return value

    def url(self, field, label, max_len):
        value = self.text(field, label, max_len)
        if value and not URL_RE.match(value):
            self.errors.append(f"{label} must be a valid URL starting with http:// or https://.")
        return value

    def email(self, field, label, max_len):
        value = self.text(field, label, max_len)
        if value and not EMAIL_RE.match(value):
            self.errors.append(f"{label} must be a valid email address.")
        return value

    def phone(self, field, label, max_len):
        value = self.text(field, label, max_len)
        if value and not PHONE_RE.match(value):
            self.errors.append(f"{label} may only contain digits, spaces, and + ( ) - . characters (7-20 long).")
        return value

    def integer(self, field, label, minimum=0, maximum=10_000_000, required=False):
        raw = (self.form.get(field) or "").strip().replace(",", "").replace("$", "")
        if not raw:
            if required:
                self.errors.append(f"{label} is required.")
            self.data[field] = None
            return None
        try:
            value = int(raw)
        except ValueError:
            self.errors.append(f"{label} must be a whole number.")
            self.data[field] = None
            return None
        if value < minimum or value > maximum:
            self.errors.append(f"{label} must be between {minimum:,} and {maximum:,}.")
        self.data[field] = value
        return value

    def date(self, field, label, required=False, allow_future=True):
        raw = (self.form.get(field) or "").strip()
        if not raw:
            if required:
                self.errors.append(f"{label} is required.")
            self.data[field] = None
            return None
        try:
            value = datetime.strptime(raw, "%Y-%m-%d").date()
        except ValueError:
            self.errors.append(f"{label} must be a valid date (YYYY-MM-DD).")
            self.data[field] = None
            return None
        if not allow_future and value > date.today():
            self.errors.append(f"{label} cannot be in the future.")
        self.data[field] = value
        return value

    def choice(self, field, label, choices, required=True):
        value = (self.form.get(field) or "").strip()
        if value not in choices:
            if required or value:
                self.errors.append(f"Please choose a valid {label}.")
            value = None
        self.data[field] = value
        return value

    def foreign_key(self, field, label, valid_ids):
        raw = (self.form.get(field) or "").strip()
        try:
            value = int(raw)
        except ValueError:
            value = None
        if value not in valid_ids:
            self.errors.append(f"Please select a {label}.")
            value = None
        self.data[field] = value
        return value

    @property
    def ok(self):
        return not self.errors

    def flash_errors(self):
        for message in self.errors:
            flash(message, "error")


def parse_skills(text):
    """'Python, SQL,  flask ,python' -> ['Python', 'SQL', 'flask'] (deduplicated, order kept)."""
    seen, skills = set(), []
    for part in re.split(r"[,;\n]", text or ""):
        skill = part.strip()
        if skill and skill.lower() not in seen:
            seen.add(skill.lower())
            skills.append(skill)
    return skills


def get_search_args():
    return (request.args.get("q") or "").strip()


# ---------------------------------------------------------------------------
# Template helpers
# ---------------------------------------------------------------------------
@app.template_filter("money")
def money_filter(value):
    return f"${value:,.0f}" if value is not None else "—"


@app.template_filter("fmtdate")
def fmtdate_filter(value):
    if not value:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%Y-%m-%d").date()
        except ValueError:
            return value
    return value.strftime("%b %d, %Y")


@app.context_processor
def inject_globals():
    return {
        "JOB_TYPES": db.JOB_TYPES,
        "APPLICATION_STATUSES": db.APPLICATION_STATUSES,
        "today": date.today().isoformat(),
    }


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
def upcoming_interviews(applications, limit=5):
    """Pull future interviews out of each application's interview_data JSON."""
    today = date.today().isoformat()
    upcoming = []
    for application in applications:
        for interview in application["interviews"]:
            if interview.get("date") and interview["date"] >= today:
                upcoming.append({**interview, "application": application})
    upcoming.sort(key=lambda item: item["date"])
    return upcoming[:limit]


@app.route("/")
def dashboard():
    stats, by_status = db.get_dashboard_stats()
    max_status = max(by_status.values()) if by_status else 0
    return render_template(
        "dashboard.html",
        stats=stats,
        by_status=by_status,
        max_status=max_status or 1,
        recent=db.get_recent_applications(),
        upcoming=upcoming_interviews(db.get_applications()),
        jobs_by_type=db.get_jobs_by_type(),
    )


# ---------------------------------------------------------------------------
# Companies CRUD
# ---------------------------------------------------------------------------
def validate_company(form, company_id=None):
    v = FormValidator(form)
    name = v.text("company_name", "Company name", 100, required=True)
    v.text("industry", "Industry", 50)
    v.url("website", "Website", 200)
    v.text("city", "City", 50)
    v.text("state", "State", 50)
    v.text("notes", "Notes", 5000)
    if name and db.company_name_exists(name, exclude_id=company_id):
        v.errors.append(f"A company named '{name}' already exists.")
    return v


@app.route("/companies")
def companies():
    search = get_search_args()
    return render_template("companies.html", companies=db.get_companies(search), search=search)


@app.route("/companies/new", methods=["GET", "POST"])
def company_new():
    if request.method == "POST":
        v = validate_company(request.form)
        if v.ok:
            new_id = db.add_company(v.data)
            flash(f"Company '{v.data['company_name']}' added.", "success")
            return redirect(url_for("company_detail", company_id=new_id))
        v.flash_errors()
        return render_template("company_form.html", company=request.form, mode="new")
    return render_template("company_form.html", company={}, mode="new")


@app.route("/companies/<int:company_id>")
def company_detail(company_id):
    company = db.get_company(company_id) or abort(404)
    return render_template(
        "company_detail.html",
        company=company,
        jobs=db.get_jobs(company_id=company_id),
        contacts=db.get_contacts(company_id=company_id),
        applications=db.get_applications_for_company(company_id),
        dependents=db.get_company_dependents(company_id),
    )


@app.route("/companies/<int:company_id>/edit", methods=["GET", "POST"])
def company_edit(company_id):
    company = db.get_company(company_id) or abort(404)
    if request.method == "POST":
        v = validate_company(request.form, company_id)
        if v.ok:
            db.update_company(company_id, v.data)
            flash("Company updated.", "success")
            return redirect(url_for("company_detail", company_id=company_id))
        v.flash_errors()
        return render_template("company_form.html", company={**request.form, "company_id": company_id}, mode="edit")
    return render_template("company_form.html", company=company, mode="edit")


@app.route("/companies/<int:company_id>/delete", methods=["POST"])
def company_delete(company_id):
    company = db.get_company(company_id) or abort(404)
    db.delete_company(company_id)
    flash(f"Company '{company['company_name']}' and its related records were deleted.", "success")
    return redirect(url_for("companies"))


# ---------------------------------------------------------------------------
# Jobs CRUD
# ---------------------------------------------------------------------------
def validate_job(form):
    v = FormValidator(form)
    v.foreign_key("company_id", "company", {c["company_id"] for c in db.get_company_choices()})
    v.text("job_title", "Job title", 100, required=True)
    v.choice("job_type", "job type", db.JOB_TYPES)
    salary_min = v.integer("salary_min", "Minimum salary")
    salary_max = v.integer("salary_max", "Maximum salary")
    if salary_min is not None and salary_max is not None and salary_min > salary_max:
        v.errors.append("Minimum salary cannot be greater than maximum salary.")
    v.url("job_url", "Job URL", 300)
    v.date("date_posted", "Date posted")

    # Build the requirements JSON object
    skills = parse_skills(form.get("skills"))
    if any(len(s) > 50 for s in skills):
        v.errors.append("Each skill must be 50 characters or fewer.")
    requirements = {"skills": skills}
    experience = v.integer("experience_years", "Years of experience", 0, 50)
    if experience is not None:
        requirements["experience_years"] = experience
    education = v.text("education", "Education", 100)
    if education:
        requirements["education"] = education
    v.data["requirements"] = requirements
    return v


def job_form_values(job):
    """Flatten a job row (with JSON requirements) into form field values."""
    req = job.get("requirements") or {}
    return {
        **job,
        "skills": ", ".join(req.get("skills", [])),
        "experience_years": req.get("experience_years", ""),
        "education": req.get("education", ""),
    }


@app.route("/jobs")
def jobs():
    search = get_search_args()
    job_type = request.args.get("type", "")
    return render_template(
        "jobs.html", jobs=db.get_jobs(search, job_type), search=search, job_type=job_type
    )


@app.route("/jobs/new", methods=["GET", "POST"])
def job_new():
    companies = db.get_company_choices()
    if not companies:
        flash("Add a company before adding a job.", "error")
        return redirect(url_for("company_new"))
    if request.method == "POST":
        v = validate_job(request.form)
        if v.ok:
            new_id = db.add_job(v.data)
            flash(f"Job '{v.data['job_title']}' added.", "success")
            return redirect(url_for("job_detail", job_id=new_id))
        v.flash_errors()
        return render_template("job_form.html", job=request.form, companies=companies, mode="new")
    preset = {"company_id": request.args.get("company_id", ""), "job_type": "Full-time"}
    return render_template("job_form.html", job=preset, companies=companies, mode="new")


@app.route("/jobs/<int:job_id>")
def job_detail(job_id):
    job = db.get_job(job_id) or abort(404)
    return render_template("job_detail.html", job=job, applications=db.get_applications(job_id=job_id))


@app.route("/jobs/<int:job_id>/edit", methods=["GET", "POST"])
def job_edit(job_id):
    job = db.get_job(job_id) or abort(404)
    companies = db.get_company_choices()
    if request.method == "POST":
        v = validate_job(request.form)
        if v.ok:
            db.update_job(job_id, v.data)
            flash("Job updated.", "success")
            return redirect(url_for("job_detail", job_id=job_id))
        v.flash_errors()
        return render_template("job_form.html", job={**request.form, "job_id": job_id}, companies=companies, mode="edit")
    return render_template("job_form.html", job=job_form_values(job), companies=companies, mode="edit")


@app.route("/jobs/<int:job_id>/delete", methods=["POST"])
def job_delete(job_id):
    job = db.get_job(job_id) or abort(404)
    db.delete_job(job_id)
    flash(f"Job '{job['job_title']}' and its applications were deleted.", "success")
    return redirect(url_for("jobs"))


# ---------------------------------------------------------------------------
# Applications CRUD
# ---------------------------------------------------------------------------
def collect_interviews(form, v):
    """Read the repeated interview rows from the form into a list of dicts."""
    rows = zip(
        form.getlist("interview_date"),
        form.getlist("interview_type"),
        form.getlist("interviewer"),
        form.getlist("interview_notes"),
    )
    interviews = []
    for number, (when, kind, who, notes) in enumerate(rows, start=1):
        when, kind, who, notes = (x.strip() for x in (when, kind, who, notes))
        if not any((when, kind, who, notes)):
            continue  # blank row - skip it
        if not when:
            v.errors.append(f"Interview #{number}: a date is required.")
        else:
            try:
                datetime.strptime(when, "%Y-%m-%d")
            except ValueError:
                v.errors.append(f"Interview #{number}: date must be YYYY-MM-DD.")
        if len(kind) > 50 or len(who) > 100 or len(notes) > 1000:
            v.errors.append(f"Interview #{number}: one of the fields is too long.")
        interviews.append({"date": when, "type": kind, "interviewer": who, "notes": notes})
    interviews.sort(key=lambda i: i["date"])
    return interviews


def validate_application(form):
    v = FormValidator(form)
    v.foreign_key("job_id", "job", {j["job_id"] for j in db.get_job_choices()})
    v.date("application_date", "Application date", required=True, allow_future=False)
    v.choice("status", "status", db.APPLICATION_STATUSES)
    v.text("resume_version", "Resume version", 50)
    v.data["cover_letter_sent"] = form.get("cover_letter_sent") == "on"
    v.data["interviews"] = collect_interviews(form, v)
    return v


def application_form_values(form, application_id=None):
    """Rebuild template values from a submitted form so the user doesn't lose input."""
    values = {**form, "cover_letter_sent": form.get("cover_letter_sent") == "on"}
    values["interviews"] = [
        {"date": d, "type": t, "interviewer": i, "notes": n}
        for d, t, i, n in zip(
            form.getlist("interview_date"), form.getlist("interview_type"),
            form.getlist("interviewer"), form.getlist("interview_notes"),
        )
        if any((d, t, i, n))
    ]
    if application_id:
        values["application_id"] = application_id
    return values


@app.route("/applications")
def applications():
    search = get_search_args()
    status = request.args.get("status", "")
    return render_template(
        "applications.html",
        applications=db.get_applications(search, status),
        search=search,
        status=status,
    )


@app.route("/applications/new", methods=["GET", "POST"])
def application_new():
    jobs = db.get_job_choices()
    if not jobs:
        flash("Add a job before adding an application.", "error")
        return redirect(url_for("job_new"))
    if request.method == "POST":
        v = validate_application(request.form)
        if v.ok:
            new_id = db.add_application(v.data)
            flash("Application added.", "success")
            return redirect(url_for("application_detail", application_id=new_id))
        v.flash_errors()
        return render_template("application_form.html", application=application_form_values(request.form), jobs=jobs, mode="new")
    preset = {
        "job_id": request.args.get("job_id", ""),
        "application_date": date.today().isoformat(),
        "status": "Applied",
        "interviews": [],
    }
    return render_template("application_form.html", application=preset, jobs=jobs, mode="new")


@app.route("/applications/<int:application_id>")
def application_detail(application_id):
    application = db.get_application(application_id) or abort(404)
    return render_template(
        "application_detail.html",
        application=application,
        job=db.get_job(application["job_id"]),
        contacts=db.get_contacts(company_id=application["company_id"]),
    )


@app.route("/applications/<int:application_id>/edit", methods=["GET", "POST"])
def application_edit(application_id):
    application = db.get_application(application_id) or abort(404)
    jobs = db.get_job_choices()
    if request.method == "POST":
        v = validate_application(request.form)
        if v.ok:
            db.update_application(application_id, v.data)
            flash("Application updated.", "success")
            return redirect(url_for("application_detail", application_id=application_id))
        v.flash_errors()
        return render_template(
            "application_form.html",
            application=application_form_values(request.form, application_id),
            jobs=jobs, mode="edit",
        )
    return render_template("application_form.html", application=application, jobs=jobs, mode="edit")


@app.route("/applications/<int:application_id>/delete", methods=["POST"])
def application_delete(application_id):
    db.get_application(application_id) or abort(404)
    db.delete_application(application_id)
    flash("Application deleted.", "success")
    return redirect(url_for("applications"))


# ---------------------------------------------------------------------------
# Contacts CRUD
# ---------------------------------------------------------------------------
def validate_contact(form):
    v = FormValidator(form)
    v.foreign_key("company_id", "company", {c["company_id"] for c in db.get_company_choices()})
    v.text("contact_name", "Contact name", 100, required=True)
    v.text("title", "Title", 100)
    v.email("email", "Email", 100)
    v.phone("phone", "Phone", 20)
    v.url("linkedin_url", "LinkedIn URL", 200)
    v.text("notes", "Notes", 5000)
    return v


@app.route("/contacts")
def contacts():
    search = get_search_args()
    return render_template("contacts.html", contacts=db.get_contacts(search), search=search)


@app.route("/contacts/new", methods=["GET", "POST"])
def contact_new():
    companies = db.get_company_choices()
    if not companies:
        flash("Add a company before adding a contact.", "error")
        return redirect(url_for("company_new"))
    if request.method == "POST":
        v = validate_contact(request.form)
        if v.ok:
            new_id = db.add_contact(v.data)
            flash(f"Contact '{v.data['contact_name']}' added.", "success")
            return redirect(url_for("contact_detail", contact_id=new_id))
        v.flash_errors()
        return render_template("contact_form.html", contact=request.form, companies=companies, mode="new")
    preset = {"company_id": request.args.get("company_id", "")}
    return render_template("contact_form.html", contact=preset, companies=companies, mode="new")


@app.route("/contacts/<int:contact_id>")
def contact_detail(contact_id):
    contact = db.get_contact(contact_id) or abort(404)
    return render_template("contact_detail.html", contact=contact)


@app.route("/contacts/<int:contact_id>/edit", methods=["GET", "POST"])
def contact_edit(contact_id):
    contact = db.get_contact(contact_id) or abort(404)
    companies = db.get_company_choices()
    if request.method == "POST":
        v = validate_contact(request.form)
        if v.ok:
            db.update_contact(contact_id, v.data)
            flash("Contact updated.", "success")
            return redirect(url_for("contact_detail", contact_id=contact_id))
        v.flash_errors()
        return render_template("contact_form.html", contact={**request.form, "contact_id": contact_id}, companies=companies, mode="edit")
    return render_template("contact_form.html", contact=contact, companies=companies, mode="edit")


@app.route("/contacts/<int:contact_id>/delete", methods=["POST"])
def contact_delete(contact_id):
    contact = db.get_contact(contact_id) or abort(404)
    db.delete_contact(contact_id)
    flash(f"Contact '{contact['contact_name']}' deleted.", "success")
    return redirect(url_for("contacts"))


# ---------------------------------------------------------------------------
# Job Match feature
# ---------------------------------------------------------------------------
# Common abbreviations / spellings mapped to one canonical name so that
# "JS" matches "JavaScript" and "Postgres" matches "PostgreSQL".
SKILL_ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "python3": "python",
    "postgres": "postgresql",
    "mysql database": "mysql",
    "html5": "html",
    "css3": "css",
    "reactjs": "react",
    "react.js": "react",
    "node": "node.js",
    "nodejs": "node.js",
    "amazon web services": "aws",
    "k8s": "kubernetes",
    "ml": "machine learning",
    "c sharp": "c#",
    "golang": "go",
}


def normalize_skill(skill):
    key = re.sub(r"\s+", " ", skill.strip().lower())
    return SKILL_ALIASES.get(key, key)


def calculate_match(user_skills, job_skills):
    """
    Compare a user's skills to one job's required skills.

    Match % = (required skills the user has) / (total required skills) * 100
    Returns a dict with the percentage, counts, and matched/missing lists
    (missing/matched use the job's original spelling for display).
    """
    user_set = {normalize_skill(s) for s in user_skills}
    matched, missing = [], []
    for skill in job_skills:
        (matched if normalize_skill(skill) in user_set else missing).append(skill)
    total = len(job_skills)
    percent = round(len(matched) * 100 / total) if total else 0
    return {
        "percent": percent,
        "matched_count": len(matched),
        "total": total,
        "matched": matched,
        "missing": missing,
    }


def rank_jobs(user_skills, jobs, min_percent=0):
    """Score every job that lists skills and sort best match first."""
    results = []
    for job in jobs:
        if not job["skills"]:
            continue
        match = calculate_match(user_skills, job["skills"])
        if match["percent"] >= min_percent:
            results.append({"job": job, **match})
    results.sort(key=lambda r: (-r["percent"], -r["matched_count"], r["job"]["job_title"].lower()))
    return results


@app.route("/job-match")
def job_match():
    skills_text = (request.args.get("skills") or "").strip()
    try:
        min_percent = max(0, min(100, int(request.args.get("min", 0))))
    except ValueError:
        min_percent = 0
    user_skills = parse_skills(skills_text)
    results = rank_jobs(user_skills, db.get_jobs(), min_percent) if user_skills else None

    # Suggest the most-requested skills across all jobs to help the user
    counts = {}
    for job in db.get_jobs():
        for skill in job["skills"]:
            counts[skill] = counts.get(skill, 0) + 1
    popular = sorted(counts, key=lambda s: (-counts[s], s.lower()))[:12]

    return render_template(
        "job_match.html",
        skills_text=skills_text,
        user_skills=user_skills,
        results=results,
        min_percent=min_percent,
        popular=popular,
    )


# ---------------------------------------------------------------------------
# Error pages
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", code=404, message="That page or record was not found."), 404


@app.errorhandler(db.Error)
def database_error(error):
    app.logger.error("Database error: %s", error)
    return render_template(
        "error.html",
        code=500,
        message="A database error occurred. Check that MySQL is running and your .env settings are correct.",
        detail=str(error),
    ), 500


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "1") == "1")
