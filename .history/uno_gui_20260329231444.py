"""
UNO Game – PyGame GUI (Bonus)
Visualises the 3-player AI game with cards, animations, and decision info.
Student ID: 24i-2528
"""

import sys
import os

# Ensure the script's directory is first on the path so uno_game.py is found
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import pygame
import random
import time
import textwrap

import importlib
_ug = importlib.import_module('uno_game')
UNOGame         = _ug.UNOGame
Card            = _ug.Card
get_valid_moves = _ug.get_valid_moves
generate_deck   = _ug.generate_deck
GameState       = _ug.GameState
evaluate        = _ug.evaluate
minimax_with_tree = _ug.minimax_with_tree
expectimax      = _ug.expectimax
expectimax_chance = _ug.expectimax_chance
print_tree      = _ug.print_tree

# ─── Colours ───────────────────────────────────────────────────────────────────

BG_COLOR        = (15, 20, 35)
TABLE_COLOR     = (18, 90, 48)     # Richer felt green
TABLE_EDGE      = (40, 30, 20)     # Wood-like edge
PANEL_COLOR     = (30, 35, 55, 230) # Slightly transparent
PANEL_BORDER    = (80, 85, 110)
TEXT_COLOR      = (240, 245, 255)
TEXT_DIM        = (150, 160, 180)
GOLD            = (255, 215, 0)
WHITE           = (255, 255, 255)
BLACK           = (0, 0, 0)

CARD_COLORS = {
    'Red':    (237, 28, 36),     # Official UNO Red
    'Blue':   (0, 114, 188),     # Official UNO Blue
    'Green':  (80, 170, 70),     # Official UNO Green
    'Yellow': (255, 204, 0),     # Official UNO Yellow
    'Back':   (20, 20, 20),      # Dark back
}
CARD_BORDER = {
    'Red':    (255, 255, 255),
    'Blue':   (255, 255, 255),
    'Green':  (255, 255, 255),
    'Yellow': (255, 255, 255),
    'Back':   (255, 255, 255),
}

PLAYER_COLORS = [
    (100, 220, 255),   # P1 – cyan highlight
    (255, 150, 80),    # P2 – orange highlight
    (200, 130, 255),   # P3 – purple highlight
]

# ─── Dimensions ────────────────────────────────────────────────────────────────

SCREEN_W, SCREEN_H = 1280, 800
CARD_W, CARD_H     = 80, 115
SMALL_W, SMALL_H   = 55, 80
FPS                = 60

# ─── Visual Helpers ────────────────────────────────────────────────────────────

def draw_shadow(surface, rect, radius=10, offset=(4, 4)):
    """Draws a soft drop shadow."""
    shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 80), shadow.get_rect(), border_radius=radius)
    surface.blit(shadow, (rect.x + offset[0], rect.y + offset[1]))

# ─── Card Rendering ────────────────────────────────────────────────────────────

def draw_card(surface, card, x, y, w=CARD_W, h=CARD_H, highlight=False, face_up=True, small=False):
    color_key = card.color if face_up else 'Back'
    fill  = CARD_COLORS.get(color_key, CARD_COLORS['Back'])
    
    rect = pygame.Rect(x, y, w, h)

    if highlight:
        glow = pygame.Surface((w + 14, h + 14), pygame.SRCALPHA)
        pygame.draw.rect(glow, (255, 220, 50, 160), glow.get_rect(), border_radius=12)
        surface.blit(glow, (x - 7, y - 7))

    # Drop shadow
    draw_shadow(surface, rect, radius=8, offset=(3,3))

    # White Border
    pygame.draw.rect(surface, WHITE, rect, border_radius=8)
    # Inner Color Fill
    inner = pygame.Rect(x + 4, y + 4, w - 8, h - 8)
    pygame.draw.rect(surface, fill, inner, border_radius=6)

    if face_up:
        # Classic UNO tilted oval inside
        oval_rect = pygame.Rect(0, 0, int(w*0.8), int(h*0.8))
        oval_rect.center = inner.center
        
        # We draw the oval on a separate transparent surface to allow rotation
        oval_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(oval_surface, WHITE, oval_surface.get_rect().inflate(-14, -14))
        pygame.draw.ellipse(oval_surface, fill, oval_surface.get_rect().inflate(-20, -20))
        
        # Tilt the oval slightly like real UNO cards
        rotated_oval = pygame.transform.rotate(oval_surface, 15)
        ro_rect = rotated_oval.get_rect(center=inner.center)
        surface.blit(rotated_oval, ro_rect.topleft)

        font_size = 20 if not small else 14
        font = pygame.font.SysFont('Arial', font_size, bold=True)
        val_str = str(card.value)
        
        # Corner text
        txt = font.render(val_str, True, WHITE)
        # Add a tiny black drop shadow for the text
        shd = font.render(val_str, True, BLACK)
        surface.blit(shd, (x + 8, y + 8))
        surface.blit(txt, (x + 7, y + 7))
        
        txt2 = pygame.transform.rotate(txt, 180)
        shd2 = pygame.transform.rotate(shd, 180)
        surface.blit(shd2, (x + w - txt2.get_width() - 6, y + h - txt2.get_height() - 6))
        surface.blit(txt2, (x + w - txt2.get_width() - 7, y + h - txt2.get_height() - 7))

        if not small:
            val_str = str(card.value) if card.value != 'Skip' else '⊘'
            big_font = pygame.font.SysFont('Impact', 45, bold=True)
            big = big_font.render(val_str, True, WHITE)
            big_shd = big_font.render(val_str, True, BLACK)
            
            # Slight rotation for the big center text
            big_rot = pygame.transform.rotate(big, 15)
            big_shd_rot = pygame.transform.rotate(big_shd, 15)
            
            bx = x + w // 2 - big_rot.get_width() // 2
            by = y + h // 2 - big_rot.get_height() // 2
            surface.blit(big_shd_rot, (bx+2, by+2))
            surface.blit(big_rot, (bx, by))
    else:
        # Card back signature design
        oval_rect = pygame.Rect(0, 0, int(w*0.8), int(h*0.8))
        oval_rect.center = inner.center
        
        oval_surface = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.ellipse(oval_surface, CARD_COLORS['Red'], oval_surface.get_rect().inflate(-14, -14))
        pygame.draw.ellipse(oval_surface, BLACK, oval_surface.get_rect().inflate(-22, -22))
        rotated_oval = pygame.transform.rotate(oval_surface, 15)
        ro_rect = rotated_oval.get_rect(center=inner.center)
        surface.blit(rotated_oval, ro_rect.topleft)
        
        # 'UNO' text on the back
        big_font = pygame.font.SysFont('Impact', 22 if small else 32, italic=True)
        big = big_font.render("UNO", True, CARD_COLORS['Yellow'])
        big_shd = big_font.render("UNO", True, CARD_COLORS['Red'])
        big_rot = pygame.transform.rotate(big, 15)
        big_shd_rot = pygame.transform.rotate(big_shd, 15)
        bx = x + w // 2 - big_rot.get_width() // 2
        by = y + h // 2 - big_rot.get_height() // 2
        surface.blit(big_shd_rot, (bx+2, by+2))
        surface.blit(big_rot, (bx, by))

def draw_card_back(surface, x, y, w=CARD_W, h=CARD_H):
    dummy = Card('Back', '?')
    draw_card(surface, dummy, x, y, w, h, face_up=False)


# ─── Panel Helper ──────────────────────────────────────────────────────────────

def draw_panel(surface, rect, title=None, border_color=PANEL_BORDER):
    # Glass effect background
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, PANEL_COLOR, s.get_rect(), border_radius=12)
    surface.blit(s, (rect.x, rect.y))
    
    # Border
    pygame.draw.rect(surface, border_color, rect, width=2, border_radius=12)
    
    # Header area
    if title:
        header_rect = pygame.Rect(rect.x, rect.y, rect.width, 35)
        pygame.draw.rect(surface, (20, 25, 40, 200), header_rect, border_top_left_radius=12, border_top_right_radius=12)
        pygame.draw.line(surface, border_color, (rect.x, rect.y + 35), (rect.right, rect.y + 35), 2)
        
        font = pygame.font.SysFont('Arial', 16, bold=True)
        t = font.render(title, True, WHITE)
        surface.blit(t, (rect.x + 15, rect.y + 8))


def draw_text(surface, text, x, y, font_size=14, color=TEXT_COLOR, bold=False):
    font = pygame.font.SysFont('Arial', font_size, bold=bold)
    t = font.render(text, True, color)
    surface.blit(t, (x, y))
    return t.get_height()


# ─── Main GUI Class ────────────────────────────────────────────────────────────

class UNOGui:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("UNO – AI Simulation (24i-2528)")
        self.clock = pygame.time.Clock()

        self.game = UNOGame(p3_mode='simulation')
        random.seed(42)
        self.game.reset()

        self.running = True
        self.auto_play = False
        self.auto_delay = 1.5   # seconds between auto turns
        self.last_auto = 0

        self.log_lines = []
        self.decision_lines = []
        self.selected_card_idx = None   # for manual P3 mode

        self.animation_queue = []
        self.anim_card = None
        self.anim_start = None
        self.anim_end = None
        self.anim_t = 0

        self.status_msg = "Press [SPACE] to play next turn | [A] toggle auto-play"
        self.highlight_cards = []   # indices in current hand to highlight
        self.last_played = None

    def run(self):
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.do_turn()
                elif event.key == pygame.K_a:
                    self.auto_play = not self.auto_play
                    self.status_msg = f"Auto-play: {'ON' if self.auto_play else 'OFF'}"
                elif event.key == pygame.K_r:
                    self.game = UNOGame(p3_mode='simulation')
                    random.seed(int(time.time()))
                    self.game.reset()
                    self.log_lines = []
                    self.decision_lines = []
                    self.last_played = None
                    self.status_msg = "Game reset! Press [SPACE] to start."

    def update(self):
        now = time.time()
        if self.auto_play and not self.game.game_over:
            if now - self.last_auto >= self.auto_delay:
                self.do_turn()
                self.last_auto = now

    def do_turn(self):
        if self.game.game_over:
            self.status_msg = f"Game Over! Winner: {self.game.PLAYER_NAMES[self.game.winner_idx]} | Press [R] to restart"
            return

        current = self.game.state.current_player
        lines = self.game.step()

        self.log_lines = lines[-20:]   # keep last 20 lines
        self.last_played = self.game.state.top_card

        # Extract decisions for display
        self.decision_lines = [l for l in lines if 'score' in l.lower() or 'decision' in l.lower() or 'expected' in l.lower()][:10]

        if self.game.game_over:
            self.status_msg = f"🏆 Winner: {self.game.PLAYER_NAMES[self.game.winner_idx]}! Press [R] to restart"
        else:
            next_p = self.game.PLAYER_NAMES[self.game.state.current_player]
            self.status_msg = f"Turn {self.game.turn_number} done | Next: {next_p} | [SPACE] next turn | [A] auto | [R] reset"

    def draw(self):
        self.screen.fill(BG_COLOR)
        self.draw_table()
        self.draw_player_areas()
        self.draw_center()
        self.draw_info_panel()
        self.draw_log_panel()
        self.draw_status_bar()
        pygame.display.flip()

    def draw_table(self):
        """Draw the green table ellipse."""
        # Draw a subtle radial gradient for the background
        center_x, center_y = SCREEN_W // 2, SCREEN_H // 2
        for radius in range(800, 0, -50):
            color = (
                max(5, BG_COLOR[0] - radius // 50),
                max(10, BG_COLOR[1] - radius // 50),
                max(20, BG_COLOR[2] - radius // 50)
            )
            pygame.draw.circle(self.screen, color, (center_x, center_y), radius)

        # Draw the main table with a thick edge and shadow
        table_rect = pygame.Rect(180, 130, 920, 540)
        draw_shadow(self.screen, table_rect, radius=260, offset=(0, 20))
        
        # Table rim
        pygame.draw.ellipse(self.screen, TABLE_EDGE, table_rect.inflate(30, 30))
        # Inner rim
        pygame.draw.ellipse(self.screen, (0, 0, 0), table_rect.inflate(6, 6))
        # Table felt
        pygame.draw.ellipse(self.screen, TABLE_COLOR, table_rect)
        
        # Draw some subtle concentric rings on the felt
        pygame.draw.ellipse(self.screen, (22, 105, 55), table_rect.inflate(-100, -100), width=3)
        pygame.draw.ellipse(self.screen, (22, 105, 55), table_rect.inflate(-200, -200), width=3)

    def draw_center(self):
        """Draw deck and top card in center."""
        cx, cy = 640, 400

        # Draw deck (pile of card backs) staggered for 3D effect
        deck_size = len(self.game.state.deck)
        for i in range(min(7, deck_size)):
            draw_card_back(self.screen, cx - 110 + i * 2, cy - CARD_H // 2 - i * 2)

        # Deck count styled like a chip
        font = pygame.font.SysFont('Arial', 14, bold=True)
        txt = font.render(f"{deck_size}", True, WHITE)
        pygame.draw.circle(self.screen, (30, 30, 30), (cx - 70, cy), 18)
        pygame.draw.circle(self.screen, WHITE, (cx - 70, cy), 18, width=2)
        self.screen.blit(txt, (cx - 70 - txt.get_width()//2, cy - txt.get_height()//2))

        # Top card
        top = self.game.state.top_card
        if top:
            draw_card(self.screen, top, cx + 20, cy - CARD_H // 2)
            draw_text(self.screen, "TOP CARD", cx + 20, cy + CARD_H // 2 + 12, 14, TEXT_DIM, bold=True)

        # Turn indicator arrow
        current = self.game.state.current_player
        col = PLAYER_COLORS[current]
        name = self.game.PLAYER_NAMES[current]
        font = pygame.font.SysFont('Arial', 20, bold=True)
        label = f"▶ {name}'s Turn ◀"
        
        # Draw label background for better visibility
        t = font.render(label, True, col)
        bg_rect = pygame.Rect(cx - t.get_width() // 2 - 15, cy - CARD_H // 2 - 60, t.get_width() + 30, 34)
        pygame.draw.rect(self.screen, (20, 20, 20, 180), bg_rect, border_radius=17)
        pygame.draw.rect(self.screen, col, bg_rect, width=2, border_radius=17)
        self.screen.blit(t, (cx - t.get_width() // 2, cy - CARD_H // 2 - 53))

    def draw_player_areas(self):
        """Draw each player's hand and label."""
        state = self.game.state
        current = state.current_player

        positions = [
            (640, 710, True, 45),     # P1 – bottom
            (80, 400, False, -30),    # P2 – left
            (640, 90, True, -55),     # P3 – top
        ]

        for idx in range(3):
            hand = state.hands[idx]
            cx, cy, horizontal, lbl_dy = positions[idx]
            col = PLAYER_COLORS[idx]
            is_current = (idx == current)
            name = self.game.PLAYER_NAMES[idx]

            # Player label
            font = pygame.font.SysFont('Arial', 15, bold=True)
            lbl = font.render(f"{name}  [{len(hand)} cards]", True, col if is_current else TEXT_DIM)
            self.screen.blit(lbl, (cx - lbl.get_width() // 2, cy + lbl_dy))

            # Cards
            n = len(hand)
            if n == 0:
                continue

            face_up = (idx == 0)   # only show P1's cards face up (for demo – change as needed)
            # Actually show all cards face up in simulation for educational value
            face_up = True

            if horizontal:
                spacing = min(SMALL_W + 4, (680) // max(n, 1))
                total_w = spacing * (n - 1) + SMALL_W
                start_x = cx - total_w // 2
                for j, card in enumerate(hand):
                    x = start_x + j * spacing
                    y = cy - SMALL_H // 2
                    valid = get_valid_moves(hand, state.top_card)
                    is_valid = card in valid
                    draw_card(self.screen, card, x, y,
                              SMALL_W, SMALL_H,
                              highlight=(is_current and is_valid),
                              face_up=face_up, small=True)
            else:
                # Vertical layout for side players
                spacing = min(SMALL_H + 4, 380 // max(n, 1))
                total_h = spacing * (n - 1) + SMALL_H
                start_y = cy - total_h // 2
                for j, card in enumerate(hand):
                    y = start_y + j * spacing
                    x = cx - SMALL_W // 2
                    valid = get_valid_moves(hand, state.top_card)
                    is_valid = card in valid
                    draw_card(self.screen, card, x, y,
                              SMALL_W, SMALL_H,
                              highlight=(is_current and is_valid),
                              face_up=face_up, small=True)

    def draw_info_panel(self):
        """Right panel showing AI decisions."""
        rect = pygame.Rect(SCREEN_W - 300, 20, 280, 460)
        draw_panel(self.screen, rect, "AI Agent Decisions", PANEL_BORDER)

        y = rect.y + 45
        for line in self.decision_lines:
            clean = line.strip()
            if not clean:
                continue
            col = GOLD if ('DECISION' in clean or '→' in clean) else TEXT_COLOR
            if 'SKIP' in clean.upper():
                col = (255, 100, 100)
            # Word wrap
            chunks = textwrap.wrap(clean, width=35)
            for chunk in chunks:
                if y > rect.bottom - 20:
                    break
                draw_text(self.screen, chunk, rect.x + 15, y, 13, col)
                y += 18

        # Score display
        if not self.game.game_over:
            y = max(y, rect.y + 340)
            y += 10
            draw_text(self.screen, "Current Evaluation Values:", rect.x + 15, y, 14, TEXT_DIM, bold=True)
            pygame.draw.line(self.screen, PANEL_BORDER, (rect.x + 15, y + 20), (rect.right - 15, y + 20), 1)
            y += 28
            state = self.game.state
            strategies = ['defensive', 'offensive', 'balanced']
            for i in range(3):
                sc = evaluate(state, i, strategies[i])
                draw_text(self.screen, f"P{i+1} : {round(sc, 1)} pts", rect.x + 15, y, 14, PLAYER_COLORS[i], bold=True)
                y += 22

    def draw_log_panel(self):
        """Bottom-right log panel."""
        rect = pygame.Rect(SCREEN_W - 300, 495, 280, 260)
        draw_panel(self.screen, rect, "Game Action Log", PANEL_BORDER)

        y = rect.y + 45
        recent = self.log_lines[-12:]
        for line in recent:
            clean = line.strip()
            if not clean:
                continue
            col = GOLD if '🏆' in clean else (TEXT_DIM if clean.startswith('Turn') else TEXT_COLOR)
            chunks = textwrap.wrap(clean, width=35)
            for chunk in chunks:
                if y > rect.bottom - 15:
                    break
                draw_text(self.screen, chunk, rect.x + 15, y, 12, col)
                y += 16

    def draw_status_bar(self):
        """Bottom status bar."""
        bar = pygame.Rect(0, SCREEN_H - 36, SCREEN_W, 36)
        pygame.draw.rect(self.screen, (10, 15, 30), bar)
        pygame.draw.line(self.screen, PANEL_BORDER, (0, SCREEN_H - 36), (SCREEN_W, SCREEN_H - 36))

        col = GOLD if self.game.game_over else TEXT_COLOR
        draw_text(self.screen, self.status_msg, 15, SCREEN_H - 26, 14, col)

        # Key hints on right
        hints = "[SPACE] next  [A] auto  [R] reset  [ESC] quit"
        draw_text(self.screen, hints, SCREEN_W - 380, SCREEN_H - 26, 13, TEXT_DIM)


# ─── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    gui = UNOGui()
    gui.run()