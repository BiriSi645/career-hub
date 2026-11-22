# Project Overview

Career Hub is a job application tracker for the Database System Design course. Visitors can browse jobs. Candidates can build a profile, upload a CV, and track their applications. Recruiters manage postings and applications for their company. Administrators manage users, companies, jobs, categories, and skills.

The project uses Python and Flask for the application, Jinja and Bootstrap for the pages, and PostgreSQL for the database. Psycopg 3 sends the application's handwritten SQL queries to PostgreSQL. Flask-Login manages sign-in, and Docker Compose starts the application and database together. See [SQL Query Demonstrations](SQL_QUERIES.md) for the query locations.

In the demo, a candidate applies for a job. The application and its first status record are saved in one transaction. When a recruiter changes the status, the new status, history record, and notification are saved together.

Recruiters can publish roles for verified companies or save drafts, attach required and preferred skills, and schedule or manage interviews. Candidates can manage notifications. The homepage shows counts from the available postings in PostgreSQL.

## MVC structure

| Layer | Directory | Responsibility |
|---|---|---|
| Model | `app/models/` | Reads and writes PostgreSQL data with SQL and Psycopg 3. |
| View | `app/templates/`, `public/static/` | Shows data in Jinja templates and styles the HTML pages. |
| Controller | `app/routes/` | Reads requests, checks permissions, calls the model or service, and renders a page or redirects. |

`app/services/applications.py` coordinates application business rules and transactions. For example, the candidate controller calls the application service, which checks the deadline and calls `app/models/applications.py` to insert both the application and its first history record. The controller then redirects to the job detail page.

