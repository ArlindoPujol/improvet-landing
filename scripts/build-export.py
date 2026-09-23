#!/usr/bin/env python3
"""Gera export/index.html e export/embed.html a partir do index.html.

- CSS escopado em .improvet-lp (não vaza pro construtor nem sofre colisão de classes)
- Remove CSS sem uso (regras cujas classes não existem no HTML) e minifica
- Keyframes renomeados com prefixo ilp- (evita colisão com animações do construtor)
- Imagens e fontes copiadas para export/assets com hash no nome (cache longo seguro)
  e referenciadas por URL absoluta
- Repassa a query string da página (UTMs, fbclid, gclid...) para os links do Typebot

Uso: python3 scripts/build-export.py
"""
import hashlib
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "export"
ASSETS = OUT / "assets"
BASE_URL = "https://improvet-landing.vercel.app/export/assets/"
SCOPE = ".improvet-lp"

# classes adicionadas pelo JavaScript em tempo de execução
JS_CLASSES = {"visible", "in-view", "testimonial-dot", "active"}


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
    if p in ("body", ":root"):
        return [SCOPE]
    return [f"{SCOPE} {p}"]


def transform_css(css, known):
    """Escopa, renomeia keyframes e descarta regras cujas classes não existem no HTML."""
    out, i = [], 0
    while i < len(css):
        j = css.find("{", i)
        if j < 0:
            break
        s = css[i:j].strip()
        depth, k = 1, j + 1
        while depth:
            depth += {"{": 1, "}": -1}.get(css[k], 0)
            k += 1
        body = css[j + 1:k - 1]
        i = k
        if s.startswith("@media") or s.startswith("@supports"):
            inner = transform_css(body, known)
            if inner:
                out.append(f"{s}{{{inner}}}")
        elif s.startswith("@keyframes"):
            out.append(f"@keyframes ilp-{s.split()[1]}{{{body}}}")
        elif s.startswith("@"):
            out.append(f"{s}{{{body}}}")
        else:
            parts = [p for p in split_selectors(s)
                     if p != "html" and all(c in known for c in re.findall(r"\.([\w-]+)", p))]
            if parts:
                scoped = []
                for p in parts:
                    scoped += scope_selector(p)
                out.append(f"{','.join(dict.fromkeys(scoped))}{{{body}}}")
    return "".join(out)


def minify_css(css):
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    css = re.sub(r"\s+", " ", css)
    css = re.sub(r"\s*([{}:;,>])\s*", r"\1", css)
    css = css.replace(";}", "}")
    # espaço é obrigatório em alguns lugares que a regra acima colapsa
    css = re.sub(r"\band\(", "and (", css)
    return css.strip()


def export_asset(rel, cache):
    """Copia o arquivo para export/assets com hash no nome e devolve a URL absoluta."""
    if rel not in cache:
        src = ROOT / rel
        digest = hashlib.sha1(src.read_bytes()).hexdigest()[:8]
        name = f"{src.stem.replace('.png', '')}-{digest}{src.suffix}"
        shutil.copyfile(src, ASSETS / name)
        cache[rel] = BASE_URL + name
    return cache[rel]


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

    head_links = "\n".join(re.findall(r'<link rel="preload"[^>]*>', html))
    css = html[html.index("<style>") + 7: html.index("</style>")]
    body = html[html.index("<body>") + 6: html.index("</body>")]
    script = body[body.index("<script>"):]
    markup = body[: body.index("<script>")].strip()

    known = {c for attr in re.findall(r'class="([^"]+)"', markup) for c in attr.split()}
    known |= JS_CLASSES

    css = transform_css(re.sub(r"/\*.*?\*/", "", css, flags=re.S), known)
    for n in set(re.findall(r"@keyframes ilp-([\w-]+)", css)):
        css = re.sub(rf"(animation(?:-name)?\s*:[^;{{}}]*?)(?<![\w-]){re.escape(n)}(?![\w-])", rf"\1ilp-{n}", css)
    css = minify_css(css) + f"{SCOPE}{{width:100%}}"

    cache = {}
    asset_re = re.compile(r"(?<![\w/.-])((?:images|fonts)/[^'\")\s,]+)")
    css, markup, head_links = (asset_re.sub(lambda m: export_asset(m.group(1), cache), x)
                               for x in (css, markup, head_links))

    script = script.replace("</script>", UTM_SCRIPT + "</script>")
    wrapped = f'<div class="improvet-lp">\n{markup}\n</div>'
    style = f"<style>{css}</style>"

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
<style>html,body{{margin:0;padding:0}}</style>
</head>
<body>
{wrapped}

{script}
</body>
</html>
"""
    (OUT / "index.html").write_text(full, encoding="utf-8")
    (OUT / "embed.html").write_text(embed, encoding="utf-8")
    print(f"CSS: {len(css) // 1024} KB · {len(cache)} arquivos em export/assets")


if __name__ == "__main__":
    main()
