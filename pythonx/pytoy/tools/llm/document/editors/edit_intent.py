from typing import assert_never
from pydantic import BaseModel
from pytoy.tools.llm.document.core import DocumentLanguageType


class EditIntent(BaseModel, frozen=True):
    intent: str
    role: str


def make_japanese_intent() -> EditIntent:
    intent = (
        "- 不完全な文や箇条書きは文脈に従って自然に補完せよ\n"
        "- 意図に沿って`...` や `???` などのプレースホルダを最も自然な内容になるように書き換えよ\n"
        "- 表現されている意図や論理構造を尊重せよ\n"
        "- 同一の概念を表す場合は、同一の単語を使用せよ\n"
        "- 箇条書き、番号付きリスト、引用、段落などの階層構造やスタイルを統一せよ\n"
        "- 文末表現（だ／である／です・ます調）を統一せよ\n"
        "- 語彙の硬さ（技術文・説明文・口語）が統一せよ\n"
        "- 連続して読んだときに違和感がないようにせよ\n"
    )
    return EditIntent(intent=intent, role="日本語編集のエキスパート")


def make_english_intent() -> EditIntent:
    intent = (
            "- You are an expert in English writing, ensure natural readability and style consistency.\n"
            "- Before rewriting, consider context outside the markers, sentence completeness, logical flow, and coherence.\n"
            "- Preserve paragraph structure, bullet points, and formatting outside the markers.\n"
            "- Resolve placeholders like '...' or '???' appropriately.\n"
    )
    return EditIntent(intent=intent, role="Expert in English document editing")


def make_python_intent() -> EditIntent:
    intent = (
        "- Preserve coding style: indentation, naming conventions, line breaks, and surrounding structure.\n"
        "- Before editing, consider context outside the markers, code correctness, and logical consistency.\n"
        "- Complete placeholders such as '...' or 'pass' according to surrounding code logic.\n"
        "- Do NOT introduce new abstractions unless explicitly instructed.\n"
    )
    return EditIntent(intent=intent, role="Python code editing expert")


def make_language_intent(language: DocumentLanguageType) -> EditIntent:
    match language:
        case "english":
            return make_english_intent()
        case "japanese":
            return make_japanese_intent()
        case "python":
            return make_python_intent()
        case _:
            assert_never(language)