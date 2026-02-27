from typing import Mapping,  get_args, Any
from pydantic import BaseModel
import toml
import re


def _generate_literal_comments(model: type[BaseModel]) -> dict[str, str]:
    """Literal 型のフィールドに対して options コメントを作る
    """
    comments = {}
    for name, field_info in model.model_fields.items():
        ann = field_info.annotation
        origin = getattr(ann, "__origin__", None)
        if origin is None:
            origin = ann
        if origin.__class__.__name__ == 'LiteralMeta' or str(origin).startswith('typing.Literal'):
            options = get_args(ann)
            options_str = " / ".join(str(opt) for opt in options)
            comments[name] = f"{name} options: {options_str}"
    return comments


def _insert_comments_in_toml(toml_text: str, model_map: Mapping[str, type[BaseModel]]) -> str:
    """
    TOML 文字列に Literal コメントを挿入する
    model_map: table_name -> BaseModel class
    """
    lines = toml_text.splitlines()
    new_lines = []
    current_table = None

    for line in lines:
        stripped = line.strip()
        # テーブル名の検出
        if stripped.startswith("[") and stripped.endswith("]"):
            current_table = stripped[1:-1]
            new_lines.append(line)
            continue

        if "=" in line and current_table in model_map:
            key = line.split("=", 1)[0].strip()
            cls = model_map[current_table]
            comments = _generate_literal_comments(cls)
            if key in comments:
                new_lines.append(f"# {comments[key]}")
        new_lines.append(line)

    return "\n".join(new_lines)


def _convert_multiline_strings(toml_text: str) -> str:
    # = の後のスペースを許容し、改行を含む文字列だけを対象
    pattern = r'^(?P<indent>\s*[^#\s].*?=)(?P<space>\s*)"(?P<content>(?:[^"\\]|\\.)*\\n(?:[^"\\]|\\.)*)"'

    def repl(m):
        indent = m.group("indent")   # = まで含めた左側（インデント含む）
        space = m.group("space")     # = の後の空白
        content = m.group("content")
        # \n を実際の改行に置換
        content_real = content.replace(r"\n", "\n")
        # インデントを維持して複数行リテラルに変換
        return f'{indent}{space}"""\n{content_real}\n"""'

    # multilineフラグで各行に対応
    return re.sub(pattern, repl, toml_text, flags=re.MULTILINE)


class TomlConverter:
    """Convert TOML string into `basemodels` back and force.
    """
    def __init__(self):
        pass

    def from_basemodels(self, models: Mapping[str, BaseModel]) -> str:
        """
        BaseModel dict -> TOML文字列
        Literalはコメントとして options を自動付加
        """
        # dict に変換
        data = {k: v.model_dump() for k, v in models.items()}
        # TOML 文字列化
        toml_text = toml.dumps(data)
        # コメント差し込み
        toml_text =  _insert_comments_in_toml(toml_text, {k: type(v) for k, v in models.items()})
        # Conver to `multiline_strings`.
        toml_text =  _convert_multiline_strings(toml_text)
        return toml_text

    def to_basemodels(self, toml_text: str, class_map: Mapping[str, type[BaseModel]]) -> Mapping[str, Any]:
        """
        TOML文字列 -> BaseModel dict
        """
        try:
            data = toml.loads(toml_text)
        except Exception:
            raise ValueError("Text is not valid `TOML` file.")
        result = {}
        for table_name, table_data in data.items():
            if table_name not in class_map:
                raise ValueError(f"No BaseModel class mapped for table: {table_name}")
            cls = class_map[table_name]
            result[table_name] = cls(**table_data)
        return result

if __name__ == "__main__":
    # -------------------------------
    # 使用例
    # -------------------------------
    from typing import Literal

    class SubPolicy(BaseModel):
        option: Literal["on", "off"]
        description: str

    class EvolvePolicy(BaseModel):
        degree: Literal["auto", "low", "medium", "high", "extreme"]
        comment: str
        sub_policy: SubPolicy

    class Compass(BaseModel):
        progress: str
        objective: str


    models = {
        "evolve_policy": EvolvePolicy(
            degree="medium",
            comment="中くらいに設定",
            sub_policy=SubPolicy(option="on", description="サブポリシー説明\n複数行")
        ),
        "compass": Compass(
            progress="shaping",
            objective="物語を形成する\n複数行テキスト"
        )
    }

    converter = TomlConverter()
    toml_text = converter.from_basemodels(models)
    print("=== TOML ===")
    print(toml_text)

    # 復元
    class_map = {
        "evolve_policy": EvolvePolicy,
        "compass": Compass
    }
    restored = converter.to_basemodels(toml_text, class_map)
    print("\n=== Restored ===")
    for k, v in restored.items():
        print(k, v)


    from typing import Literal
    from pydantic import BaseModel

    # -------------------------------
    # ネストモデル
    # -------------------------------
    class SubPolicy(BaseModel):
        option: Literal["on", "off"]
        description: str

    class EvolvePolicyNested(BaseModel):
        degree: Literal["auto", "low", "medium", "high", "extreme"]
        comment: str
        sub_policy: SubPolicy

    class CompassNested(BaseModel):
        progress: str
        objective: str

    # -------------------------------
    # ネストテストケース
    # -------------------------------
    def test_nested_toml_converter():
        models = {
            "evolve_policy": EvolvePolicyNested(
                degree="medium",
                comment="中くらいに設定",
                sub_policy=SubPolicy(option="on", description="サブポリシー説明\n複数行")
            ),
            "compass": CompassNested(
                progress="shaping",
                objective="物語を形成する\n複数行テキスト"
            )
        }

        converter = TomlConverter()
        
        # 1. BaseModel -> TOML 変換
        toml_text = converter.from_basemodels(models)
        print("=== ネスト TOML 出力 ===")
        print(toml_text)
        
        # 確認
        assert "degree" in toml_text
        assert "sub_policy" in toml_text
        assert "options" in toml_text  # Literal コメントがあること
        assert '"""' in toml_text      # 複数行文字列が """ """ で囲まれる

        # 2. TOML -> BaseModel 復元
        class_map = {"evolve_policy": EvolvePolicyNested, "compass": CompassNested}
        restored_models = converter.to_basemodels(toml_text, class_map)

        # 型チェック
        assert isinstance(restored_models["evolve_policy"], EvolvePolicyNested)
        assert isinstance(restored_models["evolve_policy"].sub_policy, SubPolicy)
        
        # 値チェック
        assert restored_models["evolve_policy"].degree == "medium"
        assert restored_models["evolve_policy"].sub_policy.option == "on"
        assert restored_models["evolve_policy"].sub_policy.description.strip("\n") == "サブポリシー説明\n複数行".strip("\n")
        assert restored_models["compass"].objective.strip("\n") == "物語を形成する\n複数行テキスト".strip("\n")

        # 出力確認
        print("=== ネスト復元モデル ===")
        for k, v in restored_models.items():
            print(k, v)

    # 実行
    test_nested_toml_converter()