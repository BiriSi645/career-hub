# Database Design

## Table purposes

| Table | What it stores |
|---|---|
| `users` | User accounts and password hashes. |
| `roles` | The candidate, recruiter, and administrator roles. |
| `user_roles` | Which roles each user has. |
| `jobseeker_profiles` | A candidate's profile details. |
| `companies` | Company details and verification status. |
| `company_staff` | Which users can act for each company. |
| `skills` | The list of skills users and job postings can reference. |
| `user_skills` | A candidate's skills and proficiency levels. |
| `educations` | A candidate's education records. |
| `experiences` | A candidate's work history, optionally linked to a registered company. |
| `resumes` | CV titles, file references, and the primary-CV flag. Uploaded files live in `instance/resumes/` locally and in Private Blob on Vercel. |
| `job_categories` | Categories used to group and filter postings. |
| `job_postings` | Job details, employer, deadline, and posting status. |
| `job_required_skills` | Skills required or preferred for a posting. |
| `applications` | A candidate's application to a posting and its current status. |
| `application_status_history` | When each application status changed and who changed it. |
| `saved_jobs` | Postings a candidate bookmarked. |
| `interviews` | Interview dates and other scheduling details for applications. |
| `notifications` | Messages sent to users and whether they have read them. |

## Keys and constraints

Most entity tables use generated integer primary keys. `jobseeker_profiles` uses its user ID as both primary and foreign key. `user_roles`, `user_skills`, `job_required_skills`, and `saved_jobs` use composite primary keys. `company_staff` has a generated ID and a separate unique company/user pair. Check constraints limit allowed values and validate date order, nonnegative skill experience, and salary range order. PostgreSQL indexes primary and unique keys. The schema also defines indexes for company-linked experiences, job status and deadlines, applications by job and status, notifications by user and read status, and interview times.

The application service coordinates application transactions and runs the SQL in `app/models/applications.py`. `sql/transactions.sql` contains teaching examples for those workflows. The `flask db upgrade` command applies `sql/schema.sql` and `sql/link_experiences.sql` through Psycopg 3 and stores the current revision in `alembic_version`.

The current base schema contains `experiences.company_id`. Revision `002_company_experiences` adds the column and foreign key only when upgrading a legacy base schema without it. It ensures the index exists and links matching company names. The admin database browser reads only allowlisted tables and excludes credential fields and selected private content.

## Fields and the interface

Candidates edit `users.phone` on their profile. Recruiters manage `interviews.status` on an application and can choose `draft` or `open` when creating a posting. The administrator can moderate all posting statuses and edit `job_categories.description` and `skills.category` in the catalog. Password hashes, file storage references, schema revisions, and record timestamps are managed by the application or PostgreSQL.

