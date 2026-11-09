from abc import ABC, abstractmethod
from collections.abc import Iterable
from decimal import Decimal
from typing import Any, ClassVar

from domain_app.value_objects import CourseResult, Grade


class GradingPolicy(ABC):
    name: ClassVar[str]
    _registry: ClassVar[dict[str, type["GradingPolicy"]]] = {}

    def __init_subclass__(cls, *, name: str, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        cls.name = name
        GradingPolicy._registry[name] = cls

    @classmethod
    def create(cls, name: str, **options: Any) -> "GradingPolicy":
        try:
            policy_class = cls._registry[name]
        except KeyError:
            raise ValueError(f"Невідома політика оцінювання: {name!r}") from None
        return policy_class(**options)

    @classmethod
    def available(cls) -> tuple[str, ...]:
        return tuple(cls._registry)

    @abstractmethod
    def average(self, results: Iterable[CourseResult]) -> Grade | None: ...


class SimpleAverage(GradingPolicy, name="simple"):
    def average(self, results: Iterable[CourseResult]) -> Grade | None:
        grades = [result.grade.value for result in results]
        if not grades:
            return None
        return Grade(sum(grades, Decimal(0)) / len(grades))


class CreditWeightedAverage(GradingPolicy, name="weighted"):
    def average(self, results: Iterable[CourseResult]) -> Grade | None:
        items = list(results)
        credits = sum(result.credits for result in items)
        if not credits:
            return None
        points = sum((result.grade.value * result.credits for result in items), Decimal(0))
        return Grade(points / credits)


class BestResultsAverage(GradingPolicy, name="best"):
    def __init__(self, best: int = 2) -> None:
        if best < 1:
            raise ValueError("Кількість найкращих оцінок має бути додатною")
        self._best = best

    def average(self, results: Iterable[CourseResult]) -> Grade | None:
        top = sorted((result.grade for result in results), reverse=True)[: self._best]
        if not top:
            return None
        return Grade(sum((grade.value for grade in top), Decimal(0)) / len(top))
