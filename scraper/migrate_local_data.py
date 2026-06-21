"""
migrate_local_data.py -- Lê os arquivos já extraídos e converte para o modelo AutoMatch.
"""
import json
import pandas as pd
from pathlib import Path

from scraper.config import OUTPUT_DIR
from scraper.cleaner import limpar_fichas
from scraper.transformer import transformar_fichas

def migrar_arquivos():
    # Define as novas subpastas baseadas no OUTPUT_DIR (output/)
    pasta_raw = OUTPUT_DIR / "raw_data"
    pasta_automatch = OUTPUT_DIR / "automatch"
    
    # Garante que a pasta de destino exista
    pasta_automatch.mkdir(parents=True, exist_ok=True)
    
    print(f"Procurando arquivos em: {pasta_raw}")
    
    # Busca todos os arquivos JSON dentro de raw_data
    arquivos_antigos = list(pasta_raw.glob("*.json"))
    
    if not arquivos_antigos:
        print("Nenhum arquivo de dados brutos pendente de migração encontrado.")
        return

    for arquivo in arquivos_antigos:
        print(f"\nProcessando: {arquivo.name}")
        
        # 1. Lê os dados brutos
        with open(arquivo, 'r', encoding='utf-8') as f:
            dados_brutos = json.load(f)
            
        # 2. Aplica o Pipeline
        dados_limpos = limpar_fichas(dados_brutos)
        dados_automatch = transformar_fichas(dados_limpos)
        
        # Extrai a marca limpando prefixos como 'fichas_' ou 'raw_' 
        nome_limpo = arquivo.stem.replace("fichas_", "").replace("raw_", "")
        partes_nome = nome_limpo.split('_')
        marca = partes_nome[0] if partes_nome else "marca_desconhecida"
        
        # 3. Salva diretamente em CSV na pasta automatch_ready
        caminho_novo_csv = pasta_automatch / f"fichas_automatch_{marca}.csv"
        
        df_automatch = pd.DataFrame(dados_automatch)

        df_automatch['ano'] = df_automatch['ano'].astype('Int64')
        df_automatch['lugares_grupo'] = df_automatch['lugares_grupo'].astype('Int64')

        df_automatch.to_csv(caminho_novo_csv, index=False, encoding="utf-8-sig")
        
        print(f" -> Sucesso! Convertido para: {pasta_automatch.name}/{caminho_novo_csv.name} ({len(dados_automatch)} linhas)")

if __name__ == "__main__":
    migrar_arquivos()
    print("\nMigração finalizada! Os arquivos CSV para o Supabase estão prontos.")