from collections.abc import Iterable
from decimal import Decimal
from typing import TypeVar

from domain_app.dto import (
    GroupSummary,
    StudentPayload,
    StudentSummary,
    student_from_payload,
    to_summary,
)
from domain_app.models import Student
from domain_app.policies import GradingPolicy
from domain_app.protocols import Notifier
from domain_app.registry import StudentRegistry
from domain_app.value_objects import CourseResult, Grade, GroupCode

S = TypeVar("S", bound=Student)


class StudentService:
    def __init__(
        self,
        registry: StudentRegistry,
        notifier: Notifier,
        policy: GradingPolicy,
    ) -> None:
        self._registry = registry
        self._notifier = notifier
        self._policy = policy

    def register(self, student: S) -> S:
        self._registry.add_student(student)
        self._notify(student, f"вас зараховано до групи {student.group} ({student.funding})")
        return student

    def register_from_payload(self, payload: StudentPayload) -> Student:
        return self.register(student_from_payload(payload))

    def edit(
        self,
        student_id: int,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ) -> Student:
        student = self._registry.edit_student(
            student_id, first_name=first_name, last_name=last_name, email=email
        )
        self._notify(student, f"дані оновлено: {student.full_name}, {student.email}")
        return student

    def transfer(self, student_id: int, group: str | GroupCode) -> Student:
        student = self._registry.transfer(student_id, group)
        self._notify(student, f"вас переведено до групи {student.group}")
        return student

    def post_result(
        self, student_id: int, subject: str, grade: Grade | str, credits: int = 3
    ) -> CourseResult:
        student = self._registry.get(student_id)
        value = grade if isinstance(grade, Grade) else Grade.of(grade)
        result = CourseResult(subject, value, credits)
        student.record.record(result)
        self._notify(student, f"{subject}: {value}, середній бал {self._average_text(student)}")
        return result

    def find_by_id(self, student_id: int) -> Student:
        return self._registry.get(student_id)

    def find_by_last_name(self, last_name: str) -> list[Student]:
        return self._registry.find_by_last_name(last_name)

    def find_in_group(self, group: str | GroupCode) -> list[Student]:
        return list(self._registry.group(group).members)

    def average_of(self, student_id: int) -> Grade | None:
        return self._registry.get(student_id).average(self._policy)

    def best_student(self, group: str | GroupCode | None = None) -> Student | None:
        return self._registry.best_student(self._policy, group)

    def _average_text(self, student: Student) -> str:
        average = student.average(self._policy)
        return "-" if average is None else str(average)

    def _notify(self, student: Student, message: str) -> None:
        self._notifier.send(student.email, f"{student.full_name}: {message}")


class ReportService:
    def __init__(self, registry: StudentRegistry, policy: GradingPolicy) -> None:
        self._registry = registry
        self._policy = policy

    def summaries(self) -> list[StudentSummary]:
        return [to_summary(student, self._policy) for student in sorted(self._registry, key=_by_id)]

    def ranking(self, group: str | GroupCode | None = None) -> list[tuple[Student, Grade]]:
        students: Iterable[Student] = (
            self._registry if group is None else self._registry.group(group)
        )
        ranked = [(s, a) for s in students if (a := s.average(self._policy)) is not None]
        return sorted(ranked, key=_by_average, reverse=True)

    def group_report(self) -> list[GroupSummary]:
        report: list[GroupSummary] = []
        for group in self._registry.groups():
            average = group.average(self._policy)
            best = group.best(self._policy)
            report.append(
                {
                    "group": group.code.value,
                    "students": len(group),
                    "average": "-" if average is None else str(average),
                    "best": "-" if best is None else best.full_name,
                }
            )
        return report

    def scholarship_holders(self) -> list[Student]:
        return [s for s in sorted(self._registry, key=_by_id) if s.has_scholarship(self._policy)]

    def card(self, student: Student) -> str:
        average = student.average(self._policy)
        lines = [
            f"Картка: {student.full_name}, {student.group}, середній бал "
            f"{'-' if average is None else average}"
        ]
        lines += [f"  {result}" for result in student.record]
        return "\n".join(lines)


def _by_id(student: Student) -> int:
    return student.id


def _by_average(pair: tuple[Student, Grade]) -> Decimal:
    return pair[1].value
