# Perguntas de negócio: chamados de manutenção de rede

Você é analista de dados de um provedor de internet por fibra óptica na região de São Roque. A gerência de operações quer entender **onde, quando e por que a rede falha**, e se o **SLA** (prazo máximo de atendimento) está sendo cumprido.

As perguntas abaixo estão em ordem crescente de dificuldade, e cada uma usa um conceito novo de SQL. As respostas estão no arquivo [`consultas.sql`](consultas.sql), identificadas pelo número da pergunta, e as conclusões no [README](README.md).

---

## A base de dados

O banco `chamados_rede.db` tem 4 tabelas:

| Tabela | O que guarda | Colunas principais |
|---|---|---|
| `chamados` | 6.000 chamados de manutenção (jan/2025 a set/2026) | `id_chamado`, `abertura`, `inicio_atendimento`, `encerramento`, `id_cliente`, `id_pop`, `id_tecnico`, `tipo_falha`, `causa_raiz`, `prioridade`, `sla_horas`, `distancia_falha_km`, `perda_db`, `status` |
| `pops` | 16 pontos de presença da rede | `id_pop`, `nome_pop`, `cidade`, `regiao`, `ano_instalacao` |
| `tecnicos` | 18 técnicos de campo | `id_tecnico`, `nome`, `nivel`, `equipe`, `data_admissao` |
| `clientes` | 400 clientes | `id_cliente`, `nome_cliente`, `segmento`, `plano`, `cidade`, `valor_mensal` |

As datas estão no formato `AAAA-MM-DD HH:MM:SS`. No SQLite, use `strftime()` para extrair partes da data e `julianday()` para calcular diferenças de tempo.

> A base é **fictícia**, gerada pelo script `gerar_base.py` para fins de estudo, inspirada em situações reais de manutenção de redes.

---

## Nível 1: consultas básicas (`SELECT`, `WHERE`, `ORDER BY`, `LIMIT`)

**1.** Mostre os 10 chamados mais recentes, com `id_chamado`, `abertura`, `tipo_falha` e `prioridade`.

**2.** Liste todos os chamados de prioridade `Crítica` que foram `Cancelado`.

**3.** Quais rompimentos de fibra tiveram a falha a mais de 10 km de distância (`distancia_falha_km`)? Ordene do mais distante para o mais próximo.

---

## Nível 2: agregações (`COUNT`, `AVG`, `GROUP BY`, `HAVING`)

**4.** Quantos chamados existem de cada `tipo_falha`? Ordene do mais frequente para o menos frequente.
> 💡 Observe o resultado com atenção: há um problema de qualidade nos dados. Qual é, e como corrigir na consulta? (Dica: `UPPER()` ou `LOWER()`.)

**5.** Quantos chamados ficaram sem `causa_raiz` preenchida, entre os que foram `Encerrado`?

**6.** Qual é o tempo médio de reparo, em horas, de cada tipo de falha? Considere só chamados encerrados.
> 💡 Tempo de reparo = `(julianday(encerramento) - julianday(inicio_atendimento)) * 24`

**7.** Quais clientes abriram mais de 30 chamados? Mostre o `id_cliente` e a quantidade.

---

## Nível 3: junção de tabelas (`JOIN`)

**8.** Quantos chamados de **falha de equipamento** cada POP teve? Mostre o `nome_pop`, a `cidade` e o `ano_instalacao`. Algum POP se destaca? O que isso pode indicar?

**9.** Em qual **região** e em qual **turno** acontecem mais furtos e vandalismo de cabo? Considere noite das 22h às 5h.
> 💡 `CASE WHEN ... THEN 'Noite' ELSE 'Dia' END`

**10.** Qual é o tempo médio de reparo de **rompimentos de fibra** por `nivel` do técnico (Júnior, Pleno, Sênior)?

---

## Nível 4: análises de negócio (`CASE`, subconsultas, CTE)

**11.** Qual é o **percentual de cumprimento do SLA** por prioridade? Um chamado cumpriu o SLA se o tempo total (da abertura ao encerramento) foi menor ou igual a `sla_horas`.
> 💡 Calcule em uma CTE (`WITH ... AS`) o tempo total de cada chamado e depois agrupe.

**12.** Compare o cumprimento do SLA entre clientes **Empresariais** e **Residenciais**. Qual é o resultado, e por que ele preocupa, considerando o `valor_mensal` de cada segmento?

**13.** Os rompimentos de fibra aumentam na **época de chuvas** (dezembro a março)? Compare a média de rompimentos por mês nas duas épocas.

---

## Nível 5: funções de janela (`OVER`, `RANK`, `LAG`)

**14.** Monte um ranking dos técnicos de cada equipe pela quantidade de chamados encerrados, usando `RANK() OVER (PARTITION BY equipe ...)`.

**15.** Mostre a quantidade de chamados por mês e a **variação em relação ao mês anterior**, usando `LAG()`.

**16.** Desafio final: encontre os **chamados reincidentes**, ou seja, quando o mesmo cliente abriu um novo chamado em até 7 dias depois do anterior. Quantos são, e quais tipos de falha mais se repetem?
