# ADR-0030: таблицы без функций — `tables/` хранит только таблицы, значение-логика в `scalars/`

- Status: Proposed
- Date: 2026-09-20

## Context

`nylium/tables/` содержит таблицы `TABLE_*` вперемешку с глобальными
функциями-хелперами в тех же файлах. Это ломает ADR-0019 (в `tables/`
должны жить только операторы SQL, но теперь рядом с ними лежит и
бизнес-логика), и размывает границу «что хранить» против «как хранить».

Отдельная боль: скалярные типы (`int`, `str`, `Decimal`, `datetime`,
`date`, `time`, `MonthDay`, `MonthDayTime`, `Color`) не имеют своих
объектов-обёрток. Их чтение/запись размазаны по глобальным функциям
(`cells.read/write/clear`, `numeric_values.read_with_unit/write_with_unit`),
а объектный слой дёргает их по имени модуля, а не через тип значения.

Плюс недавний сплит ADR-0019-фазы (`70d078a`) разнёс доменные таблицы в
`objects/tables`, а Row-снимки в `objects/rows` — это оставило `tables/`
неполным и породило мягкий цикл импортов (Table-стор возвращает Row,
Row навигирует через сторы).

## Decision

1. **`nylium/scalars/` — новый пакет для wrapper-классов скаляров.**
   Один класс на скалярный вид значения: `String`, `Integer`, `Numeric`,
   `Boolean`, `Datetime`, `Date`, `Time`, `MonthDay`, `MonthDayTime`,
   `Color`. Каждый оборачивает python-значение и владеет методами
   `read(inst_uuid, prop_uuid)` / `write(...)` / `clear(...)`;
   `Numeric` дополнительно — `read_with_unit` / `write_with_unit`.
   Глобальные функции `cells.*` и `numeric_values.read/write_with_unit`
   становятся методами этих классов.

2. **`nylium/tables/` — только табличный слой.** Никаких глобальных
   функций. Сюда возвращаются: все `TABLE_*` (доменные — из
   `objects/tables`), Table-сторы (классы `Table` + синглтоны
   `types`/`instances`/`props`/…), и Row-снимки (из `objects/rows`) —
   иначе стор и Row тянут друг друга через границу пакета. Функции,
   что жили в файлах таблиц, переносятся в обёртки по смыслу (скаляры —
   в `scalars/`, остальное — в объектный слой или в методы сторов).

3. **`nylium/objects/`** остаётся слоем W-фасадов (`WObject`, `WProp`,
   `WType`, `WArray`, `WEmbedded`, `WEnum`, `WUnit`, `WFile`,
   `WFunction`). Он потребляет `scalars/` для значений и `tables/`
   только через сторы/Row, не через функции.

4. **Семантика verbatim:** read/write/clear/with_unit переносятся как
   есть, поведение коммитов (`use_same_session` / `commit_after_this`)
   не меняется. Это механический перенос, не перепроектирование.

## Consequences

- `WScalar`-маркеры (в `objects/wscalar.py`) и новые `scalars/`-обёртки
  связаны, но не сливаются: маркер аннотирует проп, обёртка — держит
  значение и умеет его читать/писать. Связь фиксируется маппингом
  `WScalar.TABLE ↔ scalars-класс`.
- Импорт-поверхность `nylium.tables` остаётся плоской для `TABLE_*` и
  сторов; функции оттуда исчезают — вызовы вида
  `from nylium.tables.values import cells` переезжают на
  `from nylium.scalars import Integer` и т.п.
- Поэтапно: фаза A — пакет `scalars/` + методы; фаза B — перенос
  доменных таблиц/сторов/Row обратно в `tables/`; фаза C — чистка
  оставшихся функций (auth/decor/files/schema) из файлов таблиц.
