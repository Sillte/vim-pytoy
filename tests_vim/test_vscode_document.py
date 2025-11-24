# Simple test for `Document`.
from pathlib import Path
from pytoy.ui.vscode.uri import Uri
from pytoy.ui.vscode.document import Document


current_doc = Document.get_current()
uri = Uri.from_untitled_name("test_hogehoge")
doc = Document.create(uri)
doc.content = ""
assert doc.content == "",  ("Empty", uri)
doc.content = "Hello!"
assert doc.content == "Hello!", (uri)
doc.show()
assert doc == Document.get_current(), ("change of current", uri)
current_doc.show()

print("Compleleted Test.")
