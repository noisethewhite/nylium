-- ADR-0008 step 3: copy direct file references into file_values (keyed by
-- owner instance + prop, pointing at files.uuid)
INSERT INTO file_values (file_uuid, inst_uuid, prop_uuid)
SELECT iv.uuid, iv.inst_uuid, iv.prop_uuid FROM instance_values iv
JOIN instances i ON iv.uuid = i.uuid
JOIN types t ON i.type_uuid = t.uuid
WHERE t.name IN ('File', 'Document', 'Image')
ON CONFLICT (inst_uuid, prop_uuid) DO NOTHING;
