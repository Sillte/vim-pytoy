from pytoy.infra.timertask import ThreadWorker

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


class EditDocumentRequester:
    def __init__(self, pytoy_fairy: PytoyFairy):
        self._id = uuid.uuid4().hex[:8]
        self.pytoy_fairy = pytoy_fairy


    @property
    def query_start(self) -> str:
        return f"[pytoy-llm][{self._id}]>$>"

    @property
    def query_end(self) -> str:
        return f">$>[pytoy-llm][{self._id}]"
    
    def _insert_markers(self, buffer: PytoyBuffer) -> None:
        selection = self.pytoy_fairy.selection
        text = buffer.get_text(selection)
        new_text = f"{self.query_start}\n{text}\n{self.query_end}"
        buffer.range_operator.replace_text(selection, new_text)

    def _revert_markers(self, buffer: PytoyBuffer) -> None:
        start_range = buffer.range_operator.find_first(self.query_start)
        if start_range:
            buffer.range_operator.replace_text(start_range, "")
        end_range = buffer.range_operator.find_first(self.query_end)
        if end_range:
            buffer.range_operator.replace_text(end_range, "")

    def _apply_output(self, buffer: PytoyBuffer, output: SyncOutput) -> None:
        output_str = str(output)
        start_range = buffer.range_operator.find_first(self.query_start)
        end_range = buffer.range_operator.find_first(self.query_end)
        if not start_range or not end_range:
            EphemeralNotification().notify("Request is gone, so no operations.")
            return
        cr = CharacterRange(start_range.start, end_range.end)
        buffer.range_operator.replace_text(cr, output_str)

    def _handle_error(self, buffer: PytoyBuffer, exception: Exception) -> None:
        self._revert_markers(buffer)
        ThreadWorker.add_message(str(exception))
        EphemeralNotification().notify("LLM Error. See `:messages`.")

    def make_interaction(self) -> LLMInteraction:
        buffer = self.pytoy_fairy.buffer
        kernel = self.pytoy_fairy.kernel
        self._insert_markers(buffer)

        document = buffer.content
        inputs = self._make_inputs(document, kernel)

        request = InteractionRequest(
            kernel=kernel,
            inputs=inputs,
            llm_output_format="str",
            on_success=lambda output: self._apply_output(buffer, output),
            on_failure=lambda exc: self._handle_error(buffer, exc),
        )
        return InteractionProvider().create(request)

    def _make_inputs(self, document: str, kernel: FairyKernel) -> list[InputMessage]:
        intent = (
            " Revise the text strictly between the markers:\n"
            f"`{self.query_start}` and `{self.query_end}`.\n"
            "as a part of <document>.\n"
            "All content outside the markers must be treated as read-only context.\n"
            "============================================================\n"
            "LOCAL INSTRUCTION OVERRIDE\n"
            "============================================================\n"
            "Immediately adjacent to the markers, there MAY be additional\n"
            "instructions written by the user.\n\n"
            "- These instructions, if present, are located:\n"
              f"- Immediately AFTER `{self.query_start}`, or\n"
              f"- Immediately BEFORE `{self.query_end}`.\n"
            "If such instructions exist:\n"
            "- You MUST follow them.\n"
            "- They take PRIORITY over all other instructions,\n"
              "except for the absolute output constraints.\n"
            "============================================================\n"
            "LANGUAGE SELECTION (MANDATORY)\n"
            "============================================================\n"

            "Before rewriting, you MUST do the following internally:\n"
            "1. Determine the dominant language of the document\n"
               "(Japanese, English, or Python).\n"
            "2. Choose ONLY ONE instruction set below that matches the dominant language.\n"
            "3. COMPLETELY IGNORE the instruction set of the other languages.\n"
            "Do NOT output this decision or any analysis.\n"
            "============================================================\n"
            "ENGLISH INSTRUCTIONS\n"
            "============================================================\n"
            "Use these instructions ONLY if the dominant language is English.\n"
            "Style and consistency:\n"
            "- Strictly match the tone, formality, and writing style of the surrounding document.\n"
            "- Match sentence length, paragraph structure, and level of explicitness.\n"
            "- Do NOT introduce new metaphors, idioms, or stylistic flair.\n"
            "- Do NOT make the text sound more “helpful” or “polite” than the rest of the document.\n"
            "Editorial rules:\n"
            "- You may rephrase, reorganize, or clarify for readability.\n"
            "- Complete incomplete sentences or bullet points when necessary.\n"
            "- Replace placeholders such as `...`, `???`, or unfinished items\n"
              "with the most plausible content.\n"
            "- Maintain technical accuracy and domain-appropriate vocabulary.\n"
            "- Maintain styles such as itemization or quotes.\n"
            "- After you rewrite the text between `{query_start}` and `{query_end}`, the text must:\n"
            " 1. Be grammatically correct. \n"
            " 2. Be naturally readable in context. \n"
            "============================================================\n"
            "JAPANESE INSTRUCTIONS\n"
            "============================================================\n"

            "Use these instructions ONLY if the dominant language is Japanese.\n"
            f"- 出力は、`{self.query_start}`、`{self.query_end}`のmarkersで囲まれた範囲のみとせよ\n"
            "- 出力の評価はmarkersを含めた範囲の文章が、出力によって書き換わった<document>内の文字列で行われる\n"
            "- あなたは日本語のエキスパートとして、<document> 内を完成度の高い自然な文章に仕上げよ\n"
            "- 脚注とメモを除いた編集範囲外の直前・直後の段落も参照し、<document>の連続性を損なわないようにせよ\n"
            "\n"
            "(出力の評価観点)\n"
            "- <document> 内で不完全な文や箇条書きは文脈に従って自然に補完せよ\n"
            "- <document> 内の意図に沿って`...` や `???` などのプレースホルダを最も自然な内容になるように書き換えよ\n"
            "- <document> 内で表現されている意図や論理構造を尊重せよ\n"
            "- <document> 内で同一の概念を表す場合は、同一の単語を使用せよ\n"
            "- <document> 内で箇条書き、番号付きリスト、引用、段落などの階層構造やスタイルを統一せよ\n"
            "- <document> 内の文末表現（だ／である／です・ます調）を統一せよ\n"
            "- <document> 内の語彙の硬さ（技術文・説明文・口語）が統一せよ\n"
            "- <document> 内で連続して読んだときに違和感がないようにせよ\n"
            "============================================================\n"
            "PYTHON INSTRUCTIONS\n"
            "============================================================\n"
            "Use these instructions ONLY if the dominant language is Python.\n"

            "Style and consistency (CRITICAL):\n"
            "- Strictly preserve the coding style of the surrounding code.\n"
            "- Match indentation, line breaks, naming conventions, and formatting.\n"
            "- Follow the existing paradigm (procedural, functional, OOP) exactly.\n"
            "- Do NOT introduce new abstractions, patterns, or helper functions\n"
            "  unless they are implied by the surrounding code.\n"

            "Code editing rules:\n"
            "- Do NOT change the external behavior or public interface.\n"
            "- Do NOT wrap the output in ```python``` or any other code blocks.\n"
            "- Maintain semantic equivalence unless the context clearly requires correction.\n"
            "- Complete incomplete code fragments if necessary, using the most plausible intent.\n"
            "- Replace placeholders such as `...`, `pass`, or unfinished blocks\n"
            "  with contextually appropriate implementations.\n"
            "- Preserve comments unless they are incorrect; match their tone and verbosity.\n"
            "- After you rewrite the code between `{query_start}` and `{query_end}`, the code must:\n"
            "   1. Be syntactically valid Python.\n"
            "   2. Remain ready to run without modification.\n"
            "Technical constraints:\n"
            "- Ensure the code remains valid Python.\n"
            "- Do NOT optimize, refactor, or modernize unless explicitly instructed.\n"
            "- If refactoring or modernization is required to resolve an issue, do NOT modify the code directly.\n"
            "  Instead, leave a comment at the relevant location describing the concern. \n"
            "- If the logic appears incorrect or ambiguous, preserve the original code and annotate the issue using comments only. \n"
            "- Avoid adding defensive checks, logging, or documentation beyond what exists.\n"
            )

        output_description = ("You are revising the document or code. \n"
                              "Output the most appropriate part of senetences\n"
                              "as the completed document.\n"
                              )

        output_spec = (f"The text between `{self.query_start}` and `{self.query_end}`.")

        llm_task = LLMTask(name="Your sole goal is to produce the final rewritten content that can be pasted back verbatim into the original document.",
                       intent=intent,
                       rules= [
                           "Rewrite ONLY the content between the markers.",
                            "Output ONLY the rewritten text.",
                            "Do NOT include the markers themselves.",
                            "Do NOT add explanations, commentary, or meta text.",
                            "Do NOT output tags such as <document>.",
                            "Prefer similar length unless clarity or correctness requires change.",
                            "The rewritten text must read naturally when placed back into the document.",
                            "Inside the markers, you MAY organize content into separate lines, bullet points, or numbered items to improve readability.",
                            "Inside the markers, you MAY format freely the content.",
                            "Line length consistency is a secondary preference and must not override document structure or semantic boundaries.",
                       ],
                       role="You are a professional editor who revise the technical documents.",
                       output_description=output_description,
                       output_spec=output_spec,
                       )

        reference_handler = kernel.llm_context.reference_handler
        if reference_handler.exist_reference:
            ref_section_writer = reference_handler.section_writer
            section_data = ref_section_writer.make_section_data()
            section_usage = ref_section_writer.make_section_usage()
            composer = TaskPromptComposer(llm_task, [section_usage], [section_data])
        else:
            composer = TaskPromptComposer(llm_task, [], [])
        messages = composer.compose_messages(user_prompt=self._make_user_prompt(document))
        return list(messages)


    def _make_user_prompt(self, document: str) -> str:
        return ("Here is the document:\n"
                "<document>\n"
                f"{document}\n"
                "</document>\n"
        )