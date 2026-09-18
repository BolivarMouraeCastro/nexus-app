# -*- coding: utf-8 -*-

def gerar_simulador_html(dados: dict) -> str:
    def fmt_br(v):
        return f"{int(v):,}".replace(",", ".")

    cliente = dados.get('cliente', '')
    reu = dados.get('reu', '')
    prob = dados.get('prob_exito', 0)
    faixa_min = int(dados.get('faixa_min', 0))
    faixa_max = int(dados.get('faixa_max', 0))
    ponto_acordo = int(dados.get('ponto_acordo', 0))
    tempo_meses = int(dados.get('tempo_meses', 0))
    tempo_total = float(dados.get('tempo_total_anos', 0))
    taxa_recurso = float(dados.get('taxa_recurso', 0))
    valor_medio = (faixa_min + faixa_max) / 2
    valor_esperado = int(valor_medio * prob)
    fmin_fmt = fmt_br(faixa_min)
    fmax_fmt = fmt_br(faixa_max)
    vesp_fmt = fmt_br(valor_esperado)

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nexus - Simulador de Acordo</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:'Segoe UI',sans-serif;background:#F9FAFB;color:#111827}}
.header{{background:#0A192F;color:#fff;padding:28px 20px;text-align:center}}
.header h1{{font-size:24px;font-weight:800;letter-spacing:-1px;margin-bottom:4px}}
.header h1 span{{color:#C5A880}}
.header p{{font-size:14px;color:#C5A880;opacity:.9}}
.container{{max-width:720px;margin:28px auto;padding:0 16px}}
.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:28px}}
.metric{{background:#fff;border-radius:12px;padding:16px;text-align:center;box-shadow:0 2px 8px rgba(0,0,0,.06);border:1px solid #E5E7EB}}
.metric-label{{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;color:#6B7280;margin-bottom:8px}}
.metric-value{{font-size:20px;font-weight:800;color:#0A192F}}
.card{{background:#fff;border-radius:14px;box-shadow:0 2px 12px rgba(0,0,0,.08);padding:32px;margin-bottom:20px}}
.card h2{{text-align:center;font-size:18px;color:#0A192F;margin-bottom:24px}}
.slider-container{{padding:0 8px}}
.slider-labels{{display:flex;justify-content:space-between;font-size:12px;color:#6B7280;margin-bottom:8px}}
input[type=range]{{width:100%;height:8px;-webkit-appearance:none;background:linear-gradient(to right,#0A192F 0%,#C5A880 50%,#991b1b 100%);border-radius:4px;outline:none;margin:16px 0}}
input[type=range]::-webkit-slider-thumb{{-webkit-appearance:none;width:28px;height:28px;border-radius:50%;background:#0A192F;border:3px solid #C5A880;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.2)}}
.valor-display{{text-align:center;margin:20px 0}}
.valor-display .amount{{font-size:36px;font-weight:800;color:#0A192F}}
.results{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:24px}}
.result-card{{background:#F9FAFB;border-radius:10px;padding:16px;text-align:center;border:1px solid #E5E7EB}}
.result-card .label{{font-size:11px;font-weight:600;color:#6B7280;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px}}
.result-card .value{{font-size:18px;font-weight:700;color:#0A192F}}
.verdict{{margin-top:24px;padding:20px;border-radius:12px;text-align:center;font-size:16px;font-weight:700;transition:all .3s}}
.verdict.verde{{background:#DCFCE7;color:#166534;border:2px solid #22C55E}}
.verdict.amarelo{{background:#FEF9C3;color:#854D0E;border:2px solid #EAB308}}
.verdict.vermelho{{background:#FEE2E2;color:#991B1B;border:2px solid #EF4444}}
.verdict .subtitle{{font-size:13px;font-weight:400;margin-top:6px;opacity:.8}}
.footer{{text-align:center;padding:20px;font-size:11px;color:#9CA3AF;margin-top:20px}}
@media(max-width:600px){{.metrics{{grid-template-columns:repeat(2,1fr)}}.results{{grid-template-columns:1fr}}.metric-value{{font-size:16px}}}}
</style>
</head>
<body>
<div class="header">
  <h1>Nex<span>us</span></h1>
  <p>Simulador de Acordo</p>
  <p style="margin-top:8px;font-size:13px;color:#fff;opacity:.7">Cliente: {cliente} | Reu: {reu}</p>
</div>

<div class="container">
  <div class="metrics">
    <div class="metric">
      <div class="metric-label">Prob. de Exito</div>
      <div class="metric-value">{int(prob*100)}%</div>
    </div>
    <div class="metric">
      <div class="metric-label">Faixa Condenacao</div>
      <div class="metric-value" style="font-size:14px">R$ {fmin_fmt} a R$ {fmax_fmt}</div>
    </div>
    <div class="metric">
      <div class="metric-label">Tempo Estimado</div>
      <div class="metric-value">{tempo_meses} meses</div>
    </div>
    <div class="metric">
      <div class="metric-label">Taxa de Recurso</div>
      <div class="metric-value">{int(taxa_recurso*100)}%</div>
    </div>
  </div>

  <div class="card">
    <h2>Ajuste o Valor do Acordo</h2>
    <div class="slider-container">
      <div class="slider-labels">
        <span>R$ 0</span>
        <span>R$ {fmax_fmt}</span>
      </div>
      <input type="range" id="slider" min="0" max="{faixa_max}" step="100" value="{ponto_acordo}">
    </div>
    <div class="valor-display">
      <div class="amount" id="valorAcordo">R$ 0</div>
    </div>

    <div class="results">
      <div class="result-card">
        <div class="label">Valor do Acordo</div>
        <div class="value" id="rValorAcordo">R$ 0</div>
      </div>
      <div class="result-card">
        <div class="label">Valor Esperado (Justica)</div>
        <div class="value" id="rValorEsperado">R$ {vesp_fmt}</div>
      </div>
      <div class="result-card">
        <div class="label">Diferenca</div>
        <div class="value" id="rDiferenca">R$ 0</div>
      </div>
      <div class="result-card">
        <div class="label">Economia de Tempo</div>
        <div class="value" id="rTempo">{tempo_total} anos</div>
      </div>
    </div>

    <div class="verdict" id="verdict">
      <span id="verdictText">Mova o slider para simular</span>
      <div class="subtitle" id="verdictSub"></div>
    </div>
  </div>
</div>

<div class="footer">
  Nexus | Dr. Gabriel Roberto | OAB/SP 351.245<br>
  Esta simulacao nao constitui garantia de resultado processual.
</div>

<script>
(function() {{
  var PROB = {prob};
  var FAIXA_MIN = {faixa_min};
  var FAIXA_MAX = {faixa_max};
  var PONTO_ACORDO = {ponto_acordo};
  var TEMPO_TOTAL = {tempo_total};
  var VALOR_ESPERADO = {int(valor_esperado)};

  function fmt(v) {{
    return 'R$ ' + Math.round(v).toLocaleString('pt-BR');
  }}

  var slider = document.getElementById('slider');
  var elValor = document.getElementById('valorAcordo');
  var elRValor = document.getElementById('rValorAcordo');
  var elRExp = document.getElementById('rValorEsperado');
  var elRDif = document.getElementById('rDiferenca');
  var elRTempo = document.getElementById('rTempo');
  var elVerdict = document.getElementById('verdict');
  var elVText = document.getElementById('verdictText');
  var elVSub = document.getElementById('verdictSub');

  function update() {{
    var val = parseInt(slider.value);
    var dif = val - VALOR_ESPERADO;
    var pct = VALOR_ESPERADO > 0 ? Math.round((val / VALOR_ESPERADO) * 100) : 0;

    elValor.textContent = fmt(val);
    elRValor.textContent = fmt(val);
    elRExp.textContent = fmt(VALOR_ESPERADO);
    elRDif.textContent = fmt(Math.abs(dif));
    if (dif >= 0) {{
      elRDif.style.color = '#166534';
      elRDif.textContent = '+ ' + fmt(dif);
    }} else {{
      elRDif.style.color = '#991b1b';
      elRDif.textContent = '- ' + fmt(Math.abs(dif));
    }}
    elRTempo.textContent = TEMPO_TOTAL + ' anos';

    if (val >= PONTO_ACORDO) {{
      elVerdict.className = 'verdict verde';
      elVText.textContent = 'ACORDO RECOMENDADO';
      elVSub.textContent = 'Aceitar ' + fmt(val) + ' agora equivale a ' + pct + '% do valor esperado na justica, economizando ' + TEMPO_TOTAL + ' anos de processo.';
    }} else if (val >= PONTO_ACORDO * 0.7) {{
      elVerdict.className = 'verdict amarelo';
      elVText.textContent = 'ACORDO NEGOCIAVEL';
      elVSub.textContent = 'O valor esta abaixo do ideal mas dentro de uma margem negociavel. Tente negociar para acima de ' + fmt(PONTO_ACORDO) + '.';
    }} else {{
      elVerdict.className = 'verdict vermelho';
      elVText.textContent = 'ACORDO DESVANTAJOSO';
      elVSub.textContent = 'Este valor representa apenas ' + pct + '% do esperado. Recomenda-se continuar com o processo judicial.';
    }}
  }}

  slider.addEventListener('input', update);
  update();
}})();
</script>
</body>
</html>"""

