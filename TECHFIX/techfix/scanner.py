from __future__ import annotations

import os
import json
from datetime import datetime


def _sample_transactions() -> list[dict]:
    today = datetime.now().strftime('%Y-%m-%d')
    return [
        {
            'date': today,
            'source_type': 'Receipt',
            'document_ref': '20050',
            'external_ref': 'POS-9847',
            'description': 'Office supplies - staplers',
            'debit_amount': 49.99,
            'credit_amount': 49.99,
            'memo': 'Cash purchase at Stationers Co.',
        },
        {
            'date': today,
            'source_type': 'Invoice',
            'document_ref': '10026',
            'external_ref': 'INV-10026',
            'description': 'Client services - November',
            'debit_amount': 1200.00,
            'credit_amount': 1200.00,
            'memo': 'Billed to Acme Corp.',
        },
    ]


def generate_mock_codes(output_dir: str) -> list[str]:
    files: list[str] = []
    txns = _sample_transactions()
    os.makedirs(output_dir, exist_ok=True)
    # Try to create QR codes
    try:
        import qrcode
        from PIL import Image
        for i, t in enumerate(txns, start=1):
            payload = json.dumps(t, ensure_ascii=False)
            qr = qrcode.QRCode(version=None, box_size=10, border=2)
            qr.add_data(payload)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            path = os.path.join(output_dir, f"txn_{i}_qr.png")
            img.save(path)
            files.append(path)
    except Exception:
        # Fallback: write payload as .txt
        for i, t in enumerate(txns, start=1):
            payload = json.dumps(t, ensure_ascii=False)
            path = os.path.join(output_dir, f"txn_{i}_qr.txt")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(payload)
            files.append(path)

    # Try to create barcodes (Code128) with compact key=value pairs
    try:
        import barcode
        from barcode.writer import ImageWriter
        for i, t in enumerate(txns, start=1):
            kv = [
                f"date={t.get('date','')}",
                f"source={t.get('source_type','')}",
                f"doc={t.get('document_ref','')}",
                f"amount={t.get('debit_amount','')}",
                f"desc={t.get('description','')[:24]}",
            ]
            data = '&'.join(kv)
            code128 = barcode.get('code128', data, writer=ImageWriter())
            path = os.path.join(output_dir, f"txn_{i}_code128")
            filename = code128.save(path)
            files.append(filename)
    except Exception:
        # Fallback: write payload as .txt
        for i, t in enumerate(txns, start=1):
            kv = [
                f"date={t.get('date','')}",
                f"source={t.get('source_type','')}",
                f"doc={t.get('document_ref','')}",
                f"amount={t.get('debit_amount','')}",
            ]
            data = '&'.join(kv)
            path = os.path.join(output_dir, f"txn_{i}_code128.txt")
            with open(path, 'w', encoding='utf-8') as f:
                f.write(data)
            files.append(path)

    return files

