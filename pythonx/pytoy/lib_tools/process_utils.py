
def force_kill(pid: int, timeout: float = 1.0):
    import psutil

    try:
        proc = psutil.Process(pid)

        # 子プロセスを再帰的に取得（新しい順で処理が安全）
        children = proc.children(recursive=True)
        for child in children:
            try:
                child.terminate()
            except Exception:
                pass

        _, alive = psutil.wait_procs(children, timeout=timeout)

        for still_alive in alive:
            try:
                still_alive.kill()
            except Exception:
                pass

        # 親も terminate → wait → kill fallback
        try:
            proc.terminate()
            proc.wait(timeout=timeout)
        except psutil.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=timeout)
    except psutil.NoSuchProcess:
        pass
    except psutil.AccessDenied:
        print("pid cannot be handled.")
    except Exception as e:
        print(f"Unexpected error: {e}")


# `import psutil` may take time.
def find_children_pids(parent_pid: int) -> list[int]:
    """Return the list of children process."""
    import psutil

    try:
        parent = psutil.Process(parent_pid)
        return [elem.pid for elem in parent.children(recursive=True)]
    except psutil.NoSuchProcess:
        return []
