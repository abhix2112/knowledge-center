from io import BytesIO

from docx import Document


def upload(client, headers, filename: str, data: bytes, category: str = "General"):
    return client.post(
        "/api/documents",
        files={"file": (filename, data)},
        data={"category": category},
        headers=headers,
    )


def make_pdf(text: str) -> bytes:
    """Build a tiny one-page PDF containing `text`."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R"
        b" /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n%s\nendobj\n" % (number, body)
    xref_at = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    pdf += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref_at)
    return pdf


def test_markdown_upload_uses_first_heading_as_title(client, alice):
    response = upload(client, alice, "guide.md", b"# Printer setup\n\nAdd the printer.", "Hardware")
    assert response.status_code == 201
    article = response.json()["article"]
    assert article["title"] == "Printer setup"
    assert article["body"] == "Add the printer."
    assert article["status"] == "draft"
    assert article["source"] == "upload"
    assert article["category"] == "Hardware"

    documents = client.get("/api/documents", headers=alice).json()
    assert documents[0]["filename"] == "guide.md"
    assert documents[0]["article_id"] == article["id"]


def test_text_upload_without_heading_uses_filename(client, alice):
    article = upload(client, alice, "wifi-notes.txt", b"Join the staff network.").json()["article"]
    assert article["title"] == "wifi-notes"


def test_docx_upload_keeps_headings(client, alice):
    doc = Document()
    doc.add_heading("Expense policy", level=1)
    doc.add_paragraph("Submit receipts within 30 days.")
    doc.add_heading("Limits", level=2)
    buffer = BytesIO()
    doc.save(buffer)

    article = upload(client, alice, "policy.docx", buffer.getvalue()).json()["article"]
    assert article["title"] == "Expense policy"
    assert "## Limits" in article["body"]


def test_pdf_upload(client, alice):
    response = upload(client, alice, "vpn.pdf", make_pdf("Connect to the VPN before using email."))
    assert response.status_code == 201
    assert "Connect to the VPN" in response.json()["article"]["body"]


def test_rejects_unsupported_and_fake_files(client, alice):
    assert upload(client, alice, "virus.exe", b"MZ...").status_code == 415
    assert upload(client, alice, "fake.pdf", b"not a pdf").status_code == 415


def test_rejects_files_without_text(client, alice):
    assert upload(client, alice, "empty.md", b"   \n").status_code == 422
