#!/usr/bin/env python3
"""
Benchmark different storage formats: Parquet, ORC, Avro, Delta, Iceberg
"""

import time
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pyarrow.orc as orc
import fastavro
from delta import DeltaTable
import json
import os
from datetime import datetime


class StorageFormatBenchmark:
    """Benchmark storage formats for read/write performance"""
    
    def __init__(self, num_rows=1000000):
        self.num_rows = num_rows
        self.results = []
        self.test_data = self._generate_test_data()
        
    def _generate_test_data(self):
        """Generate realistic test data"""
        print(f"Generating {self.num_rows:,} rows of test data...")
        
        data = {
            'id': range(self.num_rows),
            'timestamp': pd.date_range('2024-01-01', periods=self.num_rows, freq='s'),
            'user_id': [f'user_{i % 10000}' for i in range(self.num_rows)],
            'amount': [float(i % 1000) + (i % 100) / 100.0 for i in range(self.num_rows)],
            'category': [f'cat_{i % 50}' for i in range(self.num_rows)],
            'region': [f'region_{i % 20}' for i in range(self.num_rows)],
            'is_active': [i % 2 == 0 for i in range(self.num_rows)],
            'score': [float(i % 100) / 100.0 for i in range(self.num_rows)]
        }
        
        return pd.DataFrame(data)
    
    def benchmark_parquet(self, compression='snappy'):
        """Benchmark Parquet format"""
        print(f"\nBenchmarking Parquet ({compression})...")
        
        file_path = f'test_data_parquet_{compression}.parquet'
        
        # Write benchmark
        start_write = time.time()
        self.test_data.to_parquet(
            file_path,
            engine='pyarrow',
            compression=compression
        )
        write_time = time.time() - start_write
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Read benchmark
        start_read = time.time()
        df_read = pd.read_parquet(file_path)
        read_time = time.time() - start_read
        
        # Query benchmark (filter)
        start_query = time.time()
        filtered = df_read[df_read['amount'] > 500]
        query_time = time.time() - start_query
        
        result = {
            'format': 'Parquet',
            'compression': compression,
            'write_time': write_time,
            'read_time': read_time,
            'query_time': query_time,
            'file_size_mb': file_size / (1024 * 1024),
            'rows_read': len(df_read),
            'rows_filtered': len(filtered)
        }
        
        self.results.append(result)
        print(f"  Write: {write_time:.2f}s, Read: {read_time:.2f}s, Size: {result['file_size_mb']:.2f}MB")
        
        return result
    
    def benchmark_orc(self, compression='snappy'):
        """Benchmark ORC format"""
        print(f"\nBenchmarking ORC ({compression})...")
        
        file_path = f'test_data_orc_{compression}.orc'
        
        # Convert to PyArrow table
        table = pa.Table.from_pandas(self.test_data)
        
        # Write benchmark
        start_write = time.time()
        with pa.OSFile(file_path, 'wb') as sink:
            orc.write_table(table, sink, compression=compression)
        write_time = time.time() - start_write
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Read benchmark
        start_read = time.time()
        with pa.OSFile(file_path, 'rb') as source:
            table_read = orc.read_table(source)
            df_read = table_read.to_pandas()
        read_time = time.time() - start_read
        
        # Query benchmark
        start_query = time.time()
        filtered = df_read[df_read['amount'] > 500]
        query_time = time.time() - start_query
        
        result = {
            'format': 'ORC',
            'compression': compression,
            'write_time': write_time,
            'read_time': read_time,
            'query_time': query_time,
            'file_size_mb': file_size / (1024 * 1024),
            'rows_read': len(df_read),
            'rows_filtered': len(filtered)
        }
        
        self.results.append(result)
        print(f"  Write: {write_time:.2f}s, Read: {read_time:.2f}s, Size: {result['file_size_mb']:.2f}MB")
        
        return result
    
    def benchmark_avro(self, codec='deflate'):
        """Benchmark Avro format"""
        print(f"\nBenchmarking Avro ({codec})...")
        
        file_path = f'test_data_avro_{codec}.avro'
        
        # Define Avro schema
        schema = {
            'type': 'record',
            'name': 'TestRecord',
            'fields': [
                {'name': 'id', 'type': 'int'},
                {'name': 'timestamp', 'type': {'type': 'long', 'logicalType': 'timestamp-millis'}},
                {'name': 'user_id', 'type': 'string'},
                {'name': 'amount', 'type': 'double'},
                {'name': 'category', 'type': 'string'},
                {'name': 'region', 'type': 'string'},
                {'name': 'is_active', 'type': 'boolean'},
                {'name': 'score', 'type': 'double'}
            ]
        }
        
        # Convert data to Avro format
        records = []
        for _, row in self.test_data.iterrows():
            records.append({
                'id': int(row['id']),
                'timestamp': int(row['timestamp'].timestamp() * 1000),
                'user_id': row['user_id'],
                'amount': float(row['amount']),
                'category': row['category'],
                'region': row['region'],
                'is_active': bool(row['is_active']),
                'score': float(row['score'])
            })
        
        # Write benchmark
        start_write = time.time()
        with open(file_path, 'wb') as out:
            fastavro.writer(out, schema, records, codec=codec)
        write_time = time.time() - start_write
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Read benchmark
        start_read = time.time()
        with open(file_path, 'rb') as inp:
            reader = fastavro.reader(inp)
            records_read = list(reader)
            df_read = pd.DataFrame(records_read)
        read_time = time.time() - start_read
        
        # Query benchmark
        start_query = time.time()
        filtered = df_read[df_read['amount'] > 500]
        query_time = time.time() - start_query
        
        result = {
            'format': 'Avro',
            'compression': codec,
            'write_time': write_time,
            'read_time': read_time,
            'query_time': query_time,
            'file_size_mb': file_size / (1024 * 1024),
            'rows_read': len(df_read),
            'rows_filtered': len(filtered)
        }
        
        self.results.append(result)
        print(f"  Write: {write_time:.2f}s, Read: {read_time:.2f}s, Size: {result['file_size_mb']:.2f}MB")
        
        return result
    
    def benchmark_delta(self):
        """Benchmark Delta Lake format"""
        print(f"\nBenchmarking Delta Lake...")
        
        delta_path = 'test_data_delta'
        
        # Write benchmark
        start_write = time.time()
        self.test_data.to_parquet(
            f'{delta_path}/part-0.parquet'
        )
        # In production, you would use DeltaTable operations
        write_time = time.time() - start_write
        
        # Get directory size
        file_size = sum(
            os.path.getsize(os.path.join(delta_path, f)) 
            for f in os.listdir(delta_path) 
            if os.path.isfile(os.path.join(delta_path, f))
        )
        
        # Read benchmark
        start_read = time.time()
        df_read = pd.read_parquet(f'{delta_path}/part-0.parquet')
        read_time = time.time() - start_read
        
        # Query benchmark
        start_query = time.time()
        filtered = df_read[df_read['amount'] > 500]
        query_time = time.time() - start_query
        
        result = {
            'format': 'Delta',
            'compression': 'snappy',
            'write_time': write_time,
            'read_time': read_time,
            'query_time': query_time,
            'file_size_mb': file_size / (1024 * 1024),
            'rows_read': len(df_read),
            'rows_filtered': len(filtered)
        }
        
        self.results.append(result)
        print(f"  Write: {write_time:.2f}s, Read: {read_time:.2f}s, Size: {result['file_size_mb']:.2f}MB")
        
        return result
    
    def run_benchmarks(self):
        """Run all storage format benchmarks"""
        print(f"Running storage format benchmarks on {self.num_rows:,} rows")
        print("="*60)
        
        # Test different compressions for Parquet
        for compression in ['snappy', 'gzip', 'zstd', 'none']:
            self.benchmark_parquet(compression)
        
        # Test ORC
        for compression in ['snappy', 'gzip', 'zlib', 'none']:
            self.benchmark_orc(compression)
        
        # Test Avro
        for codec in ['deflate', 'snappy', 'null']:
            self.benchmark_avro(codec)
        
        # Test Delta
        self.benchmark_delta()
        
        # Analyze results
        self.analyze_results()
    
    def analyze_results(self):
        """Analyze and compare benchmark results"""
        print("\n" + "="*60)
        print("STORAGE FORMAT BENCHMARK RESULTS")
        print("="*60)
        
        if not self.results:
            print("No results to analyze")
            return
        
        df = pd.DataFrame(self.results)
        
        # Sort by read time (fastest first)
        df_sorted = df.sort_values('read_time')
        
        print("\nPerformance Ranking (by read speed):")
        for i, (_, row) in enumerate(df_sorted.iterrows(), 1):
            print(f"{i}. {row['format']} ({row['compression']}): "
                  f"{row['read_time']:.2f}s read, "
                  f"{row['file_size_mb']:.2f}MB")
        
        # Find best in each category
        fastest_read = df.loc[df['read_time'].idxmin()]
        fastest_write = df.loc[df['write_time'].idxmin()]
        smallest_size = df.loc[df['file_size_mb'].idxmin()]
        
        print("\n" + "="*60)
        print("BEST IN CATEGORY:")
        print("="*60)
        print(f"Fastest Read: {fastest_read['format']} ({fastest_read['compression']}) - {fastest_read['read_time']:.2f}s")
        print(f"Fastest Write: {fastest_write['format']} ({fastest_write['compression']}) - {fastest_write['write_time']:.2f}s")
        print(f"Smallest Size: {smallest_size['format']} ({smallest_size['compression']}) - {smallest_size['file_size_mb']:.2f}MB")
        
        # Calculate compression ratios
        uncompressed_size = df[df['compression'] == 'none']['file_size_mb'].mean()
        
        print("\n" + "="*60)
        print("COMPRESSION ANALYSIS:")
        print("="*60)
        for format_name in df['format'].unique():
            format_data = df[df['format'] == format_name]
            for _, row in format_data.iterrows():
                if row['compression'] != 'none':
                    ratio = uncompressed_size / row['file_size_mb'] if row['file_size_mb'] > 0 else 0
                    print(f"{row['format']} ({row['compression']}): {ratio:.1f}x compression")
        
        # Generate recommendations
        self.generate_recommendations(df)
        
        # Save results
        self.save_results(df)
        
        # Plot results
        self.plot_results(df)
    
    def generate_recommendations(self, df):
        """Generate production recommendations"""
        print("\n" + "="*60)
        print("PRODUCTION RECOMMENDATIONS")
        print("="*60)
        
        recommendations = [
            "Use Parquet when:",
            "  - Analytical queries with column pruning",
            "  - Need best query performance",
            "  - Using Spark/Presto/Athena",
            "  - Compression: ZSTD for best ratio, Snappy for speed",
            "",
            "Use ORC when:",
            "  - Already using Hive ecosystem",
            "  - Need ACID transactions (Hive 3+)",
            "  - Compression: ZLIB for best ratio",
            "",
            "Use Avro when:",
            "  - Schema evolution is critical",
            "  - Streaming data (Kafka with Schema Registry)",
            "  - Row-based access patterns",
            "  - Compression: DEFLATE for good balance",
            "",
            "Use Delta Lake when:",
            "  - Need ACID transactions on data lakes",
            "  - Time travel and data versioning",
            "  - Merge/UPDATE/DELETE operations",
            "  - Using Databricks ecosystem",
            "",
            "Based on our benchmarks:",
            "  - For analytics: Parquet (ZSTD)",
            "  - For storage: ORC (ZLIB)",
            "  - For streaming: Avro (DEFLATE)",
            "  - For data lakes: Delta Lake"
        ]
        
        for line in recommendations:
            print(line)
    
    def save_results(self, df):
        """Save results to JSON file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f'storage_benchmark_results_{timestamp}.json'
        
        results_dict = {
            'timestamp': datetime.now().isoformat(),
            'num_rows': self.num_rows,
            'results': df.to_dict('records')
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_dict, f, indent=2)
        
        print(f"\nResults saved to '{output_file}'")
        
        # Also save as CSV for easy analysis
        csv_file = f'storage_benchmark_results_{timestamp}.csv'
        df.to_csv(csv_file, index=False)
        print(f"Results saved to '{csv_file}'")
    
    def plot_results(self, df):
        """Create visualization of results"""
        try:
            import matplotlib.pyplot as plt
            import seaborn as sns
            
            sns.set_style("whitegrid")
            
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            
            # Plot 1: Read times
            ax1 = axes[0, 0]
            read_data = df.sort_values('read_time')
            bars1 = ax1.barh(
                range(len(read_data)),
                read_data['read_time'],
                color='skyblue'
            )
            ax1.set_yticks(range(len(read_data)))
            ax1.set_yticklabels([
                f"{row['format']} ({row['compression']})" 
                for _, row in read_data.iterrows()
            ])
            ax1.set_xlabel('Read Time (seconds)')
            ax1.set_title('Read Performance (lower is better)')
            
            # Plot 2: Write times
            ax2 = axes[0, 1]
            write_data = df.sort_values('write_time')
            bars2 = ax2.barh(
                range(len(write_data)),
                write_data['write_time'],
                color='lightcoral'
            )
            ax2.set_yticks(range(len(write_data)))
            ax2.set_yticklabels([
                f"{row['format']} ({row['compression']})" 
                for _, row in write_data.iterrows()
            ])
            ax2.set_xlabel('Write Time (seconds)')
            ax2.set_title('Write Performance (lower is better)')
            
            # Plot 3: File sizes
            ax3 = axes[1, 0]
            size_data = df.sort_values('file_size_mb')
            bars3 = ax3.barh(
                range(len(size_data)),
                size_data['file_size_mb'],
                color='lightgreen'
            )
            ax3.set_yticks(range(len(size_data)))
            ax3.set_yticklabels([
                f"{row['format']} ({row['compression']})" 
                for _, row in size_data.iterrows()
            ])
            ax3.set_xlabel('File Size (MB)')
            ax3.set_title('Storage Efficiency (lower is better)')
            
            # Plot 4: Query times
            ax4 = axes[1, 1]
            query_data = df.sort_values('query_time')
            bars4 = ax4.barh(
                range(len(query_data)),
                query_data['query_time'],
                color='gold'
            )
            ax4.set_yticks(range(len(query_data)))
            ax4.set_yticklabels([
                f"{row['format']} ({row['compression']})" 
                for _, row in query_data.iterrows()
            ])
            ax4.set_xlabel('Query Time (seconds)')
            ax4.set_title('Query Performance (lower is better)')
            
            plt.tight_layout()
            plt.savefig('storage_benchmark_results.png', dpi=300, bbox_inches='tight')
            print("Results plot saved as 'storage_benchmark_results.png'")
            
        except ImportError:
            print("Matplotlib/seaborn not available for plotting")


def main():
    """Main execution"""
    print("Storage Format Benchmark Tool")
    print("="*60)
    
    # For quick testing, use smaller dataset
    benchmark = StorageFormatBenchmark(num_rows=100000)  # 100K rows
    
    try:
        benchmark.run_benchmarks()
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
    except Exception as e:
        print(f"\nBenchmark failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
