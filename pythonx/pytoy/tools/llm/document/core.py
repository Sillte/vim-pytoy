from typing import Annotated, Literal

from pydantic import BaseModel, Field

type LanguageKind = Literal["python", "english", "japanese"]

type ContentKindType = Literal["document", "mail", "config", "comment", "review"]


class DocumentKind(BaseModel):
    language: Annotated[LanguageKind, Field(description="The dominant language of the document.")]
    content_kind: Annotated[ContentKindType | None, Field(description="Kind of the document, if specified.")] = None
