-- ADR-0008 step 4: drop the old instance_values rows for file refs (now in
-- file_values; their uuid FK -> instances would block step 8)
DELETE FROM instance_values iv USING instances i, types t
WHERE iv.uuid = i.uuid AND i.type_uuid = t.uuid
  AND t.name IN ('File', 'Document', 'Image');
