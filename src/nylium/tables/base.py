# The single ORM registry for every TABLE_* mapped class. Singleton module
# attribute, same shape as Database.engine: import `reg` and decorate with
# `@reg.mapped` — no Base subclassing, no per-class registry wiring.
from sqlalchemy.orm import registry

reg = registry()
