import json
from abc import ABC, abstractmethod

from domain_app.dto import StudentRow
from domain_app.exceptions import InvalidStudentDataError
from domain_app.protocols import Formatter, Parser, Validator
from domain_app.value_objects import LEVEL_LABELS, Grade, GroupCode


def _text(row: StudentRow) -> str:
    level = LEVEL_LABELS[row.average.level]
    return f"{row.student_id}: {row.full_name}, {row.group}, {row.average} ({level})"


def _check(row: StudentRow) -> None:
    if row.student_id < 1 or not row.full_name.strip():
        raise InvalidStudentDataError(f"Некоректний рядок: {row}")


class BaseRowProcessor(ABC):
    def process(self, line: str) -> str:
        row = self.parse(line)
        self.validate(row)
        return self.format(row)

    @abstractmethod
    def parse(self, line: str) -> StudentRow: ...

    def validate(self, row: StudentRow) -> None:
        _check(row)

    def format(self, row: StudentRow) -> str:
        return _text(row)


class CsvRowProcessor(BaseRowProcessor):
    def parse(self, line: str) -> StudentRow:
        return CsvParser().parse(line)


class CsvParser:
    def parse(self, line: str) -> StudentRow:
        student_id, first_name, last_name, group, grade = line.strip().split(",")
        return StudentRow(
            int(student_id), f"{first_name} {last_name}", GroupCode(group), Grade.of(grade)
        )


class JsonParser:
    def parse(self, line: str) -> StudentRow:
        data = json.loads(line)
        return StudentRow(
            int(data["student_id"]),
            f"{data['first_name']} {data['last_name']}",
            GroupCode(data["group"]),
            Grade.of(data["average_grade"]),
        )


class RowValidator:
    def validate(self, row: StudentRow) -> None:
        _check(row)


class TextFormatter:
    def format(self, row: StudentRow) -> str:
        return _text(row)


class ShortFormatter:
    def format(self, row: StudentRow) -> str:
        return f"{row.group} #{row.student_id} {row.average}"


class RowProcessor:
    def __init__(self, parser: Parser, validator: Validator, formatter: Formatter) -> None:
        self._parser = parser
        self._validator = validator
        self._formatter = formatter

    def process(self, line: str) -> str:
        row = self._parser.parse(line)
        self._validator.validate(row)
        return self._formatter.format(row)
