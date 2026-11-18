# AI Usage Documentation

## Summary

I used **Claude (Claude Code, by Anthropic)** as my main development tool for this project.
I gave it the course project description and specification, and it generated the first working
version of the application: database schema, Flask routes, data-access functions, HTML templates,
CSS, the Job Match algorithm, unit tests, and draft documentation.

My role: reviewing and understanding the generated code, setting up and running the app locally,
testing it against MySQL, making my own changes (listed below), recording the demo, and writing
this reflection.

## Tools Used

| Tool | Used for |
|------|----------|
| Claude (Claude Code) | Generating the initial application and documentation, end-to-end testing, fixing UI issues |
| *(add any others, e.g. ChatGPT to explain an error)* | |

## Key Prompts

1. **Initial build:** the full project description and spec, with the request
   *"Please help me complete this course project for a job application tracker using the information I have provided here."*
2. **GitHub setup:** asked Claude to push the project to my existing course repository, keeping my earlier commits.
3. **Documentation:** asked Claude to tighten the wording of this file.
4. *(add prompts you use from here on, e.g. "Explain how `rank_jobs` sorts the results" or "Help me add a deadline field to jobs")*

## What AI Generated

- `schema.sql`: 4 tables, foreign keys with `ON DELETE CASCADE`, ENUMs, JSON columns
  (`jobs.requirements`, `applications.interview_data`), CHECK constraints, sample data
- `database.py`: connection helper and parameterized CRUD queries for every table
- `app.py`: routes for every page, a `FormValidator` class for server-side validation, and the Job Match
  algorithm (`match % = required skills the user has / total required skills × 100`, with an alias table so "JS" matches "JavaScript")
- All templates in `templates/` and `static/style.css`
- `test_job_match.py`, plus first drafts of `README.md` and this file

## What Worked Well

- Giving the AI the complete spec (exact columns, required pages, the Job Match example) produced code
  that matched the assignment instead of a generic app.
- Repetitive CRUD code for four tables came out consistent and quickly.
- Keeping all SQL in `database.py` with `%s` placeholders made the code easier to follow and safe from SQL injection.
- The AI tested its own work: it loaded the schema into a local MySQL-compatible server, exercised every
  route (including invalid input and cascade deletes), and took screenshots of the pages.

## What Was Changed After the First Version

Fixed during AI testing:
- Required-field asterisks wrapped onto their own line (a CSS flexbox issue), so the label markup was fixed.
- A placeholder in empty interview rows ("Phone Screen") looked like saved data, so it was changed to "e.g. Phone Screen".

My own changes:
- *(list each change you make yourself: what you changed and why)*

## Lessons Learned

*(Write this section yourself. Some questions to answer: What did you learn about Flask, MySQL, or JSON
columns from reading the generated code? What did you have to look up or ask about to understand it?
Where did the AI's output need human judgment? What would you do differently next time?)*
