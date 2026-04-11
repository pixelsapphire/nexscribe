import unittest
from unittest import TestCase

from nexscribe.util.pipeline import Pipeline, StatefulPipeline, StatefulResult, StatefulTask, Task


# Dummy functions for testing
def add_one(x: int) -> int:
    return x + 1


def multiply_by_two(x: int) -> int:
    return x * 2


def add_prefix(x: object) -> str:
    return f"prefix_{x}"


class TestPipeline(TestCase):

    def test_pipeline_begin_then_and_steps(self):
        pipeline: Pipeline[int, int] = Pipeline.begin(add_one, name="Add One")
        extended: Pipeline[int, int] = pipeline.then(multiply_by_two, name="Multiply by Two")

        self.assertEqual(len(pipeline.steps), 1)
        self.assertEqual(pipeline.steps[0].name, "Add One")
        self.assertEqual(len(extended.steps), 2)
        self.assertEqual(extended.steps[1].name, "Multiply by Two")

    def test_task_call_and_as_pipeline(self):
        seen: list[int] = []
        task: Task[int, int] = Task(add_one, on_result=seen.append)

        self.assertEqual(task(1), 2)
        self.assertEqual(seen, [2])
        self.assertEqual(task.as_pipeline()(2), 3)

    def test_pipeline_operator_overloads(self):
        base: Pipeline[int, int] = Pipeline.begin(add_one)
        with_function: Pipeline[int, int] = base | multiply_by_two
        with_task: Pipeline[int, int] = base | Task(multiply_by_two)
        with_pipeline: Pipeline[int, int] = base | Pipeline.begin(multiply_by_two)

        self.assertEqual(with_function(4), 10)
        self.assertEqual(with_task(4), 10)
        self.assertEqual(with_pipeline(4), 10)

    def test_pipeline_call_with_events_and_decorated_mode(self):
        events: list[tuple[int, int, str | None]] = []
        pipeline: Pipeline[int, int] = Pipeline.begin(add_one, name='add').then(multiply_by_two, name='mul')

        result: int = pipeline(3, on_next_task=lambda event: events.append((event.index, event.total, event.task_name)))
        decorated: int = pipeline(3, display_progress=True)

        self.assertEqual(result, 8)
        self.assertEqual(decorated, 8)
        self.assertEqual(events, [(1, 2, 'mul')])

    def test_pipeline_with_string_manipulation(self):
        pipeline: Pipeline[object, str] = Pipeline.begin(str).then(add_prefix)
        result: str = pipeline(123)
        self.assertEqual(result, "prefix_123")


def stateful_add_one(state: dict[str, int], value: int) -> int:
    state['calls'] = state.get('calls', 0) + 1
    return value + 1


def stateful_multiply_by_two(state: dict[str, int], value: int) -> int:
    state['calls'] = state.get('calls', 0) + 1
    return value * 2


class TestStatefulPipeline(TestCase):

    def test_stateful_pipeline_begin_then_and_steps(self):
        pipeline: StatefulPipeline[int, int, dict[str, int]] = StatefulPipeline.begin(lambda: {}, stateful_add_one, name='Stateful Add One')
        extended: StatefulPipeline[int, int, dict[str, int]] = pipeline.then(stateful_multiply_by_two, name='Stateful Multiply by Two')

        self.assertEqual(len(pipeline.steps), 1)
        self.assertEqual(pipeline.steps[0].name, 'Stateful Add One')
        self.assertEqual(len(extended.steps), 2)
        self.assertEqual(extended.steps[1].name, 'Stateful Multiply by Two')

    def test_stateful_task_call_and_as_pipeline(self):
        seen: list[tuple[int, dict[str, int]]] = []

        def _capture(data: int, state: dict[str, int]) -> None:
            seen.append((data, state))

        task: StatefulTask[int, int, dict[str, int]] = StatefulTask(stateful_add_one, on_result=_capture)
        state: dict[str, int] = {}
        task_result: StatefulResult[int, dict[str, int]] = task(state, 2)
        pipeline_result: StatefulResult[int, dict[str, int]] = task.as_pipeline(lambda: {})(2)

        self.assertEqual(task_result.data, 3)
        self.assertEqual(task_result.state['calls'], 1)
        self.assertEqual(seen[0][0], 3)
        self.assertIs(seen[0][1], state)
        self.assertEqual(pipeline_result.data, 3)

    def test_stateful_pipeline_call_and_fresh_supplier_state(self):
        pipeline: StatefulPipeline[int, int, dict[str, int]] = StatefulPipeline.begin(
            lambda: {'initialized': 1},
            stateful_add_one,
        ).then(stateful_multiply_by_two)

        first: StatefulResult[int, dict[str, int]] = pipeline(10)
        second: StatefulResult[int, dict[str, int]] = pipeline(10)

        self.assertEqual(first.data, 22)
        self.assertEqual(first.state['initialized'], 1)
        self.assertEqual(first.state['calls'], 2)
        self.assertIsNot(first.state, second.state)

    def test_stateful_pipeline_is_immutable(self):
        original: StatefulPipeline[int, int, dict[str, int]] = StatefulPipeline.begin(lambda: {}, stateful_add_one)
        updated: StatefulPipeline[int, int, dict[str, int]] = original.then(stateful_multiply_by_two)
        self.assertEqual(len(original.steps), 1)
        self.assertEqual(len(updated.steps), 2)

    def test_stateful_pipeline_operator_overloads(self):
        first: StatefulPipeline[int, int, dict[str, int]] = StatefulPipeline.begin(lambda: {}, stateful_add_one)
        second_task: StatefulTask[int, int, dict[str, int]] = StatefulTask(stateful_multiply_by_two)
        with_task: StatefulPipeline[int, int, dict[str, int]] = first | second_task
        with_function: StatefulPipeline[int, int, dict[str, int]] = first | stateful_multiply_by_two
        with_pipeline: StatefulPipeline[int, int, dict[str, int]] = first | StatefulPipeline.begin(lambda: {'calls': 100}, stateful_multiply_by_two)

        self.assertEqual(with_task(4).data, 10)
        self.assertEqual(with_function(4).data, 10)
        self.assertEqual(with_pipeline(4).data, 10)

    def test_stateful_pipeline_call_with_events_and_decorated_mode(self):
        events: list[tuple[int, int, str | None]] = []
        pipeline: StatefulPipeline[int, int, dict[str, int]] = StatefulPipeline.begin(lambda: {}, stateful_add_one, name='add').then(
            stateful_multiply_by_two,
            name='mul',
        )

        result: StatefulResult[int, dict[str, int]] = pipeline(
            3,
            on_next_task=lambda event: events.append((event.index, event.total, event.task_name)),
        )
        decorated: StatefulResult[int, dict[str, int]] = pipeline(3, display_progress=True)

        self.assertEqual(result.data, 8)
        self.assertEqual(decorated.data, 8)
        self.assertEqual(events, [(1, 2, 'mul')])


if __name__ == '__main__':
    unittest.main()
