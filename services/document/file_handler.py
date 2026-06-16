import os
import uuid
from typing import Tuple
from fastapi import UploadFile, HTTPException
from config import UPLOAD_DIR


ALLOWED_EXTENSIONS = {".doc", ".docx", ".pdf"}


def validate_file(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename or "unknown")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' is not supported. Only .doc, .docx, .pdf are allowed."
        )
    return ext


async def save_upload(file: UploadFile) -> Tuple[str, str, str]:
    ext = validate_file(file)
    contract_id = str(uuid.uuid4())
    safe_filename = f"{contract_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return contract_id, file_path, ext
