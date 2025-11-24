
from pathlib import Path
from pytoy.ui.vscode.uri import Uri
from pytoy.ui.vscode.document import Document
from pytoy.ui.vscode.editor import Editor

current = Editor.get_current()
doc = current.document #  `document` is fixed, here. not dynamic.

assert current.valid
current.focus()
uris = current.get_clean_target_uris_for_unique()

current.close()

doc.show()
print("Test Complete")

