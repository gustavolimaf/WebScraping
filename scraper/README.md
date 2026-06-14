# Scraper Modular — Ficha Completa

Estrutura refatorada e modular do web scraper para `fichacompleta.com.br` com separação rigorosa de responsabilidades, tratamento automático de erros OCR e validação de dados.

## Estrutura do Projeto

```
scraper/
├── main.py                    ← Entrypoint + CLI (argparse)
├── scraper/
│   ├── __init__.py
│   ├── config.py              ← Configurações, seletores, delays
│   ├── browser.py             ← Playwright: contexto + navegação
│   ├── parser.py              ← Extração de HTML → estruturas Python
│   ├── cleaner.py             ← Limpeza automática + validação
│   ├── storage.py             ← Salvamento JSON + CSV + relatórios
│   ├── orchestrator.py        ← Orquestra 3 níveis (marca → modelo → versão)
│   └── logging_config.py      ← Configuração centralizada de logs
└── tests/
    ├── __init__.py
    └── test_parser_cleaner.py ← 17 testes unitários
```

## Uso

### Scrape padrão (apenas BYD)
```bash
cd scraper
python main.py
```

### Scrape de uma marca específica
```bash
python main.py --marca toyota
```

### Scrape de múltiplas marcas
```bash
python main.py --marcas byd toyota honda volkswagen
```

### Scrape de todas as marcas conhecidas
```bash
python main.py --todas
```

### Scrape de uma versão específica (URL direta)
```bash
python main.py --url "https://www.fichacompleta.com.br/carros/byd/seagull/plus/"
```

### Listar URLs sem raspar fichas (dry-run)
```bash
python main.py --dry-run
python main.py --marca toyota --dry-run
```

### Executar testes unitários
```bash
python -m pytest tests/ -v
pytest tests/ -v -k "Parser"   # Apenas testes do parser
pytest tests/ -v -k "Cleaner"  # Apenas testes do cleaner
```

## Funcionalidades

### 1. **Configuração Centralizada** (`config.py`)
- **URL base** do site
- **Delays** entre requisições (milissegundos para parecer humano)
- **Seletores CSS** para modelos, versões e fichas
- **Configurações do Playwright** (viewport, user-agent, locale, timezone)
- **Validações de formato** para campos numéricos com unidade

### 2. **Browser Automation** (`browser.py`)
- Cria contexto do Playwright com headers anti-bot
- `criar_contexto()`: Configura browser com user-agent, locale e timezone
- `get_html_aguardando()`: Navega e aguarda um seletor CSS específico
- `get_html_simples()`: Navega e aguarda networkidle (sem seletor crítico)
- Retry automático com backoff exponencial

### 3. **Parser** (`parser.py`)
Extração estruturada de HTML para Python (sem dependência de Playwright):

- `slugify()`: Converte texto em `snake_case` sem acentos
- `parsear_modelos()`: Extrai lista de modelos (Nível 1)
- `parsear_versoes()`: Extrai lista de versões (Nível 2)
- `parsear_ficha()`: Extrai dados estruturados da ficha técnica (Nível 3)

**Caraterística:** Funções independentes facilitam testes unitários sem Playwright

### 4. **Cleaner** (`cleaner.py`)
Limpeza automática e validação inteligente de dados com:

**Correções de Erros OCR (regex-based):**
| Campo | Padrão | Correção |
|-------|--------|----------|
| `potencia_maxima` | `\bg(\d+)` | `g8 cv` → `98 cv` |
| `peso` | `(\d)AT(\d)` | `2AT9 kg` → `2479 kg` |

**Normalização:**
- Valores "Não informado" → removidos (None)
- Espaçamento normalizado
- Sinônimos de campos unificados (ex: `vao_livre_do_solo` → `altura_minima_do_solo`)

**Validações de Formato:**
- `peso`: deve casar com `^\d[\d.,]* kg$`
- `potencia_maxima`: deve casar com `^\d[\d.,]* cv$`
- `autonomia`: deve casar com `^\d[\d.,]* km$`

**API Pública:**
- `limpar_ficha(ficha: dict) → dict`: Limpa um registro individual
- `limpar_fichas(fichas: list[dict]) → list[dict]`: Limpa uma lista

### 5. **Storage** (`storage.py`)
Salvamento flexível dos dados:

- `salvar()`: Função genérica (detecta formato)
- Salva em **JSON** (indentado, UTF-8, sem BOM)
- Salva em **CSV** (com pandas, UTF-8, headers automáticos)
- Geração automática de nomes com timestamp

### 6. **Orchestrator** (`orchestrator.py`)
Orquestra os **3 níveis de scraping** em sequência:

1. **Nível 1**: `raspar_marca()` → lista de modelos
2. **Nível 2**: Para cada modelo → lista de versões
3. **Nível 3**: Para cada versão → ficha técnica (com limpeza)

**Funções principales:**
- `raspar_marca(marca: str, dry_run=False)`: Raspa uma marca completa
- `raspar_url_unica(url: str)`: Raspa uma versão específica
- Suporta modo `dry_run` para visualizar URLs sem raspar

### 7. **Logging Centralizado** (`logging_config.py`)
- Função `configurar_logging()`
- Saída simultânea em **console** (colorido) e **arquivo**
- Nível INFO por padrão
- Arquivo: `output/scraper.log`

## Marcas Suportadas

Atualmente suportadas (em `main.py`):
```python
TODAS_AS_MARCAS = [
    "byd", "toyota", "honda", "volkswagen", "chevrolet",
    "fiat", "hyundai", "nissan", "jeep", "ford",
    "mitsubishi", "renault", "peugeot", "citroen", "kia",
    "mercedes-benz", "bmw", "audi", "volvo", "land-rover",
    "ram", "dodge", "chrysler", "chery", "great-wall",
    "jac", "caoa-chery",
]
```

## Adicionando Novas Marcas

1. Adicione o slug em `TODAS_AS_MARCAS` em `main.py`
2. Execute:
```bash
python main.py --marca <novo_slug>
# ou
python main.py --todas
```

## Tratando Novos Erros OCR

Se encontrar novos erros OCR durante o scraping:

1. Abra `scraper/cleaner.py`
2. Localize a seção `CORRECOES_VALOR`
3. Adicione uma nova regra (campo, padrão regex, substituto):

```python
CORRECOES_VALOR: list[tuple[str, str, str]] = [
    (r"geral__potencia_maxima", r"\bg(\d+)\b", r"9\1"),    # Existente
    (r"geral__peso", r"\b(\d)AT(\d)\b", r"\g<1>47\2"),    # Existente
    # Adicione aqui:
    (r"seu_campo", r"seu_padrão_regex", r"sua_substituição"),
]
```

## Testes Unitários

**17 testes em `tests/test_parser_cleaner.py`:**

```bash
# Executar todos
pytest tests/ -v

# Apenas parser
pytest tests/ -v -k "slugify or extrair or parsear"

# Apenas cleaner
pytest tests/ -v -k "normalizar or remapear or limpar"
```

**Cobertura:**
- Normalização de valores
- Remapeamento de sinônimos
- Limpeza de fichas
- Extração de HTML
- Casos extremos (valores vazios, inválidos, etc)

## Estrutura de Output

Após raspar, encontre em `output/`:
```
output/
├── fichas_byd_20260614_145248.json
├── fichas_byd_20260614_145248.csv
├── relatorio_qualidade_fichas_byd_20260614_145248.json
└── scraper.log
```

**JSON:** Array de registros completos com metadados + ficha
**CSV:** Flat com colunas (marca, modelo, versao, url, geral__peso, geral__potencia_maxima, etc)
**Relatório:** Estatísticas (total, com_ficha, incompleta, cobertura)

## Estrutura de um Registro

```json
{
  "marca": "byd",
  "modelo": "seagull",
  "versao": "Plus",
  "url": "https://www.fichacompleta.com.br/carros/byd/seagull/plus/",
  "ficha": {
    "geral__peso": "1350 kg",
    "geral__potencia_maxima": "98 cv",
    "geral__altura_minima_do_solo": "150 mm",
    "geral__comprimento": "3615 mm",
    ...
  }
}
```

## Desenvolvimento

Para estender ou customizar:

1. **Novo erro OCR**: Adicione regex em `cleaner.py` → `CORRECOES_VALOR`
2. **Novo sinônimo**: Adicione em `cleaner.py` → `CAMPOS_SINONIMOS`
3. **Novo validação**: Adicione em `cleaner.py` → `VALIDACOES`
4. **Novo seletor CSS**: Atualize em `config.py` (SEL_*)
5. **Teste unitário**: Adicione em `tests/test_parser_cleaner.py`

## Requirements

Ver `requirements.txt`:
```
playwright>=1.40.0
beautifulsoup4>=4.12.0
pandas>=2.0.0
pytest>=7.4.0
lxml>=4.9.0
```

Instale:
```bash
pip install -r requirements.txt
playwright install chromium
```

## Licença

Uso pessoal/educacional. Respeite `robots.txt` e termos de serviço do site.

