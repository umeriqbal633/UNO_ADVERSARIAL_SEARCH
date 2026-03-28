import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

COLORS = ["Red", "Blue", "Green", "Yellow"]
NUMBERS = list(range(10))

@dataclass(frozen=True)
class Card:
    color: str
    number: Optional[int] = None  # None => Skip

    def is_skip(self) -> bool:
        return self.number is None

    def label(self) -> str:
        return f"{self.color} Skip" if self.is_skip() else f"{self.color} {self.number}"


def generate_deck(seed: Optional[int] = None, skip_per_color: int = 2) -> List[Card]:
    """Creates and shuffles the simplified UNO deck."""
    deck: List[Card] = []
    for c in COLORS:
        for n in NUMBERS:
            deck.append(Card(c, n))
        for _ in range(skip_per_color):
            deck.append(Card(c, None))  # Skip

    if seed is not None:
        random.seed(seed)
    random.shuffle(deck)
    return deck


def is_play_legal(card: Card, top: Card) -> bool:
    """Rule 1: same color OR same number (Skip has no number)."""
    if card.color == top.color:
        return True

    # same number only works if both cards are numbered
    if (not card.is_skip()) and (not top.is_skip()) and card.number == top.number:
        return True

    return False


def get_valid_moves(hand: List[Card], top: Card) -> List[Tuple[str, Optional[int]]]:
    """
    Returns list of moves:
    - ("play", index) if playable
    - ("draw", None) if nothing playable
    """
    moves: List[Tuple[str, Optional[int]]] = []
    for i, c in enumerate(hand):
        if is_play_legal(c, top):
            moves.append(("play", i))
    if not moves:
        moves.append(("draw", None))
    return moves


@dataclass
class State:
    hands: List[List[Card]]   # hands[0], hands[1], hands[2]
    top_card: Card
    deck: List[Card]
    current_player: int = 0
    pending_skip: bool = False
    last_move_desc: str = ""


def deal_initial(deck: List[Card], cards_each: int = 5) -> State:
    hands = [[], [], []]
    for _ in range(cards_each):
        for p in range(3):
            hands[p].append(deck.pop())
    top = deck.pop()
    return State(hands=hands, top_card=top, deck=deck, current_player=0)


def advance_turn(s: State) -> None:
    """Handles next player, and applies skip if pending."""
    next_p = (s.current_player + 1) % 3
    if s.pending_skip:
        skipped = next_p
        next_p = (next_p + 1) % 3
        s.pending_skip = False
        s.last_move_desc += f" (Skip! P{skipped+1} skipped)"
    s.current_player = next_p


def apply_move(s: State, move: Tuple[str, Optional[int]]) -> None:
    """Applies move to state (in-place). Implements Rule 2 and Rule 3."""
    p = s.current_player
    action, idx = move

    if action == "play":
        card = s.hands[p].pop(idx)
        s.top_card = card
        s.last_move_desc = f"P{p+1} plays {card.label()}"
        if card.is_skip():
            s.pending_skip = True
    else:
        # draw 1
        if s.deck:
            drawn = s.deck.pop()
            s.hands[p].append(drawn)
            s.last_move_desc = f"P{p+1} draws {drawn.label()}"
        else:
            s.last_move_desc = f"P{p+1} draws (deck empty)"

    advance_turn(s)


def is_terminal(s: State) -> bool:
    """Rule 4: a player wins when their hand is empty."""
    return any(len(h) == 0 for h in s.hands)


def winner(s: State) -> Optional[int]:
    for i in range(3):
        if len(s.hands[i]) == 0:
            return i
    return None


def print_state(s: State) -> None:
    print(f"Top card: {s.top_card.label()}")
    print(f"Deck size: {len(s.deck)}")
    for i in range(3):
        labels = ", ".join([c.label() for c in s.hands[i]])
        print(f"P{i+1} hand ({len(s.hands[i])}): {labels}")