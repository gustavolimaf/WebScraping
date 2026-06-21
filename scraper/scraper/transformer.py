"""
transformer.py -- Transforma os dados limpos no schema exigido pelo Supabase/IA.
"""
import re
import logging

log = logging.getLogger(__name__)

def clean_numeric(text: str | float | int) -> float:
    """Extrai números de strings como '150 cv' ou '12.5 km/l'."""
    if text is None:
        return 0.0
    if isinstance(text, (int, float)):
        return float(text)
    
    match = re.search(r"(\d+\.?\d*)", str(text).replace(',', '.'))
    return float(match.group(1)) if match else 0.0

def _mapear_cambio(tipo_cambio: str) -> str:
    """Padroniza a transmissão para o modelo da IA."""
    if not tipo_cambio:
        return "Manual"
    
    tipo_lower = str(tipo_cambio).lower()
    if any(x in tipo_lower for x in ["automático", "automatizado", "cvt"]):
        return "Auto"
    return "Manual"

def _mapear_categoria(carroceria: str) -> str:
    """Enquadra a carroceria nas macros do AutoMatch."""
    if not carroceria:
        return "Indefinido"
        
    c_lower = str(carroceria).lower()
    if "hatch" in c_lower: return "Hatch"
    if "sedã" in c_lower or "sedan" in c_lower: return "Sedan"
    if "suv" in c_lower or "utilitário" in c_lower: return "SUV"
    if "picape" in c_lower or "caminhonete" in c_lower: return "Picape"
    return "Premium" # Fallback ou criar regra mais específica

def transformar_ficha_automatch(ficha: dict) -> dict:
    """
    Filtra e transforma uma ficha completa em um formato enxuto para o Supabase.
    """
    return {
        # Identificadores Básicos
        "marca": ficha.get("marca"),
        "modelo": ficha.get("modelo"),
        "versao": ficha.get("versao"),
        
        # Variáveis da IA (Two-Tower)
        "preco_orcamento": clean_numeric(ficha.get("geral__preco")),
        "ano": clean_numeric(ficha.get("geral__ano")),
        "potencia_cv": clean_numeric(ficha.get("geral__potencia_maxima")),
        "lugares_grupo": clean_numeric(ficha.get("geral__lugares", 5)),
        
        # Variáveis Categóricas
        "cambio": _mapear_cambio(ficha.get("geral__cambio")),
        "categoria": _mapear_categoria(ficha.get("geral__carroceria")),
        
        # Mapeamento de Ambiente (Exemplo de heurística baseada em tração)
        "ambiente_ideal": "Rural" if "4x4" in str(ficha.get("geral__tracao", "")) else "Urbano"
    }

def transformar_fichas(fichas_limpas: list[dict]) -> list[dict]:
    """Aplica a transformação em lote."""
    return [transformar_ficha_automatch(f) for f in fichas_limpas]