# -*- coding: utf-8 -*-
"""
Nexus - Aplicativo Web
===========================
Rode com: python app.py
Acesse em: http://localhost:5000
"""

import json, io, os, re, sqlite3, uuid, sys
from datetime import datetime
from functools import wraps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, request, send_file, render_template_string, session, redirect, url_for, Response

from datajud_client import buscar_jurisprudencia
from honorarios import calcular_honorarios
from simulador import gerar_simulador_html
from auth import LOGIN_HTML, PAINEL_HTML, ADMIN_USER, verificar_login, calcular_metricas, gerar_csv

app = Flask(__name__)
app.secret_key = 'nexus-secret-key-2026-gabriel-roberto'

def get_db():
    conn = sqlite3.connect('/tmp/historico.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    import uuid as _uuid
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS laudos (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        data_hora TEXT, 
        cliente TEXT, 
        reu TEXT, 
        tipo_acao TEXT, 
        vara TEXT, 
        prob_exito REAL, 
        faixa_min INTEGER, 
        faixa_max INTEGER, 
        ponto_acordo INTEGER,
        token TEXT,
        tempo_meses INTEGER,
        tempo_total REAL,
        taxa_recurso REAL)''')
    # Migration: adiciona colunas se tabela antiga
    try: conn.execute("ALTER TABLE laudos ADD COLUMN token TEXT")
    except: pass
    try: conn.execute("ALTER TABLE laudos ADD COLUMN tempo_meses INTEGER")
    except: pass
    try: conn.execute("ALTER TABLE laudos ADD COLUMN tempo_total REAL")
    except: pass
    try: conn.execute("ALTER TABLE laudos ADD COLUMN taxa_recurso REAL")
    except: pass
    conn.commit()
    conn.close()

init_db()

ESCRITORIO = {
    "advogado": "Dr. Gabriel Roberto",
    "oab":      "OAB/SP 351.245",
    "nome":     "Gabriel Roberto",
}

BASE_FILE = "base_tjsp.json"
with open(BASE_FILE, encoding="utf-8") as f:
    BASE = json.load(f)

ARIAL   = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts', 'arial.ttf')
ARIAL_B = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts', 'arialbd.ttf')
ARIAL_I = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'fonts', 'ariali.ttf')

# ─────────────────────────────────────────────
# MOTOR DE SCORING
# ─────────────────────────────────────────────
def calcular_score(caso):
    vara_data = BASE["varas"].get(caso["vara"], BASE["varas"]["VARA_CIVEL_INTERIOR"])
    acao_data = vara_data["acoes"].get(caso["tipo_acao"], list(vara_data["acoes"].values())[0])
    fatores   = BASE["fatores_ajuste"]

    prob   = acao_data["taxa_procedencia"]
    ajuste = sum(delta for fator, delta in fatores.items() if caso.get(fator))
    prob   = max(0.05, min(0.92, prob + ajuste))

    taxa_recurso = BASE["taxa_recurso_por_reu"].get(caso["tipo_reu"], 0.60)
    tipo_reforma = "dano_moral" if "dano_moral" in caso["tipo_acao"] else "revisao_contrato"
    taxa_reforma  = BASE["taxa_reforma_2_instancia"].get(tipo_reforma, 0.22)

    tempo_sent  = acao_data["tempo_medio_meses"]
    tempo_total = (tempo_sent + (18 if taxa_recurso > 0.5 else 6)) / 12

    valor_medio = acao_data["valor_medio"]
    faixa_min   = acao_data["faixa_tipica_min"]
    faixa_max   = acao_data["faixa_tipica_max"]

    valor_causa = float(caso.get("valor_causa") or 0)
    if valor_causa and valor_causa < valor_medio:
        valor_medio = min(valor_medio, valor_causa * 0.8)
        faixa_max   = min(faixa_max, valor_causa)

    valor_esperado = valor_medio * prob
    ponto_acordo   = valor_esperado * 0.70

    return {
        "prob":           prob,
        "tempo_sent":     tempo_sent,
        "tempo_total":    round(tempo_total, 1),
        "taxa_recurso":   taxa_recurso,
        "valor_medio":    round(valor_medio),
        "faixa_min":      round(faixa_min),
        "faixa_max":      round(faixa_max),
        "valor_esperado": round(valor_esperado),
        "ponto_acordo":   round(ponto_acordo),
        "confianca":      acao_data["confianca"],
        "vara_desc":      vara_data["descricao"],
    }

# ─────────────────────────────────────────────
# GERACAO DO PDF (Arial Unicode)
# ─────────────────────────────────────────────
def gerar_pdf(caso, score):
    from fpdf import FPDF

    # Cores da landing page
    NAVY   = (10, 25, 47)    # #0A192F
    NAVY2  = (23, 42, 69)    # #172A45
    GOLD   = (197, 168, 128) # #C5A880
    WHITE  = (255, 255, 255)
    GRAY   = (249, 250, 251) # #F9FAFB
    TEXT   = (17, 24, 39)    # #111827
    MUTED  = (75, 85, 99)    # #4B5563
    BORDER = (229, 231, 235) # #E5E7EB
    GREEN  = (22, 101, 52)   # #166534
    RED    = (153, 27, 27)   # #991b1b

    class PDF(FPDF):
        def __init__(self):
            super().__init__()
            self.add_font("Arial",  "",  ARIAL)
            self.add_font("Arial",  "B", ARIAL_B)
            self.add_font("Arial",  "I", ARIAL_I)

        def header(self):
            self.set_fill_color(*NAVY)
            self.rect(0, 0, 210, 36, "F")
            # Linha dourada
            self.set_fill_color(*GOLD)
            self.rect(0, 36, 210, 1.5, "F")
            self.set_y(8)
            self.set_font("Arial", "B", 22)
            self.set_text_color(*WHITE)
            self.cell(0, 10, "Nexus", new_x="LMARGIN", new_y="NEXT", align="C")
            self.set_font("Arial", "", 9)
            self.set_text_color(*GOLD)
            self.cell(0, 6, "JURIMETRIA & RISCO ESTRATEGICO", new_x="LMARGIN", new_y="NEXT", align="C")
            self.set_text_color(*TEXT)
            self.ln(8)

        def footer(self):
            self.set_y(-20)
            self.set_fill_color(*NAVY)
            self.rect(0, self.get_y() - 2, 210, 24, "F")
            self.set_font("Arial", "I", 7)
            self.set_text_color(150, 160, 180)
            self.cell(0, 4,
                "Este laudo e uma analise estatistica baseada em dados historicos publicos. "
                "Nao constitui garantia de resultado processual.",
                new_x="LMARGIN", new_y="NEXT", align="C")
            self.set_font("Arial", "", 7)
            self.set_text_color(*GOLD)
            self.cell(0, 4,
                f"{ESCRITORIO['advogado']}  |  {ESCRITORIO['oab']}  |  Pag. {self.page_no()}",
                align="C")

    pdf = PDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=24)

    data_hoje  = datetime.now().strftime("%d/%m/%Y")
    acao_label = caso["tipo_acao"].replace("_", " ").title()
    vara_label = caso["vara"].replace("_", " ").title()

    # --- Cabeçalho do caso ---
    pdf.set_font("Arial", "", 9)
    pdf.set_fill_color(*GRAY)
    pdf.set_text_color(*MUTED)
    pdf.cell(0, 7, f"Data: {data_hoje}   |   Cliente: {caso['cliente']}   |   Reu: {caso['reu']}", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.cell(0, 7, f"Acao: {acao_label}   |   Vara/Juizo: {vara_label}", new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.ln(6)

    # --- Titulo PANORAMA ---
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, "PANORAMA DO CASO", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*GOLD)
    pdf.set_line_width(0.8)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # --- GRÁFICO DE BARRAS HORIZONTAIS ---
    bar_data = [
        ("Probabilidade de Exito",   score["prob"],         GOLD),
        ("Prob. Improcedencia",       1 - score["prob"],     MUTED),
        ("Taxa de Recurso do Reu",   score["taxa_recurso"], NAVY2),
    ]
    bar_max_w = 100  # largura maxima da barra em mm
    bar_h     = 8    # altura de cada barra
    bar_x     = 75   # inicio X das barras
    label_x   = 12   # inicio X dos labels

    for label, value, color in bar_data:
        y = pdf.get_y()
        # Label
        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(*MUTED)
        pdf.set_xy(label_x, y)
        pdf.cell(60, bar_h, label)
        # Barra de fundo
        pdf.set_fill_color(*BORDER)
        pdf.rect(bar_x, y + 1, bar_max_w, bar_h - 2, "F")
        # Barra de valor
        pdf.set_fill_color(*color)
        bar_w = max(2, value * bar_max_w)
        pdf.rect(bar_x, y + 1, bar_w, bar_h - 2, "F")
        # Percentual
        pdf.set_font("Arial", "B", 9)
        pdf.set_text_color(*NAVY)
        pdf.set_xy(bar_x + bar_max_w + 3, y)
        pdf.cell(20, bar_h, f"{value:.0%}")
        pdf.ln(bar_h + 2)

    pdf.ln(3)

    # --- Métricas em blocos ---
    def bloco(titulo, valor, cor_borda=GOLD):
        pdf.set_draw_color(*cor_borda)
        pdf.set_line_width(0.6)
        y = pdf.get_y()
        pdf.rect(10, y, 190, 9)
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.set_xy(14, y + 1)
        pdf.cell(90, 7, titulo)
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(*NAVY)
        pdf.set_xy(110, y + 1)
        pdf.cell(86, 7, valor, align="R")
        pdf.set_y(y + 11)

    faixa_txt = f"R$ {score['faixa_min']:,}  a  R$ {score['faixa_max']:,}".replace(",", ".")
    acordo_txt = f"R$ {score['ponto_acordo']:,}".replace(",", ".")

    bloco("Tempo Estimado ate Sentenca",     f"{score['tempo_sent']} meses")
    bloco("Faixa de Condenacao Historica",   faixa_txt)
    bloco("Tempo Total com Recursos",        f"{score['tempo_total']:.1f} anos")
    bloco("Ponto de Equilibrio para Acordo", acordo_txt, cor_borda=GOLD)

    pdf.ln(6)

    # --- ANÁLISE DETALHADA ---
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 8, "ANALISE DETALHADA", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*GOLD)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

    if score["prob"] >= 0.60:
        avaliacao = "O caso apresenta boas perspectivas de exito judicial."
    elif score["prob"] >= 0.40:
        avaliacao = "O caso apresenta perspectivas moderadas, com resultado incerto."
    else:
        avaliacao = "O caso apresenta desafios significativos. A probabilidade de exito e inferior a media."

    ponto_forte = caso.get("ponto_forte", "").strip()
    ponto_fraco = caso.get("ponto_fraco", "").strip()
    descricao   = caso.get("descricao",   "").strip()

    valor_med  = f"R$ {score['valor_medio']:,}".replace(",", ".")
    ponto_txt  = f"R$ {score['ponto_acordo']:,}".replace(",", ".")

    texto = f"{avaliacao} Com base nos dados historicos do TJSP, a analise indica probabilidade de exito de {score['prob']:.0%}, com confianca {score['confianca']} baseada em grande volume de casos similares.\n\n"

    if descricao:
        texto += f"Situacao do caso: {descricao}\n\n"

    texto += (
        f"Em caso de procedencia, a faixa historica de condenacao situa-se entre {faixa_txt} "
        f"(valor medio: {valor_med}).\n\n"
        f"O tempo estimado ate sentenca e de {score['tempo_sent']} meses. "
        f"Ha probabilidade de {score['taxa_recurso']:.0%} de recurso pelo reu, "
        f"podendo o processo se estender a {score['tempo_total']:.1f} anos no total.\n\n"
        f"Financeiramente, um acordo acima de {ponto_txt} seria matematicamente vantajoso "
        f"considerando tempo e risco processual."
    )

    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(40, 40, 60)
    pdf.multi_cell(0, 6, texto)
    pdf.ln(4)

    # --- PONTOS RELEVANTES ---
    if ponto_forte or ponto_fraco:
        # Verifica se cabe na página (precisa de ~80mm)
        if pdf.get_y() > 180:
            pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 8, "PONTOS RELEVANTES", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*GOLD)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

        if ponto_forte:
            if pdf.get_y() > 210:
                pdf.add_page()
            pdf.set_fill_color(230, 242, 230)
            pdf.set_font("Arial", "B", 9)
            pdf.set_text_color(*GREEN)
            pdf.cell(0, 6, "  PONTO FORTE", new_x="LMARGIN", new_y="NEXT", fill=True)
            pdf.set_font("Arial", "", 9)
            pdf.set_text_color(40, 70, 40)
            pdf.set_fill_color(242, 252, 245)
            pdf.multi_cell(0, 6, f"  {ponto_forte}", fill=True)
            pdf.ln(3)

        if ponto_fraco:
            if pdf.get_y() > 210:
                pdf.add_page()
            pdf.set_fill_color(252, 230, 230)
            pdf.set_font("Arial", "B", 9)
            pdf.set_text_color(*RED)
            pdf.cell(0, 6, "  PONTO DE ATENCAO", new_x="LMARGIN", new_y="NEXT", fill=True)
            pdf.set_font("Arial", "", 9)
            pdf.set_text_color(100, 30, 30)
            pdf.set_fill_color(255, 245, 246)
            pdf.multi_cell(0, 6, f"  {ponto_fraco}", fill=True)
            pdf.ln(3)

    # --- JURISPRUDÊNCIA RELEVANTE ---
    juris = caso.get("_jurisprudencia", [])
    if juris:
        if pdf.get_y() > 180:
            pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 8, "JURISPRUDENCIA RELEVANTE", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*GOLD)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)
        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(*MUTED)
        for i, j in enumerate(juris[:5], 1):
            data_j = j.get("data_julgamento", "")[:10] if j.get("data_julgamento") else ""
            txt = f"{i}. CNJ {j.get('numero_cnj','')}  |  {j.get('classe','')}  |  {j.get('assunto','')}  |  {data_j}  |  {j.get('vara','')}"
            pdf.cell(0, 5, txt, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # --- ESTIMATIVA DE HONORÁRIOS ---
    hon = caso.get("_honorarios")
    if hon:
        # Precisa de ~60mm para a tabela completa
        if pdf.get_y() > 170:
            pdf.add_page()
        pdf.set_font("Arial", "B", 12)
        pdf.set_text_color(*NAVY)
        pdf.cell(0, 8, "ESTIMATIVA DE HONORARIOS", new_x="LMARGIN", new_y="NEXT")
        pdf.set_draw_color(*GOLD)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

        def fmt(v): return f"R$ {int(v):,}".replace(",", ".")

        def bloco_hon(titulo, valor):
            pdf.set_draw_color(*BORDER)
            pdf.set_line_width(0.4)
            y = pdf.get_y()
            pdf.rect(10, y, 190, 8)
            pdf.set_font("Arial", "", 8)
            pdf.set_text_color(*MUTED)
            pdf.set_xy(14, y + 1)
            pdf.cell(100, 6, titulo)
            pdf.set_font("Arial", "B", 9)
            pdf.set_text_color(*NAVY)
            pdf.set_xy(120, y + 1)
            pdf.cell(76, 6, valor, align="R")
            pdf.set_y(y + 9)

        bloco_hon("Honorarios Contratuais (20-30% sobre exito)", f"{fmt(hon['honorarios_contratuais_min'])} a {fmt(hon['honorarios_contratuais_max'])}")
        bloco_hon("Honorarios de Sucumbencia (estimado)", fmt(hon['honorarios_sucumbencia_estimado']))
        bloco_hon("Custas Processuais Estimadas", fmt(hon['custas_estimadas']))
        bloco_hon("Retorno Liquido ao Cliente (estimado)", f"{fmt(hon['retorno_liquido_min'])} a {fmt(hon['retorno_liquido_max'])}")
        bloco_hon("ROI Estimado", f"{hon['roi_estimado']:.0f}%")
        pdf.ln(3)

    # --- Assinatura ---
    pdf.ln(6)
    pdf.set_font("Arial", "I", 9)
    pdf.set_text_color(*GOLD)
    pdf.cell(0, 5, f"Emitido em {data_hoje} por {ESCRITORIO['advogado']} - {ESCRITORIO['oab']}", align="R", new_x="LMARGIN", new_y="NEXT")

    buf = io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf

# ─────────────────────────────────────────────
# HTML DO FORMULÁRIO
# ─────────────────────────────────────────────
FORM_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nexus - Gerar Laudo</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#1a1a2e;font-size:14px}
  .header{background:linear-gradient(135deg,#1a1a2e,#0f3460);color:#fff;padding:20px 32px;display:flex;align-items:center;gap:16px}
  .header h1{font-size:24px;font-weight:800;letter-spacing:-1px}
  .header h1 span{color:#e94560}
  .header p{font-size:12px;opacity:.7;margin-top:2px}
  .adv-badge{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);border-radius:8px;padding:8px 14px;font-size:12px;text-align:right;margin-left:auto}
  .adv-badge strong{display:block;font-size:13px}
  .container{max-width:760px;margin:28px auto;padding:0 16px}
  .card{background:#fff;border-radius:14px;box-shadow:0 2px 12px rgba(0,0,0,.08);overflow:hidden;margin-bottom:20px}
  .card-header{background:#1a1a2e;color:#fff;padding:14px 20px;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
  .card-body{padding:20px}
  .grid2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
  .field{margin-bottom:14px}
  label{display:block;font-size:12px;font-weight:600;color:#555;margin-bottom:5px;text-transform:uppercase;letter-spacing:.4px}
  input[type=text],input[type=number],select,textarea{width:100%;padding:10px 12px;border:1.5px solid #e0e0e0;border-radius:8px;font-size:13px;color:#1a1a2e;background:#fafafa;transition:border .2s}
  input:focus,select:focus,textarea:focus{outline:none;border-color:#e94560;background:#fff}
  textarea{min-height:70px;resize:vertical}
  .checks{display:flex;flex-direction:column;gap:10px}
  .check-item{display:flex;align-items:center;gap:10px;font-size:13px;cursor:pointer;padding:8px 10px;border-radius:8px;border:1.5px solid #eee;transition:border .2s}
  .check-item:hover{border-color:#e94560}
  .check-item input{width:16px;height:16px;accent-color:#e94560;cursor:pointer;flex-shrink:0}
  .check-item.positivo{color:#166534}
  .check-item.negativo{color:#991b1b}
  .btn-gerar{width:100%;padding:15px;background:linear-gradient(135deg,#e94560,#c73652);color:#fff;border:none;border-radius:10px;font-size:15px;font-weight:800;cursor:pointer;letter-spacing:.5px;transition:all .2s;box-shadow:0 4px 14px rgba(233,69,96,.3)}
  .btn-gerar:hover{transform:translateY(-2px);box-shadow:0 6px 18px rgba(233,69,96,.4)}
  .nota{background:#fffbeb;border-left:4px solid #f59e0b;padding:12px 16px;border-radius:0 8px 8px 0;font-size:12px;color:#78350f;margin-bottom:20px;line-height:1.6}
  .erro{background:#fee2e2;border-left:4px solid #e94560;padding:12px 16px;border-radius:0 8px 8px 0;font-size:13px;color:#991b1b;margin-bottom:16px}
  @media(max-width:580px){.grid2{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>Nex<span>us</span></h1>
    <p>Sistema de Laudo de Risco Processual</p>
  </div>
  <a href="/painel" style="color:#fff;text-decoration:none;font-weight:600;font-size:14px;margin-left:20px;padding:8px 12px;background:rgba(255,255,255,0.1);border-radius:6px;">Painel</a>
  <div class="adv-badge">
    <strong>{{ adv }}</strong>{{ oab }}
  </div>
</div>

<div class="container">

  <div class="nota">
    Preencha os dados do caso abaixo e clique em <strong>Gerar Laudo PDF</strong>.
    O arquivo sera baixado automaticamente.
  </div>

  {% if erro %}
  <div class="erro"><strong>Erro:</strong> {{ erro }}</div>
  {% endif %}

  <form method="POST" action="/gerar">

    <div class="card">
      <div class="card-header">1. Dados Basicos</div>
      <div class="card-body">
        <div class="grid2">
          <div class="field">
            <label>Nome do Cliente</label>
            <input type="text" name="cliente" placeholder="Ex: Joao da Silva" required>
          </div>
          <div class="field">
            <label>Reu (Empresa ou Pessoa)</label>
            <input type="text" name="reu" placeholder="Ex: Banco Bradesco S.A." required>
          </div>
        </div>
        <div class="grid2">
          <div class="field">
            <label>Tipo do Reu</label>
            <select name="tipo_reu" required>
              <option value="">Selecione...</option>
              <option value="banco">Banco</option>
              <option value="operadora_telefonia">Operadora de Telefonia</option>
              <option value="plano_saude">Plano de Saude</option>
              <option value="empresa_varejo">Empresa de Varejo / Comercio</option>
              <option value="companhia_aerea">Companhia Aérea</option>
              <option value="pessoa_fisica">Pessoa Fisica</option>
            </select>
          </div>
          <div class="field">
            <label>Valor da Causa (R$)</label>
            <input type="number" name="valor_causa" placeholder="Ex: 15000" min="0">
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">2. Tipo de Acao e Vara</div>
      <div class="card-body">
        <div class="grid2">
          <div class="field">
            <label>Tipo de Acao</label>
            <select name="tipo_acao" required>
              <option value="">Selecione...</option>
              <optgroup label="Dano Moral (Civel)">
                <option value="dano_moral_banco">Dano Moral - Banco</option>
                <option value="dano_moral_operadora">Dano Moral - Operadora Telefonia</option>
                <option value="dano_moral_plano_saude">Dano Moral - Plano de Saude</option>
                <option value="negativacao_indevida_jec">Negativação Indevida (JEC)</option>
              </optgroup>
              <optgroup label="Outros (Civel)">
                <option value="cobranca_indevida">Cobranca Indevida</option>
                <option value="revisao_contrato_bancario">Revisao de Contrato Bancario</option>
                <option value="rescisao_contrato">Rescisao de Contrato</option>
                <option value="indenizacao_acidente">Indenizacao por Acidente</option>
                <option value="despejo">Despejo / Locacao</option>
                <option value="produto_defeituoso">Produto Defeituoso / CDC</option>
                <option value="negativacao_indevida">Negativação Indevida (Vara Civel)</option>
                <option value="erro_medico">Erro Médico</option>
                <option value="dano_estetico">Dano Estético</option>
                <option value="responsabilidade_civil_condominio">Responsabilidade Civil Condomínio</option>
              </optgroup>
              <optgroup label="Direito do Passageiro (Aéreo)">
                <option value="atraso_cancelamento_voo">Atraso ou Cancelamento de Voo</option>
                <option value="extravio_bagagem">Extravio de Bagagem</option>
              </optgroup>
              <optgroup label="Trabalhista (TRT)">
                <option value="horas_extras">Horas Extras</option>
                <option value="rescisao_indireta">Rescisao Indireta</option>
                <option value="assedio_moral">Assedio Moral</option>
                <option value="dano_moral_trabalhista">Dano Moral Trabalhista</option>
                <option value="adicional_insalubridade">Adicional de Insalubridade</option>
                <option value="acidente_trabalho">Acidente de Trabalho</option>
              </optgroup>
            </select>
          </div>
          <div class="field">
            <label>Vara / Juizo</label>
            <select name="vara" required>
              <option value="">Selecione...</option>
              <option value="JEC_GERAL">Juizado Especial Civel (JEC)</option>
              <option value="VARA_CIVEL_CAPITAL">Vara Civel - Capital SP</option>
              <option value="VARA_CIVEL_INTERIOR">Vara Civel - Interior SP</option>
              <option value="TRT2_SAO_PAULO">TRT 2a Regiao (Trabalhista)</option>
            </select>
          </div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">3. Fatores do Caso</div>
      <div class="card-body">
        <div class="checks">
          <label class="check-item positivo">
            <input type="checkbox" name="prova_documental_forte" value="1">
            Tem prova documental forte (contratos, comprovantes, prints, laudos)
          </label>
          <label class="check-item positivo">
            <input type="checkbox" name="caso_recente_jurisprudencia_favoravel" value="1">
            Ha jurisprudencia recente favoravel neste tipo de caso
          </label>
          <label class="check-item positivo">
            <input type="checkbox" name="advogado_especialista_area" value="1">
            Advogado especialista na area (teses bem fundamentadas)
          </label>
          <label class="check-item negativo">
            <input type="checkbox" name="ausencia_testemunhas" value="1">
            Ausencia de testemunhas (caso depende so de documentos)
          </label>
          <label class="check-item negativo">
            <input type="checkbox" name="caso_repetitivo_mass_litigation" value="1">
            Caso de mass litigation (reu tem muitos processos identicos)
          </label>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-header">4. Descricao do Caso</div>
      <div class="card-body">
        <div class="field">
          <label>Resumo do Problema</label>
          <textarea name="descricao" placeholder="Ex: Negativacao indevida no SPC por divida ja quitada em 03/2024. Cliente possui comprovante..."></textarea>
        </div>
        <div class="grid2">
          <div class="field">
            <label>Principal Ponto Forte</label>
            <textarea name="ponto_forte" placeholder="Deixe em branco para a IA gerar automaticamente ou digite..."></textarea>
          </div>
          <div class="field">
            <label>Principal Ponto de Atencao</label>
            <textarea name="ponto_fraco" placeholder="Deixe em branco para a IA gerar automaticamente ou digite..."></textarea>
          </div>
        </div>
      </div>
    </div>

    <button type="submit" class="btn-gerar">GERAR LAUDO PDF</button>
    <p style="text-align:center;margin-top:12px;font-size:12px;color:#999">
      A IA analisa o relato e gera automaticamente os pontos fortes e de atencao.
    </p>
    <br>
  </form>
</div>
</body>
</html>"""


LANDING_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Nexus | Jurimetria e Análise de Risco</title>
<style>
  :root {
    --primary: #0A192F; /* Deep Navy */
    --secondary: #172A45; /* Lighter Navy */
    --accent: #C5A880; /* Elegant Gold/Bronze */
    --accent-hover: #A88B60;
    --text-dark: #111827;
    --text-muted: #4B5563;
    --bg-light: #F9FAFB;
    --white: #FFFFFF;
    --border: #E5E7EB;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: var(--text-dark);
    background-color: var(--bg-light);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
  }

  /* Typography */
  h1, h2, h3, h4 {
    font-family: "Georgia", "Times New Roman", serif;
    font-weight: 400;
    color: var(--primary);
  }

  /* Navigation */
  header {
    background-color: var(--white);
    border-bottom: 1px solid var(--border);
    padding: 20px 0;
    position: sticky;
    top: 0;
    z-index: 100;
  }
  .nav-container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 24px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .logo {
    font-family: "Georgia", serif;
    font-size: 24px;
    font-weight: 600;
    color: var(--primary);
    text-decoration: none;
    letter-spacing: 0.5px;
  }
  .logo span { color: var(--accent); }
  .btn-nav {
    background-color: var(--primary);
    color: var(--white);
    padding: 10px 24px;
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 1px;
    transition: background-color 0.3s;
  }
  .btn-nav:hover { background-color: var(--accent); color: var(--white); }

  /* Hero Section */
  .hero {
    background-color: var(--primary);
    color: var(--white);
    padding: 100px 24px;
    text-align: center;
  }
  .hero-inner {
    max-width: 800px;
    margin: 0 auto;
  }
  .hero h1 {
    color: var(--white);
    font-size: 48px;
    line-height: 1.2;
    margin-bottom: 24px;
  }
  .hero p {
    font-size: 18px;
    color: #9CA3AF;
    margin-bottom: 40px;
    font-weight: 300;
  }
  .btn-primary {
    display: inline-block;
    background-color: var(--accent);
    color: var(--white);
    padding: 16px 40px;
    text-decoration: none;
    font-size: 15px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    transition: all 0.3s ease;
    border: 1px solid var(--accent);
  }
  .btn-primary:hover {
    background-color: var(--accent-hover);
    border-color: var(--accent-hover);
  }
  .btn-outline {
    display: inline-block;
    background-color: transparent;
    color: var(--white);
    padding: 16px 40px;
    text-decoration: none;
    font-size: 15px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    transition: all 0.3s ease;
    border: 1px solid var(--white);
    margin-left: 16px;
  }
  .btn-outline:hover {
    background-color: var(--white);
    color: var(--primary);
  }

  /* Section Styles */
  .section { padding: 90px 24px; }
  .section-light { background-color: var(--white); }
  .section-dark { background-color: var(--bg-light); }
  .container { max-width: 1200px; margin: 0 auto; }
  .section-title {
    text-align: center;
    font-size: 36px;
    margin-bottom: 16px;
  }
  .section-subtitle {
    text-align: center;
    font-size: 16px;
    color: var(--text-muted);
    margin-bottom: 64px;
    max-width: 600px;
    margin-left: auto;
    margin-right: auto;
  }

  /* Features Grid */
  .grid-3 {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
    gap: 40px;
  }
  .feature-card {
    background: var(--white);
    padding: 40px 32px;
    border-top: 4px solid var(--accent);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    transition: transform 0.3s ease;
  }
  .feature-card:hover { transform: translateY(-5px); }
  .feature-icon {
    width: 48px;
    height: 48px;
    color: var(--primary);
    margin-bottom: 24px;
  }
  .feature-card h3 {
    font-size: 22px;
    margin-bottom: 16px;
    font-family: -apple-system, sans-serif;
    font-weight: 600;
  }
  .feature-card p {
    color: var(--text-muted);
    font-size: 15px;
  }

  /* Report Mockup */
  .report-showcase {
    display: flex;
    align-items: center;
    gap: 64px;
  }
  .report-text { flex: 1; }
  .report-text h2 { font-size: 36px; margin-bottom: 24px; }
  .report-text p { font-size: 16px; color: var(--text-muted); margin-bottom: 24px; }
  .report-text ul { list-style: none; margin-bottom: 32px; }
  .report-text li { 
    margin-bottom: 12px; 
    display: flex; 
    align-items: center; 
    gap: 12px;
    color: var(--primary);
    font-weight: 500;
  }
  .report-text li svg { width: 20px; height: 20px; color: var(--accent); }
  
  .report-visual {
    flex: 1;
    background: var(--white);
    padding: 40px;
    border: 1px solid var(--border);
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
  }
  .mock-header { border-bottom: 2px solid var(--primary); padding-bottom: 16px; margin-bottom: 24px; }
  .mock-title { font-family: "Georgia", serif; font-size: 20px; color: var(--primary); }
  .mock-row { display: flex; justify-content: space-between; padding: 12px 0; border-bottom: 1px solid #F3F4F6; }
  .mock-label { font-weight: 600; color: var(--text-dark); font-size: 13px; text-transform: uppercase; }
  .mock-value { color: var(--primary); font-size: 15px; }
  .mock-highlight { color: var(--accent); font-weight: 700; }

  /* Pricing */
  .pricing-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 32px;
    align-items: center;
  }
  .pricing-card {
    background: var(--white);
    border: 1px solid var(--border);
    padding: 48px 32px;
    text-align: center;
    transition: all 0.3s ease;
  }
  .pricing-card.popular {
    border-color: var(--primary);
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    transform: scale(1.05);
    background-color: var(--primary);
    color: var(--white);
  }
  .pricing-card.popular h3, .pricing-card.popular .price, .pricing-card.popular li {
    color: var(--white);
  }
  .pricing-card h3 {
    font-family: -apple-system, sans-serif;
    font-size: 20px;
    font-weight: 600;
    margin-bottom: 16px;
    text-transform: uppercase;
    letter-spacing: 1px;
  }
  .price {
    font-size: 40px;
    font-weight: 300;
    color: var(--primary);
    margin-bottom: 24px;
    font-family: "Georgia", serif;
  }
  .price span { font-size: 16px; color: var(--text-muted); font-family: -apple-system, sans-serif; }
  .pricing-card.popular .price span { color: #9CA3AF; }
  .pricing-features {
    list-style: none;
    margin-bottom: 40px;
    text-align: left;
  }
  .pricing-features li {
    padding: 12px 0;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
    color: var(--text-muted);
  }
  .pricing-card.popular .pricing-features li { border-color: rgba(255,255,255,0.1); }
  
  .btn-pricing {
    display: block;
    width: 100%;
    padding: 14px;
    background: var(--white);
    color: var(--primary);
    border: 1px solid var(--primary);
    text-decoration: none;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    font-size: 13px;
    transition: all 0.3s;
  }
  .btn-pricing:hover { background: var(--primary); color: var(--white); }
  
  .pricing-card.popular .btn-pricing {
    background: var(--accent);
    border-color: var(--accent);
    color: var(--white);
  }
  .pricing-card.popular .btn-pricing:hover {
    background: var(--accent-hover);
  }

  /* CTA Section */
  .cta-section {
    background-color: var(--secondary);
    color: var(--white);
    text-align: center;
    padding: 80px 24px;
  }
  .cta-section h2 { color: var(--white); margin-bottom: 24px; font-size: 32px; }
  .cta-section p { color: #9CA3AF; margin-bottom: 40px; font-size: 18px; }

  /* Footer */
  footer {
    background-color: var(--primary);
    color: #9CA3AF;
    text-align: center;
    padding: 40px 24px;
    font-size: 14px;
    border-top: 1px solid rgba(255,255,255,0.1);
  }
  footer p { margin-bottom: 8px; }

  @media (max-width: 768px) {
    .hero h1 { font-size: 36px; }
    .btn-outline { margin-left: 0; margin-top: 16px; display: block; }
    .report-showcase { flex-direction: column; }
    .pricing-card.popular { transform: scale(1); }
  }
</style>
</head>
<body>

  <!-- Header -->
  <header>
    <div class="nav-container">
      <a href="#" class="logo">Nex<span>us</span></a>
      <div style="display:flex;gap:12px;align-items:center">
        <a href="/login" style="background:#C5A880;color:#0A192F;padding:10px 24px;border-radius:6px;font-weight:700;text-decoration:none;font-size:14px;transition:all .2s;">Acessar Sistema</a>
      </div>
    </div>
  </header>

  <!-- Hero -->
  <section class="hero">
    <div class="hero-inner">
      <h1>Inteligência Preditiva para Decisões Estratégicas</h1>
      <p>Transforme a incerteza jurídica em análises de risco quantificáveis. O Nexus fornece auditoria preditiva e provisionamento preciso para bancas multinacionais e departamentos corporativos.</p>
      <div style="display:flex;gap:16px;flex-wrap:wrap;justify-content:center;">
        <a href="#planos" class="btn-primary">Ver Planos Corporativos</a>
        <a href="/login" style="display:inline-block;padding:16px 32px;font-size:15px;font-weight:700;border-radius:8px;text-decoration:none;border:2px solid #C5A880;color:#C5A880;transition:all .3s;">Acessar Sistema</a>
        <a href="#solucao" style="display:inline-block;padding:16px 32px;font-size:15px;font-weight:700;border-radius:8px;text-decoration:none;border:2px solid rgba(255,255,255,.3);color:rgba(255,255,255,.8);transition:all .3s;">Como Funciona</a>
      </div>
    </div>
  </section>

  <!-- Solução / Mockup -->
  <section id="solucao" class="section section-light">
    <div class="container report-showcase">
      <div class="report-text">
        <h2>Do Subjetivo ao Quantificável</h2>
        <p>Substitua horas de pesquisa jurisprudencial manual e estimativas baseadas em intuição por relatórios estatísticos fundamentados em dados reais do Tribunal de Justiça.</p>
        <ul>
          <li>
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="square" stroke-linejoin="miter" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
            Mitigação de Riscos em Mass Litigation
          </li>
          <li>
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="square" stroke-linejoin="miter" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
            Provisionamento Contábil de Passivos
          </li>
          <li>
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="square" stroke-linejoin="miter" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
            Padronização de Relatórios de Compliance
          </li>
        </ul>
      </div>
      <div class="report-visual">
        <div class="mock-header">
          <div class="mock-title">LAUDO DE RISCO PROCESSUAL</div>
          <div style="font-size: 11px; color: var(--text-muted); margin-top: 4px; text-transform: uppercase;">Uso Interno / Confidencial</div>
        </div>
        <div class="mock-row">
          <span class="mock-label">Probabilidade de Êxito</span>
          <span class="mock-value">62% (Risco Moderado)</span>
        </div>
        <div class="mock-row">
          <span class="mock-label">Tempo Est. de Resolução</span>
          <span class="mock-value">18 a 24 meses</span>
        </div>
        <div class="mock-row">
          <span class="mock-label">Faixa de Condenação Histórica</span>
          <span class="mock-value">R$ 15.000 a R$ 45.000</span>
        </div>
        <div class="mock-row" style="border-bottom: none; padding-bottom: 0;">
          <span class="mock-label">Ponto de Equilíbrio (Acordo)</span>
          <span class="mock-value mock-highlight">R$ 21.450</span>
        </div>
      </div>
    </div>
  </section>

  <!-- Features -->
  <section class="section section-dark">
    <div class="container">
      <h2 class="section-title">Vantagem Competitiva Baseada em Dados</h2>
      <p class="section-subtitle">Desenvolvido para atender aos mais rigorosos padrões de escritórios e departamentos jurídicos de grande porte.</p>
      
      <div class="grid-3">
        <div class="feature-card">
          <svg class="feature-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="square" stroke-linejoin="miter" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path>
          </svg>
          <h3>Análise de Big Data</h3>
          <p>Motor de scoring alimentado por milhares de decisões reais, oferecendo previsibilidade estatística sobre a jurisprudência atual do TJSP e TRT2.</p>
        </div>
        <div class="feature-card">
          <svg class="feature-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="square" stroke-linejoin="miter" stroke-width="1.5" d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
          </svg>
          <h3>White-Label Integrado</h3>
          <p>Relatórios gerados automaticamente em PDF, ostentando a identidade visual, nome e credenciais (OAB) do seu próprio escritório ou empresa.</p>
        </div>
        <div class="feature-card">
          <svg class="feature-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="square" stroke-linejoin="miter" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path>
          </svg>
          <h3>Governança e Compliance</h3>
          <p>Fundamente aprovações de acordos e provisões contábeis com documentação estatística sólida, mitigando riscos de auditoria interna.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Pricing -->
  <section id="planos" class="section section-light">
    <div class="container">
      <h2 class="section-title">Investimento Estratégico</h2>
      <p class="section-subtitle">Soluções escaláveis desenhadas para estruturas jurídicas complexas.</p>

      <div class="pricing-grid">
        <!-- Boutique -->
        <div class="pricing-card">
          <h3>Boutique</h3>
          <div class="price">R$ 890<span>/mês</span></div>
          <ul class="pricing-features">
            <li>Até 50 laudos mensais</li>
            <li>Acesso completo à base TJSP/TRT2</li>
            <li>Exportação em PDF White-label</li>
            <li>Suporte por e-mail</li>
          </ul>
          <a href="https://wa.me/5511999999999?text=Tenho%20interesse%20no%20plano%20Boutique" class="btn-pricing">Assinar Boutique</a>
        </div>

        <!-- Corporate -->
        <div class="pricing-card popular">
          <h3>Corporate</h3>
          <div class="price">R$ 2.450<span>/mês</span></div>
          <ul class="pricing-features">
            <li>Laudos Ilimitados</li>
            <li>Até 10 usuários simultâneos</li>
            <li>Histórico e Banco de Dados na Nuvem</li>
            <li>Suporte prioritário via WhatsApp</li>
            <li>Onboarding dedicado</li>
          </ul>
          <a href="https://wa.me/5511999999999?text=Tenho%20interesse%20no%20plano%20Corporate" class="btn-pricing">Agendar Demonstração</a>
        </div>

        <!-- Enterprise -->
        <div class="pricing-card">
          <h3>Enterprise</h3>
          <div class="price">Sob Consulta</div>
          <ul class="pricing-features">
            <li>Volume Ilimitado / Usuários Ilimitados</li>
            <li>Integração API com ERP/Software Jurídico</li>
            <li>Bases de dados de outros Tribunais (sob demanda)</li>
            <li>SLA de 99.9% e Gerente de Sucesso</li>
          </ul>
          <a href="https://wa.me/5511999999999?text=Tenho%20interesse%20no%20plano%20Enterprise" class="btn-pricing">Fale com Vendas</a>
        </div>
      </div>
    </div>
  </section>

  <!-- CTA -->
  <section class="cta-section">
    <div class="container">
      <h2>Eleve o padrão de inteligência do seu escritório.</h2>
      <p>Agende uma reunião estratégica para entender o impacto do Nexus na sua carteira processual.</p>
      <a href="https://wa.me/5511999999999?text=Gostaria%20de%20agendar%20uma%20demonstra%C3%A7%C3%A3o%20do%20Nexus" class="btn-primary" style="background-color: var(--white); color: var(--primary); border: none;">Agendar Call Executiva</a>
    </div>
  </section>

  <!-- Footer -->
  <footer>
    <p><strong>Nexus — Jurimetria & Risco Estratégico</strong></p>
    <p>Desenvolvido sob coordenação de Dr. Gabriel Roberto | OAB/SP 351.245</p>
    <p style="margin-top: 16px; font-size: 12px; color: #6B7280;">© 2026 Nexus. Todos os direitos reservados.</p>
  </footer>

</body>
</html>
"""

# ─────────────────────────────────────────────
# ROTAS
# ─────────────────────────────────────────────
@app.route("/", methods=["GET"])
def landing():
    return LANDING_HTML

@app.route("/app", methods=["GET"])
def formulario():
    if not session.get("logado"):
        return redirect(url_for("login"))
    return render_template_string(FORM_HTML,
        adv=ESCRITORIO["advogado"], oab=ESCRITORIO["oab"], erro=None)

@app.route("/gerar", methods=["POST"])
def gerar():
    try:
        f = request.form
        caso = {
            "cliente":    f.get("cliente", "").strip(),
            "reu":        f.get("reu", "").strip(),
            "tipo_reu":   f.get("tipo_reu", "banco"),
            "tipo_acao":  f.get("tipo_acao", "dano_moral_banco"),
            "vara":       f.get("vara", "JEC_GERAL"),
            "valor_causa": f.get("valor_causa", 0),
            "descricao":  f.get("descricao", "").strip(),
            "ponto_forte": f.get("ponto_forte", "").strip(),
            "ponto_fraco": f.get("ponto_fraco", "").strip(),
            "prova_documental_forte":               bool(f.get("prova_documental_forte")),
            "caso_recente_jurisprudencia_favoravel": bool(f.get("caso_recente_jurisprudencia_favoravel")),
            "advogado_especialista_area":            bool(f.get("advogado_especialista_area")),
            "ausencia_testemunhas":                  bool(f.get("ausencia_testemunhas")),
            "caso_repetitivo_mass_litigation":       bool(f.get("caso_repetitivo_mass_litigation")),
            "valor_causa_baixo": float(f.get("valor_causa") or 0) < 20000,
        }

        # --- INTEGRAÇÃO COM IA (GEMINI) ---
        if caso["descricao"] and (not caso["ponto_forte"] or not caso["ponto_fraco"]):
            try:
                from google import genai
                client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY", ""))
                prompt = (f"Analise o caso juridico brasileiro: Tipo de acao: {caso['tipo_acao'].replace('_',' ')} contra {caso['reu']}. "
                          f"Relato do cliente: {caso['descricao']}\n\n"
                          "Aja como um advogado senior brasileiro analisando a jurisprudencia do TJSP. "
                          "Identifique 1 principal ponto forte da nossa tese (maximo 2 frases) e 1 principal ponto de atencao/risco deste caso (maximo 2 frases). "
                          "Seja direto e objetivo, sem juridiques. "
                          'Responda APENAS em JSON puro assim: {"ponto_forte": "...", "ponto_fraco": "..."}')
                response = client.models.generate_content(
                    model="gemini-3.6-flash",
                    contents=prompt
                )
                texto_resp = response.text.strip()
                texto_resp = re.sub(r'^```json\s*', '', texto_resp)
                texto_resp = re.sub(r'\s*```$', '', texto_resp)
                ia_data = json.loads(texto_resp)
                if not caso["ponto_forte"]: caso["ponto_forte"] = ia_data.get("ponto_forte", "")
                if not caso["ponto_fraco"]: caso["ponto_fraco"] = ia_data.get("ponto_fraco", "")
                print(f"  [IA Gemini OK: forte={caso['ponto_forte'][:40]}...]")
            except Exception as e:
                print(f"  [IA Gemini - erro: {e}]")
        # -------------------------

        score = calcular_score(caso)

        # Busca jurisprudência real
        caso["_jurisprudencia"] = buscar_jurisprudencia(caso["tipo_acao"])

        # Calcula honorários
        caso["_honorarios"] = calcular_honorarios(
            valor_causa=float(caso.get("valor_causa") or 0),
            prob_exito=score["prob"],
            faixa_min=score["faixa_min"],
            faixa_max=score["faixa_max"],
            tempo_meses=score["tempo_sent"],
            vara=caso["vara"]
        )

        pdf   = gerar_pdf(caso, score)
        nome  = f"Laudo_{caso['cliente'].replace(' ','_')}_{datetime.now().strftime('%d%m%Y')}.pdf"
        
        # Salva no histórico com token único
        import uuid
        token = str(uuid.uuid4())[:8]
        conn = get_db()
        conn.execute('''INSERT INTO laudos (data_hora, cliente, reu, tipo_acao, vara, prob_exito, faixa_min, faixa_max, ponto_acordo, token, tempo_meses, tempo_total, taxa_recurso) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), caso['cliente'], caso['reu'], caso['tipo_acao'], caso['vara'], score['prob'], score['faixa_min'], score['faixa_max'], score['ponto_acordo'], token, score['tempo_sent'], score['tempo_total'], score['taxa_recurso']))
        conn.commit()
        conn.close()

        # Salva token na sessão para redirect
        session['ultimo_token'] = token

        return send_file(pdf, mimetype="application/pdf",
                         as_attachment=True, download_name=nome)
    except Exception as e:
        return render_template_string(FORM_HTML,
            adv=ESCRITORIO["advogado"], oab=ESCRITORIO["oab"], erro=str(e))

HISTORICO_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nexus - Histórico</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#1a1a2e;font-size:14px}
  .header{background:linear-gradient(135deg,#1a1a2e,#0f3460);color:#fff;padding:20px 32px;display:flex;align-items:center;gap:16px}
  .header h1{font-size:24px;font-weight:800;letter-spacing:-1px}
  .header h1 span{color:#e94560}
  .header p{font-size:12px;opacity:.7;margin-top:2px}
  .header a{color:#fff;text-decoration:none;font-weight:600;font-size:14px;margin-left:20px;padding:8px 12px;background:rgba(255,255,255,0.1);border-radius:6px;}
  .header a:hover{background:rgba(255,255,255,0.2);}
  .adv-badge{background:rgba(255,255,255,.1);border:1px solid rgba(255,255,255,.2);border-radius:8px;padding:8px 14px;font-size:12px;text-align:right;margin-left:auto}
  .adv-badge strong{display:block;font-size:13px}
  .container{max-width:1000px;margin:28px auto;padding:0 16px}
  .card{background:#fff;border-radius:14px;box-shadow:0 2px 12px rgba(0,0,0,.08);overflow:hidden;margin-bottom:20px}
  .card-header{background:#1a1a2e;color:#fff;padding:14px 20px;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
  .card-body{padding:20px;overflow-x:auto;}
  table{width:100%;border-collapse:collapse;text-align:left;}
  th,td{padding:12px 15px;border-bottom:1px solid #eee;}
  th{background:#f8f9fa;font-weight:600;color:#555;font-size:12px;text-transform:uppercase;letter-spacing:0.5px;}
  td{font-size:13px;}
  .prob{font-weight:bold;color:#166534;}
  .empty{text-align:center;padding:40px;color:#777;font-style:italic;}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>Nex<span>us</span></h1>
    <p>Sistema de Laudo de Risco Processual</p>
  </div>
  <a href="/">← Voltar</a>
  <div class="adv-badge">
    <strong>{{ adv }}</strong>{{ oab }}
  </div>
</div>

<div class="container">
  <div class="card">
    <div class="card-header">Histórico de Laudos Gerados</div>
    <div class="card-body">
      {% if laudos %}
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Data</th>
            <th>Cliente</th>
            <th>Réu</th>
            <th>Tipo de Ação</th>
            <th>Probabilidade</th>
            <th>Faixa de Valor</th>
            <th>Ponto de Acordo</th>
            <th>Simulador</th>
          </tr>
        </thead>
        <tbody>
          {% for l in laudos %}
          <tr>
            <td>{{ l.id }}</td>
            <td>{{ l.data_hora }}</td>
            <td>{{ l.cliente }}</td>
            <td>{{ l.reu }}</td>
            <td>{{ l.tipo_acao }}</td>
            <td class="prob">{{ "%.0f"|format(l.prob_exito * 100) }}%</td>
            <td>R$ {{ l.faixa_min }} - R$ {{ l.faixa_max }}</td>
            <td>R$ {{ l.ponto_acordo }}</td>
            <td>{% if l.token %}<a href="/simulador/{{ l.token }}" target="_blank" style="color:#C5A880;font-weight:600;">Abrir</a>{% else %}-{% endif %}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      {% else %}
      <div class="empty">Nenhum laudo gerado ainda.</div>
      {% endif %}
    </div>
  </div>
</div>
</body>
</html>"""

@app.route("/historico", methods=["GET"])
def historico():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM laudos ORDER BY data_hora DESC")
    laudos = cur.fetchall()
    conn.close()
    return render_template_string(HISTORICO_HTML, adv=ESCRITORIO["advogado"], oab=ESCRITORIO["oab"], laudos=laudos)

# ─────────────────────────────────────────────
# LOGIN E PAINEL
# ─────────────────────────────────────────────
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "").strip()
        if verificar_login(email, senha):
            session["logado"] = True
            session["nome"] = ADMIN_USER["nome"]
            return redirect(url_for("formulario"))
        return render_template_string(LOGIN_HTML, erro="Email ou senha incorretos.")
    return render_template_string(LOGIN_HTML, erro=None)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/painel")
def painel():
    if not session.get("logado"):
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM laudos ORDER BY data_hora DESC")
    laudos = cur.fetchall()
    conn.close()
    metricas = calcular_metricas(laudos)
    return render_template_string(PAINEL_HTML,
        adv=ESCRITORIO["advogado"], oab=ESCRITORIO["oab"],
        laudos=laudos, **metricas)

@app.route("/exportar-csv")
def exportar_csv():
    if not session.get("logado"):
        return redirect(url_for("login"))
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM laudos ORDER BY data_hora DESC")
    laudos = cur.fetchall()
    conn.close()
    csv_data = gerar_csv(laudos)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=laudos_nexus.csv"}
    )

# ─────────────────────────────────────────────
# SIMULADOR DE ACORDO (link por token)
# ─────────────────────────────────────────────
@app.route("/simulador")
@app.route("/simulador/<token>")
def simulador(token=None):
    if not token:
        token = session.get("ultimo_token")
    if not token:
        return redirect(url_for("index"))
    conn = get_db()
    row = conn.execute("SELECT * FROM laudos WHERE token = ?", (token,)).fetchone()
    conn.close()
    if not row:
        return redirect(url_for("index"))
    dados = {
        'cliente': row['cliente'],
        'reu': row['reu'],
        'tipo_acao': row['tipo_acao'],
        'prob_exito': row['prob_exito'],
        'faixa_min': row['faixa_min'],
        'faixa_max': row['faixa_max'],
        'ponto_acordo': row['ponto_acordo'],
        'tempo_meses': row['tempo_meses'] or 12,
        'tempo_total_anos': row['tempo_total'] or 2.0,
        'taxa_recurso': row['taxa_recurso'] or 0.6,
    }
    return gerar_simulador_html(dados)

# ─────────────────────────────────────────────
# INICIALIZACAO
# ─────────────────────────────────────────────
