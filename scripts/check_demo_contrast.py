"""Verify the public demo's core text palette meets basic WCAG contrast targets."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "demo" / "styles.css"
TOKEN_PATTERN = re.compile(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6})\s*;")


def relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]

    def linearize(channel: float) -> float:
        if channel <= 0.04045:
            return channel / 12.92
        return ((channel + 0.055) / 1.055) ** 2.4

    red, green, blue = (linearize(channel) for channel in channels)
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(foreground: str, background: str) -> float:
    first = relative_luminance(foreground)
    second = relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def main() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    tokens = dict(TOKEN_PATTERN.findall(css))
    required_pairs = (
        ("text", "surface"),
        ("text", "bg"),
        ("muted", "surface"),
        ("muted", "bg"),
        ("terracotta", "surface"),
        ("aqua", "surface"),
        ("emerald", "surface"),
        ("purple", "surface"),
        ("danger", "surface"),
        ("surface", "surface-dark"),
    )

    failures: list[str] = []
    for foreground_name, background_name in required_pairs:
        try:
            foreground = tokens[foreground_name]
            background = tokens[background_name]
        except KeyError as error:
            failures.append(f"Missing CSS token: --{error.args[0]}")
            continue

        ratio = contrast_ratio(foreground, background)
        print(
            f"--{foreground_name} on --{background_name}: "
            f"{ratio:.2f}:1"
        )
        if ratio < 4.5:
            failures.append(
                f"--{foreground_name} on --{background_name} is {ratio:.2f}:1; "
                "expected at least 4.5:1"
            )

    if failures:
        raise SystemExit("\n".join(failures))

    print("Public demo core palette meets the 4.5:1 text contrast target.")


if __name__ == "__main__":
    main()
