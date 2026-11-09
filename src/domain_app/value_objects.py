import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from functools import total_ordering
from typing import Self

from domain_app.exceptions import InvalidGradeError, InvalidGroupCodeError, InvalidStudentDataError

GROUP_CODE_PATTERN = re.compile(r"[A-Z]{2}-\d{2}")
HUNDREDTH = Decimal("0.01")
MAX_POINTS = Decimal(100)

LEVELS: tuple[tuple[Decimal, str], ...] = (
    (Decimal(90), "excellent"),
    (Decimal(75), "good"),
    (Decimal(60), "satisfactory"),
    (Decimal(0), "failing"),
)

LEVEL_LABELS: dict[str, str] = {
    "excellent": "відмінно",
    "good": "добре",
    "satisfactory": "задовільно",
    "failing": "незадовільно",
}


@total_ordering
@dataclass(frozen=True, slots=True)
class Grade:
    value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.value, Decimal):
            raise TypeError("value має бути Decimal; використовуйте Grade.of()")
        if not self.value.is_finite() or not 0 <= self.value <= MAX_POINTS:
            raise InvalidGradeError(f"Оцінка поза межами 0-100: {self.value}")
        object.__setattr__(self, "value", self.value.quantize(HUNDREDTH, ROUND_HALF_UP))

    @classmethod
    def of(cls, value: Decimal | int | str) -> Self:
        if isinstance(value, float):
            raise TypeError("float не підходить для оцінок: використовуйте str або Decimal")
        try:
            return cls(Decimal(value))
        except InvalidOperation:
            raise InvalidGradeError(f"Оцінка не є числом: {value!r}") from None

    @property
    def level(self) -> str:
        return next(label for threshold, label in LEVELS if self.value >= threshold)

    def __lt__(self, other: "Grade") -> bool:
        return self.value < other.value

    def __str__(self) -> str:
        return f"{self.value:.2f}"


@dataclass(frozen=True, slots=True, order=True)
class GroupCode:
    value: str

    def __post_init__(self) -> None:
        if not GROUP_CODE_PATTERN.fullmatch(self.value):
            raise InvalidGroupCodeError(f"Некоректний код групи: {self.value!r}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class CourseResult:
    subject: str
    grade: Grade
    credits: int = 3

    def __post_init__(self) -> None:
        if not self.subject.strip():
            raise InvalidStudentDataError("Назва предмета не може бути порожньою")
        if not 1 <= self.credits <= 30:
            raise InvalidStudentDataError(f"Кількість кредитів поза межами 1-30: {self.credits}")

    def __str__(self) -> str:
        return f"{self.subject}: {self.grade} ({self.credits} кр.)"
