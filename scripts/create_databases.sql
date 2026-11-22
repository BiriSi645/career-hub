-- Run as a PostgreSQL administrator: psql -U postgres -f scripts/create_databases.sql
SELECT 'CREATE DATABASE career_hub'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'career_hub')\gexec


