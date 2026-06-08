import asyncio, json, re, logging, argparse, random
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from playwright.async_api import async_playwright, Page, TimeoutError as PWTimeout
from bs4 import BeautifulSoup
import pandas as pd

# ──────────────────────────────────────────────────────────────
# Configuração
# ──────────────────────────────────────────────────────────────
BASE_URL   = "https://www.fichacompleta.com.br"
DELAY_MIN  = 1500   # ms de pausa humana
DELAY_MAX  = 3500
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(OUTPUT_DIR / "scraper.log", mode="w", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# Utilitários
# ──────────────────────────────────────────────────────────────
def slugify(texto: str) -> str:
    subs = {
        "á":"a","à":"a","ã":"a","â":"a","ä":"a",
        "é":"e","è":"e","ê":"e","ë":"e",
        "í":"i","ì":"i","î":"i","ï":"i",
        "ó":"o","ò":"o","õ":"o","ô":"o","ö":"o",
        "ú":"u","ù":"u","û":"u","ü":"u",
        "ç":"c","ñ":"n",
    }
    texto = texto.lower().strip()
    for orig, rep in subs.items():
        texto = texto.replace(orig, rep)
    texto = re.sub(r"[^\w\s]", "", texto)
    texto = re.sub(r"\s+", "_", texto)
    return re.sub(r"_+", "_", texto).strip("_")


# ──────────────────────────────────────────────────────────────
# Browser
# ──────────────────────────────────────────────────────────────
async def criar_contexto(playwright):
    browser = await playwright.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
    )
    context = await browser.new_context(
        viewport={"width": 1366, "height": 768},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        locale="pt-BR",
        timezone_id="America/Sao_Paulo",
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
    """Navega e aguarda seletor CSS aparecer (conteúdo JS renderizado)."""
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
    return None


async def get_html_simples(page: Page, url: str, tentativas: int = 3) -> str | None:
    """Navega e aguarda networkidle — para páginas sem seletor crítico."""
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
    return None


# ──────────────────────────────────────────────────────────────
# Nível 1 — modelos da marca
# ──────────────────────────────────────────────────────────────
async def listar_modelos(page: Page, marca: str) -> list[dict]:
    url = f"{BASE_URL}/carros/{marca}/"
    log.info(f"[Nível 1] Modelos: {url}")

    html = await get_html_aguardando(page, url, "div.mod-grid a.mod-card")
    if not html:
        log.error("Falha ao carregar página da marca.")
        return []

    soup = BeautifulSoup(html, "lxml")
    modelos = []
    for a in soup.select("div.mod-grid a.mod-card"):
        href = a.get("href", "").strip()
        if not href:
            continue
        nome = a.get_text(" ", strip=True) or href.strip("/").split("/")[-1]
        slug = href.strip("/").split("/")[-1]
        modelos.append({"marca": marca, "nome": nome, "slug": slug, "url": urljoin(BASE_URL, href)})

    log.info(f"  → {len(modelos)} modelos")
    return modelos


# ──────────────────────────────────────────────────────────────
# Nível 2 — versões de um modelo
# Extrai slugs de:  <input rel="seal-ev-2024" class="versaoComp ver-card_check">
# Fallback para:    <a href="/carros/byd/seal-ev-2024" class="ver-card_link">
# ──────────────────────────────────────────────────────────────
async def listar_versoes(page: Page, modelo: dict) -> list[dict]:
    log.info(f"  [Nível 2] Versões: {modelo['nome']}")

    html = await get_html_simples(page, modelo["url"])
    if not html:
        log.warning(f"  Falha ao carregar página do modelo.")
        return []

    soup = BeautifulSoup(html, "lxml")
    versoes = []
    vistos = set()

    # Estratégia A: input[rel] — mais confiável (não depende de link renderizado)
    for inp in soup.select("input.versaoComp[rel]"):
        slug_v = inp.get("rel", "").strip()
        if not slug_v or slug_v in vistos:
            continue
        vistos.add(slug_v)
        # Tenta pegar o texto do link irmão
        card = inp.find_parent("div", class_="ver-card")
        link = card.select_one("a.ver-card_link") if card else None
        nome_v = link.get_text(" ", strip=True) if link else slug_v
        versoes.append({
            "marca":       modelo["marca"],
            "modelo":      modelo["nome"],
            "modelo_slug": modelo["slug"],
            "versao":      nome_v or slug_v,
            "versao_slug": slug_v,
            "url":         f"{BASE_URL}/carros/{modelo['marca']}/{slug_v}",
        })

    # Estratégia B: links ver-card_link (fallback)
    if not versoes:
        for a in soup.select("a.ver-card_link"):
            href = a.get("href", "").strip()
            if not href:
                continue
            slug_v = href.strip("/").split("/")[-1]
            if slug_v in vistos:
                continue
            vistos.add(slug_v)
            versoes.append({
                "marca":       modelo["marca"],
                "modelo":      modelo["nome"],
                "modelo_slug": modelo["slug"],
                "versao":      a.get_text(" ", strip=True) or slug_v,
                "versao_slug": slug_v,
                "url":         urljoin(BASE_URL, href),
            })

    log.info(f"    → {len(versoes)} versões")
    return versoes


# ──────────────────────────────────────────────────────────────
# Nível 3 — ficha técnica de uma versão
# ──────────────────────────────────────────────────────────────
async def extrair_ficha(page: Page, versao: dict) -> dict:
    log.info(f"    [Nível 3] Ficha: {versao.get('versao_slug', '')}")

    dados = {
        "marca":       versao.get("marca", ""),
        "modelo":      versao.get("modelo", ""),
        "modelo_slug": versao.get("modelo_slug", ""),
        "versao":      versao.get("versao", ""),
        "versao_slug": versao.get("versao_slug", ""),
        "url":         versao["url"],
        "coletado_em": datetime.now().isoformat(),
    }

    html = await get_html_aguardando(page, versao["url"], "div.ent-ficha-group")
    if not html:
        dados["erro"] = "falha_na_requisicao"
        return dados

    soup = BeautifulSoup(html, "lxml")

    h1 = soup.select_one("h1")
    if h1:
        dados["titulo_pagina"] = h1.get_text(strip=True)

    for grupo in soup.select("div.ent-ficha-group"):
        titulo_el = grupo.select_one("h3.ent-ficha-group_title")
        categoria = titulo_el.get_text(strip=True) if titulo_el else "geral"
        cat_slug  = slugify(categoria)

        for item in grupo.select("div.ent-spec-item"):
            label_el = item.select_one("span.ent-spec-label")
            value_el = item.select_one("span.ent-spec-value")
            if label_el and value_el:
                chave = f"{cat_slug}__{slugify(label_el.get_text(strip=True))}"
                dados[chave] = value_el.get_text(strip=True)

    campos = sum(1 for k in dados if "__" in k)
    log.info(f"      → {campos} campos extraídos")
    return dados


# ──────────────────────────────────────────────────────────────
# Orquestrador
# ──────────────────────────────────────────────────────────────
async def raspar_marca(marca: str, dry_run: bool = False) -> list[dict]:
    async with async_playwright() as pw:
        browser, context = await criar_contexto(pw)
        page = await context.new_page()
        try:
            log.info("Aquecendo sessão na home…")
            await get_html_simples(page, BASE_URL)

            modelos = await listar_modelos(page, marca)
            if not modelos:
                return []

            if dry_run:
                print(f"\n{'─'*60}\nDRY RUN — {len(modelos)} modelos em '{marca}'\n{'─'*60}")
                for m in modelos:
                    versoes = await listar_versoes(page, m)
                    status  = f"{len(versoes)} versões" if versoes else "sem versões"
                    print(f"  {m['nome']:30s}  ({status})")
                    for v in versoes:
                        print(f"    ↳ {v['versao_slug']}")
                return []

            todas_fichas = []
            for i, modelo in enumerate(modelos, 1):
                log.info(f"\n── Modelo {i}/{len(modelos)}: {modelo['nome']} ──")
                versoes = await listar_versoes(page, modelo)

                for j, versao in enumerate(versoes, 1):
                    log.info(f"  Versão {j}/{len(versoes)}: {versao['versao']}")
                    ficha = await extrair_ficha(page, versao)
                    todas_fichas.append(ficha)

            return todas_fichas
        finally:
            await browser.close()


async def raspar_url_unica(url: str) -> list[dict]:
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
            ficha = await extrair_ficha(page, versao_info)
            if "titulo_pagina" in ficha and not ficha["modelo"]:
                ficha["modelo"] = ficha["titulo_pagina"]
            return [ficha]
        finally:
            await browser.close()


# ──────────────────────────────────────────────────────────────
# Persistência
# ──────────────────────────────────────────────────────────────
def salvar(fichas: list[dict], prefixo: str = "fichas"):
    if not fichas:
        log.warning("Nenhum dado para salvar.")
        return

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    jp = OUTPUT_DIR / f"{prefixo}_{ts}.json"
    cp = OUTPUT_DIR / f"{prefixo}_{ts}.csv"

    with open(jp, "w", encoding="utf-8") as f:
        json.dump(fichas, f, ensure_ascii=False, indent=2)

    df = pd.DataFrame(fichas)
    df.to_csv(cp, index=False, encoding="utf-8-sig")

    log.info(f"\n{'═'*55}")
    log.info(f"  Registros : {len(fichas)}")
    log.info(f"  Colunas   : {len(df.columns)}")
    log.info(f"  JSON      : {jp}")
    log.info(f"  CSV       : {cp}")
    log.info(f"{'═'*55}")


# ──────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Scraper fichacompleta.com.br")
    parser.add_argument("--marca",   default="byd",  help="Slug da marca (ex: byd, toyota)")
    parser.add_argument("--url",     default=None,    help="URL de uma versão específica")
    parser.add_argument("--dry-run", action="store_true", help="Lista modelos e versões sem raspar fichas")
    args = parser.parse_args()

    log.info("═" * 55)
    log.info("  Scraper fichacompleta.com.br  [Playwright]")
    log.info("═" * 55)

    if args.url:
        fichas  = asyncio.run(raspar_url_unica(args.url))
        prefixo = "ficha_unica"
    else:
        fichas  = asyncio.run(raspar_marca(args.marca, dry_run=args.dry_run))
        prefixo = f"fichas_{args.marca}"

    if fichas:
        salvar(fichas, prefixo)

    log.info("Scraper finalizado.")


if __name__ == "__main__":
    main()