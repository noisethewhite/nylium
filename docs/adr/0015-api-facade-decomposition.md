# ADR-0015: Декомпозиция фасада Api по доменам

- Status: Accepted
- Date: 2026-09-13

## Context

`api/api.py` вырос в монолит: один `class Api` на ~1400 строк — прямое
нарушение принципа ≤250 LOC на файл и «helpers have owners» (модульные
функции `_prop_value_type_name`, `_is_builtin_type` висят без владельца).
Фасад при этом — единая точка входа для server/routes/codec и CLI:
`Api.<method>` как classmethod-интерфейс.

## Decision

`Api` разделяется на доменные классы-примеси, по одному классу на файл
в пакете `nylium/api/`:

- `shared.py` — `ApiShared`: сквозные инварианты и нормализация
  (`_ensure_value_type`, `_resolve_value_spec`, `_normalize_props`,
  `_normalize_value`, `_check_color`, `_check_icon`, `_check_reserved_name`,
  `_type_result`, `_trait_result`, бывшие модульные `_prop_value_type_name`
  и `_is_builtin_type` — приватными методами класса).
- `types.py` — `TypesApi`: CRUD типов, rename, delete.
- `enums.py` — `EnumsApi`: create_enum, sync_enum_options.
- `units.py` — `UnitsApi`: create_unit, sync_unit_parts, валидация драфта.
- `schema.py` — `SchemaApi`: sync_props, reorder_props.
- `traits.py` — `TraitsApi`: CRUD трейтов, attach/detach.
- `objects.py` — `ObjectsApi`: CRUD объектов, export_markdown.
- `files.py` — `FilesApi`: CRUD файлов, storage_stats.
- `functions.py` — `FunctionsApi`: CRUD функций, set_prop_function,
  формульные переписывания.
- `api.py` — тонкий агрегатор: `class Api(...mixins)` + `PropInput`
  (реэкспорт — codec.py импортирует его отсюда).

Наследование вместо композиции: поверхность `Api.<method>` сохраняется
один-в-один, ни один call site в server/, auth/, cli не меняется. Код
переносится verbatim, включая декораторы `@databasemethod` — рефактор
не меняет семантику.

## Consequences

+ Каждый файл ≤250 LOC, владелец у каждого хелпера, доменная навигация
  по имени файла.
+ Новый домен = новый mixin-файл + одна строка в списке наследования.
− Десяток файлов вместо одного; порядок MRO значения не имеет
  (все методы classmethod, пересечений имён нет — это инвариант).
