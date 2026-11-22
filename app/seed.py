from psycopg.rows import scalar_row
from datetime import datetime, timedelta, timezone

from werkzeug.security import generate_password_hash

from app.clock import local_today
from app.database import get_db, write_transaction
from app.models import applications


def seed_database():
    with write_transaction():
        get_db().execute("SELECT pg_advisory_xact_lock(708192362)")
        insert_demo_data()


def seed_catalog():
    execute = get_db().execute
    execute("""
        INSERT INTO roles (name, description)
        VALUES ('admin', 'Platform administrator'), ('jobseeker', 'Job seeker'),
               ('recruiter', 'Company recruiter')
        ON CONFLICT (name) DO NOTHING
    """)
    category_names = ["Software Development", "Data Science", "Product & Design", "Business", "Cybersecurity"]
    skill_names = [
        "Python", "Flask", "PostgreSQL", "JavaScript", "HTML/CSS", "React", "Git", "Docker",
        "Machine Learning", "Data Analysis", "Figma", "Communication", "Agile", "Cloud Computing", "Cybersecurity",
    ]
    with get_db().cursor() as cursor:
        cursor.executemany("""
            INSERT INTO job_categories (name) VALUES (%(name)s) ON CONFLICT (name) DO NOTHING
        """, [{"name": name} for name in category_names])
        cursor.executemany("""
            INSERT INTO skills (name, category) VALUES (%(name)s, %(category)s) ON CONFLICT (name) DO NOTHING
        """, [{"name": name, "category": "Professional" if name in {"Communication", "Agile"} else "Technical"}
               for name in skill_names])
    return category_names, skill_names


def insert_demo_data():
    category_names, skill_names = seed_catalog()
    execute = get_db().execute
    password_hash = generate_password_hash("Demo123!")

    def user(email, first, last, role):
        params = {"email": email, "first": first, "last": last, "role": role, "hash": password_hash}
        user_id = get_db().cursor(row_factory=scalar_row).execute("""
            INSERT INTO users (email, password_hash, first_name, last_name)
            VALUES (%(email)s, %(hash)s, %(first)s, %(last)s)
            ON CONFLICT (email) DO NOTHING RETURNING id
        """, params).fetchone()
        if user_id is None:
            return get_db().cursor(row_factory=scalar_row).execute("SELECT id FROM users WHERE email = %(email)s", params).fetchone()
        params["user_id"] = user_id
        execute("""
            INSERT INTO user_roles (user_id, role_id)
            SELECT %(user_id)s, id FROM roles WHERE name = %(role)s
        """, params)
        if role == "jobseeker":
            execute("""
                INSERT INTO jobseeker_profiles (user_id, headline, city, country)
                VALUES (%(user_id)s, 'Software engineering student', 'Istanbul', 'Türkiye')
            """, params)
        return user_id

    user("admin@careerhub.local", "Ada", "Admin", "admin")
    seekers = [
        user(f"student{i}@careerhub.local", fn, ln, "jobseeker")
        for i, (fn, ln) in enumerate(
            [
                ("Elif", "Yılmaz"),
                ("Mert", "Kaya"),
                ("Zeynep", "Demir"),
                ("Can", "Aydın"),
                ("Ece", "Şahin"),
                ("Bora", "Çelik"),
                ("Selin", "Arslan"),
                ("Emir", "Koç"),
            ],
            1,
        )
    ]
    recruiters = [
        user(f"recruiter{i}@careerhub.local", fn, ln, "recruiter")
        for i, (fn, ln) in enumerate(
            [
                ("Deniz", "Aksoy"),
                ("Işıl", "Güneş"),
                ("Ozan", "Tekin"),
                ("Derya", "Polat"),
            ],
            1,
        )
    ]
    company_data = [
        ("NovaTech Labs", "Software"),
        ("Bosporus Analytics", "Data & AI"),
        ("GreenRoute Mobility", "Transportation"),
        ("Lumen Finance", "Fintech"),
    ]
    companies = []
    for (name, industry), recruiter_id in zip(company_data, recruiters):
        params = {"name": name, "industry": industry,
                  "description": f"{name} builds thoughtful technology products."}
        company_id = get_db().cursor(row_factory=scalar_row).execute("""
            INSERT INTO companies (name, industry, description, city, is_verified)
            VALUES (%(name)s, %(industry)s, %(description)s, 'Istanbul', TRUE)
            ON CONFLICT (name) DO NOTHING RETURNING id
        """, params).fetchone()
        if company_id is None:
            company_id = get_db().cursor(row_factory=scalar_row).execute("SELECT id FROM companies WHERE name = %(name)s", params).fetchone()
        companies.append(company_id)
        execute("""
            INSERT INTO company_staff (company_id, user_id, title, can_manage_company)
            VALUES (%(company_id)s, %(user_id)s, 'Talent Partner', TRUE)
            ON CONFLICT (company_id, user_id) DO NOTHING
        """, {"company_id": company_id, "user_id": recruiter_id})

    category_ids = dict(execute("SELECT name, id FROM job_categories").fetchall())
    skill_ids = dict(execute("SELECT name, id FROM skills").fetchall())
    categories = [category_ids[name] for name in category_names]
    skills = [skill_ids[name] for name in skill_names]

    for i, user_id in enumerate(seekers):
        params = {"user_id": user_id}
        execute("""
            INSERT INTO educations (user_id, institution, degree, field_of_study, start_date)
            SELECT %(user_id)s, 'Fatih Sultan Mehmet Vakıf University', 'BSc', 'Software Engineering', DATE '2022-09-01'
            WHERE NOT EXISTS (SELECT 1 FROM educations WHERE user_id = %(user_id)s)
        """, params)
        execute("""
            INSERT INTO experiences (user_id, company_name, title, start_date, end_date)
            SELECT %(user_id)s, 'Student Technology Club', 'Developer', DATE '2024-02-01', DATE '2024-06-30'
            WHERE NOT EXISTS (SELECT 1 FROM experiences WHERE user_id = %(user_id)s)
        """, params)
        execute("""
            UPDATE experiences SET end_date = DATE '2024-06-30', updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %(user_id)s AND company_id IS NULL AND company_name = 'Student Technology Club'
              AND title = 'Developer' AND start_date = DATE '2024-02-01' AND end_date IS NULL
              AND location IS NULL AND description IS NULL
        """, params)
        execute("""
            INSERT INTO resumes (user_id, title, file_url, is_primary)
            SELECT %(user_id)s, 'Demo CV', 'demo:cv', TRUE
            WHERE NOT EXISTS (SELECT 1 FROM resumes WHERE user_id = %(user_id)s)
        """, params)
        with get_db().cursor() as cursor:
            cursor.executemany("""
                INSERT INTO user_skills (user_id, skill_id, proficiency, years_experience)
                VALUES (%(user_id)s, %(skill_id)s, 'intermediate', 1)
                ON CONFLICT (user_id, skill_id) DO NOTHING
            """, [{"user_id": user_id, "skill_id": skills[(i + offset) % len(skills)]} for offset in range(3)])

    titles = [
        "Junior Python Developer",
        "Backend Engineering Intern",
        "Data Analyst",
        "Frontend Developer",
        "Product Design Intern",
        "QA Engineer",
        "Machine Learning Intern",
        "Full Stack Developer",
        "Business Analyst",
        "Cloud Engineering Intern",
        "Mobile Developer",
        "Database Developer",
        "Security Analyst Intern",
        "DevOps Engineer",
        "Product Manager Intern",
        "Software Support Specialist",
        "Data Engineering Intern",
        "UX Researcher",
        "Automation Test Engineer",
        "Graduate Software Engineer",
    ]
    jobs = []
    for i, title in enumerate(titles):
        params = {"title": title, "company_id": companies[i % 4]}
        job_id = get_db().cursor(row_factory=scalar_row).execute("""
            SELECT id FROM job_postings WHERE title = %(title)s AND company_id = %(company_id)s ORDER BY id LIMIT 1
        """, params).fetchone()
        if job_id is None:
            job_id = get_db().cursor(row_factory=scalar_row).execute("""
                INSERT INTO job_postings (company_id, category_id, created_by, title, description,
                    requirements, location, employment_type, workplace_type, salary_min, salary_max, status, deadline)
                VALUES (%(company_id)s, %(category_id)s, %(recruiter_id)s, %(title)s, %(description)s,
                    'Curiosity, collaboration, and relevant foundational skills.', 'Istanbul',
                    %(employment_type)s, %(workplace_type)s, %(salary_min)s, %(salary_max)s, 'open', %(deadline)s)
                RETURNING id
            """, {**params, "category_id": categories[i % 5], "recruiter_id": recruiters[i % 4],
                   "description": f"Join our team as a {title}. You will collaborate on real products, learn from peers, and deliver measurable impact.",
                   "employment_type": "internship" if "Intern" in title else "full_time",
                   "workplace_type": ("remote", "hybrid", "onsite")[i % 3],
                   "salary_min": 20000 + i * 500, "salary_max": 30000 + i * 700,
                   "deadline": local_today() + timedelta(days=30 + i)}).fetchone()
            execute("""
                INSERT INTO job_required_skills (job_id, skill_id, is_mandatory, minimum_proficiency)
                VALUES (%(job_id)s, %(skill_id)s, TRUE, 'beginner')
            """, {"job_id": job_id, "skill_id": skills[i % len(skills)]})
        jobs.append(job_id)

    paths = (
        ("submitted",), ("submitted", "reviewing"),
        ("submitted", "reviewing", "shortlisted"), ("submitted", "reviewing", "interview"),
        ("submitted", "rejected"),
    )
    for i in range(24):
        path = paths[i % len(paths)]
        params = {"job_id": jobs[i % 20], "user_id": seekers[i % 8],
                  "status": path[-1], "recruiter_id": recruiters[i % 4]}
        application_id = get_db().cursor(row_factory=scalar_row).execute("""
            INSERT INTO applications (job_id, applicant_id, resume_id, cover_letter, status)
            VALUES (%(job_id)s, %(user_id)s,
                    (SELECT id FROM resumes WHERE user_id = %(user_id)s AND is_primary ORDER BY id LIMIT 1),
                    'I am excited to contribute and grow with your team.', %(status)s)
            ON CONFLICT (job_id, applicant_id) DO NOTHING RETURNING id
        """, params).fetchone()
        if application_id is None:
            continue
        params["id"] = application_id
        execute("""
            INSERT INTO application_status_history (application_id, new_status, changed_by, note)
            VALUES (%(id)s, 'submitted', %(user_id)s, 'Demo application')
        """, params)
        for old_status, new_status in zip(path, path[1:]):
            execute("""
                INSERT INTO application_status_history (application_id, old_status, new_status, changed_by, note)
                VALUES (%(id)s, %(old_status)s, %(new_status)s, %(recruiter_id)s, 'Recruiter review')
            """, {**params, "old_status": old_status, "new_status": new_status})
        if path[-1] == "interview":
            params["scheduled_at"] = datetime.now(timezone.utc) + timedelta(days=i + 2)
            execute("""
                INSERT INTO interviews (application_id, scheduled_by, scheduled_at, interview_type, location_or_link)
                VALUES (%(id)s, %(recruiter_id)s, %(scheduled_at)s, 'onsite', 'Company reception (demo)')
            """, params)
        if len(path) > 1:
            execute("""
                INSERT INTO notifications (user_id, title, message, link)
                VALUES (%(user_id)s, 'Application update', %(message)s, %(link)s)
            """, {**params, "message": f"There is an update for {titles[i % len(titles)]}.",
                   "link": f"/seeker/applications/{application_id}"})
    for i, user_id in enumerate(seekers):
        execute("""
            INSERT INTO saved_jobs (user_id, job_id) VALUES (%(user_id)s, %(job_id)s)
            ON CONFLICT (user_id, job_id) DO NOTHING
        """, {"user_id": user_id, "job_id": jobs[(i + 5) % 20]})

    # Advance selected untouched demo applications through offer and hire.
    for job_index, seeker_index in ((17, 1), (12, 4), (2, 6)):
        hire_demo_candidate(jobs[job_index], seekers[seeker_index], recruiters[job_index % 4])


def hire_demo_candidate(job_id, user_id, recruiter_id):
    params = {"job_id": job_id, "user_id": user_id}
    application = get_db().execute("""
        SELECT a.id, j.title, j.location, c.id AS company_id, c.name AS company_name
        FROM applications AS a JOIN job_postings AS j ON j.id = a.job_id
        JOIN companies AS c ON c.id = j.company_id
        WHERE a.job_id = %(job_id)s AND a.applicant_id = %(user_id)s AND a.status = 'shortlisted'
          AND a.cover_letter = 'I am excited to contribute and grow with your team.'
          AND (SELECT array_agg(h.new_status::text ORDER BY h.id)
               FROM application_status_history AS h WHERE h.application_id = a.id)
              IN (ARRAY['submitted', 'shortlisted'], ARRAY['submitted', 'reviewing', 'shortlisted'])
          AND NOT EXISTS (SELECT 1 FROM application_status_history AS h WHERE h.application_id = a.id
                          AND h.note IS DISTINCT FROM 'Demo application'
                          AND h.note IS DISTINCT FROM 'Recruiter review')
        FOR UPDATE OF a
    """, params).fetchone()
    if application is None:
        return
    legacy_history = get_db().execute("""
        UPDATE application_status_history SET new_status = 'reviewing'
        WHERE application_id = %s AND old_status = 'submitted' AND new_status = 'shortlisted'
    """, (application.id,)).rowcount
    if legacy_history:
        applications.insert_status_history(application.id, "reviewing", "shortlisted", recruiter_id, "Recruiter review")
    for old_status, new_status in (("shortlisted", "offered"), ("offered", "hired")):
        applications.update_status(new_status, application.id, old_status)
        applications.insert_status_history(application.id, old_status, new_status, recruiter_id, "Demo hiring")
    applications.insert_hired_experience({**application._asdict(), "user_id": user_id, "start_date": local_today()})
    applications.insert_notification(user_id, "Congratulations — you were hired",
                                     f"You were hired by {application.company_name} as {application.title}.",
                                     f"/seeker/applications/{application.id}")
