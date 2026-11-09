from collections.abc import Iterable, Iterator
from typing import TypeVar

from domain_app.exceptions import DuplicateKeyError, GroupNotFoundError, StudentNotFoundError
from domain_app.models import Group, Student
from domain_app.policies import GradingPolicy
from domain_app.repositories import Repository
from domain_app.value_objects import Grade, GroupCode

S = TypeVar("S", bound=Student)


class StudentRegistry:
    def __init__(
        self,
        students: Repository[int, Student],
        groups: Repository[GroupCode, Group],
    ) -> None:
        self._students = students
        self._groups = groups

    def add_student(self, student: S) -> S:
        if self._students.get(student.id) is not None:
            raise DuplicateKeyError(f"Студент із id {student.id} уже зареєстрований")
        self._group_or_create(student.group).add(student)
        self._students.add(student)
        return student

    def get(self, student_id: int) -> Student:
        student = self._students.get(student_id)
        if student is None:
            raise StudentNotFoundError(f"Студента {student_id} не знайдено")
        return student

    def group(self, code: str | GroupCode) -> Group:
        key = code if isinstance(code, GroupCode) else GroupCode(code)
        group = self._groups.get(key)
        if group is None:
            raise GroupNotFoundError(f"Групу {key} не знайдено")
        return group

    def groups(self) -> list[Group]:
        return sorted(self._groups, key=lambda group: group.code)

    def find_by_last_name(self, last_name: str) -> list[Student]:
        wanted = last_name.casefold()
        return self._students.find(lambda student: student.last_name.casefold() == wanted)

    def edit_student(
        self,
        student_id: int,
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ) -> Student:
        student = self.get(student_id)
        student.edit(first_name=first_name, last_name=last_name, email=email)
        return student

    def transfer(self, student_id: int, code: str | GroupCode) -> Student:
        student = self.get(student_id)
        target = self._group_or_create(code if isinstance(code, GroupCode) else GroupCode(code))
        if student in target:
            return student
        self.group(student.group).remove(student_id)
        target.add(student)
        return student

    def remove_student(self, student_id: int) -> Student:
        student = self.get(student_id)
        self.group(student.group).remove(student_id)
        self._students.remove(student_id)
        return student

    def best_student(
        self, policy: GradingPolicy, group: str | GroupCode | None = None
    ) -> Student | None:
        candidates: Iterable[Student] = self._students if group is None else self.group(group)
        ranked = [(s, a) for s in candidates if (a := s.average(policy)) is not None]
        if not ranked:
            return None
        return max(ranked, key=_by_average)[0]

    def __len__(self) -> int:
        return len(self._students)

    def __iter__(self) -> Iterator[Student]:
        return iter(self._students)

    def __contains__(self, student_id: object) -> bool:
        return isinstance(student_id, int) and self._students.get(student_id) is not None

    def _group_or_create(self, code: GroupCode) -> Group:
        group = self._groups.get(code)
        if group is None:
            group = Group(code)
            self._groups.add(group)
        return group


def _by_average(pair: tuple[Student, Grade]) -> Grade:
    return pair[1]
