"""IPython Terminal 

NOTE:
    When you handle `vim.buffer`, you shoud be careful not to access at the same time.   
    I wonder, they are not `thread-safe`?  
"""
import vim
import time 
import re
from threading import Thread
from queue import Queue, Empty

from pytoy.infra.timertask import TimerTask
from pytoy.ui.pytoy_buffer import make_buffer
from pytoy.ui import get_ui_enum, UIEnum

    
class IPythonTerminal:
    # vim functions. 
    def v_sendkeys(self, buffer: int, content: str, naive: bool = True):
        if naive:
            vim.command(f"call term_sendkeys({buffer}, '{content}')")
        else:
            content = content.replace("'", '"')
            #json_content = json.dumps(content) 
            #vim.command(f"""call term_sendkeys({buffer}, json_decode('{json_content}'))""")
            vim.command(f"call term_sendkeys({buffer}, '{content}')")


    def v_start(self, command, options):
        import json 
        import shlex
        safe_json = json.dumps(options) 
        safe_json = shlex.quote(safe_json)
        vim.command(f"call term_start('{command}', json_decode({safe_json}))")

    def v_status(self, buffer: int):
        ret = vim.eval(f"term_getstatus({buffer})")
        if isinstance(ret, bytes):
            return ret.decode()
        return str(ret)


    # ## Special handling as for first execution. 
    # * The first activation must be performed specially.
    #   This is because the terminal may not reach the state of acceptance of commands.
    # 
    # ## State of the this class.
    # * `IDLE`: terminal can accept any `send_keys`   
    # * `RUNNING`: terminal is currently running.  
    #
    # `send` surely invokes transient of `state`.
    # - If `IDLE`, then it becomes `RUNNING` by `send`.
    # - If `RUNNING`, then it returns to `IDLE.
    #   Then, performs `send`.   

    def __init__(self, output_bufname=None):
        if get_ui_enum() != UIEnum.VIM: 
            raise RuntimeError("This class is only available in VIM")
        term_name = "__IPYTYON_TERM__"
        self.maximum_line = 1000  # The maximum line for buffer.
        self.in_pattern = re.compile(r"^In \[(\d+)\]:")

        # Whether the execution is first or not 
        # affects whether to wait for preparation of terminal. 
        self._is_first_execution = True

        if output_bufname is None:
            output_bufname = "IPYTHON"
        self.term_buffer:int = self._start_term(term_name)
        self.term_name = term_name


        pytoy_buffer = make_buffer(output_bufname, "vertical")

        from pytoy.ui.pytoy_buffer.impl_vim import PytoyBufferVim
        assert isinstance(pytoy_buffer.impl, PytoyBufferVim)

        self.pytoy_buffer = pytoy_buffer
        self.stdout_queue = Queue()
        self.consume_task = None
        self.output_buffer: int = pytoy_buffer.impl.buffer.number
        # Settings for buffer.
        vim.buffers[self.output_buffer].options["buftype"] = "nofile"
        vim.buffers[self.output_buffer].options["swapfile"] = False

        # Thread related variables.
        self.running_thread = None
        self._running_terminate = False
        

    def stop(self):
        self.to_idle()
        self.v_sendkeys(self.term_buffer, "\03", naive=True)  # <ctrl-c>
        # I do not know, however, the time-interval is mandatory to send the control code.
        time.sleep(0.05)

    def is_idle(self) -> bool:
        return self.running_thread is None

    def to_idle(self):
        """Transit to `IDLE` state.  
        """
        if self.is_idle():
            return
        assert self.running_thread is not None
        if not self.running_thread.is_alive():
            self._consume_queue()
            if self.consume_task:
                TimerTask.deregister(self.consume_task)
            self.running_thread = None
            self.consume_task = None
            return 
        self._running_terminate = True
        self.running_thread.join()
        self._consume_queue()
        if self.consume_task:
            TimerTask.deregister(self.consume_task)
        self._running_terminate = False
        self.running_thread = None
        self.consume_task = None

    def _consume_queue(self):
        while self.stdout_queue.qsize():
            try:
                line = self.stdout_queue.get_nowait()
                self.pytoy_buffer.append(line)
            except Empty:
                break

    def to_running(self):
        """Transit to `RUNNING` state. 
        This function must be called at the start of `send` function. 
        This is mainly due to the acquisition of **start_time_lines**.

        """
        if not self.is_idle():
            print("ERROR@to_running")
            self.to_idel()
        self._running_terminate = False
        self.running_thread = Thread(target=self._loop_function, daemon=True)
        self.consume_task = TimerTask.register(self._consume_queue, 300)
        self.running_thread.start()

    def _loop_function(self):
        start_term_lines = len(vim.buffers[self.term_buffer])  # The start point.
        t_term_lines = start_term_lines  # transcribed terminal lines.
        term_buf: "buffer" = vim.buffers[self.term_buffer]
        output_buf: "buffer" = vim.buffers[self.output_buffer]

        def _is_terminated():
            # Whether the snippets execution is finished?  
            n_line = len(vim.buffers[self.term_buffer])
            if n_line == start_term_lines:  # processing does not yet start.
                return False
            term_buf = vim.buffers[self.term_buffer]
            last_line = term_buf[-1]
            if self.in_pattern.match(last_line):
                return True
            return False

        def _appendbufline(buf, string):
            # If you `buffer` is directly written, then problem occurs. 
            # Hence, this function is prepared. 

            # order is important.
            # escape is required.
            #string = string.replace("\\", "\\\\")
            #string = string.replace(r'"', r'\"')
            #string = string.replace(r"'", r"''")
            #server = vim.eval("v:servername")
            #func = vim.Function("remote_expr")
            #v = func(server, rf'execute("call appendbufline({buf}, \'$\', \'{string}\')")')
            self.stdout_queue.put(string)

        def _transcript():
            nonlocal t_term_lines
            term_buf: "buffer" = vim.buffers[self.term_buffer]
            output_buf: "buffer" = vim.buffers[self.output_buffer]
            while t_term_lines < len(term_buf):
                if len(output_buf) < self.maximum_line:  
                    # output_buf.append(term_buf[t_term_lines])
                    _appendbufline(self.output_buffer, term_buf[t_term_lines])
                    t_term_lines += 1
                else:
                    _appendbufline(self.output_buffer, "`stdout` is full.")
                    # output_buf.append("`stdout` is full.")
                    break

        def _inner():
            try:
                if _is_terminated():
                    self._running_terminate = True
                _transcript()
            except Exception as e:
                output_buf.append(str(e))
                self._running_terminate = True
            vim.command(f"redraw")

        while (not self._running_terminate):
            time.sleep(0.5)   # It seems this is required.
            TimerTask.execute_oneshot(_inner, 1)

            # (2022/02/06) I wonder whether it is effecive?
            #output_buf.append(f"_running_terminate {self._running_terminate}")
            
        # (2022/07/03): This procedure seems required.
        #time.sleep(0.5)
        #vim.command(f"redraw")


    def reset_output(self):
        """Reset the output_buffer.
        """
        try:
            out_buf = vim.buffers[self.output_buffer]
            out_buf[:] = None
        except vim.error:
            # maybe error occurs at the first.
            pass

    def transcript(self):
        """Transcript the buffer's content.
        """
        in_buf = vim.buffers[self.term_buffer]
        out_buf = vim.buffers[self.output_buffer]
        try:
            out_buf[:] = None
        except vim.error:
            # maybe error occurs at the first.
            pass
        for line in in_buf:
            out_buf.append(line)

    def send(self, text):

        # important to invoke this snippets before `sendkeys`.
        if self._is_first_execution:
            self.reset_output()
            thread = Thread(target=self._send_first, args=(text, ), daemon=True)
            thread.start()
            self._is_first_execution = False
            return 
        self.to_idle()
        # The position is important.
        # Here, it is assured that another `Thread` does not modify the buffer. 
        self.reset_output() 
        self.to_running()
        # The running codes are stopped.
        self.v_sendkeys(self.term_buffer, "\03", naive=True)  # <ctrl-c>
        # I do not know, however, the time-interval is mandatory to send the control code.
        time.sleep(0.02)

        self._cpaste(text, 0.1)

    def _send_first(self, text):
        """
        At first, it is uncertain that terminal buffer is available.   
        You have to check `vim.buffers`, but the update of it is not performed
        until the processing is returned to the caller of this class.  

        Hence, this should be to called in another `Thread`.
        And this function perform as below. 

        * Wait until the terminal can accept the `send_keys`.
        * perform `send` to `ipython-terminal`.


        Notice that `print` in another thread may cause problem. 
        """
        try:
            self.to_idle()
            def _is_prepare_finished():
                term_buf = vim.buffers[self.term_buffer]
                if not len(term_buf):
                    return False
                last_line = term_buf[-1]
                # print("last_line", last_line, len(term_buf))
                if self.in_pattern.match(last_line):
                    return True
                return False
            started_time = time.time()
            while True:
                if 5 < time.time() - started_time:
                    print("Peculiarity happens at activation of `ipython`.")
                    break
                if _is_prepare_finished():
                    break
                time.sleep(0.1)

            self.to_running()
            #self._cpaste(text)
            TimerTask.execute_oneshot(lambda: self._cpaste(text), 1) 

        except Exception as e:
            print("Error _send_first", str(e))

    def _cpaste(self, text, wait_time=0.1):
        """Common processing of `cpaste`. 
        """
        self.v_sendkeys(self.term_buffer, "%cpaste -q\n", naive=True)
        # I do not know, however, 
        # this `wait_time` seems important.
        time.sleep(wait_time)
        text = text.replace("\n", "\r")
        self.v_sendkeys(self.term_buffer, text, naive=False)
        self.v_sendkeys(self.term_buffer, "\r--\r", naive=True)


    def send_current_line(self):
        """Send the current line.
        """
        line = vim.current.line
        self.send(line)

    def send_current_range(self):
        """Send the current range.
        """
        start_line = int(vim.eval("line(\"'<\")"))
        end_line = int(vim.eval("line(\"'>\")"))
        buf = vim.current.buffer
        lines = buf[start_line - 1:end_line]

        # (2022/07/06) 
        # You have to solve's indent problem. 
        # Maybe the start of the line starts space. 
        prev_space = re.match(r"\s*", lines[0]).end()
        def _to_trim(line, trim_space):
            s_space = re.match(r"\s*", line).end()
            return line[min(s_space, trim_space):]
        lines = [_to_trim(line, prev_space) for line in lines]
        lines = "\n".join(lines)
        lines = lines.strip()

        self.send(lines)


    ## Terminal Related utilities

    def assure_alive(self):
        if not self._is_term_alive():
            self.term_buffer = self._start_term(self.term_name)
    
    def reset_term(self):
        """Reboot `terminal`. 
        """
        vim.command(f"bdelete! {self.term_buffer}")
        self.assure_alive()


    def _is_term_alive(self):
        """Return whether the terminal is alive or not.
        """
        if self.term_buffer is None:
            return False
        status = self.v_status(self.term_buffer)
        return status == "running"

    def _start_term(self, term_name:str) -> int:
        """Start the terminal.
        """
        bufno = self._try_fetch(term_name)
        if bufno:
            print("skip for `term_start`.")
            term_buffer = bufno
        else:
            options = dict()
            options["term_name"] = term_name
            options["term_kill"] = "quit"
            options["hidden"] = True
            term_buffer = self.v_start("ipython", options)
            self._is_first_execution = True

            # Though, mainly waiting is performed below,
            # Experimentally, the wait here is important to prevent problem? 
            # (2021/02/01): It seems unnecessary here. 
            # However, the below processing seem mandatory.
            #time.sleep(0.5)

            # You should wait the sufficient time.  
            # However, the waiting mechanism 
            # should be embedded in another `Thread`
            # because `vim.buffers` are not updated until 
            # this call returns. 
            # See `_send_first` and `Thread`.
        return term_buffer

    def _try_fetch(self, term_name) ->int:
        bufno = int(vim.eval(f'bufnr("{term_name}")'))
        if 0 < bufno:
            status = self.v_status(bufno)
            print("status", status)
            if status == "running":
                return bufno
        return None
