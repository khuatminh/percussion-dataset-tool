#!/usr/bin/env python3
"""Chuyển bao_cao_mmdb_yeu_cau_3_4.tex sang Markdown theo quy ước của build_report.py.
Chỉ xử lý các lệnh LaTeX có trong báo cáo này; bảng có tiêu đề nhiều tầng được sửa tay sau.
Dùng: python3 tex2md.py ../bao_cao_mmdb_yeu_cau_3_4.tex > than_bai.md"""
import re
import sys

CITE = {
    'freesound': 'Ramires và cộng sự, 2021', 'postgres': 'PostgreSQL Global Development Group, n.d.',
    'pgvector': 'Kane và cộng sự, 2024', 'hnsw': 'Malkov & Yashunin, 2020', 'kdtree': 'Bentley, 1975',
    'friedman': 'Friedman và cộng sự, 1977', 'weber': 'Weber và cộng sự, 1998', 'manning': 'Manning và cộng sự, 2008',
}
def arg(s, i):
    """Trả (nội dung trong cặp ngoặc nhọn bắt đầu tại s[i], chỉ số sau ngoặc đóng)."""
    assert s[i] == '{', s[i:i + 30]
    d = 0
    for j in range(i, len(s)):
        d += {'{': 1, '}': -1}.get(s[j], 0)
        if d == 0:
            return s[i + 1:j], j + 1
    raise ValueError(s[i:i + 40])


def cmd(s, name, fn, nargs=1):
    out, i = [], 0
    pat = re.compile(r'\\' + name + r'(?![a-zA-Z])\s*')
    while True:
        m = pat.search(s, i)
        if not m:
            return ''.join(out) + s[i:]
        out.append(s[i:m.start()])
        j, args = m.end(), []
        for _ in range(nargs):
            a, j = arg(s, j)
            args.append(a)
        out.append(fn(*args))
        i = j


def code(x):
    return '`' + x.replace('\\_', '_').replace('\\#', '#').replace('\\&', '&') + '`'


def text(s):
    """Chuyển phần chữ (ngoài công thức)."""
    s = cmd(s, 'textbf', lambda x: '**' + text(x) + '**')
    s = cmd(s, 'emph', lambda x: '*' + text(x) + '*')
    s = cmd(s, 'textit', lambda x: '*' + text(x) + '*')
    s = cmd(s, 'url', lambda x: x)
    s = re.sub(r'~?\\cite\{([^}]*)\}', lambda m: ' (' + '; '.join(CITE[k.strip()] for k in m.group(1).split(',')) + ')', s)
    s = re.sub(r'\\ref\{([^}]*)\}', r'@\1', s)
    s = s.replace("``", '“').replace("''", '”').replace('---', '—').replace('--', '–')
    s = s.replace('\\%', '%').replace('\\ldots', '…').replace('\\&', '&').replace('\\#', '#').replace('\\_', '_')
    s = s.replace('~', ' ')
    return s


def inl(s):
    """Chuyển một dòng, giữ nguyên công thức $...$."""
    s = cmd(s, 'texttt', lambda x: code(x.replace('$', '')))
    parts = re.split(r'(\$[^$]+\$)', s)
    return ''.join(p if p.startswith('$') and p.endswith('$') and len(p) > 1 else text(p) for p in parts).strip()


def split_cells(row):
    cells, cur, in_math = [], '', False
    for k, ch in enumerate(row):
        if ch == '$':
            in_math = not in_math
        if ch == '&' and not in_math and (k == 0 or row[k - 1] != '\\'):
            cells.append(cur)
            cur = ''
        else:
            cur += ch
    cells.append(cur)
    out = []
    for c in cells:
        c = c.strip()
        m = re.match(r'\\multicolumn\{(\d+)\}\{[^}]*\}\{(.*)\}$', c)
        if m:
            out += [m.group(2)] + [''] * (int(m.group(1)) - 1)
        else:
            out.append(c)
    return [inl(c) for c in out]


def table(lines):
    body = ' '.join(lines)
    body = re.sub(r'\\(toprule|midrule|bottomrule|hline)', '', body)
    body = re.sub(r'\\cmidrule\([a-z]*\)\{[^}]*\}', '', body)
    rows = [r.strip() for r in re.split(r'\\\\', body) if r.strip()]
    rows = [split_cells(r) for r in rows]
    out = ['| ' + ' | '.join(rows[0]) + ' |', '|' + '---|' * len(rows[0])]
    out += ['| ' + ' | '.join(r) + ' |' for r in rows[1:]]
    return out


def convert(src):
    L = src.split('\n')
    out, i, depth, counters = [], 0, 0, []
    while i < len(L):
        ln = L[i].strip()
        i += 1
        if not ln or ln.startswith('%'):
            if not ln:
                out.append('')
            continue
        if ln.startswith('\\begin{thebibliography}') or ln.startswith('\\end{document}'):
            break
        if re.match(r'\\(clearpage|phantomsection|addcontentsline|pdfbookmark|enlargethispage|Needspace|setcounter|vspace|hfill|FloatBarrier)', ln):
            continue
        m = re.match(r'\\phan\{(.*)\}$', ln)
        if m:
            out += ['', '# ' + inl(m.group(1)), '']
            continue
        m = re.match(r'\\(section|subsection)(\*?)\{(.*?)\}(?:\\label\{(.*?)\})?$', ln)
        if m:
            lvl = '#' if m.group(2) else ('##' if m.group(1) == 'section' else '###')
            title = inl(m.group(3)) + (' {-}' if m.group(2) else '') + (f' {{#{m.group(4)}}}' if m.group(4) else '')
            out += ['', lvl + ' ' + title, '']
            continue
        if ln.startswith('\\begin{figure}'):
            blk = []
            while not L[i].strip().startswith('\\end{figure}'):
                blk.append(L[i])
                i += 1
            i += 1
            b = '\n'.join(blk)
            lab = re.search(r'\\label\{(.*?)\}', b).group(1)
            path = '../hinh/' + re.search(r'\\includegraphics(?:\[.*?\])?\{(.*?)\}', b).group(1).replace('.pdf', '.png')
            cap = inl(re.search(r'\\caption\{(.*)\}\\label', b).group(1))
            out += ['', f'![{cap} {{#{lab}}}]({path})', '']
            continue
        if ln.startswith('\\begin{table}'):
            blk = []
            while not L[i].strip().startswith('\\end{table}'):
                blk.append(L[i].strip())
                i += 1
            i += 1
            capl = next(x for x in blk if x.startswith('\\caption'))
            cap, j = arg(capl, len('\\caption'))
            lab = re.search(r'\\label\{(.*?)\}', capl).group(1)
            k0 = next(k for k, x in enumerate(blk) if x.startswith('\\begin{tabular'))
            k1 = next(k for k, x in enumerate(blk) if x.startswith('\\end{tabular'))
            out += ['', f'Bảng: {inl(cap)} {{#{lab}}}'] + table(blk[k0 + 1:k1]) + ['']
            continue
        if ln.startswith('\\begin{verbatim}'):
            out.append('```')
            while not L[i].strip().startswith('\\end{verbatim}'):
                out.append(L[i])
                i += 1
            i += 1
            out.append('```')
            continue
        if ln.startswith('\\['):
            blk = []
            while not L[i].strip().startswith('\\]'):
                blk.append(L[i].strip())
                i += 1
            i += 1
            out += ['', '$$' + ' '.join(blk) + '$$', '']
            continue
        m = re.match(r'\\begin\{(itemize|enumerate)\}', ln)
        if m:
            counters.append(m.group(1))
            continue
        if re.match(r'\\end\{(itemize|enumerate)\}', ln):
            counters.pop()
            continue
        m = re.match(r'\\item\s*(.*)$', ln)
        if m:
            ind = '   ' * (len(counters) - 1) if counters[-1] == 'enumerate' else '  ' * (len(counters) - 1)
            mark = '1.' if counters[-1] == 'enumerate' else '-'
            out.append(f'{ind}{mark} {inl(m.group(1))}')
            continue
        if ln.startswith('\\'):
            m2 = re.match(r'\\(begin|end|centering|small|hfill|textit)', ln)
            if m2 and not ln.startswith('\\textbf'):
                sys.stderr.write(f'bỏ qua dòng {i}: {ln[:70]}\n')
                continue
        out.append(inl(ln))
    s = '\n'.join(out)
    return re.sub(r'\n{3,}', '\n\n', s).strip() + '\n'


if __name__ == '__main__':
    src = open(sys.argv[1], encoding='utf-8').read()
    a = src.index('\\section*{Lời nói đầu}')
    print(convert(src[a:]))
