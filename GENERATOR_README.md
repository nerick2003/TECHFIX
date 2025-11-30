# Mock Data Generator

A GUI application to generate large quantities of mock data files for TechFix testing.

## Features

- **mock_codes**: Generates QR codes and barcodes in PNG format with corresponding TXT files containing JSON data
- **mock_codes_jpg**: Generates barcodes in JPG format
- **SampleSourceDocs**: Generates source documents with JSON sidecar files containing transaction data

## Requirements

Install the required packages:

```bash
pip install qrcode python-barcode Pillow
```

Or install all TechFix requirements:

```bash
pip install -r TECHFIX/requirements.txt
```

## Usage

1. Run the generator:
   ```bash
   python generate_mock_data.py
   ```

2. In the GUI:
   - Enter the number of files you want to generate (e.g., 100000)
   - Select which types of files to generate (checkboxes)
   - Click "Generate Files"
   - Monitor progress in the status window

## Output Structure

### mock_codes/
- `txn_{id}_qr.png` - QR code image
- `txn_{id}_qr.txt` - JSON data for QR code
- `txn_{id}_code128.png` - Barcode image
- `txn_{id}_code128.txt` - JSON data for barcode

### mock_codes_jpg/
- `barcode_{id:05d}.jpg` - Barcode image in JPG format

### SampleSourceDocs/
- `YYYY-MM-DD_{Type}_{DocNo}_{Description}.{ext}` - Mock document files
- `YYYY-MM-DD_{Type}_{DocNo}_{Description}.json` - JSON sidecar with transaction data

## Generated Data

The generator creates realistic transaction data with:
- Random dates within a 2-year range
- Appropriate account mappings based on transaction type
- Realistic amounts ($10 - $5,000)
- Proper document references and descriptions
- All standard source types: Invoice, Receipt, Bank, Adjust, Payroll, Other

## Notes

- Generating 100,000 files may take some time (several minutes to hours depending on your system)
- Files are generated in the same directory as the script
- Existing files with the same names will be overwritten
- Progress is shown in real-time in the status window

