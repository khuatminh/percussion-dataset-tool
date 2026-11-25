#!/usr/bin/env python3
"""
build_report.py — Chuyển Markdown (kèm YAML front matter) thành file .docx
theo quy chuẩn trình bày tiểu luận / báo cáo PTIT.

Cách dùng:
    pip install python-docx pyyaml pillow
    python build_report.py input.md output.docx [--logo ptit-logo.png]

Quy ước Markdown (xem README / SKILL.md):
    # Tên chương          -> CHƯƠNG n: TÊN CHƯƠNG (Heading 1, sang trang mới)
    # Lời mở đầu {-}      -> Heading 1 không đánh số
    ## / ### / ####       -> 1.1. / 1.1.1. / 1.1.1.1.
    - mục / "  - mục"     -> bullet cấp 1 "-" / cấp 2 "+"
    1. mục / "   1. mục"  -> danh sách 1. / a)
    ![Chú thích](anh.png) -> ảnh + "Hình n: Chú thích" (dưới ảnh)
    Bảng: Chú thích       -> dòng ngay trên bảng Markdown -> "Bảng n: ..." (trên bảng)
    # Tài liệu tham khảo  -> mỗi đoạn/bullet bên dưới là 1 tài liệu APA 7
    **đậm**, *nghiêng*
"""
import argparse
import copy
import os
import subprocess
import tempfile
import zipfile
import re
import sys
import unicodedata

import yaml
from lxml import etree
from docx import Document
from docx.enum.section import WD_ORIENT  # noqa: F401
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

# ----------------------------------------------------------------- cấu hình
FONT = "Times New Roman"
SIZE = 13
CAPTION_SIZE = 12
TABLE_SIZE = 12
MARGINS = dict(top=2, bottom=2, left=3, right=1.5)  # cm
TEXT_WIDTH_CM = 21 - MARGINS["left"] - MARGINS["right"]  # 16.5 cm
FIRST_LINE = 1.27  # cm
MAX_IMG_CM = 15
# shortcut: khoảng cố định, đề tài/khối Lớp quá dài thì giảm để dòng thời gian không tràn trang
COVER_DATE_GAP = 24  # pt, khoảng trống trên dòng địa điểm - thời gian ở bìa
SCHOOL = "HỌC VIỆN CÔNG NGHỆ BƯU CHÍNH VIỄN THÔNG"
CHAPTER_FMT = "PHẦN {n}: {title}"
# Báo cáo Yêu cầu 3-4 nối tiếp bản Yêu cầu 1-2: Phần III, Mục 14, Bảng 12, Hình 3
CHAPTER_START = 2      # số phần đã dùng trước đó
CHAPTER_ROMAN = True   # PHẦN III thay vì PHẦN 3
SECTION_START = 13     # số mục (##) đã dùng; mục đánh số liên tục qua các phần
SECTION_GLOBAL = True  # "## " -> "14.", "### " -> "14.1." (không kèm số phần)
FIG_START, TAB_START = 2, 11
CODE_SIZE = 12  # mã nguồn dùng chung phông Times New Roman
SUB_SEP = ". "  # "1.1. Tên mục"
REF_TITLES = {"tai lieu tham khao", "references"}

J = WD_ALIGN_PARAGRAPH


# ----------------------------------------------------------------- tiện ích
def strip_accents(s):
    s = s.replace("đ", "d").replace("Đ", "D")
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn").lower()


def el(tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k), str(v))
    return e


def set_rfonts(rpr, font=FONT):
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = el("w:rFonts")
        rpr.insert(0, rf)
    for a in list(rf.attrib):
        del rf.attrib[a]
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), font)


def style_fmt(st, size=SIZE, bold=False, italic=False, align=J.JUSTIFY,
              first_line=None, before=6, after=6, line=1.5,
              page_break=False, keep_next=False, left=None):
    st.font.name = FONT
    st.font.size = Pt(size)
    st.font.bold = bold
    st.font.italic = italic
    st.font.color.rgb = RGBColor(0, 0, 0)
    rpr = st.element.get_or_add_rPr()
    set_rfonts(rpr)
    pf = st.paragraph_format
    pf.alignment = align
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    pf.first_line_indent = Cm(first_line) if first_line else Cm(0)
    pf.left_indent = Cm(left) if left is not None else Cm(0)
    pf.page_break_before = page_break
    pf.keep_with_next = keep_next


def get_style(doc, name, base="Normal"):
    try:
        return doc.styles[name]
    except KeyError:
        st = doc.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
        st.base_style = doc.styles[base]
        return st


def add_field(par, instr, cached="", bold=None, italic=None):
    def run():
        r = par.add_run()
        if bold is not None:
            r.bold = bold
        if italic is not None:
            r.italic = italic
        return r
    r = run()
    r._r.append(el("w:fldChar", **{"w:fldCharType": "begin", "w:dirty": "true"}))
    r = run()
    it = el("w:instrText", **{"xml:space": "preserve"})
    it.text = f" {instr} "
    r._r.append(it)
    r = run()
    r._r.append(el("w:fldChar", **{"w:fldCharType": "separate"}))
    r = run()
    r.text = cached
    r = run()
    r._r.append(el("w:fldChar", **{"w:fldCharType": "end"}))


PPR_ORDER = ["pStyle", "keepNext", "keepLines", "pageBreakBefore", "framePr",
             "widowControl", "numPr", "suppressLineNumbers", "pBdr", "shd",
             "tabs", "suppressAutoHyphens", "kinsoku", "wordWrap",
             "overflowPunct", "topLinePunct", "autoSpaceDE", "autoSpaceDN",
             "bidi", "adjustRightInd", "snapToGrid", "spacing", "ind",
             "contextualSpacing", "mirrorIndents", "suppressOverlap", "jc",
             "textDirection", "textAlignment", "textboxTightWrap",
             "outlineLvl", "divId", "cnfStyle", "rPr", "sectPr", "pPrChange"]


def ppr_insert(ppr, child):
    """Chèn phần tử vào w:pPr đúng thứ tự schema (Word kiểm tra chặt)."""
    name = child.tag.split("}")[1]
    old = ppr.find(qn(f"w:{name}"))
    if old is not None:
        ppr.remove(old)
    idx = PPR_ORDER.index(name)
    for i, c in enumerate(ppr):
        cname = c.tag.split("}")[1]
        if cname in PPR_ORDER and PPR_ORDER.index(cname) > idx:
            ppr.insert(i, child)
            return
    ppr.append(child)


INLINE = re.compile(r"(\$\$[^$]+\$\$|\$[^$]+\$|`[^`]+`|\*\*(?:[^*`]|`[^`]*`)+\*\*|\*[^*\s][^*]*\*)")
MATH = {}  # công thức LaTeX -> phần tử OMML (m:oMath / m:oMathPara), dựng sẵn bằng pandoc


def math_cache(texts):
    """Đổi mọi công thức $...$, $$...$$ sang OMML bằng một lần chạy pandoc."""
    found = []
    for t in texts:
        for f in re.findall(r"\$\$[^$]+\$\$|\$[^$]+\$", t):
            if f not in MATH and f not in found:
                found.append(f)
    if not found:
        return
    with tempfile.TemporaryDirectory() as d:
        md, dx = os.path.join(d, "m.md"), os.path.join(d, "m.docx")
        with open(md, "w", encoding="utf-8") as f:
            # số thập phân dấu phẩy 0{,}5 -> chữ thẳng "0,5" để Word không chèn khoảng trắng sau dấu phẩy
            f.write("\n\n".join(re.sub(r"(\d+)\{,\}(\d+)", r"\\text{\1,\2}", x) for x in found) + "\n")
        subprocess.run(["pandoc", md, "-f", "markdown", "-o", dx], check=True)
        with zipfile.ZipFile(dx) as z:
            root = etree.fromstring(z.read("word/document.xml"))
    M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
    pars = root.findall(f".//{{{qn('w:body').split('}')[0][1:]}}}p")
    assert len(pars) >= len(found), (len(pars), len(found))
    for f, p in zip(found, pars):
        e = p.find(f"{{{M}}}oMathPara") if f.startswith("$$") else p.find(f"{{{M}}}oMath")
        assert e is not None, f"pandoc không đổi được công thức {f}"
        MATH[f] = e


def add_runs(par, text, bold=None, italic=None, size=None):
    for tok in INLINE.split(text):
        if not tok:
            continue
        if tok.startswith("$") and tok.endswith("$") and len(tok) > 2:
            par._p.append(copy.deepcopy(MATH[tok]))
            continue
        if tok.startswith("**") and tok.endswith("**") and len(tok) > 4:
            add_runs(par, tok[2:-2], True, italic, size)
            continue
        if tok.startswith("*") and tok.endswith("*") and len(tok) > 1:
            add_runs(par, tok[1:-1], bold, True, size)
            continue
        is_code = tok.startswith("`") and tok.endswith("`") and len(tok) > 1
        r = par.add_run(tok[1:-1] if is_code else tok)
        if bold is not None:
            r.bold = bold
        if italic is not None:
            r.italic = italic
        if size:
            r.font.size = Pt(size)


def para(doc, text="", style=None, **kw):
    p = doc.add_paragraph(style=style)
    if text:
        add_runs(p, text, kw.get("bold"), kw.get("italic"), kw.get("size"))
    pf = p.paragraph_format
    if "align" in kw:
        pf.alignment = kw["align"]
    if "before" in kw:
        pf.space_before = Pt(kw["before"])
    if "after" in kw:
        pf.space_after = Pt(kw["after"])
    if "left" in kw:
        pf.left_indent = Cm(kw["left"])
    if kw.get("no_indent"):
        pf.first_line_indent = Cm(0)
    if kw.get("keep_next"):
        pf.keep_with_next = True
    return p


# ----------------------------------------------------------------- thiết lập
def setup_document(doc):
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    sec.top_margin, sec.bottom_margin = Cm(MARGINS["top"]), Cm(MARGINS["bottom"])
    sec.left_margin, sec.right_margin = Cm(MARGINS["left"]), Cm(MARGINS["right"])
    sec.header_distance = Cm(1)
    sec.footer_distance = Cm(0.8)

    # kiểu có sẵn của mẫu python-docx (Macro Text…) dùng Courier: đưa về phông chung
    for rf in doc.styles.element.iter(qn("w:rFonts")):
        if "Courier" in "".join(rf.attrib.values()):
            set_rfonts(rf.getparent())

    normal = doc.styles["Normal"]
    style_fmt(normal, first_line=FIRST_LINE)
    rpr = normal.element.get_or_add_rPr()
    rpr.append(el("w:lang", **{"w:val": "vi-VN"}))

    style_fmt(doc.styles["Heading 1"], bold=True, align=J.CENTER,
              page_break=True, keep_next=True)
    style_fmt(doc.styles["Heading 2"], bold=True, keep_next=True)
    style_fmt(doc.styles["Heading 3"], italic=True, keep_next=True)
    style_fmt(doc.styles["Heading 4"], italic=True, keep_next=True)
    for i in range(1, 5):
        h = doc.styles[f"Heading {i}"]
        h.paragraph_format.first_line_indent = Cm(0)
        pPr = h.element.get_or_add_pPr()
        ol = pPr.find(qn("w:outlineLvl"))
        if ol is None:
            ppr_insert(pPr, el("w:outlineLvl", **{"w:val": i - 1}))

    style_fmt(get_style(doc, "Caption"), size=CAPTION_SIZE, italic=True,
              align=J.CENTER)
    style_fmt(get_style(doc, "Tieu de trang"), bold=True, align=J.CENTER,
              page_break=True, keep_next=True)
    style_fmt(get_style(doc, "Bang"), size=TABLE_SIZE, align=J.LEFT)
    style_fmt(get_style(doc, "Danh sach"), align=J.JUSTIFY)
    style_fmt(get_style(doc, "Tai lieu tham khao"), align=J.LEFT)  # APA 7: căn trái, thụt treo 1,27 cm
    style_fmt(get_style(doc, "Anh"), align=J.CENTER, keep_next=True)
    st = get_style(doc, "Ma nguon")
    style_fmt(st, size=CODE_SIZE, align=J.LEFT, before=0, after=0, line=1.0, left=0.6)
    style_fmt(get_style(doc, "Cong thuc"), align=J.CENTER)
    ref = doc.styles["Tai lieu tham khao"].paragraph_format
    ref.left_indent, ref.first_line_indent = Cm(1.27), Cm(-1.27)

    # mục lục / danh mục hình, bảng
    for name, left in [("toc 1", 0), ("toc 2", 0.6), ("toc 3", 1.2),
                       ("toc 4", 1.8), ("table of figures", 0)]:
        st = get_style(doc, name)
        style_fmt(st, align=J.LEFT, left=left)
        st.paragraph_format.tab_stops.add_tab_stop(
            Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)

    ft = get_style(doc, "Footer")
    style_fmt(ft, align=J.CENTER, before=0, after=0, line=1.0)

    # cập nhật trường (mục lục, số hình/bảng) khi mở file trong Word
    st_el = doc.settings.element
    upd = el("w:updateFields", **{"w:val": "true"})
    after_tags = ["w:hdrShapeDefaults", "w:footnotePr", "w:endnotePr",
                  "w:compat", "w:docVars", "w:rsids", "m:mathPr",
                  "w:themeFontLang", "w:clrSchemeMapping", "w:decimalSymbol",
                  "w:listSeparator"]
    anchor = None
    for child in st_el:
        if any(child.tag == qn(t) for t in after_tags):
            anchor = child
            break
    if anchor is not None:
        anchor.addprevious(upd)
    else:
        st_el.append(upd)


def setup_page(doc):
    """Gọi SAU khi dựng trang bìa: tách bìa thành section riêng (có khung,
    không số trang); section nội dung đánh số liên tục, bìa = trang 1."""
    from docx.enum.section import WD_SECTION
    doc.add_section(WD_SECTION.NEW_PAGE)
    cover_sec, main_sec = doc.sections[0], doc.sections[1]
    main_sec.footer.is_linked_to_previous = False
    p = main_sec.footer.paragraphs[0]
    p.style = doc.styles["Footer"]
    add_field(p, "PAGE", "2")
    pb = el("w:pgBorders", **{"w:offsetFrom": "page"})
    for side in ("top", "left", "bottom", "right"):
        pb.append(el(f"w:{side}", **{"w:val": "thinThickSmallGap", "w:sz": 24,
                                     "w:space": 24, "w:color": "000000"}))
    cover_sec._sectPr.find(qn("w:pgMar")).addnext(pb)


# ----------------------------------------------------------------- numbering
class Lists:
    def __init__(self, doc):
        self.np = doc.part.numbering_part.element
        self.bullet_abs, self.order_abs = 9001, 9002
        self._abs(self.bullet_abs, [("bullet", "-"), ("bullet", "+")])
        self._abs(self.order_abs, [("decimal", "%1."), ("lowerLetter", "%2)")])
        self.next_id = 9100
        self.bullet_num = self._num(self.bullet_abs)

    def _abs(self, aid, levels):
        a = el("w:abstractNum", **{"w:abstractNumId": aid})
        a.append(el("w:multiLevelType", **{"w:val": "hybridMultilevel"}))
        for ilvl, (fmt, text) in enumerate(levels):
            lvl = el("w:lvl", **{"w:ilvl": ilvl})
            lvl.append(el("w:start", **{"w:val": 1}))
            lvl.append(el("w:numFmt", **{"w:val": fmt}))
            lvl.append(el("w:lvlText", **{"w:val": text}))
            lvl.append(el("w:lvlJc", **{"w:val": "left"}))
            ppr = el("w:pPr")
            ppr.append(el("w:ind", **{"w:left": 720 + 360 * ilvl, "w:hanging": 360}))
            lvl.append(ppr)
            rpr = el("w:rPr")
            rpr.append(el("w:rFonts", **{"w:ascii": FONT, "w:hAnsi": FONT,
                                         "w:hint": "default"}))
            lvl.append(rpr)
            a.append(lvl)
        first_num = self.np.find(qn("w:num"))
        if first_num is not None:
            first_num.addprevious(a)
        else:
            self.np.append(a)

    def _num(self, aid, restart=False):
        nid = self.next_id
        self.next_id += 1
        n = el("w:num", **{"w:numId": nid})
        n.append(el("w:abstractNumId", **{"w:val": aid}))
        if restart:
            for ilvl in (0, 1):
                o = el("w:lvlOverride", **{"w:ilvl": ilvl})
                o.append(el("w:startOverride", **{"w:val": 1}))
                n.append(o)
        self.np.append(n)
        return nid

    def new_ordered(self):
        return self._num(self.order_abs, restart=True)

    @staticmethod
    def apply(p, num_id, ilvl):
        ppr = p._p.get_or_add_pPr()
        numpr = el("w:numPr")
        numpr.append(el("w:ilvl", **{"w:val": ilvl}))
        numpr.append(el("w:numId", **{"w:val": num_id}))
        ppr_insert(ppr, numpr)
        ppr_insert(ppr, el("w:ind", **{"w:left": 720 + 360 * ilvl, "w:hanging": 360}))


# ----------------------------------------------------------------- parser
def parse_markdown(text):
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if m:
        meta = yaml.safe_load(m.group(1)) or {}
        text = text[m.end():]
    lines = text.splitlines()
    blocks, buf, i = [], [], 0

    def flush():
        if buf:
            blocks.append(("p", " ".join(s.strip() for s in buf)))
            buf.clear()

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        if not s:
            flush(); i += 1; continue
        if s.startswith("```"):
            flush()
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i]); i += 1
            blocks.append(("code", code)); i += 1; continue
        mh = re.match(r"^(#{1,4})\s+(.*?)\s*$", ln)
        if mh:
            flush()
            title = mh.group(2)
            unnum = title.endswith("{-}")
            title = title.replace("{-}", "").strip()
            blocks.append(("h", len(mh.group(1)), title, unnum)); i += 1; continue
        mi = re.match(r"^!\[(.*?)\]\((.*?)\)\s*$", s)
        if mi:
            flush(); blocks.append(("img", mi.group(1), mi.group(2))); i += 1; continue
        mc = re.match(r"^(Bảng|Table)\s*:\s*(.+)$", s)
        if mc and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
            flush(); blocks.append(("tcap", mc.group(2))); i += 1; continue
        if s.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                r = lines[i].strip()[1:-1]
                cells = [c.strip() for c in re.split(r"\|(?=(?:[^$`]*[$`][^$`]*[$`])*[^$`]*$)", r)]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            blocks.append(("table", rows)); continue
        mb = re.match(r"^(\s*)([-*+])\s+(.*)$", ln)
        mo = re.match(r"^(\s*)(\d+|[a-z])[.)]\s+(.*)$", ln)
        if mb or mo:
            flush()
            mm = mb or mo
            lvl = 1 if len(mm.group(1).expandtabs(4)) >= 2 else 0
            blocks.append(("li", "ul" if mb else "ol", lvl, mm.group(3)))
            i += 1; continue
        buf.append(ln); i += 1
    flush()
    return meta, blocks


# ----------------------------------------------------------------- trang bìa
def cover(doc, meta, logo):
    khoa = str(meta.get("khoa", "")).strip()
    if khoa and not strip_accents(khoa).startswith("khoa"):
        khoa = "Khoa " + khoa
    big = dict(no_indent=True, align=J.CENTER, before=0, after=0)
    para(doc, SCHOOL, bold=True, size=14, before=24, after=6,
         no_indent=True, align=J.CENTER)
    if khoa:
        para(doc, khoa.upper(), bold=True, size=14, after=0,
             no_indent=True, align=J.CENTER, before=0)
    # đường kẻ ngắn
    p = para(doc, "", no_indent=True, before=0, after=18)
    p.paragraph_format.left_indent = Cm(5.25)
    p.paragraph_format.right_indent = Cm(5.25)
    pbdr = el("w:pBdr")
    pbdr.append(el("w:bottom", **{"w:val": "single", "w:sz": 8, "w:space": 1,
                                   "w:color": "000000"}))
    ppr_insert(p._p.get_or_add_pPr(), pbdr)
    # logo
    p = para(doc, "", **big)
    if logo and os.path.exists(logo):
        p.add_run().add_picture(logo, width=Cm(4.5))
    else:
        add_runs(p, "[Chèn logo PTIT]", italic=True)
    loai = str(meta.get("loai_tai_lieu", "TIỂU LUẬN")).upper()
    mon = str(meta.get("mon", "")).upper()
    para(doc, loai, bold=True, size=24, no_indent=True, align=J.CENTER,
         before=30, after=0)
    para(doc, f"MÔN {mon}".strip(), bold=True, size=24, no_indent=True,
         align=J.CENTER, before=0, after=12)
    if meta.get("de_tai"):
        para(doc, f"Đề tài: {meta['de_tai']}", bold=True, size=16,
             no_indent=True, align=J.CENTER, after=36)
    for label, key in [("Lớp", "lop"), ("Nhóm", "nhom"),
                       ("Giảng viên", "giang_vien")]:
        if meta.get(key) is not None:
            para(doc, f"{label}: {meta[key]}", bold=True, size=14,
                 no_indent=True, align=J.LEFT, left=4.0, before=0, after=6)
    # dòng địa điểm - thời gian: đoạn thường sau khối Lớp/Nhóm (khung neo đáy
    # trang làm LibreOffice đẩy Lớp/Nhóm sang trang 2)
    noi = meta.get("dia_diem", "Hà Nội")
    tg = meta.get("thoi_gian", "")
    para(doc, f"{noi}, {tg}".strip(", "), bold=True, italic=True, size=14,
         no_indent=True, align=J.CENTER, before=COVER_DATE_GAP, after=0)


# ----------------------------------------------------------------- các trang đầu
def page_title(doc, text, in_toc=True):
    if in_toc:
        return doc.add_paragraph(text.upper(), style="Heading 1")
    return doc.add_paragraph(text.upper(), style="Tieu de trang")


def auto_widths(rows, ncol):
    """Chia bề rộng trang theo độ dài chữ của từng cột, để bảng luôn rộng hết dòng."""
    def size(c):
        c = re.sub(r"\$[^$]*\$", "xxxx", c).replace("**", "").replace("`", "")
        return min(max([len(w) for w in c.split()] + [len(c) / 3]), 28)
    def avg(ci):
        cs = [r[ci] for r in rows[1:] if ci < len(r) and r[ci]]
        return sum(len(c) for c in cs) / max(1, len(cs)) / 2.5
    wts = [max(5, min(28, max(avg(ci), max(size(r[ci]) if ci < len(r) else 0 for r in rows))))
           for ci in range(ncol)]
    return [TEXT_WIDTH_CM * w / sum(wts) for w in wts]


def make_table(doc, rows, widths=None):
    ncol = max(len(r) for r in rows)
    widths = widths or auto_widths(rows, ncol)
    t = doc.add_table(rows=len(rows), cols=ncol)
    t.style = doc.styles["Table Grid"]
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for ri, row in enumerate(rows):
        for ci in range(ncol):
            cell = t.cell(ri, ci)
            p = cell.paragraphs[0]
            p.style = doc.styles["Bang"]
            txt = row[ci] if ci < len(row) else ""
            if ri == 0:
                p.alignment = J.CENTER
                add_runs(p, txt, bold=True)
            else:
                add_runs(p, txt)
            if widths:
                cell.width = Cm(widths[ci])
    t.autofit = False
    for ci, col in enumerate(t.columns):
        col.width = Cm(widths[ci])
    trpr = t.rows[0]._tr.get_or_add_trPr()
    trpr.append(el("w:tblHeader"))
    return t


def front_matter(doc, meta, n_fig, n_tab):
    p = page_title(doc, "Mục lục", in_toc=False)
    p.paragraph_format.page_break_before = False  # đã sang trang nhờ section break
    p = doc.add_paragraph(style="toc 1")
    add_field(p, 'TOC \\o "1-4" \\h \\z \\u',
              "Nhấn chuột phải vào đây → Update Field (F9) để cập nhật mục lục.")

    members = meta.get("thanh_vien") or []
    if members:
        page_title(doc, "Danh sách thành viên")
        rows = [["STT", "Họ và tên", "Mã sinh viên", "Ghi chú"]]
        for k, m in enumerate(members, 1):
            if isinstance(m, dict):
                m = [m.get("ho_ten", ""), m.get("msv", ""), m.get("ghi_chu", "")]
            m = list(m) + ["", "", ""]
            rows.append([str(k), str(m[0]), str(m[1]), str(m[2] or "")])
        make_table(doc, rows, widths=[1.5, 6, 4.5, 4.5])

    if n_fig:
        page_title(doc, "Danh mục hình ảnh")
        p = doc.add_paragraph(style="table of figures")
        add_field(p, 'TOC \\h \\z \\c "Hình"', "Cập nhật trường (F9) để hiện danh mục hình.")
    if n_tab:
        page_title(doc, "Danh mục bảng biểu")
        p = doc.add_paragraph(style="table of figures")
        add_field(p, 'TOC \\h \\z \\c "Bảng"', "Cập nhật trường (F9) để hiện danh mục bảng.")

    abbr = meta.get("viet_tat") or []
    if abbr:
        if isinstance(abbr, dict):
            abbr = list(abbr.items())
        abbr = sorted(([str(a[0]), str(a[1])] for a in abbr),
                      key=lambda x: strip_accents(x[0]))
        page_title(doc, "Danh mục từ viết tắt")
        make_table(doc, [["Từ viết tắt", "Ý nghĩa"]] + abbr, widths=[4.5, 12])


# ----------------------------------------------------------------- nội dung
def caption(doc, kind, n, text, keep_next=False):
    p = doc.add_paragraph(style="Caption")
    r = p.add_run(f"{kind} ")
    add_field(p, f"SEQ {kind} \\r {n} \\* ARABIC", str(n))
    p.add_run(": ")
    add_runs(p, text)
    if keep_next:
        p.paragraph_format.keep_with_next = True
    return p


def roman(n):
    out = ""
    for v, r in [(10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")]:
        while n >= v:
            out, n = out + r, n - v
    return out


LABEL = re.compile(r"\s*\{#([\w:.-]+)\}")


def number_blocks(blocks):
    """Đánh số đề mục, hình, bảng; gỡ {#nhãn} và thay @nhãn bằng số."""
    ch = [CHAPTER_START, SECTION_START, 0, 0]
    n_fig, n_tab, labels = FIG_START, TAB_START, {}
    out = []
    for b in blocks:
        b = list(b)
        if b[0] == "h":
            _, lvl, title, unnum = b
            m = LABEL.search(title)
            title = LABEL.sub("", title).strip()
            if lvl == 1 and not unnum and strip_accents(title) not in REF_TITLES:
                ch[0] += 1
                ch[2:] = [0, 0]
                if not SECTION_GLOBAL:
                    ch[1] = 0
                num = roman(ch[0]) if CHAPTER_ROMAN else str(ch[0])
            elif lvl > 1:
                ch[lvl - 1] += 1
                ch[lvl:] = [0] * (4 - lvl)
                num = ".".join(str(x) for x in ch[1 if SECTION_GLOBAL else 0:lvl])
            else:
                num = None
            if m and num:
                labels[m.group(1)] = num
            b = ["h", lvl, title, unnum, num]
        elif b[0] == "img" and b[1]:
            m = LABEL.search(b[1])
            n_fig += 1
            if m:
                labels[m.group(1)] = str(n_fig)
            b[1] = LABEL.sub("", b[1]).strip()
        elif b[0] == "tcap":
            m = LABEL.search(b[1])
            n_tab += 1
            if m:
                labels[m.group(1)] = str(n_tab)
            b[1] = LABEL.sub("", b[1]).strip()
        out.append(b)

    def sub(t):
        def one(m):
            assert m.group(1) in labels, f"không có nhãn {m.group(1)}"
            return labels[m.group(1)]
        return re.sub(r"@((?:sec|tab|fig):[\w-]+)", one, t)
    for b in out:
        if b[0] in ("p", "tcap"):
            b[1] = sub(b[1])
        elif b[0] == "li":
            b[3] = sub(b[3])
        elif b[0] == "img":
            b[1] = sub(b[1])
        elif b[0] == "table":
            b[1] = [[sub(c) for c in r] for r in b[1]]
    return out


def body(doc, blocks, base_dir, lists):
    n_fig, n_tab = FIG_START, TAB_START
    in_refs = False
    refs = []
    pending_tcap = None
    cur_ol = None
    prev_kind = None

    def flush_refs():
        for r in sorted(refs, key=strip_accents):
            p = doc.add_paragraph(style="Tai lieu tham khao")
            add_runs(p, r)
        refs.clear()

    for b in blocks:
        kind = b[0]
        if kind == "h":
            _, lvl, title, unnum, num = b
            if in_refs:
                flush_refs()
            in_refs = lvl == 1 and strip_accents(title) in REF_TITLES
            if lvl == 1:
                if unnum or in_refs:
                    text = title.upper()
                else:
                    text = CHAPTER_FMT.format(n=num, title=title.upper())
            else:
                text = f"{num}{SUB_SEP}{title}"
            doc.add_paragraph(text, style=f"Heading {lvl}")
            cur_ol = None
        elif in_refs and kind in ("p", "li"):
            refs.append(b[1] if kind == "p" else b[3])
        elif kind == "p":
            t = b[1]
            if re.fullmatch(r"\$\$[^$]+\$\$", t):
                p = doc.add_paragraph(style="Cong thuc")
            else:
                p = doc.add_paragraph(style="Normal")
                if t.startswith("{>}"):  # dòng ký tên căn phải
                    t = t[3:].strip()
                    p.alignment = J.RIGHT
                    p.paragraph_format.first_line_indent = Cm(0)
            add_runs(p, t)
            cur_ol = None
        elif kind == "code":
            for k, ln in enumerate(b[1]):
                p = doc.add_paragraph(style="Ma nguon")
                p.add_run(ln)
                if k == 0:
                    p.paragraph_format.space_before = Pt(6)
                if k == len(b[1]) - 1:
                    p.paragraph_format.space_after = Pt(6)
                else:
                    p.paragraph_format.keep_with_next = True
            cur_ol = None
        elif kind == "li":
            _, typ, lvl, txt = b
            p = doc.add_paragraph(style="Danh sach")
            add_runs(p, txt)
            if typ == "ul":
                Lists.apply(p, lists.bullet_num, lvl)
            else:
                if cur_ol is None or (lvl == 0 and prev_kind != "li"):
                    cur_ol = lists.new_ordered()
                Lists.apply(p, cur_ol, lvl)
        elif kind == "img":
            _, cap, path = b
            full = path if os.path.isabs(path) else os.path.join(base_dir, path)
            p = doc.add_paragraph(style="Anh")
            if os.path.exists(full):
                w = MAX_IMG_CM
                try:
                    from PIL import Image
                    with Image.open(full) as im:
                        dpi = (im.info.get("dpi") or (96, 96))[0] or 96
                        w = min(MAX_IMG_CM, im.width / dpi * 2.54)
                except Exception:
                    pass
                p.add_run().add_picture(full, width=Cm(w))
            else:
                add_runs(p, f"[Chèn hình: {path}]", italic=True)
            if cap:
                n_fig += 1
                caption(doc, "Hình", n_fig, cap)
            cur_ol = None
        elif kind == "tcap":
            pending_tcap = b[1]
        elif kind == "table":
            if pending_tcap:
                n_tab += 1
                caption(doc, "Bảng", n_tab, pending_tcap, keep_next=True)
                pending_tcap = None
            make_table(doc, b[1])
            doc.add_paragraph(style="Bang").paragraph_format.space_after = Pt(0)
            cur_ol = None
        prev_kind = kind
    if in_refs:
        flush_refs()
    return n_fig, n_tab


def count_captions(blocks):
    nf = sum(1 for b in blocks if b[0] == "img" and b[1])
    nt = sum(1 for k, b in enumerate(blocks) if b[0] == "tcap")
    return nf, nt


def build(md_path, out_path, logo=None):
    with open(md_path, encoding="utf-8") as f:
        meta, blocks = parse_markdown(f.read())
    doc = Document()
    setup_document(doc)
    lists = Lists(doc)
    # xoá đoạn trống mặc định
    for p in list(doc.paragraphs):
        p._p.getparent().remove(p._p)
    cover(doc, meta, logo)
    setup_page(doc)
    nf, nt = count_captions(blocks)
    blocks = number_blocks(blocks)
    texts = []
    for b in blocks:
        if b[0] in ("p", "tcap", "img"):
            texts.append(b[1])
        elif b[0] == "li":
            texts.append(b[3])
        elif b[0] == "table":
            texts += [c for r in b[1] for c in r]
    math_cache(texts)
    front_matter(doc, meta, nf, nt)
    body(doc, blocks, os.path.dirname(os.path.abspath(md_path)), lists)
    doc.core_properties.title = str(meta.get("de_tai", ""))
    # phần phụ của mẫu python-docx (stylesWithEffects, fontTable) vẫn khai báo Courier: bỏ đi
    for part in doc.part.package.iter_parts():
        name = str(part.partname)
        if name.endswith("stylesWithEffects.xml"):
            part._blob = part.blob.replace(b'"Courier"', f'"{FONT}"'.encode())
        elif name.endswith("fontTable.xml"):
            part._blob = re.sub(rb'<w:font w:name="Courier[^"]*">.*?</w:font>', b"", part.blob, flags=re.S)
    doc.save(out_path)
    return out_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--logo", default=None,
                    help="Đường dẫn logo (mặc định: ptit-logo.png cạnh script nếu có)")
    a = ap.parse_args()
    logo = a.logo
    if not logo:
        cand = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ptit-logo.png")
        logo = cand if os.path.exists(cand) else None
    print(build(a.input, a.output, logo))
