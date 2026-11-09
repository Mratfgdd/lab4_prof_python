from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, ClassVar

from domain_app.exceptions import (
    DuplicateKeyError,
    InvalidStudentDataError,
    StudentNotFoundError,
)
from domain_app.policies import GradingPolicy
from domain_app.value_objects import CourseResult, Grade, GroupCode

SCHOLARSHIP_MINIMUM = Grade.of(82)


class AcademicRecord:
    def __init__(self, results: Iterable[CourseResult] = ()) -> None:
        self._results: dict[str, CourseResult] = {}
        for result in results:
            self.record(result)

    def record(self, result: CourseResult) -> None:
        self._results[result.subject] = result

    @property
    def results(self) -> tuple[CourseResult, ...]:
        return tuple(self._results.values())

    def average(self, policy: GradingPolicy) -> Grade | None:
        return policy.average(self._results.values())

    def __len__(self) -> int:
        return len(self._results)

    def __iter__(self) -> Iterator[CourseResult]:
        return iter(self._results.values())

    def __getitem__(self, subject: str) -> CourseResult:
        return self._results[subject]

    def __contains__(self, item: object) -> bool:
        if isinstance(item, CourseResult):
            return self._results.get(item.subject) == item
        return item in self._results

    def __repr__(self) -> str:
        return f"AcademicRecord(results={len(self)})"


def _check_person(first_name: str, last_name: str, email: str) -> None:
    if not first_name.strip() or not last_name.strip():
        raise InvalidStudentDataError("Ім'я та прізвище не можуть бути порожніми")
    if "@" not in email:
        raise InvalidStudentDataError(f"Некоректний email: {email!r}")


@dataclass(eq=False, slots=True)
class Student:
    id: int
    first_name: str
    last_name: str
    email: str
    group: GroupCode
    record: AcademicRecord = field(default_factory=AcademicRecord)
    funding: ClassVar[str] = "none"

    def __post_init__(self) -> None:
        if self.id <= 0:
            raise InvalidStudentDataError("id студента має бути додатним")
        _check_person(self.first_name, self.last_name, self.email)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def edit(
        self,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ) -> None:
        new_first = self.first_name if first_name is None else first_name
        new_last = self.last_name if last_name is None else last_name
        new_email = self.email if email is None else email
        _check_person(new_first, new_last, new_email)
        self.first_name, self.last_name, self.email = new_first, new_last, new_email

    def average(self, policy: GradingPolicy) -> Grade | None:
        return self.record.average(policy)

    def has_scholarship(self, policy: GradingPolicy) -> bool:
        return False

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Student) and other.id == self.id

    def __hash__(self) -> int:
        return hash(self.id)

    def __str__(self) -> str:
        return f"{self.id:>2} {self.full_name} ({self.group}, {self.funding})"


@dataclass(eq=False, slots=True)
class BudgetStudent(Student):
    funding: ClassVar[str] = "budget"

    def has_scholarship(self, policy: GradingPolicy) -> bool:
        average = self.average(policy)
        return average is not None and average >= SCHOLARSHIP_MINIMUM


@dataclass(eq=False, slots=True)
class ContractStudent(Student):
    funding: ClassVar[str] = "contract"


STUDENT_KINDS: dict[str, type[Student]] = {
    BudgetStudent.funding: BudgetStudent,
    ContractStudent.funding: ContractStudent,
}


def create_student(kind: str, **fields: Any) -> Student:
    try:
        student_class = STUDENT_KINDS[kind]
    except KeyError:
        raise ValueError(f"Невідомий вид студента: {kind!r}") from None
    return student_class(**fields)


class Group:
    def __init__(self, code: GroupCode, curator: str = "") -> None:
        self._code = code
        self._curator = curator
        self._members: dict[int, Student] = {}

    @property
    def code(self) -> GroupCode:
        return self._code

    @property
    def curator(self) -> str:
        return self._curator

    @property
    def members(self) -> tuple[Student, ...]:
        return tuple(self._members.values())

    def add(self, student: Student) -> None:
        if student.id in self._members:
            raise DuplicateKeyError(f"Студент {student.id} уже є в групі {self._code}")
        self._members[student.id] = student
        student.group = self._code

    def remove(self, student_id: int) -> Student:
        try:
            return self._members.pop(student_id)
        except KeyError:
            raise StudentNotFoundError(
                f"Студента {student_id} немає в групі {self._code}"
            ) from None

    def average(self, policy: GradingPolicy) -> Grade | None:
        averages = [a for a in (s.average(policy) for s in self) if a is not None]
        if not averages:
            return None
        return Grade(sum((a.value for a in averages), Decimal(0)) / len(averages))

    def best(self, policy: GradingPolicy) -> Student | None:
        ranked = [(s, a) for s in self if (a := s.average(policy)) is not None]
        if not ranked:
            return None
        return max(ranked, key=lambda pair: pair[1])[0]

    def __len__(self) -> int:
        return len(self._members)

    def __iter__(self) -> Iterator[Student]:
        return iter(self._members.values())

    def __contains__(self, item: object) -> bool:
        if isinstance(item, Student):
            return item.id in self._members
        return item in self._members

    def __repr__(self) -> str:
        return f"Group(code={self._code.value!r}, students={len(self)})"
