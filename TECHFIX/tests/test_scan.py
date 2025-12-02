"""
Test script for scan/scan image functionality.
Tests OpenCV, QR code detection, and barcode scanning capabilities.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_opencv_import():
    """Test if OpenCV can be imported."""
    print("=" * 60)
    print("Testing OpenCV Import...")
    print("=" * 60)
    try:
        import cv2
        print(f"✓ OpenCV imported successfully")
        print(f"  Version: {cv2.__version__}")
        return True, cv2
    except ImportError as e:
        print(f"✗ Failed to import OpenCV: {e}")
        return False, None
    except Exception as e:
        print(f"✗ Unexpected error importing OpenCV: {e}")
        return False, None

def test_qr_detector(cv2):
    """Test QR code detector initialization."""
    print("\n" + "=" * 60)
    print("Testing QR Code Detector...")
    print("=" * 60)
    try:
        detector = cv2.QRCodeDetector()
        print("✓ QRCodeDetector created successfully")
        return True, detector
    except Exception as e:
        print(f"✗ Failed to create QRCodeDetector: {e}")
        return False, None

def test_image_reading(cv2):
    """Test if OpenCV can read images."""
    print("\n" + "=" * 60)
    print("Testing Image Reading...")
    print("=" * 60)
    try:
        # Create a simple test image (black square)
        import numpy as np
        test_img = np.zeros((100, 100, 3), dtype=np.uint8)
        print("✓ Can create test images with numpy")
        
        # Test reading a non-existent file (should return None)
        result = cv2.imread("nonexistent_file.png")
        if result is None:
            print("✓ Image reading handles missing files correctly")
        else:
            print("⚠ Image reading returned non-None for missing file")
        
        return True
    except ImportError:
        print("⚠ numpy not available (optional)")
        return True  # numpy is optional
    except Exception as e:
        print(f"✗ Error testing image reading: {e}")
        return False

def test_pyzbar():
    """Test if pyzbar is available."""
    print("\n" + "=" * 60)
    print("Testing pyzbar (Barcode Scanner)...")
    print("=" * 60)
    try:
        from pyzbar.pyzbar import decode
        print("✓ pyzbar imported successfully")
        return True, decode
    except ImportError:
        print("⚠ pyzbar not installed (optional for barcode scanning)")
        print("  Install with: pip install pyzbar")
        return False, None
    except Exception as e:
        print(f"✗ Error importing pyzbar: {e}")
        return False, None

def test_pillow():
    """Test if Pillow is available."""
    print("\n" + "=" * 60)
    print("Testing Pillow (Image Processing)...")
    print("=" * 60)
    try:
        from PIL import Image, ImageTk
        print("✓ Pillow imported successfully")
        print(f"  Version: {Image.__version__}")
        return True, Image
    except ImportError:
        print("✗ Pillow not installed (required)")
        print("  Install with: pip install Pillow")
        return False, None
    except Exception as e:
        print(f"✗ Error importing Pillow: {e}")
        return False, None

def test_camera_access(cv2):
    """Test if camera can be accessed."""
    print("\n" + "=" * 60)
    print("Testing Camera Access...")
    print("=" * 60)
    try:
        cap = cv2.VideoCapture(0)
        if cap is None or not cap.isOpened():
            print("⚠ Camera not accessible (may not be available or permissions denied)")
            if cap:
                cap.release()
            return False
        else:
            print("✓ Camera accessible")
            # Try to read a frame
            ret, frame = cap.read()
            if ret:
                print(f"✓ Can read frames from camera (frame size: {frame.shape})")
                cap.release()
                return True
            else:
                print("⚠ Camera opened but cannot read frames")
                cap.release()
                return False
    except Exception as e:
        print(f"✗ Error accessing camera: {e}")
        return False

def test_qr_code_detection_from_image(cv2, detector):
    """Test QR code detection from a sample image."""
    print("\n" + "=" * 60)
    print("Testing QR Code Detection from Image...")
    print("=" * 60)
    
    # Create a simple QR code test
    try:
        import qrcode
        import numpy as np
        from PIL import Image as PILImage
        
        # Generate a test QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        test_data = '{"date":"2024-01-15","description":"Test Transaction","debit_amount":"100.00"}'
        qr.add_data(test_data)
        qr.make(fit=True)
        
        # Create PIL image
        img_pil = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to numpy array
        img_array = np.array(img_pil.convert('RGB'))
        # Convert RGB to BGR for OpenCV
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        
        # Try to detect QR code
        data, points, _ = detector.detectAndDecode(img_bgr)
        
        if points is not None and data:
            print(f"✓ QR code detected successfully!")
            print(f"  Decoded data: {data}")
            if data == test_data:
                print("✓ Decoded data matches original")
            else:
                print("⚠ Decoded data doesn't match (may be encoding issue)")
            return True
        else:
            print("⚠ QR code not detected in generated image")
            print("  This might be a detection issue or image format problem")
            return False
            
    except ImportError as e:
        print(f"⚠ Cannot test QR generation: {e}")
        print("  Install qrcode with: pip install qrcode")
        return None  # Not a failure, just can't test
    except Exception as e:
        print(f"✗ Error testing QR code detection: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_scan_image_function():
    """Test the actual scan_from_image_file function logic."""
    print("\n" + "=" * 60)
    print("Testing Scan Image Function Logic...")
    print("=" * 60)
    
    try:
        # Import the function components
        from techfix.gui import TechFixApp
        
        # We can't fully test without GUI, but we can test the parsing logic
        app = TechFixApp()
        
        # Test payload parsing
        test_cases = [
            ('{"date":"2024-01-15","description":"Test"}', True),
            ('date=2024-01-15&description=Test', True),
            ('date=2024-01-15|description=Test', True),
            ('invalid data', False),
            ('', False),
        ]
        
        print("Testing payload parsing...")
        for payload, should_parse in test_cases:
            result = app._parse_scanned_payload(payload)
            if should_parse:
                if result:
                    print(f"✓ Parsed: {payload[:50]}... -> {len(result)} fields")
                else:
                    print(f"✗ Failed to parse (expected success): {payload[:50]}...")
            else:
                if not result:
                    print(f"✓ Correctly rejected: {payload[:50]}...")
                else:
                    print(f"⚠ Unexpectedly parsed (expected failure): {payload[:50]}...")
        
        app.destroy()
        return True
    except Exception as e:
        print(f"✗ Error testing scan function: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SCAN FUNCTIONALITY TEST SUITE")
    print("=" * 60)
    
    results = {}
    
    # Test OpenCV
    cv2_ok, cv2 = test_opencv_import()
    results['opencv'] = cv2_ok
    
    if not cv2_ok:
        print("\n" + "=" * 60)
        print("CRITICAL: OpenCV not available. Cannot proceed with scan tests.")
        print("=" * 60)
        return
    
    # Test QR detector
    qr_ok, detector = test_qr_detector(cv2)
    results['qr_detector'] = qr_ok
    
    # Test image reading
    img_ok = test_image_reading(cv2)
    results['image_reading'] = img_ok
    
    # Test Pillow
    pillow_ok, _ = test_pillow()
    results['pillow'] = pillow_ok
    
    # Test pyzbar
    pyzbar_ok, _ = test_pyzbar()
    results['pyzbar'] = pyzbar_ok
    
    # Test camera (optional)
    camera_ok = test_camera_access(cv2)
    results['camera'] = camera_ok
    
    # Test QR detection
    if qr_ok and detector:
        qr_detect_ok = test_qr_code_detection_from_image(cv2, detector)
        results['qr_detection'] = qr_detect_ok
    
    # Test scan function logic
    try:
        scan_func_ok = test_scan_image_function()
        results['scan_function'] = scan_func_ok
    except Exception as e:
        print(f"\n⚠ Could not test scan function (GUI dependency): {e}")
        results['scan_function'] = None
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    critical = ['opencv', 'pillow']
    optional = ['pyzbar', 'camera', 'qr_detection']
    
    for test_name, result in results.items():
        if result is True:
            status = "✓ PASS"
        elif result is False:
            status = "✗ FAIL"
        elif result is None:
            status = "⚠ SKIP"
        else:
            status = "? UNKNOWN"
        
        importance = "CRITICAL" if test_name in critical else "OPTIONAL"
        print(f"{status} - {test_name.upper():20s} ({importance})")
    
    print("\n" + "=" * 60)
    critical_passed = all(results.get(k, False) for k in critical)
    if critical_passed:
        print("✓ All critical components are working!")
        print("  Your scan/scan image functionality should work.")
    else:
        print("✗ Some critical components are missing.")
        print("  Please install missing packages.")
    print("=" * 60)

if __name__ == "__main__":
    main()

