import hashlib
from pathlib import Path


def compute_sha256(file_path: Path, chunk_size: int = 65536) -> str:
    """
    Computes the SHA-256 hash of a file efficiently by streaming chunks.
    
    Args:
        file_path: Path to the target file.
        chunk_size: Byte size for buffered reads (default: 64 KB).
        
    Returns:
        Hexadecimal SHA-256 string.
    """
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            sha256.update(chunk)
    return sha256.hexdigest()
