from pytoy.tools.llm.references.converters import ReferenceConverterManager
from pytoy.tools.llm.references.models import DatasetMeta, ReferenceDataset, ReferenceInfo, ReferencePathPair, ResourceUri


import os
from pathlib import Path
from typing import Final, Sequence


class ReferenceCollector:
    info_suffix: Final[str] = ".json"

    def __init__(self, stored_folder: Path | str, reference_coverter_manager: ReferenceConverterManager | None = None) -> None:
        reference_coverter_manager = reference_coverter_manager or ReferenceConverterManager()
        self._converter_manager = reference_coverter_manager

        self._stored_folder = Path(stored_folder)
        self._stored_folder.mkdir(exist_ok=True, parents=True)

        self._exclude_predicators = [lambda item: item.startswith("."), lambda item: item.startswith("__")]

    def _filter_dirs(self, dirs: Sequence[str]) -> list[str]:
        for ex_predictor in self._exclude_predicators:
            dirs = [item for item in dirs if not ex_predictor(item)]
        return list(dirs)

    def collect_all(self, root_folder: Path | str) -> ReferenceDataset:
        root_folder = Path(root_folder)
        # https://docs.python.org/3/library/os.html#os.walk
        filepaths = []
        for root, dirs, files in os.walk(root_folder, topdown=True):
            # Logic for exclusion.
            if Path(root) == self._stored_folder:
                dirs[:] = []
                continue
            dirs[:] = self._filter_dirs(dirs)

            filepaths += [Path(root) / filename for filename in files]

        path_pairs = self._dump_reference(root_folder, filepaths)
        meta = DatasetMeta(root_folder=root_folder)
        dataset = ReferenceDataset(meta=meta,path_pairs=path_pairs)
        dataset.dump(self._stored_folder)
        return dataset

    def _dump_reference(self, root_folder: Path, source_paths: list[Path]) -> list[ReferencePathPair]:
        stored_folder = self._stored_folder
        ref_paths = []
        for filepath in source_paths:
            if converter := self._converter_manager.pick(ResourceUri.from_any(filepath)):
                uri = ResourceUri.from_any(filepath)
                hash_id = uri.hash_id
                info_path = stored_folder / f"{hash_id}{self.info_suffix}"
                markdown_path = info_path.with_suffix(".md")

                info = ReferenceInfo.from_path(filepath, root_folder)
                info_path.write_text(info.model_dump_json(), encoding="utf8")
                markdown = converter.to_markdown(filepath)
                markdown_path.write_text(markdown, encoding="utf8")
                ref_paths.append(ReferencePathPair(markdown_path=markdown_path, info_path=info_path))
        return ref_paths

if __name__ == "__main__":
    collector = ReferenceCollector(r"C:\Users\zaube\Desktop\Storing")
    collector.collect_all(r"C:\LocalLibrary\PublicLibrary\vim-pytoy\pythonx\pytoy\tools\llm\references")