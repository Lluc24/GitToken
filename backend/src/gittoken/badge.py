from html import escape

from gittoken.domain import Agent

_CARD_WIDTH = 360
_PADDING = 16
_MAX_ROWS = 4
_FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"
_MONO = "ui-monospace, SFMono-Regular, Menlo, monospace"

_AGENT_NAMES = {
    "claude_code": "Claude Code",
    "codex": "Codex",
    "copilot": "Copilot",
    "cursor": "Cursor",
    "devin": "Devin",
    "jules": "Jules",
    "aider": "Aider",
}

_AGENT_MARKS = {
    "claude_code": (
        "#d97757",
        (
            "m4.7144 15.9555 4.7174-2.6471.079-.2307-.079-.1275h-.2307l-.7893-.0486-2.6956-.0729-2.3375-.0971-2.2646-.1214-.5707-.1215-.5343-.7042.0546-.3522.4797-.3218.686.0608 1.5179.1032 2.2767.1578 1.6514.0972 2.4468.255h.3886l.0546-.1579-.1336-.0971-.1032-.0972L6.973 9.8356l-2.55-1.6879-1.3356-.9714-.7225-.4918-.3643-.4614-.1578-1.0078.6557-.7225.8803.0607.2246.0607.8925.686 1.9064 1.4754 2.4893 1.8336.3643.3035.1457-.1032.0182-.0728-.164-.2733-1.3539-2.4467-1.445-2.4893-.6435-1.032-.17-.6194c-.0607-.255-.1032-.4674-.1032-.7285L6.287.1335 6.6997 0l.9957.1336.419.3642.6192 1.4147 1.0018 2.2282 1.5543 3"
            ".0296.4553.8985.2429.8318.091.255h.1579v-.1457l.1275-1.706.2368-2.0947.2307-2.6957.0789-.7589.3764-.9107.7468-.4918.5828.2793.4797.686-.0668.4433-.2853 1.8517-.5586 2.9021-.3643 1.9429h.2125l.2429-.2429.9835-1.3053 1.6514-2.0643.7286-.8196.85-.9046.5464-.4311h1.0321l.759 1.1293-.34 1.1657-1.0625 1.3478-.8804 1.1414-1.2628 1.7-.7893 1.36.0729.1093.1882-.0183 2.8535-.607 1.5421-.2794 1.8396-.3157.8318.3886.091.3946-.3278.8075-1.967.4857-2.3072.4614-3.4364.8136-.0425.0304.0486.0607 1.5482.1457.6618.0364h1.621l3.0175.2247.7892.522.4736.6376-.079.4857-1.2142.6193-1.6393-.3886-3.825-.9107-1.3113-.32"
            "79h-.1822v.1093l1.0929 1.0686 2.0035 1.8092 2.5075 2.3314.1275.5768-.3218.4554-.34-.0486-2.2039-1.6575-.85-.7468-1.9246-1.621h-.1275v.17l.4432.6496 2.3436 3.5214.1214 1.0807-.17.3521-.6071.2125-.6679-.1214-1.3721-1.9246L14.38 17.959l-1.1414-1.9428-.1397.079-.674 7.2552-.3156.3703-.7286.2793-.6071-.4614-.3218-.7468.3218-1.4753.3886-1.9246.3157-1.53.2853-1.9004.17-.6314-.0121-.0425-.1397.0182-1.4328 1.9672-2.1796 2.9446-1.7243 1.8456-.4128.164-.7164-.3704.0667-.6618.4008-.5889 2.386-3.0357 1.4389-1.882.929-1.0868-.0062-.1579h-.0546l-6.3385 4.1164-1.1293.1457-.4857-.4554.0608-.7467.2307-.2429 1.9"
            "064-1.3114Z"
        ),
    ),
    "copilot": (
        "#000000",
        (
            "M23.922 16.997C23.061 18.492 18.063 22.02 12 22.02 5.937 22.02.939 18.492.078 16.997A.641.641 0 0 1 0 16.741v-2.869a.883.883 0 0 1 .053-.22c.372-.935 1.347-2.292 2.605-2.656.167-.429.414-1.055.644-1.517a10.098 10.098 0 0 1-.052-1.086c0-1.331.282-2.499 1.132-3.368.397-.406.89-.717 1.474-.952C7.255 2.937 9.248 1.98 11.978 1.98c2.731 0 4.767.957 6.166 2.093.584.235 1.077.546 1.474.952.85.869 1.132 2.037 1.132 3.368 0 .368-.014.733-.052 1.086.23.462.477 1.088.644 1.517 1.258.364 2.233 1.721 2.605 2.656a.841.841 0 0 1 .053.22v2.869a.641.641 0 0 1-.078.256Zm-11.75-5.992h-.344a4.359 4.359 0 0 1-.355."
            "508c-.77.947-1.918 1.492-3.508 1.492-1.725 0-2.989-.359-3.782-1.259a2.137 2.137 0 0 1-.085-.104L4 11.746v6.585c1.435.779 4.514 2.179 8 2.179 3.486 0 6.565-1.4 8-2.179v-6.585l-.098-.104s-.033.045-.085.104c-.793.9-2.057 1.259-3.782 1.259-1.59 0-2.738-.545-3.508-1.492a4.359 4.359 0 0 1-.355-.508Zm2.328 3.25c.549 0 1 .451 1 1v2c0 .549-.451 1-1 1-.549 0-1-.451-1-1v-2c0-.549.451-1 1-1Zm-5 0c.549 0 1 .451 1 1v2c0 .549-.451 1-1 1-.549 0-1-.451-1-1v-2c0-.549.451-1 1-1Zm3.313-6.185c.136 1.057.403 1.913.878 2.497.442.544 1.134.938 2.344.938 1.573 0 2.292-.337 2.657-.751.384-.435.558-1.15.558-2.361 0-1.14"
            "-.243-1.847-.705-2.319-.477-.488-1.319-.862-2.824-1.025-1.487-.161-2.192.138-2.533.529-.269.307-.437.808-.438 1.578v.021c0 .265.021.562.063.893Zm-1.626 0c.042-.331.063-.628.063-.894v-.02c-.001-.77-.169-1.271-.438-1.578-.341-.391-1.046-.69-2.533-.529-1.505.163-2.347.537-2.824 1.025-.462.472-.705 1.179-.705 2.319 0 1.211.175 1.926.558 2.361.365.414 1.084.751 2.657.751 1.21 0 1.902-.394 2.344-.938.475-.584.742-1.44.878-2.497Z"
        ),
    ),
    "cursor": (
        "#000000",
        (
            "M11.503.131 1.891 5.678a.84.84 0 0 0-.42.726v11.188c0 .3.162.575.42.724l9.609 5.55a1 1 0 0 0 .998 0l9.61-5.55a.84.84 0 0 0 .42-.724V6.404a.84.84 0 0 0-.42-.726L12.497.131a1.01 1.01 0 0 0-.996 0M2.657 6.338h18.55c.263 0 .43.287.297.515L12.23 22.918c-.062.107-.229.064-.229-.06V12.335a.59.59 0 0 0-.295-.51l-9.11-5.257c-.109-.063-.064-.23.061-.23"
        ),
    ),
}


def _format_tokens(tokens: int) -> str:
    for threshold, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "K")):
        if tokens >= threshold:
            text = f"{tokens / threshold:.1f}".rstrip("0").rstrip(".")
            return f"{text}{suffix}"
    return str(tokens)


def _agent_row(agent: str, tokens: int, total: int, top: int) -> str:
    name = escape(_AGENT_NAMES.get(agent, agent))
    percent = round(tokens / total * 100) if total else 0
    stats = f"{_format_tokens(tokens)} · {percent}%"
    mark = ""
    if agent in _AGENT_MARKS:
        color, path = _AGENT_MARKS[agent]
        mark = (
            f'<g transform="translate({_PADDING} {top}) scale(0.625)">'
            f'<path fill="{color}" d="{path}"/></g>'
        )
    inner = _CARD_WIDTH - 2 * _PADDING
    bar_fill = max(3, round(inner * tokens / total)) if total else 0
    return (
        mark
        + f'<text x="{_PADDING + 22}" y="{top + 11}" fill="#101528" '
        + f'font-family="{_FONT}" font-size="12">{name}</text>'
        + f'<text x="{_CARD_WIDTH - _PADDING}" y="{top + 11}" text-anchor="end" '
        + f'fill="#101528" font-family="{_MONO}" font-size="12">{stats}</text>'
        + f'<rect x="{_PADDING}" y="{top + 18}" width="{inner}" height="6" rx="3" fill="#eceff3"/>'
        + f'<rect x="{_PADDING}" y="{top + 18}" width="{bar_fill}" height="6" rx="3" fill="#5ec95a"/>'
    )


def render_badge(
    login: str,
    total_tokens: int,
    tokens_by_agent: dict[Agent, int],
    rarity: str,
) -> str:
    label = escape(login)
    total_text = f"{total_tokens:,} estimated tokens"
    subtitle = escape(f"{rarity} · {total_text}")
    agents = sorted(tokens_by_agent.items(), key=lambda item: item[1], reverse=True)
    rows = agents[:_MAX_ROWS]
    extra = len(agents) - len(rows)
    parts = []
    top = 62
    for agent, tokens in rows:
        parts.append(_agent_row(agent, tokens, total_tokens, top))
        top += 34
    if extra > 0:
        parts.append(
            f'<text x="{_PADDING}" y="{top + 2}" fill="#6b7280" '
            f'font-family="{_FONT}" font-size="11">+{extra} more agents</text>'
        )
        top += 18
    height = top + _PADDING - 6
    body = "".join(parts)
    aria = escape(f"{login}: {total_text}")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{_CARD_WIDTH}" '
        f'height="{height}" role="img" aria-label="{aria}">'
        f"<title>{aria}</title>"
        f'<rect width="{_CARD_WIDTH}" height="{height}" rx="12" fill="#ffffff" '
        f'stroke="#dfe3ea"/>'
        f'<text x="{_PADDING}" y="{_PADDING + 15}" fill="#101528" '
        f'font-family="{_FONT}" font-size="15" font-weight="bold">{label}</text>'
        f'<text x="{_CARD_WIDTH - _PADDING}" y="{_PADDING + 15}" text-anchor="end" '
        f'fill="#101528" font-family="{_MONO}" font-size="14" font-weight="bold">'
        f"{_format_tokens(total_tokens)}</text>"
        f'<text x="{_PADDING}" y="{_PADDING + 31}" fill="#6b7280" '
        f'font-family="{_FONT}" font-size="11">{subtitle}</text>'
        f'<rect x="{_PADDING}" y="48" width="{_CARD_WIDTH - 2 * _PADDING}" '
        f'height="1" fill="#eceff3"/>'
        f"{body}</svg>"
    )
