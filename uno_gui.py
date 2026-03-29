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
TABLE_COLOR     = (20, 100, 60)
TABLE_EDGE      = (10, 70, 40)
PANEL_COLOR     = (25, 30, 50)
PANEL_BORDER    = (60, 65, 90)
TEXT_COLOR      = (220, 225, 240)
TEXT_DIM        = (130, 135, 160)
GOLD            = (255, 200, 50)
WHITE           = (255, 255, 255)
BLACK           = (0, 0, 0)

CARD_COLORS = {
    'Red':    (220, 50, 50),
    'Blue':   (50, 100, 220),
    'Green':  (50, 180, 80),
    'Yellow': (230, 190, 30),
    'Back':   (30, 40, 80),
}
CARD_BORDER = {
    'Red':    (160, 20, 20),
    'Blue':   (20, 60, 170),
    'Green':  (20, 130, 50),
    'Yellow': (180, 140, 10),
    'Back':   (15, 20, 50),
}

PLAYER_COLORS = [
    (100, 200, 255),   # P1 – cyan
    (255, 130, 80),    # P2 – orange
    (180, 130, 255),   # P3 – purple
]

# ─── Dimensions ────────────────────────────────────────────────────────────────

SCREEN_W, SCREEN_H = 1280, 800
CARD_W, CARD_H     = 70, 100
SMALL_W, SMALL_H   = 46, 66
FPS                = 30

# ─── Card Rendering ────────────────────────────────────────────────────────────

def draw_card(surface, card, x, y, w=CARD_W, h=CARD_H, highlight=False, face_up=True, small=False):
    color_key = card.color if face_up else 'Back'
    fill  = CARD_COLORS[color_key]
    border = CARD_BORDER[color_key]
    radius = 10

    rect = pygame.Rect(x, y, w, h)

    if highlight:
        glow = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
        pygame.draw.rect(glow, (255, 255, 100, 100), glow.get_rect(), border_radius=radius + 4)
        surface.blit(glow, (x - 4, y - 4))

    pygame.draw.rect(surface, border, rect, border_radius=radius)
    inner = pygame.Rect(x + 3, y + 3, w - 6, h - 6)
    pygame.draw.rect(surface, fill, inner, border_radius=radius - 2)

    if face_up:
        font_size = 18 if not small else 13
        font = pygame.font.SysFont('Arial', font_size, bold=True)
        val_str = str(card.value)
        txt = font.render(val_str, True, WHITE)
        # top-left
        surface.blit(txt, (x + 6, y + 6))
        # bottom-right rotated
        txt2 = pygame.transform.rotate(txt, 180)
        surface.blit(txt2, (x + w - txt2.get_width() - 6, y + h - txt2.get_height() - 6))

        if not small:
            big_font = pygame.font.SysFont('Arial', 30, bold=True)
            big = big_font.render(val_str, True, (255, 255, 255, 180))
            bx = x + w // 2 - big.get_width() // 2
            by = y + h // 2 - big.get_height() // 2
            surface.blit(big, (bx, by))
    else:
        # Card back pattern
        for row in range(3):
            for col in range(3):
                px = x + 12 + col * 18
                py = y + 15 + row * 24
                pygame.draw.rect(surface, (50, 60, 100), (px, py, 12, 16), border_radius=3)


def draw_card_back(surface, x, y, w=CARD_W, h=CARD_H):
    dummy = Card('Back', '?')
    pygame.draw.rect(surface, CARD_COLORS['Back'], (x, y, w, h), border_radius=10)
    pygame.draw.rect(surface, PANEL_BORDER, (x, y, w, h), width=2, border_radius=10)
    for row in range(3):
        for col in range(3):
            px = x + 12 + col * 18
            py = y + 15 + row * 24
            pygame.draw.rect(surface, (50, 60, 110), (px, py, 12, 16), border_radius=3)


# ─── Panel Helper ──────────────────────────────────────────────────────────────

def draw_panel(surface, rect, title=None, border_color=PANEL_BORDER):
    pygame.draw.rect(surface, PANEL_COLOR, rect, border_radius=10)
    pygame.draw.rect(surface, border_color, rect, width=2, border_radius=10)
    if title:
        font = pygame.font.SysFont('Arial', 14, bold=True)
        t = font.render(title, True, TEXT_DIM)
        surface.blit(t, (rect.x + 10, rect.y + 8))


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
        table_rect = pygame.Rect(180, 150, 920, 500)
        pygame.draw.ellipse(self.screen, TABLE_EDGE, table_rect.inflate(12, 12))
        pygame.draw.ellipse(self.screen, TABLE_COLOR, table_rect)

    def draw_center(self):
        """Draw deck and top card in center."""
        cx, cy = 640, 400

        # Draw deck (pile of card backs)
        deck_size = len(self.game.state.deck)
        for i in range(min(5, deck_size)):
            draw_card_back(self.screen, cx - 90 + i * 2, cy - CARD_H // 2 - i * 2)

        # Deck count
        draw_text(self.screen, f"Deck: {deck_size}", cx - 90, cy + CARD_H // 2 + 8, 13, TEXT_DIM)

        # Top card
        top = self.game.state.top_card
        if top:
            draw_card(self.screen, top, cx + 10, cy - CARD_H // 2, highlight=True)
            draw_text(self.screen, "Top Card", cx + 10, cy + CARD_H // 2 + 8, 13, TEXT_DIM)

        # Turn indicator arrow
        current = self.game.state.current_player
        col = PLAYER_COLORS[current]
        name = self.game.PLAYER_NAMES[current]
        font = pygame.font.SysFont('Arial', 16, bold=True)
        label = f"▶ {name}'s Turn"
        t = font.render(label, True, col)
        self.screen.blit(t, (cx - t.get_width() // 2, cy - CARD_H // 2 - 35))

    def draw_player_areas(self):
        """Draw each player's hand and label."""
        state = self.game.state
        current = state.current_player

        positions = [
            # (x_center, y_center, layout_horizontal, label_offset_y)
            (640, 690, True, 25),    # P1 – bottom
            (90, 400, False, -30),   # P2 – left
            (640, 160, True, -45),   # P3 – top
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
        rect = pygame.Rect(SCREEN_W - 280, 10, 270, 450)
        draw_panel(self.screen, rect, "AI Decisions", PANEL_BORDER)

        y = rect.y + 30
        for line in self.decision_lines:
            clean = line.strip()
            if not clean:
                continue
            col = GOLD if ('DECISION' in clean or '→' in clean) else TEXT_COLOR
            if 'SKIP' in clean.upper():
                col = (255, 100, 100)
            # Word wrap
            chunks = textwrap.wrap(clean, width=33)
            for chunk in chunks:
                if y > rect.bottom - 20:
                    break
                draw_text(self.screen, chunk, rect.x + 10, y, 12, col)
                y += 16

        # Score display
        if not self.game.game_over:
            y = max(y, rect.y + 320)
            y += 10
            draw_text(self.screen, "Current Scores:", rect.x + 10, y, 13, TEXT_DIM, bold=True)
            y += 18
            state = self.game.state
            strategies = ['defensive', 'offensive', 'balanced']
            for i in range(3):
                sc = evaluate(state, i, strategies[i])
                draw_text(self.screen, f"P{i+1}: {round(sc, 1)}", rect.x + 10, y, 13, PLAYER_COLORS[i])
                y += 18

    def draw_log_panel(self):
        """Bottom-right log panel."""
        rect = pygame.Rect(SCREEN_W - 280, 470, 270, 320)
        draw_panel(self.screen, rect, "Game Log", PANEL_BORDER)

        y = rect.y + 28
        recent = self.log_lines[-14:]
        for line in recent:
            clean = line.strip()
            if not clean:
                continue
            col = GOLD if '🏆' in clean else (TEXT_DIM if clean.startswith('Turn') else TEXT_COLOR)
            chunks = textwrap.wrap(clean, width=33)
            for chunk in chunks:
                if y > rect.bottom - 15:
                    break
                draw_text(self.screen, chunk, rect.x + 8, y, 11, col)
                y += 14

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