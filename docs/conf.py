from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

project = "tierproxy"
author = "tierproxy"
copyright = "2026, tierproxy"  # noqa: A001  # Sphinx-required name

try:
    from tierproxy._version import __version__ as _version
except Exception:
    _version = "0.0.0"

version = _version
release = _version

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_tabs.tabs",
    "sphinx_sitemap",
]

myst_enable_extensions = [
    "colon_fence",
    "deflist",
]
myst_heading_anchors = 3

source_suffix = {
    ".md": "markdown",
    ".rst": "restructuredtext",
}

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_title = "tierproxy — Python SDK"
html_logo = "_static/logo.svg"
html_favicon = "_static/favicon.ico"
html_static_path = ["_static"]
html_baseurl = "https://python.tierproxy.com/"
html_theme_options = {
    "source_repository": "https://github.com/tierproxy/python-sdk",
    "source_branch": "main",
    "source_directory": "docs/",
    "announcement": (
        "<em>v0.1.0 launching soon —</em> "
        "<a href='https://github.com/tierproxy/python-sdk/discussions'>watch the repo</a>."
    ),
}
html_meta = {
    "description": "Python SDK for tierproxy — multi-provider proxy infrastructure for AI/ML pipelines",
    "og:image": "https://python.tierproxy.com/_static/og-image.png",
    "og:type": "website",
}

autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
autodoc_mock_imports = [
    "httpx",
    "httpx_sse",
    "pydantic",
    "requests",
]

napoleon_google_docstring = True
napoleon_numpy_docstring = False

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pydantic": ("https://docs.pydantic.dev/latest/", None),
}
intersphinx_disabled_reftypes = ["std:doc"]
# Tolerate transient intersphinx fetch failures so -W builds remain stable.
intersphinx_timeout = 5

# sphinx-sitemap settings
sitemap_url_scheme = "{link}"

nitpicky = False
suppress_warnings = ["myst.header"]
