from pytoy.shared.command import App


app = App()


@app.command(name="Qnext")
def q_next():
    from pytoy.shared.ui.pytoy_quickfix import PytoyQuickfix

    PytoyQuickfix().next()


@app.command(name="Qprev")
def q_prev():
    from pytoy.shared.ui.pytoy_quickfix import PytoyQuickfix

    PytoyQuickfix().prev()


@app.command(name="QQ")
def QQ():
    from pytoy.shared.ui.pytoy_quickfix import PytoyQuickfix

    PytoyQuickfix().jump()
