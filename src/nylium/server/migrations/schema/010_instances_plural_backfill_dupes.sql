UPDATE instances SET plural_name = name || 's-' || substr(uuid::text, 1, 8)
WHERE plural_name IS NULL;
