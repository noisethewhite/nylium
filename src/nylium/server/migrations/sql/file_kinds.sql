-- ADR-0006 follow-up: File/Document/Image are a dedicated kind, not object.
-- Idempotent — re-running re-sets the same value.
UPDATE types SET kind = 'file' WHERE name IN ('File', 'Document', 'Image');
