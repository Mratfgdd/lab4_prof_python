import unittest
from dataclasses import FrozenInstanceError
from decimal import Decimal
from typing import Any

from domain_app.exceptions import (
    DuplicateKeyError,
    GroupNotFoundError,
    InvalidGradeError,
    InvalidGroupCodeError,
    InvalidStudentDataError,
    StudentError,
    StudentNotFoundError,
)
from domain_app.models import (
    AcademicRecord,
    BudgetStudent,
    ContractStudent,
    Group,
    Student,
    create_student,
)
from domain_app.policies import (
    BestResultsAverage,
    CreditWeightedAverage,
    GradingPolicy,
    SimpleAverage,
)
from domain_app.registry import StudentRegistry
from domain_app.repositories import InMemoryRepository
from domain_app.value_objects import CourseResult, Grade, GroupCode

PI21 = GroupCode("PI-21")
PI22 = GroupCode("PI-22")
FLOAT_VALUE: Any = 91.5
ABSTRACT_POLICY: Any = GradingPolicy


def assign(target: object, name: str, value: object) -> None:
    setattr(target, name, value)


def result(subject: str, grade: str, credits: int = 3) -> CourseResult:
    return CourseResult(subject, Grade.of(grade), credits)


def anna_record() -> AcademicRecord:
    return AcademicRecord(
        [
            result("Математика", "90", 5),
            result("Програмування", "95", 6),
            result("Англійська", "89.5"),
        ]
    )


def budget(student_id: int, group: GroupCode = PI21, grades: tuple[str, ...] = ()) -> BudgetStudent:
    record = AcademicRecord(result(f"Предмет {i}", g) for i, g in enumerate(grades))
    return BudgetStudent(student_id, "Ім'я", f"Прізвище{student_id}", "a@b.ua", group, record)


def registry() -> StudentRegistry:
    return StudentRegistry(
        InMemoryRepository[int, Student](key=lambda student: student.id),
        InMemoryRepository[GroupCode, Group](key=lambda group: group.code),
    )


class GradeTests(unittest.TestCase):
    def test_rounding_half_up_and_str(self) -> None:
        self.assertEqual(Grade.of("91.555").value, Decimal("91.56"))
        self.assertEqual(str(Grade.of(90)), "90.00")

    def test_validation(self) -> None:
        for bad in ("-0.01", "100.01", "abc", "NaN", "Infinity"):
            with self.subTest(bad=bad), self.assertRaises(InvalidGradeError):
                Grade.of(bad)
        with self.assertRaises(TypeError):
            Grade.of(FLOAT_VALUE)
        self.assertEqual(Grade.of(0).value, Decimal("0.00"))
        self.assertEqual(Grade.of(100).value, Decimal("100.00"))

    def test_levels_at_boundaries(self) -> None:
        expected = {
            "100": "excellent",
            "90": "excellent",
            "89.99": "good",
            "75": "good",
            "74.99": "satisfactory",
            "60": "satisfactory",
            "59.99": "failing",
            "0": "failing",
        }
        for value, level in expected.items():
            self.assertEqual(Grade.of(value).level, level, value)

    def test_ordering_from_total_ordering(self) -> None:
        grades = [Grade.of("70"), Grade.of("95.2"), Grade.of("80")]
        self.assertEqual([str(g) for g in sorted(grades)], ["70.00", "80.00", "95.20"])
        self.assertTrue(Grade.of("90") >= Grade.of("90.00"))
        self.assertEqual(max(grades), Grade.of("95.2"))

    def test_immutable_and_hashable(self) -> None:
        grade = Grade.of("90")
        with self.assertRaises(FrozenInstanceError):
            assign(grade, "value", Decimal(1))
        self.assertEqual(len({Grade.of("90"), Grade.of("90.00")}), 1)


class GroupCodeAndResultTests(unittest.TestCase):
    def test_group_code_validation_and_order(self) -> None:
        self.assertEqual(str(GroupCode("PI-21")), "PI-21")
        for bad in ("PI-2", "pi-21", "PI21", "PI-211", ""):
            with self.subTest(bad=bad), self.assertRaises(InvalidGroupCodeError):
                GroupCode(bad)
        self.assertLess(GroupCode("PI-21"), GroupCode("PI-22"))

    def test_course_result_validation(self) -> None:
        for subject, credits in ((" ", 3), ("Фізика", 0), ("Фізика", 31)):
            with self.subTest(credits=credits), self.assertRaises(InvalidStudentDataError):
                CourseResult(subject, Grade.of(80), credits)
        self.assertIn("Фізика: 80.00", str(CourseResult("Фізика", Grade.of(80))))


class PolicyTests(unittest.TestCase):
    def test_policies_on_known_data(self) -> None:
        record = anna_record()
        self.assertEqual(str(record.average(SimpleAverage())), "91.50")
        self.assertEqual(str(record.average(CreditWeightedAverage())), "92.04")
        self.assertEqual(str(record.average(BestResultsAverage(2))), "92.50")
        self.assertEqual(str(record.average(BestResultsAverage(10))), "91.50")

    def test_empty_record_has_no_average(self) -> None:
        for policy in (SimpleAverage(), CreditWeightedAverage(), BestResultsAverage()):
            self.assertIsNone(AcademicRecord().average(policy))

    def test_factory_and_registry(self) -> None:
        self.assertEqual(set(GradingPolicy.available()), {"simple", "weighted", "best"})
        self.assertIsInstance(GradingPolicy.create("weighted"), CreditWeightedAverage)
        self.assertEqual(GradingPolicy.create("best", best=1).average(anna_record()), Grade.of(95))
        with self.assertRaises(ValueError):
            GradingPolicy.create("median")
        with self.assertRaises(ValueError):
            BestResultsAverage(0)

    def test_policy_is_abstract(self) -> None:
        with self.assertRaises(TypeError):
            ABSTRACT_POLICY()


class AcademicRecordTests(unittest.TestCase):
    def test_retake_replaces_result_of_same_subject(self) -> None:
        record = anna_record()
        record.record(result("Математика", "70", 5))
        self.assertEqual(len(record), 3)
        self.assertEqual(record["Математика"].grade, Grade.of(70))

    def test_collection_protocol(self) -> None:
        record = anna_record()
        first = record["Математика"]
        self.assertEqual(len(record), 3)
        self.assertEqual([r.subject for r in record][0], "Математика")
        self.assertIn("Математика", record)
        self.assertIn(first, record)
        self.assertNotIn(result("Математика", "1", 5), record)
        self.assertNotIn("Фізика", record)
        with self.assertRaises(KeyError):
            record["Фізика"]
        self.assertEqual(repr(record), "AcademicRecord(results=3)")

    def test_results_is_snapshot(self) -> None:
        record = anna_record()
        snapshot = record.results
        record.record(result("Фізика", "80"))
        self.assertEqual(len(snapshot), 3)
        self.assertEqual(len(record.results), 4)


class StudentTests(unittest.TestCase):
    def test_validation(self) -> None:
        for args in (
            (0, "А", "Б", "a@b"),
            (1, " ", "Б", "a@b"),
            (1, "А", "", "a@b"),
            (1, "А", "Б", "no-at"),
        ):
            with self.subTest(args=args), self.assertRaises(InvalidStudentDataError):
                BudgetStudent(*args, PI21)

    def test_edit_is_atomic(self) -> None:
        student = budget(1)
        student.edit(first_name="Ганна", email="h@b.ua")
        self.assertEqual((student.first_name, student.email), ("Ганна", "h@b.ua"))
        with self.assertRaises(InvalidStudentDataError):
            student.edit(first_name="Нове", last_name=" ")
        self.assertEqual(student.first_name, "Ганна")

    def test_full_name_is_read_only_property(self) -> None:
        student = budget(1)
        self.assertEqual(student.full_name, "Ім'я Прізвище1")
        with self.assertRaises(AttributeError):
            assign(student, "full_name", "Інше")

    def test_entity_equality_by_id(self) -> None:
        a = budget(1)
        b = ContractStudent(1, "Інший", "Студент", "c@d.ua", PI22)
        self.assertEqual(a, b)
        self.assertEqual(len({a, b}), 1)
        self.assertNotEqual(a, budget(2))
        self.assertIn("budget", str(a))

    def test_scholarship_is_polymorphic(self) -> None:
        policy = SimpleAverage()
        self.assertTrue(budget(1, grades=("82", "82")).has_scholarship(policy))
        self.assertFalse(budget(2, grades=("81.99",)).has_scholarship(policy))
        self.assertFalse(budget(3).has_scholarship(policy))
        contract = ContractStudent(
            4, "А", "Б", "a@b.ua", PI21, AcademicRecord([result("М", "100")])
        )
        self.assertFalse(contract.has_scholarship(policy))

    def test_factory(self) -> None:
        fields = {"id": 1, "first_name": "А", "last_name": "Б", "email": "a@b.ua", "group": PI21}
        self.assertIsInstance(create_student("budget", **fields), BudgetStudent)
        self.assertIsInstance(create_student("contract", **fields), ContractStudent)
        with self.assertRaises(ValueError):
            create_student("exchange", **fields)

    def test_subclasses(self) -> None:
        self.assertTrue(issubclass(BudgetStudent, Student))
        self.assertEqual((BudgetStudent.funding, ContractStudent.funding), ("budget", "contract"))


class GroupTests(unittest.TestCase):
    def test_add_remove_and_dunder(self) -> None:
        group = Group(PI21)
        student = budget(1, PI22)
        group.add(student)
        self.assertEqual(student.group, PI21)
        self.assertEqual(len(group), 1)
        self.assertIn(student, group)
        self.assertIn(1, group)
        self.assertNotIn(2, group)
        self.assertEqual(list(group), [student])
        self.assertEqual(repr(group), "Group(code='PI-21', students=1)")
        with self.assertRaises(DuplicateKeyError):
            group.add(student)
        self.assertIs(group.remove(1), student)
        with self.assertRaises(StudentNotFoundError):
            group.remove(1)

    def test_members_is_snapshot(self) -> None:
        group = Group(PI21, curator="Іваненко")
        group.add(budget(1))
        members = group.members
        group.add(budget(2))
        self.assertEqual((len(members), len(group), group.curator), (1, 2, "Іваненко"))

    def test_average_and_best(self) -> None:
        group = Group(PI21)
        policy = SimpleAverage()
        self.assertIsNone(group.average(policy))
        self.assertIsNone(group.best(policy))
        group.add(budget(1, grades=("90", "80")))
        group.add(budget(2, grades=("70",)))
        group.add(budget(3))
        self.assertEqual(str(group.average(policy)), "77.50")
        best = group.best(policy)
        self.assertIsNotNone(best)
        self.assertEqual(best.id if best else 0, 1)


class RepositoryTests(unittest.TestCase):
    def test_generic_repository(self) -> None:
        repo = InMemoryRepository[int, Student](key=lambda student: student.id)
        student = budget(1)
        repo.add(student)
        self.assertIs(repo.get(1), student)
        self.assertIs(repo[1], student)
        self.assertIn(1, repo)
        self.assertEqual(len(repo), 1)
        self.assertEqual(repo.find(lambda s: s.email.endswith("b.ua")), [student])
        self.assertEqual(repr(repo), "InMemoryRepository(size=1)")
        with self.assertRaises(DuplicateKeyError):
            repo.add(student)
        self.assertTrue(repo.remove(1))
        self.assertFalse(repo.remove(1))
        self.assertIsNone(repo.get(1))

    def test_group_code_keys(self) -> None:
        repo = InMemoryRepository[GroupCode, Group](key=lambda group: group.code)
        repo.add(Group(PI21))
        self.assertIn(PI21, repo)
        self.assertIsNone(repo.get(PI22))


class RegistryTests(unittest.TestCase):
    def test_add_creates_group_and_rejects_duplicates(self) -> None:
        reg = registry()
        student = reg.add_student(budget(1))
        self.assertIs(reg.get(1), student)
        self.assertIn(student, reg.group("PI-21"))
        self.assertEqual((len(reg), 1 in reg, 2 in reg), (1, True, False))
        with self.assertRaises(DuplicateKeyError):
            reg.add_student(budget(1, PI22))
        self.assertEqual(len(reg.groups()), 1)

    def test_lookup_errors(self) -> None:
        reg = registry()
        with self.assertRaises(StudentNotFoundError):
            reg.get(1)
        with self.assertRaises(GroupNotFoundError):
            reg.group("PI-21")
        with self.assertRaises(InvalidGroupCodeError):
            reg.group("PI-2")
        self.assertTrue(issubclass(StudentNotFoundError, StudentError))

    def test_search_by_last_name_ignores_case(self) -> None:
        reg = registry()
        reg.add_student(BudgetStudent(1, "Олег", "Мельник", "a@b.ua", PI21))
        reg.add_student(BudgetStudent(2, "Максим", "Мельник", "c@d.ua", PI22))
        reg.add_student(BudgetStudent(3, "Марія", "Бойко", "e@f.ua", PI22))
        self.assertEqual([s.id for s in reg.find_by_last_name("мЕЛЬНИК")], [1, 2])
        self.assertEqual(reg.find_by_last_name("Невідоме"), [])

    def test_edit_and_transfer(self) -> None:
        reg = registry()
        reg.add_student(budget(1))
        reg.edit_student(1, last_name="Нове")
        self.assertEqual(reg.get(1).last_name, "Нове")
        moved = reg.transfer(1, "PI-22")
        self.assertEqual(moved.group, PI22)
        self.assertEqual((len(reg.group("PI-21")), len(reg.group("PI-22"))), (0, 1))
        self.assertIs(reg.transfer(1, PI22), moved)
        self.assertEqual(len(reg.group("PI-22")), 1)

    def test_remove_student(self) -> None:
        reg = registry()
        reg.add_student(budget(1))
        reg.remove_student(1)
        self.assertEqual((len(reg), len(reg.group("PI-21"))), (0, 0))
        with self.assertRaises(StudentNotFoundError):
            reg.remove_student(1)

    def test_best_student_overall_and_in_group(self) -> None:
        reg = registry()
        reg.add_student(budget(1, PI21, ("70",)))
        reg.add_student(budget(2, PI22, ("90",)))
        reg.add_student(budget(3, PI22, ("80",)))
        reg.add_student(budget(4, PI22))
        policy = SimpleAverage()
        overall = reg.best_student(policy)
        in_group = reg.best_student(policy, PI21)
        self.assertEqual((overall.id if overall else 0, in_group.id if in_group else 0), (2, 1))
        self.assertIsNone(registry().best_student(policy))

    def test_bound_type_var_keeps_subclass(self) -> None:
        reg = registry()
        added: BudgetStudent = reg.add_student(budget(1))
        self.assertIsInstance(added, BudgetStudent)


if __name__ == "__main__":
    unittest.main()
