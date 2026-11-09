from domain_app.models import BudgetStudent, Group, Student
from domain_app.policies import GradingPolicy, SimpleAverage
from domain_app.repositories import InMemoryRepository
from domain_app.value_objects import Grade, GroupCode

student_id: int = 1


def total() -> int:
    return 100


groups = InMemoryRepository[GroupCode, Group](key=lambda group: group.code)
groups.add(Group(GroupCode("PI-21")))

student = BudgetStudent(student_id, "Анна", "Коваль", "anna@example.com", GroupCode("PI-21"))
student.edit(first_name="Ганна")
grade = Grade.of("91.5")
policy: GradingPolicy = SimpleAverage()
students = InMemoryRepository[int, Student](key=lambda s: s.id)

if __name__ == "__main__":
    print(total(), student.full_name, grade, policy.name, len(groups), len(students), sep="\n")
