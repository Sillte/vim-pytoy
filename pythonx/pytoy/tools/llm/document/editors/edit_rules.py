from typing import assert_never, Sequence, Self, Literal
from pydantic import BaseModel
from pytoy.tools.llm.document.core import DocumentKind
from pytoy.tools.llm.document.core import LanguageKind



class LanguageRuleSet(BaseModel, frozen=True):
    """Rules related to `language`"""

    language_kind: LanguageKind | None = None
    rules: list[str]

    @classmethod
    def from_document_kind(cls, language_kind: LanguageKind) -> Self:
        match language_kind:
            case "japanese":
                rules = [
                    "The output MUST be grammatically correct and natural Japanese.",
                    "Avoid unnatural or machine-translated expressions.",
                ]
                return cls(rules=rules, language_kind=language_kind)
            case "english":
                rules = [
                    "The output MUST be grammatically correct and natural English.",
                    "Avoid unnatural or machine-generated phrasing.",
                ]
                return cls(rules=rules, language_kind=language_kind)
            case "python":
                rules = [
                    "The output MUST be syntactically valid Python code.",
                ]
                return cls(rules=rules, language_kind=language_kind)
        return cls(rules=[])


class ConceptCoherenceRuleSet(BaseModel, frozen=True):
    """Rules ensuring conceptual and logical coherence of document content, 
    excluding formatting or style concerns."""

    consistent_terms: bool = True
    paragraph_flow: bool = True
    avoid_conflicts: bool = False
    cross_check: bool = False

    rules: Sequence[str]

    @classmethod
    def from_flags(
        cls,
        consistent_terms: bool = True,
        paragraph_flow: bool = True,
        avoid_conflicts: bool = False,
        cross_check: bool = False,
    ) -> Self:
        """Generate a ContentCoherenceRuleSet with specific checks enabled."""

        rules = []
        if consistent_terms:
            rules.append("Use consistent terminology for the same concepts throughout the document.")
        if paragraph_flow:
            rules.append("Ensure logical coherence between sentences and paragraphs.")
        if avoid_conflicts:
            rules.append("Avoid contradictions in information across different sections.")
        if cross_check:
            rules.append("Cross-check related statements to ensure consistency of facts and numbers.")

        return cls(
            consistent_terms=consistent_terms,
            paragraph_flow=paragraph_flow,
            avoid_conflicts=avoid_conflicts,
            cross_check=cross_check,
            rules=rules
        )
        

type CompletionMode = Literal["conservative", "clarifying", "expansive"]


class CompletionRuleSet(BaseModel, frozen=True):
    mode: CompletionMode
    rules: Sequence[str]

    @classmethod
    def from_completion_mode(cls, completion_mode: CompletionMode) -> Self:

        base_rules = [
            "If placeholders such as `...`, `…`, or `???` appear and are not natural as literal expressions, they MUST be replaced with contextually appropriate content.",
            "The minimal reconstruction constraint does NOT justify leaving placeholders unresolved.",
        ]

        match completion_mode:

            case "conservative":
                rules = base_rules + [
                    "Perform only the minimal necessary reconstruction required to achieve coherence.",
                    "Preserve original wording, structure, and tone whenever possible.",
                    "Avoid noticeable expansion in volume.",
                    "The length of reconstruction should remain proportionate to the original scoped content.",
                    "Do NOT introduce new themes, claims, or expansions beyond what is required for coherence.",
                ]
                return cls(rules=rules, mode=completion_mode)

            case "clarifying":
                rules = base_rules + [
                    "Make implicit subjects, objects, or conclusions explicit when this improves clarity.",
                    "Resolve fragmented expressions into logically clear sentences.",
                    "Preserve original intent and structure unless clarity requires adjustment.",
                    "Avoid introducing ideas that are not reasonably inferable from context.",
                    "Expansion is permitted only to the extent necessary for clarity.", 
                    "Do not significantly increase the length unless required for understanding.",
                ]
                return cls(rules=rules, mode=completion_mode)

            case "expansive":
                rules = base_rules + [
                    "Allow controlled elaboration when it improves clarity or expressive richness.",
                    "Expand fragmented thoughts into well-developed expressions when appropriate.",
                    "Preserve original intent and thematic direction.",
                    "Do NOT introduce speculative information.",
                    "Do not significantly increase the length unless required for understanding.",
                ]
                return cls(rules=rules, mode=completion_mode)

            case _:
                assert_never(completion_mode)


type UniformityMode = Literal[
    "document",
    "structure",
    "identity", 
]


class StyleRuleSet(BaseModel, frozen=True):
    language_kind: LanguageKind
    uniformity_mode: UniformityMode
    rules: Sequence[str]

    @classmethod
    def from_language_and_uniformity_mode(
        cls,
        language_kind: LanguageKind,
        uniformity_mode: UniformityMode,
    ) -> Self:
        styles = cls._make_enforced_style_elements(language_kind)
        components = cls._make_component_labels(language_kind)

        rules = [
            f"For stylistic consistency, enforce uniformity for the following attributes: {';'.join(styles)}",
            "Treat `style` as a combination of values for these attributes.",
            "For each attribute, select exactly one dominant value.",
            "These attributes do not exhaust all possible stylistic aspects; only these are enforced for uniformity.",
            "You do NOT need to explicitly name or label style values; apply them implicitly and consistently.",
            "Noun-phrase endings (体言止め) are considered complete and valid stylistic forms, not incomplete sentences.",
        ]

        match uniformity_mode:
            case "document":
                rules += [
                    "Identify the dominant `style` of the document from the context.",
                    "Use the same selected `style` across the entire document.",
                ]
            case "structure":
                rules += [
                    "Classify `components` of texts based on their structural purpose in the document, not visual formatting.",
                    f"When identifying `component`, classify text into one of: {';'.join(components)}",
                    "A `component` represents a logical structure in the document, not a strict syntactic or markup-based category.",
                    "Select one dominant `style` for each `component`.",
                    "Using multiple `styles` within the same `component` is considered a violation.",
                    "Within the same `component`, maintain not only stylistic attributes but also a consistent narrative distance and formality level.",
                ]
            case "identity":
                rules += ["Classify `roles` of the texts based on who speaks.",  
                          "Select one dominant `style` for each `role`",
                          "Using multiple `styles` within the same `component` is considered a violation, unless the speaker intentionally change `style`.",
                ]
        return cls(
            language_kind=language_kind,
            uniformity_mode=uniformity_mode,
            rules=rules,
        )

    @classmethod
    def _make_enforced_style_elements(cls, language_kind: LanguageKind) -> list[str]:
        match language_kind:
            case "english":
                return ["tone", "politeness", "complexity of sentences", "words/sentence"]
            case "japanese":
                return [
                    "文末表現（だ・である調 / です・ます調）",
                    "語彙の硬さ（技術文 / 説明文 / 口語)",
                    "文末の句読点(。/. / 句読点なし)",
                    "箇条書きにおける体言止めの使用可否",
                ]
            case "python":
                return [
                    "usage of type annotations",
                    "usage of walrus operator",
                    "naming convention",
                    "error handling style",
                ]

    @classmethod
    def _make_component_labels(cls, language_kind: LanguageKind) -> list[str]:
        match language_kind:
            case "english":
                return ["header", "table", "itemization", "body", "title", "quotation"]
            case "japanese":
                return ["header", "table", "itemization", "body", "title", "quotation"]
            case "python":
                return ["code", "docstring"]
