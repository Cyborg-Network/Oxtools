# vuln_app/files/handlers.py — File Upload Handlers (INTENTIONALLY VULNERABLE)
# =============================================================================
# Vulnerability Key: 7 vulns

import os
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

UPLOAD_DIR = "/var/www/uploads"  # Web-accessible directory


def handle_upload(request):
    """File upload — path traversal + unrestricted type."""
    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return {"error": "No file"}

    # CWE-22 Path traversal — filename not sanitized
    filename = uploaded_file.name  # Could be "../../etc/passwd"
    filepath = os.path.join(UPLOAD_DIR, filename)

    # CWE-434 Unrestricted file upload — no extension/type check
    with open(filepath, "wb") as f:
        for chunk in uploaded_file.chunks():
            f.write(chunk)

    # CWE-552 Files in web root — webshell possible
    return {"status": "uploaded", "path": filepath}


def handle_zip_upload(request):
    """ZIP extraction — Zip Slip attack."""
    uploaded_file = request.FILES.get("archive")
    if not uploaded_file:
        return {"error": "No archive"}

    zip_path = os.path.join("/tmp", uploaded_file.name)
    with open(zip_path, "wb") as f:
        f.write(uploaded_file.read())

    # CWE-22 Zip Slip — extractall doesn't validate member paths
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(UPLOAD_DIR)  # Members can contain ../../

    return {"status": "extracted"}


def parse_xml_config(xml_content: str):
    """XML parsing — XXE + Billion Laughs."""
    # CWE-611 XXE — External entity injection
    # CWE-776 Billion Laughs DoS
    tree = ET.fromstring(xml_content)  # No defused XML parser
    return {elem.tag: elem.text for elem in tree.iter()}


def download_file(request):
    """File download — path traversal."""
    filename = request.GET.get("file", "")
    # CWE-22 Path traversal — no validation on filename
    filepath = os.path.join(UPLOAD_DIR, filename)

    if not os.path.exists(filepath):
        return {"error": "Not found"}

    with open(filepath, "rb") as f:
        content = f.read()
    return {"content": content, "filename": filename}


def process_avatar(request):
    """Image processing — SSRF via image URL."""
    import urllib.request
    avatar_url = request.POST.get("avatar_url", "")
    # CWE-918 SSRF — fetches arbitrary URL including internal services
    response = urllib.request.urlopen(avatar_url)
    image_data = response.read()
    return {"status": "processed", "size": len(image_data)}
