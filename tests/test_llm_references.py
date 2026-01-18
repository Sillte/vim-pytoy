from pytoy.tools.llm.references import ReferenceCollector
from pathlib import Path

def test_naive():
    stored_folder = "./__save"
    collector = ReferenceCollector(stored_folder)
    ret = collector.collect_all("./")
    assert ret is not None
    assert Path(stored_folder).exists()


if __name__  == "__main__":
    pass
