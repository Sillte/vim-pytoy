# Text transformation plugins

Add trusted Python plugin files to the global folder returned by
`PytoyConfiguration().get_folder("text_transformation_plugins", location="global")`.

```python
from pytoy.tools.text_transformation_plugin import register_text_transformation


@register_text_transformation(name="uppercase")
def uppercase(content: str) -> str:
    return content.upper()
```

Run a transformation on the current buffer with `:TextTransform uppercase`.
The command completer finds literal names from registered functions without
importing or executing plugin code. Use a string literal for the `name` argument
so it can be completed. The whole buffer content is passed to the function,
and its returned string is applied when the work completes. The optional
`--on-conflict` value defaults to `preserve`: if the buffer changed while the
plugin ran, the original is kept and
the result is shown in a separate buffer. Use `--on-conflict=overwrite` to
replace the buffer even if it changed during processing.

Use `:TextTransformExample` to create a sample plugin file without overwriting
an existing `example.py`. Use `:TextTransformOpenFolder` to open the global
plugin folder in the operating system's file manager.

Plugins run in a worker thread in the editor's Python process. They are trusted
Python code, not sandboxed code; only install plugins you trust.
