/* =============================================================================
 * RJOS Compositor — main.c
 * Compositor Wayland baseado em wlroots
 *
 * Responsável por:
 *   - Gerenciar superfícies Wayland (janelas)
 *   - Input: teclado, mouse, touchpad
 *   - Output: monitores, resolução, posicionamento
 *   - Decorações de janela
 *   - Animações e efeitos visuais
 *
 * Compilar: meson setup build && cd build && ninja
 * ============================================================================*/

#define _POSIX_C_SOURCE 200809L

#include <assert.h>
#include <getopt.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <wayland-server-core.h>

/* wlroots — incluir antes de qualquer header específico */
#define WLR_USE_UNSTABLE
#include <wlr/backend.h>
#include <wlr/render/allocator.h>
#include <wlr/render/wlr_renderer.h>
#include <wlr/types/wlr_compositor.h>
#include <wlr/types/wlr_cursor.h>
#include <wlr/types/wlr_data_device.h>
#include <wlr/types/wlr_input_device.h>
#include <wlr/types/wlr_keyboard.h>
#include <wlr/types/wlr_output.h>
#include <wlr/types/wlr_output_layout.h>
#include <wlr/types/wlr_pointer.h>
#include <wlr/types/wlr_scene.h>
#include <wlr/types/wlr_seat.h>
#include <wlr/types/wlr_subcompositor.h>
#include <wlr/types/wlr_xcursor_manager.h>
#include <wlr/types/wlr_xdg_decoration_v1.h>
#include <wlr/types/wlr_xdg_shell.h>
#include <wlr/types/wlr_layer_shell_v1.h>
#include <wlr/types/wlr_server_decoration.h>
#include <wlr/types/wlr_screencopy_v1.h>
#include <wlr/types/wlr_viewporter.h>
#include <wlr/util/log.h>

/* ─── Paleta de cores oficial RJOS ─────────────────────────────────────────── */
#define RJOS_COLOR_BORDER_ACTIVE   { 0.0f, 0.357f, 0.588f, 1.0f }   /* #005B96 Azul Oceano */
#define RJOS_COLOR_BORDER_INACTIVE { 0.161f, 0.161f, 0.161f, 1.0f } /* #292929 Superfície secundária */
#define RJOS_COLOR_TITLEBAR_BG     { 0.118f, 0.118f, 0.118f, 0.98f } /* #1E1E1E Superfície */
#define RJOS_COLOR_TITLEBAR_TEXT   { 1.0f, 1.0f, 1.0f, 1.0f }       /* #FFFFFF Branco */
#define RJOS_BORDER_WIDTH          2
#define RJOS_TITLEBAR_HEIGHT       32
#define RJOS_CORNER_RADIUS         8
#define RJOS_ANIMATION_MS          200

/* ─── Estruturas principais ─────────────────────────────────────────────────── */

struct rjos_server {
    struct wl_display          *wl_display;
    struct wlr_backend         *backend;
    struct wlr_renderer        *renderer;
    struct wlr_allocator       *allocator;
    struct wlr_scene           *scene;
    struct wlr_scene_output_layout *scene_layout;

    /* Protocolo XDG Shell (janelas de apps) */
    struct wlr_xdg_shell       *xdg_shell;
    struct wl_listener          new_xdg_toplevel;
    struct wl_listener          new_xdg_popup;

    /* Layer shell (painéis, launchers, wallpaper) */
    struct wlr_layer_shell_v1  *layer_shell;
    struct wl_listener          new_layer_surface;

    /* Gerenciamento de outputs (monitores) */
    struct wlr_output_layout   *output_layout;
    struct wl_list              outputs;
    struct wl_listener          new_output;

    /* Gerenciamento de inputs */
    struct wl_list              keyboards;
    struct wl_list              pointers;
    struct wlr_cursor           *cursor;
    struct wlr_xcursor_manager  *cursor_mgr;
    struct wl_listener          cursor_motion;
    struct wl_listener          cursor_motion_absolute;
    struct wl_listener          cursor_button;
    struct wl_listener          cursor_axis;
    struct wl_listener          cursor_frame;
    struct wl_listener          new_input;
    struct wlr_seat             *seat;
    struct wl_listener          request_cursor;
    struct wl_listener          request_set_selection;

    /* Decorações server-side */
    struct wlr_xdg_decoration_manager_v1 *xdg_decoration_manager;
    struct wl_listener          new_toplevel_decoration;

    /* Screencopy (screenshot, recording) */
    struct wlr_screencopy_manager_v1 *screencopy_manager;

    /* Lista de toplevels (janelas) */
    struct wl_list              toplevels;

    /* Workspace ativo (0 a 3) */
    int                         active_workspace;

    /* Toplevel com foco */
    struct rjos_toplevel        *focused_toplevel;

    /* Estado de interação */
    struct {
        enum { RJOS_CURSOR_PASSTHROUGH, RJOS_CURSOR_MOVE, RJOS_CURSOR_RESIZE }
            mode;
        struct rjos_toplevel   *toplevel;
        double                  grab_x, grab_y;
        struct wlr_box          grab_geobox;
        uint32_t                resize_edges;
    } cursor_state;
};

struct rjos_output {
    struct wl_list              link;
    struct rjos_server          *server;
    struct wlr_output           *wlr_output;
    struct wlr_scene_output     *scene_output;
    struct wl_listener          frame;
    struct wl_listener          request_state;
    struct wl_listener          destroy;
};

struct rjos_toplevel {
    struct wl_list              link;
    struct rjos_server          *server;
    struct wlr_xdg_toplevel     *xdg_toplevel;
    struct wlr_scene_tree       *scene_tree;

    /* Listeners de eventos da janela */
    struct wl_listener          map;
    struct wl_listener          unmap;
    struct wl_listener          commit;
    struct wl_listener          destroy;
    struct wl_listener          request_move;
    struct wl_listener          request_resize;
    struct wl_listener          request_maximize;
    struct wl_listener          request_minimize;
    struct wl_listener          request_fullscreen;

    /* Estado da janela */
    bool                        mapped;
    bool                        maximized;
    bool                        minimized;
    bool                        fullscreen;
    int                         workspace;

    /* Geometria antes de maximizar/fullscreen */
    struct wlr_box              saved_geometry;

    /* Animação */
    float                       opacity;          /* 0.0 - 1.0 */
    struct timespec             open_time;
};

struct rjos_keyboard {
    struct wl_list              link;
    struct rjos_server          *server;
    struct wlr_keyboard         *wlr_keyboard;
    struct wl_listener          modifiers;
    struct wl_listener          key;
    struct wl_listener          destroy;
};

/* ─── Funções de foco e workspaces ──────────────────────────────────────────── */

static void rjos_focus_toplevel(struct rjos_toplevel *toplevel,
                                 struct wlr_surface *surface);

static void rjos_set_workspace(struct rjos_server *server, int ws_index) {
    if (ws_index < 0 || ws_index > 3) return;
    server->active_workspace = ws_index;

    struct rjos_toplevel *tl;
    struct rjos_toplevel *focus_candidate = NULL;

    wl_list_for_each(tl, &server->toplevels, link) {
        if (!tl->mapped) continue;
        
        if (tl->workspace == ws_index) {
            wlr_scene_node_set_enabled(&tl->scene_tree->node, true);
            if (!focus_candidate) focus_candidate = tl;
        } else {
            wlr_scene_node_set_enabled(&tl->scene_tree->node, false);
        }
    }
    
    if (focus_candidate) {
        rjos_focus_toplevel(focus_candidate, focus_candidate->xdg_toplevel->base->surface);
    } else {
        wlr_seat_keyboard_clear_focus(server->seat);
        server->focused_toplevel = NULL;
    }
}

static void rjos_focus_toplevel(struct rjos_toplevel *toplevel,
                                 struct wlr_surface *surface) {
    if (toplevel == NULL) return;

    struct rjos_server *server = toplevel->server;
    struct wlr_seat    *seat   = server->seat;

    struct wlr_surface *prev_surface = seat->keyboard_state.focused_surface;
    if (prev_surface == surface) return;

    /* Tira foco da janela anterior */
    if (prev_surface) {
        struct wlr_xdg_surface *prev_xdg =
            wlr_xdg_surface_try_from_wlr_surface(prev_surface);
        if (prev_xdg != NULL) {
            assert(prev_xdg->role == WLR_XDG_SURFACE_ROLE_TOPLEVEL);
            wlr_xdg_toplevel_set_activated(prev_xdg->toplevel, false);
        }
    }

    /* Coloca janela no topo da pilha de renderização */
    wlr_scene_node_raise_to_top(&toplevel->scene_tree->node);

    /* Move para o início da lista (mais recente = mais prioritária) */
    wl_list_remove(&toplevel->link);
    wl_list_insert(&server->toplevels, &toplevel->link);

    /* Ativa decoração da janela */
    wlr_xdg_toplevel_set_activated(toplevel->xdg_toplevel, true);

    /* Transfere foco do teclado */
    struct wlr_keyboard *keyboard = wlr_seat_get_keyboard(seat);
    if (keyboard != NULL) {
        wlr_seat_keyboard_notify_enter(
            seat,
            toplevel->xdg_toplevel->base->surface,
            keyboard->keycodes,
            keyboard->num_keycodes,
            &keyboard->modifiers
        );
    }

    server->focused_toplevel = toplevel;
}

/* ─── Handlers de janela (toplevel) ────────────────────────────────────────── */

static void on_toplevel_map(struct wl_listener *listener, void *data) {
    struct rjos_toplevel *toplevel = wl_container_of(listener, toplevel, map);
    toplevel->mapped = true;

    /* Centraliza janela no output primário */
    struct wlr_output *output =
        wlr_output_layout_get_center_output(toplevel->server->output_layout);

    if (output) {
        int ow, oh;
        wlr_output_effective_resolution(output, &ow, &oh);

        int w = toplevel->xdg_toplevel->base->geometry.width;
        int h = toplevel->xdg_toplevel->base->geometry.height;

        if (w > 0 && h > 0) {
            wlr_scene_node_set_position(
                &toplevel->scene_tree->node,
                (ow - w) / 2,
                (oh - h) / 2
            );
        }
    }

    /* Inicia animação de abertura */
    toplevel->opacity = 0.0f;
    clock_gettime(CLOCK_MONOTONIC, &toplevel->open_time);

    rjos_focus_toplevel(toplevel, toplevel->xdg_toplevel->base->surface);
}

static void on_toplevel_unmap(struct wl_listener *listener, void *data) {
    struct rjos_toplevel *toplevel = wl_container_of(listener, toplevel, unmap);
    toplevel->mapped = false;

    if (toplevel == toplevel->server->focused_toplevel) {
        toplevel->server->focused_toplevel = NULL;
    }
}

static void on_toplevel_destroy(struct wl_listener *listener, void *data) {
    struct rjos_toplevel *toplevel = wl_container_of(listener, toplevel, destroy);

    wl_list_remove(&toplevel->map.link);
    wl_list_remove(&toplevel->unmap.link);
    wl_list_remove(&toplevel->commit.link);
    wl_list_remove(&toplevel->destroy.link);
    wl_list_remove(&toplevel->request_move.link);
    wl_list_remove(&toplevel->request_resize.link);
    wl_list_remove(&toplevel->request_maximize.link);
    wl_list_remove(&toplevel->request_minimize.link);
    wl_list_remove(&toplevel->request_fullscreen.link);
    wl_list_remove(&toplevel->link);

    free(toplevel);
}

static void on_request_move(struct wl_listener *listener, void *data) {
    struct rjos_toplevel *toplevel = wl_container_of(listener, toplevel, request_move);
    struct rjos_server *server = toplevel->server;

    if (toplevel->maximized || toplevel->fullscreen) return;

    server->cursor_state.mode    = RJOS_CURSOR_MOVE;
    server->cursor_state.toplevel = toplevel;
    server->cursor_state.grab_x  = server->cursor->x
        - toplevel->scene_tree->node.x;
    server->cursor_state.grab_y  = server->cursor->y
        - toplevel->scene_tree->node.y;
}

static void on_request_resize(struct wl_listener *listener, void *data) {
    struct wlr_xdg_toplevel_resize_event *event = data;
    struct rjos_toplevel *toplevel = wl_container_of(listener, toplevel, request_resize);
    struct rjos_server *server = toplevel->server;

    if (toplevel->maximized || toplevel->fullscreen) return;

    server->cursor_state.mode         = RJOS_CURSOR_RESIZE;
    server->cursor_state.toplevel      = toplevel;
    server->cursor_state.resize_edges  = event->edges;

    struct wlr_box geo;
    geo = toplevel->xdg_toplevel->base->geometry;
    server->cursor_state.grab_geobox = geo;
    server->cursor_state.grab_geobox.x += toplevel->scene_tree->node.x;
    server->cursor_state.grab_geobox.y += toplevel->scene_tree->node.y;
    server->cursor_state.grab_x = server->cursor->x;
    server->cursor_state.grab_y = server->cursor->y;
}

static void on_request_maximize(struct wl_listener *listener, void *data) {
    struct rjos_toplevel *toplevel =
        wl_container_of(listener, toplevel, request_maximize);

    if (!toplevel->xdg_toplevel->base->initialized) return;

    struct wlr_output *output =
        wlr_output_layout_get_center_output(toplevel->server->output_layout);
    if (!output) return;

    int ow, oh;
    wlr_output_effective_resolution(output, &ow, &oh);

    if (toplevel->xdg_toplevel->requested.maximized) {
        /* Salva geometria atual antes de maximizar */
        struct wlr_box geo;
        geo = toplevel->xdg_toplevel->base->geometry;
        toplevel->saved_geometry.x = toplevel->scene_tree->node.x;
        toplevel->saved_geometry.y = toplevel->scene_tree->node.y;
        toplevel->saved_geometry.width  = geo.width;
        toplevel->saved_geometry.height = geo.height;

        /* Maximiza */
        wlr_xdg_toplevel_set_size(toplevel->xdg_toplevel, ow, oh);
        wlr_scene_node_set_position(&toplevel->scene_tree->node, 0, 0);
        toplevel->maximized = true;
    } else {
        /* Restaura */
        wlr_xdg_toplevel_set_size(toplevel->xdg_toplevel,
            toplevel->saved_geometry.width,
            toplevel->saved_geometry.height);
        wlr_scene_node_set_position(&toplevel->scene_tree->node,
            toplevel->saved_geometry.x,
            toplevel->saved_geometry.y);
        toplevel->maximized = false;
    }

    wlr_xdg_toplevel_set_maximized(
        toplevel->xdg_toplevel,
        toplevel->xdg_toplevel->requested.maximized
    );
}

static void on_request_fullscreen(struct wl_listener *listener, void *data) {
    struct rjos_toplevel *toplevel =
        wl_container_of(listener, toplevel, request_fullscreen);

    if (!toplevel->xdg_toplevel->base->initialized) return;

    struct wlr_output *output =
        wlr_output_layout_get_center_output(toplevel->server->output_layout);
    if (!output) return;

    int ow, oh;
    wlr_output_effective_resolution(output, &ow, &oh);

    bool want_fullscreen = toplevel->xdg_toplevel->requested.fullscreen;

    if (want_fullscreen && !toplevel->fullscreen) {
        struct wlr_box geo;
        geo = toplevel->xdg_toplevel->base->geometry;
        toplevel->saved_geometry.x = toplevel->scene_tree->node.x;
        toplevel->saved_geometry.y = toplevel->scene_tree->node.y;
        toplevel->saved_geometry.width  = geo.width;
        toplevel->saved_geometry.height = geo.height;

        wlr_xdg_toplevel_set_size(toplevel->xdg_toplevel, ow, oh);
        wlr_scene_node_set_position(&toplevel->scene_tree->node, 0, 0);
        toplevel->fullscreen = true;
    } else if (!want_fullscreen && toplevel->fullscreen) {
        wlr_xdg_toplevel_set_size(toplevel->xdg_toplevel,
            toplevel->saved_geometry.width,
            toplevel->saved_geometry.height);
        wlr_scene_node_set_position(&toplevel->scene_tree->node,
            toplevel->saved_geometry.x,
            toplevel->saved_geometry.y);
        toplevel->fullscreen = false;
    }

    wlr_xdg_toplevel_set_fullscreen(toplevel->xdg_toplevel, want_fullscreen);
}

/* ─── Handler novo toplevel ────────────────────────────────────────────────── */

static void on_new_xdg_toplevel(struct wl_listener *listener, void *data) {
    struct rjos_server *server =
        wl_container_of(listener, server, new_xdg_toplevel);
    struct wlr_xdg_toplevel *xdg_toplevel = data;

    struct rjos_toplevel *toplevel = calloc(1, sizeof(*toplevel));
    toplevel->server       = server;
    toplevel->xdg_toplevel = xdg_toplevel;
    toplevel->scene_tree   =
        wlr_scene_xdg_surface_create(&server->scene->tree,
                                      xdg_toplevel->base);

    /* Associa toplevel à scene_tree para lookup */
    toplevel->scene_tree->node.data = toplevel;
    xdg_toplevel->base->data        = toplevel->scene_tree;
    toplevel->workspace             = server->active_workspace;

    /* Conecta listeners */
    toplevel->map.notify            = on_toplevel_map;
    toplevel->unmap.notify          = on_toplevel_unmap;
    toplevel->destroy.notify        = on_toplevel_destroy;
    toplevel->request_move.notify   = on_request_move;
    toplevel->request_resize.notify = on_request_resize;
    toplevel->request_maximize.notify  = on_request_maximize;
    toplevel->request_fullscreen.notify = on_request_fullscreen;

    wl_signal_add(&xdg_toplevel->base->surface->events.map,    &toplevel->map);
    wl_signal_add(&xdg_toplevel->base->surface->events.unmap,  &toplevel->unmap);
    wl_signal_add(&xdg_toplevel->events.destroy,               &toplevel->destroy);
    wl_signal_add(&xdg_toplevel->events.request_move,          &toplevel->request_move);
    wl_signal_add(&xdg_toplevel->events.request_resize,        &toplevel->request_resize);
    wl_signal_add(&xdg_toplevel->events.request_maximize,      &toplevel->request_maximize);
    wl_signal_add(&xdg_toplevel->events.request_fullscreen,    &toplevel->request_fullscreen);

    wl_list_insert(&server->toplevels, &toplevel->link);
}

/* ─── Cursor / Mouse ────────────────────────────────────────────────────────── */

static struct rjos_toplevel *toplevel_at(struct rjos_server *server,
                                          double lx, double ly,
                                          struct wlr_surface **surface,
                                          double *sx, double *sy) {
    struct wlr_scene_node *node = wlr_scene_node_at(
        &server->scene->tree.node, lx, ly, sx, sy
    );

    if (node == NULL || node->type != WLR_SCENE_NODE_BUFFER) return NULL;

    struct wlr_scene_buffer *scene_buffer = wlr_scene_buffer_from_node(node);
    struct wlr_scene_surface *scene_surface =
        wlr_scene_surface_try_from_buffer(scene_buffer);
    if (!scene_surface) return NULL;

    *surface = scene_surface->surface;

    struct wlr_scene_tree *tree = node->parent;
    while (tree != NULL && tree->node.data == NULL) {
        tree = tree->node.parent;
    }

    return tree ? tree->node.data : NULL;
}

static void process_cursor_motion(struct rjos_server *server, uint32_t time) {
    if (server->cursor_state.mode == RJOS_CURSOR_MOVE) {
        /* Mover janela */
        struct rjos_toplevel *tl = server->cursor_state.toplevel;
        wlr_scene_node_set_position(
            &tl->scene_tree->node,
            server->cursor->x - server->cursor_state.grab_x,
            server->cursor->y - server->cursor_state.grab_y
        );
        return;
    }

    if (server->cursor_state.mode == RJOS_CURSOR_RESIZE) {
        /* Redimensionar janela */
        struct rjos_toplevel *tl = server->cursor_state.toplevel;
        double dx = server->cursor->x - server->cursor_state.grab_x;
        double dy = server->cursor->y - server->cursor_state.grab_y;
        struct wlr_box *geo = &server->cursor_state.grab_geobox;

        int new_left   = geo->x;
        int new_right  = geo->x + geo->width;
        int new_top    = geo->y;
        int new_bottom = geo->y + geo->height;

        if (server->cursor_state.resize_edges & WLR_EDGE_LEFT)   new_left   += dx;
        if (server->cursor_state.resize_edges & WLR_EDGE_RIGHT)  new_right  += dx;
        if (server->cursor_state.resize_edges & WLR_EDGE_TOP)    new_top    += dy;
        if (server->cursor_state.resize_edges & WLR_EDGE_BOTTOM) new_bottom += dy;

        int new_w = new_right  - new_left;
        int new_h = new_bottom - new_top;

        struct wlr_box geo_box;
        geo_box = tl->xdg_toplevel->base->geometry;

        wlr_scene_node_set_position(&tl->scene_tree->node,
            new_left - geo_box.x, new_top - geo_box.y);
        wlr_xdg_toplevel_set_size(tl->xdg_toplevel,
            new_w > 64 ? new_w : 64,
            new_h > 32 ? new_h : 32);
        return;
    }

    /* Passthrough: atualiza cursor e surface com foco */
    double sx, sy;
    struct wlr_surface *surface = NULL;
    struct rjos_toplevel *toplevel =
        toplevel_at(server, server->cursor->x, server->cursor->y, &surface, &sx, &sy);

    if (!toplevel) {
        wlr_cursor_set_xcursor(server->cursor, server->cursor_mgr, "default");
    }

    if (surface) {
        wlr_seat_pointer_notify_enter(server->seat, surface, sx, sy);
        wlr_seat_pointer_notify_motion(server->seat, time, sx, sy);
    } else {
        wlr_seat_pointer_clear_focus(server->seat);
    }
}

static void on_cursor_motion(struct wl_listener *listener, void *data) {
    struct rjos_server *server = wl_container_of(listener, server, cursor_motion);
    struct wlr_pointer_motion_event *event = data;
    wlr_cursor_move(server->cursor, &event->pointer->base,
                    event->delta_x, event->delta_y);
    process_cursor_motion(server, event->time_msec);
}

static void on_cursor_motion_absolute(struct wl_listener *listener, void *data) {
    struct rjos_server *server =
        wl_container_of(listener, server, cursor_motion_absolute);
    struct wlr_pointer_motion_absolute_event *event = data;
    wlr_cursor_warp_absolute(server->cursor, &event->pointer->base,
                              event->x, event->y);
    process_cursor_motion(server, event->time_msec);
}

static void on_cursor_button(struct wl_listener *listener, void *data) {
    struct rjos_server *server = wl_container_of(listener, server, cursor_button);
    struct wlr_pointer_button_event *event = data;

    wlr_seat_pointer_notify_button(server->seat,
        event->time_msec, event->button, event->state);

    if (event->state == WL_POINTER_BUTTON_STATE_RELEASED) {
        /* Lógica de Window Snap (arrastar para as bordas) */
        if (server->cursor_state.mode == RJOS_CURSOR_MOVE && server->cursor_state.toplevel) {
            struct rjos_toplevel *tl = server->cursor_state.toplevel;
            struct wlr_output *output = wlr_output_layout_get_center_output(server->output_layout);
            if (output) {
                int ow, oh;
                wlr_output_effective_resolution(output, &ow, &oh);
                
                if (server->cursor->x <= 10) {
                    /* Snap metade esquerda */
                    wlr_xdg_toplevel_set_size(tl->xdg_toplevel, ow / 2, oh);
                    wlr_scene_node_set_position(&tl->scene_tree->node, 0, 0);
                } else if (server->cursor->x >= ow - 10) {
                    /* Snap metade direita */
                    wlr_xdg_toplevel_set_size(tl->xdg_toplevel, ow / 2, oh);
                    wlr_scene_node_set_position(&tl->scene_tree->node, ow / 2, 0);
                } else if (server->cursor->y <= 10) {
                    /* Snap maximizar (topo) */
                    if (!tl->maximized) {
                        struct wlr_box geo;
                        geo = tl->xdg_toplevel->base->geometry;
                        tl->saved_geometry.x = tl->scene_tree->node.x;
                        tl->saved_geometry.y = tl->scene_tree->node.y;
                        tl->saved_geometry.width = geo.width;
                        tl->saved_geometry.height = geo.height;
                        
                        wlr_xdg_toplevel_set_size(tl->xdg_toplevel, ow, oh);
                        wlr_scene_node_set_position(&tl->scene_tree->node, 0, 0);
                        tl->maximized = true;
                        wlr_xdg_toplevel_set_maximized(tl->xdg_toplevel, true);
                    }
                }
            }
        }
        
        /* Termina move/resize ao soltar botão */
        server->cursor_state.mode = RJOS_CURSOR_PASSTHROUGH;
        server->cursor_state.toplevel = NULL;
        return;
    }

    /* Clique: foca janela sob o cursor */
    double sx, sy;
    struct wlr_surface *surface = NULL;
    struct rjos_toplevel *toplevel =
        toplevel_at(server, server->cursor->x, server->cursor->y, &surface, &sx, &sy);

    if (toplevel) {
        rjos_focus_toplevel(toplevel, surface);
    }
}

static void on_cursor_axis(struct wl_listener *listener, void *data) {
    struct rjos_server *server = wl_container_of(listener, server, cursor_axis);
    struct wlr_pointer_axis_event *event = data;
    wlr_seat_pointer_notify_axis(server->seat,
        event->time_msec, event->orientation,
        event->delta, event->delta_discrete, event->source,
        event->relative_direction);
}

static void on_cursor_frame(struct wl_listener *listener, void *data) {
    struct rjos_server *server = wl_container_of(listener, server, cursor_frame);
    wlr_seat_pointer_notify_frame(server->seat);
}

/* ─── Teclado ──────────────────────────────────────────────────────────────── */

static bool rjos_handle_keybinding(struct rjos_server *server, xkb_keysym_t sym,
                                    uint32_t modifiers) {
    /* Super = Mod4 */
    bool super = (modifiers & WLR_MODIFIER_LOGO) != 0;
    bool shift = (modifiers & WLR_MODIFIER_SHIFT) != 0;
    bool alt   = (modifiers & WLR_MODIFIER_ALT) != 0;

    /* Super+Q — Fecha janela focada */
    if (super && sym == XKB_KEY_q) {
        if (server->focused_toplevel) {
            wlr_xdg_toplevel_send_close(server->focused_toplevel->xdg_toplevel);
            return true;
        }
    }

    /* Super+T — Abre terminal (rjos-terminal) */
    if (super && sym == XKB_KEY_t) {
        if (fork() == 0) {
            execl("/bin/sh", "sh", "-c",
                  "rjos-terminal || xterm || foot || alacritty", NULL);
            _exit(0);
        }
        return true;
    }

    /* Super+F — Abre gerenciador de arquivos */
    if (super && sym == XKB_KEY_f) {
        if (fork() == 0) {
            execl("/bin/sh", "sh", "-c", "rjos-files", NULL);
            _exit(0);
        }
        return true;
    }

    /* Super+Space — Abre launcher */
    if (super && sym == XKB_KEY_space) {
        if (fork() == 0) {
            execl("/bin/sh", "sh", "-c", "rjos-launcher || wofi --show run", NULL);
            _exit(0);
        }
        return true;
    }

    /* Super+M — Maximizar janela focada */
    if (super && sym == XKB_KEY_m) {
        if (server->focused_toplevel) {
            struct rjos_toplevel *tl = server->focused_toplevel;
            bool new_state = !tl->maximized;
            wlr_xdg_toplevel_set_maximized(tl->xdg_toplevel, new_state);
            on_request_maximize(&tl->request_maximize, NULL);
            return true;
        }
    }

    /* Super+1 a Super+4 — Trocar workspace */
    if (super && !shift && sym >= XKB_KEY_1 && sym <= XKB_KEY_4) {
        rjos_set_workspace(server, sym - XKB_KEY_1);
        return true;
    }

    /* Super+Shift+1 a Super+Shift+4 — Mover janela para workspace */
    if (super && shift && sym >= XKB_KEY_1 && sym <= XKB_KEY_4) {
        if (server->focused_toplevel) {
            server->focused_toplevel->workspace = sym - XKB_KEY_1;
            wlr_scene_node_set_enabled(&server->focused_toplevel->scene_tree->node, false);
            server->focused_toplevel = NULL;
            rjos_set_workspace(server, server->active_workspace);
        }
        return true;
    }

    /* Super+Tab — Alterna janelas no workspace atual */
    if (super && sym == XKB_KEY_Tab) {
        struct rjos_toplevel *next = NULL;
        struct rjos_toplevel *tl;
        bool take_next = false;

        wl_list_for_each(tl, &server->toplevels, link) {
            if (!tl->mapped || tl->workspace != server->active_workspace) continue;
            if (take_next) { next = tl; break; }
            if (tl == server->focused_toplevel) take_next = true;
        }

        if (!next) {
            wl_list_for_each(tl, &server->toplevels, link) {
                if (tl->mapped && tl->workspace == server->active_workspace) { next = tl; break; }
            }
        }

        if (next) rjos_focus_toplevel(next, next->xdg_toplevel->base->surface);
        return true;
    }

    /* Super+Left — Janela na metade esquerda */
    if (super && sym == XKB_KEY_Left) {
        if (server->focused_toplevel) {
            struct wlr_output *output =
                wlr_output_layout_get_center_output(server->output_layout);
            if (output) {
                int ow, oh;
                wlr_output_effective_resolution(output, &ow, &oh);
                struct rjos_toplevel *tl = server->focused_toplevel;
                wlr_xdg_toplevel_set_size(tl->xdg_toplevel, ow / 2, oh);
                wlr_scene_node_set_position(&tl->scene_tree->node, 0, 0);
            }
        }
        return true;
    }

    /* Super+Right — Janela na metade direita */
    if (super && sym == XKB_KEY_Right) {
        if (server->focused_toplevel) {
            struct wlr_output *output =
                wlr_output_layout_get_center_output(server->output_layout);
            if (output) {
                int ow, oh;
                wlr_output_effective_resolution(output, &ow, &oh);
                struct rjos_toplevel *tl = server->focused_toplevel;
                wlr_xdg_toplevel_set_size(tl->xdg_toplevel, ow / 2, oh);
                wlr_scene_node_set_position(&tl->scene_tree->node, ow / 2, 0);
            }
        }
        return true;
    }

    /* Super+Shift+E — Encerrar compositor (logout) */
    if (super && shift && sym == XKB_KEY_e) {
        wl_display_terminate(server->wl_display);
        return true;
    }

    return false;
}

static void on_keyboard_key(struct wl_listener *listener, void *data) {
    struct rjos_keyboard *kb = wl_container_of(listener, kb, key);
    struct rjos_server   *server = kb->server;
    struct wlr_keyboard_key_event *event = data;
    struct wlr_seat *seat = server->seat;

    uint32_t keycode = event->keycode + 8;
    const xkb_keysym_t *syms;
    int nsyms = xkb_state_key_get_syms(
        kb->wlr_keyboard->xkb_state, keycode, &syms);

    bool handled = false;
    uint32_t modifiers = wlr_keyboard_get_modifiers(kb->wlr_keyboard);

    if (event->state == WL_KEYBOARD_KEY_STATE_PRESSED) {
        for (int i = 0; i < nsyms; i++) {
            handled = rjos_handle_keybinding(server, syms[i], modifiers);
        }
    }

    if (!handled) {
        wlr_seat_keyboard_notify_key(seat,
            event->time_msec, event->keycode, event->state);
    }
}

static void on_keyboard_modifiers(struct wl_listener *listener, void *data) {
    struct rjos_keyboard *kb = wl_container_of(listener, kb, modifiers);
    wlr_seat_keyboard_notify_modifiers(
        kb->server->seat, &kb->wlr_keyboard->modifiers);
}

static void on_keyboard_destroy(struct wl_listener *listener, void *data) {
    struct rjos_keyboard *kb = wl_container_of(listener, kb, destroy);
    wl_list_remove(&kb->modifiers.link);
    wl_list_remove(&kb->key.link);
    wl_list_remove(&kb->destroy.link);
    wl_list_remove(&kb->link);
    free(kb);
}

static void rjos_new_keyboard(struct rjos_server *server,
                               struct wlr_input_device *device) {
    struct wlr_keyboard *wlr_kb = wlr_keyboard_from_input_device(device);

    struct rjos_keyboard *kb = calloc(1, sizeof(*kb));
    kb->server      = server;
    kb->wlr_keyboard = wlr_kb;

    /* Layout de teclado — detecta do ambiente ou usa ABNT2 */
    const char *layout = getenv("RJOS_KB_LAYOUT");
    if (!layout) layout = "br";

    struct xkb_context *ctx = xkb_context_new(XKB_CONTEXT_NO_FLAGS);
    struct xkb_rule_names rules = {
        .layout  = layout,
        .variant = "",
    };
    struct xkb_keymap *keymap =
        xkb_keymap_new_from_names(ctx, &rules, XKB_KEYMAP_COMPILE_NO_FLAGS);

    wlr_keyboard_set_keymap(wlr_kb, keymap);
    xkb_keymap_unref(keymap);
    xkb_context_unref(ctx);

    /* Taxa de repetição */
    wlr_keyboard_set_repeat_info(wlr_kb, 25, 600);

    kb->modifiers.notify = on_keyboard_modifiers;
    kb->key.notify       = on_keyboard_key;
    kb->destroy.notify   = on_keyboard_destroy;

    wl_signal_add(&wlr_kb->events.modifiers, &kb->modifiers);
    wl_signal_add(&wlr_kb->events.key,       &kb->key);
    wl_signal_add(&device->events.destroy,   &kb->destroy);

    wlr_seat_set_keyboard(server->seat, wlr_kb);
    wl_list_insert(&server->keyboards, &kb->link);
}

static void on_new_input(struct wl_listener *listener, void *data) {
    struct rjos_server      *server = wl_container_of(listener, server, new_input);
    struct wlr_input_device *device = data;

    switch (device->type) {
    case WLR_INPUT_DEVICE_KEYBOARD:
        rjos_new_keyboard(server, device);
        break;
    case WLR_INPUT_DEVICE_POINTER:
        wlr_cursor_attach_input_device(server->cursor, device);
        break;
    default:
        break;
    }

    /* Atualiza capacidades do seat */
    uint32_t caps = 0;
    if (!wl_list_empty(&server->keyboards)) caps |= WL_SEAT_CAPABILITY_KEYBOARD;
    caps |= WL_SEAT_CAPABILITY_POINTER;
    wlr_seat_set_capabilities(server->seat, caps);
}

/* ─── Output (monitor) ──────────────────────────────────────────────────────── */

static void on_output_frame(struct wl_listener *listener, void *data) {
    struct rjos_output *output = wl_container_of(listener, output, frame);
    struct wlr_scene   *scene  = output->server->scene;

    struct wlr_scene_output *scene_output =
        wlr_scene_get_scene_output(scene, output->wlr_output);

    wlr_scene_output_commit(scene_output, NULL);

    struct timespec now;
    clock_gettime(CLOCK_MONOTONIC, &now);
    wlr_scene_output_send_frame_done(scene_output, &now);
}

static void on_output_request_state(struct wl_listener *listener, void *data) {
    struct rjos_output *output =
        wl_container_of(listener, output, request_state);
    const struct wlr_output_event_request_state *event = data;
    wlr_output_commit_state(output->wlr_output, event->state);
}

static void on_output_destroy(struct wl_listener *listener, void *data) {
    struct rjos_output *output = wl_container_of(listener, output, destroy);
    wl_list_remove(&output->frame.link);
    wl_list_remove(&output->request_state.link);
    wl_list_remove(&output->destroy.link);
    wl_list_remove(&output->link);
    free(output);
}

static void on_new_output(struct wl_listener *listener, void *data) {
    struct rjos_server *server = wl_container_of(listener, server, new_output);
    struct wlr_output  *wlr_output = data;

    wlr_output_init_render(wlr_output, server->allocator, server->renderer);

    /* Configuração inicial do output */
    struct wlr_output_state state;
    wlr_output_state_init(&state);
    wlr_output_state_set_enabled(&state, true);

    /* Modo preferido (resolução nativa) */
    struct wlr_output_mode *mode = wlr_output_preferred_mode(wlr_output);
    if (mode != NULL) {
        wlr_output_state_set_mode(&state, mode);
    }
    wlr_output_commit_state(wlr_output, &state);
    wlr_output_state_finish(&state);

    struct rjos_output *output = calloc(1, sizeof(*output));
    output->wlr_output = wlr_output;
    output->server     = server;

    output->frame.notify         = on_output_frame;
    output->request_state.notify = on_output_request_state;
    output->destroy.notify       = on_output_destroy;

    wl_signal_add(&wlr_output->events.frame,         &output->frame);
    wl_signal_add(&wlr_output->events.request_state, &output->request_state);
    wl_signal_add(&wlr_output->events.destroy,        &output->destroy);

    wl_list_insert(&server->outputs, &output->link);

    /* Adiciona ao layout (posição automática) */
    struct wlr_output_layout_output *l_output =
        wlr_output_layout_add_auto(server->output_layout, wlr_output);

    output->scene_output =
        wlr_scene_output_create(server->scene, wlr_output);
    wlr_scene_output_layout_add_output(server->scene_layout, l_output,
                                        output->scene_output);

    wlr_log(WLR_INFO, "Novo monitor: %s (%dx%d)",
            wlr_output->name,
            wlr_output->width,
            wlr_output->height);
}

/* ─── Decorações server-side ────────────────────────────────────────────────── */

static void on_new_toplevel_decoration(struct wl_listener *listener, void *data) {
    struct wlr_xdg_toplevel_decoration_v1 *decoration = data;
    /* Força decorações server-side (compositor desenha bordas) */
    wlr_xdg_toplevel_decoration_v1_set_mode(
        decoration,
        WLR_XDG_TOPLEVEL_DECORATION_V1_MODE_SERVER_SIDE
    );
}

/* ─── Inicialização do servidor ─────────────────────────────────────────────── */

static bool rjos_server_init(struct rjos_server *server) {
    wlr_log_init(WLR_DEBUG, NULL);

    server->wl_display = wl_display_create();
    if (!server->wl_display) return false;

    server->backend = wlr_backend_autocreate(
        wl_display_get_event_loop(server->wl_display), NULL);
    if (!server->backend) {
        wlr_log(WLR_ERROR, "Falha ao criar backend wlroots");
        return false;
    }

    server->renderer = wlr_renderer_autocreate(server->backend);
    if (!server->renderer) return false;
    wlr_renderer_init_wl_display(server->renderer, server->wl_display);

    server->allocator = wlr_allocator_autocreate(server->backend, server->renderer);
    if (!server->allocator) return false;

    /* Compositor e subcompositor Wayland */
    wlr_compositor_create(server->wl_display, 5, server->renderer);
    wlr_subcompositor_create(server->wl_display);
    wlr_data_device_manager_create(server->wl_display);

    /* Output layout */
    server->output_layout = wlr_output_layout_create(server->wl_display);
    wl_list_init(&server->outputs);
    server->new_output.notify = on_new_output;
    wl_signal_add(&server->backend->events.new_output, &server->new_output);

    /* Scene graph */
    server->scene = wlr_scene_create();
    server->scene_layout =
        wlr_scene_attach_output_layout(server->scene, server->output_layout);

    /* XDG Shell */
    wl_list_init(&server->toplevels);
    server->xdg_shell = wlr_xdg_shell_create(server->wl_display, 3);
    server->new_xdg_toplevel.notify = on_new_xdg_toplevel;
    wl_signal_add(&server->xdg_shell->events.new_toplevel,
                  &server->new_xdg_toplevel);

    /* Layer Shell */
    server->layer_shell = wlr_layer_shell_v1_create(server->wl_display, 4);

    /* Cursor */
    server->cursor = wlr_cursor_create();
    wlr_cursor_attach_output_layout(server->cursor, server->output_layout);
    server->cursor_mgr = wlr_xcursor_manager_create(NULL, 24);

    server->cursor_motion.notify          = on_cursor_motion;
    server->cursor_motion_absolute.notify = on_cursor_motion_absolute;
    server->cursor_button.notify          = on_cursor_button;
    server->cursor_axis.notify            = on_cursor_axis;
    server->cursor_frame.notify           = on_cursor_frame;

    wl_signal_add(&server->cursor->events.motion,          &server->cursor_motion);
    wl_signal_add(&server->cursor->events.motion_absolute, &server->cursor_motion_absolute);
    wl_signal_add(&server->cursor->events.button,          &server->cursor_button);
    wl_signal_add(&server->cursor->events.axis,            &server->cursor_axis);
    wl_signal_add(&server->cursor->events.frame,           &server->cursor_frame);

    /* Input */
    wl_list_init(&server->keyboards);
    server->new_input.notify = on_new_input;
    wl_signal_add(&server->backend->events.new_input, &server->new_input);

    /* Seat */
    server->seat = wlr_seat_create(server->wl_display, "seat0");
    server->request_cursor.notify = NULL;  /* implementado via wlr_seat */

    /* Decorações */
    server->xdg_decoration_manager =
        wlr_xdg_decoration_manager_v1_create(server->wl_display);
    server->new_toplevel_decoration.notify = on_new_toplevel_decoration;
    wl_signal_add(&server->xdg_decoration_manager->events.new_toplevel_decoration,
                  &server->new_toplevel_decoration);

    /* Screencopy */
    server->screencopy_manager =
        wlr_screencopy_manager_v1_create(server->wl_display);

    /* Viewporter */
    wlr_viewporter_create(server->wl_display);

    return true;
}

/* ─── main ──────────────────────────────────────────────────────────────────── */

int main(int argc, char *argv[]) {
    /* Parse argumentos */
    int opt;
    while ((opt = getopt(argc, argv, "s:h")) != -1) {
        switch (opt) {
        case 's':
            /* -s "comando a executar no startup" */
            break;
        case 'h':
            fprintf(stdout,
                "rjos-compositor — RJOS Wayland Compositor\n"
                "Uso: rjos-compositor [-s 'startup-cmd']\n"
                "  -s CMD   Executa CMD ao iniciar\n"
                "  -h       Mostra esta ajuda\n"
            );
            return 0;
        }
    }

    fprintf(stdout, "\n  RJOS Compositor iniciando...\n\n");

    struct rjos_server server = {0};

    if (!rjos_server_init(&server)) {
        fprintf(stderr, "Falha ao inicializar compositor\n");
        return 1;
    }

    /* Socket Wayland */
    const char *socket = wl_display_add_socket_auto(server.wl_display);
    if (!socket) {
        fprintf(stderr, "Falha ao criar socket Wayland\n");
        wlr_backend_destroy(server.backend);
        return 1;
    }

    if (!wlr_backend_start(server.backend)) {
        fprintf(stderr, "Falha ao iniciar backend\n");
        wlr_backend_destroy(server.backend);
        wl_display_destroy(server.wl_display);
        return 1;
    }

    setenv("WAYLAND_DISPLAY", socket, true);
    setenv("XDG_SESSION_TYPE", "wayland", true);
    setenv("XDG_CURRENT_DESKTOP", "RJOS", true);
    setenv("MOZ_ENABLE_WAYLAND", "1", true);
    setenv("QT_QPA_PLATFORM", "wayland", true);

    fprintf(stdout, "  WAYLAND_DISPLAY=%s\n\n", socket);

    /* Inicia a shell do desktop (painel, wallpaper) */
    if (fork() == 0) {
        execl("/bin/sh", "sh", "-c",
              "sleep 0.5 && rjos-shell", NULL);
        _exit(0);
    }

    /* Loop de eventos principal */
    wlr_log(WLR_INFO, "RJOS Compositor ativo em WAYLAND_DISPLAY=%s", socket);
    wl_display_run(server.wl_display);

    wl_display_destroy_clients(server.wl_display);
    wlr_scene_node_destroy(&server.scene->tree.node);
    wlr_xcursor_manager_destroy(server.cursor_mgr);
    wlr_cursor_destroy(server.cursor);
    wlr_output_layout_destroy(server.output_layout);
    wlr_backend_destroy(server.backend);
    wl_display_destroy(server.wl_display);

    return 0;
}
