from textwrap import dedent

from pytoy.tools.llm.idea_routine.values.models import ValuableDemand


def make_ss_demand() -> ValuableDemand:
    validity_conditions = dedent(
        """
   * A complete short story is produced as an artifact.
   * The story has a coherent premise, progression, and conclusion.
   * The artifact is readable as a standalone work.
   * If it is a derivative fiction, it must respect the specified source material sufficiently to remain recognizable as such.
   """.strip()
    )
    quality_criteria = dedent(
        """
    * Narrative coherence should be maintained.
    * Character appeal. Character should be memorable. 
    * Originality.
    * Humor. Linking the multiple concepts and finding the latent structures between them. 
    * Intentions of the article; What the artifcact would like to provide should be clear.    
    * Faithfulness to the source material, for derivative fiction.
    """.strip()
    )
    preference = dedent(
        """
    If it is a derivative fiction, the nummber characters should not be so large. 
    It is not good to scratch the surface of the characters of the original work.  
    It may be preferable to focus on a small number of characters and describe their personalities deeply.  

    As another perspective, mixing the characters from the different origial works may yield interesting structure.
   
    """.strip()
    )
    return ValuableDemand(
        validity_conditions=validity_conditions, quality_criteria=quality_criteria, preference=preference
    )


def make_python_article_demand() -> ValuableDemand:
    validity_conditions = dedent(
        """
        * A complete technical article is produced as an artifact.
        * The technical subject and intended scope of the article are clearly defined.
        * Technical claims are sufficiently accurate and do not knowingly contradict
          the behavior or specifications of the relevant software, language, or system.
        * Code examples are internally consistent and correspond to the explanations.
        * Important assumptions, version dependencies, platform dependencies, and
          limitations are identified when they materially affect the claims.
        * The article provides enough explanation for an expert reader to understand
          the technical subject without relying on unexplained essential steps.
        """.strip()
    )

    quality_criteria = dedent(
        """
        * Technical depth. The article should explain mechanisms and underlying
          principles rather than merely describe surface-level usage.
        * Technical precision. Terminology, distinctions, and explanations should
          be precise enough for expert readers.
        * Practical usefulness. The knowledge should help the reader make decisions,
          implement systems, debug problems, or understand real implementations.
        * Conceptual clarity. Complex mechanisms should be organized into a structure
          that makes their relationships understandable.
        * Examples. Examples should expose important behavior and illuminate the
          underlying concepts rather than merely demonstrate syntax.
        * Edge-case awareness. Important exceptional behavior and limitations should
          be addressed when relevant.
        * Connection between abstraction and implementation. The article should
          connect conceptual explanations with what actually happens in programs,
          runtimes, libraries, operating systems, or hardware when appropriate.
        * Conciseness. The article should avoid explanation that does not contribute
          to understanding the intended subject.
        """.strip()
    )

    preference = dedent(
        """
       The expected readers are experienced Python developers or software engineers.
       Accessibility to beginners is not a primary objective.
       Depth and intellectual value for experienced readers should take priority.

       The readers are expected to be interested in design principles,
       such as design patterns and domain-driven design.
       Connections between Python implementation and higher-level design
       policies or principles are particularly appreciated.
       In addition, the readers are expected to be curious about
       other programming languages, machine learning, and prompt/context engineering.

       It is preferable to explain why a mechanism behaves as it does rather than
       merely showing how to use an API.

       When useful, the article may cross abstraction boundaries, such as explaining
       Python behavior through CPython internals, C interfaces, operating-system
       mechanisms, compiler behavior, or Rust interoperability.

       A technically interesting connection is preferable to a broad but shallow
       survey of unrelated features.

       When several implementation strategies are possible, the article should
       make the trade-offs and assumptions behind the preferred approach explicit.

       The readers are assumed to use Python 3.12 or later.

       """.strip()
    )

    return ValuableDemand(
        validity_conditions=validity_conditions,
        quality_criteria=quality_criteria,
        preference=preference,
    )


def make_mathematical_proof_demand() -> ValuableDemand:
    validity_conditions = dedent(
        """
        * A complete mathematical statement and its proof are produced as an artifact.
        * The assumptions, definitions, and scope of the statement are explicit
          or unambiguously established from the context.
        * Every essential logical step in the proof is justified.
        * No essential claim is treated as established without an appropriate
          justification, theorem, definition, or previously established result.
        * The conclusion follows from the stated assumptions.
        * Mathematical notation is used consistently and does not introduce
          ambiguity that materially affects the argument.
        """.strip()
    )

    quality_criteria = dedent(
        """
        * Rigor. The proof should make the logical dependencies of the argument
          sufficiently explicit.
        * Clarity. The structure and purpose of the argument should be understandable
          to the intended mathematical reader.
        * Conceptual insight. The proof should reveal why the theorem is true,
          rather than merely establish that it is true.
        * Elegance. When appropriate, the proof should use a particularly natural,
          economical, or illuminating argument.
        * Generality. The argument should expose a more general principle when doing
          so provides meaningful mathematical value.
        * Brevity. The proof should avoid unnecessary technical steps without hiding
          essential reasoning.
        * Pedagogical value. The exposition should help the intended reader learn,
          review, or reconstruct the mathematical ideas involved.
        * Appropriate abstraction. The level of abstraction should be appropriate
          to the mathematical subject and intended reader.
        * Connections. When useful, the proof may reveal relationships with other
          mathematical concepts, equivalent formulations, or related theorems.
        """.strip()
    )

    preference = dedent(
        """
        The default intended reader has a university-to-graduate level mathematical
        background.

        When the subject is elementary enough, the artifact should aim for a
        particularly polished treatment that allows the reader to review the
        underlying university mathematics at a high level.

        When the problem is genuinely difficult, advanced or research-level
        mathematical knowledge may be used when necessary, but unexplained
        sophistication should not replace a clear argument.

        It is preferable to distinguish the core proof from optional remarks,
        generalizations, historical context, or connections to other areas.

        When multiple proofs are available, a proof that exposes the underlying
        mathematical structure is generally preferable to one that merely provides
        the shortest derivation.

        A proof may deliberately sacrifice brevity for conceptual clarity when
        doing so substantially improves the reader's understanding.
        """.strip()
    )

    return ValuableDemand(
        validity_conditions=validity_conditions,
        quality_criteria=quality_criteria,
        preference=preference,
    )
