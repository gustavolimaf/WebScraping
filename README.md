# Scraper — fichacompleta.com.br

Extrai fichas técnicas de veículos do site fichacompleta.com.br e salva em **JSON** e **CSV**.

---

## Instalação

Recomendado usar Python 3.10+.

```bash
pip install -r requirements.txt
python -m playwright install
```

Se estiver usando um ambiente virtual, ative-o antes de instalar as dependências.

---

## Uso

### 1. Raspar todos os modelos BYD (padrão)
```bash
python scraper.py
```

### 2. Raspar outra marca
```bash
python scraper.py --marca toyota
python scraper.py --marca fiat
```

### 3. Raspar um modelo específico
```bash
python scraper.py --url https://www.fichacompleta.com.br/carros/byd/dolphin-2023
```

### 4. Dry-run: só listar URLs sem raspar
```bash
python scraper.py --marca byd --dry-run
```

---

## Saída

Os arquivos são salvos na pasta `output/`:

| Arquivo | Descrição |
|---|---|
| `fichas_byd_YYYYMMDD_HHMMSS.json` | Dados completos (preserva campos ausentes) |
| `fichas_byd_YYYYMMDD_HHMMSS.csv` | Tabela plana para Excel / Pandas / banco de dados |
| `scraper.log` | Log de execução |

### Exemplo de registro JSON

```json
{
  "url": "https://www.fichacompleta.com.br/carros/byd/dolphin-2023",
  "coletado_em": "2024-05-31T14:22:05.123456",
  "modelo_completo": "BYD Dolphin 2023",
  "marca": "byd",
  "motor": "Elétrico",
  "potencia_cv": "204",
  "autonomia_km": "400",
  "bateria_kwh": "60.4",
  "peso_kg": "1550",
  ...
}
```

---

## Configurações (topo do scraper.py)

| Variável | Padrão | Descrição |
|---|---|---|
| `DELAY_MIN` | `2.0` | Delay mínimo entre requisições (segundos) |
| `DELAY_MAX` | `5.0` | Delay máximo entre requisições (segundos) |
| `USER_AGENTS` | lista | Pool de User-Agents para rotação |

> **Atenção:** Não reduza os delays para evitar sobrecarga no servidor e bloqueios por rate limiting.

---

## Anti-bot: como o scraper lida

1. **Rotação de User-Agent** — alterna entre 5 navegadores reais a cada requisição  
2. **Delays aleatórios** — pausa humana entre 2–5 s entre cada página  
3. **Aquecimento de sessão** — visita a home antes de entrar nas páginas de modelos  
4. **Retry com backoff** — em caso de 429/403, aguarda e tenta novamente  
5. **Headers realistas** — inclui `Accept-Language`, `Sec-Fetch-*`, `DNT`, etc.

---

## Escalando para outras marcas

```python
# No Python, raspe múltiplas marcas sequencialmente:
from scraper import raspar_marca, salvar_resultados

for marca in ["byd", "toyota", "honda"]:
    fichas = raspar_marca(marca)
    salvar_resultados(fichas, f"fichas_{marca}")
```

---

## Nota legal

Use este scraper apenas para fins educacionais e de pesquisa.  
Verifique os Termos de Uso do site antes de raspar em escala.  
Respeite o `robots.txt`: `https://www.fichacompleta.com.br/robots.txt`