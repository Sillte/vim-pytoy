import logging

from pytoy.shared.pytoy_configuration import PytoyConfiguration


def get_llm_logger() -> logging.Logger:
    return PytoyConfiguration().get_logger(location="global", level=logging.INFO)
