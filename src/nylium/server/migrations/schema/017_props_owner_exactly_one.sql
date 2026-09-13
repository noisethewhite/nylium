-- ADD CONSTRAINT has no IF NOT EXISTS — DO + pg_constraint instead
DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint
  WHERE conname = 'props_owner_exactly_one') THEN
  ALTER TABLE props ADD CONSTRAINT props_owner_exactly_one
  CHECK ((owner_type_uuid IS NULL) <> (owner_trait_uuid IS NULL));
END IF; END $$;
