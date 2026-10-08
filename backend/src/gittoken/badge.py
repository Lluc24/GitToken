from html import escape


def render_badge(login: str, tokens: int) -> str:
    label = escape(login)
    value = f"{tokens:,} estimated tokens"
    width = max(240, (len(login) + len(value)) * 8 + 40)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="28" '
        f'role="img" aria-label="{label}: {value}">'
        f"<title>{label}: {value}</title>"
        f'<rect width="{width}" height="28" rx="5" fill="#071a25"/>'
        f'<text x="12" y="19" fill="#ffffff" font-family="monospace" font-size="12">'
        f'{label}</text><text x="{width - 12}" y="19" text-anchor="end" '
        f'fill="#62c655" font-family="monospace" font-size="12">{value}</text></svg>'
    )
