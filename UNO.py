from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from collections import Counter

from uno_core import State, Card, get_valid_moves, apply_move, is_terminal, winner

Move = Tuple[str, Optional[int]]  # ("play", index) or ("draw", None)

# ----------------------------
# Strategy weight tuning
# ----------------------------

# Baseline: Score = 50 − 5(CAI) + 2(Copp) + 3(S)
# Defensive: block opponents, value Skip more
DEF_W = dict(base=50.0, w_ai=-6.0, w_opp=+3.0, w_skip=+5.0)

# Offensive: shed fast, less opponent focus
OFF_W = dict(base=50.0, w_ai=-7.0, w_opp=+1.5, w_skip=+3.0)

# Terminal bonus to force winning/avoid losing inside depth-limited search
WIN_BONUS = 1000.0


def eval_for_player(s: State, player: int, weights: Dict[str, float]) -> float:
    cai = len(s.hands[player])
    opp = [i for i in range(3) if i != player]
    copp = (len(s.hands[opp[0]]) + len(s.hands[opp[1]])) / 2.0
    skip_count = sum(1 for c in s.hands[player] if c.is_skip())

    score = (
        weights["base"]
        + weights["w_ai"] * cai
        + weights["w_opp"] * copp
        + weights["w_skip"] * skip_count
    )

    w = winner(s)
    if w is not None:
        if w == player:
            score += WIN_BONUS
        else:
            score -= WIN_BONUS
    return score


# ----------------------------
# Helpers: clone state (simple safe copy)
# ----------------------------

def clone_state(s: State) -> State:
    return State(
        hands=[h.copy() for h in s.hands],
        top_card=s.top_card,
        deck=s.deck.copy(),
        current_player=s.current_player,
        pending_skip=s.pending_skip,
        last_move_desc=s.last_move_desc,
    )


# ----------------------------
# Minimax (Defensive) - P1 (and later reuse for P3 sim)
# ----------------------------

def minimax(s: State, depth: int, maximizing_player: int, weights: Dict[str, float]) -> float:
    if depth == 0 or is_terminal(s):
        return eval_for_player(s, maximizing_player, weights)

    turn = s.current_player
    moves = get_valid_moves(s.hands[turn], s.top_card)

    if turn == maximizing_player:
        best = float("-inf")
        for mv in moves:
            ns = clone_state(s)
            apply_move(ns, mv)
            best = max(best, minimax(ns, depth - 1, maximizing_player, weights))
        return best
    else:
        # Defensive assumption: opponents minimize our score
        best = float("inf")
        for mv in moves:
            ns = clone_state(s)
            apply_move(ns, mv)
            best = min(best, minimax(ns, depth - 1, maximizing_player, weights))
        return best


def choose_minimax_move(s: State, depth: int, player: int, weights: Dict[str, float]) -> Tuple[Move, float, List[Tuple[str, float]]]:
    moves = get_valid_moves(s.hands[player], s.top_card)

    best_move = moves[0]
    best_val = float("-inf")
    decision_rows: List[Tuple[str, float]] = []

    for mv in moves:
        ns = clone_state(s)
        apply_move(ns, mv)
        val = minimax(ns, depth - 1, player, weights)
        decision_rows.append((pretty_move(s, player, mv), val))
        if val > best_val:
            best_val, best_move = val, mv

    return best_move, best_val, decision_rows


# ----------------------------
# Expectimax (Offensive) - P2
# Draw is a CHANCE node (expected value over remaining deck)
# Opponents: "random legal move" -> modeled as uniform average over their legal moves
# ----------------------------

def expectimax(s: State, depth: int, max_player: int, weights: Dict[str, float]) -> float:
    if depth == 0 or is_terminal(s):
        return eval_for_player(s, max_player, weights)

    turn = s.current_player
    moves = get_valid_moves(s.hands[turn], s.top_card)

    if turn == max_player:
        best = float("-inf")
        for mv in moves:
            if mv[0] == "draw":
                val = chance_draw_value(s, depth, max_player, weights)
            else:
                ns = clone_state(s)
                apply_move(ns, mv)
                val = expectimax(ns, depth - 1, max_player, weights)
            best = max(best, val)
        return best

    # Opponent node: uniform over their legal moves (stable form of "random legal move")
    p = 1.0 / len(moves)
    total = 0.0
    for mv in moves:
        ns = clone_state(s)
        apply_move(ns, mv)
        total += p * expectimax(ns, depth - 1, max_player, weights)
    return total


def chance_draw_value(s: State, depth: int, max_player: int, weights: Dict[str, float]) -> float:
    # If deck empty, just apply draw (no card gained)
    if not s.deck:
        ns = clone_state(s)
        apply_move(ns, ("draw", None))
        return expectimax(ns, depth - 1, max_player, weights)

    # Expected value over all remaining cards in deck
    counts = Counter(s.deck)
    total_cards = len(s.deck)

    ev = 0.0
    for card, cnt in counts.items():
        prob = cnt / total_cards
        ns = clone_state(s)

        # simulate drawing this exact card:
        ns.deck.remove(card)
        ns.hands[ns.current_player].append(card)
        ns.last_move_desc = f"P{ns.current_player+1} draws {card.label()} (chance)"

        # advance turn logic is in apply_move normally; we need to replicate "end of turn"
        # easiest: directly call apply_move with a fake draw, but that would draw again.
        # So we do a tiny manual turn advance:
        # (copy of uno_core.advance_turn behavior)
        next_p = (ns.current_player + 1) % 3
        if ns.pending_skip:
            next_p = (next_p + 1) % 3
            ns.pending_skip = False
        ns.current_player = next_p

        ev += prob * expectimax(ns, depth - 1, max_player, weights)

    return ev


def choose_expectimax_move(s: State, depth: int, player: int, weights: Dict[str, float]) -> Tuple[Move, float, List[Tuple[str, float]]]:
    moves = get_valid_moves(s.hands[player], s.top_card)

    best_move = moves[0]
    best_val = float("-inf")
    decision_rows: List[Tuple[str, float]] = []

    for mv in moves:
        if mv[0] == "draw":
            val = chance_draw_value(s, depth, player, weights)
        else:
            ns = clone_state(s)
            apply_move(ns, mv)
            val = expectimax(ns, depth - 1, player, weights)

        decision_rows.append((pretty_move(s, player, mv), val))
        if val > best_val:
            best_val, best_move = val, mv

    return best_move, best_val, decision_rows


# ----------------------------
# Pretty move (for decision tables)
# ----------------------------

def pretty_move(s: State, player: int, mv: Move) -> str:
    action, idx = mv
    if action == "draw":
        return "Draw 1 card"
    card: Card = s.hands[player][idx]
    return f"Play {card.label()}"