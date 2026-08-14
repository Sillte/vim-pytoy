TERM_STDOUT = "__pystdout__"  # TERIMINAL NAME of `stdout`.
TERM_STDERR = "__pystderr__"  # TERIMINAL NAME of `stderr`.


def initialize_plugin(): 
    # Command definitions.
    # Maybe `Command` uses the public interfaces,
    # Hence, `import`s are placed here.
    from pytoy import commands  # NOQA

    from pytoy.contexts.core import GlobalCoreContext 
    context = GlobalCoreContext.get()
    context.llm_import_resolver.import_background()


def run(path=None):
    """Perform `python {path}`."""
    from pytoy.commands.console_command import script_run

    script_run(path=path)


def rerun():
    """Perform `python` with the previous `path`."""
    from pytoy.commands.console_command import script_rerun

    script_rerun()


def stop():
    from pytoy.commands.console_command import script_stop

    script_stop()


def reset():
    from pytoy.commands.console_command import hide_temporary

    hide_temporary()

initialize_plugin()

if __name__ == "__main__":
    print("__name__", __name__)
