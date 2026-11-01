import os
from pathlib import Path

from pytoy.devtools.dev_rebooter.models import RebootInfo
from pytoy.devtools.dev_rebooter.rebooter import RebooterWithInfoProtocol


class DummyRebooter(RebooterWithInfoProtocol):
    def __init__(self, root_folder: Path, *, minimal: bool = False, kill_myprocess: bool = True):
        self._root_folder = Path(root_folder)

    def prepare(self) -> RebootInfo:
        cache_folder = (
            Path(os.environ["XDG_CACHE_HOME"]) / "dummy_pytoy"
            if "XDG_CACHE_HOME" in os.environ
            else Path.home() / ".cache" / "dummy_pytoy"
        )
        return RebootInfo.from_cache_folder(cache_folder, self._root_folder)

    def reboot(self, reboot_info: RebootInfo) -> None:
        pass
