-- 1 available jobs and companies (INNER JOIN, ORDER BY)

SELECT
    j.id,
    j.title,
    c.name AS company,
    j.location
FROM job_postings j
INNER JOIN companies c ON c.id = j.company_id
WHERE j.status = 'open' AND c.is_verified
  AND (j.deadline IS NULL OR j.deadline >= (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Istanbul')::date)
ORDER BY j.created_at DESC;

-- 2 internships

SELECT j.id, j.title, j.location
FROM job_postings AS j JOIN companies AS c ON c.id = j.company_id
WHERE
    j.employment_type = 'internship' AND j.status = 'open' AND c.is_verified
    AND (j.deadline IS NULL OR j.deadline >= (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Istanbul')::date);

-- 3 users with Python (multi-table, ILIKE)

SELECT DISTINCT
    u.id,
    u.first_name,
    u.last_name
FROM users u
JOIN user_skills us ON us.user_id = u.id
JOIN skills s ON s.id = us.skill_id
WHERE s.name ILIKE 'python';

-- 4 application counts including zero (LEFT JOIN, GROUP BY)

SELECT
    j.title,
    COUNT(a.id) application_count
FROM job_postings j
LEFT JOIN applications a ON a.job_id = j.id
GROUP BY j.id
ORDER BY application_count DESC;

-- 5 postings per company

SELECT
    c.name,
    COUNT(j.id) posting_count
FROM companies c
LEFT JOIN job_postings j ON j.company_id = c.id
GROUP BY c.id;

-- 6 companies with >3 active jobs (HAVING)

SELECT
    c.name,
    COUNT(*) active_jobs
FROM companies c
JOIN job_postings j ON j.company_id = c.id
WHERE j.status = 'open' AND c.is_verified
  AND (j.deadline IS NULL OR j.deadline >= (CURRENT_TIMESTAMP AT TIME ZONE 'Europe/Istanbul')::date)
GROUP BY c.id
HAVING COUNT(*) > 3;

-- 7 applications with seeker and company

SELECT
    a.id,
    u.email,
    j.title,
    c.name,
    a.status
FROM applications a
JOIN users u ON u.id = a.applicant_id
JOIN job_postings j ON j.id = a.job_id
JOIN companies c ON c.id = j.company_id;

-- 8 users never applying (NOT EXISTS)

SELECT u.id, u.first_name, u.last_name
FROM users u
WHERE
    NOT EXISTS
    (
        SELECT 1
        FROM applications a
        WHERE a.applicant_id = u.id
    );

-- 9 jobs requiring Python (EXISTS)

SELECT j.*
FROM job_postings j
WHERE
    EXISTS
    (
        SELECT 1
        FROM job_required_skills rs
        JOIN skills s ON s.id = rs.skill_id
        WHERE
            rs.job_id = j.id
            AND s.name = 'Python'
    );

-- 10 popular categories

SELECT
    jc.name,
    COUNT(a.id) applications
FROM job_categories jc
JOIN job_postings j ON j.category_id = jc.id
LEFT JOIN applications a ON a.job_id = j.id
GROUP BY jc.id
ORDER BY applications DESC;

-- 11 pending pipeline (IN)

SELECT *
FROM applications
WHERE status IN ('submitted', 'reviewing', 'shortlisted')
ORDER BY applied_at;

-- 12 saved jobs for a user

SELECT
    j.title,
    c.name
FROM saved_jobs sj
JOIN job_postings j ON j.id = sj.job_id
JOIN companies c ON c.id = j.company_id
WHERE sj.user_id = :user_id
ORDER BY sj.saved_at DESC;

-- 13 upcoming interviews

SELECT
    i.scheduled_at,
    u.email,
    j.title
FROM interviews i
JOIN applications a ON a.id = i.application_id
JOIN users u ON u.id = a.applicant_id
JOIN job_postings j ON j.id = a.job_id
WHERE
    i.scheduled_at > NOW()
    AND i.status = 'scheduled'
ORDER BY i.scheduled_at;

-- 14 average offered salary by category (AVG)

SELECT
    jc.name,
    ROUND(AVG((j.salary_min + j.salary_max) / 2), 2) average_salary
FROM job_categories jc
JOIN job_postings j ON j.category_id = jc.id
WHERE
    j.salary_min IS NOT NULL
    AND j.salary_max IS NOT NULL
GROUP BY jc.id;

-- 15 companies ranked by received applications

SELECT
    c.name,
    COUNT(a.id) applications,
    DENSE_RANK() OVER (
        ORDER BY COUNT(a.id) DESC
    ) rank
FROM companies c
LEFT JOIN job_postings j ON j.company_id = c.id
LEFT JOIN applications a ON a.job_id = j.id
GROUP BY c.id;

-- 16 total midpoint salary budgets (SUM)

SELECT
    c.name,
    SUM((j.salary_min + j.salary_max) / 2) total_midpoint
FROM companies c
JOIN job_postings j ON j.company_id = c.id
GROUP BY c.id;

-- 17 above-average salary postings (subquery)

SELECT
    title,
    salary_max
FROM job_postings
WHERE
    salary_max
    > (
        SELECT AVG(salary_max)
        FROM job_postings
        WHERE salary_max IS NOT NULL
    );

-- 18 search titles/descriptions

SELECT
    id,
    title
FROM job_postings
WHERE
    title ILIKE '%' || :term || '%'
    OR description ILIKE '%' || :term || '%';
