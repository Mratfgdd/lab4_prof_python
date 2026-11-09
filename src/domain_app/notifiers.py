class ConsoleNotifier:
    def send(self, recipient: str, message: str) -> None:
        print(f"  [повідомлення -> {recipient}] {message}")


class MemoryNotifier:
    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def send(self, recipient: str, message: str) -> None:
        self.messages.append((recipient, message))
