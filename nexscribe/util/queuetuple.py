from typing import cast, Generic, TypeVar, TypeVarTuple, Unpack


Types = TypeVarTuple('Types')
Head = TypeVar('Head')
Tail = TypeVarTuple('Tail')
T = TypeVar('T')


class QueueTuple(tuple[Unpack[Types]], Generic[Unpack[Types]]):

    def __new__(cls: type[QueueTuple[Unpack[Types]]], items: tuple[Unpack[Types]] | None = ()) -> QueueTuple[Unpack[Types]]:
        return super().__new__(cls, items)

    def advance(self: QueueTuple[Head, Unpack[Tail]]) -> tuple[Head, QueueTuple[Unpack[Tail]]]:
        first_element: Head = self[0]
        remaining_elements: tuple[Unpack[Tail]] = cast(tuple[Unpack[Tail]], self[1:])
        new_queue: QueueTuple[Unpack[Tail]] = QueueTuple(remaining_elements)
        return first_element, new_queue

    def put(self: QueueTuple[Unpack[Types]], item: T) -> QueueTuple[Unpack[Types], T]:
        updated_tuple: tuple[Unpack[Types], T] = cast(tuple[Unpack[Types], T], self + (item,))
        return QueueTuple(updated_tuple)

    def __repr__(self: QueueTuple[Unpack[Types]]) -> str:
        return f'QueueTuple{super().__repr__()}'
