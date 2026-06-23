# Brand spec — Paxman landing page (neon.com-inspired)

## Source
- Reference: https://neon.com — Postgres backend platform
- Package: Paxman (paxman) by Nexus Envision Sdn Bhd
- Developer: Azahari Zaman (azahari@nexusnv.net)
- Website: https://www.nexusnv.net

## Palette (OKLch)

```css
:root {
  --bg:      oklch(6% 0.012 260);
  --surface: oklch(12% 0.015 260);
  --fg:      oklch(93% 0.004 260);
  --muted:   oklch(48% 0.012 260);
  --border:  oklch(18% 0.012 260);
  --accent:  oklch(68% 0.18 170);

  --font-display: -apple-system, BlinkMacSystemFont, 'Inter', 'SF Pro Display', system-ui, sans-serif;
  --font-body:    -apple-system, BlinkMacSystemFont, 'Inter', 'SF Pro Text', system-ui, sans-serif;
  --font-mono:    'JetBrains Mono', 'IBM Plex Mono', 'SF Mono', ui-monospace, monospace;
}
```

## Design patterns observed

1. **Deep dark canvas** — near-black background (#0a0a0f equivalent), not pure black
2. **Bright accent** — single neon-green/cyan accent, used sparingly (buttons, links, eyebrow text)
3. **Terminal/code blocks** — inline code snippets with dark surface + bright accent prompt character
4. **Large stat counters** — big numbers with labels, monospace numeric styling
5. **Bento grid** — feature cards in asymmetric grid layout
6. **Minimal chrome** — no shadows, hairline borders, no rounded cards beyond 8px
7. **Gradient accent** — subtle accent-to-transparent gradient on hero/divider elements only
