# Deepwick for Midnight Commander

Deepwick colors for [Midnight Commander](https://midnight-commander.org).

> Deepwick is an unofficial theme derived from
> [Polywick Blue](https://vscode.polywickstudio.net) by Polywick Studio (MIT).
> Not affiliated with Polywick Studio.

![Deepwick in Midnight Commander](screenshot.png)

## Install

```sh
mkdir -p ~/.local/share/mc/skins
cp deepwick.ini deepwick16.ini ~/.local/share/mc/skins/
```

## Activate

Pick **Options → Appearance → Skin → Deepwick**, or set it in
`~/.config/mc/ini`:

```ini
[Midnight-Commander]
skin=deepwick
```

You can also run `MC_SKIN=deepwick mc`.

`deepwick` is the 24-bit skin. It needs `COLORTERM=truecolor` (most modern
terminals set it) and an mc built with S-Lang (Fedora, Debian and Ubuntu
packages are). Otherwise mc shows "Unable to use 'deepwick' skin with true
colors support" and falls back to its default skin. In that case use
`deepwick16`, which uses the 16 ANSI slots and looks right with a Deepwick
terminal theme ([Ptyxis](https://github.com/deepwick/ptyxis),
[Konsole](https://github.com/deepwick/konsole),
[Alacritty](https://github.com/deepwick/alacritty),
[Ghostty](https://github.com/deepwick/ghostty)).

## Notes

- File colors follow the Deepwick file-listing roles: directories bold Blue,
  executables bold Green, symlinks Cyan, broken links Red, devices and FIFOs
  Gold, archives Rose, media and images Magenta, documents Orange, source
  Yellow, temp files Muted. mc colors the whole row, not just the name.
- Dialogs, menus, the status bar and the button bar sit on Surface; the cursor row is on
  Selection; marked files are bold Yellow.
- The internal editor's syntax colors come from mc's syntax files, not the
  skin, so they are not themed.
- `deepwick16` uses the nearest ANSI slot where Deepwick has none: Surface
  becomes Overlay; Selection becomes Blue with Overlay text; Gold (hotkeys,
  devices) becomes bright yellow; Cyan (symlinks) becomes bright cyan; Orange
  (documents, help links) becomes bright red; Rose (archives) becomes Red, the
  same as broken links; Comment becomes Muted; and the diff viewer uses solid
  Green, Red and Blue backgrounds with Overlay text. Text drawn in Background
  (gauge, reverse, focused error buttons, found bookmarks) becomes Overlay, and
  changed text within a changed diff line uses bright blue (Light Blue).

Tested with GNU Midnight Commander 4.8.33.

## License

MIT. See [LICENSE](LICENSE).
