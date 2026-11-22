# Requirements

## Functional

- Register as a job seeker or recruiter, sign in, and sign out. Administrators manage role assignments.
- Maintain a candidate profile and phone number, add education and experience, manage skills, and upload, download or delete CV files.
- Search and filter open jobs, bookmark jobs, and submit one application per eligible job before or on its deadline.
- Create and edit companies, save drafts, publish verified-company postings, and set mandatory or preferred skills and minimum proficiency. Preserve postings with application records and confirm deletion of other postings.
- Validate application state transitions, schedule interviews in Istanbul time, and update interview status.
- Administer users, company verification, moderation, categories, and skills.
- Show notification history and let candidates mark their own notifications as read. Calculate the homepage and dashboard statistics from database records.

## Nonfunctional

- PostgreSQL foreign keys, uniqueness and check constraints, transactions for related writes, and indexes for selected lookups.
- Password hashing, CSRF protection, configurable secure cookies, and server-side role and ownership checks.
- Bootstrap layouts, form feedback, MVC structure, and repeatable demo data setup.
- Windows-local installation through Docker Compose or a local PostgreSQL setup.

Actors are Visitor, Job Seeker, Recruiter, and Administrator. Permission details are in `BUSINESS_RULES.md`.

