"""
Gera a base fictícia de chamados de manutenção de uma rede de fibra óptica.

A base é FICTÍCIA, criada para estudo de SQL e Power BI, inspirada em
situações reais do dia a dia de manutenção de redes. Nomes de técnicos
e clientes são inventados.

Saídas:
  chamados_rede.db   -> banco SQLite com 4 tabelas
  csv/*.csv          -> as mesmas tabelas em CSV (para o Power BI)

Uso:  python gerar_base.py
"""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEMENTE = 2026
rng = np.random.default_rng(SEMENTE)

INICIO = datetime(2025, 1, 1)
FIM = datetime(2026, 9, 30, 23, 59)
N_CHAMADOS = 6000

# ---------------------------------------------------------------------------
# POPs (pontos de presença)
# ---------------------------------------------------------------------------
SIGLAS = {"São Roque": "SRQ", "Mairinque": "MRQ", "Alumínio": "ALU", "Ibiúna": "IBI", "Sorocaba": "SOR",
          "Votorantim": "VOT", "Itu": "ITU", "Araçariguama": "ARA", "Cotia": "COT", "Vargem Grande Paulista": "VGP"}
cidades = {
    "São Roque": "Oeste", "Mairinque": "Oeste", "Alumínio": "Oeste", "Ibiúna": "Oeste",
    "Sorocaba": "Sorocaba", "Votorantim": "Sorocaba",
    "Itu": "Norte", "Araçariguama": "Norte",
    "Cotia": "Leste", "Vargem Grande Paulista": "Leste",
}
pops = []
for cidade, regiao in cidades.items():
    qtd = 3 if cidade == "Sorocaba" else (2 if cidade in ("São Roque", "Mairinque", "Itu", "Cotia") else 1)
    for i in range(1, qtd + 1):
        sigla = SIGLAS[cidade]
        pops.append({
            "id_pop": len(pops) + 1,
            "nome_pop": f"POP-{sigla}-{i:02d}",
            "cidade": cidade,
            "regiao": regiao,
            "ano_instalacao": int(rng.integers(2012, 2024)),
        })
pops = pd.DataFrame(pops)
# Um POP antigo, com equipamento perto do fim da vida útil (padrão a descobrir)
POP_ANTIGO = int(pops.loc[pops["nome_pop"] == "POP-MRQ-02", "id_pop"].iloc[0])
pops.loc[pops["id_pop"] == POP_ANTIGO, "ano_instalacao"] = 2009

# ---------------------------------------------------------------------------
# Técnicos (nomes fictícios)
# ---------------------------------------------------------------------------
nomes = ["Rafael Lima", "Juliana Prado", "Marcos Teixeira", "Patrícia Nunes", "Diego Fernandes",
         "Camila Rocha", "André Moura", "Fernanda Alves", "Thiago Barros", "Larissa Campos",
         "Bruno Siqueira", "Renata Duarte", "Felipe Antunes", "Vanessa Lopes", "Gustavo Ribeiro",
         "Aline Martins", "Leandro Castro", "Priscila Gomes"]
niveis = ["Júnior"] * 7 + ["Pleno"] * 7 + ["Sênior"] * 4
rng.shuffle(niveis)
equipes = ["Equipe Oeste", "Equipe Sorocaba", "Equipe Norte/Leste"]
tecnicos = pd.DataFrame({
    "id_tecnico": range(1, len(nomes) + 1),
    "nome": nomes,
    "nivel": niveis,
    "equipe": [equipes[i % 3] for i in range(len(nomes))],
    "data_admissao": [(datetime(2016, 1, 1) + timedelta(days=int(d))).date().isoformat()
                      for d in rng.integers(0, 3300, len(nomes))],
})
regiao_equipe = {"Oeste": "Equipe Oeste", "Sorocaba": "Equipe Sorocaba", "Norte": "Equipe Norte/Leste", "Leste": "Equipe Norte/Leste"}

# ---------------------------------------------------------------------------
# Clientes (nomes fictícios)
# ---------------------------------------------------------------------------
prefixos = ["Alfa", "Beta", "Nova", "Prime", "Vale", "Serra", "Rio", "Sol", "Max", "Mega", "Delta", "Orion"]
sufixos = ["Logística", "Metalúrgica", "Hospital", "Supermercados", "Escola", "Contabilidade", "Indústria", "Clínica", "Transportes", "Tecnologia"]
clientes = []
for i in range(1, 401):
    b2b = i <= 120
    cidade = rng.choice(list(cidades))
    clientes.append({
        "id_cliente": i,
        "nome_cliente": f"{rng.choice(prefixos)} {rng.choice(sufixos)} {i:03d}" if b2b else f"Condomínio/Residencial {i:03d}",
        "segmento": "Empresarial" if b2b else "Residencial",
        "plano": rng.choice(["Dedicado 1 Gbps", "Dedicado 500 Mbps", "Dedicado 200 Mbps"]) if b2b
                 else rng.choice(["Fibra 1 Gbps", "Fibra 600 Mbps", "Fibra 300 Mbps"], p=[.2, .5, .3]),
        "cidade": cidade,
        "valor_mensal": float(rng.choice([2490, 1590, 890])) if b2b else float(rng.choice([149.9, 119.9, 99.9])),
    })
clientes = pd.DataFrame(clientes)

# ---------------------------------------------------------------------------
# Chamados
# ---------------------------------------------------------------------------
TIPOS = {
    # tipo: (peso base, horas médias de reparo, é falha de fibra?)
    "Rompimento de fibra": (0.26, 4.0, True),
    "Atenuação alta": (0.22, 3.0, True),
    "Falha de equipamento": (0.20, 2.5, False),
    "Queda de energia": (0.17, 1.5, False),
    "Furto/vandalismo de cabo": (0.07, 5.0, True),
    "Configuração": (0.08, 1.0, False),
}
CAUSAS = {
    "Rompimento de fibra": ["Obra de terceiros", "Queda de árvore", "Acidente de trânsito (poste)", "Roedores"],
    "Atenuação alta": ["Conector sujo", "Curvatura excessiva", "Emenda degradada", "Umidade na caixa de emenda"],
    "Falha de equipamento": ["Módulo óptico (SFP/QSFP)", "Placa de interface", "Switch", "Fonte de alimentação"],
    "Queda de energia": ["Falta de energia da concessionária", "Bateria do nobreak", "Disjuntor"],
    "Furto/vandalismo de cabo": ["Furto de cabo", "Vandalismo"],
    "Configuração": ["Erro de configuração", "Atualização de firmware"],
}
SLA = {"Crítica": 4, "Alta": 8, "Média": 24, "Baixa": 48}

total_seg = int((FIM - INICIO).total_seconds())
linhas = []
while len(linhas) < N_CHAMADOS:
    abertura = INICIO + timedelta(seconds=int(rng.integers(0, total_seg)))
    mes = abertura.month
    chuva = mes in (12, 1, 2, 3)
    noite = abertura.hour >= 22 or abertura.hour < 5
    fim_semana = abertura.weekday() >= 5

    pop = pops.sample(1, random_state=int(rng.integers(1e9))).iloc[0]
    pesos = {t: v[0] for t, v in TIPOS.items()}
    if chuva:
        pesos["Rompimento de fibra"] *= 1.9
        pesos["Queda de energia"] *= 1.6
    if pop["id_pop"] == POP_ANTIGO:
        pesos["Falha de equipamento"] *= 4
    if pop["regiao"] == "Sorocaba" and noite:
        pesos["Furto/vandalismo de cabo"] *= 6
    tipos, p = zip(*pesos.items())
    p = np.array(p) / sum(p)
    tipo = rng.choice(tipos, p=p)

    # Mais chamados de equipamento no POP antigo: aceita sempre; outros POPs aceitam com probabilidade menor
    if pop["id_pop"] != POP_ANTIGO and tipo == "Falha de equipamento" and rng.random() < 0.15:
        continue

    cidade_clientes = clientes[clientes["cidade"] == pop["cidade"]]
    cliente = (cidade_clientes if len(cidade_clientes) else clientes).sample(1, random_state=int(rng.integers(1e9))).iloc[0]
    empresarial = cliente["segmento"] == "Empresarial"

    if tipo in ("Rompimento de fibra", "Furto/vandalismo de cabo"):
        prioridade = "Crítica" if empresarial or rng.random() < 0.5 else "Alta"
    elif empresarial:
        prioridade = rng.choice(["Crítica", "Alta", "Média"], p=[.3, .5, .2])
    else:
        prioridade = rng.choice(["Alta", "Média", "Baixa"], p=[.2, .55, .25])

    equipe = regiao_equipe[pop["regiao"]]
    candidatos = tecnicos[tecnicos["equipe"] == equipe]
    tecnico = candidatos.sample(1, random_state=int(rng.integers(1e9))).iloc[0]

    # Tempo até iniciar o atendimento (horas)
    espera = rng.gamma(2, {"Crítica": 0.35, "Alta": 0.8, "Média": 3, "Baixa": 7}[prioridade])
    if noite or fim_semana:
        espera *= 1.6
    # Tempo de reparo (horas)
    reparo = rng.gamma(3, TIPOS[tipo][1] / 3)
    if tecnico["nivel"] == "Júnior" and tipo in ("Rompimento de fibra", "Atenuação alta"):
        reparo *= 1.35
    if tecnico["nivel"] == "Sênior":
        reparo *= 0.85
    if chuva and tipo == "Rompimento de fibra":
        reparo *= 1.2

    inicio = abertura + timedelta(hours=float(espera))
    encerramento = inicio + timedelta(hours=float(reparo))

    sorteio = rng.random()
    status = "Cancelado" if sorteio < 0.03 else "Encerrado"
    if encerramento > FIM:
        status = "Em aberto"

    fibra = TIPOS[tipo][2]
    linhas.append({
        "abertura": abertura,
        "inicio_atendimento": inicio if status != "Cancelado" else None,
        "encerramento": encerramento if status == "Encerrado" else None,
        "id_cliente": int(cliente["id_cliente"]),
        "id_pop": int(pop["id_pop"]),
        "id_tecnico": int(tecnico["id_tecnico"]) if status != "Cancelado" else None,
        "tipo_falha": tipo,
        "causa_raiz": rng.choice(CAUSAS[tipo]) if status == "Encerrado" else None,
        "prioridade": prioridade,
        "sla_horas": SLA[prioridade],
        "distancia_falha_km": round(float(rng.gamma(2, 2.2)), 2) if fibra else None,
        "perda_db": round(float(rng.uniform(1.5, 9.0) if tipo == "Atenuação alta" else rng.uniform(18, 40)), 1) if fibra else None,
        "status": status,
    })

chamados = pd.DataFrame(linhas).sort_values("abertura").reset_index(drop=True)
chamados.insert(0, "id_chamado", range(1, len(chamados) + 1))

# Alguns registros com problemas comuns de base real (para treinar limpeza)
idx = rng.choice(chamados.index, 25, replace=False)
chamados.loc[idx[:15], "causa_raiz"] = None   # causa não preenchida pelo técnico
chamados.loc[idx[15:], "tipo_falha"] = chamados.loc[idx[15:], "tipo_falha"].str.upper()  # digitação inconsistente

for col in ("abertura", "inicio_atendimento", "encerramento"):
    chamados[col] = pd.to_datetime(chamados[col]).dt.strftime("%Y-%m-%d %H:%M:%S")

# ---------------------------------------------------------------------------
# Gravação
# ---------------------------------------------------------------------------
Path("csv").mkdir(exist_ok=True)
banco = Path("chamados_rede.db")
banco.unlink(missing_ok=True)
with sqlite3.connect(banco) as con:
    con.executescript("""
    CREATE TABLE pops (
        id_pop INTEGER PRIMARY KEY, nome_pop TEXT, cidade TEXT, regiao TEXT, ano_instalacao INTEGER);
    CREATE TABLE tecnicos (
        id_tecnico INTEGER PRIMARY KEY, nome TEXT, nivel TEXT, equipe TEXT, data_admissao TEXT);
    CREATE TABLE clientes (
        id_cliente INTEGER PRIMARY KEY, nome_cliente TEXT, segmento TEXT, plano TEXT, cidade TEXT, valor_mensal REAL);
    CREATE TABLE chamados (
        id_chamado INTEGER PRIMARY KEY, abertura TEXT, inicio_atendimento TEXT, encerramento TEXT,
        id_cliente INTEGER REFERENCES clientes(id_cliente), id_pop INTEGER REFERENCES pops(id_pop),
        id_tecnico INTEGER REFERENCES tecnicos(id_tecnico), tipo_falha TEXT, causa_raiz TEXT,
        prioridade TEXT, sla_horas INTEGER, distancia_falha_km REAL, perda_db REAL, status TEXT);
    """)
    for nome, df in [("pops", pops), ("tecnicos", tecnicos), ("clientes", clientes), ("chamados", chamados)]:
        df.to_sql(nome, con, if_exists="append", index=False)
        df.to_csv(f"csv/{nome}.csv", index=False, encoding="utf-8-sig")
        print(f"{nome}: {len(df):,} linhas")

print("Base gerada: chamados_rede.db e pasta csv/")
