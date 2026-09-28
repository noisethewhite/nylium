-- ADR-0028: many-to-one reference links. instance_values was keyed by the
-- target uuid (its PK), so a target could only be referenced from a single
-- owner. Re-key by (inst_uuid, prop_uuid) — "one target per (owner, prop)"
-- — and demote the target to an indexed FK column, so one target can be
-- referenced from any number of owners.

-- 1. Collapse any stale (owner, prop) duplicates left by re-pointing a ref
--    (the old merge_link keyed on target uuid never removed the old row).
--    Keep the most recently inserted row per (owner, prop).
DELETE FROM instance_values a
USING instance_values b
WHERE a.inst_uuid = b.inst_uuid
  AND a.prop_uuid = b.prop_uuid
  AND a.ctid < b.ctid;

-- 2. If the PK is still keyed on the target uuid, re-key it on (owner, prop).
DO $$
DECLARE
  pk_name text;
BEGIN
  SELECT c.conname INTO pk_name
  FROM pg_constraint c
  JOIN pg_attribute a
    ON a.attrelid = c.conrelid AND a.attnum = ANY (c.conkey)
  WHERE c.conrelid = 'instance_values'::regclass
    AND c.contype = 'p'
    AND a.attname = 'uuid'
  LIMIT 1;

  IF pk_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE instance_values DROP CONSTRAINT %I', pk_name);
    ALTER TABLE instance_values ADD PRIMARY KEY (inst_uuid, prop_uuid);
  END IF;
END $$;

-- 3. Index the target column for reverse lookups (backlinks, delete_links_to).
CREATE INDEX IF NOT EXISTS ix_instance_values_uuid ON instance_values (uuid);
