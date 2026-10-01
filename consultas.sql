-- =============================================================================
-- Projeto: Análise de chamados de manutenção de rede de fibra óptica com SQL
-- Autor:   Alessandro José dos Santos
-- Banco:   chamados_rede.db (SQLite)
--
-- Cada bloco responde a uma pergunta do arquivo perguntas.md.
-- Os comentários explicam o raciocínio de cada consulta.
-- =============================================================================


-- @P01 ------------------------------------------------------------------------
-- Pergunta 1: os 10 chamados mais recentes.
-- ORDER BY ... DESC ordena do maior para o menor (data mais nova primeiro)
-- e LIMIT corta o resultado nas 10 primeiras linhas.
SELECT id_chamado, abertura, tipo_falha, prioridade
FROM chamados
ORDER BY abertura DESC
LIMIT 10;


-- @P02 ------------------------------------------------------------------------
-- Pergunta 2: chamados críticos que foram cancelados.
-- WHERE com AND exige que as duas condições sejam verdadeiras.
SELECT id_chamado, abertura, tipo_falha, id_cliente
FROM chamados
WHERE prioridade = 'Crítica'
  AND status = 'Cancelado'
ORDER BY abertura;


-- @P03 ------------------------------------------------------------------------
-- Pergunta 3: rompimentos de fibra com falha a mais de 10 km (medida do OTDR).
SELECT id_chamado, abertura, id_pop, distancia_falha_km, perda_db
FROM chamados
WHERE tipo_falha = 'Rompimento de fibra'
  AND distancia_falha_km > 10
ORDER BY distancia_falha_km DESC;


-- @P04a -----------------------------------------------------------------------
-- Pergunta 4 (parte 1): quantidade de chamados por tipo de falha.
-- O resultado mostra um problema de qualidade: alguns tipos foram digitados
-- em MAIÚSCULAS ("ROMPIMENTO DE FIBRA"), e o GROUP BY os conta separado.
SELECT tipo_falha, COUNT(*) AS qtd
FROM chamados
GROUP BY tipo_falha
ORDER BY qtd DESC;


-- @P04b -----------------------------------------------------------------------
-- Pergunta 4 (parte 2): correção.
-- No SQLite, UPPER/LOWER não convertem letras acentuadas (Ç, Ã), então
-- padronizar com LOWER não resolveria "CONFIGURAÇÃO". A solução robusta é
-- classificar pelo início do texto com LIKE (que ignora maiúsculas/minúsculas
-- nas letras sem acento).
--
-- Em vez de repetir essa correção em toda consulta, criamos uma VIEW: uma
-- "tabela virtual" com os dados já limpos e com as colunas de tempo calculadas.
-- As próximas consultas usam a view vw_chamados.
DROP VIEW IF EXISTS vw_chamados;
CREATE VIEW vw_chamados AS
SELECT
    c.*,
    CASE
        WHEN c.tipo_falha LIKE 'rompimento%'   THEN 'Rompimento de fibra'
        WHEN c.tipo_falha LIKE 'atenua%'       THEN 'Atenuação alta'
        WHEN c.tipo_falha LIKE 'falha de equi%' THEN 'Falha de equipamento'
        WHEN c.tipo_falha LIKE 'queda%'        THEN 'Queda de energia'
        WHEN c.tipo_falha LIKE 'furto%'        THEN 'Furto/vandalismo de cabo'
        WHEN c.tipo_falha LIKE 'configura%'    THEN 'Configuração'
    END AS tipo,
    -- julianday() devolve a data em dias; a diferença * 24 dá horas
    (julianday(c.encerramento) - julianday(c.abertura)) * 24           AS horas_total,
    (julianday(c.encerramento) - julianday(c.inicio_atendimento)) * 24 AS horas_reparo
FROM chamados AS c;

SELECT tipo, COUNT(*) AS qtd
FROM vw_chamados
GROUP BY tipo
ORDER BY qtd DESC;


-- @P05 ------------------------------------------------------------------------
-- Pergunta 5: chamados encerrados sem causa raiz preenchida.
-- Valor ausente no SQL é NULL, e só pode ser testado com IS NULL (nunca "= NULL").
SELECT COUNT(*) AS encerrados_sem_causa
FROM chamados
WHERE status = 'Encerrado'
  AND causa_raiz IS NULL;


-- @P06 ------------------------------------------------------------------------
-- Pergunta 6: tempo médio de reparo, em horas, por tipo de falha.
SELECT tipo,
       COUNT(*)                    AS chamados,
       ROUND(AVG(horas_reparo), 1) AS media_horas_reparo
FROM vw_chamados
WHERE status = 'Encerrado'
GROUP BY tipo
ORDER BY media_horas_reparo DESC;


-- @P07 ------------------------------------------------------------------------
-- Pergunta 7: clientes com mais de 30 chamados.
-- HAVING filtra DEPOIS do agrupamento (WHERE filtra antes).
SELECT id_cliente, COUNT(*) AS qtd_chamados
FROM chamados
GROUP BY id_cliente
HAVING COUNT(*) > 30
ORDER BY qtd_chamados DESC;


-- @P08 ------------------------------------------------------------------------
-- Pergunta 8: falhas de equipamento por POP, com o ano de instalação.
-- JOIN liga cada chamado ao seu POP pela coluna em comum (id_pop).
SELECT p.nome_pop,
       p.cidade,
       p.ano_instalacao,
       COUNT(*) AS falhas_equipamento
FROM vw_chamados AS c
JOIN pops AS p ON p.id_pop = c.id_pop
WHERE c.tipo = 'Falha de equipamento'
GROUP BY p.nome_pop, p.cidade, p.ano_instalacao
ORDER BY falhas_equipamento DESC;


-- @P09 ------------------------------------------------------------------------
-- Pergunta 9: furtos e vandalismo por região e turno (noite = 22h às 5h).
-- strftime('%H', ...) extrai a hora; CAST converte o texto em número.
SELECT p.regiao,
       CASE
           WHEN CAST(strftime('%H', c.abertura) AS INTEGER) >= 22
             OR CAST(strftime('%H', c.abertura) AS INTEGER) < 5 THEN 'Noite'
           ELSE 'Dia'
       END AS turno,
       COUNT(*) AS furtos_vandalismo
FROM vw_chamados AS c
JOIN pops AS p ON p.id_pop = c.id_pop
WHERE c.tipo = 'Furto/vandalismo de cabo'
GROUP BY p.regiao, turno
ORDER BY furtos_vandalismo DESC;


-- @P10 ------------------------------------------------------------------------
-- Pergunta 10: tempo médio de reparo de rompimentos por nível do técnico.
SELECT t.nivel,
       COUNT(*)                      AS rompimentos,
       ROUND(AVG(c.horas_reparo), 1) AS media_horas_reparo
FROM vw_chamados AS c
JOIN tecnicos AS t ON t.id_tecnico = c.id_tecnico
WHERE c.tipo = 'Rompimento de fibra'
  AND c.status = 'Encerrado'
GROUP BY t.nivel
ORDER BY media_horas_reparo DESC;


-- @P11 ------------------------------------------------------------------------
-- Pergunta 11: percentual de cumprimento do SLA por prioridade.
-- A CTE (WITH) cria uma etapa intermediária com nome, deixando a consulta
-- final mais legível. Em SQLite, uma comparação vale 1 (verdadeiro) ou
-- 0 (falso), então AVG(condição) dá direto a proporção de chamados no prazo.
WITH encerrados AS (
    SELECT prioridade, sla_horas, horas_total,
           horas_total <= sla_horas AS no_prazo
    FROM vw_chamados
    WHERE status = 'Encerrado'
)
SELECT prioridade,
       sla_horas,
       COUNT(*)                          AS chamados,
       ROUND(AVG(horas_total), 1)        AS media_horas_total,
       ROUND(100.0 * AVG(no_prazo), 1)   AS pct_sla_cumprido
FROM encerrados
GROUP BY prioridade, sla_horas
ORDER BY sla_horas;


-- @P12 ------------------------------------------------------------------------
-- Pergunta 12: cumprimento do SLA por segmento de cliente, com a receita
-- mensal da carteira de cada segmento para dar peso de negócio ao resultado.
WITH sla AS (
    SELECT cl.segmento,
           ROUND(100.0 * AVG(c.horas_total <= c.sla_horas), 1) AS pct_sla_cumprido,
           COUNT(*) AS chamados
    FROM vw_chamados AS c
    JOIN clientes AS cl ON cl.id_cliente = c.id_cliente
    WHERE c.status = 'Encerrado'
    GROUP BY cl.segmento
),
receita AS (
    SELECT segmento,
           COUNT(*)          AS clientes,
           SUM(valor_mensal) AS receita_mensal
    FROM clientes
    GROUP BY segmento
)
SELECT s.segmento, s.chamados, s.pct_sla_cumprido, r.clientes,
       ROUND(r.receita_mensal, 2) AS receita_mensal
FROM sla AS s
JOIN receita AS r ON r.segmento = s.segmento;


-- @P13 ------------------------------------------------------------------------
-- Pergunta 13: rompimentos por mês na época de chuvas (dez a mar) x seca.
-- Como as épocas têm quantidades de meses diferentes, comparamos a MÉDIA
-- por mês, e não o total.
WITH por_mes AS (
    SELECT strftime('%Y-%m', abertura) AS mes,
           CASE WHEN CAST(strftime('%m', abertura) AS INTEGER) IN (12, 1, 2, 3)
                THEN 'Chuvas' ELSE 'Seca' END AS epoca,
           COUNT(*) AS rompimentos
    FROM vw_chamados
    WHERE tipo = 'Rompimento de fibra'
    GROUP BY mes, epoca
)
SELECT epoca,
       COUNT(*)                   AS meses,
       ROUND(AVG(rompimentos), 1) AS media_rompimentos_por_mes
FROM por_mes
GROUP BY epoca;


-- @P14 ------------------------------------------------------------------------
-- Pergunta 14: ranking de técnicos dentro de cada equipe.
-- Funções de janela calculam algo "por grupo" sem juntar as linhas:
-- PARTITION BY reinicia o ranking a cada equipe.
WITH producao AS (
    SELECT t.equipe, t.nome, t.nivel, COUNT(*) AS encerrados
    FROM vw_chamados AS c
    JOIN tecnicos AS t ON t.id_tecnico = c.id_tecnico
    WHERE c.status = 'Encerrado'
    GROUP BY t.equipe, t.nome, t.nivel
)
SELECT equipe, nome, nivel, encerrados,
       RANK() OVER (PARTITION BY equipe ORDER BY encerrados DESC) AS posicao
FROM producao
ORDER BY equipe, posicao;


-- @P15 ------------------------------------------------------------------------
-- Pergunta 15: chamados por mês e variação em relação ao mês anterior.
-- LAG() busca o valor da linha anterior na ordem definida no OVER.
WITH mensal AS (
    SELECT strftime('%Y-%m', abertura) AS mes, COUNT(*) AS chamados
    FROM chamados
    GROUP BY mes
)
SELECT mes,
       chamados,
       chamados - LAG(chamados) OVER (ORDER BY mes) AS variacao,
       ROUND(100.0 * (chamados - LAG(chamados) OVER (ORDER BY mes))
             / LAG(chamados) OVER (ORDER BY mes), 1)  AS variacao_pct
FROM mensal
ORDER BY mes;


-- @P16a -----------------------------------------------------------------------
-- Pergunta 16: chamados reincidentes (mesmo cliente, novo chamado em até
-- 7 dias depois do anterior).
-- LAG com PARTITION BY id_cliente traz a data do chamado anterior DO MESMO
-- cliente; depois basta comparar as duas datas.
WITH sequencia AS (
    SELECT id_chamado, id_cliente, tipo, abertura,
           LAG(abertura) OVER (PARTITION BY id_cliente ORDER BY abertura) AS abertura_anterior,
           LAG(tipo)     OVER (PARTITION BY id_cliente ORDER BY abertura) AS tipo_anterior
    FROM vw_chamados
)
SELECT COUNT(*) AS reincidentes,
       ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM chamados), 1) AS pct_do_total,
       SUM(tipo = tipo_anterior) AS mesmo_tipo_de_falha
FROM sequencia
WHERE julianday(abertura) - julianday(abertura_anterior) <= 7;


-- @P16b -----------------------------------------------------------------------
-- Pergunta 16 (parte 2): quais tipos de falha mais se repetem como reincidência.
WITH sequencia AS (
    SELECT tipo, abertura,
           LAG(abertura) OVER (PARTITION BY id_cliente ORDER BY abertura) AS abertura_anterior
    FROM vw_chamados
)
SELECT tipo, COUNT(*) AS reincidencias
FROM sequencia
WHERE julianday(abertura) - julianday(abertura_anterior) <= 7
GROUP BY tipo
ORDER BY reincidencias DESC;
