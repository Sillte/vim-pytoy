from pytoy.command import CommandManager


@CommandManager.register(name="Qnext")
def q_next():
    from pytoy.ui.pytoy_quickfix import PytoyQuickfix

    PytoyQuickfix().next()


@CommandManager.register(name="Qprev")
def q_prev():
    from pytoy.ui.pytoy_quickfix import PytoyQuickfix

    PytoyQuickfix().prev()


@CommandManager.register(name="QQ")
def QQ():
    from pytoy.ui.pytoy_quickfix import PytoyQuickfix

    PytoyQuickfix().jump()
