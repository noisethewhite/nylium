-- ADR-0014: backfill type decor from legacy columns, then drop them.
-- Runs only while the old columns still exist.
DO $$ BEGIN IF EXISTS (SELECT 1 FROM information_schema.columns
  WHERE table_name = 'types' AND column_name = 'icon') THEN
  INSERT INTO type_decor (uuid, plural_name, icon, color)
  SELECT uuid, plural_name, icon, color FROM types
  ON CONFLICT (uuid) DO NOTHING;
  ALTER TABLE types DROP COLUMN plural_name;
  ALTER TABLE types DROP COLUMN icon;
  ALTER TABLE types DROP COLUMN color;
END IF; END $$;
