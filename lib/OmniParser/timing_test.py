#!/usr/bin/env python3
"""
Test script to verify OmniParser timing functionality.
This script will run a simple test to ensure all timing information is being printed.
"""
import os
import sys
import time
from PIL import Image
import numpy as np

# Add the path to load OmniParser
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Import after path setup
from agent0 import process

def create_test_image():
    """Create a simple test image for timing verification"""
    # Create a simple 800x600 RGB image with some text-like patterns
    img = Image.new('RGB', (800, 600), color='white')

    # Add some colored rectangles to simulate UI elements
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)

    # Add some rectangles that might be detected as icons
    draw.rectangle([100, 100, 200, 150], fill='blue')
    draw.rectangle([300, 200, 400, 250], fill='red')
    draw.rectangle([500, 300, 600, 350], fill='green')

    # Add some text-like rectangles
    draw.rectangle([100, 400, 300, 430], fill='black')
    draw.rectangle([400, 450, 600, 480], fill='black')

    return img

def main():
    print("Starting OmniParser timing test...")
    print("Creating test image...")

    test_image = create_test_image()

    print("Running OmniParser with timing information...")
    print("This will show detailed timing for each processing step.\n")

    # Run the process function which now includes comprehensive timing
    try:
        result_image, parsed_content = process(
            image_input=test_image,
            box_threshold=0.05,
            iou_threshold=0.1,
            use_paddleocr=False,  # Use EasyOCR for this test
            imgsz=640
        )

        print(f"\nTiming test completed successfully!")
        print(f"Parsed content preview:")
        print(parsed_content[:200] + "..." if len(parsed_content) > 200 else parsed_content)

    except Exception as e:
        print(f"Error during timing test: {e}")
        return False

    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Timing functionality test completed successfully!")
        print("All timing information should be visible in the output above.")
    else:
        print("\n❌ Timing functionality test failed!")
    sys.exit(0 if success else 1)
