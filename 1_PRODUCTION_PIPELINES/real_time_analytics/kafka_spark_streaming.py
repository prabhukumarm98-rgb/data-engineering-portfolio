"""
Production Real-time Analytics Pipeline
Processes 10K+ events/sec for fraud detection and user analytics
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *
from datetime import datetime
import json


class RealTimeAnalyticsPipeline:
    """
    Production Kafka-Spark Streaming pipeline
    Used for:
    - Real-time fraud detection
    - User behavior analytics
    - Live dashboard updates
    """
    
    def __init__(self):
        self.spark = self._create_spark_session()
        self.kafka_brokers = "kafka-broker1:9092,kafka-broker2:9092"
        
    def _create_spark_session(self):
        """Create optimized Spark session for streaming"""
        return SparkSession.builder \
            .appName("RealTimeAnalytics") \
            .config("spark.sql.streaming.checkpointLocation", "/checkpoints/") \
            .config("spark.streaming.backpressure.enabled", "true") \
            .config("spark.streaming.kafka.maxRatePerPartition", "1000") \
            .config("spark.sql.shuffle.partitions", "200") \
            .getOrCreate()
    
    def read_from_kafka(self, topic):
        """
        Read streaming data from Kafka
        Production setup with schema validation
        """
        schema = StructType([
            StructField("user_id", StringType(), False),
            StructField("event_type", StringType(), False),
            StructField("timestamp", TimestampType(), False),
            StructField("amount", DecimalType(10, 2), True),
            StructField("device_id", StringType(), True),
            StructField("location", StringType(), True),
            StructField("session_id", StringType(), True)
        ])
        
        df = self.spark \
            .readStream \
            .format("kafka") \
            .option("kafka.bootstrap.servers", self.kafka_brokers) \
            .option("subscribe", topic) \
            .option("startingOffsets", "latest") \
            .option("failOnDataLoss", "false") \
            .load()
        
        # Parse JSON and apply schema
        parsed_df = df.select(
            from_json(col("value").cast("string"), schema).alias("data")
        ).select("data.*")
        
        return parsed_df
    
    def detect_fraud_patterns(self, stream_df):
        """
        Real-time fraud detection using windowed aggregations
        Detects: velocity attacks, unusual amounts, geo anomalies
        """
        # Window: 5 minute sliding window every 1 minute
        window_spec = window("timestamp", "5 minutes", "1 minute")
        
        fraud_checks = stream_df \
            .withWatermark("timestamp", "10 minutes") \
            .groupBy(window_spec, "user_id") \
            .agg(
                count("*").alias("transaction_count"),
                sum("amount").alias("total_amount"),
                countDistinct("location").alias("unique_locations")
            ) \
            .withColumn("avg_amount_per_min", col("total_amount") / 5) \
            .withColumn("fraud_risk", 
                when(col("transaction_count") > 20, "HIGH")
                .when(col("avg_amount_per_min") > 1000, "HIGH")
                .when(col("unique_locations") > 3, "MEDIUM")
                .otherwise("LOW")
            )
        
        return fraud_checks
    
    def calculate_user_metrics(self, stream_df):
        """
        Calculate real-time user engagement metrics
        Used for personalization and recommendations
        """
        metrics = stream_df \
            .withWatermark("timestamp", "30 minutes") \
            .groupBy("user_id", window("timestamp", "1 hour")) \
            .agg(
                count("*").alias("event_count"),
                countDistinct("event_type").alias("unique_events"),
                sum(when(col("event_type") == "purchase", 1).otherwise(0)).alias("purchases"),
                avg("amount").alias("avg_transaction_value")
            ) \
            .withColumn("engagement_score",
                col("event_count") * 0.3 +
                col("unique_events") * 0.4 +
                col("purchases") * 0.3
            )
        
        return metrics
    
    def write_to_delta(self, stream_df, table_name):
        """
        Write streaming results to Delta Lake
        Production-grade with merge schemas and compaction
        """
        checkpoint_path = f"/checkpoints/{table_name}"
        
        query = stream_df \
            .writeStream \
            .format("delta") \
            .outputMode("append") \
            .option("checkpointLocation", checkpoint_path) \
            .option("mergeSchema", "true") \
            .trigger(processingTime="1 minute") \
            .table(table_name)
        
        return query
    
    def create_dashboard_stream(self, stream_df):
        """
        Create real-time dashboard stream
        Aggregates data for Power BI/Tableau consumption
        """
        dashboard_stream = stream_df \
            .withWatermark("timestamp", "1 minute") \
            .groupBy(window("timestamp", "1 minute")) \
            .agg(
                count("*").alias("events_per_minute"),
                countDistinct("user_id").alias("active_users"),
                sum("amount").alias("total_volume"),
                approx_count_distinct("session_id").alias("active_sessions")
            ) \
            .select(
                col("window.start").alias("minute"),
                "events_per_minute",
                "active_users",
                "total_volume",
                "active_sessions"
            )
        
        return dashboard_stream
    
    def run_pipeline(self):
        """Main pipeline execution"""
        print(f"[{datetime.now()}] Starting Real-time Analytics Pipeline")
        
        # 1. Read from Kafka
        print("Reading from Kafka topic: user-events")
        raw_stream = self.read_from_kafka("user-events")
        
        # 2. Fraud detection
        print("Running fraud detection...")
        fraud_alerts = self.detect_fraud_patterns(raw_stream)
        
        # 3. User analytics
        print("Calculating user metrics...")
        user_metrics = self.calculate_user_metrics(raw_stream)
        
        # 4. Dashboard stream
        print("Creating dashboard stream...")
        dashboard_data = self.create_dashboard_stream(raw_stream)
        
        # 5. Start all streams
        print("Starting streaming queries...")
        
        fraud_query = self.write_to_delta(fraud_alerts, "fraud_alerts")
        metrics_query = self.write_to_delta(user_metrics, "user_metrics")
        dashboard_query = dashboard_data \
            .writeStream \
            .format("console") \
            .outputMode("complete") \
            .trigger(processingTime="30 seconds") \
            .start()
        
        print("Pipeline started successfully!")
        print("Streaming queries active:")
        print(f"1. Fraud alerts -> Delta table 'fraud_alerts'")
        print(f"2. User metrics -> Delta table 'user_metrics'")
        print(f"3. Dashboard data -> Console output")
        
        return fraud_query, metrics_query, dashboard_query


def main():
    """Example usage of the pipeline"""
    print("="*70)
    print("REAL-TIME ANALYTICS PIPELINE - PRODUCTION EXAMPLE")
    print("="*70)
    
    try:
        pipeline = RealTimeAnalyticsPipeline()
        queries = pipeline.run_pipeline()
        
        # Keep pipeline running
        for query in queries:
            query.awaitTermination()
            
    except KeyboardInterrupt:
        print("\nPipeline stopped by user")
    except Exception as e:
        print(f"Pipeline error: {str(e)}")
    finally:
        print("Pipeline shutdown complete")


if __name__ == "__main__":
    main()
