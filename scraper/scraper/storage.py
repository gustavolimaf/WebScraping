"""
storage.py — Persistência dos resultados em JSON e CSV.
"""

import json
import logging
from datetime import datetime
from pathlib import Path

import pandas as pd

from .config import OUTPUT_DIR

log = logging.getLogger(__name__)


def salvar(fichas: list[dict], prefixo: str = "fichas") -> tuple[Path, Path] | None:
    """
    Salva a lista de fichas em JSON e CSV com timestamp no nome.

    Retorna os caminhos (json_path, csv_path) ou None se não houver dados.
    """
    if not fichas:
        log.warning("Nenhum dado para salvar.")
        return None

    ts  = datetime.now().strftime("%Y%m%d_%H%M%S")
    jp  = OUTPUT_DIR / f"{prefixo}_{ts}.json"
    cp  = OUTPUT_DIR / f"{prefixo}_{ts}.csv"

    # JSON — preserva campos ausentes (None) e estrutura completa
    with open(jp, "w", encoding="utf-8") as f:
        json.dump(fichas, f, ensure_ascii=False, indent=2)

    # CSV — utf-8-sig para compatibilidade com Excel
    df = pd.DataFrame(fichas)
    df.to_csv(cp, index=False, encoding="utf-8-sig")

    log.info("═" * 55)
    log.info(f"  Registros : {len(fichas)}")
    log.info(f"  Colunas   : {len(df.columns)}")
    log.info(f"  JSON      : {jp}")
    log.info(f"  CSV       : {cp}")
    log.info("═" * 55)

    return jp, cp