from textwrap import dedent
from pytoy.infra.core.models import Event
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
        root_folder = buffer.path.parent
        if not root_folder:
            print("No root folder found for the buffer. Cannot collect references.")
            return
        print(f"{root_folder=} in `ReferenceDatasetConstructor`.")
        collector.collect_all(root_folder)
        
