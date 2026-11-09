from domain_app.models import BudgetStudent, Group, Student
from domain_app.policies import GradingPolicy
from domain_app.repositories import InMemoryRepository
from domain_app.value_objects import Grade, GroupCode

student_id: int = "1"


def total() -> int:
    return "100"


repository = InMemoryRepository[int, Student](key=lambda student: student.id)
repository.add(Group(GroupCode("PI-21")))

student = BudgetStudent(1, "Анна", "Коваль", "anna@example.com", GroupCode("PI-21"))
student.full_name = "Хтось інший"
grade = Grade.of(91.5)
policy = GradingPolicy()
by_name = InMemoryRepository[str, Student](key=lambda s: s.last_name)
