from typing import Protocol

from pytoy.ui.pytoy_buffer import PytoyBuffer

class PytoyWindowProtocol(Protocol):

    @property
    def buffer(self) -> PytoyBuffer | None:
         ...

    @property
    def valid(self) -> bool: 
        """Return whether the window is valid or not
        """
        ...
         
    def is_left(self) -> bool: 
        """Return whether this is leftwindow or not.
        """
        ...

    def close(self) -> bool:
        ...
        
class PytoyWindowProviderProtocol(Protocol):
    def get_current(self) -> PytoyWindowProtocol:
        ...
    
