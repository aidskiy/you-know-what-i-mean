#!/usr/bin/env python3
"""Quick test of fal.ai image generation."""

import os
from pathlib import Path

# Test fal.ai image generation
try:
    from fal_image import generate_image
    
    # Create test directory
    test_dir = Path("test_output")
    test_dir.mkdir(exist_ok=True)
    
    # Generate a test image
    print("Testing fal.ai image generation...")
    result_path = generate_image(
        "A simple test image of a red apple on a white background, minimal style",
        test_dir / "test_apple.png"
    )
    
    print(f"✅ Success! Image generated at: {result_path}")
    print(f"File size: {result_path.stat().st_size} bytes")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("\nMake sure FAL_API_KEY is set in your .env file")
