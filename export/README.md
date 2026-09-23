# Improvet · exportação da landing page

Versão estática da landing page, pronta para importar em qualquer construtor que aceite HTML personalizado. Não depende de Next.js, React, API ou rotas da Vercel.

## Arquivos

| Arquivo | Quando usar |
|---|---|
| `index.html` | Plataformas que recebem uma **página HTML completa** (upload de arquivo, hospedagem estática). |
| `embed.html` | Construtores que recebem um **bloco de HTML personalizado** (Rock Funnels, Elementor, Webflow Embed, WordPress, etc.). Cole o conteúdo inteiro do arquivo no bloco. |
| `assets/` | Cópia das imagens. Os arquivos HTML já apontam para elas por URL absoluta, então **não é preciso subir esta pasta**. |

## O que já vem resolvido

- **Imagens e fontes:** URLs públicas absolutas em `https://improvet-landing.vercel.app/export/assets/`, com hash no nome e cache de 1 ano. Imagens em WebP, com tamanhos diferentes para celular e desktop (`srcset`) e carregamento sob demanda abaixo da primeira dobra.
- **Fontes:** só os 7 pesos usados (Poppins, Inter Tight, DM Serif Display), com fontes reserva de mesmas medidas: o texto não "pula" quando a fonte carrega.
- **CSS:** todo escopado em `.improvet-lp`. Não altera o resto da página do construtor, e o CSS do construtor não quebra a landing.
- **Responsivo:** mesmo layout do site atual (desktop, tablet e celular).
- **JavaScript:** só o do navegador (animações ao rolar, carrossel de depoimentos, faixa animada no celular).
- **Botões/formulário:** todos os CTAs levam ao Typebot (`typebot.co/formul-rio-leads-7lc0byu`). A página não tem formulário próprio.
- **UTMs:** tudo que vier na URL da página (`utm_*`, `fbclid`, `gclid`...) é repassado automaticamente para o link do Typebot.

## Rock Funnels (e outros construtores de blocos)

- Cole o **`embed.html`**, não o `index.html`. O `index.html` traz `<!DOCTYPE>`, `<html>` e `<head>` próprios, que ficam inválidos dentro de um bloco.
- Título, descrição, idioma e favicon da página são configurados **no construtor** (configurações de SEO da página). Sem isso o Lighthouse perde pontos em SEO e acessibilidade.
- O Rock Funnels monta a página no navegador, depois de baixar o próprio JavaScript (~250 KB). Isso atrasa a primeira exibição e não dá para resolver pelo HTML da landing.

## Pixels e rastreamento

A página original **não tem** Pixel da Meta, Google Tag Manager, GA4 nem outro script de rastreamento. Instale-os pelo próprio construtor (campo de scripts do `<head>` ou integração nativa).

## Como gerar de novo

Depois de editar o `index.html` da raiz do repositório:

```bash
python3 scripts/build-export.py
```
