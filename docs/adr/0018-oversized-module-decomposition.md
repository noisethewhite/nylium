# ADR-0018: Пакетная декомпозиция oversized-модулей

- Status: Accepted
- Date: 2026-09-14

## Context

После ADR-0015/0016/0017 в кодовой базе остались файлы за пределом
≤250 LOC: `server/bodies.py` (685), `objects/wfunction.py` (721),
`objects/wformula.py` (423), `api/views.py` (419), `objects/wobject.py`
(416). Дополнительно — коллизия имён `api/views.py` ↔ `server/views.py`:
два разных DTO-слоя с одинаковым именем модуля (grep/навигация путают).

`bodies.py` уже содержит доменные секции-комментарии и файловое
исключение из one-class-per-file — но исключение масштабировалось
плохо: 34 request-DTO восьми доменов в одном файле.

## Decision

1. **`server/bodies.py` → пакет `server/bodies/`** по существующим
   доменным секциям: `types.py`, `traits.py`, `objects.py`, `files.py`,
   `functions.py`. Общее (`_CONFIG`, `_Path`, разрешение forward
   references в route-сигнатурах) — в `shared.py`; каждый доменный
   модуль резолвит хинты своих классов на импорте. `__init__.py`
   реэкспортирует всю поверхность — `app.py` и прочие call sites
   (`bodies.<Name>`) не меняются.
2. **`objects/wformula.py` → пакет `objects/wformula/`** по фазам
   конвейера: `nodes.py` (AST + `FUNCTIONS`), `parsing.py` (токенизатор
   + recursive-descent), `formula.py` (публичный класс `Formula`:
   валидация/запросы), `evaluation.py` (fold по живым строкам),
   `rewriting.py` (канонический рендер + переименования). `__init__.py`
   реэкспортирует прежнюю поверхность. Цикл `_Parser` ↔ `Formula`
   разрывается переносом `FUNCTIONS` в `nodes.py`.
3. **`api/views.py` → `api/display.py`** — коллизия устранена на стороне
   API-слоя: `server/views.py` держит задокументированное исключение
   (один wire-контракт ответов), API-проекции получают имя по своей
   роли. Восемь import-site обновлены, поведение не меняется.
4. **`wfunction.py` и `wobject.py` осознанно не разделяются**: это по
   одному когезивному классу на файл (graph-engine и instance-lifecycle
   соответственно). Механический сплит одного класса по mixin-файлам
   ухудшает читаемость — поток логики класса разрывается между файлами.
   Лимит ≤250 LOC применим к модулям-агрегатам, а не к единственному
   классу; файлы получают docstring-обоснование по образцу
   `server/views.py`.
5. Семантика `W*`-слоя документируется в `objects/__init__.py` —
   раньше вычитывалась только из ADR.

## Consequences

+ Все модули-агрегаты ≤250 LOC; навигация по имени файла совпадает с
  доменом во всех слоях (api/, tables/, теперь server/bodies/ и
  objects/wformula/).
+ Ни один внешний import-path не сломан: пакеты сохраняют прежние
  точки входа через `__init__.py`.
− Механизм `_resolve_route_hints` из одного вызова превращается в
  вызов на доменный модуль — забыть его в новом модуле = неработающие
  route-hints. Страховка: тесты покрывают все routes end-to-end.
