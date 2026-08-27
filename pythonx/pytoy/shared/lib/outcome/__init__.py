from typing import TypeGuard
from dataclasses import dataclass

@dataclass(frozen=True)
class Success[T]:
    value: T

@dataclass(frozen=True)
class Failure[E]:
    error: E

type Outcome[T, E] = Success[T] | Failure[E]


def is_success[T, E](outcome: Outcome[T, E]) -> TypeGuard[Success[T]]:
    return isinstance(outcome, Success)

def is_failure[T, E](outcome: Outcome[T, E]) -> TypeGuard[Failure[E]]:
    return isinstance(outcome, Failure)
