# Customising the panels

Create `%LOCALAPPDATA%\cc-dialogs\style.json`. Every key is optional — anything
you leave out keeps its default. A missing or malformed file is ignored, so a
typo degrades to the built-in look rather than breaking the panel.

Preview your changes without restarting Claude Code:

```
py -3 packages/cc-dialogs/selftest.py --ui
```

Edit, re-run, repeat. The panels read the file fresh on every launch.

## Full example

```json
{
  "mode": "auto",
  "corner": "bottom-right",
  "width": 470,
  "margin": 16,
  "radius": 10,
  "font": "Segoe UI",
  "fontSize": 9.75,
  "monoFont": "Cascadia Code",
  "autoCloseSeconds": 570,

  "dark": {
    "Back":      "#202020",
    "Panel":     "#2B2B2B",
    "Text":      "#F0F0F0",
    "Muted":     "#A0A0A0",
    "Border":    "#414141",
    "Accent":    "#4084D6",
    "AccentTxt": "#FFFFFF",
    "BtnBack":   "#3A3A3A",
    "BtnText":   "#EBEBEB"
  },

  "light": {
    "Back":      "#F9F9F9",
    "Panel":     "#FFFFFF",
    "Text":      "#1C1C1C",
    "Muted":     "#696969",
    "Border":    "#DEDEDE",
    "Accent":    "#0067C0",
    "AccentTxt": "#FFFFFF",
    "BtnBack":   "#FBFBFB",
    "BtnText":   "#1C1C1C"
  }
}
```

## Keys

| Key | Default | Meaning |
|---|---|---|
| `mode` | `auto` | `auto` follows the Windows app theme; `light` / `dark` pin one |
| `corner` | `bottom-right` | `bottom-right`, `bottom-left`, `top-right`, `top-left`, `center` |
| `width` | `470` | Panel width in pixels. Height is computed from the content |
| `margin` | `16` | Gap from the screen edge |
| `radius` | `10` | Corner rounding; `0` for square |
| `font` | `Segoe UI` | UI font family |
| `fontSize` | `9.75` | Base size; titles and list rows scale off this |
| `monoFont` | `Consolas` | Font for the command / diff body in the permission panel |
| `autoCloseSeconds` | `570` | See below. `0` disables |

## Colour roles

| Role | Where it shows |
|---|---|
| `Back` | Panel background |
| `Panel` | Inset surfaces — the command box, the option list |
| `Text` | Primary text |
| `Muted` | The small caption row at the top |
| `Border` | Panel outline and control outlines |
| `Accent` | Primary button fill (Allow / OK) |
| `AccentTxt` | Text on the primary button |
| `BtnBack` | Secondary button fill |
| `BtnText` | Text on secondary buttons |

Colours are `#RRGGBB`. An unparseable value falls back to the default for that
role, so one bad colour will not take the whole theme down.

## About `autoCloseSeconds`

The panel does **not** close when you click elsewhere — it stays on top and
waits for a button. This timer exists for one specific case: Claude Code kills
the hook at 600 seconds and falls back to the terminal prompt. A panel left
open past that point is a dead window whose buttons no longer reach anything.
Closing at 570s keeps the two in step.

Raising it above 600 has no useful effect — the hook is already gone. Set it
to `0` only if you have also raised the hook timeout in `settings.json`.
