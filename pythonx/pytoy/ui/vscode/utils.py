import time 

def wait_until_true(condition_func, timeout: float=3.0, n_trials: int=3, initial_wait=None) -> bool:
    """Wait the `condition_func` returns true.  
    If `timeout` passes and this func returns False. 
    """

    interval = timeout / n_trials  
    if initial_wait is None:
        initial_wait = interval // 10
    time.sleep(initial_wait)
    for _ in range(n_trials):
        if condition_func():
            return True
        time.sleep(interval)
    return False
