#!/usr/bin/env python3
"""Test parameter grid generation"""
import sys
sys.path.insert(0, 'src')

from optimization.parameter_optimizer import ParameterOptimizer
import json

print("="*70)
print("PARAMETER GRID GENERATION TEST")
print("="*70)

# Create optimizer
opt = ParameterOptimizer()

print("\n1. Default Configuration:")
for category, params in opt.config.items():
    total = 1
    for param, values in params.items():
        total *= len(values)
    print(f"   {category}: {total:,} combinations")

print("\n2. Generating 10 sample combinations...")
grids = opt.generate_parameter_grid(sample_size=10)
print(f"   ✓ Generated {len(grids)} combinations")

print("\n3. First combination structure:")
print(json.dumps(grids[0], indent=2))

print("\n4. Flattened format (for CSV storage):")
flat = {}
for category, values in grids[0].items():
    for param, value in values.items():
        flat[f"{category}_{param}"] = value

for key in list(flat.keys())[:10]:
    print(f"   {key}: {flat[key]}")
print(f"   ... ({len(flat)} total parameters)")

print("\n" + "="*70)
print("✓ PARAMETER GRID GENERATION WORKING!")
print("="*70)
print("\nNext: Ready for STEP 3 - Multi-Strategy Testing")
