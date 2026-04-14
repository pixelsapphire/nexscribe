from importlib import import_module
from os import PathLike
from typing import Any, Callable, cast, Final, Generator, get_args, get_origin, Iterable, Literal, Mapping, overload, ParamSpec, Protocol, \
    SupportsBytes, \
    SupportsFloat, SupportsInt, TypeAliasType, TypeVar, Union

from nexscribe.core._aliases import pytypes


RuntimeTypeCheck = Callable[[Any, Any], bool]

try:
    from type_check.core import type_check as _third_party_type_check  # type: ignore[reportUnknownVariableType]
    import_module('type_check.builtin_checks')
    _runtime_type_check: RuntimeTypeCheck | None = cast(RuntimeTypeCheck, _third_party_type_check)
except ImportError:
    _runtime_type_check = None


def _matches_exact_type(value: Any, expected_type: Any) -> bool:
    origin: Any = get_origin(expected_type)

    if expected_type is Any: return True

    if origin is None:
        if expected_type is type(None): return value is None
        if isinstance(expected_type, type): return isinstance(value, expected_type)
        return False

    if origin in (pytypes.UnionType, Union): return any(_matches_exact_type(value, option) for option in get_args(expected_type))
    if origin is Literal: return value in get_args(expected_type)
    if not isinstance(origin, type) or type(value) is not origin: return False

    args = get_args(expected_type)
    if not args: return True

    if origin in (list, set, frozenset):
        (item_type,) = args
        return all(_matches_exact_type(item, item_type) for item in value)

    if origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis: return all(_matches_exact_type(item, args[0]) for item in value)
        if len(args) != len(value): return False
        return all(_matches_exact_type(item, item_type) for item, item_type in zip(value, args, strict=True))

    if origin is dict:
        if len(args) != 2: return False
        key_type, value_type = args
        return all(_matches_exact_type(key, key_type) and _matches_exact_type(item, value_type) for key, item in value.items())

    return True


def _runtime_type_matches(value: Any, expected_type: Any) -> bool:
    if _runtime_type_check is None: return _matches_exact_type(value, expected_type)
    return bool(_runtime_type_check(value, expected_type)) and _matches_exact_type(value, expected_type)


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


@overload
def dynamic_cast(t: type[Literal['']], obj: Any) -> Any: ...


@overload
def dynamic_cast[T](t: type[T], obj: Any) -> T | None: ...


@overload
def dynamic_cast(t: pytypes.UnionType, obj: Any) -> Any: ...


@overload
def dynamic_cast(t: TypeAliasType, obj: Any) -> Any: ...


@overload
def dynamic_cast[T](t: T, obj: Any) -> T | None: ...


def dynamic_cast(t: Any, obj: Any) -> Any:
    return obj if _runtime_type_matches(obj, t) else None
