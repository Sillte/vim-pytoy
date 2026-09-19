from pytoy.shared.command import App

app = App()


@app.command(name="Qnext")
def q_next():
    from pytoy.shared.ui.pytoy_quickfix import Quickfix

    quickfix = Quickfix.current()
    viewer = quickfix.provide_ui("backend")
    viewer.sync_from_ui()
    quickfix.next()
    viewer.sync_to_ui()
    viewer.jump()


@app.command(name="Qprev")
def q_prev():
    from pytoy.shared.ui.pytoy_quickfix import Quickfix

    quickfix = Quickfix.current()
    viewer = quickfix.provide_ui("backend")
    viewer.sync_from_ui()
    quickfix.prev()
    viewer.sync_to_ui()
    viewer.jump()


@app.command(name="QQ")
def QQ():
    from pytoy.shared.ui.pytoy_quickfix import Quickfix

    quickfix = Quickfix.current()
    quickfix.provide_ui("backend").jump()
