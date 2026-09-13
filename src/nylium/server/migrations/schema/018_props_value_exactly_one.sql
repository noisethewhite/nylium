DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_constraint
  WHERE conname = 'props_value_exactly_one') THEN
  ALTER TABLE props ADD CONSTRAINT props_value_exactly_one
  CHECK ((value_type_uuid IS NULL) <> (value_trait_uuid IS NULL));
END IF; END $$;
