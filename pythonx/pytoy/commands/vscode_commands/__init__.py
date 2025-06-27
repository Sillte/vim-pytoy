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

@CommandManager.register(name="OnlyThisEditor")
def sweep_editors_command():
    from pytoy.ui.vscode.document_user import sweep_editors
    sweep_editors() 
