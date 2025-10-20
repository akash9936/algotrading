#!/usr/bin/env python3
"""Minimal test"""
import sys
sys.path.insert(0, 'src')

print("Step 1: Testing import...")
try:
    from optimization.parameter_optimizer import ParameterOptimizer
    print("✓ Import OK")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

print("\nStep 2: Creating optimizer...")
try:
    opt = ParameterOptimizer()
    print("✓ Optimizer created")
except Exception as e:
    print(f"✗ Failed: {e}")
    sys.exit(1)

print("\nStep 3: Checking config...")
print(f"✓ Config has {len(opt.config)} categories")

print("\n✓ STEP 2 COMPLETE - Parameter optimizer working!")
