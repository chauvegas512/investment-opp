# HoHa Slide third-party notices

This file is a human-readable index. The complete attribution text remains in
`NOTICE`, and the authoritative license texts remain with their respective
packages and distributions.

## Presenton-derived portions

Some portions of HoHa Slide are derived from the Presenton project.

- Upstream project: https://github.com/presenton/presenton
- License: Apache License 2.0
- Copyright notice: retained in `LICENSE` and `NOTICE`
- Changes: described in `MODIFICATIONS.md` and the version-control history

The Presenton name and logos are not HoHa Slide product branding. Their use in
legal notices, historical database identifiers, or dependency identifiers is
solely to describe origin or technical compatibility.

## PptxGenJS

HoHa Slide's independent editable PowerPoint export path uses PptxGenJS.

- Project: https://github.com/gitbrent/PptxGenJS
- License: MIT

The PptxGenJS copyright and MIT license text must be included in commercial
distributions that bundle this dependency.

## Generated dependency notices

`NOTICE` includes generated notices for bundled JavaScript and Python
dependencies. Entries may only be removed after confirming that the relevant
code, binary, font, asset, or transitive dependency is absent from the shipped
artifact.

## PPTAgent evidence helpers

Smart render fingerprints reuse sha256/render_current/pptx_info from ICIP-CAS PPTAgent, commit `833cda553b343be0e486a93b0b57cac962cdd566`. The extracted dependency-free module is `servers/fastapi/services/vendor/pptagent_evidence.py`; the full MIT copyright/license is retained in `services/vendor/PPTAGENT_LICENSE`. HoHa adds an owner-authorized adapter for HTML/CSS/font/image dependencies. Upstream: https://github.com/icip-cas/PPTAgent.
