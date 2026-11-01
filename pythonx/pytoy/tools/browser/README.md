# Browser source

Use `:BrowserSource` to retrieve the page selected by `fairybrowser.sync_page`
and display its HTML source. `--name=<browser-name>` selects a managed browser.

`--simplify` applies `fairybrowser`'s balanced HTML simplification before any
custom transformation. `--transform=<name>` applies the named text transformation
registered in the global `text_transformation_plugins` folder. When both options
are given, simplification runs first. Transformation names are completed from
registered plugin declarations.

The existing `:Browser source` operation accepts the same `--simplify` and
`--transform` options.
