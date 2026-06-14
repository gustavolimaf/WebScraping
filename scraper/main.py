"""
main.py -- Ponto de entrada do scraper.

Uso:
    python main.py                        # raspa todos os BYDs
    python main.py --marca toyota         # outra marca
    python main.py --marcas byd toyota    # varias marcas de uma vez
    python main.py --todas                # todas as marcas do site
    python main.py --dry-run              # lista modelos/versoes sem raspar
    python main.py --url <url_versao>     # versao unica
"""

import asyncio
import argparse
import logging

from scraper.logging_config import configurar_logging
from scraper.orchestrator   import raspar_marca, raspar_url_unica
from scraper.storage        import salvar

configurar_logging()
log = logging.getLogger(__name__)

# Slugs de todas as marcas disponíveis no site (amplie conforme necessario)
TODAS_AS_MARCAS = [
    "byd", "toyota", "honda", "volkswagen", "chevrolet",
    "fiat", "hyundai", "nissan", "jeep", "ford",
    "mitsubishi", "renault", "peugeot", "citroen", "kia",
    "mercedes-benz", "bmw", "audi", "volvo", "land-rover",
    "ram", "dodge", "chrysler", "chery", "great-wall",
    "jac", "caoa-chery",
]


def main():
    parser = argparse.ArgumentParser(
        description="Scraper fichacompleta.com.br",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--marca",   default="byd",   help="Slug de uma unica marca")
    parser.add_argument("--marcas",  nargs="+",        help="Lista de slugs de marcas")
    parser.add_argument("--todas",   action="store_true", help="Raspa todas as marcas conhecidas")
    parser.add_argument("--url",     default=None,     help="URL de uma versao especifica")
    parser.add_argument("--dry-run", action="store_true", help="Lista URLs sem raspar fichas")
    args = parser.parse_args()

    log.info("-" * 55)
    log.info("  Scraper fichacompleta.com.br  [Playwright]")
    log.info("-" * 55)

    if args.url:
        fichas = asyncio.run(raspar_url_unica(args.url))
        salvar(fichas, "ficha_unica")

    elif args.todas:
        for marca in TODAS_AS_MARCAS:
            log.info(f"\n{'-'*55}\n  MARCA: {marca.upper()}\n{'-'*55}")
            fichas = asyncio.run(raspar_marca(marca, dry_run=args.dry_run))
            if fichas:
                salvar(fichas, f"fichas_{marca}")

    else:
        marcas = args.marcas or [args.marca]
        for marca in marcas:
            log.info(f"\n{'-'*55}\n  MARCA: {marca.upper()}\n{'-'*55}")
            fichas = asyncio.run(raspar_marca(marca, dry_run=args.dry_run))
            if fichas:
                salvar(fichas, f"fichas_{marca}")

    log.info("Scraper finalizado.")


if __name__ == "__main__":
    main()