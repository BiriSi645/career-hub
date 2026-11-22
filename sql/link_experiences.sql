-- The base schema already includes this relationship. Install it only on legacy schemas.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_attribute
        WHERE attrelid = 'experiences'::regclass AND attname = 'company_id' AND NOT attisdropped
    ) THEN
        ALTER TABLE experiences ADD COLUMN company_id INTEGER
            CONSTRAINT fk_experiences_company_id REFERENCES companies(id) ON DELETE SET NULL;
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS ix_experiences_company_id ON experiences (company_id);

UPDATE experiences AS experience
SET company_id = company.id
FROM companies AS company
WHERE experience.company_id IS NULL
  AND lower(trim(experience.company_name)) = lower(trim(company.name));
