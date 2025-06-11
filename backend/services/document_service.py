from fastapi import HTTPException, status, UploadFile
from pathlib import Path
import tempfile
import shutil

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain"
}

def validate_file_service(upload_file: UploadFile):
    if upload_file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {upload_file.content_type}"
        )

def save_upload_file_service(upload_file: UploadFile) -> Path:
    try:
        suffix = Path(upload_file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(upload_file.file, tmp)
            temp_path = Path(tmp.name)
        return temp_path
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save uploaded file: {str(e)}"
        )

def parse_document_content_service(path: Path, mime_type: str) -> str:
    try:
        if mime_type == "application/pdf":
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                texts = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        texts.append(page_text)
            raw_text = "\n".join(texts)
        elif mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            from docx import Document
            doc = Document(str(path))
            raw_text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
        elif mime_type in ("text/plain", "text/markdown"):
            raw_text = path.read_text(encoding="utf-8")
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported MIME type for parsing: {mime_type}"
            )
        if not raw_text or not raw_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No text extracted"
            )
        return raw_text
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document parsing error: {str(e)}"
        )
