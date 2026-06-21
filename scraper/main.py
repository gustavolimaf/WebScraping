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
from scraper.config         import OUTPUT_DIR

configurar_logging()
log = logging.getLogger(__name__)

# Slugs de todas as marcas disponíveis no site (ampliar conforme necessario)
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
    parser.add_argument("--marca",   default="byd",  help="Slug de uma unica marca")
    parser.add_argument("--marcas",  nargs="+",      help="Lista de slugs de marcas")
    parser.add_argument("--todas",   action="store_true", help="Raspa todas as marcas conhecidas")
    parser.add_argument("--url",     default=None,   help="URL de uma versao especifica")
    parser.add_argument("--dry-run", action="store_true", help="Lista URLs sem raspar fichas")
    parser.add_argument("--force",   action="store_true", help="Refaz marcas mesmo se ja houver saida")
    args = parser.parse_args()

    log.info("-" * 55)
    log.info("  Scraper fichacompleta.com.br  [Playwright]")
    log.info("-" * 55)

    if args.url:
        resultados = asyncio.run(raspar_url_unica(args.url))
        if resultados and resultados.get("brutos"):
            salvar(resultados["brutos"], "ficha_unica_raw")
            salvar(resultados["automatch"], "ficha_unica_automatch")

    elif args.todas:
        marcas = TODAS_AS_MARCAS if args.force else [m for m in TODAS_AS_MARCAS if not _ja_processada(m)]
        if not marcas:
            log.info("Nenhuma marca pendente. Use --force para raspar tudo novamente.")
        for marca in marcas:
            log.info(f"\n{'-'*55}\n  MARCA: {marca.upper()}\n{'-'*55}")
            resultados = asyncio.run(raspar_marca(marca, dry_run=args.dry_run))
            
            if resultados and resultados.get("brutos"):
                # Salva os dois ficheiros com prefixos diferentes
                salvar(resultados["brutos"], f"fichas_raw_{marca}")
                salvar(resultados["automatch"], f"fichas_automatch_{marca}")
            elif not args.force and not args.dry_run:
                log.info(f"Sem resultados novos para a marca {marca.upper()}.")

    else:
        marcas = args.marcas or [args.marca]
        for marca in marcas:
            log.info(f"\n{'-'*55}\n  MARCA: {marca.upper()}\n{'-'*55}")
            resultados = asyncio.run(raspar_marca(marca, dry_run=args.dry_run))
            
            if resultados and resultados.get("brutos"):
                # Salva os dois ficheiros com prefixos diferentes
                salvar(resultados["brutos"], f"fichas_raw_{marca}")
                salvar(resultados["automatch"], f"fichas_automatch_{marca}")

    log.info("Scraper finalizado.")


def _ja_processada(marca: str) -> bool:
    # Atualizado para procurar pelo novo prefixo de dados brutos
    padrao = f"fichas_raw_{marca}_*.json"
    return any(OUTPUT_DIR.glob(padrao))


if __name__ == "__main__":
    main()