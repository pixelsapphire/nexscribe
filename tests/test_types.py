from dataclasses import dataclass
from typing import Literal
from unittest import TestCase

from nexscribe.util.types import dynamic_cast


@dataclass
class UserTransformDelta:
    @dataclass
    class TransformCall:
        function: str
        arguments: list[object]

    field: str
    type: Literal['transform']
    transform: TransformCall


@dataclass
class UserDeleteDelta:
    field: str
    type: Literal['delete']


type UserDelta = UserTransformDelta | UserDeleteDelta


class TestDynamicCast(TestCase):
    def test_exact_primitive_type(self):
        self.assertEqual(dynamic_cast(int, 5), 5)
        self.assertIsNone(dynamic_cast(float, 5))

    def test_exact_parameterized_list(self):
        self.assertEqual(dynamic_cast(list[int], [1, 2]), [1, 2])
        self.assertIsNone(dynamic_cast(list[int], [1, '2']))

    def test_exact_nested_parameterized_type(self):
        value = [{'a': 1}, {'b': 2}]
        self.assertEqual(dynamic_cast(list[dict[str, int]], value), value)
        self.assertIsNone(dynamic_cast(list[dict[str, int]], [{'a': '1'}]))

    def test_optional_union(self):
        self.assertEqual(dynamic_cast(int | None, 1), 1)
        self.assertIsNone(dynamic_cast(int | None, '1'))
        self.assertIsNone(dynamic_cast(int, None))

    def test_inheritance(self) -> None:
        self.assertEqual(dynamic_cast(object, 'value'), 'value')
        self.assertIsNone(dynamic_cast(TestDynamicCast, TestCase()))

    def test_user_delta(self) -> None:
        self.assertEqual(dynamic_cast(list[UserDelta], []), [])
