# Vision

Removes AI design defaults from visual work: audits HTML, CSS or screenshots against twenty slop indicators, applies the fixes, commits a brief to a three-color direction, generates textured backgrounds, and teaches the vocabulary needed to direct a model.

The material comes from the Unslop School course in [unslop-school.html](unslop-school.html): twenty terms, twenty indicators, twenty fixes in four moves, three palette studies and twenty-two textures, adapted from Charles Liu's short videos on AI design. The course ends with six prompts for building skills. This tool is those six skills, built once as capabilities of one library so any agent or script can call them.

## Goals

- `audit` and `scan` tell a person which defaults a design shows, with evidence they can check, a score out of twenty and the three fixes to make first. `scan` is static and free; `audit` adds a model's judgment of whether a choice was deliberate.
- `unslop` turns that reading into a diff that keeps the content, brand colours and layout intent, and only writes when asked.
- `direct` and `contrast` take a design past clean to committed: one concrete scene, three colours with roles that pass WCAG AA, type the subject would use, and CSS tokens.
- `texture` replaces flat fills and purple gradients with a background from the subject's world, as code under 3 KB that keeps text readable.
- `tutor` teaches the twenty terms with live demos, so a non-designer can ask for what they want by name.
- `antislop` chains the rest into one entry point, reporting a before and after score.
- `reference` hands the course material to any caller as data, and `route` names the capability and Agent Skill a job calls for, so an agent never has to guess.

## Non-Goals

- Not a renderer or a browser. Screenshots are read by the model; HTML is read as text. Visual regression and pixel measurement belong to other tools.
- Not a design system. It emits a handful of tokens and leaves component libraries to the project.
- Not a copywriting tool. It shortens and sharpens existing copy and never invents claims.
- Not a judge of taste. The twenty indicators are tells, not rules; a repeated, subject-driven choice is reported as deliberate and left alone.

## Principles

- The library is the tool. The CLI and any other surface are thin wrappers over it.
- Deterministic capabilities run with no model provider configured, and never refuse to load without one.
- The intelligence is behind an interface, so another implementation is a new module rather than a rewrite.
- One source of truth for the course material: `knowledge.py`, read by prompts, scans and `reference` alike.
- The tool works on Windows, macOS, and Linux seamlessly.
