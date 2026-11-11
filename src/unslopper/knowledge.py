"""The course material every capability draws on: terms, indicators, fixes, textures, palette studies.

Adapted from Charles Liu's short videos on AI design, as organised by the Unslop School course in docs/unslop-school.html.
One source of truth: prompts, deterministic scans and the reference command all read from here.
"""

from unslopper.schemas import Fix, Indicator, Move, PaletteStudy, Swatch, Term, Texture

TERMS: tuple[Term, ...] = (
    Term(
        name="Kerning",
        meaning="Adjusting the space between one specific pair of letters, like A and V, so the gaps look even.",
        ai_note="Fonts ship with kerning tables. Models rarely break them, but they often add global letter-spacing that fights them.",
    ),
    Term(
        name="Optical centre",
        meaning="The point that looks centered to the eye, which sits slightly above the true middle. A play triangle needs nudging right for the same reason.",
        ai_note="Generated layouts center by the math, so icons in buttons often look off.",
    ),
    Term(
        name="Tabular numbers",
        meaning="Digits that all take the same width, so columns of figures line up and counters do not jitter as they change.",
        ai_note="Prices, tables and timers in AI mockups almost always use the default proportional digits.",
    ),
    Term(
        name="Layout shift",
        meaning="Content jumping around as images, fonts or data load in. Fixed by reserving space before the content arrives.",
        ai_note="Models write the finished state and forget the loading one.",
    ),
    Term(
        name="Tracking",
        meaning="Uniform spacing across a whole run of text. Loosen it for small caps, tighten it slightly for large display type, leave body text alone.",
        ai_note="The tell is negative tracking applied to everything, including small text.",
    ),
    Term(
        name="Optimistic update",
        meaning="Showing the result of an action immediately, before the server confirms, then rolling back if it fails. Makes apps feel instant.",
        ai_note="Ask for it by name. Without it, generated UIs show a spinner on every like and checkbox.",
    ),
    Term(
        name="x-height",
        meaning="The height of lowercase letters. A taller x-height reads larger at the same point size, which matters when pairing two fonts.",
        ai_note="Mismatched x-heights are why a body font and a heading font can look like they belong to different sites.",
    ),
    Term(
        name="Touch target",
        meaning="The tappable area of a control, which can be bigger than what is drawn. Aim for at least 44 by 44 points.",
        ai_note="Tiny icon buttons are a common mobile miss in generated code.",
    ),
    Term(
        name="Leading",
        meaning="The vertical space between lines, set as line-height. Body text breathes at about 1.5; big headlines want closer to 1.1.",
        ai_note="Models default to one line-height for everything, which leaves headlines looking gappy.",
    ),
    Term(
        name="Origin-aware animation",
        meaning="A menu or popover grows out of the button that opened it, rather than from the center of the screen.",
        ai_note="An easy instruction that makes a generated interface feel designed.",
    ),
    Term(
        name="OKLCH",
        meaning="A color space built around how people perceive lightness. Two colors with the same L value look equally bright, so scales and themes stay even.",
        ai_note="Ask the model to build palettes in OKLCH and its tints stop going muddy.",
    ),
    Term(
        name="Widow",
        meaning="A single word stranded on the last line of a paragraph or heading. CSS text-wrap: pretty and balance fix most of them.",
        ai_note="Very common in generated headlines, which are often set too wide.",
    ),
    Term(
        name="Safe area",
        meaning="The parts of a phone screen not covered by the notch, the rounded corners or the home bar.",
        ai_note="Generated mobile layouts often put buttons under the home indicator.",
    ),
    Term(
        name="Stagger",
        meaning="Starting each item's animation a few milliseconds after the previous one, so a list arrives in a cascade.",
        ai_note="Used with restraint it feels crafted. Used on every element it is another tell.",
    ),
    Term(
        name="Line length",
        meaning="How many characters fit on one line of text. Comfortable reading sits around 45 to 75.",
        ai_note="Full-width paragraphs on desktop are a quick sign nobody checked.",
    ),
    Term(
        name="Affordance",
        meaning="A visual cue that tells you how something can be used: a raised button, an underlined link, a drag handle.",
        ai_note="When every element is a bordered box, nothing has an affordance, because everything looks clickable.",
    ),
    Term(
        name="Combobox",
        meaning="A text field joined to a list: you type, the list filters, you pick. The right control for long option lists.",
        ai_note="Name it and you get filtering and keyboard support instead of a 200-item dropdown.",
    ),
    Term(
        name="Interruptible animation",
        meaning="An animation that can change direction mid-flight when the user acts again, instead of finishing first.",
        ai_note="Models write fixed CSS transitions that queue up and feel sluggish.",
    ),
    Term(
        name="Progressive disclosure",
        meaning="Showing the essentials first and revealing advanced options only when someone asks for them.",
        ai_note="The antidote to over-detailed UI, slop indicator 5.",
    ),
    Term(
        name="Shared element transition",
        meaning="One element, like a card's image, smoothly grows into its place on the next screen. The View Transitions API does this natively.",
        ai_note="A single one of these does more than ten decorative effects.",
    ),
)

MOVES: dict[Move, str] = {
    "Subtract": "Most slop is additive. Start here, it is the cheapest work.",
    "Focus": "Decide what matters most and say it specifically.",
    "Systematize": "Replace one-off choices with a few rules applied everywhere.",
    "Respond": "Design the moments between states, where real products feel alive.",
}

FIXES: tuple[Fix, ...] = (
    Fix(
        id=1,
        name="Delete filler badges",
        how="If a pill says New, Beta or AI-powered on every item, it says nothing. Keep badges only for real state, like Sold out.",
        move="Subtract",
    ),
    Fix(
        id=2,
        name="Drop redundant labels",
        how="An eyebrow that repeats the heading, a label that names the obvious. Delete it and check whether anything was lost.",
        move="Subtract",
    ),
    Fix(
        id=3,
        name="Unitalicize random words",
        how="Italics are for one word of genuine stress or a title. Three per headline is decoration.",
        move="Subtract",
    ),
    Fix(
        id=4,
        name="Mono only where needed",
        how="Monospace belongs to code, data and terminals. Everywhere else it is costume.",
        move="Subtract",
    ),
    Fix(
        id=5,
        name="Use a design system",
        how="Define a handful of color, type and spacing tokens and use only those. Most mud comes from one-off values.",
        move="Systematize",
    ),
    Fix(
        id=6,
        name="Show the actual product",
        how="Replace abstract illustrations and fake dashboards with a real screenshot, the real output or a live demo.",
        move="Focus",
    ),
    Fix(
        id=7,
        name="Enlarge the main feature",
        how="Pick the one thing the page exists for and make it clearly bigger than everything else.",
        move="Focus",
    ),
    Fix(
        id=8,
        name="Group with spacing",
        how="Related things sit closer together, unrelated things further apart. Spacing does what borders and dividers were doing.",
        move="Systematize",
    ),
    Fix(
        id=9,
        name="Make headlines specific",
        how="Say what the thing does for this reader. A headline that fits any product fits none.",
        move="Focus",
    ),
    Fix(
        id=10,
        name="Emphasize the CTA",
        how="One solid primary action per view. Secondary actions become quiet links.",
        move="Focus",
    ),
    Fix(
        id=11,
        name="Add an accent colour",
        how="One saturated color, used sparingly for the thing you want clicked or noticed.",
        move="Systematize",
    ),
    Fix(
        id=12,
        name="Keep icons consistent",
        how="One icon family, one stroke weight, one size grid. Mixed sets read as assembled.",
        move="Systematize",
    ),
    Fix(
        id=13,
        name="Remove embellishments",
        how="Sparkles, glows, decorative arrows, extra nodes in diagrams. If it carries no meaning, cut it.",
        move="Subtract",
    ),
    Fix(
        id=14,
        name="Inner radius = outer - padding",
        how="Nested rounded corners stay concentric when the inner radius equals the outer radius minus the gap between them.",
        move="Systematize",
    ),
    Fix(
        id=15,
        name="Improve text contrast",
        how="Grey text at 40 percent opacity on a gradient fails people. Aim for WCAG AA, 4.5 to 1 for body text.",
        move="Systematize",
    ),
    Fix(
        id=16,
        name="Wrap headlines properly",
        how="Use text-wrap: balance on headings and set a max width in ch, so lines break where a person would break them.",
        move="Focus",
    ),
    Fix(
        id=17,
        name="Align by eye, not pixels",
        how="Round shapes, triangles and type overshoot their boxes. Nudge until it looks aligned, then trust your eye.",
        move="Systematize",
    ),
    Fix(
        id=18,
        name="Use tabular nums",
        how="Turn on tabular figures anywhere numbers stack or change: prices, tables, timers, stats.",
        move="Systematize",
    ),
    Fix(
        id=19,
        name="Add loading states",
        how="Design the skeleton, the empty state and the error, so the layout holds still while data arrives.",
        move="Respond",
    ),
    Fix(
        id=20,
        name="Animate useful feedback",
        how="Motion should confirm something: added to cart, saved, moved. Animation without information is noise.",
        move="Respond",
    ),
)

# The order fixes are worth doing in: the cheapest high-impact subtraction first, state design last.
PRIORITY: tuple[int, ...] = (1, 2, 3, 4, 13, 9, 10, 7, 6, 8, 5, 11, 15, 14, 16, 18, 12, 17, 19, 20)

INDICATORS: tuple[Indicator, ...] = (
    Indicator(
        name="Instrument Serif",
        layer="Type",
        description="An elegant italic display serif that became the go-to tasteful choice in 2025. It is a fine typeface, and now it is a signature of generated pages.",
        fix_ids=[5],
    ),
    Indicator(
        name="Excessive italics",
        layer="Type",
        description="Random words in a headline set in italics for flavor, as in Plans <em>first</em>. Acts <em>second</em>.",
        fix_ids=[3],
    ),
    Indicator(
        name="Negative kerning",
        layer="Type",
        description="Tight negative letter-spacing applied to every heading, sometimes to body text, so letters start to collide.",
        fix_ids=[5, 17],
    ),
    Indicator(
        name="Excessive mono fonts",
        layer="Type",
        description="Monospace used for labels, captions, nav and stats to look technical.",
        fix_ids=[4],
    ),
    Indicator(
        name="ALL CAPS subtitles",
        layer="Type",
        description="Small uppercase lines of adjectives under a headline. Hard to read and rarely read.",
        fix_ids=[2],
    ),
    Indicator(
        name="Periods in titles",
        layer="Type",
        description="Short staccato headlines with full stops. Fast. Confident. Generic.",
        fix_ids=[9, 16],
    ),
    Indicator(
        name="Gradient backgrounds",
        layer="Surface",
        description="The purple to blue diagonal, the most recognizable AI background there is.",
        fix_ids=[5, 11],
    ),
    Indicator(
        name="Color shades and opacities",
        layer="Surface",
        description="Many tints of one hue at 10, 20 and 40 percent opacity, stacked until hierarchy turns to mud.",
        fix_ids=[5, 11, 15],
    ),
    Indicator(
        name="Squircles",
        layer="Surface",
        description="Large soft corner radii on every card, button and image, with nested corners that do not line up.",
        fix_ids=[14],
    ),
    Indicator(
        name="Containers with borders",
        layer="Surface",
        description="Every block boxed in a thin border, often inside another bordered box.",
        fix_ids=[8],
    ),
    Indicator(
        name="Overusing dividers",
        layer="Surface",
        description="Hairline rules between every section and inside every card.",
        fix_ids=[8],
    ),
    Indicator(
        name="Dithering",
        layer="Surface",
        description="Pixel dither patterns added for retro texture, regardless of the brand.",
        fix_ids=[13],
    ),
    Indicator(
        name="ASCII images",
        layer="Surface",
        description="Pictures drawn from characters, used as a shortcut to look technical.",
        fix_ids=[13, 6],
    ),
    Indicator(
        name="Tags and pills",
        layer="Structure",
        description="Rounded badges on headings and cards that carry no real information.",
        fix_ids=[1],
    ),
    Indicator(
        name="Eyebrows",
        layer="Structure",
        description="A tiny uppercase label above every heading, usually repeating it.",
        fix_ids=[2],
    ),
    Indicator(
        name="Section numbering",
        layer="Structure",
        description="01, 02, 03 on content that has no real order.",
        fix_ids=[2],
    ),
    Indicator(
        name="Code breadcrumbs",
        layer="Structure",
        description="File paths, arrows and comment syntax used as decoration on marketing pages.",
        fix_ids=[4, 6],
    ),
    Indicator(
        name="Verbose, redundant text",
        layer="Content",
        description="Copy that restates the headline, stacks adjectives and says seamlessly.",
        fix_ids=[9, 2],
    ),
    Indicator(
        name="Over-the-top detailed UI",
        layer="Content",
        description="Fake dashboards crammed with tiny charts, numbers and status dots to look impressive.",
        fix_ids=[6, 7],
    ),
    Indicator(
        name="Overly detailed diagrams",
        layer="Content",
        description="Flowcharts with more boxes, arrows and glows than the idea needs.",
        fix_ids=[13],
    ),
)

LAYERS: dict[str, str] = {
    "Type": "Look at the letters before anything else.",
    "Surface": "Then look at fills, edges and effects.",
    "Structure": "Then the scaffolding around the content.",
    "Content": "Finally, what is actually being said and shown.",
}

TEXTURES: tuple[Texture, ...] = (
    Texture(name="Felt texture", use="Warm, tactile. Games, kids' products, crafts."),
    Texture(name="Fluted glass", use="Color seen through ribbed glass. Premium, architectural."),
    Texture(name="Thermal gradients", use="Heat-camera color. Data, energy, performance."),
    Texture(name="Water ripples", use="Interference rings. Calm, wellness, travel."),
    Texture(name="Speckled graphite", use="Dark, mineral, serious. Tools, finance."),
    Texture(name="Single-hue landscapes", use="Layered hills in one color. Outdoor, editorial."),
    Texture(name="Blueprint grids", use="Engineering, hardware, developer tools."),
    Texture(name="Halftone", use="Print and comics. Retro, editorial, zines."),
    Texture(name="Grainy gradients", use="Soft color with film grain. Calmer than a plain gradient."),
    Texture(name="Grass texture", use="Organic and literal. Sport, garden, outdoors."),
    Texture(name="Dithered images", use="Two-tone pixel shading. Use with an intent, not as decoration."),
    Texture(name="Paper texture", use="Publishing, stationery, anything about writing."),
    Texture(name="Contour lines", use="Topographic maps. Outdoors, data, geography."),
    Texture(name="Cloud sky", use="Airy and optimistic. Travel, weather, consumer."),
    Texture(name="Pixel mosaics", use="Chunky color blocks. Games, playful brands."),
    Texture(name="Lens distortion", use="A grid bending as if behind glass. Optics, cameras, AR."),
    Texture(name="Stippled gradients", use="Dots that thin out. Hand-made, scientific illustration."),
    Texture(name="Square-dot grids", use="A quiet technical ground. Dashboards, docs."),
    Texture(name="Blurred photos", use="A photo turned into soft color fields. Keeps mood, drops detail."),
    Texture(name="Iridescent shapes", use="Oil-slick color on a single form. Beauty, fashion."),
    Texture(name="Impressionist paintings", use="Visible brushwork. Culture, food, hospitality."),
    Texture(name="ASCII and pixels", use="Characters as pixels. Developer brands, when it means something."),
)

PALETTE_STUDIES: tuple[PaletteStudy, ...] = (
    PaletteStudy(
        name="Northern Time",
        mood="A mechanical watch brand, lit like the aurora",
        swatches=[
            Swatch(role="ground", hex="#000412", note="Black with a trace of blue, like a night sky"),
            Swatch(role="light", hex="#E8EEF2", note="Ice white for text and the steel case"),
            Swatch(role="signal", hex="#2BF08A", note="Aurora green, used only in the light trails"),
        ],
        typography="A high-contrast serif with wide-tracked small caps, luxury watchmaking's own vernacular",
    ),
    PaletteStudy(
        name="Three Days Louder",
        mood="A music festival that wants to feel like a crowd surge",
        swatches=[
            Swatch(role="ground", hex="#C9EF35", note="Lime, loud enough to read from across a field"),
            Swatch(role="light", hex="#111111", note="Near-black for heavy display type"),
            Swatch(role="signal", hex="#FF2E93", note="Hot pink as confetti in the photo"),
        ],
        typography="A fat, chunky display face set huge and tight, poster style",
    ),
    PaletteStudy(
        name="Still Waters",
        mood="A silent retreat in Kyoto, golden hour on water",
        swatches=[
            Swatch(role="ground", hex="#603E1E", note="Brown, warm and low like wood"),
            Swatch(role="light", hex="#F1D9A8", note="Pale gold for quiet text"),
            Swatch(role="signal", hex="#FFC34D", note="Glowing gold as light rays on the heron"),
        ],
        typography="A refined serif with generous tracking and lots of air",
    ),
)

# Words that name a feeling without committing to one; a direction built on them stays generic.
BANNED_ADJECTIVES: tuple[str, ...] = ("modern", "clean", "sleek", "minimal")
# Faces that read as generated in 2025 because every model reached for them.
DEFAULT_FACES: tuple[str, ...] = ("Instrument Serif", "Inter", "Space Grotesk")


def fix(fix_id: int) -> Fix:
    """The fix with this id; ids run 1 to 20."""
    for entry in FIXES:
        if entry.id == fix_id:
            return entry
    raise KeyError(fix_id)


def indicator(name: str) -> Indicator:
    """The indicator with this name, matched case-insensitively."""
    wanted = name.strip().lower()
    for entry in INDICATORS:
        if entry.name.lower() == wanted:
            return entry
    raise KeyError(name)


def fixes_for(indicator_names: list[str]) -> list[Fix]:
    """The fixes the named indicators call for, in priority order and without repeats."""
    needed = {fix_id for name in indicator_names for fix_id in indicator(name).fix_ids}
    return [fix(fix_id) for fix_id in PRIORITY if fix_id in needed]


def verdict(score: int) -> str:
    """The course's reading of a count of indicators present, out of 20."""
    if score <= 0:
        return "No defaults showing"
    if score <= 2:
        return "Mostly intentional. Check those were choices"
    if score <= 5:
        return "Some defaults showing"
    if score <= 9:
        return "Reads as generated"
    return "Pure default output"
