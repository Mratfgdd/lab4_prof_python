from collections.abc import Callable

from domain_app.dto import ResultPayload, StudentPayload
from domain_app.exceptions import StudentError
from domain_app.models import BudgetStudent, ContractStudent, Group, Student
from domain_app.notifiers import ConsoleNotifier, MemoryNotifier
from domain_app.policies import GradingPolicy, SimpleAverage
from domain_app.processing import (
    CsvParser,
    CsvRowProcessor,
    JsonParser,
    RowProcessor,
    RowValidator,
    ShortFormatter,
    TextFormatter,
)
from domain_app.protocols import Notifier
from domain_app.registry import StudentRegistry
from domain_app.repositories import InMemoryRepository
from domain_app.services import ReportService, StudentService
from domain_app.value_objects import LEVEL_LABELS, Grade, GroupCode

SUBJECTS: tuple[tuple[str, int], ...] = (("Математика", 5), ("Програмування", 6), ("Англійська", 3))

DEMO_ROWS: tuple[tuple[int, str, str, str, str, tuple[str, str, str]], ...] = (
    (1, "Анна", "Коваль", "PI-21", "budget", ("90", "95", "89.5")),
    (2, "Олег", "Мельник", "PI-21", "contract", ("80", "88", "84")),
    (3, "Ірина", "Бондар", "PI-22", "budget", ("94", "98", "93.6")),
    (4, "Андрій", "Шевченко", "PI-21", "budget", ("85", "92", "89.1")),
    (5, "Марія", "Бойко", "PI-22", "contract", ("75", "82", "80.9")),
    (6, "Тарас", "Гриценко", "PI-23", "budget", ("70", "75", "72.2")),
    (7, "Софія", "Гнатюк", "PI-22", "budget", ("60", "72", "68.4")),
    (8, "Дмитро", "Ткаченко", "PI-23", "contract", ("55", "62", "59.7")),
    (9, "Катерина", "Лисенко", "PI-23", "budget", ("92", "95", "92.3")),
    (10, "Максим", "Мельник", "PI-21", "contract", ("65", "76", "70.8")),
)


def build_registry() -> StudentRegistry:
    students = InMemoryRepository[int, Student](key=lambda student: student.id)
    groups = InMemoryRepository[GroupCode, Group](key=lambda group: group.code)
    return StudentRegistry(students, groups)


def build_services(
    registry: StudentRegistry, notifier: Notifier, policy: GradingPolicy
) -> tuple[StudentService, ReportService]:
    return StudentService(registry, notifier, policy), ReportService(registry, policy)


def demo_payloads() -> list[StudentPayload]:
    payloads: list[StudentPayload] = []
    for student_id, first_name, last_name, group, kind, grades in DEMO_ROWS:
        results: list[ResultPayload] = [
            {"subject": subject, "grade": grade, "credits": credits}
            for (subject, credits), grade in zip(SUBJECTS, grades, strict=True)
        ]
        payloads.append(
            {
                "id": student_id,
                "first_name": first_name,
                "last_name": last_name,
                "email": f"student{student_id}@lnu.edu.ua",
                "group": group,
                "kind": "budget" if kind == "budget" else "contract",
                "results": results,
            }
        )
    return payloads


def load_demo_data(registry: StudentRegistry) -> MemoryNotifier:
    quiet = MemoryNotifier()
    loader, _ = build_services(registry, quiet, SimpleAverage())
    *payloads, last = demo_payloads()
    for payload in payloads:
        loader.register_from_payload(payload)
    student = loader.register(
        ContractStudent(
            id=last["id"],
            first_name=last["first_name"],
            last_name=last["last_name"],
            email=last["email"],
            group=GroupCode(last["group"]),
        )
    )
    for result in last.get("results", []):
        loader.post_result(student.id, result["subject"], result["grade"], result.get("credits", 3))
    return quiet


def show_loading(registry: StudentRegistry, quiet: MemoryNotifier) -> None:
    print(
        f"\nЗавантажено {len(registry)} студентів у {len(registry.groups())} групах; "
        f"повідомлень у MemoryNotifier: {len(quiet.messages)}"
    )
    print(f"isinstance(ConsoleNotifier(), Notifier) = {isinstance(ConsoleNotifier(), Notifier)}")
    print(f"Політики оцінювання (фабрика GradingPolicy.create): {GradingPolicy.available()}")


def show_search(service: StudentService) -> None:
    print("\nПошук:")
    print(f"  за ID 3: {service.find_by_id(3)}")
    print(
        f"  за прізвищем 'мельник': {[s.full_name for s in service.find_by_last_name('мельник')]}"
    )
    print(f"  у групі PI-22: {[s.full_name for s in service.find_in_group('PI-22')]}")


def show_averages(registry: StudentRegistry) -> None:
    print("\nСередній бал Анни Коваль за різними політиками (strategy):")
    anna = registry.get(1)
    for name in GradingPolicy.available():
        print(f"  {name:9} -> {anna.average(GradingPolicy.create(name))}")
    simple, weighted = SimpleAverage(), GradingPolicy.create("weighted")
    for label, policy in (("simple", simple), ("weighted", weighted)):
        best = registry.best_student(policy)
        in_group = registry.best_student(policy, "PI-23")
        print(
            f"  найкращий студент ({label}): {best.full_name if best else '-'}; "
            f"у групі PI-23: {in_group.full_name if in_group else '-'}"
        )


def show_polymorphism(registry: StudentRegistry, reports: ReportService) -> None:
    print("\nСтипендія (поліморфний has_scholarship, поріг для BudgetStudent - 82):")
    holders = reports.scholarship_holders()
    print(f"  {[s.full_name for s in holders]}")
    kinds = {type(s).__name__ for s in registry}
    print(
        f"  види студентів: {sorted(kinds)}; BudgetStudent - підклас Student: "
        f"{issubclass(BudgetStudent, Student)}"
    )


def show_changes(service: StudentService, registry: StudentRegistry) -> None:
    print("\nРедагування, переведення та перездача (повідомлення йдуть у ConsoleNotifier):")
    service.edit(2, email="oleh.melnyk@lnu.edu.ua")
    service.transfer(10, "PI-22")
    service.post_result(8, "Математика", "70", credits=5)
    sizes = {group.code.value: len(group) for group in registry.groups()}
    print(f"  розміри груп після переведення: {sizes}")


def show_errors(service: StudentService) -> None:
    print("\nПомилки предметної області:")
    duplicate = BudgetStudent(1, "Анна", "Дубль", "dup@lnu.edu.ua", GroupCode("PI-21"))
    attempts: tuple[tuple[str, Callable[[], object]], ...] = (
        ("оцінка 105", lambda: service.post_result(1, "Фізика", "105")),
        ("оцінка 'abc'", lambda: service.post_result(1, "Фізика", "abc")),
        ("невідомий студент 99", lambda: service.find_by_id(99)),
        ("дубль id 1", lambda: service.register(duplicate)),
        ("код групи PI-2", lambda: service.find_in_group("PI-2")),
        ("порожнє ім'я", lambda: service.edit(1, first_name=" ")),
        ("група PI-99", lambda: service.find_in_group("PI-99")),
    )
    for label, action in attempts:
        try:
            action()
        except StudentError as error:
            print(f"  {label}: {type(error).__name__}: {error}")


def show_reports(registry: StudentRegistry, reports: ReportService) -> None:
    print("\nЗвіти (ReportService):")
    print("  summaries -> TypedDict:")
    for summary in reports.summaries()[:3]:
        print(f"    {summary}")
    ranking = ", ".join(f"{s.last_name} {a}" for s, a in reports.ranking()[:4])
    print(f"  топ-4: {ranking}")
    for item in reports.group_report():
        print(f"  {item}")
    print(reports.card(registry.get(3)))


def show_dunder(registry: StudentRegistry) -> None:
    student = registry.get(3)
    record = student.record
    print("\nDunder methods:")
    print(
        f"  repr(record)={record!r}, len={len(record)}, 'Математика' in record: "
        f"{'Математика' in record}, record['Математика'] -> {record['Математика']}"
    )
    print(
        f"  Grade: max(...)={max(Grade.of('91.5'), Grade.of('95.2'))}, "
        f"Grade.of('90') >= Grade.of('89.99'): {Grade.of('90') >= Grade.of('89.99')}"
    )
    print(f"  Group: {registry.group('PI-22')!r}, 3 in group: {3 in registry.group('PI-22')}")
    average = student.average(SimpleAverage())
    level = LEVEL_LABELS[average.level] if average is not None else "-"
    print(
        f"  Student: == за id: {student == registry.get(3)}, "
        f"hash збігається: {hash(student) == hash(registry.get(3))}, рівень: {level}"
    )


def compare_processing() -> None:
    print("\nInheritance vs composition (рядок із ЛР3):")
    csv_line = "3,Ірина,Бондар,PI-22,95.2"
    json_line = (
        '{"student_id": 12, "first_name": "Оксана", "last_name": "Мороз", '
        '"group": "PI-24", "average_grade": "97"}'
    )
    print(f"  inheritance (CsvRowProcessor): {CsvRowProcessor().process(csv_line)}")
    validator = RowValidator()
    for parser, line in ((CsvParser(), csv_line), (JsonParser(), json_line)):
        for formatter in (TextFormatter(), ShortFormatter()):
            processor = RowProcessor(parser, validator, formatter)
            print(
                f"  composition {type(parser).__name__:10} + {type(formatter).__name__:14}: "
                f"{processor.process(line)}"
            )


def main() -> None:
    print("ЛР4, варіант 1: система обліку студентів")
    registry = build_registry()
    quiet = load_demo_data(registry)
    show_loading(registry, quiet)
    service, reports = build_services(registry, ConsoleNotifier(), SimpleAverage())
    show_search(service)
    show_averages(registry)
    show_polymorphism(registry, reports)
    show_changes(service, registry)
    show_errors(service)
    show_reports(registry, reports)
    show_dunder(registry)
    compare_processing()


if __name__ == "__main__":
    main()
