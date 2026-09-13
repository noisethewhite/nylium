-- ADR-0008 step 7: drop the redundant name prop on file types
-- (cascades string_values)
DELETE FROM props p USING types t WHERE p.owner_type_uuid = t.uuid
  AND t.name IN ('File', 'Document', 'Image') AND p.key = 'name';
