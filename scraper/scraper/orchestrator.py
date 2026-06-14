"""
orchestrator.py — Orquestra os três níveis de scraping.

Nível 1: listar modelos de uma marca
Nível 2: listar versões de cada modelo
Nível 3: extrair ficha técnica de cada versão
"""

import logging
from datetime import datetime
from urllib.parse import urljoin

from playwright.async_api import async_playwright

from .config   import BASE_URL, SEL_MODELOS, SEL_FICHA
from .browser  import criar_contexto, get_html_aguardando, get_html_simples
from .parser   import parsear_modelos, parsear_versoes, parsear_ficha
from .cleaner  import limpar_fichas

log = logging.getLogger(__name__)


async def raspar_marca(marca: str, dry_run: bool = False) -> list[dict]:
    """
    Raspa todos os modelos e versões de uma marca.
    Se `dry_run=True`, apenas lista modelos/versões sem raspar fichas.
    """
    async with async_playwright() as pw:
        browser, context = await criar_contexto(pw)
        page = await context.new_page()
        try:
            log.info("Aquecendo sessão na home…")
            await get_html_simples(page, BASE_URL)

            # ── Nível 1: modelos ──────────────────────────────
            url_marca = f"{BASE_URL}/carros/{marca}/"
            log.info(f"[Nível 1] Modelos: {url_marca}")
            html = await get_html_aguardando(page, url_marca, SEL_MODELOS)
            if not html:
                log.error("Falha ao carregar página da marca.")
                return []

            modelos = parsear_modelos(html, marca)
            if not modelos:
                log.error("Nenhum modelo encontrado. Verifique o slug da marca.")
                return []

            if dry_run:
                _exibir_dry_run(marca, modelos)
                for m in modelos:
                    html_m = await get_html_simples(page, m["url"])
                    if html_m:
                        versoes = parsear_versoes(html_m, m)
                        for v in versoes:
                            print(f"    ↳ {v['versao_slug']}")
                return []

            # ── Níveis 2 e 3: versões e fichas ───────────────
            todas_fichas = []
            for i, modelo in enumerate(modelos, 1):
                log.info(f"\n── Modelo {i}/{len(modelos)}: {modelo['nome']} ──")

                html_m = await get_html_simples(page, modelo["url"])
                if not html_m:
                    log.warning(f"  Falha ao carregar página do modelo.")
                    continue

                versoes = parsear_versoes(html_m, modelo)
                log.info(f"  [Nível 2] {len(versoes)} versões")

                for j, versao in enumerate(versoes, 1):
                    log.info(f"  [Nível 3] Versão {j}/{len(versoes)}: {versao['versao']}")
                    html_v = await get_html_aguardando(page, versao["url"], SEL_FICHA)
                    if html_v:
                        ficha = parsear_ficha(html_v, versao)
                    else:
                        ficha = {**versao, "erro": "falha_na_requisicao",
                                 "coletado_em": datetime.now().isoformat()}
                    todas_fichas.append(ficha)

            return limpar_fichas(todas_fichas)

        finally:
            await browser.close()


async def raspar_url_unica(url: str) -> list[dict]:
    """Raspa a ficha técnica de uma versão específica via URL direta."""
    partes = url.rstrip("/").split("/")
    versao_info = {
        "marca":       partes[-3] if len(partes) >= 3 else "",
        "modelo":      "",
        "modelo_slug": partes[-2] if len(partes) >= 2 else "",
        "versao":      partes[-1],
        "versao_slug": partes[-1],
        "url":         url,
    }
    async with async_playwright() as pw:
        browser, context = await criar_contexto(pw)
        page = await context.new_page()
        try:
            html = await get_html_aguardando(page, url, SEL_FICHA)
            if not html:
                return [{**versao_info, "erro": "falha_na_requisicao",
                         "coletado_em": datetime.now().isoformat()}]
            ficha = parsear_ficha(html, versao_info)
            if "titulo_pagina" in ficha and not ficha["modelo"]:
                ficha["modelo"] = ficha["titulo_pagina"]
            return limpar_fichas([ficha])
        finally:
            await browser.close()


def _exibir_dry_run(marca: str, modelos: list[dict]) -> None:
    print(f"\n{'─'*60}\nDRY RUN — {len(modelos)} modelos em '{marca}'\n{'─'*60}")
    for m in modelos:
        print(f"  {m['nome']:30s}  {m['url']}")