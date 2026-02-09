from typing import assert_never, Sequence
from pydantic import BaseModel
from pytoy.tools.llm.document.core import DocumentKind
from pytoy.tools.llm.document.core import DocumentLanguageType


class EditPolicy(BaseModel, frozen=True):
    rules: list[str]
    
class EditPolicies(BaseModel, frozen=True):
    items: Sequence[EditPolicy]
    intent: str
    role: str | None = None
    

def make_edit_polices(language: DocumentLanguageType, edit_kind = "scoped") -> EditPolicies:
    document_kind = DocumentKind(language=language)
    items =  [ContentEditPolicyFactory(document_kind).edit_policy]
    if edit_kind == "scoped":
        items.append(ScopedContentPolicyFactory().edit_policy)
    items.append(GeneralEditPolicyFactory().edit_policy)
    role = f"Expert of  {language}"
    intent = f"Edit the {language} content while preserving intent, structure, and coherence."


    return EditPolicies(items=items, role=role, intent=intent)


class ContentEditPolicyFactory:
    def __init__(self, document_kind: DocumentKind):
        self.document_kind = document_kind

    @property
    def edit_policy(self) -> EditPolicy:
        language = self.document_kind.language
        match language:
            case "japanese":
                rules = [
                    "The output MUST be grammatically correct Japanese.",
                    "Incomplete sentences or bullet points MUST be completed naturally based on context.",
                    "Use consistent terminology for the same concepts.",
                    "文末表現（だ／である／です・ます調）を統一せよ。",
                    "語彙の硬さ（技術文・説明文・口語）を文書全体で統一せよ。",
                ]
                return EditPolicy(rules=rules)
            case "english":
                rules = [
                    "The output MUST be valid and natural English.",
                    "Preserve paragraph structure, bullet points, and formatting unless correction is required.",
                    "Incomplete sentences MUST be completed based on context.",
                ]
                return EditPolicy(rules=rules)
            case "python":
                rules = [
                    "The output MUST be valid Python code.",
                    "Preserve indentation, naming conventions, and block structure.",
                ]
                return EditPolicy(rules=rules)
        return EditPolicy(rules=[])


class ScopedContentPolicyFactory:
    @property
    def edit_policy(self) -> EditPolicy:
        return EditPolicy(
            rules=[
                "Prefer similar length unless clarity or correctness requires change.",
                "Line length consistency is a secondary preference.",
                "The rewritten text must read naturally when the markers are removed.",
                "Do NOT restate or duplicate information that exists outside the edited region.",
                "Do NOT introduce new conclusions or summaries based on outside content.",
            ],
        )


class GeneralEditPolicyFactory:
    @property
    def edit_policy(self) -> EditPolicy:
        return EditPolicy(
            rules=[
                "Do NOT add explanations, commentary, or meta text.",
                "Prioritize sentence-ending consistency over perceived readability or politeness.",
                "Line length consistency is a secondary preference and must not override document structure or semantic boundaries.",
                "Prefer similar length unless clarity or correctness requires change.",
            ],
        )
