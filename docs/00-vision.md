# Vision

Removes AI design defaults from visual work: audits HTML, CSS or screenshots against twenty slop indicators, applies the fixes, commits a brief to a three-color direction, generates textured backgrounds, and teaches the vocabulary needed to direct a model.

Explicit prose mode brings the same evidence-first method to existing text and Markdown, integrating
Stop-Slop's prose discipline while preserving author voice and factual meaning.

The material comes from the Unslop School course in [unslop-school.html](unslop-school.html): twenty terms, twenty indicators, twenty fixes in four moves, three palette studies and twenty-two textures, adapted from Charles Liu's short videos on AI design. The course ends with six prompts for building skills. This tool is those six skills, built once as capabilities of one library so any agent or script can call them.

## Goals

- `audit` and `scan` tell a person which defaults a design shows, with evidence they can check, a score out of twenty and the three fixes to make first. `scan` is static and free: its score counts candidate indicators, not visual quality. `audit` adds a model's judgment of whether a choice was deliberate; confirm actual problems before rewriting.
- `unslop` turns that reading into a diff that keeps the content, brand colours and layout intent, and only writes when asked.
- `scan`, `audit` and `unslop` with `prose=True` review or edit writing. Prose reports separate objective problems from review cues, anchor findings to the source, and abstain on authorship without a score.
- Editor, research partner and designer are scoped roles over those existing capabilities. Research review maps claims to supplied evidence and returns questions about reasoning to the caller; design review separates source observations from inspected visual states and task impact. See [roles](roles.md).
- `direct` and `contrast` take a design past clean to committed: one concrete scene, three colours with roles that pass WCAG AA, type the subject would use, and CSS tokens.
- `texture` creates an optional background from the subject's world when requested, as code under 3 KB that keeps text readable.
- `tutor` teaches the twenty terms with live demos, so a non-designer can ask for what they want by name.
- `antislop` chains the rest into one entry point, reporting a before and after score.
- `reference` hands the course material to any caller as data, and `route` names the capability and Agent Skill a job calls for, so an agent never has to guess.

## Non-Goals

- Not a renderer or a browser. Screenshots are read by the model; HTML is read as text. Visual regression and pixel measurement belong to other tools.
- Not a design system. It emits a handful of tokens and leaves component libraries to the project.
- Not an author or an authorship detector. It edits existing writing without inventing claims; it does not assign an AI probability. Facts, uncertainty, attribution, references, quotes, dialect and intentional rhetoric take priority over stylistic preferences.
- Not comprehensive fact checking. A scoped source or logic review leaves unavailable evidence unverified and never contacts the original author.
- Not a judge of taste. The twenty indicators are tells, not rules; a repeated, subject-driven choice is reported as deliberate and left alone.

## Principles

- The library is the tool. The CLI and any other surface are thin wrappers over it.
- Deterministic capabilities run with no model provider configured, and never refuse to load without one.
- The intelligence is behind an interface, so another implementation is a new module rather than a rewrite.
- One source of truth for the course material: `knowledge.py`, read by prompts, scans and `reference` alike.
- Shared prose discipline applies to prose mode and model-backed copy review in visual work. Stylistic tendencies are contextual cues, not proof of authorship or automatic rewrite rules. See [evidence and limits](prose-evidence.md).
- The tool works on Windows, macOS, and Linux seamlessly.
