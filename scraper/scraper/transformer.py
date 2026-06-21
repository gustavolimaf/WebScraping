"""
transformer.py -- Transforma os dados limpos no schema exigido pelo Supabase/IA.
"""
import re
import logging

log = logging.getLogger(__name__)

def clean_numeric(text, return_int=False):
    """Extrai números tratando o padrão brasileiro (R$ 380.000,00 ou 10,5 km/l)."""
    if text is None or str(text).strip() in ["", "None", "n/d", "-"]:
        return None  # Retorna nulo para o banco de dados ignorar
        
    if isinstance(text, (int, float)):
        return int(text) if return_int else float(text)
    
    # Remove separadores de milhar (ponto) e converte decimal (vírgula para ponto)
    texto_limpo = str(text).replace('.', '').replace(',', '.')
    match = re.search(r"(\d+\.?\d*)", texto_limpo)
    
    if match:
        val = float(match.group(1))
        return int(val) if return_int else val
    return None

def _extrair_ano(ficha: dict) -> int | None:
    """Tenta extrair o ano do campo específico, do título ou do slug da versão."""
    # 1. Tenta do campo geral (caso exista em outras marcas)
    ano = clean_numeric(ficha.get("geral__ano"), return_int=True)
    if ano: return ano
    
    # 2. Tenta extrair do título da página (ex: "Audi A3 1.8 Turbo 1999")
    titulo = str(ficha.get("titulo_pagina", ""))
    match_titulo = re.search(r"\b(19\d{2}|20\d{2})\b", titulo)
    if match_titulo: return int(match_titulo.group(1))
    
    # 3. Tenta extrair do final do slug (ex: "a3-1-8-turbo-1999")
    slug = str(ficha.get("versao_slug", ""))
    match_slug = re.search(r"(19\d{2}|20\d{2})$", slug)
    if match_slug: return int(match_slug.group(1))
    
    return None

def _mapear_cambio(tipo_cambio: str) -> str:
    """Padroniza a transmissão para o modelo da IA."""
    if not tipo_cambio: return "Manual"
    tipo_lower = str(tipo_cambio).lower()
    if any(x in tipo_lower for x in ["automático", "automatizado", "cvt", "s-tronic", "dsg"]):
        return "Auto"
    return "Manual"

def _mapear_categoria(carroceria: str) -> str:
    """Enquadra a carroceria nas macros do AutoMatch."""
    if not carroceria: return "Indefinido"
    c_lower = str(carroceria).lower()
    if "hatch" in c_lower: return "Hatch"
    if "sedã" in c_lower or "sedan" in c_lower: return "Sedan"
    if "suv" in c_lower or "utilitário" in c_lower: return "SUV"
    if "picape" in c_lower or "caminhonete" in c_lower: return "Picape"
    return "Premium"

def transformar_ficha_automatch(ficha: dict) -> dict:
    """Filtra e transforma uma ficha completa em um formato enxuto para o Supabase."""
    tracao = str(ficha.get("geral__tracao", "")).lower()
    
    return {
        "marca": ficha.get("marca"),
        "modelo": ficha.get("modelo"),
        "versao": ficha.get("versao"),
        "preco_orcamento": clean_numeric(ficha.get("geral__preco")), # Fica vazio (NULL) se não tiver preço
        "ano": _extrair_ano(ficha),
        "potencia_cv": clean_numeric(ficha.get("geral__potencia_maxima")),
        "lugares_grupo": clean_numeric(ficha.get("geral__lugares"), return_int=True) or 5, # Padrão 5 lugares
        "cambio": _mapear_cambio(ficha.get("geral__cambio")),
        "categoria": _mapear_categoria(ficha.get("geral__carroceria")),
        "ambiente_ideal": "Rural" if "4x4" in tracao or "integral" in tracao else "Urbano"
    }

def transformar_fichas(fichas_limpas: list[dict]) -> list[dict]:
    return [transformar_ficha_automatch(f) for f in fichas_limpas]