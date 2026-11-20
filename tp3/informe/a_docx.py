"""Convierte informe_TP3.html a informe_TP3.docx (editable) con pandoc + ajustes de formato.
Uso: python informe/a_docx.py   (requiere pandoc y python-docx)"""
import subprocess
from pathlib import Path
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

AQUI = Path(__file__).resolve().parent
import re
tmp = AQUI / "_tmp.docx"
html = (AQUI / "informe_TP3.html").read_text(encoding="utf-8")
html = re.sub(r"<title>.*?</title>", "", html, flags=re.S)


def _decision(m):
    filas = re.findall(r"<div><span>(.*?)</span><b>(.*?)</b><span>(.*?)</span></div>", m.group(0), flags=re.S)
    cuerpo = "".join(f"<tr><td>{a}</td><td><b>{b}</b></td><td>{c}</td></tr>" for a, b, c in filas)
    return f"<table><thead><tr><th>Decisión</th><th>Valor</th><th>Detalle</th></tr></thead><tbody>{cuerpo}</tbody></table>"


html = re.sub(r'<div class="decision">.*?</div>\s*</div>', _decision, html, flags=re.S)


def _lineas(m):
    return "".join(f"<p><code>{l.strip()}</code></p>" if "form" in m.group(1) else f"<p>{l.strip()}</p>"
                   for l in m.group(2).split("\n") if l.strip())


html = re.sub(r'<div class="(caja mono|form)"[^>]*>(.*?)</div>', _lineas, html, flags=re.S)
src = AQUI / "_tmp.html"
src.write_text(html, encoding="utf-8")
subprocess.run(["pandoc", str(src), "-f", "html", "-t", "docx", "-o", str(tmp)], check=True)
src.unlink()
d = Document(tmp)

for s in d.sections:
    s.page_width, s.page_height = Cm(21), Cm(29.7)
    s.left_margin = s.right_margin = Cm(1.8)
    s.top_margin = s.bottom_margin = Cm(1.8)
ancho = Cm(21 - 3.6)

AZUL = RGBColor(0x2A, 0x78, 0xD6)
ESTILOS = {st.name.lower(): st for st in d.styles}
for nombre in ("Normal", "Body Text", "First Paragraph", "Compact"):
    st = ESTILOS.get(nombre.lower())
    if st is not None:
        st.font.name, st.font.size = "Calibri", Pt(10)
        st.paragraph_format.space_after = Pt(4)
for nombre, tam in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 11)):
    st = ESTILOS.get(nombre.lower())
    if st is not None:
        st.font.name, st.font.size, st.font.bold = "Calibri", Pt(tam), True
        st.font.color.rgb = RGBColor(0x1B, 0x1B, 0x1A) if nombre != "Heading 2" else AZUL
        st.paragraph_format.space_before = Pt(10)
        st.paragraph_format.space_after = Pt(4)
        st.paragraph_format.keep_with_next = True

for p in d.paragraphs:
    if p.style.name.lower() in ("body text", "first paragraph"):
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    for r in p.runs:  # imágenes al ancho de página
        for il in r._element.findall(".//" + qn("wp:inline")):
            ext = il.find(qn("wp:extent"))
            cx, cy = int(ext.get("cx")), int(ext.get("cy"))
            nuevo = int(ancho)
            ext.set("cy", str(int(cy * nuevo / cx))); ext.set("cx", str(nuevo))
            for e in il.findall(".//" + qn("a:ext")):
                e.set("cx", str(nuevo)); e.set("cy", str(int(cy * nuevo / cx)))


def borde(celda, color="BBBBBB"):
    tcPr = celda._tc.get_or_add_tcPr()
    b = OxmlElement("w:tcBorders")
    for lado in ("top", "bottom", "left", "right"):
        e = OxmlElement(f"w:{lado}")
        e.set(qn("w:val"), "single"); e.set(qn("w:sz"), "4"); e.set(qn("w:color"), color)
        b.append(e)
    tcPr.append(b)


def sombra(celda, color="F0EFEA"):
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"); sh.set(qn("w:color"), "auto"); sh.set(qn("w:fill"), color)
    celda._tc.get_or_add_tcPr().append(sh)


for t in d.tables:
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = t._tbl.tblPr
    w = OxmlElement("w:tblW"); w.set(qn("w:w"), str(int(ancho.twips if hasattr(ancho, 'twips') else ancho / 635))); w.set(qn("w:type"), "dxa")
    for old in tblPr.findall(qn("w:tblW")):
        tblPr.remove(old)
    tblPr.append(w)
    for i, fila in enumerate(t.rows):
        for c in fila.cells:
            borde(c)
            if i == 0:
                sombra(c)
            for p in c.paragraphs:
                p.paragraph_format.space_after = Pt(1)
                for r in p.runs:
                    r.font.size = Pt(8.5)
                    if i == 0:
                        r.font.bold = True

out = AQUI / "informe_TP3.docx"
d.save(out)
tmp.unlink()
print("DOCX:", out)
