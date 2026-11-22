# SQL Query Demonstrations

`sql/queries.sql` contains 18 read-only examples. They cover `SELECT`, inner and left joins, `DISTINCT`, `ILIKE`, `IN`, `EXISTS` and `NOT EXISTS`, grouping, `HAVING`, ordering, `COUNT`, `AVG`, `SUM`, a scalar subquery, and window ranking. Example 8 returns IDs and names of users without applications.

From the project directory in PowerShell, run the examples against the Docker database with sample values for `:user_id` and `:term`.

```powershell
Get-Content -Raw .\sql\queries.sql |
  docker compose exec -T db psql -U postgres -d career_hub -v ON_ERROR_STOP=1 -v user_id=1 -v "term='Python'"
```

`sql/transactions.sql` illustrates writes for submitting an application and moving it from submitted to reviewing. Run each example separately in a disposable database. Example A uses `:job_id`, `:user_id`, `:resume_id`, and `:cover_letter` and returns the inserted application ID. Example B uses that ID as `:application_id` and a company recruiter as `:recruiter_id`. If a guard matches no row, its transaction writes nothing. If a statement fails in an interactive transaction, run `ROLLBACK` before retrying.

Python queries bind values separately with Psycopg 3 placeholders such as `%(user_id)s` or `%s`.

## SQL used by the website

- `app/models/jobs.py` uses `SELECT`, `JOIN`, `WHERE`, `ILIKE`, and `ORDER BY` to show and filter job postings.
- `app/models/applications.py` uses `INSERT ... RETURNING` to create an application and get its ID for the first history record. `app/services/applications.py` checks the business rules and runs the status update, history and notification as a single transaction.
- `app/models/candidates.py` contains the candidate dashboard, profile, CV and bookmark queries.
- `app/models/users.py` contains account, sign-in and role queries.
- `app/models/companies.py` contains company, company membership, posting, applicant and interview queries.
- `app/models/administration.py` contains administration, catalog and database browser queries.
- `app/seed.py` contains the SQL that loads the demo data.

Psycopg 3 executes the handwritten SQL in the website and demo setup. The transaction helper in `app/database.py` calls `commit()` when all writes succeed and `rollback()` if one fails.

