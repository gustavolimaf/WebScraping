"""
parser.py — Extração de dados do HTML.

Cada função recebe um BeautifulSoup e retorna dados estruturados,
sem nenhuma dependência de Playwright (facilita testes unitários).
"""

import logging
import re
from datetime import datetime
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .config import BASE_URL, SEL_MODELOS, SEL_VERSOES, SEL_FICHA

log = logging.getLogger(__name__)


# ── Utilitários ───────────────────────────────────────────────────────────────

def slugify(texto: str) -> str:
    """Converte texto em snake_case sem acentos."""
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


# ── Nível 1: modelos ──────────────────────────────────────────────────────────

def parsear_modelos(html: str, marca: str) -> list[dict]:
    """
    Extrai lista de modelos da página da marca.
    Selector: div.mod-grid > a.mod-card
    """
    soup = BeautifulSoup(html, "lxml")
    modelos = []
    for a in soup.select(SEL_MODELOS):
        href = a.get("href", "").strip()
        if not href:
            continue
        nome = a.get_text(" ", strip=True) or href.strip("/").split("/")[-1]
        slug = href.strip("/").split("/")[-1]
        modelos.append({
            "marca": marca,
            "nome":  nome,
            "slug":  slug,
            "url":   urljoin(BASE_URL, href),
        })
    log.info(f"  → {len(modelos)} modelos")
    return modelos


# ── Nível 2: versões ──────────────────────────────────────────────────────────

def parsear_versoes(html: str, modelo: dict) -> list[dict]:
    """
    Extrai versões da página do modelo.

    Estratégia A (principal): input[rel] — slug disponível diretamente no atributo,
    independente de AJAX ou link renderizado.

    Estratégia B (fallback): a.ver-card_link — usado se strategy A não retornar nada.
    """
    soup = BeautifulSoup(html, "lxml")
    versoes = []
    vistos  = set()

    # A: input[rel]
    for inp in soup.select(SEL_VERSOES):
        slug_v = inp.get("rel", "").strip()
        if not slug_v or slug_v in vistos:
            continue
        vistos.add(slug_v)
        card   = inp.find_parent("div", class_="ver-card")
        link   = card.select_one("a.ver-card_link") if card else None
        nome_v = link.get_text(" ", strip=True) if link else slug_v
        versoes.append(_montar_versao(modelo, slug_v, nome_v or slug_v))

    # B: fallback
    if not versoes:
        for a in soup.select("a.ver-card_link"):
            href   = a.get("href", "").strip()
            slug_v = href.strip("/").split("/")[-1]
            if not href or slug_v in vistos:
                continue
            vistos.add(slug_v)
            versoes.append(_montar_versao(modelo, slug_v, a.get_text(" ", strip=True) or slug_v, href))

    log.info(f"    → {len(versoes)} versões")
    return versoes


def _montar_versao(modelo: dict, slug_v: str, nome_v: str, href: str = None) -> dict:
    url = urljoin(BASE_URL, href) if href else f"{BASE_URL}/carros/{modelo['marca']}/{slug_v}"
    return {
        "marca":       modelo["marca"],
        "modelo":      modelo["nome"],
        "modelo_slug": modelo["slug"],
        "versao":      nome_v,
        "versao_slug": slug_v,
        "url":         url,
    }


# ── Nível 3: ficha técnica ───────────────────────────────────────────────────

def parsear_ficha(html: str, versao: dict) -> dict:
    """
    Extrai todos os campos da ficha técnica.

    Estrutura HTML esperada:
        div.ent-ficha-group
            h3.ent-ficha-group_title  → categoria (ex: "Motores eletricos")
            div.ent-ficha-grid
                div.ent-spec-item
                    span.ent-spec-label  → nome do campo
                    span.ent-spec-value  → valor

    Campos são nomeados como  `{categoria}__{campo}`.
    """
    soup = BeautifulSoup(html, "lxml")
    dados: dict = {
        "marca":       versao.get("marca", ""),
        "modelo":      versao.get("modelo", ""),
        "modelo_slug": versao.get("modelo_slug", ""),
        "versao":      versao.get("versao", ""),
        "versao_slug": versao.get("versao_slug", ""),
        "url":         versao["url"],
        "coletado_em": datetime.now().isoformat(),
    }

    h1 = soup.select_one("h1")
    if h1:
        dados["titulo_pagina"] = h1.get_text(strip=True)

    for grupo in soup.select(SEL_FICHA):
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