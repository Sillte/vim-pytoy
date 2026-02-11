from typing import Literal, Annotated
from pydantic import Field, BaseModel

type LanguageKind = Literal["python", "english", "japanese"]

type ContentKindType = Literal["document", "mail", "config", "comment", "review"]

class DocumentKind(BaseModel):
    language: Annotated[
        LanguageKind, Field(description="The dominant language of the document.")
    ]
    content_kind: Annotated[
        ContentKindType | None, Field(description="Kind of the document, if specified.")  
    ] = None
