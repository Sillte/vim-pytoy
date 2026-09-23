# Reference Package 廃止メモ

## Status

旧 `pytoy.tools.llm.references` パッケージは廃止する。

現時点では、このパッケージを別の実装へ置き換えることはしない。

この文書では、旧実装を記録するとともに、
そこから得られた設計上の知見を残す。

---

## Background

このパッケージは、ローカルファイルやWeb上の資料を収集し、
LLMへ渡しやすい形式に変換・保存するために作られた。

当時は、おおむね次のような処理を一つの仕組みとして扱っていた。

- ファイルの探索
- ファイル形式の判定
- Markdownへの変換
- 資料に関するメタデータの生成
- 変換結果のキャッシュ
- 資料集合の保存
- LLMへ渡すためのテキスト生成

結果として、資料そのものと、
LLMへ資料を渡すための中間処理が
`Reference` という概念の下に集約されていた。

---

## Previous Converter Implementation

当時のConverterは、概ね次のような構造だった。

```python
class ConverterProtocol(Protocol):
    @property
    def extension(self) -> Extension: ...

    @property
    def preference(self) -> int: ...

    def to_markdown(self, path: Path) -> str: ...


class MarkdownConverter:
    @property
    def extension(self) -> Extension:
        return ".md"

    @property
    def preference(self) -> int:
        return 0

    def to_markdown(self, path: Path) -> str:
        return path.read_text()


class MarkItDownConverter:
    @property
    def extension(self) -> Extension:
        return ".pdf"

    @property
    def preference(self) -> int:
        return 10

    def to_markdown(self, path: Path) -> str: ...


class ReferenceConverterManager:
    def __init__(
        self,
        converters: Sequence[ConverterProtocol],
    ) -> None:
        self._converters = converters

    def get(self, extension: Extension) -> ConverterProtocol:
        converters = [converter for converter in self._converters if converter.extension == extension]
        return max(converters, key=lambda converter: converter.preference)
````

実際には `.md`、`.txt`、`.py`、`.docx`、`.pptx`、
`.xlsx`、`.pdf`、`.json`、`.yaml`、`.yml`、`.toml` などを
扱うConverterが存在していた。

---

## What Was Inappropriate

### 1. Converterの出力をMarkdownに固定していた

最も大きな問題は、

```python
def to_markdown(self, path: Path) -> str: ...
```

というAPIだった。

これは一見すると単純で扱いやすいが、

> 「LLMが扱うために資料を別の表現へ変換する」

という問題を、

> 「あらゆる資料をMarkdownへ変換する」

という問題に狭めてしまっている。

実際には、LLMへ資料を渡す場合でも、
常にMarkdownが最適とは限らない。

例えば、

* PDF → Markdown
* PDF → plain text
* PDF → 構造化されたセクション
* HTML → Markdown
* HTML → 本文テキスト
* Excel → 表形式データ
* 画像 → OCRテキスト
* Webページ → 抽出された本文

など、用途によって適した表現は異なる。

したがって、MarkdownはConverterの本質ではなく、
ある一つの出力形式に過ぎない。

---

### 2. 入力を `Path` に固定していた

Converterは、

```python
def to_markdown(self, path: Path) -> str:
```

という形になっていた。

しかし、LLMへ資料を渡す対象は
必ずしもローカルファイルとは限らない。

例えば、

* ローカルファイル
* URL
* Webページ
* メモリ上のデータ
* APIから取得したデータ
* 画像
* その他の外部リソース

などが考えられる。

つまり、

```text
Path → Markdown
```

をConverterの基本モデルにすると、
「何を変換するのか」という問題と
「どこに存在するのか」という問題を
早い段階で固定してしまう。

---

### 3. 拡張子をConverter選択の中心にしていた

Converterの選択は、

```python
converter.extension == extension
```

という考え方を中心にしていた。

これはローカルファイルを扱う場合には便利だが、
拡張子はリソースの本質的な形式を完全には表さない。

例えば、

* MIME type
* Content-Type
* URL
* 実際のファイル内容
* リソースの種類
* 変換可能な表現

など、別の情報が必要になる可能性がある。

また、URLのように拡張子を持たないリソースもある。

したがって、

```text
extension → converter
```

という関係をConverterの基本モデルにすることには
限界がある。

---

### 4. `preference` がConverter選択の詳細を漏らしていた

当時は同じ拡張子に対して複数のConverterを登録できるように、

```python
@property
def preference(self) -> int: ...
```

を持たせていた。

これは実装としては便利だったが、
「どのConverterを選ぶべきか」という判断基準が
Converter自身の数値に埋め込まれていた。

将来的に、

* 出力形式
* コスト
* 変換品質
* 外部ツールの有無
* MIME type
* 利用可能な環境
* ユーザーの要求

などを考慮するようになると、
単純な整数の優先度では表現しにくい。

---

## What Was Still Valuable

旧設計のすべてが不要だったわけではない。

特に、

> 外部リソースを、LLMが扱いやすい表現へ変換する

という責務そのものは、今後も必要になる可能性が高い。

重要なのは、これを `Reference` という概念に結び付けず、
独立した問題として捉え直すことだった。

例えば将来的には、

```text
Resource
    ↓
Representation / Conversion
    ↓
LLM-readable material
```

のような考え方から設計したほうが、
特定のファイル形式やMarkdownに依存しにくい。

ただし、現時点ではそのAPIを決定しない。

---

## Lessons

今回の設計から得られた重要な知見は、

**「現在必要な具体的な変換」と
「将来的に必要になるかもしれない変換の概念」を
同じ抽象化に押し込まない**

ということだった。

当時のConverterは、

```text
Path
  ↓
extension
  ↓
Converter
  ↓
Markdown
```

という具体的な処理から設計されていた。

そのため、最初は分かりやすかった一方で、
扱うリソースや出力形式が増えるにつれて、
Converterそのものが問題領域を狭く定義してしまう。

将来再設計する場合には、
「Markdown Converter」を作り直すのではなく、

> LLMが利用できる表現への変換

という、より一般的な問題から設計を開始する。

---

## Decision

旧 `references` パッケージは削除する。

旧Converterの実装やAPIは、そのまま後継設計へ持ち込まない。

ただし、

> 外部リソースをLLMが扱える表現へ変換する仕組みは、
> 将来的に独立した概念として必要になる可能性がある。

という知見は、この文書に残す。

必要になった時点で、
入力・出力・リソース・変換方式・ provenance などを改めて検討し、
新しい設計として作り直す。
