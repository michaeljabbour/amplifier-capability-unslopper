"""Colour math every capability can trust: hex parsing, WCAG 2 contrast and OKLCH, with no model involved."""

import math

from unslopper.schemas import ContrastResult, UnslopperError

AA_BODY = 4.5
AA_LARGE = 3.0
AAA_BODY = 7.0


def parse_hex(value: str) -> tuple[int, int, int]:
    """`#RGB` or `#RRGGBB`, with or without the hash, as 0 to 255 channels."""
    digits = value.strip().lstrip("#")
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    if len(digits) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in digits):
        raise UnslopperError(f"'{value}' is not a hex colour. Use #RGB or #RRGGBB, like #2BF08A.")
    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def normalize_hex(value: str) -> str:
    """The colour as `#RRGGBB` in upper case."""
    return "#{:02X}{:02X}{:02X}".format(*parse_hex(value))


def relative_luminance(value: str) -> float:
    """WCAG 2 relative luminance, 0 for black and 1 for white."""
    red, green, blue = (_linear(channel / 255) for channel in parse_hex(value))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    """WCAG 2 contrast ratio, from 1 to 21, rounded to two decimals."""
    lighter, darker = sorted((relative_luminance(foreground), relative_luminance(background)), reverse=True)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def contrast(foreground: str, background: str) -> ContrastResult:
    """The ratio and the WCAG levels it passes."""
    ratio = contrast_ratio(foreground, background)
    return ContrastResult(
        foreground=normalize_hex(foreground),
        background=normalize_hex(background),
        ratio=ratio,
        aa_body=ratio >= AA_BODY,
        aa_large=ratio >= AA_LARGE,
        aaa_body=ratio >= AAA_BODY,
    )


def to_oklch(value: str) -> str:
    """The colour as a CSS `oklch()` value, lightness as a percentage."""
    red, green, blue = (_linear(channel / 255) for channel in parse_hex(value))
    # Bjorn Ottosson's Oklab: linear sRGB to an LMS-like space, cube root, then to Lab.
    long = math.cbrt(0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue)
    medium = math.cbrt(0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue)
    short = math.cbrt(0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue)
    lightness = 0.2104542553 * long + 0.7936177850 * medium - 0.0040720468 * short
    a = 1.9779984951 * long - 2.4285922050 * medium + 0.4505937099 * short
    b = 0.0259040371 * long + 0.7827717662 * medium - 0.8086757660 * short
    chroma = math.hypot(a, b)
    hue = math.degrees(math.atan2(b, a)) % 360 if chroma > 1e-4 else 0.0
    return f"oklch({lightness * 100:.1f}% {chroma:.3f} {hue:.1f})"


def _linear(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
