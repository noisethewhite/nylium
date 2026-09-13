-- ADR-0007: computed-scalar reference (mutually exclusive with formula)
ALTER TABLE props ADD COLUMN IF NOT EXISTS function_uuid UUID;
