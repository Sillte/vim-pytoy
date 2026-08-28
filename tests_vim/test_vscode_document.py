# Simple test for `Document`.
from pytoy.shared.ui.vscode.document import Document
from pytoy.shared.ui.vscode.uri import VSCodeUri

current_doc = Document.get_current()
uri = VSCodeUri.from_untitled_name("test_hogehoge")
doc = Document.create(uri)
doc.content = ""
assert doc.content == "", ("Empty", uri)
doc.content = "Hello!"
assert doc.content == "Hello!", uri
doc.show()
assert doc == Document.get_current(), ("change of current", uri)
current_doc.show()

print("Compleleted Test.")
