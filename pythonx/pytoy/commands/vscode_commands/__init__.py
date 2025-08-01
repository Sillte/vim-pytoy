from pytoy.command import CommandManager

@CommandManager.register(name="Qnext")
def q_next():
    from pytoy.ui.pytoy_quickfix import PytoyQuickFix
    PytoyQuickFix().next()

@CommandManager.register(name="Qprev")
def q_prev():
    from pytoy.ui.pytoy_quickfix import PytoyQuickFix
    PytoyQuickFix().prev()

@CommandManager.register(name="QQ")
def QQ():
    from pytoy.ui.pytoy_quickfix import PytoyQuickFix
    PytoyQuickFix().go()

#@CommandManager.register(name="UniqueEditor")
#def unique_editor_command():
#    from pytoy.ui.pytoy_window import PytoyWindow
#    current = PytoyWindow.get_current()
#    current.unique(within_tab=False)
#
#@CommandManager.register(name="UniqueWindow")
#def unique_window_command():
#    from pytoy.ui.pytoy_window import PytoyWindow
#    current = PytoyWindow.get_current()
#    current.unique(within_tab=True)
#
