-- psql example A. In a demo database, set :job_id, :user_id, :resume_id and :cover_letter.
-- Use NULL for an optional value, or pass a quoted SQL literal for the cover letter.
BEGIN;

WITH eligible_job AS (
    SELECT j.id
    FROM job_postings AS j
    JOIN companies AS c ON c.id = j.company_id
    WHERE j.id = :job_id AND j.status = 'open' AND c.is_verified
      AND (j.deadline IS NULL OR j.deadline >= (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Istanbul')::date)
      AND EXISTS (
          SELECT 1 FROM users AS u
          JOIN user_roles AS ur ON ur.user_id = u.id
          JOIN roles AS r ON r.id = ur.role_id
          WHERE u.id = :user_id AND u.is_active_account AND r.name = 'jobseeker'
      )
      AND (:resume_id IS NULL OR EXISTS (
          SELECT 1 FROM resumes WHERE id = :resume_id AND user_id = :user_id
      ))
    FOR SHARE OF j, c
), inserted AS (
    INSERT INTO applications (job_id, applicant_id, resume_id, cover_letter, status)
    SELECT eligible_job.id, :user_id, :resume_id, :cover_letter, 'submitted'
    FROM eligible_job
    ON CONFLICT (job_id, applicant_id) DO NOTHING
    RETURNING id
)
INSERT INTO application_status_history (application_id, new_status, changed_by, note)
SELECT id, 'submitted', :user_id, 'Application submitted'
FROM inserted
RETURNING application_id;

COMMIT;

-- psql example B. Set :application_id to the returned ID and :recruiter_id to a
-- recruiter who belongs to the company. This example performs one legal transition.
BEGIN;

WITH changed AS (
    UPDATE applications AS a
    SET status = 'reviewing', updated_at = CURRENT_TIMESTAMP
    FROM job_postings AS j
    JOIN company_staff AS cs ON cs.company_id = j.company_id
    JOIN users AS u ON u.id = cs.user_id
    JOIN user_roles AS ur ON ur.user_id = u.id
    JOIN roles AS r ON r.id = ur.role_id
    WHERE a.id = :application_id AND a.job_id = j.id AND a.status = 'submitted'
      AND u.id = :recruiter_id AND u.is_active_account AND r.name = 'recruiter'
    RETURNING a.id, a.applicant_id
), history AS (
    INSERT INTO application_status_history (application_id, old_status, new_status, changed_by)
    SELECT id, 'submitted', 'reviewing', :recruiter_id
    FROM changed
    RETURNING application_id
)
INSERT INTO notifications (user_id, title, message, link)
SELECT c.applicant_id, 'Application status updated', 'Your application is now under review.',
       '/seeker/applications/' || c.id
FROM changed AS c
JOIN history AS h ON h.application_id = c.id
RETURNING id;

COMMIT;

-- If a statement fails in an interactive session, use ROLLBACK before retrying.
-- A guard that matches no row writes nothing in its transaction.
