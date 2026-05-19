from unittest import TestCase

from nexscribe.util.queuetuple import QueueTuple


class TestQueueTuple(TestCase):

    def test_new_and_repr(self) -> None:
        self.assertEqual(repr(QueueTuple((1, 'a'))), "QueueTuple(1, 'a')")
        self.assertEqual(repr(QueueTuple(())), 'QueueTuple()')

    def test_advance_returns_head_and_tail(self) -> None:
        queue: QueueTuple[int, int, int] = QueueTuple((1, 2, 3))
        head, tail = queue.advance()

        self.assertEqual(head, 1)
        self.assertEqual(tail, QueueTuple((2, 3)))
        self.assertEqual(queue, QueueTuple((1, 2, 3)))
        self.assertIsNot(queue, tail)

    def test_advance_single_element(self) -> None:
        queue: QueueTuple[str] = QueueTuple(('only',))
        head, tail = queue.advance()

        self.assertEqual(head, 'only')
        self.assertEqual(tail, QueueTuple(()))

    def test_advance_empty_raises(self) -> None:
        queue = QueueTuple(())
        with self.assertRaises(IndexError):
            queue.advance()

    def test_heterogeneous_queue(self) -> None:
        queue: QueueTuple[int, str, float] = QueueTuple((1, 'two', 3.5))
        head, tail = queue.advance()
        updated = tail.put({'four': 4})

        self.assertEqual(head, 1)
        self.assertEqual(tail, QueueTuple(('two', 3.5)))
        self.assertEqual(updated, QueueTuple(('two', 3.5, {'four': 4})))

    def test_put_appends(self) -> None:
        queue: QueueTuple[int, int] = QueueTuple((1, 2))
        updated = queue.put(3)

        self.assertEqual(updated, QueueTuple((1, 2, 3)))
        self.assertEqual(queue, QueueTuple((1, 2)))
        self.assertIsInstance(updated, QueueTuple)
