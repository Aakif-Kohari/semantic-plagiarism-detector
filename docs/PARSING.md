# Document Parsing Guidelines

## Supported Formats & File Size Limits

| Extension | Parser Library | OCR Support | Limitations / Max Size |
|---|---|---|---|
| `.pdf` | PyMuPDF / pdfplumber | Yes (Tesseract) | Max 50 MB; scanned pages require OCR |
| `.docx` | python-docx | No | Max 25 MB |
| `.txt` | Native Python | No | Max 10 MB; plain text only |
| `.rtf` | striprtf / native | No | Max 10 MB |
| `.epub` | ebooklib | No | Max 20 MB |

## Extraction Options

* **Text Parsing:** Extract raw text from standard documents.
* **OCR Fallback:** Automated OCR fallback for scanned PDF documents.

## OCR DPI Settings

* **Default DPI:** 300 DPI
* **Recommended Range:** 150 - 300 DPI for optimal accuracy vs performance.