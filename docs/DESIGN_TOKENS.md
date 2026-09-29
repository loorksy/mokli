# Design tokens

The brief named screenshots as the visual source. None were attached to the repository or the run. These tokens are the stand-in, and every screen uses them.

| Token | Value | Use |
| --- | --- | --- |
| `--bg` | `#0b0d11` | Page |
| `--surface` | `#12161d` | Sidebar |
| `--card` | `#171c25` | Cards |
| `--line` | `#2c3444` | Borders and chart grid |
| `--text` | `#ece8e1` | Primary text |
| `--muted` | `#8e97a8` | Secondary text |
| `--gold` | `#d7b15a` | Accent, primary buttons |
| `--gold-soft` | `#f0d48a` | Highlight |
| `--buy` | `#2fbf8a` | Up candles and approve |
| `--sell` | `#e15d66` | Down candles and reject |
| `--danger` | `#ff4d4f` | Kill switch |
| `--radius` | `14px` | Cards |
| `--shadow` | `0 12px 32px rgba(0,0,0,.35)` | Cards |
| Font | IBM Plex Sans, IBM Plex Sans Arabic | UI |
| Chart direction | `ltr` | Always, including Arabic RTL chrome |

Spacing uses Tailwind's 4px scale. Navigation is a horizontal scroller at 360px and a sidebar from 768px up. Buttons are at least 40px tall. The kill switch is the only danger-colored control on the dashboard.
