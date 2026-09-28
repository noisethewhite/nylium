-- ADR-0008 step 6: sever files.uuid FK -> instances so file rows outlive instances
ALTER TABLE files DROP CONSTRAINT IF EXISTS files_uuid_fkey;
