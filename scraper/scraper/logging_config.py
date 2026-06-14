"""
logging_config.py -- Configuracao centralizada de logging.
"""

import logging
from .config import OUTPUT_DIR


def configurar_logging() -> None:
    """
    Configura log para console e arquivo.
    mode="w" garante que o arquivo comeca limpo a cada execucao.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(OUTPUT_DIR / "scraper.log", mode="w", encoding="utf-8"),
        ],
    )