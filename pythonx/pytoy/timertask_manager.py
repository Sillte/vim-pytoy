import vim

import inspect
class TimerTaskManager:
    """Using `timer_start` function, it enables asyncronous process 
    executed in VIM main loop. 
    Especially, it is expected to use updating UI of VIM.

    [NOTE]: In the future, it may be a good strategy to  
    prepare the onetime-shot function. 
    """
    FUNCTION_MAP = dict() # name -> function
    TIMER_MAP = dict()  # name -> timer-id 
    VIMFUNCNAME_MAP = dict() # name -> vimfunc_name

    counter = 0

    @classmethod
    def register(cls, func, interval:int=100, name: str | None= None) -> str:
        """Register the function without the argument. 
        """
        interval = int(interval)
        sig = inspect.signature(func)
        if len(sig.parameters) != 0:
            raise ValueError("Callback must be without parameters.")
        
        if name is None:
            name = f"AUTONAME{cls.counter}"

        vim_funcname = f"LoopTask_{name}_{id(func)}"
        if "__name__" in locals():
            prefix = f"{__name__}."
        else:
            prefix = "" 
        
        procedures = f"python3 {prefix}TimerTaskManager.FUNCTION_MAP['{name}']()"

        vim.command(f"""function! {vim_funcname}(timer) 
            {procedures}
            endfunction
            """)
        timer_id = int(vim.eval(f"timer_start({interval}, '{vim_funcname}', {{'repeat': -1}})"))

        cls.FUNCTION_MAP[name] = func
        cls.VIMFUNCNAME_MAP[name] = vim_funcname
        cls.TIMER_MAP[name] = timer_id
        cls.counter += 1
        return name

    @classmethod
    def deregister(cls, name: str):
        if name not in cls.FUNCTION_MAP:
            raise ValueError("No `{name=}` exist for deregistration")

        timer_id = cls.TIMER_MAP[name]
        vim.eval(f"timer_stop({timer_id})")
        vimfunc_name = cls.VIMFUNCNAME_MAP[name]
        vim.command(f"delfunction! {vimfunc_name}")

        del cls.TIMER_MAP[name]
        del cls.VIMFUNCNAME_MAP[name]
        del cls.FUNCTION_MAP[name]

if  __name__ == "__main__":
    pass
