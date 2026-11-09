import contextlib
import io

from domain_app.main import build_registry, build_services
from domain_app.models import BudgetStudent, Student
from domain_app.notifiers import ConsoleNotifier, MemoryNotifier
from domain_app.policies import SimpleAverage
from domain_app.registry import StudentRegistry
from domain_app.value_objects import GroupCode


def make_student() -> BudgetStudent:
    return BudgetStudent(1, "Анна", "Коваль", "anna@example.com", GroupCode("PI-21"))


class HardwiredStudentService:
    def __init__(self) -> None:
        self._registry: StudentRegistry = build_registry()
        self._notifier = ConsoleNotifier()

    def register(self, student: Student) -> None:
        self._registry.add_student(student)
        self._notifier.send(student.email, f"{student.full_name}: вас зараховано")


def verify_variant_a() -> str:
    service = HardwiredStudentService()
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        service.register(make_student())
    return buffer.getvalue().strip()


def verify_variant_b() -> list[tuple[str, str]]:
    notifier = MemoryNotifier()
    service, _ = build_services(build_registry(), notifier, SimpleAverage())
    service.register(make_student())
    return notifier.messages


if __name__ == "__main__":
    print("A (hardwired):", verify_variant_a())
    print("B (DI):       ", verify_variant_b())
