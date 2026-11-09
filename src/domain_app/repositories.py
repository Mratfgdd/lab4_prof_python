from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from typing import Generic, TypeVar

from domain_app.exceptions import DuplicateKeyError
from domain_app.value_objects import GroupCode

K = TypeVar("K", int, GroupCode)
T = TypeVar("T")


class Repository(ABC, Generic[K, T]):
    @abstractmethod
    def add(self, item: T) -> None: ...

    @abstractmethod
    def get(self, key: K) -> T | None: ...

    @abstractmethod
    def remove(self, key: K) -> bool: ...

    @abstractmethod
    def __iter__(self) -> Iterator[T]: ...

    @abstractmethod
    def __len__(self) -> int: ...

    def find(self, predicate: Callable[[T], bool]) -> list[T]:
        return [item for item in self if predicate(item)]


class InMemoryRepository(Repository[K, T]):
    def __init__(self, key: Callable[[T], K]) -> None:
        self._key: Callable[[T], K] = key
        self._items: dict[K, T] = {}

    def add(self, item: T) -> None:
        key = self._key(item)
        if key in self._items:
            raise DuplicateKeyError(f"Запис із ключем {key} вже існує")
        self._items[key] = item

    def get(self, key: K) -> T | None:
        return self._items.get(key)

    def remove(self, key: K) -> bool:
        return self._items.pop(key, None) is not None

    def __iter__(self) -> Iterator[T]:
        return iter(self._items.values())

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, key: object) -> bool:
        return key in self._items

    def __getitem__(self, key: K) -> T:
        return self._items[key]

    def __repr__(self) -> str:
        return f"{type(self).__name__}(size={len(self)})"
