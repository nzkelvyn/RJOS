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

wlroots = dependency('wlroots-0.18',
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

# ─── Fontes ──────────────────────────────────────────────────────────────────

sources = files(
  'src/main.c',
)

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
