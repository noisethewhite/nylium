-- ADR-0008 step 9: lock the new columns
ALTER TABLE files ALTER COLUMN type_name SET NOT NULL;
