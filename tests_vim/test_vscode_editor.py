from pytoy.shared.ui.vscode.editor import Editor
from pytoy.shared.ui.vscode.uri import VSCodeUri

current = Editor.get_current()
doc = current.document  #  `document` is fixed, here. not dynamic.

assert current.valid
current.focus()
uris = current.get_clean_target_uris_for_unique()

current.close()

uri = VSCodeUri.from_untitled_name("hogehgeo")
editor = Editor.create(uri)
assert editor.valid

doc.show()

print("Test Complete")
