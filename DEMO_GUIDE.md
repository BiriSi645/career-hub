# Instructor Demonstration Guide

The seed includes three examples of current employment linked to hired applications. In the admin **Employees** view, their titles and companies match the postings. The Student Technology Club entries represent past experience.

1. Start the app and PostgreSQL using the Docker commands in [README.md](README.md).
2. Open the landing page and search for “Python”; explain the multi-table company/job query.
3. Sign in as `student2@careerhub.local` / `Demo123!`. Open **Junior Python Developer** at NovaTech Labs. Check its required skills, save it, and submit an application with the demo CV. This pair has no existing application in a fresh seed.
4. Submit the same application again to demonstrate the `UNIQUE(job_id, applicant_id)` rule and service validation.
5. Sign out and sign in as `recruiter1@careerhub.local`. Open the applicants for that posting, move the new application from Submitted to Reviewing, and schedule a future onsite interview using Istanbul time.
6. Return as the student to see the application history and interview. Open **Notifications**, mark an alert as read, and check the unread count on the dashboard.
7. Try opening another company's create-job URL as the recruiter to demonstrate server-side authorization (403).
8. Sign in as admin, show platform counts, verify a company, moderate a job, and add a catalog skill.
9. In PostgreSQL, run selected statements from `sql/queries.sql`; show joins, aggregation, subqueries, `EXISTS`, and window ranking.
10. Show the live SQL in `app/models/applications.py`, the transaction flow in `app/services/applications.py`, and the standalone examples in `sql/transactions.sql`.
11. Render the Mermaid ERD/class diagram in the documentation and point out 19 connected tables, PKs, FKs, and delete behavior.

