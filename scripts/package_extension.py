#!/usr/bin/env python3
"""
Packages the Authentica Manifest V3 Chrome Extension into a distributable zip archive
and saves it in frontend/public/authentica-extension.zip for 1-click web downloads.
"""

import os
import zipfile
from pathlib import Path

def package_extension():
    root_dir = Path(__file__).resolve().parent.parent
    extension_dir = root_dir / "extension"
    public_dir = root_dir / "frontend" / "public"
    public_dir.mkdir(parents=True, exist_ok=True)
    target_zip = public_dir / "authentica-extension.zip"

    if not extension_dir.is_dir():
        print(f"Error: Extension directory not found at {extension_dir}")
        return

    file_count = 0
    with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(extension_dir):
            for file in files:
                # Ignore system files
                if file.startswith(".") or file.endswith(".pyc"):
                    continue
                full_path = Path(root) / file
                arcname = full_path.relative_to(extension_dir)
                zipf.write(full_path, arcname)
                file_count += 1

    print(f"Successfully packaged {file_count} extension files into {target_zip} ({target_zip.stat().st_size / 1024:.1f} KB)")

if __name__ == "__main__":
    package_extension()

