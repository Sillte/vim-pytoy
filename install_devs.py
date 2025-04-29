"""Install the `development` version of libraries 

Here, this mechanism heavily relies on `myvimrc` 
(https://github.com/Sillte/myvimrc). 

"""

from pathlib import Path
import shutil

_this_folder = Path(__file__).absolute().parent

PLUGUIN_NAME = "pytoy"


def _get_plugin_folder():
    home = Path.home()
    vim_folder = home / ".vim"
    assert vim_folder.exists()
    plugin_folder = vim_folder / "_plugins"
    # Accorind to https://github.com/Sillte/myvimrc,
    # the experimental plugin should reside there.
    return plugin_folder


if __name__ == "__main__":
    plugin_folder = _get_plugin_folder()
    plugin_folder.mkdir(exist_ok=True)

    dst_folder = plugin_folder / PLUGUIN_NAME

    if dst_folder.exists():
        import time

        shutil.rmtree(dst_folder)
        time.sleep(0.3)

    def ignore_dot_git(parent, children):
        return [elem for elem in children if elem == ".git"]

    shutil.copytree(_this_folder, dst_folder, ignore=ignore_dot_git)
