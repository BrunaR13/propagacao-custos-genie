# Genie Cost por Departamento — Interativo

Notebook interativo para análise de **custos de consumo do Genie por departamento**, com suporte a períodos gratuitos (FREE) e pagos.

## Objetivo

Permitir que times de FinOps e administradores visualizem o consumo de DBUs do Genie segmentado por departamento, usando uma tabela externa de mapeamento usuário → departamento.

## Parâmetros (widgets)

| Parâmetro | Tipo | Descrição | Exemplo |
| --- | --- | --- | --- |
| `genie_surface` | Dropdown (multi) | Surfaces do Genie a incluir na análise | `GENIE_CODE`, `GENIE_ONE`, `GENIE_AGENTS` |
| `data_inicio` | Texto | Data de início do período (formato `YYYY-MM-DD`) | `2026-09-01` |
| `data_fim` | Texto | Data de fim do período (formato `YYYY-MM-DD`) | `2026-09-30` |
| `tabela_dept_mapping` | Texto | Nome completo da tabela de mapeamento (`catalog.schema.tabela`) | `meu_catalog.meu_schema.user_department_mapping` |

## Tabela de mapeamento de departamento

O parâmetro `tabela_dept_mapping` deve apontar para uma tabela com, no mínimo, as seguintes colunas:

| Coluna | Tipo | Descrição |
| --- | --- | --- |
| `email` | STRING | E-mail do usuário (deve corresponder ao campo `identity_metadata.run_as` de `system.billing.usage`) |
| `departamento` | STRING | Nome do departamento ao qual o usuário pertence |

Usuários sem correspondência na tabela aparecem como **"Sem Mapeamento"**.

## Estrutura do notebook

### Célula 1 — Instruções
Markdown com orientações de uso e descrição dos parâmetros.

### Célula 2 — Versão 1: Período FREE
Estima o custo dos DBUs gratuitos (`GENIE_FREE_USAGE`) usando o SKU pago mais recente do workspace como proxy de preço. Útil para entender quanto **teria custado** o consumo durante o período de free trial.

### Célula 3 — Versão 2: Período PAGO
Calcula o custo real cobrado a partir dos SKUs pagos do Genie, cruzando com `system.billing.list_prices` para obter o preço unitário vigente.

## Tabelas de sistema utilizadas

| Tabela | Uso |
| --- | --- |
| `system.billing.usage` | Registros de consumo de DBUs do Genie |
| `system.billing.list_prices` | Preços vigentes por SKU para cálculo de custo |

## Colunas de saída

Ambas as versões retornam:

| Coluna | Descrição |
| --- | --- |
| `departamento` | Nome do departamento (ou "Sem Mapeamento") |
| `qtd_usuarios` | Quantidade de usuários distintos |
| `total_dbus` | Total de DBUs consumidos |
| `total_custo_estimado_usd` / `total_custo_real_usd` | Custo em USD (estimado na V1, real na V2) |

## Como usar

1. Ajuste os widgets no topo do notebook (`genie_surface`, `data_inicio`, `data_fim`, `tabela_dept_mapping`)
2. Execute a **Célula 2** para ver o custo estimado no período FREE
3. Execute a **Célula 3** para ver o custo real no período PAGO
4. Compare os resultados para entender a evolução de custos

## Pré-requisitos

- Acesso de leitura às system tables `system.billing.usage` e `system.billing.list_prices`
- Tabela de mapeamento de departamento criada e populada com as colunas `email` e `departamento`
- Compute com suporte a Databricks SQL (Serverless ou SQL Warehouse)


## Disclaimer

> **Este notebook não é um produto oficial da Databricks.** Foi criado de forma independente para fins de análise e demonstração. Não possui garantia de suporte, manutenção ou compatibilidade futura. Use por sua conta e risco. Para soluções oficiais de FinOps e monitoramento de custos, consulte a documentação da Databricks.
