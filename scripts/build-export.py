#!/usr/bin/env python3
"""Gera export/index.html e export/embed.html a partir do index.html.

- CSS escopado em .improvet-lp (não vaza pro construtor nem sofre colisão de classes)
- Remove CSS morto (hero antigo e nav, que não existem mais no HTML)
- Keyframes renomeados com prefixo ilp- (evita colisão com animações do construtor)
- Imagens otimizadas em export/assets/ e referenciadas por URL absoluta
- Repassa a query string da página (UTMs, fbclid, gclid...) para os links do Typebot

Uso: python3 scripts/build-export.py
"""
import re
import shutil
import urllib.parse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "export"
ASSETS = OUT / "assets"
BASE_URL = "https://improvet-landing.vercel.app/export/assets/"
SCOPE = ".improvet-lp"

DEAD = re.compile(r"^(\.hero(?!-espera)\b|\.hero-(text|scroll|badge|cta-row)\b|nav\b)")


def split_selectors(sel):
    parts, depth, cur = [], 0, ""
    for ch in sel:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur.strip())
            cur = ""
        else:
            cur += ch
    parts.append(cur.strip())
    return [p for p in parts if p]


def scope_selector(p):
    if p == "*":
        return [SCOPE, f"{SCOPE} *"]
    if p in ("html", "body", ":root"):
        return [SCOPE]
    if p.startswith("*::") or p.startswith("*:"):
        return [f"{SCOPE} {p}"]
    return [f"{SCOPE} {p}"]


def transform_css(css):
    out, i = [], 0
    while i < len(css):
        j = css.find("{", i)
        if j < 0:
            out.append(css[i:])
            break
        sel = css[i:j]
        depth, k = 1, j + 1
        while depth:
            if css[k] == "{":
                depth += 1
            elif css[k] == "}":
                depth -= 1
            k += 1
        body = css[j + 1:k - 1]
        lead = sel[: len(sel) - len(sel.lstrip())]
        s = sel.strip()
        # comentários antes do seletor ficam junto dele
        comments = "".join(c + "\n" + lead.lstrip("\n") for c in re.findall(r"/\*.*?\*/", s, flags=re.S))
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.S).strip()
        if s.startswith("@media") or s.startswith("@supports"):
            inner = transform_css(body)
            if inner.strip():
                out.append(f"{lead}{comments}{s} {{{inner}}}")
        elif s.startswith("@keyframes"):
            name = s.split()[1]
            out.append(f"{lead}{comments}@keyframes ilp-{name} {{{body}}}")
        elif s.startswith("@"):
            out.append(f"{lead}{comments}{s} {{{body}}}")
        else:
            parts = [p for p in split_selectors(s) if not DEAD.match(p)]
            parts = [p for p in parts if p != "html"]
            if parts:
                scoped = []
                for p in parts:
                    scoped += scope_selector(p)
                out.append(f"{lead}{comments}{', '.join(dict.fromkeys(scoped))} {{{body}}}")
        i = k
    return "".join(out)


def export_image(rel):
    """Copia/otimiza a imagem para export/assets e devolve a URL absoluta."""
    src = ROOT / urllib.parse.unquote(rel)
    stem = re.sub(r"[^a-z0-9]+", "-", src.stem.lower().replace(".png", "")).strip("-")
    if src.stat().st_size > 300_000:
        name = stem + ".webp"
        im = Image.open(src)
        if im.width > 1600:
            im = im.resize((1600, round(im.height * 1600 / im.width)), Image.LANCZOS)
        im.save(ASSETS / name, "WEBP", quality=85, method=6)
    else:
        name = stem + src.suffix.lower()
        shutil.copyfile(src, ASSETS / name)
    return BASE_URL + name


UTM_SCRIPT = """
  // Repassa UTMs e demais parâmetros da URL da página para os links do Typebot
  (function() {
    var qs = window.location.search.replace(/^\\?/, '');
    if (!qs) return;
    document.querySelectorAll('.improvet-lp a[href*="typebot.co"]').forEach(function(a) {
      a.href = a.href + (a.href.indexOf('?') > -1 ? '&' : '?') + qs;
    });
  })();
"""


def main():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    if ASSETS.exists():
        shutil.rmtree(ASSETS)
    ASSETS.mkdir(parents=True)

    head_links = "\n".join(re.findall(r'<link [^>]*fonts\.(?:googleapis|gstatic)[^>]*>', html))
    css = html[html.index("<style>") + 7: html.index("</style>")]
    body = html[html.index("<body>") + 6: html.index("</body>")]
    script = body[body.index("<script>"):]
    markup = body[: body.index("<script>")].strip()

    # CSS
    css = transform_css(css)
    names = set(re.findall(r"@keyframes ilp-([\w-]+)", css))
    for n in names:
        css = re.sub(rf"(animation(?:-name)?\s*:[^;{{}}]*?)(?<![\w-]){re.escape(n)}(?![\w-])", rf"\1ilp-{n}", css)

    # imagens: só as usadas (no markup e nas regras CSS que sobraram)
    cache = {}

    def repl(m):
        rel = m.group(2)
        if rel not in cache:
            cache[rel] = export_image(rel)
        return m.group(1) + cache[rel]

    pat = re.compile(r"""((?:src=["']|url\(['"]?))(images/[^'")]+)""")
    css = pat.sub(repl, css)
    markup = pat.sub(repl, markup)

    # JS: animações/carrossel + repasse de UTMs
    script = script.replace("</script>", UTM_SCRIPT + "</script>")

    wrapped = f'<div class="improvet-lp">\n{markup}\n</div>'
    style = f"<style>\n{css.strip()}\n  {SCOPE} {{ width: 100%; }}\n</style>"

    embed = f"<!-- Improvet · landing page (bloco HTML para construtores) -->\n{head_links}\n{style}\n\n{wrapped}\n\n{script}\n"
    title = re.search(r"<title>.*?</title>", html).group(0)
    desc = re.search(r'<meta name="description"[^>]*>', html).group(0)
    full = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
{title}
{desc}
{head_links}
{style}
<style>html, body {{ margin: 0; padding: 0; }}</style>
</head>
<body>
{wrapped}

{script}
</body>
</html>
"""
    (OUT / "index.html").write_text(full, encoding="utf-8")
    (OUT / "embed.html").write_text(embed, encoding="utf-8")
    print(f"{len(cache)} imagens em export/assets")
    for rel, url in cache.items():
        print(" ", urllib.parse.unquote(rel), "->", url.rsplit("/", 1)[1])


if __name__ == "__main__":
    main()
