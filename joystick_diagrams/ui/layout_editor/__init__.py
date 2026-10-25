"""Hybrid layout editor (spike S3).

A QWebEngineView hosts a vanilla-JS canvas that inlines the template SVG, finds the
placeholder slots and lets the user move, resize, hide and add boxes. Every completed
gesture is sent to Python as one layout op through QWebChannel (``bridge.py``), and the
page assets plus the template bytes are served over the ``jdeditor://`` scheme
(``scheme.py``) to avoid ``setHtml``'s 2 MB limit.

Nothing in here is wired into the main window yet; see ``spike.py`` for a launcher.
"""
