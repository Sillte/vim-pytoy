class TextTransformationPluginError(Exception):
    """Base error for text transformation plugins."""


class InvalidTextTransformationPluginError(TextTransformationPluginError):
    """Raised when a plugin registration is invalid or duplicated."""


class TextTransformationPluginLoadError(TextTransformationPluginError):
    """Raised when a plugin module cannot be loaded."""


class TextTransformationNotFoundError(TextTransformationPluginError):
    """Raised when a requested transformation is not registered."""


class InvalidTextTransformationResultError(TextTransformationPluginError):
    """Raised when a transformation does not return a string."""
