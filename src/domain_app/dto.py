from dataclasses import dataclass
from typing import Literal, NotRequired, TypedDict

from domain_app.models import AcademicRecord, Student, create_student
from domain_app.policies import GradingPolicy
from domain_app.value_objects import CourseResult, Grade, GroupCode


class ResultPayload(TypedDict):
    subject: str
    grade: str
    credits: NotRequired[int]


class StudentPayload(TypedDict):
    id: int
    first_name: str
    last_name: str
    email: str
    group: str
    kind: Literal["budget", "contract"]
    results: NotRequired[list[ResultPayload]]


class StudentSummary(TypedDict):
    id: int
    full_name: str
    group: str
    kind: str
    average: str
    results: int


class GroupSummary(TypedDict):
    group: str
    students: int
    average: str
    best: str


@dataclass(frozen=True, slots=True)
class StudentRow:
    student_id: int
    full_name: str
    group: GroupCode
    average: Grade


def result_from_payload(payload: ResultPayload) -> CourseResult:
    return CourseResult(payload["subject"], Grade.of(payload["grade"]), payload.get("credits", 3))


def student_from_payload(payload: StudentPayload) -> Student:
    record = AcademicRecord(result_from_payload(item) for item in payload.get("results", []))
    return create_student(
        payload["kind"],
        id=payload["id"],
        first_name=payload["first_name"],
        last_name=payload["last_name"],
        email=payload["email"],
        group=GroupCode(payload["group"]),
        record=record,
    )


def to_summary(student: Student, policy: GradingPolicy) -> StudentSummary:
    average = student.average(policy)
    return {
        "id": student.id,
        "full_name": student.full_name,
        "group": student.group.value,
        "kind": student.funding,
        "average": str(average) if average is not None else "-",
        "results": len(student.record),
    }
