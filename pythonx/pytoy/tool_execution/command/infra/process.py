# psutil take some times for importing.
def find_children_pids(parent_pid: int) -> list[int]:
    """Return the list of children process."""
    import psutil

    try:
        parent = psutil.Process(parent_pid)
        return [elem.pid for elem in parent.children(recursive=True)]
    except psutil.NoSuchProcess:
        return []
