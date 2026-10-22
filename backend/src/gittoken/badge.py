from dataclasses import dataclass
from html import escape

from gittoken.domain import NAME_BY_AGENT, Agent, Rarity

# The card mirrors the page's player card: 300x520, a 5px rarity frame around a dark pitch.
_CARD_WIDTH = 300
_CARD_HEIGHT = 520
_FRAME_WIDTH = 5
_AVATAR_HEIGHT = 270
_PADDING = 33
_ROW_HEIGHT = 40
_MAX_ROWS = 4
_NAME_MAX_WIDTH = 230
_DISPLAY_FONT = "Oswald, 'Arial Narrow', Arial, sans-serif"
_FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"
_MONO = "ui-monospace, SFMono-Regular, Menlo, monospace"
_PITCH_NIGHT = "#070b24"
_PITCH_BLUE = "#1b2a6b"
_MUTED = "#9aa3c9"
_SCOUT_GREEN = "#5ec95a"


@dataclass(frozen=True)
class _RarityStyle:
    frame_colors: tuple[str, ...]
    accent_color: str
    has_cut_corners: bool


# Legendary and champion cards have cut corners in Clash Royale; the lower rarities are rounded.
_STYLE_BY_RARITY = {
    Rarity.COMMON: _RarityStyle(("#e4e9ef", "#8a96a3"), "#e4e9ef", has_cut_corners=False),
    Rarity.RARE: _RarityStyle(("#ffb15e", "#b35a1f"), "#ffb15e", has_cut_corners=False),
    Rarity.EPIC: _RarityStyle(("#d68cff", "#6d2fb0"), "#d68cff", has_cut_corners=False),
    Rarity.LEGENDARY: _RarityStyle(
        ("#67e8f9", "#e879f9", "#fcd34d"), "#a5f3fc", has_cut_corners=True
    ),
    Rarity.CHAMPION: _RarityStyle(("#e6c65c", "#9c7a26"), "#e6c65c", has_cut_corners=True),
}

_AGENT_MARKS = {
    "claude_code": (
        "m4.7144 15.9555 4.7174-2.6471.079-.2307-.079-.1275h-.2307l-.7893-.0486-2.6956-.0729-2.3375-.0971-2.2646-.1214-.5707-.1215-.5343-.7042.0546-.3522.4797-.3218.686.0608 1.5179.1032 2.2767.1578 1.6514.0972 2.4468.255h.3886l.0546-.1579-.1336-.0971-.1032-.0972L6.973 9.8356l-2.55-1.6879-1.3356-.9714-.7225-.4918-.3643-.4614-.1578-1.0078.6557-.7225.8803.0607.2246.0607.8925.686 1.9064 1.4754 2.4893 1.8336.3643.3035.1457-.1032.0182-.0728-.164-.2733-1.3539-2.4467-1.445-2.4893-.6435-1.032-.17-.6194c-.0607-.255-.1032-.4674-.1032-.7285L6.287.1335 6.6997 0l.9957.1336.419.3642.6192 1.4147 1.0018 2.2282 1.5543 3"
        ".0296.4553.8985.2429.8318.091.255h.1579v-.1457l.1275-1.706.2368-2.0947.2307-2.6957.0789-.7589.3764-.9107.7468-.4918.5828.2793.4797.686-.0668.4433-.2853 1.8517-.5586 2.9021-.3643 1.9429h.2125l.2429-.2429.9835-1.3053 1.6514-2.0643.7286-.8196.85-.9046.5464-.4311h1.0321l.759 1.1293-.34 1.1657-1.0625 1.3478-.8804 1.1414-1.2628 1.7-.7893 1.36.0729.1093.1882-.0183 2.8535-.607 1.5421-.2794 1.8396-.3157.8318.3886.091.3946-.3278.8075-1.967.4857-2.3072.4614-3.4364.8136-.0425.0304.0486.0607 1.5482.1457.6618.0364h1.621l3.0175.2247.7892.522.4736.6376-.079.4857-1.2142.6193-1.6393-.3886-3.825-.9107-1.3113-.32"
        "79h-.1822v.1093l1.0929 1.0686 2.0035 1.8092 2.5075 2.3314.1275.5768-.3218.4554-.34-.0486-2.2039-1.6575-.85-.7468-1.9246-1.621h-.1275v.17l.4432.6496 2.3436 3.5214.1214 1.0807-.17.3521-.6071.2125-.6679-.1214-1.3721-1.9246L14.38 17.959l-1.1414-1.9428-.1397.079-.674 7.2552-.3156.3703-.7286.2793-.6071-.4614-.3218-.7468.3218-1.4753.3886-1.9246.3157-1.53.2853-1.9004.17-.6314-.0121-.0425-.1397.0182-1.4328 1.9672-2.1796 2.9446-1.7243 1.8456-.4128.164-.7164-.3704.0667-.6618.4008-.5889 2.386-3.0357 1.4389-1.882.929-1.0868-.0062-.1579h-.0546l-6.3385 4.1164-1.1293.1457-.4857-.4554.0608-.7467.2307-.2429 1.9"
        "064-1.3114Z"
    ),
    "copilot": (
        "M23.922 16.997C23.061 18.492 18.063 22.02 12 22.02 5.937 22.02.939 18.492.078 16.997A.641.641 0 0 1 0 16.741v-2.869a.883.883 0 0 1 .053-.22c.372-.935 1.347-2.292 2.605-2.656.167-.429.414-1.055.644-1.517a10.098 10.098 0 0 1-.052-1.086c0-1.331.282-2.499 1.132-3.368.397-.406.89-.717 1.474-.952C7.255 2.937 9.248 1.98 11.978 1.98c2.731 0 4.767.957 6.166 2.093.584.235 1.077.546 1.474.952.85.869 1.132 2.037 1.132 3.368 0 .368-.014.733-.052 1.086.23.462.477 1.088.644 1.517 1.258.364 2.233 1.721 2.605 2.656a.841.841 0 0 1 .053.22v2.869a.641.641 0 0 1-.078.256Zm-11.75-5.992h-.344a4.359 4.359 0 0 1-.355."
        "508c-.77.947-1.918 1.492-3.508 1.492-1.725 0-2.989-.359-3.782-1.259a2.137 2.137 0 0 1-.085-.104L4 11.746v6.585c1.435.779 4.514 2.179 8 2.179 3.486 0 6.565-1.4 8-2.179v-6.585l-.098-.104s-.033.045-.085.104c-.793.9-2.057 1.259-3.782 1.259-1.59 0-2.738-.545-3.508-1.492a4.359 4.359 0 0 1-.355-.508Zm2.328 3.25c.549 0 1 .451 1 1v2c0 .549-.451 1-1 1-.549 0-1-.451-1-1v-2c0-.549.451-1 1-1Zm-5 0c.549 0 1 .451 1 1v2c0 .549-.451 1-1 1-.549 0-1-.451-1-1v-2c0-.549.451-1 1-1Zm3.313-6.185c.136 1.057.403 1.913.878 2.497.442.544 1.134.938 2.344.938 1.573 0 2.292-.337 2.657-.751.384-.435.558-1.15.558-2.361 0-1.14"
        "-.243-1.847-.705-2.319-.477-.488-1.319-.862-2.824-1.025-1.487-.161-2.192.138-2.533.529-.269.307-.437.808-.438 1.578v.021c0 .265.021.562.063.893Zm-1.626 0c.042-.331.063-.628.063-.894v-.02c-.001-.77-.169-1.271-.438-1.578-.341-.391-1.046-.69-2.533-.529-1.505.163-2.347.537-2.824 1.025-.462.472-.705 1.179-.705 2.319 0 1.211.175 1.926.558 2.361.365.414 1.084.751 2.657.751 1.21 0 1.902-.394 2.344-.938.475-.584.742-1.44.878-2.497Z"
    ),
    "cursor": (
        "M11.503.131 1.891 5.678a.84.84 0 0 0-.42.726v11.188c0 .3.162.575.42.724l9.609 5.55a1 1 0 0 0 .998 0l9.61-5.55a.84.84 0 0 0 .42-.724V6.404a.84.84 0 0 0-.42-.726L12.497.131a1.01 1.01 0 0 0-.996 0M2.657 6.338h18.55c.263 0 .43.287.297.515L12.23 22.918c-.062.107-.229.064-.229-.06V12.335a.59.59 0 0 0-.295-.51l-9.11-5.257c-.109-.063-.064-.23.061-.23"
    ),
}


def _format_tokens(tokens: int) -> str:
    for threshold, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if tokens >= threshold:
            text = f"{tokens / threshold:.1f}".rstrip("0").rstrip(".")
            return f"{text}{suffix}"
    return str(tokens)


def _card_shape(inset: int, corner: int, style: _RarityStyle, fill: str) -> str:
    left, top = inset, inset
    right, bottom = _CARD_WIDTH - inset, _CARD_HEIGHT - inset
    if style.has_cut_corners:
        points = (
            f"{left + corner},{top} {right - corner},{top} {right},{top + corner} "
            f"{right},{bottom - corner} {right - corner},{bottom} {left + corner},{bottom} "
            f"{left},{bottom - corner} {left},{top + corner}"
        )
        return f'<polygon points="{points}" fill="{fill}"/>'
    return (
        f'<rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" '
        f'rx="{corner // 2}" fill="{fill}"/>'
    )


def _gradient(gradient_id: str, colors: tuple[str, ...]) -> str:
    last = len(colors) - 1
    stops = "".join(
        f'<stop offset="{index / last:.2f}" stop-color="{color}"/>'
        for index, color in enumerate(colors)
    )
    return (
        f'<linearGradient id="{gradient_id}" x1="0" y1="0" x2="0" y2="1">{stops}</linearGradient>'
    )


def _token_drop(total_tokens: int, style: _RarityStyle) -> str:
    """The rarity-colored drop with the total tokens, pointing up like the page's badge."""
    radius = 32
    center_x, center_y = (68, 60) if style.has_cut_corners else (56, 48)
    tip_y = center_y - radius * 1.414
    side = radius * 0.707
    path = (
        f"M{center_x} {tip_y:.1f}L{center_x + side:.1f} {center_y - side:.1f}"
        f"A{radius} {radius} 0 1 1 {center_x - side:.1f} {center_y - side:.1f}Z"
    )
    return (
        f'<path d="{path}" fill="{_PITCH_NIGHT}" stroke="{style.accent_color}" stroke-width="2"/>'
        f'<text x="{center_x}" y="{center_y + 5}" text-anchor="middle" fill="{style.accent_color}" '
        f'font-family="{_DISPLAY_FONT}" font-size="14" font-weight="bold">'
        f"{_format_tokens(total_tokens)}</text>"
    )


def _name_plate(login: str, rarity: Rarity, style: _RarityStyle) -> str:
    top = _FRAME_WIDTH + _AVATAR_HEIGHT - 74
    # Long logins shrink to fit; ~16px per uppercase condensed glyph at 30px.
    fit = (
        f' textLength="{_NAME_MAX_WIDTH}" lengthAdjust="spacingAndGlyphs"'
        if len(login) * 16 > _NAME_MAX_WIDTH
        else ""
    )
    return (
        f'<rect x="25" y="{top}" width="250" height="62" fill="{_PITCH_NIGHT}" fill-opacity="0.8"/>'
        f'<rect x="25" y="{top}" width="250" height="1" fill="{style.accent_color}"/>'
        f'<rect x="25" y="{top + 61}" width="250" height="1" fill="{style.accent_color}"/>'
        f'<text x="150" y="{top + 37}" text-anchor="middle" fill="#ffffff" '
        f'font-family="{_DISPLAY_FONT}" font-size="30" font-weight="bold" '
        f'letter-spacing="0.75"{fit}>{escape(login.upper())}</text>'
        f'<text x="150" y="{top + 54}" text-anchor="middle" fill="{style.accent_color}" '
        f'font-family="{_DISPLAY_FONT}" font-size="11" letter-spacing="3.3">'
        f"{rarity.upper()}</text>"
    )


def _agent_row(agent: Agent, tokens: int, agent_total: int, top: int) -> str:
    percent = round(tokens / agent_total * 100)
    name_left = _PADDING
    mark = ""
    if agent in _AGENT_MARKS:
        name_left += 24
        mark = (
            f'<g transform="translate({_PADDING} {top}) scale(0.667)">'
            f'<path fill="#ffffff" d="{_AGENT_MARKS[agent]}"/></g>'
        )
    inner = _CARD_WIDTH - 2 * _PADDING
    bar_fill = max(6, round(inner * tokens / agent_total))
    return (
        mark
        + f'<text x="{name_left}" y="{top + 13}" fill="#ffffff" font-family="{_FONT}" '
        + f'font-size="14">{escape(NAME_BY_AGENT[agent])}</text>'
        + f'<text x="{_CARD_WIDTH - _PADDING}" y="{top + 13}" text-anchor="end" fill="#ffffff" '
        + f'font-family="{_MONO}" font-size="13">{_format_tokens(tokens)} '
        + f'<tspan fill="{_MUTED}">({percent}%)</tspan></text>'
        + f'<rect x="{_PADDING}" y="{top + 21}" width="{inner}" height="6" rx="3" '
        + 'fill="#ffffff" fill-opacity="0.1"/>'
        + f'<rect x="{_PADDING}" y="{top + 21}" width="{bar_fill}" height="6" rx="3" '
        + f'fill="{_SCOUT_GREEN}"/>'
    )


def _agent_section(tokens_by_agent: dict[Agent, int], style: _RarityStyle) -> str:
    top = _FRAME_WIDTH + _AVATAR_HEIGHT + 12
    parts = [
        f'<text x="{_PADDING}" y="{top + 12}" fill="{style.accent_color}" '
        f'font-family="{_DISPLAY_FONT}" font-size="11" letter-spacing="3.3">TOKENS BY AGENT</text>'
    ]
    agent_total = sum(tokens_by_agent.values())
    agents = sorted(tokens_by_agent.items(), key=lambda item: item[1], reverse=True)
    rows = agents[:_MAX_ROWS]
    row_top = top + 26
    if agent_total > 0:
        for agent, tokens in rows:
            parts.append(_agent_row(agent, tokens, agent_total, row_top))
            row_top += _ROW_HEIGHT
    else:
        parts.append(
            f'<text x="{_PADDING}" y="{row_top + 13}" fill="{_MUTED}" font-family="{_FONT}" '
            f'font-size="13">No attributed agent tokens found.</text>'
        )
    hidden_agent_count = len(agents) - len(rows)
    if hidden_agent_count > 0:
        parts.append(
            f'<text x="{_PADDING}" y="{row_top + 6}" fill="{_MUTED}" font-family="{_FONT}" '
            f'font-size="11">+{hidden_agent_count} more agents</text>'
        )
    return "".join(parts)


def render_badge(
    login: str,
    total_tokens: int,
    tokens_by_agent: dict[Agent, int],
    rarity: Rarity,
    avatar_data_url: str,
) -> str:
    """Pre: avatar_data_url is a data: URL, since images embedded with <img> cannot load external resources."""
    style = _STYLE_BY_RARITY[rarity]
    aria = escape(f"{login}: {total_tokens:,} estimated tokens, {rarity}")
    inner_top = _FRAME_WIDTH
    avatar_bottom = inner_top + _AVATAR_HEIGHT
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_CARD_WIDTH}" height="{_CARD_HEIGHT}" '
        f'viewBox="0 0 {_CARD_WIDTH} {_CARD_HEIGHT}" role="img" aria-label="{aria}">'
        f"<title>{aria}</title>"
        "<defs>"
        + _gradient("frame", style.frame_colors)
        + _gradient("pitch", (_PITCH_BLUE, _PITCH_NIGHT))
        + '<linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0" stop-color="{_PITCH_NIGHT}" stop-opacity="0"/>'
        f'<stop offset="1" stop-color="{_PITCH_NIGHT}"/></linearGradient>'
        '<clipPath id="inner">'
        + _card_shape(_FRAME_WIDTH, 30, style, "#000000")
        + "</clipPath></defs>"
        + _card_shape(0, 32, style, "url(#frame)")
        + _card_shape(_FRAME_WIDTH, 30, style, "url(#pitch)")
        + '<g clip-path="url(#inner)">'
        f'<image href="{avatar_data_url}" x="0" y="{inner_top}" width="{_CARD_WIDTH}" '
        f'height="{_AVATAR_HEIGHT}" preserveAspectRatio="xMidYMid slice"/>'
        f'<rect x="0" y="{avatar_bottom - 128}" width="{_CARD_WIDTH}" height="128" fill="url(#fade)"/>'
        "</g>"
        + _name_plate(login, rarity, style)
        + _token_drop(total_tokens, style)
        + _agent_section(tokens_by_agent, style)
        + f'<text x="150" y="{_CARD_HEIGHT - 13}" text-anchor="middle" fill="#ffffff" '
        f'fill-opacity="0.5" font-family="{_DISPLAY_FONT}" font-size="10" letter-spacing="3">'
        "GITTOKEN</text></svg>"
    )
