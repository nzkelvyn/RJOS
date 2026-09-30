project('rjos-compositor', 'c',
  version: '0.1.0',
  default_options: [
    'c_std=c11',
    'warning_level=2',
    'werror=false',
  ]
)

cc = meson.get_compiler('c')

# ─── Dependências ─────────────────────────────────────────────────────────────

wlroots = dependency('wlroots-0.19',
  fallback: ['wlroots', 'wlroots'],
  default_options: ['examples=false', 'backends=auto', 'renderers=auto']
)

wayland_server = dependency('wayland-server', version: '>=1.21')
wayland_proto  = dependency('wayland-protocols', version: '>=1.32')
xkbcommon      = dependency('xkbcommon')
pixman         = dependency('pixman-1')

# ─── Flags de compilação ──────────────────────────────────────────────────────

add_project_arguments(
  '-DWLR_USE_UNSTABLE',
  '-D_POSIX_C_SOURCE=200809L',
  '-DRJOS_VERSION="@0@"'.format(meson.project_version()),
  language: 'c'
)

wayland_scanner = find_program('wayland-scanner')
wl_datadir = wayland_proto.get_variable(pkgconfig: 'pkgdatadir')
xdg_shell_xml = join_paths(wl_datadir, 'stable', 'xdg-shell', 'xdg-shell.xml')
xdg_shell_h = custom_target('xdg-shell-protocol.h',
  command: [wayland_scanner, 'server-header', '@INPUT@', '@OUTPUT@'],
  input: xdg_shell_xml,
  output: 'xdg-shell-protocol.h'
)

wlr_layer_shell_xml = 'protocols/wlr-layer-shell-unstable-v1.xml'
wlr_layer_shell_h = custom_target('wlr-layer-shell-unstable-v1-protocol.h',
  command: [wayland_scanner, 'server-header', '@INPUT@', '@OUTPUT@'],
  input: wlr_layer_shell_xml,
  output: 'wlr-layer-shell-unstable-v1-protocol.h'
)

# ─── Fontes ──────────────────────────────────────────────────────────────────

sources = [
  'src/main.c',
  xdg_shell_h,
  wlr_layer_shell_h,
]

# ─── Executável ──────────────────────────────────────────────────────────────

executable('rjos-compositor',
  sources,
  dependencies: [
    wlroots,
    wayland_server,
    xkbcommon,
    pixman,
  ],
  install: true,
  install_dir: get_option('bindir'),
)

message('rjos-compositor configurado. Execute: cd build && ninja')
