"""
browser.py — Inicialização do Playwright e helpers de navegação.
"""

import random
import logging
from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout
from .config import (
    BROWSER_VIEWPORT, BROWSER_USER_AGENT, BROWSER_LOCALE,
    BROWSER_TIMEZONE, DELAY_MIN, DELAY_MAX,
)

log = logging.getLogger(__name__)


async def criar_contexto(playwright):
    """Lança Chromium com fingerprint realista para evitar detecção."""
    browser = await playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    context = await browser.new_context(
        viewport=BROWSER_VIEWPORT,
        user_agent=BROWSER_USER_AGENT,
        locale=BROWSER_LOCALE,
        timezone_id=BROWSER_TIMEZONE,
        extra_http_headers={
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8",
            "DNT": "1",
        },
    )
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        Object.defineProperty(navigator, 'plugins',   { get: () => [1, 2, 3] });
        window.chrome = { runtime: {} };
    """)
    return browser, context


async def get_html_aguardando(page: Page, url: str, seletor: str, tentativas: int = 3) -> str | None:
    """
    Navega até `url` e aguarda o seletor CSS aparecer no DOM.
    Usado quando o conteúdo é renderizado por JavaScript.
    """
    for t in range(1, tentativas + 1):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_selector(seletor, timeout=15_000)
            await page.wait_for_timeout(random.randint(DELAY_MIN, DELAY_MAX))
            return await page.content()
        except PWTimeout:
            log.warning(f"  Timeout '{seletor}' ({t}/{tentativas}) — {url}")
            await page.wait_for_timeout(5_000 * t)
        except Exception as e:
            log.error(f"  Erro ({t}/{tentativas}): {e}")
            await page.wait_for_timeout(5_000 * t)
    log.error(f"  Desistindo após {tentativas} tentativas: {url}")
    return None


async def get_html_simples(page: Page, url: str, tentativas: int = 3) -> str | None:
    """
    Navega até `url` aguardando networkidle.
    Usado quando não há seletor crítico a esperar.
    """
    for t in range(1, tentativas + 1):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)
            await page.wait_for_load_state("networkidle", timeout=15_000)
            await page.wait_for_timeout(random.randint(DELAY_MIN, DELAY_MAX))
            return await page.content()
        except PWTimeout:
            log.warning(f"  Timeout networkidle ({t}/{tentativas}) — {url}")
            await page.wait_for_timeout(5_000 * t)
        except Exception as e:
            log.error(f"  Erro ({t}/{tentativas}): {e}")
            await page.wait_for_timeout(5_000 * t)
    log.error(f"  Desistindo após {tentativas} tentativas: {url}")
    return None