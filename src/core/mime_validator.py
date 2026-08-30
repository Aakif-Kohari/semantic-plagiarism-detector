def validate_pdf_no_polyglot(file_bytes: bytes) -> bool:
    """
    Validates that a file claiming to be a PDF does not contain embedded 
    executable MZ headers or JAR manifest indicators (polyglot detection).
    """
    # Ensure it starts with standard PDF magic bytes
    if not file_bytes.startswith(b"%PDF-"):
        return False
        
    # Check for embedded DOS/Windows executable MZ header (PE headers)
    if b"MZ" in file_bytes[:1024]:
        return False
        
    # Check for embedded JAR/ZIP archive metadata or manifest indicators
    if b"META-INF/" in file_bytes or b"PK\x03\x04" in file_bytes[1024:]:
        return False
        
    return True
