-- PRODUCTION SNOWFLAKE OPTIMIZATION SCRIPTS
-- Used daily to manage 50TB+ data warehouse


-- 1. ZERO-COPY CLONE MANAGEMENT


-- Create development clone from production (instant, no storage cost)
CREATE OR REPLACE DATABASE analytics_dev 
CLONE analytics_prod;

-- Clone specific schema for testing
CREATE OR REPLACE SCHEMA analytics_dev.testing 
CLONE analytics_prod.core;

-- Clone table with history (time travel included)
CREATE OR REPLACE TABLE analytics_dev.core.users 
CLONE analytics_prod.core.users;


-- 2. TIME TRAVEL QUERIES (Data Recovery)


-- View table changes in last 24 hours
SELECT *
FROM analytics_prod.core.customers
AT(OFFSET => -60*60*24)  -- 24 hours ago
MINUS
SELECT *
FROM analytics_prod.core.customers;

-- Restore deleted rows from 2 hours ago
INSERT INTO analytics_prod.core.customers
SELECT *
FROM analytics_prod.core.customers
AT(OFFSET => -60*60*2)   -- 2 hours ago
WHERE customer_id IN (
    SELECT customer_id 
    FROM analytics_prod.core.deleted_customers 
    WHERE deleted_at > CURRENT_TIMESTAMP - INTERVAL '2 hours'
);

-- Compare current vs yesterday's data
WITH current_data AS (
    SELECT customer_id, total_orders, lifetime_value
    FROM analytics_prod.core.customers
),
yesterday_data AS (
    SELECT customer_id, total_orders, lifetime_value
    FROM analytics_prod.core.customers
    AT(OFFSET => -60*60*24)  -- Yesterday
)
SELECT 
    c.customer_id,
    c.total_orders as orders_today,
    y.total_orders as orders_yesterday,
    c.lifetime_value - y.lifetime_value as daily_growth
FROM current_data c
JOIN yesterday_data y ON c.customer_id = y.customer_id
WHERE c.total_orders != y.total_orders;


-- 3. PERFORMANCE OPTIMIZATION


-- Analyze table for query optimization
ALTER TABLE analytics_prod.core.transactions 
CLUSTER BY (transaction_date, customer_id);

-- Check clustering effectiveness
SELECT 
    table_name,
    ROUND(clustering_ratio, 2) as clustering_ratio,
    CASE 
        WHEN clustering_ratio > 0.7 THEN 'Well clustered'
        WHEN clustering_ratio > 0.3 THEN 'Needs improvement'
        ELSE 'Re-cluster needed'
    END as cluster_status
FROM information_schema.table_storage_metrics
WHERE table_schema = 'CORE'
AND table_name = 'TRANSACTIONS';

-- Materialized view for frequent queries
CREATE OR REPLACE MATERIALIZED VIEW analytics_prod.core.daily_sales_mv
AS
SELECT 
    DATE_TRUNC('day', transaction_date) as sale_date,
    product_category,
    COUNT(*) as transaction_count,
    SUM(amount) as total_sales,
    AVG(amount) as avg_transaction,
    COUNT(DISTINCT customer_id) as unique_customers
FROM analytics_prod.core.transactions
WHERE transaction_date >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY 1, 2;

-- Auto-refresh materialized view
ALTER MATERIALIZED VIEW analytics_prod.core.daily_sales_mv 
SET SCHEDULE = '10 MINUTE';


-- 4. RESOURCE MONITORING & COST CONTROL


-- Monitor warehouse usage
SELECT 
    warehouse_name,
    DATE(start_time) as usage_date,
    SUM(credits_used) as total_credits,
    SUM(credits_used_compute) as compute_credits,
    SUM(credits_used_cloud_services) as cloud_services_credits,
    ROUND(SUM(credits_used) * 3.00, 2) as estimated_cost_usd  -- $3/credit
FROM snowflake.account_usage.warehouse_metering_history
WHERE start_time >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY 1, 2
ORDER BY total_credits DESC;

-- Find expensive queries
SELECT 
    query_id,
    query_text,
    user_name,
    warehouse_name,
    execution_time / 1000 as execution_seconds,
    partitions_scanned,
    bytes_scanned / POWER(1024, 3) as gb_scanned,
    credits_used_cloud_services,
    ROUND(credits_used_cloud_services * 3.00, 2) as cloud_cost_usd
FROM snowflake.account_usage.query_history
WHERE bytes_scanned > 100 * 1024 * 1024 * 1024  -- Queries scanning >100GB
AND start_time >= CURRENT_DATE - INTERVAL '1 day'
ORDER BY bytes_scanned DESC
LIMIT 20;


-- 5. DATA SHARING & SECURE VIEWS


-- Create secure view for external sharing
CREATE OR REPLACE SECURE VIEW analytics_prod.shared.sales_dashboard
AS
SELECT 
    region,
    product_category,
    DATE_TRUNC('month', transaction_date) as month,
    COUNT(*) as transaction_count,
    SUM(amount) as total_sales,
    COUNT(DISTINCT customer_id) as unique_customers
FROM analytics_prod.core.transactions
WHERE transaction_date >= '2024-01-01'
GROUP BY 1, 2, 3;

-- Create share for external consumers
CREATE SHARE sales_data_share;
GRANT USAGE ON DATABASE analytics_prod TO SHARE sales_data_share;
GRANT USAGE ON SCHEMA analytics_prod.shared TO SHARE sales_data_share;
GRANT SELECT ON VIEW analytics_prod.shared.sales_dashboard TO SHARE sales_data_share;

-- Add consumer account to share
ALTER SHARE sales_data_share ADD ACCOUNTS = consumer_account;

-- 6. AUTOMATED GOVERNANCE


-- Tag sensitive data for governance
ALTER TABLE analytics_prod.core.customers 
SET TAG data_classification = 'PII';

ALTER TABLE analytics_prod.core.transactions 
SET TAG data_classification = 'FINANCIAL';

-- Create masking policy for PII
CREATE OR REPLACE MASKING POLICY email_mask AS (val string) RETURNS string ->
    CASE 
        WHEN CURRENT_ROLE() IN ('ANALYST', 'DATA_SCIENTIST') THEN val
        ELSE REGEXP_REPLACE(val, '(.)[^@]+@', '\\1****@')
    END;

-- Apply masking policy
ALTER TABLE analytics_prod.core.customers 
MODIFY COLUMN email 
SET MASKING POLICY email_mask;


-- 7. PRODUCTION MONITORING DASHBOARD


CREATE OR REPLACE VIEW analytics_prod.monitoring.warehouse_health
AS
SELECT 
    wh.warehouse_name,
    DATE(wh.start_time) as metric_date,
    COUNT(DISTINCT qh.query_id) as total_queries,
    AVG(qh.execution_time / 1000) as avg_execution_seconds,
    SUM(wh.credits_used) as total_credits,
    SUM(qh.bytes_scanned) / POWER(1024, 4) as tb_scanned,
    -- Performance metrics
    ROUND(SUM(qh.bytes_scanned) / NULLIF(SUM(wh.credits_used), 0) / POWER(1024, 3), 2) as gb_per_credit,
    ROUND(AVG(qh.partitions_total), 0) as avg_partitions_used,
    -- Cost metrics
    ROUND(SUM(wh.credits_used) * 3.00, 2) as estimated_cost_usd
FROM snowflake.account_usage.warehouse_metering_history wh
JOIN snowflake.account_usage.query_history qh 
    ON wh.warehouse_id = qh.warehouse_id
    AND wh.start_time = qh.start_time
WHERE wh.start_time >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY 1, 2
ORDER BY metric_date DESC, total_credits DESC;
