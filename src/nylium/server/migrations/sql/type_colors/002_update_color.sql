-- ADR-0005: rewrite one legacy palette name to its hex value
UPDATE types SET color = :hex WHERE color = :name;
