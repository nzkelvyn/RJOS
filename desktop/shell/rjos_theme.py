# =============================================================================
# RJOS Design Tokens & Visual Identity Module — rjos_theme.py
# Centralização oficial de cores, estilos e design system do RJOS
# =============================================================================

# ─── Paleta Oficial do RJOS (Inspirada no Rio de Janeiro) ─────────────────────
RJOS_BLUE             = "#005B96"  # Azul Oceano: Identidade principal, botões, seleção, foco
RJOS_BLUE_HOVER       = "#006FB7"  # Azul Oceano (Hover)
RJOS_BLUE_ACTIVE      = "#004877"  # Azul Oceano (Active / Pressed)
RJOS_BLUE_DIM         = "rgba(0, 91, 150, 0.18)" # Azul translúcido para fundos de seleção

RJOS_GREEN            = "#00A86B"  # Verde Tropical: Estados positivos, sucesso, conectado
RJOS_GREEN_HOVER      = "#00C27B"  # Verde Tropical (Hover)
RJOS_GREEN_DIM        = "rgba(0, 168, 107, 0.18)" # Verde translúcido

RJOS_YELLOW           = "#F2C94C"  # Amarelo Sol: Atenção, avisos, notificações, energia
RJOS_YELLOW_HOVER     = "#F5D46E"  # Amarelo Sol (Hover)
RJOS_YELLOW_DIM       = "rgba(242, 201, 76, 0.18)" # Amarelo translúcido

RJOS_BG               = "#121212"  # Carvão: Fundo principal da interface escura
RJOS_SURFACE          = "#1E1E1E"  # Superfície: Janelas, painéis, menus, cards, popovers
RJOS_SURFACE_HOVER    = "#292929"  # Superfície secundária: Hover, itens selecionáveis
RJOS_SURFACE_ACTIVE   = "#333333"  # Superfície ativa / clique
RJOS_SURFACE_BORDER   = "rgba(255, 255, 255, 0.08)" # Borda sutil de superfícies

RJOS_TEXT             = "#FFFFFF"  # Branco: Títulos, textos principais, ícones primários
RJOS_TEXT_SECONDARY   = "#B8B8B8"  # Texto secundário: Descrições, metadados, legendas
RJOS_TEXT_MUTED       = "#757575"  # Texto esmaecido / desabilitado

# Cor de erro crítico (uso restrito a falhas e erros)
RJOS_ERROR            = "#E05252"
RJOS_ERROR_DIM        = "rgba(224, 82, 82, 0.18)"

# ─── Definição de Variáveis CSS Compartilhadas (GTK4 / Web) ──────────────────
RJOS_SHARED_CSS_VARS = f"""
@define-color rjos-blue             {RJOS_BLUE};
@define-color rjos-blue-hover       {RJOS_BLUE_HOVER};
@define-color rjos-blue-active      {RJOS_BLUE_ACTIVE};
@define-color rjos-blue-dim         {RJOS_BLUE_DIM};

@define-color rjos-green            {RJOS_GREEN};
@define-color rjos-green-hover      {RJOS_GREEN_HOVER};
@define-color rjos-green-dim        {RJOS_GREEN_DIM};

@define-color rjos-yellow           {RJOS_YELLOW};
@define-color rjos-yellow-hover     {RJOS_YELLOW_HOVER};
@define-color rjos-yellow-dim       {RJOS_YELLOW_DIM};

@define-color rjos-bg               {RJOS_BG};
@define-color rjos-surface          {RJOS_SURFACE};
@define-color rjos-surface-hover    {RJOS_SURFACE_HOVER};
@define-color rjos-surface-active   {RJOS_SURFACE_ACTIVE};
@define-color rjos-surface-border   {RJOS_SURFACE_BORDER};

@define-color rjos-text             {RJOS_TEXT};
@define-color rjos-text-secondary   {RJOS_TEXT_SECONDARY};
@define-color rjos-text-muted       {RJOS_TEXT_MUTED};

@define-color rjos-error            {RJOS_ERROR};
@define-color rjos-error-dim        {RJOS_ERROR_DIM};

/* Global Design System Variables */
* {
    /* Radii */
    --rjos-radius-sm: 4px;
    --rjos-radius-md: 8px;
    --rjos-radius-lg: 12px;
    --rjos-radius-xl: 18px;
    --rjos-radius-pill: 9999px;

    /* Spacing */
    --rjos-space-xs: 4px;
    --rjos-space-sm: 8px;
    --rjos-space-md: 16px;
    --rjos-space-lg: 24px;
    --rjos-space-xl: 32px;

    /* Shadows */
    --rjos-shadow-sm: 0 2px 4px rgba(0,0,0,0.1);
    --rjos-shadow-md: 0 4px 12px rgba(0,0,0,0.2);
    --rjos-shadow-lg: 0 8px 24px rgba(0,0,0,0.4);
    --rjos-shadow-xl: 0 16px 48px rgba(0,0,0,0.6);

    /* Typography */
    --rjos-font-family: "Inter", sans-serif;
    
    /* Transitions */
    --rjos-transition-fast: 150ms cubic-bezier(0.4, 0, 0.2, 1);
    --rjos-transition-normal: 250ms cubic-bezier(0.4, 0, 0.2, 1);
}

/* Base Classes */
.rjos-surface {
    background-color: @rjos-surface;
    border: 1px solid @rjos-surface-border;
    border-radius: var(--rjos-radius-md);
    box-shadow: var(--rjos-shadow-md);
    color: @rjos-text;
}

.rjos-surface-hover:hover {
    background-color: @rjos-surface-hover;
}

.rjos-dock {
    background-color: alpha(@rjos-bg, 0.85);
    border: 1px solid @rjos-surface-border;
    border-radius: var(--rjos-radius-xl);
    box-shadow: var(--rjos-shadow-lg);
}

.rjos-panel {
    background-color: alpha(@rjos-bg, 0.95);
    color: @rjos-text;
    border-bottom: 1px solid @rjos-surface-border;
}
"""

# ─── Helper de CSS Provider para GTK4 ─────────────────────────────────────────
def apply_rjos_theme_provider(css_content=""):
    """Injeta as variáveis e regras de CSS do RJOS no display padrão do GTK."""
    try:
        import gi
        gi.require_version('Gtk', '4.0')
        from gi.repository import Gtk, Gdk
        provider = Gtk.CssProvider()
        full_css = f"{RJOS_SHARED_CSS_VARS}\n{css_content}"
        provider.load_from_data(full_css.encode('utf-8'))
        display = Gdk.Display.get_default()
        if display:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        return provider
    except Exception as e:
        return None
