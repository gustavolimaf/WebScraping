"""
tests/test_parser_cleaner.py -- Testes unitarios para parser e cleaner.
Execute com: python -m pytest tests/ -v
"""

import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))

from scraper.parser  import slugify, parsear_modelos, parsear_versoes, parsear_ficha
from scraper.cleaner import limpar_ficha

# -- slugify

def test_slugify_basico():
    assert slugify("Motores eletricos") == "motores_eletricos"

def test_slugify_parenteses_e_barras():
    assert slugify("0 a 100 km/h") == "0_a_100_kmh"

def test_slugify_acentos():
    assert slugify("Potencia (CV)") == "potencia_cv"

def test_slugify_underscores_duplos():
    assert slugify("peso  bruto") == "peso_bruto"


# -- parsear_modelos

HTML_MODELOS = """
<div class='mod-grid'>
  <a href='/carros/byd/seal/'    class='mod-card'>Seal</a>
  <a href='/carros/byd/dolphin/' class='mod-card'>Dolphin</a>
  <a href='/carros/byd/han/'     class='mod-card'>Han</a>
</div>
"""

def test_parsear_modelos_quantidade():
    modelos = parsear_modelos(HTML_MODELOS, "byd")
    assert len(modelos) == 3

def test_parsear_modelos_campos():
    modelos = parsear_modelos(HTML_MODELOS, "byd")
    seal = modelos[0]
    assert seal["marca"] == "byd"
    assert seal["slug"]  == "seal"
    assert "fichacompleta.com.br/carros/byd/seal" in seal["url"]


# -- parsear_versoes

HTML_VERSOES = """
<div class='ver-list'>
  <div class='ver-card'>
    <input rel='seal-ev-2024' class='versaoComp ver-card_check'>
    <a href='/carros/byd/seal-ev-2024' class='ver-card_link'>Seal EV 2024</a>
  </div>
  <div class='ver-card'>
    <input rel='seal-ev-2025' class='versaoComp ver-card_check'>
    <a href='/carros/byd/seal-ev-2025' class='ver-card_link'>Seal EV 2025</a>
  </div>
</div>
"""

MODELO_SEAL = {"marca": "byd", "nome": "Seal", "slug": "seal",
               "url": "https://www.fichacompleta.com.br/carros/byd/seal/"}

def test_parsear_versoes_quantidade():
    versoes = parsear_versoes(HTML_VERSOES, MODELO_SEAL)
    assert len(versoes) == 2

def test_parsear_versoes_slug():
    versoes = parsear_versoes(HTML_VERSOES, MODELO_SEAL)
    assert versoes[0]["versao_slug"] == "seal-ev-2024"
    assert versoes[1]["versao_slug"] == "seal-ev-2025"

def test_parsear_versoes_url():
    versoes = parsear_versoes(HTML_VERSOES, MODELO_SEAL)
    assert "seal-ev-2025" in versoes[1]["url"]


# -- parsear_ficha

HTML_FICHA = """
<h1>BYD Seal EV 2025</h1>
<div class='ent-ficha-group'>
  <h3 class='ent-ficha-group_title'>Motores eletricos</h3>
  <div class='ent-ficha-grid'>
    <div class='ent-spec-item'>
      <span class='ent-spec-label'>Autonomia</span>
      <span class='ent-spec-value'>372 km</span>
    </div>
    <div class='ent-spec-item'>
      <span class='ent-spec-label'>Potencia combinada</span>
      <span class='ent-spec-value'>530 cv</span>
    </div>
  </div>
</div>
<div class='ent-ficha-group'>
  <h3 class='ent-ficha-group_title'>Dimensoes</h3>
  <div class='ent-ficha-grid'>
    <div class='ent-spec-item'>
      <span class='ent-spec-label'>Comprimento</span>
      <span class='ent-spec-value'>4800 mm</span>
    </div>
  </div>
</div>
"""

VERSAO_SEAL = {
    "marca": "byd", "modelo": "Seal", "modelo_slug": "seal",
    "versao": "Seal EV 2025", "versao_slug": "seal-ev-2025",
    "url": "https://www.fichacompleta.com.br/carros/byd/seal-ev-2025",
}

def test_parsear_ficha_titulo():
    ficha = parsear_ficha(HTML_FICHA, VERSAO_SEAL)
    assert ficha["titulo_pagina"] == "BYD Seal EV 2025"

def test_parsear_ficha_campo_com_categoria():
    ficha = parsear_ficha(HTML_FICHA, VERSAO_SEAL)
    assert ficha["motores_eletricos__autonomia"]        == "372 km"
    assert ficha["motores_eletricos__potencia_combinada"] == "530 cv"
    assert ficha["dimensoes__comprimento"]              == "4800 mm"

def test_parsear_ficha_metadados():
    ficha = parsear_ficha(HTML_FICHA, VERSAO_SEAL)
    assert ficha["marca"] == "byd"
    assert ficha["versao_slug"] == "seal-ev-2025"
    assert "coletado_em" in ficha


# -- cleaner

def test_cleaner_corrige_potencia_ocr():
    ficha = {"versao_slug": "x", "geral__potencia_maxima": "g8 cv"}
    limpa = limpar_ficha(ficha)
    assert limpa["geral__potencia_maxima"] == "98 cv"

def test_cleaner_corrige_peso_ocr():
    ficha = {"versao_slug": "x", "geral__peso": "2AT9 kg"}
    limpa = limpar_ficha(ficha)
    assert limpa["geral__peso"] == "2479 kg"

def test_cleaner_nao_informado_vira_none():
    ficha = {"versao_slug": "x", "geral__diametro_de_giro": "Nao informado"}
    limpa = limpar_ficha(ficha)
    assert limpa["geral__diametro_de_giro"] is None

def test_cleaner_normaliza_sinonimo():
    ficha = {"versao_slug": "x", "geral__vao_livre_do_solo": "125 mm"}
    limpa = limpar_ficha(ficha)
    assert "geral__altura_minima_do_solo" in limpa
    assert "geral__vao_livre_do_solo"     not in limpa

def test_cleaner_nao_altera_campo_correto():
    ficha = {"versao_slug": "x", "geral__potencia_maxima": "110 cv"}
    limpa = limpar_ficha(ficha)
    assert limpa["geral__potencia_maxima"] == "110 cv"