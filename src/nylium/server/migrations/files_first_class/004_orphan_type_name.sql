-- orphan files rows (no instance) get a sane fallback before NOT NULL
UPDATE files SET type_name = 'File' WHERE type_name IS NULL;
