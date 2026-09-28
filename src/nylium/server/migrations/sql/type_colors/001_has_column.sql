-- ADR-0005: does the legacy types.color column still exist?
SELECT 1 FROM information_schema.columns WHERE table_name = 'types' AND column_name = 'color';
