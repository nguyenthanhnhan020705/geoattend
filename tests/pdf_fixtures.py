"""Synthetic PDFs shared by report browser tests; no AI dependency."""

def text_pdf(text='Weekly report: completed API tests.', pages=1):
    # Valid synthetic PDF, no personal data or external font dependency.
    objects = ['<< /Type /Catalog /Pages 2 0 R >>',
               '<< /Type /Pages /Kids [' + ' '.join(f'{4+i*2} 0 R' for i in range(pages)) + f'] /Count {pages} >>',
               '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
    for _ in range(pages):
        content_id = len(objects) + 2
        objects.append(f'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>')
        stream = f'BT /F1 12 Tf 50 780 Td ({text}) Tj ET'
        objects.append(f'<< /Length {len(stream)} >>\nstream\n{stream}\nendstream')
    out = bytearray(b'%PDF-1.4\n')
    offsets = [0]
    for n, obj in enumerate(objects, 1):
        offsets.append(len(out))
        out.extend(f'{n} 0 obj\n{obj}\nendobj\n'.encode())
    xref = len(out)
    out.extend(f'xref\n0 {len(offsets)}\n0000000000 65535 f \n'.encode())
    for offset in offsets[1:]:
        out.extend(f'{offset:010d} 00000 n \n'.encode())
    out.extend(f'trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(out)
