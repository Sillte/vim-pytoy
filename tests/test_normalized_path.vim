python3 << EOF
# Makeshift tests for CommandManager.register / exist / deregister.
from unittest import mock
from pytoy.ui.utils import normalize_path, UIEnum

with mock.patch("pytoy.ui.utils.get_ui_enum", return_value=UIEnum.VSCODE):
    path = normalize_path("vscode-remote://wsl%2Bubuntu/home/zaube/.vscode-server/data/Machine/settings.json")
    print(path)
EOF




