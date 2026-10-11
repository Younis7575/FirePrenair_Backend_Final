"""
Turns the website's server-rendered static pages (legal, about, how it works,
FAQ, features ...) into a JSON layout tree the mobile / tablet apps can render.

The pages carry no database content: their text lives in the Django templates
under ``home/templates/home``.  Instead of copying that text into the apps we
render the template's ``content`` block, run a tiny CSS cascade over the page's
own ``<style>`` rules (colour, background, font size/weight, alignment, flex /
grid direction) and emit a tree of blocks:

    hero      {title, text, image, height, style}
    heading   {level, text, style}
    paragraph {runs:[{t,b,i,href,c}], style}
    list      {ordered, items:[{runs, children:[list blocks]}], style}
    image     {src, alt}
    button    {text, href, style}
    icon      {name, style}
    faq       {title, blocks}
    row       {cols:[{span, blocks}]}               (bootstrap grid)
    group     {dir, wrap, justify, align, min_width, style, blocks}   (flex/grid)
    box       {style, blocks}                       (an element with its own background)

Nothing here is a model/DB lookup, so the whole module is read-only.
"""
import os
import re
from html.parser import HTMLParser

from django.conf import settings
from django.template import Context, engines
from django.template.loader_tags import BlockNode, ExtendsNode

TEMPLATE_DIR = os.path.join(settings.BASE_DIR, 'home', 'templates')

VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
        'meta', 'param', 'source', 'track', 'wbr'}
SKIP_TAGS = {'script', 'style', 'noscript', 'head', 'link', 'meta', 'header',
             'nav', 'svg', 'form', 'select', 'input', 'textarea', 'button',
             'iframe', 'video', 'audio', 'canvas', 'footer'}
INLINE_TAGS = {'a', 'b', 'strong', 'em', 'i', 'u', 'span', 'small', 'br',
               'mark', 'sup', 'sub', 'code'}
ICON_PREFIXES = ('ri-', 'fa-', 'bx', 'fas', 'far', 'fab', 'feather')
SKIP_CLASS_TOKENS = {'navbar-final', 'close-btn-final', 'sidebar-final',
                     'modal', 'mobile-sidebar', 'search-container-final'}


# ---------------------------------------------------------------- tiny DOM
class Node:
    __slots__ = ('tag', 'attrs', 'children', 'parent', 'text', 'style')

    def __init__(self, tag, attrs=None, parent=None, text=None):
        self.tag = tag
        self.attrs = dict(attrs or {})
        self.children = []
        self.parent = parent
        self.text = text
        self.style = {}

    @property
    def classes(self):
        return (self.attrs.get('class') or '').split()


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node('root')
        self.cur = self.root

    def handle_starttag(self, tag, attrs):
        n = Node(tag, attrs, self.cur)
        self.cur.children.append(n)
        if tag not in VOID:
            self.cur = n

    def handle_startendtag(self, tag, attrs):
        self.cur.children.append(Node(tag, attrs, self.cur))

    def handle_endtag(self, tag):
        n = self.cur
        while n is not None and n.tag != tag:
            n = n.parent
        if n is not None and n.parent is not None:
            self.cur = n.parent

    def handle_data(self, data):
        if data:
            self.cur.children.append(Node('#text', parent=self.cur, text=data))


def parse_html(html):
    b = _Builder()
    b.feed(html)
    return b.root


# ---------------------------------------------------------------- CSS
_PROPS = {'color', 'background', 'background-color', 'font-size', 'font-weight',
          'text-align', 'display', 'flex-direction', 'flex-wrap',
          'justify-content', 'align-items', 'height', 'min-height',
          'grid-template-columns', 'box-shadow', 'border', 'border-radius',
          'text-transform', 'font-style', 'flex-grow', 'flex'}


def _strip_at_blocks(css):
    out, i = [], 0
    while i < len(css):
        if css[i] == '@':
            j = css.find('{', i)
            if j < 0:
                break
            depth, k = 1, j + 1
            while k < len(css) and depth:
                depth += (css[k] == '{') - (css[k] == '}')
                k += 1
            i = k
        else:
            out.append(css[i])
            i += 1
    return ''.join(out)


def parse_css(css):
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    css = _strip_at_blocks(css)
    rules = []
    for m in re.finditer(r'([^{}]+)\{([^{}]*)\}', css):
        decl = {}
        for part in m.group(2).split(';'):
            if ':' not in part:
                continue
            k, v = part.split(':', 1)
            k = k.strip().lower()
            if k in _PROPS:
                decl[k] = v.strip()
        if not decl:
            continue
        for sel in m.group(1).split(','):
            sel = sel.strip()
            if not sel or any(c in sel for c in ':>+~[*#'):
                continue
            parts = sel.split()
            spec = (0,
                    sum(p.count('.') for p in parts),
                    sum(1 for p in parts if re.match(r'^[a-zA-Z]', p)))
            rules.append((spec, len(rules), parts, decl))
    rules.sort(key=lambda r: (r[0], r[1]))
    return [(r[2], r[3]) for r in rules]


def _compound_match(part, node):
    m = re.match(r'^([a-zA-Z][a-zA-Z0-9]*)?((?:\.[\w-]+)*)$', part)
    if not m:
        return False
    tag, cls = m.group(1), [c for c in m.group(2).split('.') if c]
    if tag and tag != node.tag:
        return False
    return all(c in node.classes for c in cls)


def _selector_matches(parts, node):
    if not _compound_match(parts[-1], node):
        return False
    anc = node.parent
    for part in reversed(parts[:-1]):
        while anc is not None and not _compound_match(part, anc):
            anc = anc.parent
        if anc is None:
            return False
        anc = anc.parent
    return True


def _inline_style(node):
    d = {}
    for part in (node.attrs.get('style') or '').split(';'):
        if ':' in part:
            k, v = part.split(':', 1)
            k = k.strip().lower()
            if k in _PROPS:
                d[k] = v.strip()
    return d


_HEX = re.compile(r'#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b')
_RGB = re.compile(r'rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)')


def _color(value):
    if not value:
        return None
    m = _HEX.search(value)
    if m:
        h = m.group(0)
        if len(h) == 4:
            h = '#' + ''.join(c * 2 for c in h[1:])
        return h.lower()
    m = _RGB.search(value)
    if m:
        return '#%02x%02x%02x' % tuple(int(x) for x in m.groups())
    named = {'white': '#ffffff', 'black': '#000000', 'transparent': None}
    return named.get(value.strip().lower())


def _px(value):
    m = re.match(r'^\s*(\d+(?:\.\d+)?)px', value or '')
    return float(m.group(1)) if m else None


def apply_css(node, rules):
    """Compute node.style (flat, only the properties the apps use)."""
    if node.tag == '#text':
        return
    computed = {}
    for parts, decl in rules:
        if _selector_matches(parts, node):
            computed.update(decl)
    computed.update(_inline_style(node))
    # inheritable props: colour / alignment / size from the nearest ancestor
    inh = node.parent.style if node.parent is not None else {}
    s = {}
    for key in ('color', 'text_align', 'font_size', 'font_weight'):
        if key in inh:
            s[key] = inh[key]
    c = _color(computed.get('color'))
    if c:
        s['color'] = c
    if 'text-align' in computed:
        s['text_align'] = computed['text-align'].strip()
    fs = _px(computed.get('font-size'))
    if fs:
        s['font_size'] = fs
    fw = computed.get('font-weight')
    if fw:
        s['font_weight'] = 700 if fw in ('bold', 'bolder') else (
            int(fw) if fw.isdigit() else 400)
    # non-inherited
    bg = computed.get('background-color') or computed.get('background')
    if bg and 'url(' not in bg:
        bc = _color(bg)
        if bc:
            s['bg'] = bc
    if computed.get('box-shadow') or computed.get('border'):
        s['bordered'] = True
    br = _px(computed.get('border-radius'))
    if br is not None:
        s['radius'] = br
    for k in ('display', 'flex-direction', 'flex-wrap', 'justify-content',
              'align-items', 'grid-template-columns', 'text-transform',
              'font-style', 'flex-grow', 'flex'):
        if k in computed:
            s[k.replace('-', '_')] = computed[k].strip()
    node.style = s
    for ch in node.children:
        apply_css(ch, rules)


def _own(style):
    """The non-inherited part of a style, trimmed for the wire."""
    out = {}
    for k in ('color', 'text_align', 'font_size', 'font_weight', 'bg',
              'radius', 'bordered', 'text_transform', 'font_style'):
        if k in style:
            out[k] = style[k]
    return out


# ---------------------------------------------------------------- walk
def _text_of(node):
    if node.tag == '#text':
        return node.text
    if node.tag in SKIP_TAGS or node.tag == 'br':
        return ' ' if node.tag == 'br' else ''
    return ''.join(_text_of(c) for c in node.children)


def _clean(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def _runs(node, base=None, out=None):
    base = dict(base or {})
    out = [] if out is None else out
    for ch in node.children:
        if ch.tag == '#text':
            t = re.sub(r'\s+', ' ', ch.text)
            if t.strip() or (t and out):
                out.append(dict(base, t=t))
        elif ch.tag == 'br':
            out.append(dict(base, t='\n'))
        elif ch.tag in ('script', 'style', 'svg') or ch.tag in ('ul', 'ol'):
            continue
        elif ch.tag == 'i' and any(c.startswith(ICON_PREFIXES) for c in ch.classes) \
                and not _clean(_text_of(ch)):
            continue
        else:
            b = dict(base)
            if ch.tag in ('b', 'strong'):
                b['b'] = True
            if ch.tag in ('em', 'i'):
                b['i'] = True
            if 'highlight' in ch.classes:
                b['b'] = True
                if ch.style.get('color'):
                    b['c'] = ch.style['color']
            elif ch.tag == 'span' and ch.style.get('font_weight', 400) >= 600:
                b['b'] = True
            if ch.tag == 'a' and ch.attrs.get('href'):
                b['href'] = ch.attrs['href']
            _runs(ch, b, out)
    return out


def _trim_runs(runs):
    # collapse whitespace at the edges
    while runs and not runs[0]['t'].strip() and runs[0]['t'] != '\n':
        runs.pop(0)
    while runs and not runs[-1]['t'].strip() and runs[-1]['t'] != '\n':
        runs.pop()
    if runs:
        runs[0] = dict(runs[0], t=runs[0]['t'].lstrip(' '))
        runs[-1] = dict(runs[-1], t=runs[-1]['t'].rstrip(' '))
    return runs


def _is_inline_only(node):
    for ch in node.children:
        if ch.tag == '#text':
            continue
        if ch.tag in INLINE_TAGS and not _is_button(ch) and _is_inline_only(ch):
            continue
        return False
    return True


def _col_span(classes):
    pick = {}
    for c in classes:
        m = re.match(r'^col(?:-(sm|md|lg|xl|xxl))?-(\d+)$', c)
        if m:
            pick[m.group(1) or 'xs'] = int(m.group(2))
    for k in ('lg', 'xl', 'md', 'xxl', 'sm', 'xs'):
        if k in pick:
            return pick[k]
    return 12 if not any(c == 'col' or c.startswith('col-') for c in classes) else 12


def _icon_name(node):
    for c in node.classes:
        if c.startswith(('ri-', 'bx-', 'fa-')) and c not in ('fa-solid', 'fa-brands', 'fa-regular'):
            return c
    return None


def _list_block(node):
    items = []
    for li in node.children:
        if li.tag != 'li':
            continue
        runs = _trim_runs(_runs(li))
        kids = [_list_block(c) for c in li.children if c.tag in ('ul', 'ol')]
        for ch in li.children:  # block children inside li (div/p)
            if ch.tag in ('div', 'p') and ch.tag != 'li':
                sub = _trim_runs(_runs(ch))
                if sub:
                    runs = runs + ([{'t': ' '}] if runs else []) + sub
        if runs or kids:
            items.append({'runs': runs, 'children': kids})
    return {'type': 'list', 'ordered': node.tag == 'ol', 'items': items,
            'style': _own(node.style)}


def _is_button(node):
    cl = set(node.classes)
    return node.tag == 'a' and (
        bool(node.style.get('bg')) or
        bool(cl & {'btn', 'category-btn-final', 'cta-button', 'btn-primary',
                   'interactive-button'}) or any('btn' in c for c in cl))


class Walker:
    def __init__(self, base_url=''):
        self.base_url = base_url

    def url(self, src):
        return src

    def walk_children(self, node):
        out, loose = [], []

        def flush():
            if loose:
                runs = _trim_runs(list(loose))
                if runs and any(r['t'].strip() for r in runs):
                    out.append({'type': 'paragraph', 'runs': runs,
                                'style': _own(node.style)})
                loose.clear()

        for ch in node.children:
            if ch.tag == '#text' or (ch.tag in INLINE_TAGS and _is_inline_only(ch)
                                     and not _is_button(ch) and (
                                         ch.tag != 'i' or _clean(_text_of(ch)))):
                tmp = Node('tmp')
                tmp.children = [ch]
                tmp.style = node.style
                loose.extend(_runs(tmp))
                continue
            flush()
            out.extend(self.walk(ch))
        flush()
        return out

    def walk(self, node):
        tag = node.tag
        if tag == '#text':
            return []
        if tag == 'button' and 'openCorporateModal' in (node.attrs.get('onclick') or ''):
            t = _clean(''.join(_text_of(c) for c in node.children))
            return [{'type': 'button', 'text': t, 'href': 'app://corporate-project',
                     'style': _own(node.style)}] if t else []
        if tag in SKIP_TAGS:
            return []
        classes = set(node.classes)
        if classes & SKIP_CLASS_TOKENS or node.attrs.get('hidden') is not None:
            return []
        if re.search(r'display\s*:\s*none', node.attrs.get('style') or ''):
            return []
        if tag == 'img':
            src = node.attrs.get('src') or ''
            return [{'type': 'image', 'src': src, 'alt': node.attrs.get('alt', '')}] if src else []
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            t = _clean(_text_of(node))
            if not t:
                return []
            return [{'type': 'heading', 'level': int(tag[1]), 'text': t,
                     'style': _own(node.style)}]
        if tag == 'p':
            runs = _trim_runs(_runs(node))
            if not runs:
                return []
            return [{'type': 'paragraph', 'runs': runs, 'style': _own(node.style)}]
        if tag in ('ul', 'ol'):
            anchors = _findall(node, lambda n: n.tag == 'a')
            if anchors and all((a.attrs.get('href') or '').startswith('#') for a in anchors):
                return []  # in-page navigation
            lb = _list_block(node)
            return [lb] if lb['items'] else []
        if tag == 'i':
            nm = _icon_name(node)
            return [{'type': 'icon', 'name': nm, 'style': _own(node.style)}] if nm else []
        if _is_button(node):
            t = _clean(_text_of(node))
            return [{'type': 'button', 'text': t, 'href': node.attrs.get('href', ''),
                     'style': _own(node.style)}] if t else []
        if tag == 'a' and not _is_inline_only(node):
            return self.walk_children(node)
        if tag == 'a':
            runs = _trim_runs(_runs(Node('tmp') if False else _wrap(node)))
            return [{'type': 'paragraph', 'runs': runs, 'style': _own(node.style)}] if runs else []
        if tag == 'table':
            return self._table(node)
        # FAQ accordion card
        if 'faq-card' in classes:
            title_el = _find(node, lambda n: 'faq-title' in n.classes)
            body_el = _find(node, lambda n: 'faq-detail' in n.classes)
            if title_el:
                return [{'type': 'faq', 'title': _clean(_text_of(title_el)),
                         'blocks': self.walk_children(body_el) if body_el else []}]
        # bootstrap grid
        if 'row' in classes and node.children and any(
                c.tag != '#text' and any(k == 'col' or k.startswith('col-') for k in c.classes)
                for c in node.children):
            cols = []
            for c in node.children:
                if c.tag == '#text':
                    continue
                blocks = self.walk_children(c) if any(
                    k == 'col' or k.startswith('col-') for k in c.classes) else self.walk(c)
                if blocks:
                    cols.append({'span': _col_span(c.classes), 'blocks': blocks,
                                 'order': _order(c.classes)})
            return [{'type': 'row', 'cols': cols}] if cols else []
        # a div / section made of inline content only -> a paragraph
        if tag in ('div', 'span', 'section', 'li') and node.children and _is_inline_only(node) \
                and _clean(_text_of(node)):
            runs = _trim_runs(_runs(node))
            st = _own(node.style)
            boxed = bool(node.style.get('bg') or node.style.get('bordered'))
            if boxed:
                st = {k: v for k, v in st.items() if k not in ('bg', 'radius', 'bordered')}
            blocks = [{'type': 'paragraph', 'runs': runs, 'style': st}]
            return self._maybe_box(node, blocks)
        # hero banner (about/legal pages): title + intro over a background image
        if 'hero-section' in classes or 'hero-content' in classes and not _find_up(node, 'hero-section'):
            h = _find(node, lambda n: n.tag in ('h1', 'h2'))
            p = _find(node, lambda n: n.tag == 'p')
            if h:
                return [{'type': 'hero', 'title': _clean(_text_of(h)),
                         'text': _clean(_text_of(p)) if p else '',
                         'style': _own(node.style),
                         'title_style': _own(h.style),
                         'text_style': _own(p.style) if p else {}}]
            if 'hero-section' in classes and not _clean(_text_of(node)):
                return [{'type': 'hero', 'title': '', 'text': '',
                         'style': _own(node.style), 'title_style': {},
                         'text_style': {}}]
        blocks = self.walk_children(node)
        if not blocks:
            return []
        disp = node.style.get('display', '')
        if 'flex' in disp or 'grid' in disp:
            direction = 'column' if 'column' in node.style.get('flex_direction', '') else 'row'
            minw = None
            m = re.search(r'minmax\(\s*(\d+)px', node.style.get('grid_template_columns', ''))
            if m:
                minw = int(m.group(1))
            wrapped = []
            for ch in node.children:
                if ch.tag == '#text':
                    continue
                sub = self.walk(ch)
                if len(sub) > 1 or (sub and ch.style.get('flex_grow')) or (
                        sub and ch.style.get('flex', '').startswith('1')):
                    grow = bool(ch.style.get('flex_grow') or ch.style.get('flex', '').startswith('1'))
                    wrapped.append({'type': 'group', 'dir': 'column', 'wrap': False,
                                    'justify': '', 'align': '', 'min_width': None,
                                    'grow': grow, 'style': {}, 'blocks': sub})
                else:
                    wrapped.extend(sub)
            blocks = wrapped or blocks
            blocks = [{'type': 'group', 'dir': direction,
                       'wrap': 'wrap' in node.style.get('flex_wrap', '') or 'grid' in disp,
                       'justify': node.style.get('justify_content', ''),
                       'align': node.style.get('align_items', ''),
                       'min_width': minw, 'style': _own(node.style),
                       'blocks': blocks}]
            return blocks
        return self._maybe_box(node, blocks)

    def _maybe_box(self, node, blocks):
        s = node.style
        if s.get('bg') or s.get('bordered'):
            return [{'type': 'box', 'style': _own(s), 'blocks': blocks}]
        return blocks

    def _table(self, node):
        rows = []
        for tr in _findall(node, lambda n: n.tag == 'tr'):
            cells = [_clean(_text_of(td)) for td in tr.children if td.tag in ('td', 'th')]
            if cells:
                rows.append(cells)
        return [{'type': 'table', 'rows': rows}] if rows else []


def _wrap(node):
    tmp = Node('tmp')
    tmp.children = [node]
    tmp.style = node.style
    return tmp


def _order(classes):
    for c in classes:
        m = re.match(r'^order-(?:lg-)?(\d+)$', c)
        if m:
            return int(m.group(1))
    return 0


def _find(node, pred):
    for ch in node.children:
        if pred(ch):
            return ch
        r = _find(ch, pred)
        if r is not None:
            return r
    return None


def _findall(node, pred, out=None):
    out = [] if out is None else out
    for ch in node.children:
        if pred(ch):
            out.append(ch)
        _findall(ch, pred, out)
    return out


def _find_up(node, cls):
    p = node.parent
    while p is not None:
        if cls in p.classes:
            return p
        p = p.parent
    return None


# ---------------------------------------------------------------- render
def _template_source(name):
    path = os.path.join(TEMPLATE_DIR, 'home', name)
    with open(path, encoding='utf-8') as fh:
        return fh.read()


def _render_content_block(template_name, request=None, extra=None):
    src = _template_source(template_name)
    # The site header / footer / chatbot are app chrome in the apps.
    src = re.sub(r"\{%\s*include\s+['\"]home/partials/(new_header|footer|chatbot|"
                 r"home-head-top-cat|corporate_modal)\.html['\"]\s*%\}", '', src)
    tpl = engines['django'].from_string(src)
    root_nodes = tpl.template.nodelist
    block = None
    for n in root_nodes:
        if isinstance(n, ExtendsNode):
            for b in n.nodelist:
                if isinstance(b, BlockNode) and b.name == 'content':
                    block = b
        elif isinstance(n, BlockNode) and n.name == 'content':
            block = n
    ctx = Context(extra or {})
    if request is not None:
        ctx['request'] = request
        ctx['user'] = getattr(request, 'user', None)
    ctx.template = tpl.template
    with ctx.render_context.push_state(tpl.template):
        html = block.nodelist.render(ctx) if block is not None else tpl.render(extra or {}, request)
    return html


def _page_css(template_name):
    """Every <style> block of the template (also those in extra_css)."""
    src = _template_source(template_name)
    styles = re.findall(r'<style[^>]*>.*?</style>', src, flags=re.S)
    if not styles:
        return ''
    head = "{% load static %}{% load i18n %}"
    try:
        html = engines['django'].from_string(head + '\n'.join(styles)).render({})
    except Exception:
        html = '\n'.join(styles)
    return '\n'.join(re.findall(r'<style[^>]*>(.*?)</style>', html, flags=re.S))


def _hero_image(css):
    m = re.search(r'\.hero-section\s*\{[^}]*?url\(\s*[\'"]?([^\'")]+)', css, flags=re.S)
    return m.group(1).strip() if m else None


def _title_of(template_name):
    m = re.search(r'\{%\s*block title\s*%\}(.*?)\{%\s*endblock', _template_source(template_name), flags=re.S)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ''


def build_page(template_name, request=None, extra=None):
    html = _render_content_block(template_name, request, extra)
    css_text = _page_css(template_name)
    rules = parse_css(css_text)
    root = parse_html(re.sub(r'<!--.*?-->', '', html, flags=re.S))
    apply_css(root, rules)
    blocks = Walker().walk_children(root)
    hero_img = _hero_image(css_text)
    hero = None
    for b in _iter_blocks(blocks):
        if b.get('type') == 'hero':
            hero = b
            if hero_img:
                b['image'] = hero_img
            break
    return {
        'title': _title_of(template_name),
        'blocks': blocks,
        'hero_image': hero_img,
    }


def _iter_blocks(blocks):
    for b in blocks:
        yield b
        for k in ('blocks',):
            if k in b:
                yield from _iter_blocks(b[k])
        for c in b.get('cols', []):
            yield from _iter_blocks(c['blocks'])


# ---------------------------------------------------------------- pricing
class _StubPlan:
    id = 0

    def __getattr__(self, name):
        return lambda: 0 if name.startswith(('int_', 'dec_')) else ''


_PLAN_CLASSES = (('free_plan', 'FreeTier'), ('starter_plan', 'StartPrenair'),
                 ('biz_plan', 'BizPrenair'), ('entre_plan', 'EntrePrenair'))


def build_pricing_cards():
    """Feature matrix of pricing.html: one card per plan + the key-features list.

    Prices/ids come from the PricingPlan table (see pricing_api); the website
    keeps the per-plan feature bullets in the template, so they are read from
    there.
    """
    stub = _StubPlan()
    html = _render_content_block('pricing.html', None, {
        'plans': [], 'basic_plan': stub, 'start_plan': stub,
        'biz_plan': stub, 'entre_plan': stub})
    root = parse_html(re.sub(r'<!--.*?-->', '', html, flags=re.S))
    cards = []
    for cls, title in _PLAN_CLASSES:
        col = _find(root, lambda n, c=cls: c in n.classes)
        if col is None:
            continue
        t = _find(col, lambda n: 'title-font' in n.classes)
        feats = []
        for li in _findall(col, lambda n: n.tag == 'li'):
            txt = _clean(_text_of(li))
            feats.append({'text': txt, 'enabled': bool(txt) and 'text-muted' not in li.classes})
        cards.append({'key': cls.replace('_plan', ''),
                      'title': _clean(_text_of(t)) if t else title,
                      'db_title': title,
                      'features': [f for f in feats if f['text']]})
    key = []
    for item in _findall(root, lambda n: 'feature-list' in n.classes):
        for row in item.children:
            spans = [s for s in row.children if s.tag == 'span']
            if len(spans) >= 2:
                key.append({'icon': _clean(_text_of(spans[0])),
                            'text': _clean(_text_of(spans[1]))})
    return {'plan_cards': cards, 'key_features': key}
