"""
Test the scan from image file functionality directly.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_scan_image_direct():
    """Test scanning an image file directly using the same logic as the app."""
    print("=" * 60)
    print("Testing Scan Image File Functionality")
    print("=" * 60)
    
    # Test with the QR code we created
    test_image = os.path.join(os.path.dirname(__file__), "test_qr_json.png")
    
    if not os.path.exists(test_image):
        print(f"✗ Test image not found: {test_image}")
        return False
    
    print(f"Testing with: {test_image}")
    
    payload = None
    
    # Try pyzbar first (same as app)
    try:
        from pyzbar.pyzbar import decode as zbar_decode
        from PIL import Image
        img = Image.open(test_image)
        res = zbar_decode(img)
        if res:
            try:
                payload = res[0].data.decode('utf-8', errors='replace')
                print(f"✓ pyzbar detected: {payload[:80]}...")
            except Exception:
                payload = None
    except Exception:
        print("⚠ pyzbar not available or failed")
    
    # Try OpenCV (same as app)
    if payload is None:
        try:
            import cv2
            detector = cv2.QRCodeDetector()
            im = cv2.imread(test_image)
            if im is not None and im.size > 0:
                # Try detection on color image first
                data, points, _ = detector.detectAndDecode(im)
                if points is not None and data and len(data) > 0:
                    payload = data
                    print(f"✓ OpenCV (color) detected: {payload[:80]}...")
                else:
                    # Try with grayscale for better detection
                    try:
                        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
                        data, points, _ = detector.detectAndDecode(gray)
                        if points is not None and data and len(data) > 0:
                            payload = data
                            print(f"✓ OpenCV (grayscale) detected: {payload[:80]}...")
                    except Exception as e:
                        print(f"⚠ Grayscale detection failed: {e}")
            else:
                print("✗ OpenCV could not read image file")
        except ImportError:
            print("✗ OpenCV not available")
        except Exception as e:
            print(f"✗ OpenCV error: {e}")
    
    if payload:
        print(f"\n✓ SUCCESS: Payload detected!")
        print(f"  Full payload: {payload}")
        
        # Test parsing (same as app)
        try:
            from techfix.gui import TechFixApp
            app = TechFixApp()
            data = app._parse_scanned_payload(payload)
            if data:
                print(f"✓ Payload parsed successfully: {len(data)} fields")
                for key, value in data.items():
                    print(f"  {key}: {value}")
            else:
                print("✗ Payload parsing failed")
            app.destroy()
        except Exception as e:
            print(f"⚠ Could not test parsing: {e}")
        
        return True
    else:
        print("\n✗ FAILED: No payload detected from image")
        return False

if __name__ == "__main__":
    success = test_scan_image_direct()
    sys.exit(0 if success else 1)

