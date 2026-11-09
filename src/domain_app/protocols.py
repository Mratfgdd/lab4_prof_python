from typing import Protocol, runtime_checkable

from domain_app.dto import StudentRow


@runtime_checkable
class Notifier(Protocol):
    def send(self, recipient: str, message: str) -> None: ...


class Parser(Protocol):
    def parse(self, line: str) -> StudentRow: ...


class Validator(Protocol):
    def validate(self, row: StudentRow) -> None: ...


class Formatter(Protocol):
    def format(self, row: StudentRow) -> str: ...
