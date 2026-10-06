# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# DBTITLE 1,Instruções
# MAGIC %md
# MAGIC # Gasto Genie por Departamento
# MAGIC
# MAGIC Use o filtro **genie_surface** acima para escolher quais surfaces incluir na análise:
# MAGIC - `GENIE_ONE` — Genie One
# MAGIC - `GENIE_AGENTS` — Genie Agents
# MAGIC - `GENIE_CODE` — Genie Code
# MAGIC
# MAGIC Selecione uma, duas ou todas.
# MAGIC
# MAGIC Use **Data Início** e **Data Fim** para definir o período de análise (formato `YYYY-MM-DD`).
# MAGIC
# MAGIC Use **Tabela Dept Mapping** para indicar a tabela de mapeamento usuário → departamento (formato `catalog.schema.tabela`). A tabela precisa conter as colunas `email` (e-mail do usuário) e `departamento` (nome do departamento).
# MAGIC
# MAGIC > **Versão 1** — Período FREE: estima o custo dos DBUs gratuitos usando o SKU pago como proxy de preço. 
# MAGIC > **Versão 2** — Período PAGO: usa o custo real cobrado (SKUs pagos).

# COMMAND ----------

# DBTITLE 1,Versão 1: Período FREE — Custo Estimado por Departamento
# MAGIC %sql
# MAGIC -- Estima o custo dos DBUs free usando o SKU pago mais recente
# MAGIC -- do workspace como proxy de preço.
# MAGIC WITH
# MAGIC free_usage AS (
# MAGIC   SELECT
# MAGIC     account_id,
# MAGIC     workspace_id,
# MAGIC     identity_metadata.run_as AS user,
# MAGIC     usage_metadata.genie.surface AS genie_surface,
# MAGIC     usage_quantity,
# MAGIC     usage_end_time
# MAGIC   FROM system.billing.usage
# MAGIC   WHERE billing_origin_product = 'GENIE'
# MAGIC     AND sku_name = 'GENIE_FREE_USAGE'
# MAGIC     AND usage_date >= :data_inicio
# MAGIC     AND usage_date <= :data_fim
# MAGIC     AND usage_metadata.genie.surface IN (:genie_surface)
# MAGIC ),
# MAGIC latest_real_sku AS (
# MAGIC   SELECT
# MAGIC     workspace_id,
# MAGIC     max_by(sku_name, usage_start_time) AS proxy_sku_name
# MAGIC   FROM system.billing.usage
# MAGIC   WHERE billing_origin_product = 'GENIE'
# MAGIC     AND sku_name != 'GENIE_FREE_USAGE'
# MAGIC     AND usage_date >= :data_inicio
# MAGIC     AND usage_date <= :data_fim
# MAGIC   GROUP BY workspace_id
# MAGIC ),
# MAGIC resolved AS (
# MAGIC   SELECT
# MAGIC     f.account_id,
# MAGIC     f.workspace_id,
# MAGIC     f.user,
# MAGIC     f.genie_surface,
# MAGIC     f.usage_quantity,
# MAGIC     f.usage_end_time,
# MAGIC     r.proxy_sku_name AS pricing_sku_name
# MAGIC   FROM free_usage f
# MAGIC   LEFT JOIN latest_real_sku r
# MAGIC     ON f.workspace_id = r.workspace_id
# MAGIC ),
# MAGIC priced AS (
# MAGIC   SELECT
# MAGIC     r.user,
# MAGIC     r.genie_surface,
# MAGIC     r.usage_quantity,
# MAGIC     lp.pricing.effective_list.default AS list_price_per_unit,
# MAGIC     r.usage_quantity * lp.pricing.effective_list.default AS estimated_cost
# MAGIC   FROM resolved r
# MAGIC   LEFT JOIN system.billing.list_prices lp
# MAGIC     ON  r.pricing_sku_name  = lp.sku_name
# MAGIC     AND r.usage_end_time    >= lp.price_start_time
# MAGIC     AND (lp.price_end_time IS NULL OR r.usage_end_time < lp.price_end_time)
# MAGIC ),
# MAGIC user_costs AS (
# MAGIC   SELECT
# MAGIC     user,
# MAGIC     SUM(usage_quantity)  AS total_dbus,
# MAGIC     SUM(estimated_cost)  AS total_custo_estimado
# MAGIC   FROM priced
# MAGIC   GROUP BY user
# MAGIC )
# MAGIC SELECT
# MAGIC   COALESCE(d.departamento, 'Sem Mapeamento') AS departamento,
# MAGIC   COUNT(DISTINCT uc.user)                    AS qtd_usuarios,
# MAGIC   ROUND(SUM(uc.total_dbus), 2)               AS total_dbus,
# MAGIC   ROUND(SUM(uc.total_custo_estimado), 2)     AS total_custo_estimado_usd
# MAGIC FROM user_costs uc
# MAGIC LEFT JOIN IDENTIFIER(:tabela_dept_mapping) d ON uc.user = d.email
# MAGIC GROUP BY d.departamento
# MAGIC ORDER BY total_custo_estimado_usd DESC

# COMMAND ----------

# DBTITLE 1,Versão 2: Período PAGO — Custo Real por Departamento
# MAGIC %sql
# MAGIC -- Usa o custo real cobrado (SKUs pagos de GENIE), sem desconto.
# MAGIC WITH
# MAGIC paid_usage AS (
# MAGIC   SELECT
# MAGIC     identity_metadata.run_as AS user,
# MAGIC     usage_metadata.genie.surface AS genie_surface,
# MAGIC     usage_quantity,
# MAGIC     usage_end_time,
# MAGIC     sku_name
# MAGIC   FROM system.billing.usage
# MAGIC   WHERE billing_origin_product = 'GENIE'
# MAGIC     AND sku_name != 'GENIE_FREE_USAGE'
# MAGIC     AND usage_date >= :data_inicio
# MAGIC     AND usage_date <= :data_fim
# MAGIC     AND usage_metadata.genie.surface IN (:genie_surface)
# MAGIC ),
# MAGIC priced_paid AS (
# MAGIC   SELECT
# MAGIC     p.user,
# MAGIC     p.genie_surface,
# MAGIC     p.usage_quantity,
# MAGIC     lp.pricing.effective_list.default AS list_price_per_unit,
# MAGIC     p.usage_quantity * lp.pricing.effective_list.default AS actual_cost
# MAGIC   FROM paid_usage p
# MAGIC   LEFT JOIN system.billing.list_prices lp
# MAGIC     ON  p.sku_name       = lp.sku_name
# MAGIC     AND p.usage_end_time >= lp.price_start_time
# MAGIC     AND (lp.price_end_time IS NULL OR p.usage_end_time < lp.price_end_time)
# MAGIC ),
# MAGIC user_costs AS (
# MAGIC   SELECT
# MAGIC     user,
# MAGIC     SUM(usage_quantity)  AS total_dbus,
# MAGIC     SUM(actual_cost)     AS total_custo_real
# MAGIC   FROM priced_paid
# MAGIC   GROUP BY user
# MAGIC )
# MAGIC SELECT
# MAGIC   COALESCE(d.departamento, 'Sem Mapeamento') AS departamento,
# MAGIC   COUNT(DISTINCT uc.user)                    AS qtd_usuarios,
# MAGIC   ROUND(SUM(uc.total_dbus), 2)               AS total_dbus,
# MAGIC   ROUND(SUM(uc.total_custo_real), 2)         AS total_custo_real_usd
# MAGIC FROM user_costs uc
# MAGIC LEFT JOIN IDENTIFIER(:tabela_dept_mapping) d ON uc.user = d.email
# MAGIC GROUP BY d.departamento
# MAGIC ORDER BY total_custo_real_usd DESC