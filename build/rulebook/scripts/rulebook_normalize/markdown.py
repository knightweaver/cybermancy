from __future__ import annotations
import html
import re
from html.parser import HTMLParser
from pathlib import Path

INCLUDE_RE = re.compile(
    r'^\s*\{%\s*include-markdown\s+["\'](?P<target>[^"\']+)["\'](?P<opts>.*?)%\}\s*$',
    re.MULTILINE,
)
HEADING_RE = re.compile(r'^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$', re.MULTILINE)
LINK_RE = re.compile(r'(?<!!)\[(?P<label>[^\]]+)\]\((?P<target>[^)\s]+)(?:\s+"[^"]*")?\)')
IMAGE_RE = re.compile(r'!\[(?P<alt>[^\]]*)\]\((?P<target>[^)\s]+)(?:\s+"[^"]*")?\)')


def normalize_heading_text(title: str) -> str:
    title = re.sub(r'\s+\{#.*?\}\s*$', '', title).strip()
    return re.sub(r'\s+', ' ', title)


def segment_before_heading(text: str, level: int, heading: str, include_boundary: bool = False) -> str:
    wanted = normalize_heading_text(heading).casefold()
    for m in HEADING_RE.finditer(text):
        if len(m.group('marks')) == level and normalize_heading_text(m.group('title')).casefold() == wanted:
            return text[:m.end() if include_boundary else m.start()].rstrip() + '\n'
    raise ValueError(f'Segmentation heading not found: H{level} {heading}')


def _heading_sections(text: str):
    matches = list(HEADING_RE.finditer(text))
    if not matches:
        return [('__preamble__', 0, text)]
    out = [('__preamble__', 0, text[:matches[0].start()])]
    for i, m in enumerate(matches):
        level = len(m.group('marks'))
        end = len(text)
        for later in matches[i+1:]:
            if len(later.group('marks')) <= level:
                end = later.start(); break
        out.append((normalize_heading_text(m.group('title')), level, text[m.start():end]))
    return out


def select_named_sections(text: str, headings: list[str], include_preamble: bool = True) -> str:
    wanted = {normalize_heading_text(h).casefold() for h in headings}
    matches = list(HEADING_RE.finditer(text))
    chunks = []
    if include_preamble:
        chunks.append(text[:matches[0].start()] if matches else text)
    selected_ranges = []
    for i, m in enumerate(matches):
        title = normalize_heading_text(m.group('title')).casefold()
        if title not in wanted:
            continue
        level = len(m.group('marks'))
        end = len(text)
        for later in matches[i+1:]:
            if len(later.group('marks')) <= level:
                end = later.start(); break
        selected_ranges.append((m.start(), end))
    for start, end in selected_ranges:
        chunks.append(text[start:end])
    return '\n\n'.join(x.rstrip() for x in chunks if x.strip()).rstrip() + '\n'


def split_h2_sections(text: str):
    matches = list(re.finditer(r'^##\s+(.+?)\s*$', text, re.MULTILINE))
    if not matches:
        return [('__preamble__', text)]
    out = [('__preamble__', text[:matches[0].start()])]
    for i, m in enumerate(matches):
        end = matches[i+1].start() if i+1 < len(matches) else len(text)
        out.append((normalize_heading_text(m.group(1)), text[m.start():end]))
    return out


def segment_rules_index(text: str, keep: set[str], drop: set[str]) -> str:
    sections = split_h2_sections(text)
    chunks = []
    keep_cf = {k.casefold() for k in keep}
    drop_cf = {k.casefold() for k in drop}
    for title, body in sections:
        if title == '__preamble__':
            chunks.append(body.rstrip())
        elif title.casefold() in keep_cf:
            chunks.append(body.rstrip())
        elif title.casefold() in drop_cf:
            continue
        else:
            raise ValueError(f'Unclassified rules/index.md section: {title}')
    return '\n\n'.join(x for x in chunks if x.strip()).rstrip() + '\n'


def drop_include_matching(text: str, needle: str) -> str:
    def repl(m):
        return '' if needle in m.group('target') else m.group(0)
    return INCLUDE_RE.sub(repl, text)


def contains_unresolved_jinja(text: str) -> bool:
    return bool(re.search(r'\{\{.*?\}\}|\{%.*?%\}', text, re.DOTALL))


def mkdocs_admonitions_to_divs(text: str) -> str:
    lines = text.splitlines()
    out, i = [], 0
    pat = re.compile(r'^(?P<indent>\s*)(?P<kind>!!!|\?\?\?)\s+(?P<type>[\w-]+)(?:\s+"(?P<title>[^"]*)")?\s*$')
    while i < len(lines):
        m = pat.match(lines[i])
        if not m:
            out.append(lines[i]); i += 1; continue
        typ = m.group('type'); title = m.group('title')
        out.append(f'::: {{.admonition .{typ}}}')
        if title:
            out.extend([f'**{title}**', ''])
        i += 1
        while i < len(lines):
            line = lines[i]
            if line.startswith('    '):
                out.append(line[4:]); i += 1
            elif not line.strip():
                out.append(''); i += 1
            else:
                break
        out.append(':::')
    return '\n'.join(out) + ('\n' if text.endswith('\n') else '')


def shift_headings(text: str, minimum_level: int = 3) -> str:
    levels = [len(m.group('marks')) for m in HEADING_RE.finditer(text)]
    if not levels:
        return text
    delta = max(0, minimum_level - min(levels))
    if not delta:
        return text
    def repl(m):
        level = min(6, len(m.group('marks')) + delta)
        return '#' * level + ' ' + m.group('title')
    return HEADING_RE.sub(repl, text)


class _HTMLToMarkdown(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.list_stack = []
        self.link_stack = []
        self.in_fast_play = 0
    def emit(self, s):
        if not self.in_fast_play:
            self.out.append(s)
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'section' and 'cybermancy-fast-play' in attrs.get('class', ''):
            self.in_fast_play += 1; return
        if self.in_fast_play:
            return
        if tag in {'p','div','section','article'}: self.emit('\n\n')
        elif tag == 'br': self.emit('\n')
        elif tag in {'strong','b'}: self.emit('**')
        elif tag in {'em','i'}: self.emit('*')
        elif tag in {'ul','ol'}: self.list_stack.append([tag, 0]); self.emit('\n')
        elif tag == 'li':
            if self.list_stack:
                self.list_stack[-1][1] += 1
                marker = f"{self.list_stack[-1][1]}. " if self.list_stack[-1][0] == 'ol' else '- '
            else: marker = '- '
            self.emit('\n' + '  ' * max(0, len(self.list_stack)-1) + marker)
        elif tag in {'h1','h2','h3','h4','h5','h6'}:
            self.emit('\n\n' + '#' * int(tag[1]) + ' ')
        elif tag == 'a': self.link_stack.append(attrs.get('href','')); self.emit('[')
        elif tag == 'img':
            src = attrs.get('src',''); alt = attrs.get('alt','')
            if src: self.emit(f'![{alt}]({src})')
        elif tag == 'hr': self.emit('\n\n---\n\n')
        elif tag == 'blockquote': self.emit('\n\n> ')
        elif tag == 'code': self.emit('`')
        elif tag == 'pre': self.emit('\n\n```\n')
        elif tag == 'table': self.emit('\n\n')
        elif tag == 'tr': self.emit('\n')
        elif tag in {'th','td'}: self.emit(' | ')
    def handle_endtag(self, tag):
        if tag == 'section' and self.in_fast_play:
            self.in_fast_play -= 1; return
        if self.in_fast_play: return
        if tag in {'strong','b'}: self.emit('**')
        elif tag in {'em','i'}: self.emit('*')
        elif tag in {'ul','ol'}:
            if self.list_stack: self.list_stack.pop()
            self.emit('\n')
        elif tag == 'a':
            href = self.link_stack.pop() if self.link_stack else ''
            self.emit(f']({href})' if href else ']')
        elif tag == 'code': self.emit('`')
        elif tag == 'pre': self.emit('\n```\n')
        elif tag in {'p','div','section','article','blockquote'}: self.emit('\n\n')
    def handle_data(self, data): self.emit(data)


def html_to_markdown(text: str) -> str:
    if '<' not in text or '>' not in text:
        return text
    p = _HTMLToMarkdown(); p.feed(text); p.close()
    out = ''.join(p.out)
    out = re.sub(r'[ \t]+\n', '\n', out)
    out = re.sub(r'\n{3,}', '\n\n', out)
    return html.unescape(out).strip()


def apply_assembly_selector(path: str, text: str, assembly_record: dict) -> str:
    mode = assembly_record.get('assemblyMode', 'whole-document')
    if mode == 'whole-document':
        return text
    selector = assembly_record.get('selector', {})
    if path == 'docs/player-facing/index.md':
        return segment_before_heading(text, 1, 'The Event: The Resonance Cascade', False)
    if path == 'docs/player-facing/rules/index.md':
        # Step 3 is authoritative: document lead + Critical Fails and descendants only.
        # "Document lead" means the H1/title plus introductory prose before the first H2.
        first_h2 = re.search(r'^##\s+', text, re.MULTILINE)
        lead = text[:first_h2.start()] if first_h2 else text
        critical = select_named_sections(text, ['Critical Fails', 'Critical fails'], include_preamble=False)
        return (lead.rstrip() + '\n\n' + critical.lstrip()).rstrip() + '\n'
    if path == 'docs/gm-facing/world/timeline.md':
        return select_named_sections(text, ['Philosophical Interpretation', 'Tone and Themes'], include_preamble=False)
    raise ValueError(f'No deterministic selector implementation for segmented source: {path}: {selector!r}')


def normalize_authored_markdown(path: str, text: str, assembly_record: dict) -> str:
    text = apply_assembly_selector(path, text, assembly_record)
    text = mkdocs_admonitions_to_divs(text)
    # include-markdown is prohibited in the normalized intermediate.
    if INCLUDE_RE.search(text):
        raise ValueError(f'Unresolved include-markdown remains after segmentation: {path}')
    # Remove Jinja comments; actual executable statements/expressions remain blockers.
    text = re.sub(r'\{#.*?#\}', '', text, flags=re.DOTALL)
    if contains_unresolved_jinja(text):
        raise ValueError(f'Unresolved Jinja remains after normalization: {path}')
    text = html_to_markdown(text)
    text = shift_headings(text, 3)
    return text.strip() + '\n'


def extract_links(text: str) -> list[str]:
    return [m.group('target') for m in LINK_RE.finditer(text)]


def extract_images(text: str) -> list[str]:
    return [m.group('target') for m in IMAGE_RE.finditer(text)]
