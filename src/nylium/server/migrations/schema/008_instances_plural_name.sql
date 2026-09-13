-- ADR-0011 phase 8: instance plural_name is mandatory + unique
ALTER TABLE instances ADD COLUMN IF NOT EXISTS plural_name TEXT;
