-- ADR-0008 step 5: sever array_values.value_uuid FK so
-- Array<File/Document/Image> members (already holding the right files.uuid)
-- survive step 8
ALTER TABLE array_values DROP CONSTRAINT IF EXISTS array_values_value_uuid_fkey;
