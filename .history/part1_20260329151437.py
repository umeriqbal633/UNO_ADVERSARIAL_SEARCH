import random
import argparse
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any, Dict

# ----------------------------
# Card + deck
# ----------------------------

COLORS = ["Red", "Blue", "Green", "Yellow"]
NUMBERS = list(range(10))
SKIP = "Skip"

@dataclass(frozen=True)
class Card:
    color: str
    number: Optional[int] = None  # None means Skip

    def is_skip(self) -> bool:
        return self.number is None

    def label(self) -> str:
        return f"{self.color} {SKIP}" if self.is_skip() else f"{self.color} {self.number}"

def generate_deck(seed: Optional[int] = None, skip_per_color: int = 2) -> List[Card]:
    deck = []
    for c in COLORS:
        for n in NUMBERS:
            deck.append(Card(c, n))
        for _ in range(skip_per_color):
            deck.append(Card(c, None))  # skip
    if seed is not None:
        random.seed(seed)
    random.shuffle(deck)
    return deck

# ----------------------------
# Game rules
# ----------------------------

def is_play_legal(card: Card, top: Card) -> bool:
    if card.color == top.color:
        return True
    if (not card.is_skip()) and (not top.is_skip()) and card.number == top.number:
        return True
    # If top is skip, "same number" doesn't apply; only same color works.
    return False

def get_valid_moves(hand: List[Card], top: Card) -> List[Tuple[str, Optional[int]]]:
    moves = []
    for i, card in enumerate(hand):
        if is_play_legal(card, top):
            moves.append(("play", i))
    if not moves:
        moves.append(("draw", None))
    return moves

# ----------------------------
# State representation
# ----------------------------

@dataclass
class State:
    hands: List[List[Card]]          # hands[0], hands[1], hands[2]
    top_card: Card
    deck: List[Card]
    current_player: int              # 0,1,2
    pending_skip: bool = False       # if True, next player's turn is skipped
    last_move_desc: str = ""

def clone_state(s: State) -> State:
    return State(
        hands=[h.copy() for h in s.hands],
        top_card=s.top_card,
        deck=s.deck.copy(),
        current_player=s.current_player,
        pending_skip=s.pending_skip,
        last_move_desc=s.last_move_desc,
    )

def apply_move(s: State, move: Tuple[str, Optional[int]]) -> State:
    ns = clone_state(s)
    p = ns.current_player

    action, idx = move
    if action == "play":
        card = ns.hands[p].pop(idx)  # remove from hand
        ns.top_card = card
        ns.last_move_desc = f"P{p+1} plays {card.label()}"
        if card.is_skip():
            ns.pending_skip = True
    else:
        # draw 1
        if ns.deck:
            drawn = ns.deck.pop()
            ns.hands[p].append(drawn)
            ns.last_move_desc = f"P{p+1} draws {drawn.label()}"
        else:
            ns.last_move_desc = f"P{p+1} draws (deck empty)"
    return advance_turn(ns)

def advance_turn(s: State) -> State:
    ns = clone_state(s)

    # move to next player
    next_p = (ns.current_player + 1) % 3

    if ns.pending_skip:
        # skip exactly one player, then clear
        skipped = next_p
        next_p = (next_p + 1) % 3
        ns.pending_skip = False
        ns.last_move_desc += f" (Skip! P{skipped+1} skipped)"

    ns.current_player = next_p
    return ns

def is_terminal(s: State) -> bool:
    return any(len(h) == 0 for h in s.hands)

def winner(s: State) -> Optional[int]:
    for i in range(3):
        if len(s.hands[i]) == 0:
            return i
    return None

# ----------------------------
# Evaluation functions
# ----------------------------

# Baseline: 50 − 5(CAI) + 2(Copp) + 3(S)
# We'll tune weights.
DEF_W = dict(base=50, w_ai=-6.0, w_opp=+3.0, w_skip=+5.0)
OFF_W = dict(base=50, w_ai=-7.0, w_opp=+1.5, w_skip=+3.0)

def eval_for_player(s: State, player: int, weights: Dict[str, float]) -> float:
    cai = len(s.hands[player])
    opp_idxs = [i for i in range(3) if i != player]
    copp = (len(s.hands[opp_idxs[0]]) + len(s.hands[opp_idxs[1]])) / 2.0
    skip_count = sum(1 for c in s.hands[player] if c.is_skip())

    score = (
        weights["base"]
        + weights["w_ai"] * cai
        + weights["w_opp"] * copp
        + weights["w_skip"] * skip_count
    )

    # Terminal bonus/penalty (helps search be decisive)
    w = winner(s)
    if w is not None:
        if w == player:
            score += 1_000.0
        else:
            score -= 1_000.0
    return score

# ----------------------------
# Minimax (Defensive) for P1 and optionally P3
# ----------------------------

def minimax(s: State, depth: int, maximizing_player: int, weights: Dict[str, float],
            tree: Optional[List[str]] = None, indent: int = 0) -> float:
    if tree is not None:
        tree.append("  " * indent + f"[MM] d={depth} turn=P{s.current_player+1} top={s.top_card.label()}")

    if depth == 0 or is_terminal(s):
        val = eval_for_player(s, maximizing_player, weights)
        if tree is not None:
            tree.append("  " * indent + f"= {val:.2f} (eval)")
        return val

    turn = s.current_player
    moves = get_valid_moves(s.hands[turn], s.top_card)

    if turn == maximizing_player:
        best = float("-inf")
        for mv in moves:
            ns = apply_move(s, mv)
            val = minimax(ns, depth - 1, maximizing_player, weights, tree, indent + 1)
            best = max(best, val)
        if tree is not None:
            tree.append("  " * indent + f"= {best:.2f} (max)")
        return best
    else:
        # Defensive assumption: opponents minimize our score
        best = float("inf")
        for mv in moves:
            ns = apply_move(s, mv)
            val = minimax(ns, depth - 1, maximizing_player, weights, tree, indent + 1)
            best = min(best, val)
        if tree is not None:
            tree.append("  " * indent + f"= {best:.2f} (min)")
        return best

def choose_minimax_move(s: State, depth: int, player: int, weights: Dict[str, float],
                        show_decisions: bool = True, show_tree: bool = False) -> Tuple[Tuple[str, Optional[int]], float, List[str]]:
    moves = get_valid_moves(s.hands[player], s.top_card)
    decision_table = []
    best_move = moves[0]
    best_val = float("-inf")
    full_tree = []

    for mv in moves:
        tree = [] if show_tree else None
        ns = apply_move(s, mv)
        val = minimax(ns, depth - 1, player, weights, tree, indent=1)
        if show_decisions:
            decision_table.append((mv, val))
        if show_tree and tree is not None:
            full_tree.append(f"ROOT move={pretty_move(s, player, mv)} val={val:.2f}")
            full_tree.extend(tree)

        if val > best_val:
            best_val, best_move = val, mv

    if show_decisions:
        print(f"AI decision (depth {depth}, P{player+1} Minimax - Defensive):")
        for mv, val in decision_table:
            print(f"  {pretty_move(s, player, mv)} -> score {val:.2f}")

    return best_move, best_val, full_tree

# ----------------------------
# Expectimax (Offensive) for P2
# ----------------------------

def expectimax(s: State, depth: int, max_player: int, weights: Dict[str, float],
               tree: Optional[List[str]] = None, indent: int = 0) -> float:
    if tree is not None:
        tree.append("  " * indent + f"[EX] d={depth} turn=P{s.current_player+1} top={s.top_card.label()}")

    if depth == 0 or is_terminal(s):
        val = eval_for_player(s, max_player, weights)
        if tree is not None:
            tree.append("  " * indent + f"= {val:.2f} (eval)")
        return val

    turn = s.current_player
    moves = get_valid_moves(s.hands[turn], s.top_card)

    if turn == max_player:
        # MAX node: choose best action
        best = float("-inf")
        for mv in moves:
            if mv[0] == "draw":
                # Chance node: expected value over possible drawn cards
                ev = chance_draw_node(s, depth, max_player, weights, tree, indent + 1)
                best = max(best, ev)
            else:
                ns = apply_move(s, mv)
                val = expectimax(ns, depth - 1, max_player, weights, tree, indent + 1)
                best = max(best, val)
        if tree is not None:
            tree.append("  " * indent + f"= {best:.2f} (max)")
        return best

    else:
        # Opponent node: "choose random legal move" as per your spec
        # In expectimax, opponent is modeled as stochastic policy.
        # We'll take uniform average over legal moves (more stable than picking one random move).
        total = 0.0
        p = 1.0 / len(moves)
        for mv in moves:
            ns = apply_move(s, mv)
            total += p * expectimax(ns, depth - 1, max_player, weights, tree, indent + 1)
        if tree is not None:
            tree.append("  " * indent + f"= {total:.2f} (opp-avg)")
        return total

def chance_draw_node(s: State, depth: int, max_player: int, weights: Dict[str, float],
                     tree: Optional[List[str]], indent: int) -> float:
    # If deck empty, drawing changes nothing except turn advance is handled in apply_move
    if not s.deck:
        ns = apply_move(s, ("draw", None))
        return expectimax(ns, depth - 1, max_player, weights, tree, indent)

    # Expected value by drawing each possible remaining card with probability proportional to count.
    # We approximate by unique card counts.
    counts: Dict[Card, int] = {}
    for c in s.deck:
        counts[c] = counts.get(c, 0) + 1
    total_cards = len(s.deck)

    ev = 0.0
    for card, cnt in counts.items():
        p = cnt / total_cards
        ns = clone_state(s)
        # simulate drawing this card:
        # remove one instance from deck
        ns.deck.remove(card)
        ns.hands[ns.current_player].append(card)
        ns.last_move_desc = f"P{ns.current_player+1} draws {card.label()} (chance)"
        ns = advance_turn(ns)
        ev += p * expectimax(ns, depth - 1, max_player, weights, tree, indent + 1)

    if tree is not None:
        tree.append("  " * indent + f"[CHANCE draw] EV={ev:.2f} over {len(counts)} unique cards")
    return ev

def choose_expectimax_move(s: State, depth: int, player: int, weights: Dict[str, float],
                           show_decisions: bool = True, show_tree: bool = False) -> Tuple[Tuple[str, Optional[int]], float, List[str]]:
    moves = get_valid_moves(s.hands[player], s.top_card)
    decision_table = []
    best_move = moves[0]
    best_val = float("-inf")
    full_tree = []

    for mv in moves:
        tree = [] if show_tree else None
        if mv[0] == "draw":
            val = chance_draw_node(s, depth, player, weights, tree, indent=1)
        else:
            ns = apply_move(s, mv)
            val = expectimax(ns, depth - 1, player, weights, tree, indent=1)

        if show_decisions:
            decision_table.append((mv, val))
        if show_tree and tree is not None:
            full_tree.append(f"ROOT move={pretty_move(s, player, mv)} val={val:.2f}")
            full_tree.extend(tree)

        if val > best_val:
            best_val, best_move = val, mv

    if show_decisions:
        print(f"AI decision (depth {depth}, P{player+1} Expectimax - Offensive):")
        for mv, val in decision_table:
            print(f"  {pretty_move(s, player, mv)} -> expected {val:.2f}")

    return best_move, best_val, full_tree

# ----------------------------
# Pretty printing helpers
# ----------------------------

def pretty_move(s: State, player: int, mv: Tuple[str, Optional[int]]) -> str:
    action, idx = mv
    if action == "draw":
        return "Draw 1 card"
    card = s.hands[player][idx]
    return f"Play {card.label()}"

def print_hand(title: str, hand: List[Card], hide: bool = False) -> None:
    print(title)
    if hide:
        print(f"  ({len(hand)} cards hidden)")
        return
    for i, c in enumerate(hand):
        print(f"  [{i}] {c.label()}")

# ----------------------------
# Game loop
# ----------------------------

def deal_initial(deck: List[Card]) -> Tuple[List[List[Card]], Card, List[Card]]:
    hands = [[], [], []]
    for _ in range(5):
        for p in range(3):
            hands[p].append(deck.pop())
    top = deck.pop()
    return hands, top, deck

def run_game(mode_p3: str, seed: int, depth: int, show_tree: bool) -> None:
    deck = generate_deck(seed=seed)
    hands, top, deck = deal_initial(deck)

    s = State(hands=hands, top_card=top, deck=deck, current_player=0)
    print(f"Initial Top card: {s.top_card.label()}")
    print()

    move_no = 1
    while not is_terminal(s):
        p = s.current_player
        print(f"\n--- Move {move_no} | Turn: P{p+1} ---")
        print(f"Top card: {s.top_card.label()}")
        print(f"Deck size: {len(s.deck)}")

        # Show hands (you can hide opponents if desired, but assignment says show moves and step-by-step)
        print_hand("P1 hand:", s.hands[0], hide=False)
        print_hand("P2 hand:", s.hands[1], hide=False)
        print_hand("P3 hand:", s.hands[2], hide=False)

        tree_lines: List[str] = []

        if p == 0:
            mv, val, tree_lines = choose_minimax_move(s, depth, 0, DEF_W, show_decisions=True, show_tree=show_tree)
        elif p == 1:
            mv, val, tree_lines = choose_expectimax_move(s, depth, 1, OFF_W, show_decisions=True, show_tree=show_tree)
        else:
            if mode_p3 == "manual":
                moves = get_valid_moves(s.hands[2], s.top_card)
                print("Valid moves:")
                for i, mvx in enumerate(moves):
                    print(f"  ({i}) {pretty_move(s, 2, mvx)}")
                choice = int(input("Choose move index: "))
                mv = moves[choice]
                val = 0.0
            else:
                mv, val, tree_lines = choose_minimax_move(s, depth, 2, DEF_W, show_decisions=True, show_tree=show_tree)

        s = apply_move(s, mv)
        print(f"Action: {s.last_move_desc}")

        if show_tree and tree_lines:
            print("\nSearch tree (text):")
            for line in tree_lines[:2500]:
                print(line)

        move_no += 1

    w = winner(s)
    print("\n=== GAME OVER ===")
    print(f"Winner: P{w+1}")
    print(f"Final top card: {s.top_card.label()}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["manual", "sim"], default="sim",
                        help="P3 mode: manual (you play) or sim (AI plays)")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--show-tree", action="store_true", help="Print search tree logs")
    args = parser.parse_args()

    run_game(mode_p3=("manual" if args.mode == "manual" else "sim"),
             seed=args.seed,
             depth=args.depth,
             show_tree=args.show_tree)

if __name__ == "__main__":
    main()