# Unslopper website

A dependency-free static site in the Amplifier Smart Tools family. `index.html` is a two-minute page: the
tool in the vision's own terms, the recorded card before and after with its scores, one short row per
capability, the capability list, install, and the non-goals. `outputs.html` renders every recorded output in
full with the manifest, the routing table and the skills. `course.html` is the Unslop School, generated from
its single source. `docs/RECORDED-OUTPUTS.md` is generated from the same artifacts by the build, and the
check fails when it is stale.

## Build and preview

From the repository root, with Python 3.12 or later and nothing installed:

```bash
python3 scripts/build.py
python3 scripts/check.py
node --check site/site.js
python3 -m http.server 8000 --bind 127.0.0.1 --directory _site
```

Or `make build`, `make check`, `make preview` and `make test`. The build writes only this checkout's `_site/`
and refuses any other path or a symlink. Every link is relative, so the output works under a repository
subpath on GitHub Pages. Node is optional and only checks the browser script's syntax.

## Source ownership

- `site.json`: the name, the promise line, the hero's second paragraph, the first request, and the theme tokens
  the check compares against the vendored theme.
- `template.html`: the short landing page with `@@PLACEHOLDER@@` slots the build fills; `outputs.html` is
  built entirely in `scripts/build.py` from the same data; `style.css`: the tool's own rules over the family
  theme; `site.js`: copy buttons only, no network or storage; `assets/favicon.svg`.
- `artifacts/`: the recorded outputs and `manifest.json`, written by `scripts/capture_artifacts.py` and never
  edited by hand or by the build. The page renders them as they are: command, date, seconds and exit code from
  the manifest, values from each JSON file, `before.html`, `after.html` and `after-antislop.html` in sandboxed
  frames. A run that failed is reported as failed with its error; nothing stands in for a missing file. The
  front page shows one representative line per run; the full rendering is on `outputs.html`, and the same
  figures are written to `../docs/RECORDED-OUTPUTS.md`.
- `../src/unslopper/core/skill.py` `CAPABILITIES` and `../src/unslopper/capabilities/route/capability.py`
  `ROUTES`: read by `ast`, rendered as the compact capability lists on `index.html` and the full routing table
  on `outputs.html`.
- `../src/unslopper/SMART_TOOL.md`: the description; `../docs/00-vision.md`: the non-goals, verbatim.
- `../skills/*/SKILL.md`: names and descriptions for the skills section, every file as a plain download, and
  all of `skills/` as `unslopper-skills.zip` with a `.sha256` (fixed timestamps, so the digest is stable).
- `../docs/unslop-school.html`: the one source of the course. The build takes its body, moves its stylesheet to
  `assets/course.css` with every selector scoped under `.course` (the course's dark scheme is dropped because
  the family has one paper), moves its script to `assets/course.js` unchanged, drops its Google Fonts links,
  adds a visible note that the demo card is shown without its web font, and wraps it in the family masthead and
  footer. A short fitting block at the end of `course.css` keeps the course's look where the family theme uses
  the same class names (`.hero`, `.note`, `.copy`).
- `../src/unslopper/knowledge.py`: the check counts its terms, indicators, fixes and textures by regex and
  compares them with the course page's own tables (20, 20, 20, 22) and the six prompts with the six
  model-backed capabilities.

## Rendering model-written markup under a strict policy

`index.html` allows no inline script or style. The recorded card and the tutor demo carry inline styles, so
they render inside `frames/*.html`, each loaded in a sandboxed `<iframe>` with its own policy that allows
inline style and nothing from the network. The texture artifact is a canvas script; its code ships unchanged in
`assets/texture-artifact.js` and draws on the page's own canvas with the artifact's width and height. Colours
from `direct.json`, `contrast.json` and `texture.json` become classes in the generated `assets/artifacts.css`.
`course.html` allows inline style attributes (`style-src-attr`) because its demos set them; scripts stay external.

## The accent decision

The course's own method: a ground, a light and one signal colour under 10 percent of the screen. The ground
and the light are the family's paper `#f6f4ee` and ink `#252823`. The signal is `#9E3A1C`, a deep brick red
taken from the course page's own accent hue and darkened until it passes WCAG AA for body text on the family
paper: `unslopper contrast "#9E3A1C" "#f6f4ee"` reports 6.21 to 1. It appears on the primary action, link hover
and focus rings only. It is deliberately darker and cooler than the warm clay most generated pages reach for,
and far from the slop card's purple, so the before and after frames read at a glance. Everything else on the
page is the family's own: Georgia display, Arial body, gold brand mark, and monospace only for commands, code,
hex values and the artifacts' JSON. Sections are separated by spacing rather than hairlines, numbers are
tabular, headings use `text-wrap: balance`, and there is one primary call to action per view.

## What the check covers

`scripts/check.py` fails on root-relative or broken links and missing anchors, duplicate ids, pages without
exactly one h1 and `lang`, images without alt text, anything loaded from outside (scripts, styles, frames,
`@import`, remote `url()`), network or storage code in the scripts, downloads that differ from their sources,
zip membership or sha256 drift, any recorded run not rendered as the manifest records it on `outputs.html` or
missing its row on `index.html`, a capability not named on `index.html`, a route or skill not on `outputs.html`,
a stale `docs/RECORDED-OUTPUTS.md`, a course count that drifts from `knowledge.py`, an unscoped course selector,
and a scan score above 2 on `index.html` by the tool itself (`unslopper` on PATH, else `uv run unslopper`,
else skipped with a note). `course.html` is exempt from the scan because it embeds the slop card on purpose.
`outputs.html` is not scanned either: it quotes the audit's findings, buzzwords included, as evidence.

## Theme provenance and publication

`theme/style.css` and `theme/LICENSE` are the unchanged Amplifier Smart Tools family theme, version 0.1.0, as
shipped by Microsoft in `microsoft/amplifier-smart-tools/site/theme`; the stylesheet's SHA-256 is
`747e554913f98d918863299e92c9436acc123b8f41a5f9db32e2f4c5789c5ac8`. The theme is MIT licensed and its notice
is kept in `theme/LICENSE` and shipped as `assets/family-LICENSE.txt`. The family's own build script is not
used; `scripts/build.py` is this repository's own, standard library only. The masthead and footer carry the
family identity, Amplifier Smart Tools, as the theme prescribes, without Microsoft's team attribution, which
belongs to its own pages.

The site publishes to `michaeljabbour.github.io/amplifier-capability-unslopper` only when the Pages workflow
is dispatched by hand; pushes and pull requests build and check without publishing.
