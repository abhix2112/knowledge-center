"""Upload a document and turn it into a draft article."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, UploadFile, status

from knowledge_center.articles import get_visible_article, insert_article
from knowledge_center.auth import CurrentUser
from knowledge_center.config import settings
from knowledge_center.db import DbConn
from knowledge_center.extract import SUPPORTED_EXTENSIONS, UnsupportedFile, extract_text, split_title
from knowledge_center.schemas import DocumentOut, UploadResult

router = APIRouter(prefix="/documents", tags=["documents"])

DOCUMENT_COLUMNS = "id, filename, content_type, size_bytes, article_id, created_at"


# A plain `def` (not async): reading the file, parsing a PDF and querying the
# database all block. FastAPI runs `def` endpoints in a thread pool, so they
# don't freeze the server for other users.
@router.post("", status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile,
    user: CurrentUser,
    conn: DbConn,
    category: str = Form(default="General", min_length=1, max_length=50),
) -> UploadResult:
    filename = Path(file.filename or "upload").name
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Upload a PDF, Word (.docx), Markdown or text file. Got: {extension or 'no extension'}",
        )

    # Read at most one byte more than the limit: enough to know it's too big,
    # without loading a huge file into memory.
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"File is larger than {settings.max_upload_mb} MB",
        )

    try:
        text = extract_text(data, extension)
    except UnsupportedFile as error:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(error)) from None
    if not text.strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "No text found in this file. Scanned PDFs (images of text) aren't supported yet.",
        )

    # Save under a random name. Never use the uploaded filename as a path:
    # a name like "../../etc/passwd" could write outside the upload folder.
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    storage_path = settings.upload_dir / f"{uuid4()}{extension}"
    storage_path.write_bytes(data)

    title, body = split_title(text, fallback_title=Path(filename).stem)
    article_id = insert_article(
        conn,
        owner_id=user.id,
        title=title[:200],
        body=body,
        category=category,
        source="upload",
    )
    document = conn.execute(
        f"""
        INSERT INTO documents (filename, storage_path, content_type, size_bytes, uploaded_by, article_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING {DOCUMENT_COLUMNS}
        """,
        (filename, str(storage_path), file.content_type or "application/octet-stream",
         len(data), user.id, article_id),
    ).fetchone()

    return UploadResult(
        document=DocumentOut(**document),
        article=get_visible_article(conn, article_id, user),
    )


@router.get("")
def list_documents(user: CurrentUser, conn: DbConn) -> list[DocumentOut]:
    rows = conn.execute(
        f"SELECT {DOCUMENT_COLUMNS} FROM documents WHERE uploaded_by = %s ORDER BY created_at DESC",
        (user.id,),
    ).fetchall()
    return [DocumentOut(**row) for row in rows]
