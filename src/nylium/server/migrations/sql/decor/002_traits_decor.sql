DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns
  WHERE table_name = 'traits' AND column_name = 'color') THEN
  INSERT INTO trait_decor (uuid, color)
  SELECT uuid, color FROM traits
  ON CONFLICT (uuid) DO NOTHING;
  ALTER TABLE traits DROP COLUMN color;
END IF; END $$;
