"""
cleaner.py — Limpeza e validação dos dados raspados.

Problemas identificados na amostra BYD:
  1. OCR/typo: "g8 cv" em vez de "98 cv" (potencia_maxima)
  2. OCR/typo: "2AT9 kg" em vez de "2479 kg" (peso)
  3. Inconsistência de campo: "vao_livre_do_solo" vs "altura_minima_do_solo"
  4. Valor textual "Não informado" onde deveria ser None/ausente
"""

import re
import logging
from copy import deepcopy

log = logging.getLogger(__name__)


# ── Mapeamento de campos sinônimos ────────────────────────────────────────────
# Normaliza nomes de campos que o site usa de forma inconsistente entre versões.
CAMPOS_SINONIMOS: dict[str, str] = {
    "geral__vao_livre_do_solo": "geral__altura_minima_do_solo",
}

# ── Valor sentinel para "não informado" ───────────────────────────────────────
NAO_INFORMADO_VALORES = {"não informado", "nao informado", "-", "n/d", "nd", ""}


# ── Regras de correção de valor ───────────────────────────────────────────────
# Cada regra: (campo, padrão_regex, substituto_ou_callable)
# O substituto pode ser uma string (com grupos de captura \1, \2…) ou callable(match) → str.
CORRECOES_VALOR: list[tuple[str, str, str]] = [
    # "g8 cv" → "98 cv"  (letra 'g' confundida com '9' em OCR)
    (r"geral__potencia_maxima", r"\bg(\d+)\b", r"9\1"),

    # "2AT9 kg" → "2479 kg" (letras A→4, T→7 em OCR)
    (r"geral__peso", r"\b(\d)AT(\d)\b", r"\g<1>47\2"),
]


# ── Validações de formato ─────────────────────────────────────────────────────
# Campos numéricos (com unidade) que devem casar com o padrão esperado.
# Se não casarem, loga um aviso mas mantém o valor original.
VALIDACOES: dict[str, str] = {
    "geral__peso":            r"^\d[\d.,]* kg$",
    "geral__potencia_maxima": r"^\d[\d.,]* cv$",
    "geral__autonomia":       r"^\d[\d.,]* km$",
}


# ── API pública ───────────────────────────────────────────────────────────────

def limpar_ficha(ficha: dict) -> dict:
    """
    Aplica todas as transformações de limpeza a um registro de ficha técnica.
    Retorna uma cópia limpa sem modificar o original.
    """
    dados = deepcopy(ficha)
    dados = _normalizar_sinonimos(dados)
    dados = _substituir_nao_informado(dados)
    dados = _corrigir_valores(dados)
    _validar_formatos(dados)
    return dados


def limpar_fichas(fichas: list[dict]) -> list[dict]:
    """Aplica `limpar_ficha` a uma lista de registros."""
    return [limpar_ficha(f) for f in fichas]


# ── Implementação interna ─────────────────────────────────────────────────────

def _normalizar_sinonimos(dados: dict) -> dict:
    """Renomeia campos sinônimos para o nome canônico."""
    for antigo, novo in CAMPOS_SINONIMOS.items():
        if antigo in dados:
            if novo not in dados:
                dados[novo] = dados.pop(antigo)
                log.debug(f"Renomeado: {antigo} → {novo}")
            else:
                # Ambos presentes: descarta o antigo
                del dados[antigo]
    return dados


def _substituir_nao_informado(dados: dict) -> dict:
    """Converte valores do tipo 'Não informado' para None."""
    for chave, valor in dados.items():
        if isinstance(valor, str) and valor.strip().lower() in NAO_INFORMADO_VALORES:
            dados[chave] = None
    return dados


def _corrigir_valores(dados: dict) -> dict:
    """Aplica correções de regex campo a campo."""
    for campo_padrao, regex, substituicao in CORRECOES_VALOR:
        for chave, valor in dados.items():
            if not isinstance(valor, str):
                continue
            if re.fullmatch(campo_padrao, chave):
                novo = re.sub(regex, substituicao, valor)
                if novo != valor:
                    log.warning(
                        f"Corrigido [{chave}]: {valor!r} → {novo!r}  "
                        f"({dados.get('versao_slug', '?')})"
                    )
                    dados[chave] = novo
    return dados


def _validar_formatos(dados: dict) -> None:
    """Loga avisos para campos com formato inesperado (não altera os dados)."""
    for campo, padrao in VALIDACOES.items():
        valor = dados.get(campo)
        if valor is None:
            continue
        if not re.match(padrao, str(valor).strip(), re.IGNORECASE):
            log.warning(
                f"Formato inesperado [{campo}]: {valor!r}  "
                f"({dados.get('versao_slug', '?')})"
            )