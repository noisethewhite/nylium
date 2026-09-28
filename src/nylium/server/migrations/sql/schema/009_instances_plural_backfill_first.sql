-- instance names are not unique: first bearer of a name gets the plain
-- "<name>s", later duplicates get a uuid-suffixed plural (010)
UPDATE instances i SET plural_name = i.name || 's'
WHERE i.plural_name IS NULL
  AND NOT EXISTS (SELECT 1 FROM instances j WHERE j.name = i.name
                  AND j.uuid::text < i.uuid::text);
