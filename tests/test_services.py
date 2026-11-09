import contextlib
import io
import unittest

from domain_app.dto import (
    StudentPayload,
    result_from_payload,
    student_from_payload,
    to_summary,
)
from domain_app.exceptions import (
    DuplicateKeyError,
    InvalidGradeError,
    InvalidStudentDataError,
    StudentNotFoundError,
)
from domain_app.main import build_registry, build_services, load_demo_data, main
from domain_app.models import BudgetStudent, ContractStudent, Student
from domain_app.notifiers import ConsoleNotifier, MemoryNotifier
from domain_app.policies import CreditWeightedAverage, SimpleAverage
from domain_app.processing import (
    CsvParser,
    CsvRowProcessor,
    JsonParser,
    RowProcessor,
    RowValidator,
    ShortFormatter,
    TextFormatter,
)
from domain_app.protocols import Notifier
from domain_app.registry import StudentRegistry
from domain_app.repositories import Repository
from domain_app.services import ReportService, StudentService
from domain_app.value_objects import Grade, GroupCode

PAYLOAD: StudentPayload = {
    "id": 7,
    "first_name": "Софія",
    "last_name": "Гнатюк",
    "email": "sofiia@lnu.edu.ua",
    "group": "PI-22",
    "kind": "budget",
    "results": [
        {"subject": "Математика", "grade": "60", "credits": 5},
        {"subject": "Програмування", "grade": "72"},
    ],
}


def setup() -> tuple[StudentRegistry, MemoryNotifier, StudentService, ReportService]:
    reg = build_registry()
    notifier = MemoryNotifier()
    service, reports = build_services(reg, notifier, SimpleAverage())
    return reg, notifier, service, reports


class StudentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry, self.notifier, self.service, self.reports = setup()

    def test_register_notifies_and_keeps_subclass_type(self) -> None:
        student = BudgetStudent(1, "Анна", "Коваль", "anna@lnu.edu.ua", GroupCode("PI-21"))
        registered: BudgetStudent = self.service.register(student)
        self.assertIs(registered, student)
        self.assertEqual(self.notifier.messages[0][0], "anna@lnu.edu.ua")
        self.assertIn("PI-21 (budget)", self.notifier.messages[0][1])
        with self.assertRaises(DuplicateKeyError):
            self.service.register(student)
        self.assertEqual(len(self.notifier.messages), 1)

    def test_register_from_payload(self) -> None:
        student = self.service.register_from_payload(PAYLOAD)
        self.assertIsInstance(student, BudgetStudent)
        self.assertEqual(len(student.record), 2)
        self.assertEqual(self.service.find_by_id(7).full_name, "Софія Гнатюк")

    def test_edit_and_transfer_notify(self) -> None:
        self.service.register_from_payload(PAYLOAD)
        self.service.edit(7, email="new@lnu.edu.ua")
        self.service.transfer(7, "PI-23")
        self.assertEqual(self.notifier.messages[-2][0], "new@lnu.edu.ua")
        self.assertIn("PI-23", self.notifier.messages[-1][1])
        self.assertEqual([s.id for s in self.service.find_in_group("PI-23")], [7])
        with self.assertRaises(InvalidStudentDataError):
            self.service.edit(7, email="bad")

    def test_post_result_updates_average_and_retake(self) -> None:
        self.service.register_from_payload(PAYLOAD)
        self.assertEqual(str(self.service.average_of(7)), "66.00")
        self.service.post_result(7, "Математика", "80", 5)
        self.assertEqual(str(self.service.average_of(7)), "76.00")
        self.assertIn("Математика: 80.00", self.notifier.messages[-1][1])
        self.service.post_result(7, "Фізика", Grade.of(100))
        self.assertEqual(len(self.service.find_by_id(7).record), 3)

    def test_invalid_result_changes_nothing(self) -> None:
        self.service.register_from_payload(PAYLOAD)
        sent = len(self.notifier.messages)
        with self.assertRaises(InvalidGradeError):
            self.service.post_result(7, "Фізика", "101")
        self.assertEqual(
            (len(self.service.find_by_id(7).record), len(self.notifier.messages)), (2, sent)
        )
        with self.assertRaises(StudentNotFoundError):
            self.service.post_result(99, "Фізика", "90")

    def test_search_and_best_student(self) -> None:
        load_demo_data(self.registry)
        self.assertEqual([s.id for s in self.service.find_by_last_name("мельник")], [2, 10])
        best = self.service.best_student()
        self.assertEqual(best.id if best else 0, 3)
        in_group = self.service.best_student("PI-23")
        self.assertEqual(in_group.id if in_group else 0, 9)

    def test_average_without_results_is_none(self) -> None:
        self.service.register(ContractStudent(1, "А", "Б", "a@b.ua", GroupCode("PI-21")))
        self.assertIsNone(self.service.average_of(1))
        self.assertIsNone(self.service.best_student())


class ReportServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry, _, self.service, self.reports = setup()
        load_demo_data(self.registry)

    def test_summaries_are_typed_dicts_sorted_by_id(self) -> None:
        summaries = self.reports.summaries()
        self.assertEqual([s["id"] for s in summaries], list(range(1, 11)))
        self.assertEqual(summaries[2]["average"], "95.20")
        self.assertIsInstance(summaries[0], dict)

    def test_ranking_is_descending_and_filters_by_group(self) -> None:
        ranking = self.reports.ranking()
        self.assertEqual([s.id for s, _ in ranking][:4], [3, 9, 1, 4])
        grades = [grade for _, grade in ranking]
        self.assertEqual(grades, sorted(grades, reverse=True))
        self.assertEqual([s.id for s, _ in self.reports.ranking("PI-22")], [3, 5, 7])

    def test_group_report(self) -> None:
        report = {item["group"]: item for item in self.reports.group_report()}
        self.assertEqual(report["PI-21"]["students"], 4)
        self.assertEqual(report["PI-23"]["best"], "Катерина Лисенко")
        self.assertEqual(report["PI-22"]["average"], "80.43")

    def test_scholarship_holders_depend_on_funding_and_average(self) -> None:
        holders = [s.id for s in self.reports.scholarship_holders()]
        self.assertEqual(holders, [1, 3, 4, 9])
        weighted = ReportService(self.registry, CreditWeightedAverage())
        self.assertIn(1, [s.id for s in weighted.scholarship_holders()])

    def test_card_lists_results(self) -> None:
        card = self.reports.card(self.registry.get(3))
        self.assertIn("середній бал 95.20", card)
        self.assertEqual(card.count("\n"), 3)


class PayloadTests(unittest.TestCase):
    def test_typed_dict_round_trip(self) -> None:
        student = student_from_payload(PAYLOAD)
        self.assertIsInstance(student, BudgetStudent)
        summary = to_summary(student, SimpleAverage())
        self.assertEqual(summary["average"], "66.00")
        self.assertEqual((summary["kind"], summary["results"]), ("budget", 2))
        self.assertIsInstance(summary, dict)

    def test_default_credits_and_empty_results(self) -> None:
        self.assertEqual(result_from_payload({"subject": "М", "grade": "90"}).credits, 3)
        payload: StudentPayload = {**PAYLOAD, "kind": "contract", "results": []}
        student = student_from_payload(payload)
        self.assertIsInstance(student, ContractStudent)
        self.assertEqual(to_summary(student, SimpleAverage())["average"], "-")


class ProtocolAndCompositionTests(unittest.TestCase):
    def test_runtime_checkable_protocol(self) -> None:
        self.assertIsInstance(ConsoleNotifier(), Notifier)
        self.assertIsInstance(MemoryNotifier(), Notifier)
        self.assertNotIsInstance(object(), Notifier)

    def test_inheritance_and_composition_agree(self) -> None:
        line = "3,Ірина,Бондар,PI-22,95.2"
        composed = RowProcessor(CsvParser(), RowValidator(), TextFormatter())
        self.assertEqual(composed.process(line), CsvRowProcessor().process(line))
        self.assertEqual(composed.process(line), "3: Ірина Бондар, PI-22, 95.20 (відмінно)")

    def test_parts_are_replaceable(self) -> None:
        json_line = (
            '{"student_id": 12, "first_name": "Оксана", "last_name": "Мороз", '
            '"group": "PI-24", "average_grade": "97"}'
        )
        processor = RowProcessor(JsonParser(), RowValidator(), ShortFormatter())
        self.assertEqual(processor.process(json_line), "PI-24 #12 97.00")

    def test_validator_rejects_bad_row(self) -> None:
        processor = RowProcessor(CsvParser(), RowValidator(), TextFormatter())
        with self.assertRaises(InvalidStudentDataError):
            processor.process("0,Ірина,Бондар,PI-22,95.2")
        with self.assertRaises(InvalidGradeError):
            CsvRowProcessor().process("3,Ірина,Бондар,PI-22,105")


class DependencyInjectionTests(unittest.TestCase):
    def test_same_registry_with_different_notifiers(self) -> None:
        reg = build_registry()
        quiet, loud = MemoryNotifier(), MemoryNotifier()
        first, _ = build_services(reg, quiet, SimpleAverage())
        second, _ = build_services(reg, loud, SimpleAverage())
        first.register_from_payload(PAYLOAD)
        second.edit(7, email="x@lnu.edu.ua")
        self.assertEqual((len(quiet.messages), len(loud.messages)), (1, 1))

    def test_demo_data_loader(self) -> None:
        reg = build_registry()
        quiet = load_demo_data(reg)
        self.assertEqual((len(reg), len(reg.groups()), len(quiet.messages)), (10, 3, 13))
        self.assertEqual(
            sorted({type(s).__name__ for s in reg}), ["BudgetStudent", "ContractStudent"]
        )

    def test_main_prints_full_scenario(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            main()
        output = buffer.getvalue()
        for expected in (
            "ЛР4, варіант 1",
            "InvalidGradeError",
            "Картка: Ірина Бондар",
            "composition JsonParser",
        ):
            self.assertIn(expected, output)


class AbstractionTests(unittest.TestCase):
    def test_repository_is_abstract(self) -> None:
        self.assertTrue(getattr(Repository, "__abstractmethods__", None))

    def test_student_subclasses_share_contract(self) -> None:
        for student_class in (BudgetStudent, ContractStudent):
            student: Student = student_class(1, "А", "Б", "a@b.ua", GroupCode("PI-21"))
            with self.subTest(kind=student.funding):
                self.assertIsNone(student.average(SimpleAverage()))
                self.assertFalse(student.has_scholarship(SimpleAverage()))


if __name__ == "__main__":
    unittest.main()
