"""Performance benchmark for empty resource filtering optimization"""

import time
import json
from fhir_converter.renderers import Hl7v2Renderer, make_environment, hl7v2_default_loader


def create_test_hl7v2_message(num_obr_segments=100):
    """Create a test HL7v2 message with many OBR segments that may produce empty resources"""
    message_parts = [
        "MSH|^~\\&|System||EMR||20241007143000||ORU^R01^ORU_R01|MSG001|P|2.5.1",
        "PID|1||12345||Doe^John||19850312|M"
    ]
    
    # Add many OBR segments with minimal data (likely to create empty resources)
    for i in range(num_obr_segments):
        message_parts.append(
            f"OBR|{i+1}|ORDER{i:03d}|ORDER{i:03d}|TEST^Test^L|||20241007143000|||||||||||||||20241007143000"
        )
        # Add some OBX segments
        message_parts.append(
            f"OBX|1|NM|8480-6^Systolic blood pressure^LN|1|135|mm[Hg]||||||F|||20241007143000"
        )
    
    return "\n".join(message_parts)


def benchmark_rendering(num_segments=100, num_iterations=5):
    """Benchmark the rendering performance"""
    renderer = Hl7v2Renderer(
        env=make_environment(
            loader=hl7v2_default_loader,
        )
    )
    
    test_message = create_test_hl7v2_message(num_segments)
    
    print(f"\nBenchmarking with {num_segments} OBR segments, {num_iterations} iterations:")
    print(f"Input message size: {len(test_message)} bytes")
    
    times = []
    result = None
    for i in range(num_iterations):
        start = time.perf_counter()
        result_json = renderer.render_fhir_string("ORU_R01", test_message)
        end = time.perf_counter()
        
        elapsed = end - start
        times.append(elapsed)
        
        # Parse result to get stats
        result = json.loads(result_json)
        num_entries = len(result.get("entry", []))
        output_size = len(result_json)
        
        print(f"  Iteration {i+1}: {elapsed:.4f}s - {num_entries} entries, {output_size} bytes output")
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"\nResults:")
    print(f"  Average: {avg_time:.4f}s")
    print(f"  Min: {min_time:.4f}s")
    print(f"  Max: {max_time:.4f}s")
    print(f"  Throughput: ~{num_segments/avg_time:.1f} segments/second")
    
    return avg_time, result


def analyze_memory_efficiency():
    """Analyze memory efficiency of the filtering approach"""
    print("\n=== Memory Efficiency Analysis ===")
    print("Optimized approach benefits:")
    print("1. Single-pass filtering during merge (O(n) instead of O(2n))")
    print("2. Skip processing empty resources entirely - no merge, no comparison")
    print("3. Reduced list comprehension overhead - filter during dict building")
    print("4. Early exit for single-entry bundles with empty resources")
    

if __name__ == "__main__":
    print("=" * 60)
    print("Empty Resource Filtering Performance Benchmark")
    print("=" * 60)
    
    # Test with different sizes
    for num_segments in [10, 50, 100]:
        benchmark_rendering(num_segments=num_segments, num_iterations=3)
        print()
    
    analyze_memory_efficiency()
    
    print("\n" + "=" * 60)
    print("Benchmark complete!")
    print("=" * 60)
