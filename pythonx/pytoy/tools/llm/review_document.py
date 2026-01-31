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
from pytoy_llm.materials.composers import InvocationPromptComposer
from pytoy_llm.materials.composers.models import SystemPromptTemplate, SectionData, SectionUsage, TextSectionData
from pytoy_llm.models import InputMessage, SyncOutput
from pytoy_llm.task import LLMTaskSpec, LLMTaskRequest


import uuid
class ReviewDocument:
    review_buffer_name = "__doc__"

    def __init__(self, pytoy_fairy: PytoyFairy):
        self._id = uuid.uuid4().hex[:8]
        self.pytoy_fairy = pytoy_fairy
        self.buffer = self.pytoy_fairy.buffer 
        

    def make_interaction(self) -> LLMInteraction:
        prompt_template = SystemPromptTemplate(
        name="Document Reviewer (Markdown Output)",
        intent=(
            "=== DOCUMENT TYPE CLASSIFICATION ===\n"
            "1. Determine the type of the document:\n"
            "   - 'text' (natural language)\n"
            "   - 'python' (Python code)\n"
            "2. If the document type is 'text', determine the language:\n"
            "   - 'ja' (Japanese)\n"
            "   - 'en' (English)\n"

            "Following the type of document, refer to the corresponding Section with `bundle_kind`. \n"
            "-  TEXT_JP (`text` and `ja`)\n"
            "-  TEXT_EN (`text` and `en`)\n"
            "-  PYTHON (`python`)\n"
            "\n"),
        rules=[
            "Apply only the relevant instructions below based on type/language.",
            "Ignore instructions not relevant to the detected type/language.",
        ],
        output_description=(
            "Based on the determined type, refer to `Section`. \n"
            "Based on the determined type, select the appropriate `Section` and follow its instructions to produce the output."
        ),
        output_spec=str,
        role="Professional writing and coding assistant"
    )

        text_jp_bundle = "TEXT_JP"
        jp_section = TextSectionData(
        bundle_kind=text_jp_bundle,
        description=(
            "Output format for review of Japanese text.\n"
            "「サマリ」/「詳細改善案」/「最終稿」/ 「原文との比較」から構成される"
        ),
        structured_text=(
            "=== サマリ ===\n"
            "- **一言感想**: \n"
            "   - <文章全体の意図に対する簡潔なコメント> と <ウィットに富んだコメント>\n"
            "- **完成度評価**: <0-100%> / <文体に対しての印象コメント>\n"
            "- **改善の必要性**: <very low - extreme> <簡潔な改善が必要・不必要な理由>\n"
            "- **次のアクション提案**: <推奨アクション>\n"
            "\n"
            "* 1行50文字以内\n"
            "* 各項目 原則2行、最大3行\n"
            "* 全体 10行以内を厳守\n"
            "\n"
            "=== 詳細改善案 ===\n"
            "* 改善提案は重要度の大きい5個以内\n"
            "- 各提案には下記の項目で構成される\n"
            "  - <開始行番号>\n"
            "  - <改善対象箇所の引用>\n"
            "  - <改善提案> (Markdownコードブロック)\n"
            "  - <改善理由>\n"
            "* <改善理由>の項目についての詳細\n"
            "  - 1. 原則50字以内、最大100字まで許容\n"
            "  - 2. それでも不可能な場合のみ次の例から1つを選択し出力\n"
            "      - 「ひどい...これは、ひどい...」 / 「評価に値しない」 / 「もうちょっと考えてみようか」\n"
            "\n"
            "====最終稿====\n"
            "* 最終稿は ``` / ``` で囲み、その前に「改善案の方針に従って修正した完成稿を示します」という1文を入れる\n"
            "* 最終稿の最重要項目として、文章の意味・主張・結論は保持すること。\n"
            "* 最終稿は詳細改善案の反映と同様の方針で修正をした統一感のある文章とする\n"
            "* 最終稿は文体・構成・表現は自由に変更してよい。\n"
            "\n"
            "==== 原文との比較 ===\n"
            "\n"
            "* 最終稿についての一言感想\n"
            "   - <文章全体の意図に対する簡潔なコメント> と <ウィットに富んだコメント>\n"
            "- **完成度評価**: <0-100%> と <文体に対しての印象コメント>\n"
            "- **次のアクション提案**: <推奨アクション>\n"
            "    - 特に原文から意味のある意図を理解できなかった場合は、「再提出を求めます。」と最後に出力する\n"
            "* 1行50文字以内\n"
            "* 各項目 原則2行、最大3行\n"
            "* 全体 10行以内を厳守\n"
        )
    )
        jp_usage = SectionUsage(bundle_kind=text_jp_bundle,
                         usage_rule=[f"If an only if document type is {text_jp_bundle}, utilize this section."])
        text_en_bundle = "TEXT_EN"
        en_section = TextSectionData(
            bundle_kind=text_en_bundle,
            description=(
                "Output format for review of English text.\n"
                "'Summary' / 'Detailed Improvements' / 'Final Draft' / 'Comparison with Original'"
            ),
            structured_text=(
                "=== Summary ===\n"
                "- **Overall Impression**: \n"
                "   - <Brief comment on intent and style> and <witty remark>\n"
                "- **Completion Score**: <0-100%> and <style impression>\n"
                "- **Need for Improvement**: <very low - extreme> <brief reason>\n"
                "- **Recommended Next Actions**: <encouraging guidance>\n"
                "\n"
                "* Max 1 line: 50 characters\n"
                "* Each item: 2 lines recommended, max 3\n"
                "* Overall: max 10 lines\n"
                "\n"
                "=== Detailed Improvements ===\n"
                "* Max 5 suggestions, most important first\n"
                "- Each suggestion must include:\n"
                "  - Line number / range\n"
                "  - Quote\n"
                "  - Proposed improvement (Markdown block allowed)\n"
                "  - Reasoning\n"
                "* Reasoning details:\n"
                "  - Normally 50 chars, max 100 allowed\n"
                "  - If impossible, pick one: 'This is terrible', 'Not worth evaluating', 'Think again'\n"
                "\n"
                "==== Final Draft ====\n"
                "* Enclose final draft with ``` / ``` and prefix with "
                "'Final draft following improvement guidelines'\n"
                "* Preserve original meaning and conclusions\n"
                "* Keep consistent style and structure, free to adjust wording\n"
                "\n"
                "==== Comparison with Original ====\n"
                "* Brief comment on final draft vs original\n"
                "* Completion score: <0-100%> and style impression\n"
                "* Recommended next actions\n"
                "* Max 1 line: 50 characters\n"
                "* Each item: 2 lines recommended, max 3\n"
                "* Overall: max 10 lines\n"
            )
        )

        en_usage = SectionUsage(
            bundle_kind=text_en_bundle,
            usage_rule=[f"If and only if document type is {text_en_bundle}, utilize this section."]
        )

        # --- Pythonコード用 Section ---
        python_bundle = "PYTHON"
        python_section = TextSectionData(
            bundle_kind=python_bundle,
            description=(
                "Output format for review of Python code.\n"
                "'Summary' / 'Detailed Improvements' / 'Final Draft' / 'Comparison with Original'"
            ),
            structured_text=(
                "=== Summary ===\n"
                "- **Overall Impression**: \n"
                "   - <Brief comment on code clarity, style, and correctness>\n"
                "- **Completion Score**: <0-100%> and <code style impression>\n"
                "- **Need for Improvement**: <very low - extreme> <brief reason>\n"
                "- **Recommended Next Actions**: <encouraging guidance>\n"
                "=== Detailed Improvements ===\n"
                "- Each suggestion must include:\n"
                "  - Line number / range\n"
                "  - Quote or snippet\n"
                "  - Proposed improvement (Markdown code block)\n"
                "  - Reasoning\n"
                "==== Final Draft ====\n"
                "* Provide copy-ready code in ```python / ``` block\n"
                "* Preserve original logic and correctness\n"
                "* Apply suggested improvements consistently\n"
                "* The output must have the quality of high-quality production code\n"
                "* The output must follow the best practice in the latest python version.\n"
                "\n"
                "==== Comparison with Original ====\n"
                "* Brief comment on final vs original code\n"
                "* Recommended next actions\n"
                "* Max 1 line: 50 characters\n"
                "* Each item: 2 lines recommended, max 3\n"
                "* Overall: max 10 lines\n"
            )
        )

        python_usage = SectionUsage(
            bundle_kind=python_bundle,
            usage_rule=[f"If and only if document type is {python_bundle}, utilize this section."]
        )
        
        def on_success(output):
            buffer =  make_buffer(self.review_buffer_name) 
            buffer.init_buffer(str(output))

        def on_failure(exception):
            EphemeralNotification().notify(str(exception))
            

        composer = InvocationPromptComposer(prompt_template, [jp_usage, en_usage, python_usage], [jp_section, en_section, python_section])
        invocation_spec = composer.compose_invocation_spec()
        task_spec = LLMTaskSpec.from_single_spec("Review document", invocation_spec)
        task_request = LLMTaskRequest(task_spec=task_spec, task_input=self.buffer.content)
        request = InteractionRequest(kernel=self.pytoy_fairy.kernel,
                                     task_request=task_request,
                                     on_success=on_success,
                                     on_failure=on_failure,
                                     )
        interaction = InteractionProvider().create(request)
        return interaction
