# Design tokens

The visual source is the attached dark Arabic chat reference. Mokli keeps its own name and gold-trading job. The craft is the near-black ground, large type, thin cards, pills, composer, side list, and sheets.

| Token | Value | Use |
| --- | --- | --- |
| `--bg` | `#141414` | Page |
| `--surface` | `#1c1c1e` | Sheets and raised rows |
| `--card` | `#242426` | Cards and pills |
| `--line` | `rgba(255,255,255,.08)` | Hairline borders |
| `--text` | `#f3f3f4` | Primary text |
| `--muted` | `#9b9ba1` | Secondary text |
| `--gold` | `#d7b15a` | Sparse trading accent |
| `--buy` | `#3dbe86` | Approve and up candles |
| `--sell` | `#e15d66` | Reject and down candles |
| `--danger` | `#ff5a5f` | Kill switch text |
| `--radius` | `22px` | Cards |
| Font | IBM Plex Sans Arabic, IBM Plex Sans | UI |
| Chart direction | `ltr` | Always, including Arabic RTL chrome |

The composer is physically left-to-right: plus on the left, voice button on the right, Arabic placeholder on the field. From 768px the side list stays open. At 360px it is a drawer. Account, settings language, and attachments are bottom sheets.
