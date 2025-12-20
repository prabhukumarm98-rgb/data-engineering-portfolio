#!/usr/bin/env python3
"""
Simple benchmark runner - runs all benchmarks
"""

import sys
import os
from datetime import datetime

def run_spark_flink_benchmark():
    """Run Spark vs Flink benchmark"""
    print("\n" + "="*60)
    print("Running Spark vs Flink Benchmark")
    print("="*60)
    
    # Import and run
    sys.path.insert(0, 'spark_vs_flink')
    from benchmark import SparkFlinkBenchmark
    
    benchmark = SparkFlinkBenchmark(data_size_gb=1)  # 1GB for quick test
    benchmark.run_comprehensive_benchmark()
    
    return True

def run_storage_format_benchmark():
    """Run storage format benchmark"""
    print("\n" + "="*60)
    print("Running Storage Format Benchmark")
    print("="*60)
    
    sys.path.insert(0, 'storage_formats')
    from benchmark_storage import StorageFormatBenchmark
    
    benchmark = StorageFormatBenchmark(num_rows=50000)  # 50K rows for quick test
    benchmark.run_benchmarks()
    
    return True

def run_join_strategy_benchmark():
    """Run join strategy benchmark"""
    print("\n" + "="*60)
    print("Running Join Strategy Benchmark")
    print("="*60)
    
    # Simple join benchmark
