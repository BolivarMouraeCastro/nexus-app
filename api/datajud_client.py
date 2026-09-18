import requests, os

def buscar_jurisprudencia(tipo_acao: str) -> list[dict]:
    url = "https://api-publica.datajud.cnj.jus.br/api_publica_tjsp/_search"
    headers = {
        "Authorization": f"APIKey {os.environ.get('DATAJUD_API_KEY', '')}",
        "Content-Type": "application/json"
    }

    if tipo_acao.startswith('dano_moral_') or tipo_acao.startswith('negativacao_indevida'):
        codigo_classe = 6251
    elif tipo_acao == 'cobranca_indevida':
        codigo_classe = 12120
    elif tipo_acao in ('atraso_cancelamento_voo', 'extravio_bagagem'):
        codigo_classe = 6251
    elif tipo_acao in ('horas_extras', 'rescisao_indireta', 'assedio_moral', 'dano_moral_trabalhista'):
        codigo_classe = 981
    elif tipo_acao == 'revisao_contrato_bancario':
        codigo_classe = 12118
    else:
        codigo_classe = 6251

    payload = {
        "size": 5,
        "query": {
            "bool": {
                "must": [
                    {"term": {"classe.codigo": codigo_classe}},
                    {"range": {"dataJulgamento": {"gte": "2022-01-01", "lte": "2024-12-31"}}}
                ]
            }
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        # Handle utf-8 encoding specifically as requested
        response.encoding = 'utf-8'
        data = response.json()
        
        resultados = []
        hits = data.get("hits", {}).get("hits", [])
        for hit in hits:
            source = hit.get("_source", {})
            
            numero_cnj = source.get("numeroProcesso", "")
            classe = source.get("classe", {}).get("nome", "")
            
            assunto = ""
            assuntos = source.get("assuntos", [])
            if assuntos and isinstance(assuntos, list):
                assunto = assuntos[0].get("nome", "")
                
            data_julgamento = source.get("dataJulgamento", "")
            vara = source.get("orgaoJulgador", {}).get("nome", "")
            
            resultados.append({
                "numero_cnj": numero_cnj,
                "classe": classe,
                "assunto": assunto,
                "data_julgamento": data_julgamento,
                "vara": vara
            })
            
        return resultados
    except Exception:
        # Never break main flow
        return []
