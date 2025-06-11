from fastapi import HTTPException, status, UploadFile
from typing import List
from backend.services.document_service import (
    validate_file_service,
    save_upload_file_service,
    parse_document_content_service,
)
from pathlib import Path

async def upload_document_controller(files: List[UploadFile], current_user):
    if not files or len(files) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files uploaded."
        )

    metadata_list = []
    temp_files = []
    parsed_docs = []

    for upload_file in files:
        validate_file_service(upload_file)
        try:
            temp_path = save_upload_file_service(upload_file)
            temp_files.append(temp_path)
            size = temp_path.stat().st_size

            try:
                raw_text = parse_document_content_service(temp_path, upload_file.content_type)
                parsed_docs.append({
                    "filename": upload_file.filename,
                    "content_type": upload_file.content_type,
                    "size": size,
                    "raw_text": raw_text,
                })
            except HTTPException as e:
                for f in temp_files:
                    try:
                        f.unlink(missing_ok=True)
                    except Exception:
                        pass
                raise

            metadata_list.append({
                "filename": upload_file.filename,
                "content_type": upload_file.content_type,
                "size": size,
                "text_preview": raw_text[:200]
            })

        except Exception as e:
            for f in temp_files:
                try:
                    f.unlink(missing_ok=True)
                except Exception:
                    pass
            raise

    return {"files": metadata_list}
