import defusedxml.ElementTree as ET
from typing import Optional

ALLOWED_MIME_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/svg+xml"
}

def validate_magic_headers(file_bytes: bytes, mime_type: str) -> bool:
    """Validate file content against expected magic bytes / signatures."""
    if mime_type == "image/png":
        return file_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    elif mime_type == "image/jpeg":
        return file_bytes.startswith(b"\xff\xd8\xff")
    elif mime_type == "image/webp":
        # Check RIFF container and WEBP signature
        return len(file_bytes) >= 12 and file_bytes.startswith(b"RIFF") and file_bytes[8:12] == b"WEBP"
    elif mime_type == "image/svg+xml":
        return validate_svg_content(file_bytes)
    return False

def validate_svg_content(file_bytes: bytes) -> bool:
    """Safely parse SVG using defusedxml and check for forbidden script tags."""
    try:
        # Parse safely to prevent XXE / entity expansion attacks
        root = ET.fromstring(file_bytes)
        
        # Check namespace or tag name contains svg
        if not root.tag.endswith("svg"):
            return False
            
        # Inspect all elements for embedded script tags or javascript URIs
        for elem in root.iter():
            # Strip namespace from tag if present
            tag_name = elem.tag.split("}")[-1].lower()
            if tag_name == "script":
                return False
                
            # Check for javascript: protocols in attributes
            for attr_val in elem.attrib.values():
                if isinstance(attr_val, str) and "javascript:" in attr_val.lower():
                    return False 
                    
        return True
    except Exception:
        # If XML parsing fails, it's not a valid SVG
        return False