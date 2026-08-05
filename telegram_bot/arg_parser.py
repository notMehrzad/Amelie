"""Utilities for parsing aiogram command arguments.

This module provides a decorator that automatically parses a command's raw
argument string into typed Python objects based on the decorated function's
signature.

Parameters are converted according to their type
annotations, while missing arguments fall back to their default values when
available.
"""

from __future__ import annotations

__all__ = ["parse_args"]

import inspect
import shlex
from functools import wraps
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, get_args

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from aiogram.filters.command import CommandObject
    from aiogram.types import Message
P = ParamSpec("P")

_TRUTHY = ("true", "yes", "y", "1", "on")
_FALSY = ("false", "no", "n", "0", "off")

_NO_DEFAULT = object()


def _convert(string: str, type_: type) -> object:
    """Convert a string into the requested type.

    Supported conversions are ``str``, ``int``, ``float``, and ``bool``.

    Args:
        string (str): String value to convert.
        type_ (type): Target type to convert the value to.

    Raises:
        TypeError: Raised when the requested type is unsupported.

    Returns:
        object: The converted value.

    """
    try:
        if type_ is str:
            return str(string)

        if type_ is int:
            return int(string)

        if type_ is float:
            return float(string)

        if type_ is bool:
            if string.lower() in _TRUTHY:
                return True
            if string.lower() in _FALSY:
                return False

        raise TypeError

    except ValueError as ext:
        raise TypeError from ext


def _convert_one(value: str, annotation: tuple[type, ...]) -> object:
    for a in annotation:
        try:
            return _convert(value, a)
        except TypeError:
            continue

    return _NO_DEFAULT


def _eval_annotation(annotation: object, func: Any) -> object:
    if not isinstance(annotation, str):
        return annotation

    try:
        return eval(annotation, getattr(func, "__globals__", {}))
    except NameError:
        return str


def _get_annotation(annotation: Any) -> tuple[type, ...]:
    if annotation is inspect.Parameter.empty:
        return (str,)

    return get_args(annotation) or (annotation,)


def parse_args(
    func: Callable[
        Concatenate[Message, P],
        Awaitable[None],
    ],
) -> Callable[Concatenate[Message, CommandObject, P], Awaitable[None]]:
    """Parse command arguments based on a command's signature.

    This decorator inspects the decorated function's parameters (excluding the
    ``Message`` and ``CommandObject`` parameters), parses the command's raw
    argument string and converts each argument to the
    corresponding annotated type before invoking the function.

    Missing arguments are replaced with the parameter's default value when one
    is defined. Parameters without annotations are treated as ``str``. Union
    types (e.g. ``int | None``) are attempted in declaration order until a
    compatible conversion succeeds.

    Args:
        func (Callable[..., Awaitable[None]]): Command callback whose arguments
            should be parsed automatically.

    Returns:
        Callable[[Message, CommandObject], Awaitable[None]]: A wrapped callback
        that parses and converts command arguments before execution.

    """

    @wraps(func)
    async def wrapper(
        message: Message,
        command: CommandObject,
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        signature = inspect.signature(func)
        params = list(signature.parameters.values())[1:]

        if not params:
            return await func(message, *args, **kwargs)

        var_param = (
            params[-1] if params[-1].kind is inspect.Parameter.VAR_POSITIONAL else None
        )
        fixed_params = params[:-1] if var_param else params

        raw_text: str = command.args.strip() if command.args else ""

        try:
            raw_words: list[str] = shlex.split(raw_text) if raw_text else []
        except ValueError:
            raw_words = raw_text.split()

        if var_param is None:
            raw_words = raw_words[: len(fixed_params)]

        fixed_words = raw_words[: len(fixed_params)]

        while len(fixed_words) < len(fixed_params):
            fixed_words.append(None)  # pyright: ignore[reportArgumentType]

        args_list: list[Any] = list(fixed_words)

        for n, p in enumerate(fixed_params):
            annotations = _get_annotation(_eval_annotation(p.annotation, func))

            default = (
                p.default if p.default is not inspect.Parameter.empty else _NO_DEFAULT
            )

            if args_list[n] is None:
                if default is not _NO_DEFAULT:
                    args_list[n] = default
                elif type(None) in annotations:
                    pass
                else:
                    msg = f"Missing required argument: {p.name}"
                    raise TypeError(msg)

                continue

            converted = _convert_one(args_list[n], annotations)

            if converted is not _NO_DEFAULT:
                args_list[n] = converted
            elif default is not _NO_DEFAULT:
                args_list[n] = default
            else:
                msg = f"Could not parse argument {p.name} from value {args_list[n]}."
                raise TypeError(msg)

        var_values: list[Any] = []
        if var_param is not None:
            var_annotation = _get_annotation(
                _eval_annotation(var_param.annotation, func),
            )
            for raw_word in raw_words[len(fixed_params) :]:
                converted = _convert_one(raw_word, var_annotation)
                if converted is _NO_DEFAULT:
                    msg = f"could not parse {var_param.name!r} value {raw_word!r}"
                    raise ValueError(msg)
                var_values.append(converted)

        return await func(message, *args_list, *var_values, *args, **kwargs)

    wrapper.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        parameters=[
            inspect.Parameter("message", inspect.Parameter.POSITIONAL_OR_KEYWORD),
            inspect.Parameter("command", inspect.Parameter.POSITIONAL_OR_KEYWORD),
        ],
    )
    del wrapper.__wrapped__

    return wrapper
