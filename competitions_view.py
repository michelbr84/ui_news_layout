import json
import os
import pygame

# -----------------------------
# Local Colors (Copy from main)
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
C_PANEL = (18, 18, 18, 180)
C_PANEL_2 = (15, 15, 15, 210)

class CompetitionsView:
    def __init__(self, json_path, Sx, Sy, Sf, get_font):
        self.json_path = json_path
        self.Sx = Sx
        self.Sy = Sy
        self.Sf = Sf
        self.get_font = get_font
        
        self.data = self.load_data()
        self.current_round = self.find_current_round()
        self.total_rounds = len(self.data.get("schedule", []))
        
        # UI State
        self.hover_prev = False
        self.hover_next = False
        
        # Cache rects
        self.prev_rect = None
        self.next_rect = None

    def load_data(self):
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar campeonato: {e}")
            return {"schedule": []}

    def find_current_round(self):
        # Tenta achar a primeira rodada com data futura ou hoje
        today = "2026-03-29" # Mock date or use datetime
        # Na verdade, vamos começar na rodada 1 ou na próxima data válida
        # Simplificação: Começa na 1
        return 1

    def handle_input(self, event):
        if event.type == pygame.MOUSEMOTION:
            mouse_pos = event.pos
            self.hover_prev = self.prev_rect and self.prev_rect.collidepoint(mouse_pos)
            self.hover_next = self.next_rect and self.next_rect.collidepoint(mouse_pos)
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mouse_pos = event.pos
                if self.hover_prev:
                    self.change_round(-1)
                elif self.hover_next:
                    self.change_round(1)

    def change_round(self, delta):
        new_r = self.current_round + delta
        if 1 <= new_r <= self.total_rounds:
            self.current_round = new_r

    def get_round_data(self, round_num):
        schedule = self.data.get("schedule", [])
        for r in schedule:
            if r.get("round") == round_num:
                return r
        return None

    def render(self, screen, main_frame_rect):
        Sx, Sy, Sf = self.Sx, self.Sy, self.Sf
        FONT_TITLE = self.get_font(Sf(28), bold=True)
        FONT_SUB = self.get_font(Sf(22), bold=True)
        FONT_TEXT = self.get_font(Sf(16))
        FONT_SMALL = self.get_font(Sf(14))

        # Title Area inside main_frame
        # Same padding as news view
        title_rect = pygame.Rect(main_frame_rect.left + Sx(10), main_frame_rect.top + Sy(10), 
                               main_frame_rect.width - Sx(20), Sy(46))
        
        # Background for title
        # Simulate beveled_panel from main
        pygame.draw.rect(screen, C_RED, title_rect, border_radius=max(2, Sx(3)))
        pygame.draw.rect(screen, (255, 80, 80), title_rect, max(1, Sx(2)), border_radius=max(2, Sx(3)))
        pygame.draw.rect(screen, C_BLACK, title_rect.inflate(-Sx(4), -Sy(4)), max(1, Sx(1)), border_radius=max(2, Sx(3)))
        
        comp_name = self.data.get("competition", {}).get("name", "Competição")
        img = FONT_TITLE.render(comp_name, True, C_WHITE)
        screen.blit(img, img.get_rect(center=title_rect.center))

        # Content Area
        content_rect = pygame.Rect(
            main_frame_rect.left + Sx(10), 
            title_rect.bottom + Sy(10),
            main_frame_rect.width - Sx(20),
            main_frame_rect.height - Sy(70)
        )
        
        # Panel BG
        s = pygame.Surface(content_rect.size, pygame.SRCALPHA)
        s.fill(C_PANEL_2)
        screen.blit(s, content_rect.topleft)
        pygame.draw.rect(screen, C_WHITE, content_rect, max(1, Sx(1)))

        # Round Navigation
        nav_h = Sy(40)
        nav_y = content_rect.top + Sy(10)
        
        center_x = content_rect.centerx
        btn_w = Sx(40)
        
        # Prev (<)
        self.prev_rect = pygame.Rect(center_x - Sx(100) - btn_w, nav_y, btn_w, nav_h)
        # Next (>)
        self.next_rect = pygame.Rect(center_x + Sx(100), nav_y, btn_w, nav_h)
        
        # Draw buttons
        for rect, hover, sym in [(self.prev_rect, self.hover_prev, "<"), (self.next_rect, self.hover_next, ">")]:
            col = (200, 200, 200) if hover else (150, 150, 150)
            pygame.draw.rect(screen, col, rect, border_radius=Sx(4))
            pygame.draw.rect(screen, C_BLACK, rect, max(1, Sx(1)), border_radius=Sx(4))
            txt = FONT_SUB.render(sym, True, C_BLACK)
            screen.blit(txt, txt.get_rect(center=rect.center))

        # Round Text
        r_data = self.get_round_data(self.current_round)
        r_date = r_data.get("date", "---") if r_data else "---"
        
        lbl = FONT_SUB.render(f"Rodada {self.current_round}", True, C_YELLOW)
        screen.blit(lbl, lbl.get_rect(center=(center_x, nav_y + nav_h//2 - Sy(8))))
        
        lbl_date = FONT_SMALL.render(r_date, True, C_GRAY)
        screen.blit(lbl_date, lbl_date.get_rect(center=(center_x, nav_y + nav_h//2 + Sy(12))))

        # Matches List
        if not r_data:
            return

        matches = r_data.get("matches", [])
        list_y = nav_y + nav_h + Sy(20)
        row_h = Sy(30)
        
        for m in matches:
            home = m.get("home", "?")
            away = m.get("away", "?")
            
            # Simple row layout:  Home [ vs ] Away
            # Home right aligned, Away left aligned
            
            mid = content_rect.centerx
            gap = Sx(20)
            
            txt_home = FONT_TEXT.render(home, True, C_WHITE)
            txt_away = FONT_TEXT.render(away, True, C_WHITE)
            txt_vs = FONT_SMALL.render("vs", True, C_GRAY)
            
            screen.blit(txt_home, (mid - gap - txt_home.get_width(), list_y))
            screen.blit(txt_vs, (mid - txt_vs.get_width()//2, list_y + Sy(2)))
            screen.blit(txt_away, (mid + gap, list_y))
            
            # Decor line
            line_y = list_y + row_h - Sy(5)
            pygame.draw.line(screen, (50, 50, 50), (content_rect.left + Sx(20), line_y), (content_rect.right - Sx(20), line_y))
            
            list_y += row_h

