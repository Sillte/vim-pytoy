import re
from pathlib import Path
from typing import Protocol, Self, Sequence, runtime_checkable

from pytoy.shared.ui.contract.quickfix import QuickfixRecord


@runtime_checkable
class QuickfixRecordsCreatorProtocol(Protocol):
    def __call__(self, content: str, working_directory: Path, /) -> Sequence[QuickfixRecord] | QuickfixRecord: ...


type QuickfixRecordRegex = str
type QuickfixRecordsCreatorLike = str | QuickfixRecordsCreatorProtocol


class QuickfixRecordsCreator:
    def __init__(self, impl: QuickfixRecordsCreatorProtocol):
        self._impl = impl

    @classmethod
    def from_any(cls, creator_like: QuickfixRecordsCreatorLike) -> Self:
        if isinstance(creator_like, str):
            return cls.from_regex(creator_like)
        elif isinstance(creator_like, QuickfixRecordsCreatorProtocol):
            return cls(impl=creator_like)
        raise TypeError(f"QuickfixRecordsCreator cannot be constructed from `{creator_like=}`.")

    @classmethod
    def from_regex(cls, regex: QuickfixRecordRegex) -> Self:
        pattern = re.compile(regex)

        def creator_impl(content: str, cwd: Path) -> Sequence[QuickfixRecord]:
            records = []
            for line in content.split("\n"):
                match = pattern.match(line)
                if match:
                    records.append(QuickfixRecord.from_dict(match.groupdict(), cwd))
            return records

        return cls(impl=creator_impl)

    def __call__(self, content: str, working_directory: Path) -> Sequence[QuickfixRecord]:
        return self.create(content, working_directory)

    def create(self, content: str, working_directory: Path) -> Sequence[QuickfixRecord]:
        result = self._impl(content, working_directory)
        if isinstance(result, QuickfixRecord):
            return [result]
        return result
