LOGIN_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus - Login</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f4f9;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .login-container {
            background-color: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
        }
        .logo-container {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo-container h1 {
            color: #0A192F;
            margin: 0;
            font-size: 28px;
        }
        .logo-container h1 span {
            color: #C5A880;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
        }
        .form-group input {
            width: 100%;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
            box-sizing: border-box;
            font-size: 16px;
        }
        .form-group input:focus {
            outline: none;
            border-color: #C5A880;
        }
        .btn-login {
            width: 100%;
            padding: 12px;
            background-color: #0A192F;
            color: white;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
            transition: background-color 0.3s;
        }
        .btn-login:hover {
            background-color: #1a2a42;
        }
        .error-message {
            color: #d9534f;
            background-color: #f9f2f2;
            border-left: 4px solid #d9534f;
            padding: 10px;
            margin-bottom: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>

<div class="login-container">
    <div class="logo-container">
        <h1>Nex<span>us</span></h1>
    </div>
    
    {% if erro %}
    <div class="error-message">
        {{ erro }}
    </div>
    {% endif %}

    <form method="POST" action="/login">
        <div class="form-group">
            <label for="email">E-mail</label>
            <input type="email" id="email" name="email" required>
        </div>
        <div class="form-group">
            <label for="senha">Senha</label>
            <input type="password" id="senha" name="senha" required>
        </div>
        <button type="submit" class="btn-login">Entrar</button>
    </form>
    <div style="text-align:center;margin-top:16px;">
        <a href="/" style="color:#C5A880;text-decoration:none;font-size:14px;font-weight:600;">Voltar para a pagina inicial</a>
    </div>
</div>

</body>
</html>
"""

PAINEL_HTML = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus - Painel do Advogado</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f4f9;
            margin: 0;
            color: #333;
        }
        .header {
            background-color: #0A192F;
            color: white;
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header .logo h2 {
            margin: 0;
        }
        .header .logo h2 span {
            color: #C5A880;
        }
        .header .user-info {
            display: flex;
            align-items: center;
            gap: 20px;
        }
        .btn-logout {
            color: white;
            text-decoration: none;
            border: 1px solid #C5A880;
            padding: 8px 15px;
            border-radius: 4px;
            transition: all 0.3s;
        }
        .btn-logout:hover {
            background-color: #C5A880;
            color: #0A192F;
        }
        .container {
            padding: 30px;
            max-width: 1200px;
            margin: 0 auto;
        }
        .summary-cards {
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
            flex-wrap: wrap;
        }
        .card {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            flex: 1;
            min-width: 250px;
            border-top: 4px solid #C5A880;
        }
        .card h3 {
            margin: 0 0 10px 0;
            font-size: 14px;
            color: #666;
            text-transform: uppercase;
        }
        .card .value {
            font-size: 28px;
            font-weight: bold;
            color: #0A192F;
        }
        .actions {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .btn {
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 4px;
            font-weight: bold;
            display: inline-block;
        }
        .btn-primary {
            background-color: #C5A880;
            color: #0A192F;
        }
        .btn-primary:hover {
            background-color: #b09570;
        }
        .btn-secondary {
            background-color: #0A192F;
            color: white;
        }
        .btn-secondary:hover {
            background-color: #1a2a42;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }
        th, td {
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background-color: #f9f9f9;
            font-weight: 600;
            color: #0A192F;
        }
        tr:last-child td {
            border-bottom: none;
        }
        tr:hover {
            background-color: #fcfcfc;
        }
        .empty-message {
            text-align: center;
            padding: 40px;
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            color: #666;
        }
    </style>
</head>
<body>

<div class="header">
    <div class="logo">
        <h2>Nex<span>us</span></h2>
    </div>
    <div class="user-info">
        <a href="/app" style="background:#C5A880;color:#0A192F;padding:8px 18px;border-radius:4px;text-decoration:none;font-weight:700;font-size:14px;">Novo Laudo</a>
        <a href="/logout" class="btn-logout">Sair</a>
    </div>
</div>

<div class="container">
    <div class="summary-cards">
        <div class="card">
            <h3>Total de Laudos Gerados</h3>
            <div class="value">{{ total_laudos }}</div>
        </div>
        <div class="card">
            <h3>Taxa Média de Êxito</h3>
            <div class="value">{{ taxa_media }}%</div>
        </div>
        <div class="card">
            <h3>Valor Total em Risco</h3>
            <div class="value">R$ {{ valor_total }}</div>
        </div>
    </div>

    <div class="actions">
        <h2>Histórico de Laudos</h2>
        <div>
            <a href="/exportar_csv" class="btn btn-secondary">Exportar CSV</a>
            <a href="/" class="btn btn-primary">Novo Laudo</a>
        </div>
    </div>

    {% if laudos %}
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Data</th>
                <th>Cliente</th>
                <th>Réu</th>
                <th>Tipo</th>
                <th>Probabilidade</th>
                <th>Faixa (R$)</th>
                <th>Acordo (R$)</th>
            </tr>
        </thead>
        <tbody>
            {% for l in laudos %}
            <tr>
                <td>{{ loop.index }}</td>
                <td>{{ l.data_hora }}</td>
                <td>{{ l.cliente }}</td>
                <td>{{ l.reu }}</td>
                <td>{{ l.tipo_acao }}</td>
                <td>{{ l.probabilidade }}</td>
                <td>{{ l.faixa_valor }}</td>
                <td>{{ l.valor_acordo }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    {% else %}
    <div class="empty-message">
        <h3>Nenhum laudo encontrado</h3>
        <p>Gere o seu primeiro laudo para visualizar o histórico e as métricas.</p>
    </div>
    {% endif %}
</div>

</body>
</html>
"""

import csv
import io

# Credenciais hardcoded (depois migra para banco)
ADMIN_USER = {
    'email': 'gabriielroberto10@gmail.com',
    'senha': '151124',
    'nome': 'Dr. Gabriel Roberto'
}

def verificar_login(email, senha) -> bool:
    '''Verifica credenciais'''
    return email == ADMIN_USER['email'] and senha == ADMIN_USER['senha']

def calcular_metricas(laudos_rows) -> dict:
    '''Recebe lista de rows do SQLite e retorna dict com:
    - total_laudos: int
    - taxa_media: float (media das prob_exito * 100, arredondado)
    - valor_total: int (soma de todos faixa_max)
    '''
    total_laudos = len(laudos_rows)
    if total_laudos == 0:
        return {
            'total_laudos': 0,
            'taxa_media': 0.0,
            'valor_total': 0
        }
    
    soma_prob = 0.0
    soma_valor = 0
    
    for row in laudos_rows:
        try:
            prob = float(row.get('prob_exito', 0.0) if isinstance(row, dict) else row['prob_exito'])
            soma_prob += prob
        except:
            pass
            
        try:
            faixa_max = int(row.get('faixa_max', 0) if isinstance(row, dict) else row['faixa_max'])
            soma_valor += faixa_max
        except:
            pass
            
    taxa_media = round((soma_prob / total_laudos) * 100, 2)
    
    return {
        'total_laudos': total_laudos,
        'taxa_media': taxa_media,
        'valor_total': soma_valor
    }

def gerar_csv(laudos_rows) -> str:
    '''Gera string CSV com header e dados dos laudos'''
    output = io.StringIO()
    writer = csv.writer(output)
    
    if not laudos_rows:
        return ""
        
    if isinstance(laudos_rows[0], dict):
        headers = laudos_rows[0].keys()
    else:
        headers = laudos_rows[0].keys()
        
    writer.writerow(headers)
    
    for row in laudos_rows:
        if isinstance(row, dict):
            writer.writerow(row.values())
        else:
            writer.writerow([row[col] for col in headers])
            
    return output.getvalue()
