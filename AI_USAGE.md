# AI Usage Documentation

> This file documents how generative AI was used to build the Job Application Tracker,
> as required by the project specification.
>
> ✏️ **Before submitting:** read through every section, make sure it matches what *you* actually did,
> and fill in the "In my own words" parts. The grader wants to see your own reflection.

## Tools Used

| Tool | What I used it for |
|------|--------------------|
| **Claude (Claude Code, Anthropic)** | Generating the initial project: schema, Flask routes, database functions, templates, CSS, the Job Match algorithm, unit tests and documentation. Also used to test the app end-to-end and fix UI issues it found. |
| *(add any others you used — e.g. ChatGPT for explaining errors, Copilot in VS Code)* | |

## Key Prompts

1. **Project kickoff** — I gave Claude the full course project description and Project Specification document and asked:
   > "Please help me complete this course project for a job application tracker using the information I have provided here."

   Claude read the spec and built the project in steps: schema → database layer → Flask routes → templates → CSS → Job Match → docs.

2. **Database schema** (part of the build):
   > "Create schema.sql with the four tables from the spec (companies, jobs, applications, contacts), proper foreign keys, the ENUM columns, and JSON columns for job requirements and interview data. Include realistic sample data."

3. **CRUD routes**:
   > "Write Flask routes for list / detail / add / edit / delete for each table. Put all SQL in database.py and use parameterized queries."

4. **Validation**:
   > "Add server-side validation to every form: required fields, max lengths, URL/email/phone formats, salary min ≤ max, and application date not in the future. Show errors without losing what the user typed."

5. **Job Match algorithm**:
   > "Create a function to calculate the skill match percentage between the user's skills and a job's required skills, rank the jobs from best to worst match, and list the missing skills. It should match the spec example: Python, SQL, Flask → Software Developer 100% (3/3), Data Analyst 67% (2/3), Missing: Tableau."

6. **Storing interviews as JSON without JavaScript**:
   > "How can a plain HTML form let me enter several interviews for one application and save them into the interview_data JSON column?"

   Answer used: repeated inputs with the same `name` (`interview_date`, `interview_type`, …) read with `request.form.getlist()` and zipped into a list of dicts.

## What Worked Well

- **Boilerplate came out fast.** The four sets of CRUD routes and templates follow the same pattern, and AI produced them consistently in minutes.
- **The `FormValidator` helper class** was a good idea from the AI — instead of repeating `if not request.form['x']:` everywhere, each form is validated in a few readable lines.
- **Keeping SQL in `database.py`** made `app.py` much easier to read, and every query uses `%s` placeholders (no SQL injection).
- **The Job Match logic** is short and easy to explain: `matched / total × 100`, sorted by percent. The AI also suggested an alias table (JS → JavaScript, Postgres → PostgreSQL) so matching is more forgiving.
- **Testing.** Claude installed a local MySQL-compatible server (MariaDB), loaded `schema.sql`, and ran a script that exercised every page and every create/update/delete route — including the invalid-input cases and cascade deletes — before I looked at it. It also wrote `test_job_match.py`, which checks the exact spec example.

## What I Modified / What Had to Be Fixed

These are changes made to the AI's first version after reviewing and testing it:

- **Asterisks on required fields wrapped onto their own line.** The form labels use `display: flex; flex-direction: column`, which turned the red `*` into a separate row. Fixed by wrapping the label text and asterisk in a `<span>`. (Found by taking screenshots of the pages.)
- **Misleading placeholder.** Blank interview rows showed the placeholder "Phone Screen", which looked like real saved data. Changed it to "e.g. Phone Screen".
- **Removed `novalidate` from the company form** so the browser's built-in validation is used along with the server-side validation, consistent with the other forms.
- **Company names made unique** (`UNIQUE` constraint + friendly error message) so duplicates like two "TechCorp" rows can't be created.
- **Delete confirmations made specific** — instead of a generic "Are you sure?", the message says how many jobs / applications / contacts will also be deleted, since the foreign keys cascade.
- **Database password moved out of the code** into a `.env` file (git-ignored) instead of the hard-coded `password='YOUR_PASSWORD'` from the spec's starter code, so the instructor can use their own credentials.
- *(Add anything you changed yourself — e.g. sample data with real companies you're applying to, colors, extra fields, wording.)*

## Lessons Learned

- **Always run AI code, don't just read it.** The generated code looked right, but the layout bug only showed up in a screenshot.
- **Give the AI the full context.** Sharing the whole specification (table columns, required pages, the Job Match example) produced code that matched the assignment on the first try, instead of a generic tracker.
- **Ask for tests with concrete examples.** Turning the spec's Job Match example into a unit test proved the algorithm gives exactly 100% and 67%.
- **AI is great at boilerplate; design decisions still need a human.** Choices like "should deleting a company delete its jobs?" (cascade vs. block) and how to store interviews in JSON are things I had to understand and agree with.
- **Understand before submitting.** I went through `app.py` and `database.py` so I can explain every route and query.

### In my own words

*(Write 3–5 sentences here: what surprised you, what you learned about Flask/MySQL from reading the AI's code, and what you'd do differently next time.)*
