"""Small OOXML workbook writer for the fixed attendance table, using stdlib only."""
from datetime import date
from io import BytesIO
import re
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

from app.attendance.service import VIETNAM

NS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
HEADERS = ('Ngày', 'Họ tên', 'Hình thức', 'Check-in sáng', 'Nghỉ trưa', 'Check-in chiều', 'Check-out', 'Lý do')


def attendance_workbook(rows):
    def tag(name):
        return '{'+NS+'}'+name

    sheet = ET.Element(tag('worksheet'))
    views = ET.SubElement(sheet, tag('sheetViews'))
    view = ET.SubElement(views, tag('sheetView'), workbookViewId='0')
    ET.SubElement(view, tag('pane'), ySplit='1', topLeftCell='A2', activePane='bottomLeft', state='frozen')
    cols = ET.SubElement(sheet, tag('cols'))
    for index, width in enumerate((15, 30, 30, 18, 18, 18, 32, 60), 1):
        ET.SubElement(cols, tag('col'), min=str(index), max=str(index), width=str(width), customWidth='1')
    data = ET.SubElement(sheet, tag('sheetData'))
    for index, values in enumerate([HEADERS, *rows], 1):
        row = ET.SubElement(data, tag('row'), r=str(index))
        if index == 1:
            row.set('ht', '28')
            row.set('customHeight', '1')
        for col, value in enumerate(values):
            cell = ET.SubElement(row, tag('c'), r=f'{chr(65+col)}{index}')
            if index > 1 and value is not None and (col == 0 or (col in (3, 4, 5, 6) and not isinstance(value, str))):
                cell.set('s', '2' if col == 0 else '3')
                if col == 0:
                    number = str((value-date(1899, 12, 30)).days)
                else:
                    local = value.astimezone(VIETNAM)
                    number = str((local.hour*3600 + local.minute*60 + local.second)/86400)
                ET.SubElement(cell, tag('v')).text = number
            else:
                cell.set('t', 'inlineStr')
                cell.set('s', '1' if index == 1 else '0')
                text = ET.SubElement(ET.SubElement(cell, tag('is')), tag('t'))
                text.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
                # XML 1.0 cannot represent these controls; text stays literal, never a formula.
                text.text = re.sub('[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]', '', '' if value is None else str(value))
    ET.SubElement(sheet, tag('autoFilter'), ref=f'A1:H{len(rows)+1}')
    ET.SubElement(sheet, tag('pageSetup'), orientation='landscape', paperSize='9')
    styles = f'''<styleSheet xmlns="{NS}">
      <numFmts count="2"><numFmt numFmtId="164" formatCode="yyyy-mm-dd"/><numFmt numFmtId="165" formatCode="hh:mm:ss"/></numFmts>
      <fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font></fonts>
      <fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill><fill><patternFill patternType="solid"><fgColor rgb="FF18786A"/><bgColor indexed="64"/></patternFill></fill></fills>
      <borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
      <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
      <cellXfs count="4"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf><xf numFmtId="164" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/><xf numFmtId="165" fontId="0" fillId="0" borderId="0" xfId="0" applyNumberFormat="1"/></cellXfs>
      <cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
    </styleSheet>'''
    files = {
        '[Content_Types].xml': '''<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/><Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>''',
        '_rels/.rels': '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>''',
        'xl/workbook.xml': f'''<workbook xmlns="{NS}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Chấm công" sheetId="1" r:id="rId1"/></sheets></workbook>''',
        'xl/_rels/workbook.xml.rels': '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/><Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/></Relationships>''',
        'xl/worksheets/sheet1.xml': ET.tostring(sheet, encoding='utf-8', xml_declaration=True),
        'xl/styles.xml': styles,
    }
    output = BytesIO()
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content.encode('utf-8') if isinstance(content, str) else content)
    return output.getvalue()
