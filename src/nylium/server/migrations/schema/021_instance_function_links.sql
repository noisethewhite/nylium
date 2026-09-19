-- ADR-0029: instance-bound functions. Drop the type-level props.function_uuid
-- column (replaced by instance_function_links) and the function_deps table
-- (replaced by per-owner dependency resolution). Prod has no functions, so
-- no data migration is needed.
ALTER TABLE props DROP COLUMN IF EXISTS function_uuid;
DROP TABLE IF EXISTS function_deps;
