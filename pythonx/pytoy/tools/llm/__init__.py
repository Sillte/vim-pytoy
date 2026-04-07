from textwrap import dedent
from pytoy.shared.lib.event.domain import Event
from pytoy.tools.llm.pytoy_fairy import PytoyFairy


class ReferenceDatasetConstructor:
    def __init__(self, pytoy_fairy: PytoyFairy) -> None:
        self.pytoy_fairy = pytoy_fairy
        
    def make_dataset(self) -> None:
        kernel = self.pytoy_fairy.kernel
        buffer = self.pytoy_fairy.buffer
        # First, construct the entire dataset.
        collector = kernel.llm_context.reference_handler.collector
        # [TODO]: In a remote context, we should ensure the `root_folder` is valid.
        # It is better to introduce `filepath` for `PytoyBuffer`.
        if  buffer.is_file:
            root_folder = buffer.file_path.parent
        else:
            root_folder = None
        if not root_folder:
            print("No root folder found for the buffer. Cannot collect references.")
            return
        print(f"{root_folder=} in `ReferenceDatasetConstructor`.")
        collector.collect_all(root_folder)
        
