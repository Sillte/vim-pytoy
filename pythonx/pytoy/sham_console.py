import subprocess
import time
from subprocess import PIPE
from threading import Thread, Lock
from queue import Queue, Empty


class ShamConsole:
    """Interactively, execute command.

    Different from preceudo-console,
    this is far from perfect.

    If the target `cmd` performs buffering,
    then non-blocking processing is impossible.

    Note:
    (2020/01/23) `python(w)` is inappropriate due to this reason.

    """

    def __init__(self, cmd="ipython", read_interval=0.1):
        self._is_alive = False
        self.cmd = cmd
        self.read_interval = read_interval

    def start(self):
        """Start the session."""
        if self._is_alive:
            raise RuntimeError(
                "Currently, running. Priorly, `stop` is should be called."
            )
        self._proc = None  # subprocess.POPEN
        self._stdout_hist = ""  # Previous `stdout`
        self._stderr_hist = ""  # Previous `stderr`
        self._stdout_diff = ""  # Difference.
        self._stdout_diff_queue = Queue()  #
        self._stderr_diff = ""
        self._stderr_diff_queue = Queue()

        self.proc = subprocess.Popen(
            self.cmd,
            shell=True,
            stdin=PIPE,
            stdout=PIPE,
            stderr=PIPE,
            text=True,
            encoding="utf8",
        )
        self._stdout_thread = Thread(
            target=self._readthread,
            args=(self.proc.stdout, self._stdout_diff_queue),
            daemon=True,
        )
        self._stderr_thread = Thread(
            target=self._readthread,
            args=(self.proc.stderr, self._stderr_diff_queue),
            daemon=True,
        )
        self._stdout_thread.start()
        self._stderr_thread.start()
        self._is_alive = True

    def is_alive(self):
        """Return whether"""
        return self._is_alive

    def send(self, arg: str):
        """Send the `string` to `Standard Input`."""
        self.proc.stdin.write(arg)
        self.proc.stdin.flush()

    @property
    def stdout(self):
        """Return all the history of `stdout`."""
        self._stdout_diff += self._unload_queue(self._stdout_diff_queue)
        return self._stdout_hist + self._stdout_diff

    def get_stdout(self):
        """Get `stdout`, only updated strings."""
        self._stdout_diff += self._unload_queue(self._stdout_diff_queue)
        diff = self._stdout_diff

        # Update of `diff` and `history`.
        self._stdout_hist += diff
        self._stdout_diff = ""
        return diff

    @property
    def stderr(self):
        """Return all the history of `stderr`."""
        self._stderr_diff += self._unload_queue(self._stderr_diff_queue)
        return self._stderr_hist + self._stderr_diff

    def get_stderr(self):
        """Get `stderr`, only updated strings."""
        self._stderr_diff += self._unload_queue(self._stderr_diff_queue)
        diff = self._stderr_diff

        # Update of `diff` and `history`.
        self._stderr_hist += diff
        self._stderr_diff = ""
        return diff

    def _readthread(self, pipe, queue):
        while True:
            try:
                line = pipe.readline()
                # print("line", line)
            except ValueError as e:  # closed `pipe`.
                break
            else:
                queue.put(line)
            time.sleep(self.read_interval)

    def _unload_queue(self, queue):
        """The items  of `queue`s are
        dumped and returned.
        """
        result = ""
        while True:
            try:
                line = queue.get_nowait()
            except Empty:
                break
            else:
                result += line
                queue.task_done()
            time.sleep(self.read_interval)
        return result

    def stop(self):
        """Stop the application."""
        try:
            outs, errs = self.proc.communicate()  # Handling of final buffer.
        except IndexError:
            # Since we stop the process in the middle of processsing,
            # `communicate` may fail.
            pass
        else:
            self._stdout_diff += self._unload_queue(self._stdout_diff_queue)
            self._stderr_diff += self._unload_queue(self._stderr_diff_queue)
            if outs:
                self._stdout_diff += outs
            if errs:
                self._stderr_diff += errs
        self._stdout_thread.join()
        self._stderr_thread.join()
        self._is_alive = False

    def restart(self):
        """Restart it.
        """
        if self.is_alive:
            self.kill()
        self.start()


# ## Memorandum

# ### Implementation of  `Popen.communication`.

# Naively, the below codes are executed.
# However, exception handling and the usage of `Thread` is performed.
# is necessary.
# Hence, I think it is better to use `proc.communicate().
# ```python
# ## proc: Popen()...
# proc.stdin.close()
# outs = proc.stdout.read()
# errs = proc.stderr.read()
# proc.stdout.close()
# proc.stderr.close()
# proc.wait()
# ```

# ### Non-blocking handling of `stdout` and `stderr`.

# Currently, if the executing program is buffering,
# then non-blocking processing is impossible.
# `python(w)` seems to perform buffering for interactive interpreter
# even with `-u` option.
#
# To counter this problem,
# `pseudo console`'s usage seems to be required.
# Firsly, I'd like to wait for works of Python's standard library.
#
# Ref:
# https://github.com/spyder-ide/pywinpty


if __name__ == "__main__":
    # Naive use-case
    target = ShamConsole("ipython")
    target.start()
    target.send(
        "3 + 3; print('ABC' * 6, flush=True); import sys; sys.stdout.flush()\nimport time; time.sleep(1) \n"
    )
    target.send("assert False")
    import time

    time.sleep(2)

    print("get_stdout", target.get_stdout(), flush=True)
    print("get_stderr", target.get_stderr(), flush=True)
    import time

    time.sleep(5)
    # target.send("3 + 4; print('XYZ'); import sys; sys.stdout.flush();")
    # print("get_stdout", target.get_stdout())
    # target.send(TEXT)
    # target.send(TEXT2)
    # import time
    # time.sleep(3)
    # print("get_stdout", target.get_stdout())
    target.send(
        "3 + 3; print('ABC' * 6, flush=True); import sys; sys.stdout.flush()\nimport time; time.sleep(1) \n"
    )
    target.send("assert False")
    import time

    time.sleep(2)

    print("get_stdout", target.get_stdout(), flush=True)
    print("get_stderr", target.get_stderr(), flush=True)
    import time

    time.sleep(5)
    target.kill()
    print("---stdout---")
    print(target.stdout)
    print("---stderr---")
    print(target.stderr)

    for _ in range(5):
        target.restart()
        target.send(
            "3 + 3; print('ABC' * 6, flush=True); import sys; sys.stdout.flush()\nimport time; time.sleep(1) \n"
        )
        target.send("assert False")
        import time

        time.sleep(2)
        print("get_stdout", target.get_stdout(), flush=True)
