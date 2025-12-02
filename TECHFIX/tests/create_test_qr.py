"""
Create a test QR code image for testing scan functionality.
"""

import qrcode
from PIL import Image

# Create a test transaction data in the format your app expects
test_data = {
    "date": "2024-01-15",
    "description": "Test Transaction from QR Code",
    "debit_amount": "150.00",
    "credit_amount": "150.00",
    "debit_account": "Cash",
    "credit_account": "Revenue",
    "document_ref": "QR-TEST-001",
    "memo": "This is a test QR code for scanning"
}

# Convert to JSON string (one format your app accepts)
json_data = str(test_data).replace("'", '"')

# Also create a key=value format (alternative format)
kv_data = "&".join([f"{k}={v}" for k, v in test_data.items()])

print("Creating test QR codes...")
print(f"JSON format: {json_data[:80]}...")
print(f"Key=Value format: {kv_data[:80]}...")

# Create QR code with JSON format
qr_json = qrcode.QRCode(version=1, box_size=10, border=4)
qr_json.add_data(json_data)
qr_json.make(fit=True)
img_json = qr_json.make_image(fill_color="black", back_color="white")
img_json.save("test_qr_json.png")
print("✓ Created test_qr_json.png")

# Create QR code with key=value format
qr_kv = qrcode.QRCode(version=1, box_size=10, border=4)
qr_kv.add_data(kv_data)
qr_kv.make(fit=True)
img_kv = qr_kv.make_image(fill_color="black", back_color="white")
img_kv.save("test_qr_kv.png")
print("✓ Created test_qr_kv.png")

print("\nTest QR codes created! You can use these to test the 'Scan Image' button.")
print("Try scanning test_qr_json.png or test_qr_kv.png in your application.")

