"""Search-engine metadata for the Streamlit app.

Streamlit serves a static index.html whose <head> only contains <title>Streamlit</title>; anything added with
st.markdown lands in the page body after JavaScript runs, so crawlers do not see it as page metadata.
inject_seo_metadata() therefore writes the title, description, Open Graph / Twitter tags and JSON-LD structured
data into Streamlit's own index.html (once; a backup of the original is kept next to it). The change applies to
pages served after the server has (re)started.
"""

import html
import json
import pathlib
import shutil

import streamlit as st

TITLE = "NiTiHf Austenite–Martensite Lattice Correspondence & XRD Peak Viewer"
DESCRIPTION = (
    "Free interactive tool for NiTi and NiTiHf shape memory alloys: calculate the crystallographic correspondence "
    "between B2 austenite and B19' martensite planes, d-spacings, transformation strains, angles between plane "
    "normals and X-ray diffraction peak positions (2θ) with Gaussian, Lorentzian and pseudo-Voigt peak profiles "
    "from your own lattice parameters."
)
KEYWORDS = (
    "NiTiHf, NiTi, nitinol, shape memory alloy, austenite, martensite, B2, B19', lattice correspondence, "
    "martensitic transformation, transformation strain, XRD, X-ray diffraction, d-spacing, peak position, "
    "pseudo-Voigt, Caglioti, crystallography"
)
AUTHOR = "Miroslav Lebeda"
# Public URL of the deployed app; fill in to add canonical / og:url tags.
APP_URL = ""

_MARKER = "<!-- seo-metadata: austenite-martensite -->"


def _head_html():
    json_ld = {
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": TITLE,
        "description": DESCRIPTION,
        "applicationCategory": "EducationalApplication",
        "operatingSystem": "Any (web browser)",
        "offers": {"@type": "Offer", "price": "0", "priceCurrency": "EUR"},
        "author": {"@type": "Person", "name": AUTHOR, "url": "https://bracerino.github.io/portfolio/"},
        "keywords": KEYWORDS,
    }
    if APP_URL:
        json_ld["url"] = APP_URL
    title, desc, kw = (html.escape(x, quote=True) for x in (TITLE, DESCRIPTION, KEYWORDS))
    url_tags = (f'<link rel="canonical" href="{APP_URL}" />\n    <meta property="og:url" content="{APP_URL}" />\n'
                if APP_URL else "")
    return f"""{_MARKER}
    <title>{title}</title>
    <meta name="description" content="{desc}" />
    <meta name="keywords" content="{kw}" />
    <meta name="author" content="{AUTHOR}" />
    <meta name="robots" content="index, follow" />
    {url_tags}<meta property="og:type" content="website" />
    <meta property="og:title" content="{title}" />
    <meta property="og:description" content="{desc}" />
    <meta name="twitter:card" content="summary" />
    <meta name="twitter:title" content="{title}" />
    <meta name="twitter:description" content="{desc}" />
    <script type="application/ld+json">{json.dumps(json_ld, ensure_ascii=False)}</script>
"""


def inject_seo_metadata():
    index = pathlib.Path(st.__file__).parent / "static" / "index.html"
    try:
        page = index.read_text(encoding="utf-8")
        if _MARKER in page:
            return
        backup = index.with_name("index.html.orig")
        if not backup.exists():
            shutil.copy(index, backup)
        page = page.replace("<title>Streamlit</title>", "", 1)
        page = page.replace("<head>", "<head>\n    " + _head_html(), 1)
        page = page.replace(
            "<noscript>You need to enable JavaScript to run this app.</noscript>",
            f"<noscript><h1>{html.escape(TITLE)}</h1><p>{html.escape(DESCRIPTION)}</p>"
            "<p>You need to enable JavaScript to run this app.</p></noscript>",
            1,
        )
        index.write_text(page, encoding="utf-8")
    except OSError:
        pass  # read-only installation: the app still works, only without the metadata
