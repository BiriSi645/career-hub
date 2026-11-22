# Entity–Relationship Diagram

The diagram covers the 19 application tables and their 26 foreign-key relationships. A solid line marks a relationship whose foreign key is part of the child table's primary key. A dashed line marks the other foreign-key relationships.

```mermaid
erDiagram
  APPLICATION_STATUS_HISTORY {
    int id PK
    int changed_by FK
    int application_id FK
  }
  APPLICATIONS {
    int id PK
    int job_id FK
    int resume_id FK
    int applicant_id FK
  }
  COMPANIES {
    int id PK
  }
  COMPANY_STAFF {
    int id PK
    int user_id FK
    int company_id FK
  }
  EDUCATIONS {
    int id PK
    int user_id FK
  }
  EXPERIENCES {
    int id PK
    int user_id FK
    int company_id FK
  }
  INTERVIEWS {
    int id PK
    int application_id FK
    int scheduled_by FK
  }
  JOB_CATEGORIES {
    int id PK
  }
  JOB_POSTINGS {
    int id PK
    int category_id FK
    int company_id FK
    int created_by FK
  }
  JOB_REQUIRED_SKILLS {
    int job_id PK, FK
    int skill_id PK, FK
  }
  JOBSEEKER_PROFILES {
    int user_id PK, FK
  }
  NOTIFICATIONS {
    int id PK
    int user_id FK
  }
  RESUMES {
    int id PK
    int user_id FK
  }
  ROLES {
    int id PK
  }
  SAVED_JOBS {
    int user_id PK, FK
    int job_id PK, FK
  }
  SKILLS {
    int id PK
  }
  USER_ROLES {
    int user_id PK, FK
    int role_id PK, FK
  }
  USER_SKILLS {
    int user_id PK, FK
    int skill_id PK, FK
  }
  USERS {
    int id PK
  }

  USERS ||--o{ USER_ROLES : has
  ROLES ||--o{ USER_ROLES : assigns
  USERS ||--o| JOBSEEKER_PROFILES : owns
  USERS ||..o{ COMPANY_STAFF : joins
  COMPANIES ||..o{ COMPANY_STAFF : authorizes
  USERS ||--o{ USER_SKILLS : has
  SKILLS ||--o{ USER_SKILLS : classifies
  USERS ||..o{ EDUCATIONS : records
  USERS ||..o{ EXPERIENCES : records
  COMPANIES o|..o{ EXPERIENCES : linked_to
  USERS ||..o{ RESUMES : uploads
  COMPANIES ||..o{ JOB_POSTINGS : publishes
  JOB_CATEGORIES ||..o{ JOB_POSTINGS : groups
  USERS ||..o{ JOB_POSTINGS : creates
  JOB_POSTINGS ||--o{ JOB_REQUIRED_SKILLS : requires
  SKILLS ||--o{ JOB_REQUIRED_SKILLS : required_in
  USERS ||..o{ APPLICATIONS : submits
  JOB_POSTINGS ||..o{ APPLICATIONS : receives
  RESUMES o|..o{ APPLICATIONS : supports
  APPLICATIONS ||..o{ APPLICATION_STATUS_HISTORY : tracks
  USERS o|..o{ APPLICATION_STATUS_HISTORY : changes
  USERS ||--o{ SAVED_JOBS : saves
  JOB_POSTINGS ||--o{ SAVED_JOBS : saved_as
  APPLICATIONS ||..o{ INTERVIEWS : schedules
  USERS o|..o{ INTERVIEWS : arranges
  USERS ||..o{ NOTIFICATIONS : receives
```

