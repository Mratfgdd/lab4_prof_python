# Student Domain Model

Лабораторна робота №4 з дисципліни «Професійний Python»:
«Професійне ООП та система типів Python».
Варіант 1: система обліку студентів (продовження ЛР1-ЛР3).

## Опис

Типізована об'єктна модель: студенти, групи, академічні записи та оцінки.

- Domain objects: `Student` (підкласи `BudgetStudent`, `ContractStudent`), `Group`,
  `AcademicRecord`, `Grade`, `StudentRegistry`; value objects `Grade`, `GroupCode`, `CourseResult`.
- Додавання та редагування даних студента, пошук за прізвищем, ID і групою, обчислення
  середнього бала, визначення найкращого студента.
- Стратегії оцінювання (`GradingPolicy`, ABC): простий, зважений за кредитами та «найкращі N».
- Repository: `Repository[K, T]` (ABC, generic) і `InMemoryRepository`.
- Notification abstraction: `Notifier` (Protocol, runtime_checkable) з адаптерами.
- Application layer: `StudentService`, `ReportService`; dependency injection у composition root.
- TypedDict для зовнішніх payload; mypy `--strict`.

## Requirements

Python 3.11+. Для перевірок: `pip install -e ".[dev]"` (mypy, ruff, pytest).

## Installation

```
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

## Run

```
python -m domain_app.main
```

або console command `student-domain`.

## Checks

```
python tools/check.py
mypy experiments/type_errors.py
```

`tools/check.py` запускає ruff, `mypy --strict` і тести. Файл `experiments/type_errors.py`
містить навмисні помилки типів, `experiments/type_errors_fixed.py` - виправлену версію,
`experiments/di_comparison.py` - порівняння сервісу з жорсткою залежністю й DI.

## Tests

```
python -m unittest discover -s tests -v
```

## Project structure

```
src/domain_app/value_objects.py   Grade, GroupCode, CourseResult (frozen)
src/domain_app/policies.py        GradingPolicy (ABC) і три стратегії
src/domain_app/models.py          AcademicRecord, Student, Budget/ContractStudent, Group
src/domain_app/registry.py        StudentRegistry (aggregate root)
src/domain_app/repositories.py    Repository[K, T], InMemoryRepository
src/domain_app/protocols.py       Notifier, Parser, Validator, Formatter
src/domain_app/services.py        StudentService, ReportService
src/domain_app/dto.py             TypedDict і StudentRow
src/domain_app/processing.py      inheritance vs composition
src/domain_app/notifiers.py       ConsoleNotifier, MemoryNotifier
src/domain_app/main.py            демонстраційний сценарій
experiments/, tests/, tools/check.py
```

## Author

Student: Левандівський Назар
