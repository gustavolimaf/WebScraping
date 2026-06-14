"""
config.py — Configurações centrais do scraper.
Altere aqui para ajustar delays, diretórios e URLs base.
"""

from pathlib import Path

# -- URL base
BASE_URL = "https://www.fichacompleta.com.br"

# -- Delays entre requisicoes (ms)
DELAY_MIN = 1500
DELAY_MAX = 3500

# -- Diretorio de saida
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

# -- Playwright
BROWSER_VIEWPORT   = {"width": 1366, "height": 768}
BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
BROWSER_LOCALE      = "pt-BR"
BROWSER_TIMEZONE    = "America/Sao_Paulo"

# -- Seletores CSS
SEL_MODELOS  = "div.mod-grid a.mod-card"
SEL_VERSOES  = "input.versaoComp[rel]"
SEL_FICHA    = "div.ent-ficha-group"