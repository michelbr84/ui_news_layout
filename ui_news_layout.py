import json
import os
import sys
import pygame
import re
import urllib.request
import urllib.error
from datetime import datetime
from competitions_view import CompetitionsView

pygame.init()
pygame.display.set_caption("Noticias (Pygame Mock)")

# -----------------------------
# Remote JSON + Webhook
# -----------------------------
JSON_URL = "https://raw.githubusercontent.com/michelbr84/ui_news_layout/refs/heads/main/news_data.json"
WEBHOOK_URL = "https://michelbr84.app.n8n.cloud/webhook/ui_news_layout"
CACHE_PATH = "news_cache.json"  # cache local (fallback se falhar internet)

HTTP_TIMEOUT_SEC = 6

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
TOP_TABS = ["Todas", "Mensagens", "Competições", "Lesões e Suspensões"]
BOTTOM_TABS = ["Contratos e Imprensa", "Transferências", "Empregos", "Registos"]
ALL_CATEGORIES = TOP_TABS[1:] + BOTTOM_TABS  # sem "Todas"

# -----------------------------
# DEFAULT JSON (fallback)
# -----------------------------
DEFAULT_JSON = {
    "coach_name": "Michel Duek",
    "sidebar_date": "Quinta-Feira\n1.1.26 TAR",
    "news": [
        {
            "date": "Qua 31 Dez NTE",
            "category": "Mensagens",
            "title": "Feliz Ano Novo",
            "description": "A equipe do jogo PyManager te deseja um excelente ano novo, que você tenha muitas vitórias."
        },
        {
            "date": "Qua 31 Dez TAR",
            "category": "Mensagens",
            "title": "Comece o ano novo com o pé direito!",
            "description": "Texto completo da notícia aqui."
        }
    ]
}

# -----------------------------
# Utils HTTP (no requests)
# -----------------------------
def http_get_json(url: str, timeout: int = HTTP_TIMEOUT_SEC) -> dict:
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "User-Agent": "ui_news_layout/1.0",
            "Accept": "application/json",
            "Cache-Control": "no-cache",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    # tenta utf-8, senão fallback
    try:
        txt = raw.decode("utf-8")
    except Exception:
        txt = raw.decode("latin-1", errors="replace")
    return json.loads(txt)

def http_post_json(url: str, payload: dict, timeout: int = HTTP_TIMEOUT_SEC) -> tuple[int, str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "User-Agent": "ui_news_layout/1.0",
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json,text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", 200)
        raw = resp.read()
    try:
        txt = raw.decode("utf-8")
    except Exception:
        txt = raw.decode("latin-1", errors="replace")
    return status, txt

def save_cache(data: dict) -> None:
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def load_cache() -> dict | None:
    if not os.path.exists(CACHE_PATH):
        return None
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

# -----------------------------
# Parsing/sorting helpers
# -----------------------------
def _norm_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())

def parse_date_key(date_str: str):
    """
    Converte strings do tipo:
      - "Qui 13 Jan NTE"
      - "Qua 31 Dez TAR"
      - "25.9.04 TAR"
    em uma chave ordenável (year, month, day, period_rank).
    Se falhar, retorna None.
    """
    s = _norm_spaces(str(date_str))

    period_rank = {
        "MAD": 0, "MAN": 0, "MNH": 0, "AM": 0,
        "TAR": 1, "PM": 1,
        "NTE": 2, "NOI": 2, "NIGHT": 2
    }

    months = {
        # PT
        "JAN": 1, "FEV": 2, "MAR": 3, "ABR": 4, "MAI": 5, "JUN": 6,
        "JUL": 7, "AGO": 8, "SET": 9, "OUT": 10, "NOV": 11, "DEZ": 12,
        # EN
        "FEB": 2, "APR": 4, "MAY": 5, "AUG": 8, "SEP": 9, "OCT": 10, "DEC": 12
    }

    # formato numérico: d.m.yy + período
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{2,4})\s*([A-Za-z]{2,5})?", s, re.IGNORECASE)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year_raw = m.group(3)
        year = int(year_raw)
        if year < 100:
            year = 2000 + year if year <= 79 else 1900 + year
        per = (m.group(4) or "").upper()
        pr = period_rank.get(per, -1)
        return (year, month, day, pr)

    tokens = s.split(" ")
    if len(tokens) >= 3:
        def try_parse_at(idx_day, idx_month, idx_period):
            try:
                day = int(re.sub(r"\D", "", tokens[idx_day]))
                mon = tokens[idx_month].upper()[:3]
                month = months.get(mon)
                if not month:
                    return None
                per = tokens[idx_period].upper() if idx_period < len(tokens) else ""
                pr = period_rank.get(per, -1)
                # sem ano -> tenta inferir pelo "agora"
                year = datetime.now().year
                return (year, month, day, pr)
            except Exception:
                return None

        key = try_parse_at(1, 2, 3) if len(tokens) >= 4 else None
        if key:
            return key
        key = try_parse_at(0, 1, 2) if len(tokens) >= 3 else None
        if key:
            return key

    return None

def normalize_data(data: dict) -> dict:
    if not isinstance(data, dict):
        data = {}

    coach = data.get("coach_name")
    if not isinstance(coach, str) or not coach.strip():
        data["coach_name"] = DEFAULT_JSON["coach_name"]

    sbd = data.get("sidebar_date")
    if not isinstance(sbd, str) or not sbd.strip():
        data["sidebar_date"] = DEFAULT_JSON["sidebar_date"]

    news = data.get("news")
    if not isinstance(news, list):
        news = []

    normalized = []
    for item in news:
        if not isinstance(item, dict):
            continue
        date = str(item.get("date", "")).strip() or "—" if "date" in item else str(item.get("date", "")).strip()
        date = str(item.get("date", "")).strip() or "—"
        title = str(item.get("title", "")).strip()
        desc = str(item.get("description", "")).strip() or "—"
        cat = str(item.get("category", "")).strip()

        if not title:
            continue

        if cat not in ALL_CATEGORIES:
            cat = "Mensagens"

        sort_key = parse_date_key(date)

        normalized.append({
            "date": date,
            "title": title,
            "description": desc,
            "category": cat,
            "_sort_key": sort_key
        })

    data["news"] = normalized
    return data

def fetch_data_remote_or_cache() -> dict:
    # 1) tenta remoto
    try:
        d = http_get_json(JSON_URL)
        d = normalize_data(d)
        save_cache(d)
        return d
    except Exception as e:
        print("[JSON] Falha remoto:", e)

    # 2) tenta cache
    cached = load_cache()
    if cached is not None:
        return normalize_data(cached)

    # 3) fallback default
    return normalize_data(DEFAULT_JSON)

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

def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, v))

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

def draw_text_wrapped(surface, text, font, color, x, y, max_width, line_height, clip_bottom=None):
    words = text.split()
    line = ""
    cur_y = y
    for w in words:
        test = (line + " " + w).strip()
        if font.size(test)[0] <= max_width:
            line = test
        else:
            if line:
                if clip_bottom is not None and cur_y + line_height > clip_bottom:
                    return cur_y
                surface.blit(font.render(line, True, color), (x, cur_y))
                cur_y += line_height
            line = w
    if line:
        if clip_bottom is not None and cur_y + line_height > clip_bottom:
            return cur_y
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

def fit_font_for_multiline(lines, max_w, max_h, start_px, bold=False, min_px=10):
    px = start_px
    while px >= min_px:
        f = get_font(px, bold=bold)
        line_h = f.get_linesize()
        total_h = line_h * len(lines)
        widest = 0
        for ln in lines:
            widest = max(widest, f.size(ln)[0])
        if widest <= max_w and total_h <= max_h:
            return f
        px -= 1
    return get_font(min_px, bold=bold)

def draw_sidebar_button(surface, rect, label, *, hovered=False, selected=False):
    base = C_BLUE if (hovered or selected) else C_BLUE_DARK
    pygame.draw.rect(surface, base, rect)
    pygame.draw.rect(surface, C_BLUE_BRIGHT, rect, max(1, Sx(1)))
    color = C_YELLOW if selected else C_WHITE

    lines = str(label).split("\n")
    pad_x = Sx(10)
    pad_y = Sy(6)
    max_w = rect.width - pad_x * 2
    max_h = rect.height - pad_y * 2
    f = fit_font_for_multiline(lines, max_w, max_h, start_px=Sf(16), bold=False, min_px=Sf(10))

    line_h = f.get_linesize()
    total_h = line_h * len(lines)
    y = rect.centery - total_h // 2

    for ln in lines:
        img = f.render(ln, True, color)
        r = img.get_rect(center=(rect.centerx, y + line_h // 2))
        surface.blit(img, r)
        y += line_h

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
# Filtering + sorting
# -----------------------------
def build_view(news_all, active_category, filter_text):
    ft = (filter_text or "").strip().lower()

    if active_category == "Todas":
        items = list(news_all)
    else:
        items = [n for n in news_all if n.get("category") == active_category]

    if ft:
        items = [n for n in items if ft in n.get("title", "").lower() or ft in n.get("description", "").lower()]

    # ordenação por data (mais recente primeiro) quando parseia
    parse_ok = [n for n in items if n.get("_sort_key") is not None]
    parse_no = [n for n in items if n.get("_sort_key") is None]
    parse_ok.sort(key=lambda n: n["_sort_key"], reverse=True)
    return parse_ok + parse_no

# -----------------------------
# Main app
# -----------------------------
def run():
    clock = pygame.time.Clock()
    BG = load_bg()

    data = fetch_data_remote_or_cache()
    coach_name = data["coach_name"]
    sidebar_date = data["sidebar_date"]
    news_all = data["news"] or [{
        "date": "—", "category": "Mensagens", "title": "Sem notícias", "description": "O JSON não contém notícias.", "_sort_key": None
    }]

    # UI State
    # UI State
    current_mode = "NEWS"  # "NEWS" | "COMPETITIONS"
    comp_view = CompetitionsView("campeonato.json", Sx, Sy, Sf, get_font)

    active_category = "Todas"
    filter_text = ""
    filter_active = False

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
    gap = Sx(10)
    tab_total_w = MAIN_W - Sx(20)
    tab_w = (tab_total_w - gap * (len(TOP_TABS) - 1)) // len(TOP_TABS)
    top_tab_rects = []
    for i in range(len(TOP_TABS)):
        top_tab_rects.append(pygame.Rect(tab_x + i * (tab_w + gap), tab_y, tab_w, TAB_H))

    # News list area
    LIST_X = MAIN_X + Sx(10)
    LIST_Y = tab_y + TAB_H + Sy(10)
    LIST_W = max(Sx(360), int(MAIN_W * 0.30))
    LIST_H = max(Sy(150), Sy(170))

    LIST_HEADER_H = Sy(30)
    list_header = pygame.Rect(LIST_X, LIST_Y, LIST_W, LIST_HEADER_H)
    list_panel = pygame.Rect(LIST_X, LIST_Y + LIST_HEADER_H, LIST_W, LIST_H - LIST_HEADER_H)
    scrollbar_rect = pygame.Rect(LIST_X + LIST_W - Sx(14), list_panel.top, Sx(14), list_panel.height)

    # --- Filtro (top-right) + Botão (abaixo) ---
    FILTER_H = clamp(Sy(20), 18, 26)

    filter_label_w = Sx(70)

    # "menos horizontal" para ler "Filtro:" com folga
    filter_input_w = clamp(int(MAIN_W * 0.30), Sx(210), Sx(320))

    filter_x_right = MAIN_X + MAIN_W - Sx(20)

    filter_input_rect = pygame.Rect(
        filter_x_right - filter_input_w,
        LIST_Y - Sy(6),
        filter_input_w,
        FILTER_H
    )
    filter_label_rect = pygame.Rect(
        filter_input_rect.left - Sx(12) - filter_label_w,
        filter_input_rect.top,
        filter_label_w,
        FILTER_H
    )

    # Botão "Ler Próxima" mais baixo e um pouco mais "gordinho"
    READ_W = clamp(int(filter_input_rect.width * 0.72), Sx(260), Sx(420))
    READ_H = clamp(Sy(34), 30, 48)
    read_next_rect = pygame.Rect(
        filter_x_right - READ_W,
        filter_input_rect.bottom + Sy(30),  # desce mais
        READ_W,
        READ_H
    )

    # Bottom tabs / nav
    BOTTOM_TABS_H = max(Sy(34), Sy(42))
    NAV_Y = HEIGHT - Sy(55)
    NAV_H = Sy(40)
    BOTTOM_TABS_Y = NAV_Y - Sy(10) - BOTTOM_TABS_H

    bt_x = MAIN_X + Sx(10)
    bt_y = BOTTOM_TABS_Y
    bt_total_w = MAIN_W - Sx(20)
    bt_w = (bt_total_w - gap * (len(BOTTOM_TABS) - 1)) // len(BOTTOM_TABS)
    bottom_tab_rects = []
    for i in range(len(BOTTOM_TABS)):
        bottom_tab_rects.append(pygame.Rect(bt_x + i * (bt_w + gap), bt_y, bt_w, BOTTOM_TABS_H))

    # Content area
    CONTENT_X = MAIN_X + Sx(10)
    CONTENT_Y = list_panel.bottom + Sy(12)
    CONTENT_W = MAIN_W - Sx(20)
    CONTENT_BOTTOM_LIMIT = BOTTOM_TABS_Y - Sy(10)
    CONTENT_H = max(Sy(240), CONTENT_BOTTOM_LIMIT - CONTENT_Y)
    content_rect = pygame.Rect(CONTENT_X, CONTENT_Y, CONTENT_W, CONTENT_H)

    # Nav buttons
    btn_prev_rect = pygame.Rect(MAIN_X + Sx(10), NAV_Y, (MAIN_W - Sx(20)) // 2 - Sx(6), NAV_H)
    btn_next_rect = pygame.Rect(btn_prev_rect.right + Sx(12), NAV_Y, (MAIN_W - Sx(20)) // 2 - Sx(6), NAV_H)

    # -----------------------------
    # Data refresh helpers
    # -----------------------------
    def refresh_json(reason: str = ""):
        nonlocal coach_name, sidebar_date, news_all
        try:
            d = fetch_data_remote_or_cache()
            coach_name = d["coach_name"]
            sidebar_date = d["sidebar_date"]
            news_all = d["news"] or [{
                "date": "—", "category": "Mensagens", "title": "Sem notícias", "description": "O JSON não contém notícias.", "_sort_key": None
            }]
            # atualiza texto do menu do lado (coach)
            SB_MENU[1] = coach_name
            print(f"[JSON] Atualizado ({reason}) | itens={len(news_all)}")
        except Exception as e:
            print("[JSON] Erro ao atualizar:", e)

    def post_continue_webhook():
        payload = {
            "event": "continue_game",
            "coach_name": coach_name,
            "active_category": active_category,
            "filter_text": filter_text,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
        try:
            status, txt = http_post_json(WEBHOOK_URL, payload)
            print(f"[WEBHOOK] POST status={status}")
            if txt:
                print("[WEBHOOK] response:", txt[:300])
        except Exception as e:
            print("[WEBHOOK] Falha POST:", e)

    # -----------------------------
    # UI helpers
    # -----------------------------
    def current_view():
        return build_view(news_all, active_category, filter_text)

    def clamp_scroll(view):
        nonlocal news_scroll
        max_scroll = max(0, len(view) - visible_rows)
        news_scroll = max(0, min(news_scroll, max_scroll))

    def ensure_selected_visible(view):
        nonlocal news_scroll
        if not view:
            return
        if selected_news < news_scroll:
            news_scroll = selected_news
        elif selected_news >= news_scroll + visible_rows:
            news_scroll = selected_news - visible_rows + 1
        clamp_scroll(view)

    def reset_selection(view):
        nonlocal selected_news, news_scroll
        selected_news = 0
        news_scroll = 0
        clamp_scroll(view)

    def on_wheel(mouse_pos, y_delta):
        nonlocal news_scroll
        view = current_view()
        if in_rect(mouse_pos, list_panel):
            news_scroll -= y_delta
            clamp_scroll(view)

    def category_is_active(label):
        return active_category == label

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

        view = current_view()
        if in_rect(mouse_pos, list_panel) and view:
            row_h = Sy(24)
            row_gap = Sy(2)
            for i in range(visible_rows):
                idx = news_scroll + i
                if idx >= len(view):
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
        nonlocal active_category, selected_news, filter_active, current_mode

        # sidebar clicks
        for i, r in enumerate(sb_btn_rects):
            if in_rect(mouse_pos, r):
                # "Continuar Jogo"
                if i == 0:
                    post_continue_webhook()
                    refresh_json("continuar_jogo")
                elif i == 1:
                    current_mode = "NEWS"
                elif i == 2:
                    current_mode = "COMPETITIONS"
                    # Opcional: recarregar dados se precisar
                    # comp_view.reload() 
                return

        # Apenas processa cliques da View de notícias se estiver no modo NEWS
        if current_mode == "NEWS":
            # filtro ativa/desativa
            if in_rect(mouse_pos, filter_input_rect):
                filter_active = True
            else:
                filter_active = False

            # top tabs -> category
            for i, r in enumerate(top_tab_rects):
                if in_rect(mouse_pos, r):
                    active_category = TOP_TABS[i]
                    v = current_view()
                    reset_selection(v)
                    return

            # bottom tabs -> category
            for i, r in enumerate(bottom_tab_rects):
                if in_rect(mouse_pos, r):
                    active_category = BOTTOM_TABS[i]
                    v = current_view()
                    reset_selection(v)
                    return

            # news rows
            if hover_news is not None:
                # (opcional) atualizar JSON ao clicar numa notícia
                refresh_json("selecionar_noticia")
                v = current_view()
                if v:
                    selected_news = min(hover_news, len(v) - 1)
                    ensure_selected_visible(v)
                else:
                    selected_news = 0
                    news_scroll = 0
                return

            # read next
            if in_rect(mouse_pos, read_next_rect):
                # regra pedida: sempre que clicar no botão, atualizar JSON
                refresh_json("ler_proxima")
                v = current_view()
                if not v:
                    return
                selected_news = (selected_news + 1) % len(v)
                ensure_selected_visible(v)
                return
        
        elif current_mode == "COMPETITIONS":
            comp_view.handle_input(pygame.event.Event(pygame.MOUSEBUTTONDOWN, {"pos": mouse_pos, "button": 1}))

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

        # Date text
        lines = str(sidebar_date).split("\n")
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

        if current_mode == "COMPETITIONS":
            comp_view.render(screen, main_frame)
            return

        # Title
        beveled_panel(screen, title_rect, C_RED, (255, 80, 80), C_BLACK, radius=max(2, Sx(3)))
        draw_text(screen, f"Notícias para {coach_name}", FONT_28, C_WHITE, title_rect, align="center")

        # Top tabs
        for i, r in enumerate(top_tab_rects):
            label = TOP_TABS[i]
            button(
                screen, r, label,
                active=category_is_active(label),
                hovered=(hover_top == i)
            )

        # Filter (top-right)
        # garante "Filtro :" legível
        draw_text(screen, "Filtro :", FONT_14, C_WHITE, filter_label_rect, align="center")
        pygame.draw.rect(screen, (40, 40, 40), filter_input_rect)
        pygame.draw.rect(screen, (180, 180, 180), filter_input_rect, max(1, Sx(1)))

        # texto do filtro + cursor
        ft = filter_text
        show = ft
        max_px = filter_input_rect.width - Sx(14)
        fnt = FONT_14
        while fnt.size(show + "|")[0] > max_px and len(show) > 0:
            show = show[1:]
        caret = "|" if filter_active and (pygame.time.get_ticks() // 400) % 2 == 0 else ""
        img = fnt.render(show + caret, True, C_WHITE)
        screen.blit(img, (filter_input_rect.left + Sx(8), filter_input_rect.centery - img.get_height() // 2))

        # view
        view = current_view()
        if not view:
            view = [{
                "date": "—", "category": "Mensagens", "title": "Sem notícias",
                "description": "Sem itens nesta categoria/filtro.", "_sort_key": None
            }]

        # safety selection/scroll
        nonlocal_sel = False
        if selected_news >= len(view):
            selected_news_local = 0
        else:
            selected_news_local = selected_news

        max_scroll = max(0, len(view) - visible_rows)
        if news_scroll > max_scroll:
            news_scroll_local = max_scroll
        else:
            news_scroll_local = news_scroll

        # List header
        sel_idx = min(selected_news_local, len(view) - 1)
        sel_title = view[sel_idx]["title"]

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
        chip_w = Sx(130)

        for i in range(visible_rows):
            idx = news_scroll_local + i
            if idx >= len(view):
                break
            item = view[idx]
            date = item["date"]
            title = item["title"]

            row_rect = pygame.Rect(
                list_panel.left + Sx(6),
                list_panel.top + Sy(6) + i * (row_h + row_gap),
                list_panel.width - Sx(28),
                row_h
            )

            is_sel = (idx == sel_idx)
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

            title_rect2 = pygame.Rect(chip.right + Sx(8), row_rect.top, row_rect.width - chip.width - Sx(8), row_rect.height)
            draw_text(screen, title, FONT_12, C_WHITE, title_rect2, align="midleft")

        # Scrollbar
        pygame.draw.rect(screen, (40, 40, 40), scrollbar_rect)
        pygame.draw.rect(screen, (120, 120, 120), scrollbar_rect, max(1, Sx(1)))

        thumb_h = max(Sy(24), int(scrollbar_rect.height * (visible_rows / max(visible_rows, len(view)))))
        max_scroll2 = max(0, len(view) - visible_rows)
        t = 0 if max_scroll2 == 0 else news_scroll_local / max_scroll2
        thumb_y = scrollbar_rect.top + int((scrollbar_rect.height - thumb_h) * t)
        thumb = pygame.Rect(scrollbar_rect.left + Sx(2), thumb_y, scrollbar_rect.width - Sx(4), thumb_h)
        pygame.draw.rect(screen, (180, 180, 180), thumb)
        pygame.draw.rect(screen, C_BLACK, thumb, max(1, Sx(1)))

        # Read next button
        pygame.draw.rect(screen, (200, 200, 200) if hover_read_next else (180, 180, 180), read_next_rect)
        pygame.draw.rect(screen, C_BLACK, read_next_rect, max(1, Sx(2)))
        draw_text(screen, "Ler Próxima", FONT_14, (20, 20, 20), read_next_rect, align="center")

        # Content area
        content_surf = pygame.Surface((content_rect.width, content_rect.height), pygame.SRCALPHA)
        content_surf.fill(C_PANEL_2)
        screen.blit(content_surf, content_rect.topleft)
        pygame.draw.rect(screen, C_WHITE, content_rect, max(1, Sx(1)))

        # Content title
        title_img = FONT_22.render(sel_title, True, C_YELLOW)
        screen.blit(title_img, (content_rect.left + Sx(16), content_rect.top + Sy(18)))

        # Description wrapped
        desc = view[sel_idx]["description"]
        body_x = content_rect.left + Sx(16)
        body_y = content_rect.top + Sy(72)
        body_w = content_rect.width - Sx(32)
        clip_bottom = content_rect.bottom - Sy(20)

        paragraphs = [p.strip() for p in str(desc).split("\n\n") if p.strip()]
        text_font = get_font(Sf(22), bold=True)
        line_h = Sy(28)
        for p in paragraphs:
            body_y = draw_text_wrapped(screen, p, text_font, C_WHITE, body_x, body_y, body_w, line_h, clip_bottom=clip_bottom)
            body_y += Sy(10)
            if body_y >= clip_bottom:
                break

        # Bottom tabs
        for i, r in enumerate(bottom_tab_rects):
            label = BOTTOM_TABS[i]
            button(
                screen, r, label,
                active=category_is_active(label),
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

    # initial refresh (already done by fetch_data_remote_or_cache)
    # main loop
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
                    refresh_json("tecla_r")
                    selected_news = 0
                    news_scroll = 0
                elif event.key == pygame.K_F5:
                    BG = load_bg()
                else:
                    if filter_active:
                        if event.key == pygame.K_BACKSPACE:
                            filter_text = filter_text[:-1]
                            selected_news = 0
                            news_scroll = 0
                        elif event.key == pygame.K_RETURN:
                            filter_active = False
                        else:
                            ch = event.unicode
                            if ch and ch.isprintable():
                                filter_text += ch
                                selected_news = 0
                                news_scroll = 0

            elif event.type == pygame.MOUSEMOTION:
                if current_mode == "COMPETITIONS":
                    comp_view.handle_input(event)
                else:
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

        # safety: ajusta selection/scroll ao vivo
        v = build_view(news_all, active_category, filter_text)
        if not v:
            v = [{
                "date": "—", "category": "Mensagens", "title": "Sem notícias",
                "description": "Sem itens nesta categoria/filtro.", "_sort_key": None
            }]

        if selected_news >= len(v):
            selected_news = 0
            news_scroll = 0

        max_scroll = max(0, len(v) - visible_rows)
        if news_scroll > max_scroll:
            news_scroll = max_scroll

        render()
        pygame.display.flip()

    pygame.quit()

# ---------- Entry ----------
if __name__ == "__main__":
    run()