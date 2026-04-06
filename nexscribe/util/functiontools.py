from typing import Iterable

from nexscribe.util.types import Consumer, Function


def foreach[T](function: Consumer[T], iterable: Iterable[T]) -> None:
    for item in iterable: function(item)


def nullsafe[T, R](function: Function[T, R], obj: T | None) -> R | None:
    return function(obj) if obj is not None else None
