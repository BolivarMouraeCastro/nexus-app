def calcular_honorarios(valor_causa: float, prob_exito: float, faixa_min: int, faixa_max: int, tempo_meses: int, vara: str) -> dict:
    honorarios_contratuais_min = float(faixa_min * 0.20)
    honorarios_contratuais_max = float(faixa_max * 0.30)
    
    valor_medio = (faixa_min + faixa_max) / 2.0
    honorarios_sucumbencia_estimado = valor_medio * 0.10
    
    vara_lower = vara.lower()
    if 'jec' in vara_lower or 'juizado especial cível' in vara_lower:
        custas_estimadas = 500.0
    elif 'trt' in vara_lower or 'trabalho' in vara_lower:
        custas_estimadas = 800.0
    else:
        custas_estimadas = 2000.0
        
    custo_total_cliente = custas_estimadas
    
    retorno_liquido_min = float(faixa_min) - honorarios_contratuais_min
    retorno_liquido_max = float(faixa_max) - float(faixa_max * 0.20)
    
    valor_esperado = valor_medio * prob_exito
    if custo_total_cliente > 0:
        roi_estimado = ((valor_esperado - custo_total_cliente) / custo_total_cliente) * 100.0
    else:
        roi_estimado = 0.0

    return {
        "honorarios_contratuais_min": honorarios_contratuais_min,
        "honorarios_contratuais_max": honorarios_contratuais_max,
        "honorarios_sucumbencia_estimado": honorarios_sucumbencia_estimado,
        "custas_estimadas": custas_estimadas,
        "custo_total_cliente": custo_total_cliente,
        "retorno_liquido_min": retorno_liquido_min,
        "retorno_liquido_max": retorno_liquido_max,
        "roi_estimado": roi_estimado
    }
