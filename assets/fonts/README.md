# Custom Fonts

Drop your custom `.ttf` or `.otf` font files here and configure them in [config.yaml](cci:7://file:///Users/ianheidt/CascadeProjects/nrhof-matrix-kiosk/config.yaml:0:0-0:0).

## Recommended Fonts

### Monospace (for terminal/matrix aesthetic):
- **JetBrains Mono** - https://www.jetbrains.com/lp/mono/
- **Fira Code** - https://github.com/tonsky/FiraCode
- **IBM Plex Mono** - https://www.ibm.com/plex/
- **Source Code Pro** - https://adobe-fonts.github.io/source-code-pro/

### Sans-serif (for UI elements):
- **Inter** - https://rsms.me/inter/
- **IBM Plex Sans** - https://www.ibm.com/plex/
- **Roboto** - https://fonts.google.com/specimen/Roboto

## Configuration

Edit [config.yaml](cci:7://file:///Users/ianheidt/CascadeProjects/nrhof-matrix-kiosk/config.yaml:0:0-0:0):

```yaml
fonts:
  mono: "JetBrainsMono-Regular.ttf"
  sans: "Inter-Regular.ttf"
  mono_bold: "JetBrainsMono-Bold.ttf"
  sans_bold: "Inter-Bold.ttf"
  directory: "assets/fonts"

