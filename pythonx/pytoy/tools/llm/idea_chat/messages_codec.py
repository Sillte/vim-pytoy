from typing import Sequence, assert_never

from pytoy_llm.models import LLMMessage, LLMMessagesLike
from pytoy_llm.models.parts import Role, TextPart


class _PartCodec:
    _USER_HEADER = "## :USER:"
    _ASSISTANT_HEADER = "## :ASSISTANT:"

    def encode(self, part: TextPart) -> str:
        match part.role:
            case "user":
                header = f"{self._USER_HEADER}\n"
            case "assistant":
                header = f"{self._ASSISTANT_HEADER}\n"
            case _:
                raise ValueError(f"Only User and Assistant are converted. `{part=}`")

        return f"{header}\n{part.content}\n"

    def decode(self, text: str) -> TextPart:
        text = text.lstrip("\n")

        if text.startswith(self._USER_HEADER):
            role: Role = "user"
            body = text[len(self._USER_HEADER) :]
        elif text.startswith(self._ASSISTANT_HEADER):
            role = "assistant"
            body = text[len(self._ASSISTANT_HEADER) :]
        else:
            raise ValueError(f"Unknown message header. `{text[:100]=}`")

        body = body.lstrip("\n")

        return TextPart(
            role=role,
            content=body.rstrip("\n"),
        )

    def is_part_start_line(self, line: str) -> bool:
        if line.strip("\n").startswith(self._USER_HEADER):
            return True
        if line.strip("\n").startswith(self._ASSISTANT_HEADER):
            return True
        return False

    @classmethod
    def make_part_from_user_prompot(cls, user_prompt: str) -> str:
        header = f"{cls._USER_HEADER}\n"
        return f"{header}\n{user_prompt}\n"


def test_user_part_round_trip():
    codec = _PartCodec()
    part = TextPart(
        role="user",
        content="Hello, world!",
    )

    assert codec.decode(codec.encode(part)) == part


def test_assistant_part_round_trip():
    codec = _PartCodec()
    part = TextPart(
        role="assistant",
        content="Hello!",
    )

    assert codec.decode(codec.encode(part)) == part


class LLMMessagesCodec:
    def __init__(self) -> None:
        self._part_codec = _PartCodec()

    def encode(self, messages: LLMMessagesLike) -> str:
        part_texts = []
        if not messages:
            return ""

        for message in LLMMessage.to_messages(messages):
            for part in message.parts:
                match part:
                    case TextPart():
                        if part.role in ("user", "assistant"):
                            try:
                                part_texts.append(self._part_codec.encode(part))
                            except ValueError:
                                part_texts.append("<INTERNAL-ERROR-OCCURS in LLMMessagesCodec>")
                    case _:
                        pass
        return "\n".join(part_texts)

    def decode(self, text: str) -> Sequence[LLMMessage]:
        messages = []
        lines = text.split("\n")
        index = 0

        while index < len(lines):
            if not self._part_codec.is_part_start_line(lines[index]):
                index += 1
                continue

            start = index
            index += 1

            while index < len(lines):
                if self._part_codec.is_part_start_line(lines[index]):
                    break
                index += 1

            part_text = "\n".join(lines[start:index])
            part = self._part_codec.decode(part_text)
            match part.role:
                case "assistant":
                    messages.append(LLMMessage.from_parts([part], kind="response"))
                case "user":
                    messages.append(LLMMessage.from_parts([part], kind="request"))
                case "system":
                    raise ValueError("ImplementationError")
                case _:
                    assert_never(part.role)
        return messages

    def make_part_from_user_prompt(self, user_prompt: str) -> str:
        return self._part_codec.make_part_from_user_prompot(user_prompt)
