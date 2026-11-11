# The twenty design terms

Generated from `unslopper.knowledge.TERMS` in teaching order; `tests/test_tutor.py` checks it stays in sync.
Each entry is the course's meaning, then why generated designs tend to miss it.

## Kerning

Adjusting the space between one specific pair of letters, like A and V, so the gaps look even.

Why generated designs miss it: Fonts ship with kerning tables. Models rarely break them, but they often add global letter-spacing that fights them.

## Tracking

Uniform spacing across a whole run of text. Loosen it for small caps, tighten it slightly for large display type, leave body text alone.

Why generated designs miss it: The tell is negative tracking applied to everything, including small text.

## Leading

The vertical space between lines, set as line-height. Body text breathes at about 1.5; big headlines want closer to 1.1.

Why generated designs miss it: Models default to one line-height for everything, which leaves headlines looking gappy.

## x-height

The height of lowercase letters. A taller x-height reads larger at the same point size, which matters when pairing two fonts.

Why generated designs miss it: Mismatched x-heights are why a body font and a heading font can look like they belong to different sites.

## Tabular numbers

Digits that all take the same width, so columns of figures line up and counters do not jitter as they change.

Why generated designs miss it: Prices, tables and timers in AI mockups almost always use the default proportional digits.

## Line length

How many characters fit on one line of text. Comfortable reading sits around 45 to 75.

Why generated designs miss it: Full-width paragraphs on desktop are a quick sign nobody checked.

## Widow

A single word stranded on the last line of a paragraph or heading. CSS text-wrap: pretty and balance fix most of them.

Why generated designs miss it: Very common in generated headlines, which are often set too wide.

## Optical centre

The point that looks centered to the eye, which sits slightly above the true middle. A play triangle needs nudging right for the same reason.

Why generated designs miss it: Generated layouts center by the math, so icons in buttons often look off.

## Touch target

The tappable area of a control, which can be bigger than what is drawn. Aim for at least 44 by 44 points.

Why generated designs miss it: Tiny icon buttons are a common mobile miss in generated code.

## Safe area

The parts of a phone screen not covered by the notch, the rounded corners or the home bar.

Why generated designs miss it: Generated mobile layouts often put buttons under the home indicator.

## Affordance

A visual cue that tells you how something can be used: a raised button, an underlined link, a drag handle.

Why generated designs miss it: When every element is a bordered box, nothing has an affordance, because everything looks clickable.

## Combobox

A text field joined to a list: you type, the list filters, you pick. The right control for long option lists.

Why generated designs miss it: Name it and you get filtering and keyboard support instead of a 200-item dropdown.

## Progressive disclosure

Showing the essentials first and revealing advanced options only when someone asks for them.

Why generated designs miss it: The antidote to over-detailed UI, slop indicator 5.

## Layout shift

Content jumping around as images, fonts or data load in. Fixed by reserving space before the content arrives.

Why generated designs miss it: Models write the finished state and forget the loading one.

## OKLCH

A color space built around how people perceive lightness. Two colors with the same L value look equally bright, so scales and themes stay even.

Why generated designs miss it: Ask the model to build palettes in OKLCH and its tints stop going muddy.

## Optimistic update

Showing the result of an action immediately, before the server confirms, then rolling back if it fails. Makes apps feel instant.

Why generated designs miss it: Ask for it by name. Without it, generated UIs show a spinner on every like and checkbox.

## Origin-aware animation

A menu or popover grows out of the button that opened it, rather than from the center of the screen.

Why generated designs miss it: An easy instruction that makes a generated interface feel designed.

## Stagger

Starting each item's animation a few milliseconds after the previous one, so a list arrives in a cascade.

Why generated designs miss it: Used with restraint it feels crafted. Used on every element it is another tell.

## Interruptible animation

An animation that can change direction mid-flight when the user acts again, instead of finishing first.

Why generated designs miss it: Models write fixed CSS transitions that queue up and feel sluggish.

## Shared element transition

One element, like a card's image, smoothly grows into its place on the next screen. The View Transitions API does this natively.

Why generated designs miss it: A single one of these does more than ten decorative effects.
