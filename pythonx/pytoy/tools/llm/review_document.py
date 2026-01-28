from pytoy.infra.timertask import ThreadWorker
from pytoy.ui.pytoy_buffer import make_buffer    

from pytoy.tools.llm.kernel import FairyKernel
from pytoy.tools.llm.interaction_provider import InteractionRequest
from pytoy.tools.llm.interaction_provider import InteractionProvider
from pytoy.tools.llm.models import HooksForInteraction, LLMInteraction

from pytoy.tools.llm.pytoy_fairy import PytoyFairy
from pytoy.ui.notifications import EphemeralNotification
from pytoy.ui.pytoy_buffer import PytoyBuffer
from pytoy.ui.pytoy_window import CharacterRange
from pytoy_llm.materials.composers import TaskPromptComposer
from pytoy_llm.materials.composers.models import LLMTask
from pytoy_llm.models import InputMessage, SyncOutput


import uuid
class ReviewDocument:
    review_buffer_name = "__doc__"

    def __init__(self, pytoy_fairy: PytoyFairy):
        self._id = uuid.uuid4().hex[:8]
        self.pytoy_fairy = pytoy_fairy
        self.buffer = self.pytoy_fairy.buffer 
        

    def make_interaction(self) -> LLMInteraction:
        review_task = LLMTask(
        name="Document Reviewer (Markdown Output)",
        intent=(
            "=== DOCUMENT TYPE CLASSIFICATION ===\n"
            "1. Determine the type of the document:\n"
            "   - 'text' (natural language)\n"
            "   - 'python' (Python code)\n"
            "2. If the document type is 'text', determine the language:\n"
            "   - 'ja' (Japanese)\n"
            "   - 'en' (English)\n"
            "3. Apply only the relevant instructions below based on type/language.\n"
            "4. Completely ignore instructions for other types.\n"
            "5. Do NOT output your type determination or analysis.\n"
            "\n"
            "=== TEXT REVIEW INSTRUCTIONS (Japanese) ===\n"
            "If 'ja':\n"
            "=== SUMMARY (最大15行, Markdown) ===\n"
            "- **一言感想**: \n"
            "   - <文章全体の意図・スタイルに対する簡潔なコメント>\n"
            "- **完成度評価**: <0-100%> (文法・文体・論理構造の総合印象)\n"
            "- **改善の必要性**: <very low - extreme> (改善が必要な理由を簡潔に)\n"
            "- **概略改善案**: \n"
            "  1. 文体・語調の統一\n"
            "  2. 論理構造の明確化\n"
            "  3. 段落・箇条書きの階層整理\n"
            "- **次のアクション提案**: <励ます形で推奨アクション>\n"
            "=== 詳細改善案 ===\n"
            "- 各提案には以下を必ず含める:\n"
            "  - 行番号 / 範囲\n"
            "  - 改善対象箇所の引用\n"
            "  - 改善提案 (Markdownコードブロック可)\n"
            "  - 改善理由\n"
            "\n"
            "=== TEXT REVIEW INSTRUCTIONS (English) ===\n"
            "If 'en':\n"
            "=== SUMMARY (max 15 lines, Markdown) ===\n"
            "- **Overall Impression**: <brief comment on intent and style>\n"
            "- **Completion Score**: <0-100%> (grammar, style, logic)\n"
            "- **Need for Improvement**: <very low - extreme> (brief reason)\n"
            "- **Outline of Improvements**:\n"
            "  1. Tone and style consistency\n"
            "  2. Logical structure clarification\n"
            "  3. Organization of paragraphs and bullet points\n"
            "- **Recommended Next Actions**: <encouraging, context-based>\n"
            "=== DETAILED IMPROVEMENTS (Markdown) ===\n"
            "- Include for each suggestion:\n"
            "  - Line number / range\n"
            "  - Quote\n"
            "  - Proposed improvement (Markdown code block if needed)\n"
            "  - Reasoning\n"
            "\n"
            "=== PYTHON REVIEW INSTRUCTIONS ===\n"
            "If 'python':\n"
            "- Check syntax, readability, Pythonic style, and potential bugs\n"
            "- Provide copy-ready fixed snippets in Markdown code blocks\n"
            "- Include line numbers and reasoning for each suggestion\n"
        ),
        rules=[
            "Determine the document type: 'text' or 'python'.",
            "If text, detect the language: 'ja' or 'en'.",
            "For text, review grammar, style, readability, logic, and structure.",
            "For Python, review syntax, readability, Pythonic style, and correctness.",
            "Provide line numbers or line ranges for all suggestions.",
            "Include detailed reasoning for each suggestion.",
            "Summaries must be <= 20 lines, Markdown formatted.",
            "Except codes, 1 line MUST NOT exceed 60 characters. "
        ],
        output_description=(
            "Structured improvement suggestions for text (Japanese or English) or Python code, "
            "formatted in Markdown. Includes: summary (max 20 lines), outline of improvements, "
            "and detailed line-by-line suggestions with reasoning. Python reviews include "
            "copy-ready code snippets."
        ),
        output_spec="str",
        reasoning_guidance=(
            "Analyze the document type and language first. Then generate a structured Markdown review: "
            "summary (max 20 lines), overall impression, completion score, improvement necessity, "
            "outline of improvements, and detailed line-by-line suggestions with reasoning. "
            "For Python, include correct, copy-ready code snippets in Markdown."
        ),
        role="Professional writing and coding assistant"
    )
        
        def on_success(output):
            buffer =  make_buffer(self.review_buffer_name) 
            buffer.init_buffer()
            from pytoy.infra.timertask import TimerTask
            def _update():
                cr = buffer.range_operator.entire_character_range
                buffer.range_operator.replace_text(cr, str(output))
            TimerTask.execute_oneshot(_update)

        def on_failure(exception):
            EphemeralNotification().notify(str(exception))
            

        composer = TaskPromptComposer(review_task, [], [])
        inputs =  composer.compose_messages(user_prompt=self.buffer.content)
        request = InteractionRequest(kernel=self.pytoy_fairy.kernel,inputs=inputs, llm_output_format="str",
                                     on_success=on_success, 
                                     on_failure=on_failure,
                                     )
        interaction = InteractionProvider().create(request)
        return interaction
