class NaivePluginError(Exception):
    """Base exception for naive plugin errors."""


class NaivePluginNotFoundError(NaivePluginError):
    """Raised when a named naive plugin cannot be found."""


class InvalidNaivePluginError(NaivePluginError):
    """Raised when a plugin definition is invalid or its name is duplicated."""


class NaivePluginLoadError(NaivePluginError):
    """Raised when loading a plugin module or creating its plugin fails."""
