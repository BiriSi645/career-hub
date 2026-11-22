# Relational Schema

The 19 application tables below use the column names from PostgreSQL. A `?` marks a nullable column. The last column shows the referenced key and the foreign key's delete action.

| Table | Columns | Primary key | Additional unique key | Foreign keys |
|---|---|---|---|---|
| `application_status_history` | `id`, `application_id`, `old_status`?, `new_status`, `changed_by`?, `note`?, `changed_at` | `id` | — | `application_id` → `applications(id)` (CASCADE)<br>`changed_by` → `users(id)` (SET NULL) |
| `applications` | `id`, `job_id`, `applicant_id`, `resume_id`?, `cover_letter`?, `status`, `applied_at`, `created_at`, `updated_at` | `id` | `job_id, applicant_id` | `applicant_id` → `users(id)` (CASCADE)<br>`job_id` → `job_postings(id)` (CASCADE)<br>`resume_id` → `resumes(id)` (SET NULL) |
| `companies` | `id`, `name`, `description`?, `website`?, `industry`?, `city`?, `country`, `is_verified`, `created_at`, `updated_at` | `id` | `name` | — |
| `company_staff` | `id`, `company_id`, `user_id`, `title`?, `can_manage_company`, `joined_at` | `id` | `company_id, user_id` | `company_id` → `companies(id)` (CASCADE)<br>`user_id` → `users(id)` (CASCADE) |
| `educations` | `id`, `user_id`, `institution`, `degree`, `field_of_study`?, `start_date`, `end_date`?, `description`?, `created_at`, `updated_at` | `id` | — | `user_id` → `users(id)` (CASCADE) |
| `experiences` | `id`, `user_id`, `company_id`?, `company_name`, `title`, `location`?, `start_date`, `end_date`?, `description`?, `created_at`, `updated_at` | `id` | — | `company_id` → `companies(id)` (SET NULL)<br>`user_id` → `users(id)` (CASCADE) |
| `interviews` | `id`, `application_id`, `scheduled_by`?, `scheduled_at`, `interview_type`, `location_or_link`, `notes`?, `status`, `created_at`, `updated_at` | `id` | — | `application_id` → `applications(id)` (CASCADE)<br>`scheduled_by` → `users(id)` (SET NULL) |
| `job_categories` | `id`, `name`, `description`? | `id` | `name` | — |
| `job_postings` | `id`, `company_id`, `category_id`, `created_by`, `title`, `description`, `requirements`?, `location`, `employment_type`, `workplace_type`, `salary_min`?, `salary_max`?, `status`, `deadline`?, `created_at`, `updated_at` | `id` | — | `category_id` → `job_categories(id)` (RESTRICT)<br>`company_id` → `companies(id)` (CASCADE)<br>`created_by` → `users(id)` (RESTRICT) |
| `job_required_skills` | `job_id`, `skill_id`, `is_mandatory`, `minimum_proficiency` | `job_id, skill_id` | — | `job_id` → `job_postings(id)` (CASCADE)<br>`skill_id` → `skills(id)` (CASCADE) |
| `jobseeker_profiles` | `user_id`, `headline`?, `bio`?, `city`?, `country`?, `linkedin_url`?, `portfolio_url`?, `created_at`, `updated_at` | `user_id` | — | `user_id` → `users(id)` (CASCADE) |
| `notifications` | `id`, `user_id`, `title`, `message`, `link`?, `is_read`, `created_at` | `id` | — | `user_id` → `users(id)` (CASCADE) |
| `resumes` | `id`, `user_id`, `title`, `file_url`, `is_primary`, `created_at`, `updated_at` | `id` | — | `user_id` → `users(id)` (CASCADE) |
| `roles` | `id`, `name`, `description`? | `id` | `name` | — |
| `saved_jobs` | `user_id`, `job_id`, `saved_at` | `user_id, job_id` | — | `job_id` → `job_postings(id)` (CASCADE)<br>`user_id` → `users(id)` (CASCADE) |
| `skills` | `id`, `name`, `category`? | `id` | `name` | — |
| `user_roles` | `user_id`, `role_id`, `assigned_at` | `user_id, role_id` | — | `role_id` → `roles(id)` (RESTRICT)<br>`user_id` → `users(id)` (CASCADE) |
| `user_skills` | `user_id`, `skill_id`, `proficiency`, `years_experience` | `user_id, skill_id` | — | `skill_id` → `skills(id)` (CASCADE)<br>`user_id` → `users(id)` (CASCADE) |
| `users` | `id`, `email`, `password_hash`, `first_name`, `last_name`, `phone`?, `is_active_account`, `created_at`, `updated_at` | `id` | `email` | — |

The separate `alembic_version` table records the schema revision. See [Database Design](DATABASE_DESIGN.md) for table purposes and [the SQL schema](../sql/schema.sql) for types, defaults, checks, and indexes.

