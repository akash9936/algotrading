#!/usr/bin/env python3
"""Quick test of parameter optimizer"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

print("Testing parameter optimizer...")

try:
    from optimization.parameter_optimizer import ParameterOptimizer
    print("✓ Import successful")

    optimizer = ParameterOptimizer()
    print("✓ Optimizer initialized")

    # Test with very small sample
    params = optimizer.generate_parameter_grid(sample_size=5)
    print(f"✓ Generated {len(params)} parameter combinations")

    print("\nFirst combination:")
    for category, values in params[0].items():
        print(f"  {category}: {values}")

    print("\n✓ All tests passed!")

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
