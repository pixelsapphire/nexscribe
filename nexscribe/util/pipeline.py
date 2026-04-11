from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Callable, cast

from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table

from nexscribe.log import console
from nexscribe.util.types import BiConsumer, BiFunction, Consumer, Function, Supplier


type TaskRunnable[T, R] = Function[T, R] | Task[T, R] | Pipeline[T, R]
type StatefulTaskRunnable[T, R, S = Any] = BiFunction[S, T, R] | StatefulTask[T, R, S] | StatefulPipeline[T, R, S]


@dataclass(frozen=True)
class TaskLaunchEvent:
    index: int
    total: int
    task_name: str | None


class TaskStatus(StrEnum):
    PENDING = 'PENDING'
    RUNNING = 'RUNNING'
    DONE = 'DONE'


@dataclass
class RuntimeTaskState:
    name: str
    status: TaskStatus = TaskStatus.PENDING


def _render_task_list(tasks: list[RuntimeTaskState]) -> Table:
    table: Table = Table.grid(padding=(0, 1))
    table.add_column(width=2)
    table.add_column()
    for task in tasks:
        if task.status is TaskStatus.RUNNING:
            icon: object = Spinner('dots', style='yellow')
            label = f'[bold white]{task.name}[/bold white]'
        elif task.status is TaskStatus.DONE:
            icon = '[green]✓[/green]'
            label = f'[white]{task.name}[/white]'
        else:
            icon = ''
            label = f'[dim]{task.name}[/dim]'
        table.add_row(icon, label)
    return table


def _run_decorated[R](
        steps: tuple[Any, ...],
        execute: Callable[[Consumer[TaskLaunchEvent]], R],
        *,
        on_next_task: Consumer[TaskLaunchEvent] | None = None,
) -> R:
    runtime_tasks = [RuntimeTaskState(name=step.name or 'Unnamed Task') for step in steps]
    if runtime_tasks: runtime_tasks[0].status = TaskStatus.RUNNING

    with Live(_render_task_list(runtime_tasks), console=console, refresh_per_second=12) as live:
        def _event_listener(event: TaskLaunchEvent) -> None:
            previous_index: int = event.index - 1
            if previous_index >= 0: runtime_tasks[previous_index].status = TaskStatus.DONE
            current_index: int = event.index
            if current_index < len(runtime_tasks): runtime_tasks[current_index].status = TaskStatus.RUNNING
            live.update(_render_task_list(runtime_tasks))
            if on_next_task: on_next_task(event)

        result: R = execute(_event_listener)

        if runtime_tasks:
            runtime_tasks[-1].status = TaskStatus.DONE
            live.update(_render_task_list(runtime_tasks))

        return result


@dataclass(frozen=True)
class Task[T, R]:
    function: Function[T, R]
    name: str | None = None
    on_result: Consumer[R] | None = None

    def __call__(self, value: T) -> R:
        result: R = self.function(value)
        if self.on_result: self.on_result(result)
        return result

    def as_pipeline(self) -> 'Pipeline[T, R]': return Pipeline((self,))

    # def __or__[NR](self: Task[T, R], other: TaskRunnable[R, NR]) -> Pipeline[T, NR]: return self.as_pipeline() | other


@dataclass(frozen=True)
class Pipeline[T, R]:
    _steps: tuple[Task[Any, Any], ...]

    @staticmethod
    def begin[T0, R0](function: Function[T0, R0], name: str | None = None, on_result: Consumer[R] | None = None) -> Pipeline[T0, R0]:
        return Pipeline((Task(function, name, on_result),))

    def then[NR](self, function: Function[R, NR], name: str | None = None) -> Pipeline[T, NR]:
        return Pipeline((*self._steps, Task(function, name)))

    @property
    def steps(self) -> tuple[Task[Any, Any], ...]: return self._steps

    def __or__[NR](self, other: Task[R, NR] | Pipeline[R, NR] | Function[R, NR]) -> Pipeline[T, NR]:
        if isinstance(other, Pipeline): return Pipeline((*self._steps, *other._steps))
        if isinstance(other, Task):
            task_other: Task[R, NR] = cast(Task[R, NR], other)
            return Pipeline((*self._steps, task_other))
        function: Function[R, NR] = other
        return Pipeline((*self._steps, Task(function)))

    def __call__(self, value: T, *, display_progress: bool = False, on_next_task: Consumer[TaskLaunchEvent] | None = None) -> R:
        if display_progress: return self._run_decorated(value, on_next_task=on_next_task)
        current: Any = value
        total: int = len(self._steps)
        for index, task in enumerate(self._steps):
            if index > 0 and on_next_task is not None: on_next_task(TaskLaunchEvent(index=index, total=total, task_name=task.name))
            current = task(current)
        return cast(R, current)

    def _run_decorated(self, value: T, *, on_next_task: Consumer[TaskLaunchEvent] | None = None) -> R:
        return _run_decorated(
            self.steps,
            lambda event_listener: self(value, on_next_task=event_listener),
            on_next_task=on_next_task,
        )


@dataclass(frozen=True)
class StatefulResult[R, S = Any]:
    data: R
    state: S


@dataclass(frozen=True)
class StatefulTask[T, R, S = Any]:
    function: BiFunction[S, T, R]
    name: str | None = None
    on_result: BiConsumer[R, S] | None = None

    def __call__(self, state: S, value: T) -> StatefulResult[R, S]:
        result: StatefulResult[R, S] = StatefulResult(data=self.function(state, value), state=state)
        if self.on_result: self.on_result(result.data, result.state)
        return result

    def as_pipeline(self, initializer: Supplier[S]) -> StatefulPipeline[T, R, S]: return StatefulPipeline((self,), initializer)

    # def __or__[NR](self, other: StatefulPipeline[R, NR, S]) -> StatefulPipeline[T, NR, S]:
    #     return StatefulPipeline((self, *other.steps), other.state_supplier)


@dataclass(frozen=True)
class StatefulPipeline[T, R, S = Any]:
    _steps: tuple[StatefulTask[Any, Any, S], ...]
    _initializer: Supplier[S]

    @staticmethod
    def begin[T0, R0](
            initializer: Supplier[S],
            function: BiFunction[S, T0, R0],
            name: str | None = None,
            on_result: BiConsumer[R, S] | None = None
    ) -> StatefulPipeline[T0, R0, S]:
        return StatefulPipeline((StatefulTask(function, name, on_result),), initializer)

    def then[NR](self, function: BiFunction[S, R, NR], name: str | None = None) -> StatefulPipeline[T, NR, S]:
        return StatefulPipeline((*self._steps, StatefulTask(function, name)), self._initializer)

    @property
    def steps(self) -> tuple[StatefulTask[Any, Any, S], ...]: return self._steps

    def __or__[NR](self, other: StatefulTask[R, NR, S] | StatefulPipeline[R, NR, S] | BiFunction[S, R, NR]) -> StatefulPipeline[T, NR, S]:
        if isinstance(other, StatefulPipeline):
            return StatefulPipeline((*self._steps, *other._steps), self._initializer)
        if isinstance(other, StatefulTask):
            task_other: StatefulTask[R, NR, S] = cast(StatefulTask[R, NR, S], other)
            return StatefulPipeline((*self._steps, task_other), self._initializer)
        function: BiFunction[S, R, NR] = other
        return StatefulPipeline((*self._steps, StatefulTask(function)), self._initializer)

    def __call__(self, value: T, *, display_progress: bool = False, on_next_task: Consumer[TaskLaunchEvent] | None = None) -> StatefulResult[R, S]:
        if display_progress: return self._run_decorated(value, on_next_task=on_next_task)
        state: S = self._initializer()
        current_state: S = state
        current: Any = value
        total: int = len(self._steps)
        for index, task in enumerate(self._steps):
            if index > 0 and on_next_task is not None: on_next_task(TaskLaunchEvent(index=index, total=total, task_name=task.name))
            task_result: StatefulResult[Any, S] = task(current_state, current)
            current_state = task_result.state
            current = task_result.data
        return StatefulResult(data=cast(R, current), state=current_state)

    def _run_decorated(self, value: T, *, on_next_task: Consumer[TaskLaunchEvent] | None = None) -> StatefulResult[R, S]:
        return _run_decorated(
            self.steps,
            lambda event_listener: self(value, on_next_task=event_listener),
            on_next_task=on_next_task,
        )
