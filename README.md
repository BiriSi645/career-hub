# Career Hub

Career Hub is a database-driven Flask application for FSM Vakıf University SEN22321E. Job seekers build profiles, discover and save roles, apply, and track decisions. Recruiters manage companies, postings, candidates, status transitions, and interviews. Administrators moderate the platform.

The application runs handwritten PostgreSQL queries through Psycopg 3. See the [SQL guide](docs/SQL_QUERIES.md) for the query locations.

## Local setup with Docker

Start Docker Desktop, then run these commands from the project folder in PowerShell:

```powershell
docker compose up -d --build --wait
docker compose exec web python -m flask --app run seed
```

Open <http://127.0.0.1:5000> and sign in with a demo account below. Compose creates the application database in its own PostgreSQL volume. The web service applies migrations on startup.

Use `docker compose stop` to stop the services and `docker compose up -d` to start them again.

For a stable session key across restarts, set `SECRET_KEY` in `.env` to a randomly generated value. An unset key uses a fresh random key per process, which works for the single local Flask process. Set a shared `SECRET_KEY` in any multi-worker installation. Compose accepts `POSTGRES_PASSWORD` and `DOCKER_DATABASE_URL` overrides. For a new custom setup, configure the database password and connection URL together. Changing the Compose password on an existing volume requires updating the PostgreSQL role first. Enable `SESSION_COOKIE_SECURE=true` when running Flask behind HTTPS and keep demo accounts limited to local use.

## PostgreSQL connection

Connect to PostgreSQL from the project directory:

```powershell
docker compose exec db psql -U postgres -d career_hub
```

PostgreSQL stays on the internal Docker network. To use pgAdmin, connect it from the same Docker network to host `db`, port `5432`, using your PostgreSQL credentials.

## Windows setup without Docker

1. Install Python 3.11+ and PostgreSQL 15+.
2. In PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

3. Create the application database in PostgreSQL:

```powershell
psql -U postgres -f scripts/create_databases.sql
```

4. Update `DATABASE_URL` in `.env` if your PostgreSQL username or password differs.
5. Initialize and seed:

```powershell
$env:FLASK_APP = "run.py"
py -m flask db upgrade
py -m flask seed
py -m flask run
```

Open <http://127.0.0.1:5000>.

## Production on Vercel

1. Import this repository as a Vercel project with the repository root as the project root. Vercel detects the Flask application in `wsgi.py`. The same CSS URL works in Docker and on Vercel.
2. In the Vercel Marketplace, connect a Neon PostgreSQL database to the project. Set `DATABASE_URL` in the Vercel project to the **pooled** Neon connection string. The application verifies the PostgreSQL server certificate and hostname using TLS.
3. Create a **Private** Vercel Blob store and connect it to the project. Use the integration's `BLOB_STORE_ID` and Vercel OIDC credentials, or its `BLOB_READ_WRITE_TOKEN` if using token-based authentication. Keep these values on the server. Enable automatic exposure of Vercel system environment variables.
4. Add a stable random `SECRET_KEY` of at least 32 characters to the Vercel project. Generate one with `py -c "import secrets; print(secrets.token_hex(32))"`. Use separate credentials and data stores for preview deployments if you enable them.
5. Initialize Neon with the commands below, then deploy. Flask enables secure session cookies on Vercel. The application starts without running migrations or creating users.

### Initialize or upgrade Neon

Use the **direct** Neon connection string for the CLI. In its query string, set `sslmode=verify-full` and `sslrootcert=system`, and preserve the other Neon parameters. Run from the project root in PowerShell.

```powershell
docker compose build web
$env:DATABASE_URL = [System.Net.NetworkCredential]::new('', (Read-Host 'Neon direct URL' -AsSecureString)).Password
docker compose run --rm --no-deps -e DATABASE_URL web python -m flask --app wsgi db upgrade
docker compose run --rm --no-deps -e DATABASE_URL web python -m flask --app wsgi seed-catalog
docker compose run --rm --no-deps -e DATABASE_URL web python -m flask --app wsgi create-admin
Remove-Item Env:DATABASE_URL
```

Run each command after the previous one succeeds. `db upgrade` creates the 19 domain tables on a fresh database and applies pending revisions on an initialized database. Run it again when a deployment includes a schema revision. `seed-catalog` is repeatable and adds roles, job categories and skills. `create-admin` prompts for the first administrator's details and refuses a second administrator. Use the `seed` command only in development to add demo data.

### CV storage

Vercel stores CV files in Private Blob and their references and primary CV status in Neon. Downloads go through Flask's authenticated candidate and recruiter routes. Vercel uploads are limited to 4 MiB per CV. Local Docker continues to store files under `instance/resumes/`. If you import existing local CV records, transfer the corresponding files and update their references before serving downloads from Vercel.

## Development-only demo accounts

All demo accounts use `Demo123!`.

- Admin: `admin@careerhub.local`
- Job seekers: `student1@careerhub.local` through `student8@careerhub.local`
- Recruiters: `recruiter1@careerhub.local` through `recruiter4@careerhub.local`

Never use these credentials in production. Set a strong `SECRET_KEY`, enable secure cookies under HTTPS, and replace demo data.

See [DEMO_GUIDE.md](DEMO_GUIDE.md) for a manual walkthrough and [Project Overview](docs/PROJECT_OVERVIEW.md) for the architecture.

