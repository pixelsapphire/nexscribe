from os import PathLike
from typing import Any, Callable, Final, Generator, Iterable, Mapping, ParamSpec, Protocol, SupportsBytes, SupportsFloat, SupportsInt, TypeVar


P = ParamSpec('P')
R = TypeVar('R')
R_co = TypeVar('R_co', covariant=True)
T = TypeVar('T')
T_contra = TypeVar('T_contra', contravariant=True)
U = TypeVar('U')
U_contra = TypeVar('U_contra', contravariant=True)


type JSONValue = None | bool | SupportsInt | SupportsFloat | str | SupportsBytes | PathLike[str] | Iterable['JSONValue'] | Mapping[str, 'JSONValue']


class UndefinedType:
    _instance: UndefinedType

    def __new__(cls) -> UndefinedType:
        if not hasattr(cls, '_instance'): cls._instance: UndefinedType = super(UndefinedType, cls).__new__(cls)
        return cls._instance


Undefined: Final[UndefinedType] = UndefinedType()


class Future(Protocol[R_co]):
    def __await__(self) -> Generator[Any, Any, R_co]: ...


class SupportsRichComparison[T_contra](Protocol):
    def __lt__(self, other: T_contra) -> bool: ...
    def __gt__(self, other: T_contra) -> bool: ...
    def __le__(self, other: T_contra) -> bool: ...
    def __ge__(self, other: T_contra) -> bool: ...


type Callback = Callable[[], None]
type Consumer[T_contra] = Callable[[T_contra], None]
type BiConsumer[T_contra, U_contra] = Callable[[T_contra, U_contra], None]
type NConsumer[**P] = Callable[P, None]
type Supplier[R_co] = Callable[[], R_co]
type Function[T_contra, R_co] = Callable[[T_contra], R_co]
type BiFunction[T_contra, U_contra, R_co] = Callable[[T_contra, U_contra], R_co]
type NFunction[**P, R_co] = Callable[P, R_co]

type Predicate = Callable[..., bool]

type AsyncCallback = Supplier[Future[None]]
type AsyncConsumer[T_contra] = Function[T_contra, Future[None]]
type AsyncSupplier[R_co] = Supplier[Future[R_co]]
type AsyncFunction[T_contra, R_co] = Function[T_contra, Future[R_co]]
type AsyncNFunction[**P, R_co] = NFunction[P, Future[R_co]]

type FutureConsumer[T_contra] = Consumer[Future[T_contra]]
type AsyncFutureConsumer[R_co] = AsyncConsumer[Future[R_co]]

type AnyConsumer = Consumer[Any]
type AnyBiConsumer = BiConsumer[Any, Any]
type AnyNConsumer = NConsumer[...]
type AnySupplier = Supplier[Any]
type AnyFunction = Function[Any, Any]
type AnyBiFunction = BiFunction[Any, Any, Any]
type AnyNFunction = Callable[..., Any]


def discard_return(function: NFunction[P, R]) -> NConsumer[P]:
    def _ignore(*args: P.args, **kwargs: P.kwargs) -> None: function(*args, **kwargs)
    return _ignore
