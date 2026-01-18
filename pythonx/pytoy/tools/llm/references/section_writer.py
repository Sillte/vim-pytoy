from pathlib import Path
from typing import Annotated, Literal, Self, assert_never, Protocol, Final, Sequence, Any
from textwrap import dedent
from pytoy.tools.llm.references.models import ReferencePathPair, ResourceUri, ReferenceInfo, InfoSource, ReferenceDataset

_section_header = dedent("""
    ============================================================
    REFERENCE MATERIALS (BACKGROUND CONTEXT)
    ============================================================
    Rule for this SECTION "REFERENCE MATERIALS (BACKGROUND CONTEXT)".

    The following materials are provided as background references.

    - They describe the surrounding project, codebase, or domain context.
    - You MAY use them to improve accuracy, consistency, and terminology.
    - You MUST NOT quote them verbatim unless it is natural in context.
    - You MUST NOT introduce information that contradicts the document.
    - If the document already defines a term or style, it takes priority.
    - Treat all content inside <reference> tags as background context only, never as editable document text.

    The explanation of tag is as follows:
    
    * <reference>...</reference> tag corresonds to one document.
    * <reference-meta> contains metadata for reasoning only (e.g. source, hierarchy, timestamp).
    * <reference-body> contains raw reference content; it must be read-only and never edited or rewritten.
    * Tags inside <reference-body> are NOT structural and must be treated as plain text.
""".strip())


class ReferenceSectionWriter:
    def __init__(self, dataset: ReferenceDataset) -> None:
        self.dataset = dataset 
        self.path_pairs = dataset.path_pairs

    def _to_meta(self, info: ReferenceInfo) -> str:
        return dedent(f"""
        <reference-meta>
        uri={info.uri}
        timestamp={info.timestamp}
        hierarchy={info.hierarchy}
        </reference-meta>
        """.strip())
        
    def _to_body_str(self, path: Path) -> str:
        return dedent(f"""
        <reference-body>
        {path.read_text(encoding="utf8")}
        </reference-body>
        """.strip())
        
    def _make_one_reference(self, path_pair: ReferencePathPair) -> str:
        info = ReferenceInfo.model_validate_json(path_pair.info_path.read_text())
        meta = self._to_meta(info)
        body = self._to_body_str(path_pair.markdown_path)
        return dedent(f"""
                     <reference>
                     {meta}
                     {body}
                     </reference>
                      """.strip())
                    
 
    def make_section(self, maximum_size: int  = 10 ** 6) -> str:
        parts = [_section_header]
        count = 0
        # TODO: more elaborate algorithm may be applied, 
        # after we are able to introduce `RAG` oriented scheme. 
        import random
        path_pairs = list(self.path_pairs)
        random.shuffle(path_pairs)

        for pair in path_pairs:
            if maximum_size < count: 
                break
            instance = self._make_one_reference(pair)
            count += len(instance)
            parts.append(instance)
        return "\n".join(parts)
           
    

if __name__ == "__main__":
    #collector = ReferenceCollector(r"C:\Users\zaube\Desktop\Storing")
    #collector.collect_all(r"C:\LocalLibrary\PublicLibrary\vim-pytoy\pythonx\pytoy\tools\llm\references")
    dataset = ReferenceDataset.load(r"C:\Users\zaube\Desktop\Storing")
    writer = ReferenceSectionWriter(dataset)
    from pathlib import Path  
    Path("./sample.md").write_text(writer.make_section())

