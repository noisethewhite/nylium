-- ADR-0008 step 8: drop the file instances themselves (name scalar
-- cascades away)
DELETE FROM instances i USING types t WHERE i.type_uuid = t.uuid
  AND t.name IN ('File', 'Document', 'Image');
