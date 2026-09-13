-- ADR-0008 step 2: backfill type_name/name from the (soon-to-die) instances
UPDATE files f SET type_name = t.name, name = COALESCE(
  (SELECT sv.value FROM string_values sv JOIN props p ON sv.prop_uuid = p.uuid
   WHERE sv.inst_uuid = f.uuid AND p.key = 'name'), i.name)
FROM instances i JOIN types t ON i.type_uuid = t.uuid
WHERE f.uuid = i.uuid AND t.name IN ('File', 'Document', 'Image');
