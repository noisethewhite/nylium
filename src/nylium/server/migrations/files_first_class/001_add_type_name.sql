-- ADR-0008 step 1: new columns (files.uuid stays the stable pointer)
ALTER TABLE files ADD COLUMN IF NOT EXISTS type_name TEXT;
