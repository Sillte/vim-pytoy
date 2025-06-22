from pytoy.command_manager import CommandManager

@CommandManager.register(name="Qnext")
def q_next():
    from pytoy.ui_pytoy.pytoy_quickfix import PytoyQuickFix
    PytoyQuickFix.next()

@CommandManager.register(name="Qprev")
def q_prev():
    from pytoy.ui_pytoy.pytoy_quickfix import PytoyQuickFix
    PytoyQuickFix.prev()

@CommandManager.register(name="QQ")
def QQ():
    from pytoy.ui_pytoy.pytoy_quickfix import PytoyQuickFix
    PytoyQuickFix.go()

@CommandManager.register(name="OnlyThisEditor")
def sweep_editors_command():
    from pytoy.ui_pytoy.vscode.document_user import sweep_editors
    sweep_editors() 
