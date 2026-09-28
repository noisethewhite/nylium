-- ADR-0013: traits + trait-bound props. traits/type_traits tables come
-- from create_all; existing props rows get the new columns
ALTER TABLE props ADD COLUMN IF NOT EXISTS owner_trait_uuid UUID REFERENCES traits(uuid) ON DELETE CASCADE;
