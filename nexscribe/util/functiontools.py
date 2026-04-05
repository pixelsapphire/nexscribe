from typing import Iterable

from nexscribe.util.types import Consumer


def foreach[T](function: Consumer[T], iterable: Iterable[T]) -> None:
    for item in iterable: function(item)
