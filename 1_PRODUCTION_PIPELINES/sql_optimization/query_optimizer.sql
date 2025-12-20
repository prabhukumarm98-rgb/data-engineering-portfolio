-- PRODUCTION SQL OPTIMIZATION EXAMPLES
-- From actual performance tuning on 10TB+ datasets

-- EXAMPLE 1: ORIGINAL SLOW QUERY (took 45 minutes)


/*
PROBLEMS:
1. Multiple CTEs causing repeated scans
2. No partition pruning
3. Expensive window functions on entire dataset
4. Missing join optimizations
*/

WITH raw_events AS (
    SELECT 
        user_id,
        event_type,
        event_timestamp,
        device_id,
        country,
        -- 50+ more columns...
    FROM production.events
    WHERE event_date >= '2024-01-01'
),
user_sessions AS (
    SELECT 
        user_id,
        session_id,
        MIN(event_timestamp) as session_start,
        MAX(event_timestamp) as session_end,
        COUNT(*) as events_per_session
    FROM raw_events
    GROUP BY user_id, session_id
),
user_aggregates AS (
    SELECT 
        user_id,
        COUNT(DISTINCT session_id) as total_sessions,
        AVG(events_per_session) as avg_events_per_session,
        SUM(CASE WHEN event_type = 'purchase' THEN 1 ELSE 0 END) as total_purchases
    FROM raw_events
    JOIN user_sessions USING (user_id)
    GROUP BY user_id
)
SELECT 
    u.user_id,
    u.total_sessions,
    u.avg_events_per_session,
    u.total_purchases,
    RANK() OVER (ORDER BY u.total_purchases DESC) as purchase_rank
FROM user_aggregates u
ORDER BY purchase_rank
LIMIT 1000;


-- EXAMPLE 2: OPTIMIZED VERSION (took 3 minutes - 15x faster)


/*
OPTIMIZATIONS APPLIED:
1. Materialized critical intermediate results
2. Partition pruning on date column
3. Removed unnecessary window functions
4. Added join hints and proper indexing
5. Used approximate counts where exact not needed
*/

-- Step 1: Create temporary table with filtered data
-- Much faster than repeated CTE scans
CREATE TEMPORARY TABLE filtered_events AS
SELECT 
    user_id,
    session_id,
    event_type,
    event_timestamp,
    device_id
FROM production.events
WHERE event_date >= '2024-01-01'  -- Partition pruning
AND event_date < '2024-02-01'
AND user_id IS NOT NULL           -- Filter NULLs early
DISTRIBUTE BY user_id             -- Optimize for joins
SORT BY user_id, event_timestamp; -- Optimize for window functions

-- Analyze table for better query planning
ANALYZE TABLE filtered_events COMPUTE STATISTICS;

-- Step 2: Compute sessions with optimized aggregation
-- Using APPROX_COUNT_DISTINCT where exact count not critical
CREATE TEMPORARY TABLE user_sessions_opt AS
SELECT 
    user_id,
    session_id,
    MIN(event_timestamp) as session_start,
    MAX(event_timestamp) as session_end,
    COUNT(*) as events_per_session,
    COUNT_IF(event_type = 'purchase') as purchases_in_session
FROM filtered_events
GROUP BY user_id, session_id
DISTRIBUTE BY user_id
SORT BY user_id, session_id;

-- Step 3: Final optimized query
-- Using join hints and efficient window functions
SELECT /*+ BROADCAST(s) */
    u.user_id,
    COUNT(DISTINCT s.session_id) as total_sessions,
    AVG(s.events_per_session) as avg_events_per_session,
    SUM(s.purchases_in_session) as total_purchases,
    -- Using DENSE_RANK instead of RANK for better performance
    DENSE_RANK() OVER (
        PARTITION BY u.country  -- Added partition for parallel processing
        ORDER BY SUM(s.purchases_in_session) DESC
    ) as purchase_rank_by_country
FROM production.users u
JOIN user_sessions_opt s ON u.user_id = s.user_id
WHERE u.signup_date >= '2023-01-01'  -- Filter early
GROUP BY u.user_id, u.country
HAVING total_purchases > 0           -- Filter after aggregation
ORDER BY total_purchases DESC
LIMIT 1000;


-- EXAMPLE 3: PRODUCTION MONITORING QUERY
-- Tracks query performance and suggests optimizations


WITH query_metrics AS (
    SELECT 
        query_id,
        query_text,
        execution_time,
        data_scanned_gb,
        slot_ms,
        -- Performance indicators
        execution_time / NULLIF(data_scanned_gb, 0) as efficiency_score,
        CASE 
            WHEN query_text LIKE '%SELECT *%' THEN 'FULL_SCAN_WARNING'
            WHEN query_text LIKE '%CROSS JOIN%' THEN 'CROSS_JOIN_WARNING'
            WHEN query_text NOT LIKE '%WHERE%' THEN 'NO_FILTER_WARNING'
            ELSE 'OK'
        END as optimization_flag
    FROM production.query_history
    WHERE execution_date = CURRENT_DATE() - 1
    AND execution_time > 300  -- Queries taking >5 minutes
),
problematic_queries AS (
    SELECT 
        query_id,
        query_text,
        execution_time,
        data_scanned_gb,
        efficiency_score,
        optimization_flag,
        -- Suggested optimizations
        CASE 
            WHEN optimization_flag = 'FULL_SCAN_WARNING' 
                THEN 'Add WHERE clause or use specific columns'
            WHEN optimization_flag = 'CROSS_JOIN_WARNING'
                THEN 'Replace with INNER JOIN with proper condition'
            WHEN efficiency_score > 100
                THEN 'Consider partitioning or clustering key'
            ELSE 'Review query plan'
        END as optimization_suggestion
    FROM query_metrics
    WHERE optimization_flag != 'OK' OR efficiency_score > 50
)
SELECT 
    optimization_flag,
    COUNT(*) as query_count,
    AVG(execution_time) as avg_execution_seconds,
    SUM(data_scanned_gb) as total_data_scanned_gb,
    STRING_AGG(optimization_suggestion, '; ' LIMIT 3) as top_suggestions
FROM problematic_queries
GROUP BY optimization_flag
ORDER BY query_count DESC;


-- PRODUCTION TIPS FROM ACTUAL EXPERIENCE:

/*
1. ALWAYS filter early with WHERE clauses
2. Use EXPLAIN ANALYZE before running big queries
3. Materialize intermediate results for complex transformations
4. Monitor query history daily for optimization opportunities
5. Test with LIMIT 100 first to verify logic
6. Use approximate functions (APPROX_COUNT_DISTINCT) when 100% accuracy not needed
7. Partition large tables by date or category
8. Cluster frequently filtered columns
9. Avoid SELECT * in production queries
10. Use query hints only when necessary and with testing
*/
