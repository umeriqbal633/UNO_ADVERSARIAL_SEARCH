"""
UNO Game with Minimax (Defensive) and Expectimax (Offensive) AI
Student ID: 24i-2528
"""

import random
import copy
import math
from collections import Counter

# ─── Card Class ────────────────────────────────────────────────────────────────

class Card:
    COLORS = ['Red', 'Blue', 'Green', 'Yellow']
    SPECIAL = 'Skip'

    def __init__(self, color, value):
        self.color = color      # 'Red', 'Blue', 'Green', 'Yellow'
        self.value = value      # 0-9 or 'Skip'

    def is_skip(self):
        return self.value == 'Skip'

    def matches(self, top_card):
        """Rule 1: same color OR same number/value."""
        return self.color == top_card.color or self.value == top_card.value

    def __repr__(self):
        return f"{self.color} {self.value}"

    def __eq__(self, other):
        return isinstance(other, Card) and self.color == other.color and self.value == other.value

    def __hash__(self):
        return hash((self.color, self.value))


# ─── Deck Generator ────────────────────────────────────────────────────────────

def generate_deck():
    """Create a full shuffled UNO deck (0-9 + Skip per color)."""
    deck = []
    for color in Card.COLORS:
        for num in range(10):
            deck.append(Card(color, num))
            deck.append(Card(color, num))   # two of each
        deck.append(Card(color, 'Skip'))
        deck.append(Card(color, 'Skip'))    # two skips per color
    random.shuffle(deck)
    return deck


# ─── Legal Move Generator ──────────────────────────────────────────────────────

def get_valid_moves(hand, top_card):
    """Return list of valid cards from hand that can be played on top_card."""
    return [card for card in hand if card.matches(top_card)]


# ─── Game State ────────────────────────────────────────────────────────────────

class GameState:
    def __init__(self, hands, top_card, deck, current_player=0, skip_next=False):
        self.hands = hands              # list of 3 lists of Cards
        self.top_card = top_card
        self.deck = deck
        self.current_player = current_player
        self.skip_next = skip_next      # whether next player should be skipped

    def clone(self):
        return GameState(
            hands=[list(h) for h in self.hands],
            top_card=self.top_card,
            deck=list(self.deck),
            current_player=self.current_player,
            skip_next=self.skip_next
        )

    def is_terminal(self):
        return any(len(h) == 0 for h in self.hands)

    def winner(self):
        for i, h in enumerate(self.hands):
            if len(h) == 0:
                return i
        return None

    def next_player(self, player):
        return (player + 1) % 3

    def apply_move(self, player_idx, card):
        """Return new state after player plays a card (or None = draw)."""
        state = self.clone()
        if card is None:
            # Draw a card (Rule 2)
            if state.deck:
                drawn = state.deck.pop()
                state.hands[player_idx].append(drawn)
            # Turn passes
            state.current_player = state.next_player(player_idx)
            return state, None

        # Play the card
        state.hands[player_idx].remove(card)
        state.top_card = card

        if card.is_skip():
            # Rule 3: skip next player
            skipped = state.next_player(player_idx)
            state.current_player = state.next_player(skipped)
        else:
            state.current_player = state.next_player(player_idx)

        return state, card

    def deck_color_probs(self):
        """Probability distribution of colors remaining in deck."""
        if not self.deck:
            return {}
        counts = Counter(c.color for c in self.deck)
        total = len(self.deck)
        return {color: counts[color] / total for color in Card.COLORS}

    def deck_value_probs(self):
        """Probability distribution of values remaining in deck."""
        if not self.deck:
            return {}
        counts = Counter(str(c.value) for c in self.deck)
        total = len(self.deck)
        return {v: counts[v] / total for v in counts}

    def to_dict(self):
        return {
            'p1_cards': len(self.hands[0]),
            'p2_cards': len(self.hands[1]),
            'p3_cards': len(self.hands[2]),
            'top_card': str(self.top_card),
            'deck_size': len(self.deck),
            'current_player': self.current_player
        }


# ─── Evaluation Functions ──────────────────────────────────────────────────────

def evaluate(state, player_idx, strategy='balanced'):
    """
    Base: Score = 50 - 5*C_AI + 2*C_opp_avg + 3*S
    Weights tuned per strategy.
    """
    my_hand = state.hands[player_idx]
    opp_indices = [i for i in range(3) if i != player_idx]
    opp_avg = sum(len(state.hands[i]) for i in opp_indices) / 2

    c_ai = len(my_hand)
    c_opp = opp_avg
    s = sum(1 for c in my_hand if c.is_skip())

    if strategy == 'defensive':
        # P1: Penalise own cards more, reward opponent cards, value skip cards highly
        w_ai = 7      # heavier penalty for own cards
        w_opp = 1.5   # less reward for opponent having cards
        w_skip = 5    # high skip value (defensive – use skips to block opponents)
        base = 50
        score = base - w_ai * c_ai + w_opp * c_opp + w_skip * s

        # Defensive bonus: if an opponent has few cards, apply extra penalty
        for i in opp_indices:
            if len(state.hands[i]) <= 2:
                score -= 15   # opponent close to winning – urgent!

    elif strategy == 'offensive':
        # P2: Reward shedding own cards aggressively
        w_ai = 4      # standard penalty for own cards
        w_opp = 3     # more reward when opponents have many cards
        w_skip = 2    # skips mildly useful offensively
        base = 50
        score = base - w_ai * c_ai + w_opp * c_opp + w_skip * s

        # Offensive bonus: reward low hand count directly
        if c_ai <= 2:
            score += 10
        if c_ai == 1:
            score += 15   # UNO situation

    else:  # balanced (P3)
        w_ai = 5
        w_opp = 2
        w_skip = 3
        base = 50
        score = base - w_ai * c_ai + w_opp * c_opp + w_skip * s

    return score


# ─── Minimax (Defensive – Player 1 & 3) ───────────────────────────────────────

def minimax(state, depth, player_idx, maximizing, strategy='defensive', alpha=-math.inf, beta=math.inf):
    """
    Minimax with alpha-beta pruning.
    Defensive strategy: P1 assumes opponents minimise its score.
    """
    if state.is_terminal() or depth == 0:
        return evaluate(state, player_idx, strategy), None

    current = state.current_player
    valid_moves = get_valid_moves(state.hands[current], state.top_card)
    actions = valid_moves + [None]   # None = draw

    if current == player_idx:
        # MAX node – AI's turn
        best_score = -math.inf
        best_action = actions[0] if actions else None
        for card in actions:
            new_state, _ = state.apply_move(current, card)
            score, _ = minimax(new_state, depth - 1, player_idx, False, strategy, alpha, beta)
            if score > best_score:
                best_score = score
                best_action = card
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break
        return best_score, best_action
    else:
        # MIN node – opponent's turn (defensive assumption: they play against AI)
        best_score = math.inf
        best_action = actions[0] if actions else None
        for card in actions:
            new_state, _ = state.apply_move(current, card)
            score, _ = minimax(new_state, depth - 1, player_idx, True, strategy, alpha, beta)
            if score < best_score:
                best_score = score
                best_action = card
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        return best_score, best_action


def minimax_with_tree(state, depth, player_idx, maximizing, strategy='defensive',
                      alpha=-math.inf, beta=math.inf, tree_node=None):
    """Minimax that also builds a tree representation for output."""
    if tree_node is None:
        tree_node = {'label': f'P{player_idx+1}(MAX)', 'children': [], 'score': None}

    if state.is_terminal() or depth == 0:
        score = evaluate(state, player_idx, strategy)
        tree_node['score'] = round(score, 2)
        tree_node['label'] += f' [score={round(score,2)}]'
        return score, None, tree_node

    current = state.current_player
    valid_moves = get_valid_moves(state.hands[current], state.top_card)
    actions = valid_moves + [None]

    if current == player_idx:
        best_score = -math.inf
        best_action = actions[0] if actions else None
        for card in actions:
            label = str(card) if card else 'Draw'
            child_node = {'label': f'→{label}', 'children': [], 'score': None}
            new_state, _ = state.apply_move(current, card)
            score, _, child_node = minimax_with_tree(
                new_state, depth - 1, player_idx, False, strategy, alpha, beta, child_node)
            tree_node['children'].append(child_node)
            if score > best_score:
                best_score = score
                best_action = card
            alpha = max(alpha, best_score)
            if beta <= alpha:
                break
        tree_node['score'] = round(best_score, 2)
        return best_score, best_action, tree_node
    else:
        best_score = math.inf
        best_action = actions[0] if actions else None
        for card in actions:
            label = str(card) if card else 'Draw'
            child_node = {'label': f'→{label}(opp)', 'children': [], 'score': None}
            new_state, _ = state.apply_move(current, card)
            score, _, child_node = minimax_with_tree(
                new_state, depth - 1, player_idx, True, strategy, alpha, beta, child_node)
            tree_node['children'].append(child_node)
            if score < best_score:
                best_score = score
                best_action = card
            beta = min(beta, best_score)
            if beta <= alpha:
                break
        tree_node['score'] = round(best_score, 2)
        return best_score, best_action, tree_node


# ─── Expectimax (Offensive – Player 2) ────────────────────────────────────────

def expectimax(state, depth, player_idx, node_type='max', tree_node=None):
    """
    Expectimax search.
    MAX node   → AI's turn (choose best move)
    CHANCE node → draw card (expected value over deck)
    Opponent   → random legal move (P2 doesn't assume worst case)
    """
    build_tree = tree_node is not None
    if build_tree and tree_node is None:
        tree_node = {'label': 'MAX', 'children': [], 'score': None}

    if state.is_terminal() or depth == 0:
        score = evaluate(state, player_idx, 'offensive')
        if build_tree:
            tree_node['score'] = round(score, 2)
            tree_node['label'] += f' [score={round(score,2)}]'
        return score, None

    current = state.current_player
    valid_moves = get_valid_moves(state.hands[current], state.top_card)

    if node_type == 'max':
        # AI's turn – maximise
        best_score = -math.inf
        best_action = None

        for card in valid_moves:
            label = str(card)
            child_node = {'label': f'→{label}', 'children': [], 'score': None} if build_tree else None
            new_state, _ = state.apply_move(current, card)
            score, _ = expectimax(new_state, depth - 1, player_idx, 'opponent', child_node)
            if build_tree:
                child_node['score'] = round(score, 2)
                tree_node['children'].append(child_node)
            if score > best_score:
                best_score = score
                best_action = card

        # Draw as a CHANCE node
        if not valid_moves or True:   # always consider draw option
            chance_node = {'label': 'CHANCE(Draw)', 'children': [], 'score': None} if build_tree else None
            draw_score = expectimax_chance(state, depth - 1, player_idx, chance_node)
            if build_tree:
                if chance_node:
                    chance_node['score'] = round(draw_score, 2)
                tree_node['children'].append(chance_node)
            # Only choose draw if no valid moves exist
            if not valid_moves:
                best_score = draw_score
                best_action = None
            elif draw_score > best_score:
                pass   # prefer playing over drawing if play is available

        if build_tree:
            tree_node['score'] = round(best_score, 2)
        return best_score, best_action

    elif node_type == 'opponent':
        # Opponent's turn – pick a random legal move (Expectimax treats opponents as stochastic)
        opp_moves = get_valid_moves(state.hands[current], state.top_card)
        if not opp_moves:
            new_state, _ = state.apply_move(current, None)
            score, _ = expectimax(new_state, depth - 1, player_idx, 'max' if new_state.current_player == player_idx else 'opponent', None)
            if build_tree:
                tree_node['score'] = round(score, 2)
            return score, None
        # Average over all legal moves (random model)
        total = 0
        for card in opp_moves:
            new_state, _ = state.apply_move(current, card)
            next_type = 'max' if new_state.current_player == player_idx else 'opponent'
            score, _ = expectimax(new_state, depth - 1, player_idx, next_type, None)
            total += score
        avg = total / len(opp_moves)
        if build_tree:
            tree_node['score'] = round(avg, 2)
        return avg, None


def expectimax_chance(state, depth, player_idx, tree_node=None):
    """
    CHANCE node: draw a card.
    Expected value = Σ P(card in deck) * expectimax(state after drawing that card)
    """
    if not state.deck:
        score = evaluate(state, player_idx, 'offensive')
        return score

    current = state.current_player
    deck_size = len(state.deck)

    # Group deck cards by type to compute probabilities
    card_counts = Counter((c.color, c.value) for c in state.deck)
    expected_value = 0.0

    for (color, value), count in card_counts.items():
        prob = count / deck_size
        drawn_card = Card(color, value)

        new_state = state.clone()
        new_state.hands[current].append(drawn_card)
        new_state.deck.remove(drawn_card)
        new_state.current_player = new_state.next_player(current)

        next_type = 'max' if new_state.current_player == player_idx else 'opponent'
        score, _ = expectimax(new_state, depth, player_idx, next_type, None)

        if tree_node is not None:
            child = {'label': f'Draw {drawn_card} (p={prob:.2f})', 'children': [], 'score': round(score, 2)}
            tree_node['children'].append(child)

        expected_value += prob * score

    return expected_value


# ─── Tree Printer ──────────────────────────────────────────────────────────────

def print_tree(node, prefix='', is_last=True, max_children=4):
    """Pretty-print the game tree."""
    connector = '└── ' if is_last else '├── '
    score_str = f" [{node['score']}]" if node['score'] is not None else ''
    print(prefix + connector + node['label'] + score_str)
    child_prefix = prefix + ('    ' if is_last else '│   ')
    children = node.get('children', [])
    if len(children) > max_children:
        shown = children[:max_children]
        hidden = len(children) - max_children
    else:
        shown = children
        hidden = 0
    for i, child in enumerate(shown):
        print_tree(child, child_prefix, i == len(shown) - 1 and hidden == 0, max_children)
    if hidden:
        print(child_prefix + f'└── ... ({hidden} more branches pruned)')


# ─── Game Controller ───────────────────────────────────────────────────────────

class UNOGame:
    PLAYER_NAMES = ['P1 (Minimax-Defensive)', 'P2 (Expectimax-Offensive)', 'P3 (User/AI)']
    DEPTH = 3

    def __init__(self, p3_mode='simulation'):
        self.p3_mode = p3_mode          # 'manual' or 'simulation'
        self.log = []                   # full game log
        self.tree_logs = {}             # search trees per turn
        self.reset()

    def reset(self):
        deck = generate_deck()
        hands = [[], [], []]
        for _ in range(5):
            for i in range(3):
                hands[i].append(deck.pop())
        top_card = deck.pop()
        while top_card.is_skip():      # don't start with a skip
            deck.insert(0, top_card)
            top_card = deck.pop()
        self.state = GameState(hands, top_card, deck, current_player=0)
        self.turn_number = 0
        self.log = []
        self.tree_logs = {}
        self.game_over = False
        self.winner_idx = None
        self._log(f"Game started. Top card: {top_card}")
        self._log_hands()

    def _log(self, msg):
        self.log.append(msg)

    def _log_hands(self):
        for i, hand in enumerate(self.state.hands):
            self._log(f"  {self.PLAYER_NAMES[i]}: {', '.join(str(c) for c in hand)}")

    def get_p1_move(self):
        """P1: Minimax defensive."""
        score, action, tree = minimax_with_tree(
            self.state, self.DEPTH, 0, True, 'defensive')
        key = f"Turn {self.turn_number} P1"
        self.tree_logs[key] = tree
        return action, score

    def get_p2_move(self):
        """P2: Expectimax offensive."""
        current = self.state.current_player
        valid_moves = get_valid_moves(self.state.hands[current], self.state.top_card)
        tree_node = {'label': 'MAX(P2)', 'children': [], 'score': None}

        best_score = -math.inf
        best_action = None
        all_decisions = []

        for card in valid_moves:
            child_node = {'label': f'→{card}', 'children': [], 'score': None}
            new_state, _ = self.state.apply_move(current, card)
            score, _ = expectimax(new_state, self.DEPTH - 1, 1, 'opponent', child_node)
            child_node['score'] = round(score, 2)
            tree_node['children'].append(child_node)
            all_decisions.append((card, score))
            if score > best_score:
                best_score = score
                best_action = card

        # Draw option (chance node)
        chance_node = {'label': 'CHANCE(Draw)', 'children': [], 'score': None}
        draw_score = expectimax_chance(self.state, self.DEPTH - 1, 1, chance_node)
        chance_node['score'] = round(draw_score, 2)
        tree_node['children'].append(chance_node)
        all_decisions.append((None, draw_score))

        if not valid_moves:
            best_action = None
            best_score = draw_score

        tree_node['score'] = round(best_score, 2)
        key = f"Turn {self.turn_number} P2"
        self.tree_logs[key] = tree_node

        return best_action, best_score, all_decisions

    def get_p3_move_simulation(self):
        """P3 in simulation: reuse minimax logic."""
        score, action, tree = minimax_with_tree(
            self.state, self.DEPTH, 2, True, 'balanced')
        key = f"Turn {self.turn_number} P3"
        self.tree_logs[key] = tree
        return action, score

    def step(self, user_card=None):
        """Execute one turn. Returns turn log lines."""
        if self.game_over:
            return []

        self.turn_number += 1
        state = self.state
        current = state.current_player
        name = self.PLAYER_NAMES[current]
        lines = []
        lines.append(f"\n{'='*60}")
        lines.append(f"Turn {self.turn_number} | {name}")
        lines.append(f"Top card: {state.top_card}")
        lines.append(f"Hand: {', '.join(str(c) for c in state.hands[current])}")

        valid = get_valid_moves(state.hands[current], state.top_card)
        lines.append(f"Valid moves: {', '.join(str(c) for c in valid) if valid else 'None (must draw)'}")

        if current == 0:
            action, score = self.get_p1_move()
            if valid:
                lines.append(f"\nMinimax decisions (depth {self.DEPTH}):")
                for card in valid:
                    test_state, _ = state.apply_move(current, card)
                    s = evaluate(test_state, 0, 'defensive')
                    lines.append(f"  Play {card}: score ≈ {round(s,2)}")
                if not valid:
                    lines.append(f"  Draw: score ≈ {round(score,2)}")
            lines.append(f"\n→ DECISION: {'Play ' + str(action) if action else 'Draw a card'} (score={round(score,2)})")

        elif current == 1:
            action, score, decisions = self.get_p2_move()
            lines.append(f"\nExpectimax decisions (depth {self.DEPTH}):")
            for card, sc in decisions:
                label = str(card) if card else "Draw (Chance)"
                lines.append(f"  {label}: expected score = {round(sc,2)}")
            lines.append(f"\n→ DECISION: {'Play ' + str(action) if action else 'Draw a card'} (expected_score={round(score,2)})")

        elif current == 2:
            if self.p3_mode == 'manual':
                action = user_card   # passed in from outside
                score = 0
            else:
                action, score = self.get_p3_move_simulation()
                lines.append(f"\nMinimax (P3-Balanced) decisions (depth {self.DEPTH}):")
                if valid:
                    for card in valid:
                        test_state, _ = state.apply_move(current, card)
                        s = evaluate(test_state, 2, 'balanced')
                        lines.append(f"  Play {card}: score ≈ {round(s,2)}")
                lines.append(f"\n→ DECISION: {'Play ' + str(action) if action else 'Draw a card'} (score={round(score,2)})")

        # Apply the move
        new_state, played_card = state.apply_move(current, action)
        self.state = new_state

        if played_card:
            lines.append(f"\n✓ {name} played: {played_card}")
            if played_card.is_skip():
                skipped = (current + 1) % 3
                lines.append(f"  ⊘ {self.PLAYER_NAMES[skipped]} is SKIPPED!")
        else:
            drawn = new_state.hands[current][-1] if new_state.hands[current] else None
            lines.append(f"\n↓ {name} draws a card: {drawn}")

        lines.append(f"\nHand sizes after turn:")
        for i, h in enumerate(new_state.hands):
            lines.append(f"  {self.PLAYER_NAMES[i]}: {len(h)} cards")

        for line in lines:
            self._log(line)

        if new_state.is_terminal():
            self.game_over = True
            self.winner_idx = new_state.winner()
            msg = f"\n🏆 WINNER: {self.PLAYER_NAMES[self.winner_idx]}!"
            self.log.append(msg)
            lines.append(msg)

        return lines

    def run_full_simulation(self, max_turns=200):
        """Run entire game in simulation mode and print everything."""
        print("=" * 60)
        print("       UNO GAME – AI SIMULATION")
        print("  P1: Minimax (Defensive) | P2: Expectimax (Offensive)")
        print("  P3: Minimax (Balanced)")
        print("=" * 60)
        print(f"\nInitial hands:")
        for i, hand in enumerate(self.state.hands):
            print(f"  {self.PLAYER_NAMES[i]}: {', '.join(str(c) for c in hand)}")
        print(f"Top card: {self.state.top_card}")

        turns = 0
        while not self.game_over and turns < max_turns:
            lines = self.step()
            for line in lines:
                print(line)
            turns += 1

        if not self.game_over:
            print("\n[Game ended: max turns reached]")
        else:
            print(f"\n{'='*60}")
            print(f"  GAME OVER in {turns} turns")
            print(f"  Winner: {self.PLAYER_NAMES[self.winner_idx]}")
            print(f"{'='*60}")

        # Print sample search tree from turn 1
        print("\n\n--- SAMPLE MINIMAX SEARCH TREE (P1, Turn 1) ---")
        if "Turn 1 P1" in self.tree_logs:
            print_tree(self.tree_logs["Turn 1 P1"])
        print("\n--- SAMPLE EXPECTIMAX SEARCH TREE (P2, Turn 2 if it ran) ---")
        key = next((k for k in self.tree_logs if 'P2' in k), None)
        if key:
            print_tree(self.tree_logs[key])


# ─── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    random.seed(42)
    game = UNOGame(p3_mode='simulation')
    game.run_full_simulation()