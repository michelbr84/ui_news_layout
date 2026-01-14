import json
import os
import sys
import pygame

pygame.init()
pygame.display.set_caption("Noticias (Pygame Mock)")

# -----------------------------
# Fullscreen (real)
# -----------------------------
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
FPS = 60

BG_IMAGE_PATH = "bg.png"  # opcional

# -----------------------------
# Colors
# -----------------------------
C_BLACK = (0, 0, 0)
C_WHITE = (245, 245, 245)
C_GRAY = (120, 120, 120)

C_BLUE_DARK = (6, 18, 70)
C_BLUE = (10, 38, 140)
C_BLUE_BRIGHT = (35, 95, 230)

C_YELLOW = (255, 210, 45)

C_RED = (175, 0, 0)
C_RED_DARK = (120, 0, 0)

C_PURPLE = (35, 0, 70)
C_PURPLE_2 = (55, 0, 110)
C_PURPLE_LINE = (180, 150, 255)

C_PANEL = (18, 18, 18, 180)
C_PANEL_2 = (15, 15, 15, 210)

# -----------------------------
# Categories
# -----------------------------
CATEGORY_ALL = "Todas"
TOP_CATEGORIES = ["Mensagens", "Competições", "Lesões e Suspensões"]
BOTTOM_CATEGORIES = ["Contratos e Imprensa", "Transferências", "Empregos", "Registos"]

ALL_CATEGORIES = [CATEGORY_ALL] + TOP_CATEGORIES + BOTTOM_CATEGORIES

# Accept alias from user JSON
CATEGORY_ALIASES = {
    "Registros": "Registos",
    "Registro": "Registos",
    "Registo": "Registos",
}

DEFAULT_CATEGORY = "Mensagens"

# -----------------------------
# JSON
# -----------------------------
DEFAULT_JSON_PATH = "news_data.json"

DEFAULT_JSON = {
    "coach_name": "Michel Duek",
    "sidebar_date": "Sábado\n25.9.04 TAR",
    "news": [
        {
            "date": "Qui 23 Set NTE",
            "category": "Competições",
            "title": "Observação do Botafogo terminada",
            "description": (
                "Artur Neto normalmente faz jogar o Botafogo num estilo 4-4-2 ofensivo e de qualidade.\n\n"
                "A má classificação do Botafogo não deixa perceber a verdadeira qualidade da equipa.\n\n"
                "Temos sorte em Vádson, que é o melhor defesa deles, estar lesionado neste momento."
            )
        },
        {
            "date": "Qui 23 Set TAR",
            "category": "Mensagens",
            "title": "Coritiba contrata Maria",
            "description": "O Coritiba anunciou a contratação de Maria. Detalhes adicionais serão divulgados em breve."
        }
    ]
}

def ensure_default_json(path: str) -> None:
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_JSON, f, ensure_ascii=False, indent=2)

def _normalize_category(cat: str) -> str:
    if not cat:
        return DEFAULT_CATEGORY
    cat = str(cat).strip()
    if cat in CATEGORY_ALIASES:
        cat = CATEGORY_ALIASES[cat]
    # Allow only known categories; otherwise default
    if cat not in TOP_CATEGORIES and cat not in BOTTOM_CATEGORIES:
        return DEFAULT_CATEGORY
    return cat

def load_data(path: str) -> dict:
    ensure_default_json(path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if "coach_name" not in data or not isinstance(data["coach_name"], str) or not data["coach_name"].strip():
        data["coach_name"] = "Michel Duek"

    if "sidebar_date" not in data or not isinstance(data["sidebar_date"], str) or not data["sidebar_date"].strip():
        data["sidebar_date"] = "Sábado\n25.9.04 TAR"

    if "news" not in data or not isinstance(data["news"], list):
        data["news"] = []

    normalized = []
    for item in data["news"]:
        if not isinstance(item, dict):
            continue

        date = str(item.get("date", "")).strip() or "—"
        title = str(item.get("title", "")).strip()
        desc = str(item.get("description", "")).strip() or "—"
        cat = _normalize_category(item.get("category", DEFAULT_CATEGORY))

        if not title:
            continue

        normalized.append({
            "date": date,
            "category": cat,
            "title": title,
            "description": desc
        })

    data["news"] = normalized
    return data

# -----------------------------
# Date parsing for sorting
# Expected examples:
# "Qui 13 Jan NTE"
# "Qua 22 Set TAR"
# Also supports "14.1.26 TAR" (basic)
# -----------------------------
MONTHS = {
    "JAN": 1, "FEV": 2, "FEB": 2, "MAR": 3, "ABR": 4, "APR": 4, "MAI": 5, "MAY": 5,
    "JUN": 6, "JUL": 7, "AGO": 8, "AUG": 8, "SET": 9, "SEP": 9, "OUT": 10, "OCT": 10,
    "NOV": 11, "DEZ": 12, "DEC": 12
}
TIME_PART = {"MAN": 1, "TAR": 2, "NTE": 3, "NOI": 3, "NIGHT": 3}

def date_sort_key(date_str: str):
    """
    Returns a tuple comparable for sorting (year, month, day, timepart).
    If year missing, uses 0.
    If parsing fails, returns very small key.
    """
    if not date_str or date_str == "—":
        return (0, 0, 0, 0)

    s = str(date_str).strip()

    # Format like "14.1.26 TAR"
    # day.month.year2
    try:
        parts = s.split()
        if parts and "." in parts[0]:
            dmy = parts[0].split(".")
            if len(dmy) >= 3:
                d = int(dmy[0])
                m = int(dmy[1])
                y2 = int(dmy[2])
                y = 2000 + y2 if y2 < 100 else y2
                tp = TIME_PART.get(parts[1].upper(), 0) if len(parts) > 1 else 0
                return (y, m, d, tp)
    except Exception:
        pass

    # Format like "Qui 13 Jan NTE" or "Qua 22 Set TAR"
    tokens = s.replace("-", " ").split()
    # Find a day number token
    day = None
    month = None
    year = 0
    tp = 0

    for i, tok in enumerate(tokens):
        t = tok.strip()
        if t.isdigit():
            day = int(t)
            # month token expected next
            if i + 1 < len(tokens):
                mt = tokens[i + 1].upper()
                month = MONTHS.get(mt, None)
            # year optional next-next (rare)
            if i + 2 < len(tokens):
                yt = tokens[i + 2]
                if yt.isdigit():
                    yv = int(yt)
                    year = 2000 + yv if yv < 100 else yv
            break

    # time part is usually last token
    if tokens:
        tp = TIME_PART.get(tokens[-1].upper(), 0)

    if day is None or month is None:
        return (0, 0, 0, 0)

    return (year, month, day, tp)

def sort_news_by_date_desc(items):
    # newest first (descending)
    # if some items share same key, keep stable by original order
    indexed = list(enumerate(items))
    indexed.sort(key=lambda it: (date_sort_key(it[1].get("date", "—")), it[0]), reverse=True)
    return [it[1] for it in indexed]

def filter_news(master_news, current_filter: str):
    if current_filter == CATEGORY_ALL:
        return sort_news_by_date_desc(master_news)

    # Filter by selected category and then sort by date desc
    filtered = [n for n in master_news if n.get("category") == current_filter]
    return sort_news_by_date_desc(filtered)

# -----------------------------
# Responsive scaling
# Base layout reference: 800x600
# -----------------------------
BASE_W, BASE_H = 800, 600
sx = WIDTH / BASE_W
sy = HEIGHT / BASE_H
s_font = (sx + sy) / 2.0

def Sx(v: float) -> int:
    return int(round(v * sx))

def Sy(v: float) -> int:
    return int(round(v * sy))

def Sf(v: float) -> int:
    return max(10, int(round(v * s_font)))

# -----------------------------
# Fonts (scaled)
# -----------------------------
def get_font(size, bold=False):
    return pygame.font.SysFont("arial", size, bold=bold)

FONT_12 = get_font(Sf(12))
FONT_14 = get_font(Sf(14))
FONT_16 = get_font(Sf(16))
FONT_22 = get_font(Sf(22), bold=True)
FONT_28 = get_font(Sf(28), bold=True)

# -----------------------------
# Helpers
# -----------------------------
def in_rect(pos, rect):
    return rect.collidepoint(pos)

def beveled_panel(surface, rect, fill, border_outer, border_inner=None, radius=0):
    pygame.draw.rect(surface, fill, rect, border_radius=radius)
    pygame.draw.rect(surface, border_outer, rect, max(1, Sx(2)), border_radius=radius)
    if border_inner:
        inner = rect.inflate(-Sx(4), -Sy(4))
        pygame.draw.rect(surface, border_inner, inner, max(1, Sx(1)), border_radius=radius)

def draw_text(surface, text, font, color, rect, align="center"):
    img = font.render(text, True, color)
    r = img.get_rect()
    if align == "center":
        r.center = rect.center
    elif align == "midleft":
        r.midleft = (rect.left + Sx(10), rect.centery)
    elif align == "topleft":
        r.topleft = (rect.left + Sx(10), rect.top + Sy(6))
    else:
        r.center = rect.center
    surface.blit(img, r)
    return r

def draw_text_wrapped(surface, text, font, color, x, y, max_width, line_height):
    words = text.split()
    line = ""
    cur_y = y
    for w in words:
        test = (line + " " + w).strip()
        if font.size(test)[0] <= max_width:
            line = test
        else:
            surface.blit(font.render(line, True, color), (x, cur_y))
            cur_y += line_height
            line = w
    if line:
        surface.blit(font.render(line, True, color), (x, cur_y))
        cur_y += line_height
    return cur_y

def button(surface, rect, label, *, active=False, hovered=False, small=False):
    base = C_PURPLE_2 if hovered else C_PURPLE
    if active:
        base = (min(255, base[0] + 25), min(255, base[1] + 10), min(255, base[2] + 25))
    beveled_panel(surface, rect, base, C_PURPLE_LINE, C_BLACK, radius=max(2, Sx(4)))
    font = FONT_14 if small else FONT_16
    color = C_YELLOW if active else C_WHITE
    draw_text(surface, label, font, color, rect, align="center")

def draw_sidebar_button(surface, rect, label, *, hovered=False, selected=False):
    base = C_BLUE if (hovered or selected) else C_BLUE_DARK
    pygame.draw.rect(surface, base, rect)
    pygame.draw.rect(surface, C_BLUE_BRIGHT, rect, max(1, Sx(1)))
    color = C_YELLOW if selected else C_WHITE

    lines = str(label).split("\n")
    lh = Sy(16)
    total_h = len(lines) * lh
    y = rect.centery - total_h // 2
    for ln in lines:
        img = FONT_14.render(ln, True, color)
        r = img.get_rect(center=(rect.centerx, y + lh // 2))
        surface.blit(img, r)
        y += lh

def draw_arrow(surface, rect, direction):
    pygame.draw.rect(surface, C_BLACK, rect, border_radius=max(2, Sx(3)))
    pygame.draw.rect(surface, C_YELLOW, rect, max(1, Sx(1)), border_radius=max(2, Sx(3)))
    cx, cy = rect.center
    d = Sx(6)
    if direction == "left":
        pts = [(cx + d, cy - d), (cx - d, cy), (cx + d, cy + d)]
    else:
        pts = [(cx - d, cy - d), (cx + d, cy), (cx - d, cy + d)]
    pygame.draw.polygon(surface, C_YELLOW, pts)

# -----------------------------
# Background
# -----------------------------
def load_bg():
    if os.path.exists(BG_IMAGE_PATH):
        try:
            img = pygame.image.load(BG_IMAGE_PATH).convert()
            return pygame.transform.smoothscale(img, (WIDTH, HEIGHT))
        except Exception:
            return None
    return None

# -----------------------------
# Main app
# -----------------------------
def run(json_path: str):
    clock = pygame.time.Clock()
    BG = load_bg()

    # Tabs (labels must match categories)
    top_tabs = [CATEGORY_ALL] + TOP_CATEGORIES
    bottom_tabs = BOTTOM_CATEGORIES[:]  # already correct labels

    # Current filter (one unified filter)
    current_filter = CATEGORY_ALL

    # Load data
    data = load_data(json_path)
    coach_name = data["coach_name"]
    sidebar_date = data["sidebar_date"]
    master_news = data["news"] or [{
        "date": "—",
        "category": DEFAULT_CATEGORY,
        "title": "Sem notícias",
        "description": "O JSON não contém notícias."
    }]

    news = filter_news(master_news, current_filter)
    if not news:
        news = [{
            "date": "—",
            "category": DEFAULT_CATEGORY,
            "title": "Sem notícias",
            "description": "Nenhuma notícia nesta categoria."
        }]

    selected_news = 0
    news_scroll = 0
    visible_rows = 5

    # Hover
    hover_top = None
    hover_bottom = None
    hover_sb = None
    hover_news = None
    hover_read_next = False

    # ------------- Layout (responsive) -------------
    SIDEBAR_W = Sx(170)
    MAIN_X = SIDEBAR_W + Sx(10)
    MAIN_W = WIDTH - MAIN_X - Sx(10)

    DATE_RECT = pygame.Rect(Sx(10), Sy(10), SIDEBAR_W - Sx(20), Sy(55))
    ARROW_W = Sx(28)
    arrow_left = pygame.Rect(DATE_RECT.left + Sx(8), DATE_RECT.bottom - Sy(28), ARROW_W, Sy(20))
    arrow_right = pygame.Rect(DATE_RECT.right - Sx(8) - ARROW_W, DATE_RECT.bottom - Sy(28), ARROW_W, Sy(20))

    # Sidebar menu
    SB_BTN_H = Sy(38)
    SB_BTN_GAP = Sy(6)
    SB_MENU = [
        "Continuar\nJogo",
        coach_name,
        "Competições",
        "Nações\n& Clubes",
        "Procurar",
        "Trocar\nJogador",
        "Opções\nJogo",
    ]
    sb_btn_rects = []
    sb_y = DATE_RECT.bottom + Sy(10)
    for i in range(len(SB_MENU)):
        sb_btn_rects.append(
            pygame.Rect(Sx(10), sb_y + i * (SB_BTN_H + SB_BTN_GAP), SIDEBAR_W - Sx(20), SB_BTN_H)
        )

    # Title + frame
    main_frame = pygame.Rect(MAIN_X, Sy(10), MAIN_W, HEIGHT - Sy(20))
    title_rect = pygame.Rect(MAIN_X + Sx(10), Sy(20), MAIN_W - Sx(20), Sy(46))

    # Tabs top
    TAB_H = max(Sy(36), Sy(44))
    tab_x = MAIN_X + Sx(10)
    tab_y = Sy(80)
    gap = Sx(6)
    tab_total_w = MAIN_W - Sx(20)
    tab_w = (tab_total_w - gap * (len(top_tabs) - 1)) // len(top_tabs)
    top_tab_rects = []
    for i in range(len(top_tabs)):
        top_tab_rects.append(pygame.Rect(tab_x + i * (tab_w + gap), tab_y, tab_w, TAB_H))

    # News list area
    LIST_X = MAIN_X + Sx(10)
    LIST_Y = tab_y + TAB_H + Sy(10)
    LIST_W = max(Sx(320), int(MAIN_W * 0.22))
    LIST_H = max(Sy(130), Sy(160))

    list_header = pygame.Rect(LIST_X, LIST_Y, LIST_W, Sy(26))
    list_panel = pygame.Rect(LIST_X, LIST_Y + Sy(26), LIST_W, LIST_H - Sy(26))
    scrollbar_rect = pygame.Rect(LIST_X + LIST_W - Sx(14), list_panel.top, Sx(14), list_panel.height)

    read_next_rect = pygame.Rect(LIST_X + LIST_W + Sx(12), LIST_Y + Sy(46), Sx(140), Sy(30))

    filter_label_rect = pygame.Rect(LIST_X + LIST_W - Sx(150), LIST_Y + LIST_H + Sy(8), Sx(60), Sy(22))
    filter_input_rect = pygame.Rect(LIST_X + LIST_W - Sx(90), LIST_Y + LIST_H + Sy(8), Sx(110), Sy(22))

    # Bottom tabs
    BOTTOM_TABS_H = max(Sy(34), Sy(42))
    BOTTOM_TABS_Y = HEIGHT - Sy(95)

    bt_x = MAIN_X + Sx(10)
    bt_y = BOTTOM_TABS_Y
    bt_total_w = MAIN_W - Sx(20)
    bt_w = (bt_total_w - gap * (len(bottom_tabs) - 1)) // len(bottom_tabs)
    bottom_tab_rects = []
    for i in range(len(bottom_tabs)):
        bottom_tab_rects.append(pygame.Rect(bt_x + i * (bt_w + gap), bt_y, bt_w, BOTTOM_TABS_H))

    # Content area
    CONTENT_X = MAIN_X + Sx(10)
    CONTENT_Y = LIST_Y + LIST_H + Sy(18)
    CONTENT_W = MAIN_W - Sx(20)
    CONTENT_H = HEIGHT - CONTENT_Y - Sy(120)  # reserva para tabs bottom + navegação
    content_rect = pygame.Rect(CONTENT_X, CONTENT_Y, CONTENT_W, max(Sy(240), CONTENT_H))

    # Bottom nav buttons
    NAV_Y = HEIGHT - Sy(55)
    NAV_H = Sy(40)
    btn_prev_rect = pygame.Rect(MAIN_X + Sx(10), NAV_Y, (MAIN_W - Sx(20)) // 2 - Sx(3), NAV_H)
    btn_next_rect = pygame.Rect(btn_prev_rect.right + Sx(6), NAV_Y, (MAIN_W - Sx(20)) // 2 - Sx(3), NAV_H)

    # ------------- helpers -------------
    def clamp_scroll():
        nonlocal news_scroll
        max_scroll = max(0, len(news) - visible_rows)
        news_scroll = max(0, min(news_scroll, max_scroll))

    def ensure_selected_visible():
        nonlocal news_scroll
        if selected_news < news_scroll:
            news_scroll = selected_news
        elif selected_news >= news_scroll + visible_rows:
            news_scroll = selected_news - visible_rows + 1
        clamp_scroll()

    def rebuild_filtered_news(reset_selection=True):
        nonlocal news, selected_news, news_scroll
        news = filter_news(master_news, current_filter)
        if not news:
            news = [{
                "date": "—",
                "category": DEFAULT_CATEGORY,
                "title": "Sem notícias",
                "description": "Nenhuma notícia nesta categoria."
            }]
        if reset_selection:
            selected_news = 0
            news_scroll = 0
        else:
            selected_news = max(0, min(selected_news, len(news) - 1))
            clamp_scroll()

    def reload_json():
        nonlocal coach_name, sidebar_date, master_news, selected_news, news_scroll
        try:
            d = load_data(json_path)
            coach_name = d["coach_name"]
            sidebar_date = d["sidebar_date"]
            master_news = d["news"] or [{
                "date": "—",
                "category": DEFAULT_CATEGORY,
                "title": "Sem notícias",
                "description": "O JSON não contém notícias."
            }]
            # Keep filter, rebuild list
            rebuild_filtered_news(reset_selection=True)
            selected_news = max(0, min(selected_news, len(news) - 1))
            news_scroll = max(0, min(news_scroll, max(0, len(news) - visible_rows)))
        except Exception as e:
            print("Erro ao recarregar JSON:", e)

    def on_wheel(mouse_pos, y_delta):
        nonlocal news_scroll
        if in_rect(mouse_pos, list_panel):
            news_scroll -= y_delta
            clamp_scroll()

    def update_hover(mouse_pos):
        nonlocal hover_top, hover_bottom, hover_sb, hover_news, hover_read_next
        hover_top = None
        hover_bottom = None
        hover_sb = None
        hover_news = None
        hover_read_next = in_rect(mouse_pos, read_next_rect)

        for i, r in enumerate(top_tab_rects):
            if in_rect(mouse_pos, r):
                hover_top = i
                break

        for i, r in enumerate(bottom_tab_rects):
            if in_rect(mouse_pos, r):
                hover_bottom = i
                break

        for i, r in enumerate(sb_btn_rects):
            if in_rect(mouse_pos, r):
                hover_sb = i
                break

        if in_rect(mouse_pos, list_panel):
            row_h = Sy(24)
            row_gap = Sy(2)
            for i in range(visible_rows):
                idx = news_scroll + i
                if idx >= len(news):
                    break
                row_rect = pygame.Rect(
                    list_panel.left + Sx(6),
                    list_panel.top + Sy(6) + i * (row_h + row_gap),
                    list_panel.width - Sx(28),
                    row_h
                )
                if in_rect(mouse_pos, row_rect):
                    hover_news = idx
                    break

    def click(mouse_pos):
        nonlocal selected_news, current_filter

        # Top tabs => set filter
        for i, r in enumerate(top_tab_rects):
            if in_rect(mouse_pos, r):
                current_filter = top_tabs[i]  # includes "Todas"
                rebuild_filtered_news(reset_selection=True)
                return

        # Bottom tabs => set filter
        for i, r in enumerate(bottom_tab_rects):
            if in_rect(mouse_pos, r):
                current_filter = bottom_tabs[i]
                rebuild_filtered_news(reset_selection=True)
                return

        # news rows
        if hover_news is not None:
            selected_news = hover_news
            ensure_selected_visible()
            return

        # next
        if in_rect(mouse_pos, read_next_rect):
            selected_news = (selected_news + 1) % len(news)
            ensure_selected_visible()
            return

    def is_top_active(label: str) -> bool:
        return current_filter == label

    def is_bottom_active(label: str) -> bool:
        return current_filter == label

    def render():
        # Background
        if BG:
            screen.blit(BG, (0, 0))
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 90))
            screen.blit(overlay, (0, 0))
        else:
            screen.fill((10, 10, 10))

        # Sidebar
        pygame.draw.rect(screen, C_BLUE_DARK, pygame.Rect(0, 0, SIDEBAR_W, HEIGHT))
        pygame.draw.rect(screen, C_BLUE_BRIGHT, pygame.Rect(0, 0, SIDEBAR_W, HEIGHT), max(1, Sx(2)))

        beveled_panel(screen, DATE_RECT, (12, 30, 130), C_YELLOW, C_BLACK, radius=max(2, Sx(4)))

        # Date text (from JSON)
        lines = sidebar_date.split("\n")
        y = DATE_RECT.top + Sy(8)
        for ln in lines:
            img = FONT_14.render(ln, True, C_YELLOW)
            screen.blit(img, (DATE_RECT.left + Sx(48), y))
            y += Sy(18)

        draw_arrow(screen, arrow_left, "left")
        draw_arrow(screen, arrow_right, "right")

        for i, r in enumerate(sb_btn_rects):
            draw_sidebar_button(
                screen,
                r,
                SB_MENU[i],
                hovered=(hover_sb == i),
                selected=(i == 6),
            )

        # Main frame
        pygame.draw.rect(screen, C_BLACK, main_frame)
        pygame.draw.rect(screen, (255, 0, 0), main_frame, max(1, Sx(2)))

        # Title
        beveled_panel(screen, title_rect, C_RED, (255, 80, 80), C_BLACK, radius=max(2, Sx(3)))
        draw_text(screen, f"Notícias para {coach_name}", FONT_28, C_WHITE, title_rect, align="center")

        # Top tabs (active driven by current_filter)
        for i, r in enumerate(top_tab_rects):
            label = top_tabs[i]
            button(
                screen, r, label,
                active=is_top_active(label),
                hovered=(hover_top == i)
            )

        # Selected title
        sel_title = news[selected_news]["title"]
        beveled_panel(screen, list_header, C_RED_DARK, (255, 80, 80), C_BLACK, radius=max(2, Sx(2)))
        draw_text(screen, sel_title, FONT_14, C_WHITE, list_header, align="midleft")

        # List panel
        panel_surf = pygame.Surface((list_panel.width, list_panel.height), pygame.SRCALPHA)
        panel_surf.fill(C_PANEL)
        screen.blit(panel_surf, list_panel.topleft)
        pygame.draw.rect(screen, (255, 80, 80), list_panel, max(1, Sx(1)))

        # Rows
        row_h = Sy(24)
        row_gap = Sy(2)
        chip_w = Sx(110)

        for i in range(visible_rows):
            idx = news_scroll + i
            if idx >= len(news):
                break
            item = news[idx]
            date = item["date"]
            title = item["title"]

            row_rect = pygame.Rect(
                list_panel.left + Sx(6),
                list_panel.top + Sy(6) + i * (row_h + row_gap),
                list_panel.width - Sx(28),
                row_h
            )

            is_sel = (idx == selected_news)
            is_hov = (hover_news == idx)

            bgc = (25, 30, 90) if not is_sel else (140, 0, 0)
            if is_hov and not is_sel:
                bgc = (35, 45, 130)

            pygame.draw.rect(screen, bgc, row_rect)
            pygame.draw.rect(screen, (255, 210, 45) if is_sel else (80, 120, 255), row_rect, max(1, Sx(1)))

            chip = pygame.Rect(row_rect.left, row_rect.top, chip_w, row_rect.height)
            pygame.draw.rect(screen, (5, 15, 65), chip)
            pygame.draw.rect(screen, (80, 120, 255), chip, max(1, Sx(1)))
            draw_text(screen, date, FONT_12, C_WHITE, chip, align="center")

            title_rect2 = pygame.Rect(
                chip.right + Sx(8),
                row_rect.top,
                row_rect.width - chip.width - Sx(8),
                row_rect.height
            )
            draw_text(screen, title, FONT_12, C_WHITE, title_rect2, align="midleft")

        # Scrollbar
        pygame.draw.rect(screen, (40, 40, 40), scrollbar_rect)
        pygame.draw.rect(screen, (120, 120, 120), scrollbar_rect, max(1, Sx(1)))

        thumb_h = max(Sy(24), int(scrollbar_rect.height * (visible_rows / max(visible_rows, len(news)))))
        max_scroll = max(0, len(news) - visible_rows)
        t = 0 if max_scroll == 0 else news_scroll / max_scroll
        thumb_y = scrollbar_rect.top + int((scrollbar_rect.height - thumb_h) * t)
        thumb = pygame.Rect(scrollbar_rect.left + Sx(2), thumb_y, scrollbar_rect.width - Sx(4), thumb_h)
        pygame.draw.rect(screen, (180, 180, 180), thumb)
        pygame.draw.rect(screen, C_BLACK, thumb, max(1, Sx(1)))

        # Read next button
        pygame.draw.rect(screen, (200, 200, 200) if hover_read_next else (180, 180, 180), read_next_rect)
        pygame.draw.rect(screen, C_BLACK, read_next_rect, max(1, Sx(2)))
        draw_text(screen, "Ler Próxima", FONT_14, (20, 20, 20), read_next_rect, align="center")

        # Filter widgets (visual only, still)
        draw_text(screen, "Filtro :", FONT_14, C_WHITE, filter_label_rect, align="center")
        pygame.draw.rect(screen, (40, 40, 40), filter_input_rect)
        pygame.draw.rect(screen, (180, 180, 180), filter_input_rect, max(1, Sx(1)))

        # Content area
        content_surf = pygame.Surface((content_rect.width, content_rect.height), pygame.SRCALPHA)
        content_surf.fill(C_PANEL_2)
        screen.blit(content_surf, content_rect.topleft)
        pygame.draw.rect(screen, C_WHITE, content_rect, max(1, Sx(1)))

        # Content title
        title_img = FONT_22.render(sel_title, True, C_YELLOW)
        screen.blit(title_img, (content_rect.left + Sx(16), content_rect.top + Sy(18)))

        # Description
        desc = news[selected_news]["description"]
        body_x = content_rect.left + Sx(16)
        body_y = content_rect.top + Sy(62)
        body_w = content_rect.width - Sx(32)

        paragraphs = [p.strip() for p in desc.split("\n\n") if p.strip()]
        text_font = get_font(Sf(20), bold=True)
        line_h = Sy(26)
        for p in paragraphs:
            body_y = draw_text_wrapped(screen, p, text_font, C_WHITE, body_x, body_y, body_w, line_h)
            body_y += Sy(12)

        # Bottom tabs (active driven by current_filter)
        for i, r in enumerate(bottom_tab_rects):
            label = bottom_tabs[i]
            button(
                screen, r, label,
                active=is_bottom_active(label),
                hovered=(hover_bottom == i),
                small=True
            )

        # Nav buttons
        pygame.draw.rect(screen, (170, 170, 170), btn_prev_rect)
        pygame.draw.rect(screen, C_BLACK, btn_prev_rect, max(1, Sx(2)))
        draw_text(screen, "Atrás", FONT_22, (240, 240, 240), btn_prev_rect, align="center")

        pygame.draw.rect(screen, (150, 150, 150), btn_next_rect)
        pygame.draw.rect(screen, C_BLACK, btn_next_rect, max(1, Sx(2)))
        draw_text(screen, "Seguinte", FONT_22, (240, 240, 240), btn_next_rect, align="center")

    # ------------- Loop -------------
    running = True
    while running:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    reload_json()
                elif event.key == pygame.K_F5:
                    BG = load_bg()

            elif event.type == pygame.MOUSEMOTION:
                update_hover(event.pos)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    click(event.pos)
                elif event.button == 4:
                    on_wheel(event.pos, 1)
                elif event.button == 5:
                    on_wheel(event.pos, -1)

            elif event.type == pygame.MOUSEWHEEL:
                on_wheel(pygame.mouse.get_pos(), event.y)

        render()
        pygame.display.flip()

    pygame.quit()

# ---------- Entry ----------
if __name__ == "__main__":
    path = DEFAULT_JSON_PATH
    if len(sys.argv) >= 2:
        path = sys.argv[1]
    run(path)