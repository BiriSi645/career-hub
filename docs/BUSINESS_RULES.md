# Business Rules

1. Email, role name, company name, category name, and skill name are unique.
2. Registration assigns either the `jobseeker` or `recruiter` role. Administrators manage role assignments through `user_roles`. The role-removal screen blocks removal of a user's sole role and protects the administrator's own role. Server-side checks protect role-specific pages.
3. A seeker has at most one profile but many qualifications and applications.
4. Each company/user pair can have one membership. Recruiter actions on postings and applications require membership in the relevant company. Editing the company also requires `can_manage_company`. Administrators moderate postings through a separate screen.
5. Each posting belongs to exactly one company and category and has one author.
6. Posting types, workplace modes, statuses, interview values, and proficiency values use checked enumerations.
7. A seeker can apply once per job while its status is `open` and its deadline, if set, has not passed. An attached CV must belong to the applicant. The database enforces one application per `(job_id, applicant_id)`.
8. Application transitions follow: submitted → reviewing/rejected/withdrawn; reviewing → shortlisted/interview/rejected; shortlisted → interview/offered/rejected; interview → offered/rejected; offered → hired/rejected. Terminal states do not transition.
9. Submitting an application creates its initial history entry. Recruiter status changes add a history entry and a notification in the same transaction as the update. Hiring can also add a linked work-experience record in that transaction. History entries are kept while the application exists. The database cascades their deletion when the application is deleted.
10. Education/experience end dates cannot precede start dates; maximum salary cannot be less than minimum.
11. Junction rows are unique through composite primary keys or unique constraints.
12. Foreign-key delete actions depend on the relationship. Deleting a posting cascades to its applications, which cascade to interviews and status history. Deleting a referenced CV, audit actor, or company linked to a work-experience record clears the corresponding optional reference. Referenced categories, assigned roles, and posting authors use `RESTRICT`.
13. The public board and homepage count open postings from verified companies whose deadlines have not passed. Draft and rejected details are hidden. A closed posting from a verified company remains viewable by its direct URL, with applications disabled. Postings created for unverified companies start as drafts.
14. Recruiter deletion preserves postings that already have applications. It closes an open posting and retains its application, interview, and status history records. Permanent deletion requires confirmation and is available for postings without applications.
15. Interviews use Istanbul time in the form and display. PostgreSQL stores the timestamp as `TIMESTAMPTZ`. An interview starts as `scheduled` and can be marked `completed` or `cancelled`. A past time cannot be scheduled, and only recruiting staff for the application's company can make changes.
16. Candidates can read and mark only their own notifications. A posting's skills record a minimum proficiency and whether that skill is required or preferred. Candidates can apply even if their profile lists different skills.

