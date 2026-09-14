# ADR-0019: SQL только в `tables/`

- Status: Accepted
- Date: 2026-09-14

## Context

Директива: все манипуляции с SQL — только в `tables/`; таблицы
образуют слой абстракции между SQL и остальным кодом. До этого
решения `objects/` (wobject, warray, wembedded, wenum, wunit, wfile,
wprop, wtype, wtypemeta, wfunction) сам исполнял `sqla`-стейтменты
через `Database.session` — знание о схеме расползалось по двум слоям.

## Decision

1. **`tables/` — единственный слой, знающий про SQLAlchemy и
   `Database.session`.** Statement helpers — модульные функции
   `@databasemethod(commit=False)` рядом с соответствующей `TABLE_*`:
   `values/cells.py` (generic scalar store для девяти `*values`),
   link/file-ref helpers в `instance_values.py` / `file_values.py`,
   row helpers (`get`/`delete_row`/`touch`/`owned_uuids`) в
   `objects/instances.py`, membership cleanup в `array_values.py`.
2. **Разделение ответственности:** `objects/` решает *что* хранить
   (семантика, валидация, dispatch по видам пропов), `tables/` решает
   *как* (statements). Направление зависимости строго
   `objects → tables`: константы уровня объектов (`ARRAY_TYPE_PREFIX`)
   не текут вниз, при необходимости дублируются с комментарием.
3. **Поведение verbatim:** семантика write/delete/touch не меняется,
   переносятся только statements (порядок cleanup в `delete()`,
   touch только при реальном удалении и т.п.).
4. **Поэтапно:** фаза A — пакет `objects/wobject/` (миксины без
   `sqla`/`Database`), фазы B–D — остальные объектные модули по
   результатам аудита прямых обращений к `Database`/`sqla` вне `tables/`.

## Consequences

- Импорт-шаблон для helpers — полный путь:
  `from nylium.tables.objects.instances import touch`. Пакетные
  `__init__` реэкспортируют синглтоны (`instances = Instances()`),
  которые **затеняют одноимённые сабмодули** при `from package import
  name` — `from nylium.tables.objects import instances` вернёт
  синглтон, а не модуль.
- Приватные хелперы объектного слоя (`_touch`, `_owned_*`) остаются
  тонкими обёртками над tables-функциями — граница коммита
  (`commit=True`) живёт на публичных операциях объектного слоя.
