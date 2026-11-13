"""Chess engine: position evaluation + Minimax / Alpha-Beta search.

The search records the whole tree it explores, so the UI can show exactly
what the AI looked at: every move, every value, and every branch that was
pruned. Nothing here is simulated -- the tree comes from real legal moves.
"""

import time

import chess

# Piece values in centipawns (100 = one pawn).
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 0,
}

# Piece-square tables, written from White's point of view, rank 8 first.
# They reward putting a piece on a good square (e.g. knights near the
# centre, pawns advanced, king tucked away in the middlegame).
PAWN_TABLE = [
    0, 0, 0, 0, 0, 0, 0, 0,
    50, 50, 50, 50, 50, 50, 50, 50,
    10, 10, 20, 30, 30, 20, 10, 10,
    5, 5, 10, 25, 25, 10, 5, 5,
    0, 0, 0, 20, 20, 0, 0, 0,
    5, -5, -10, 0, 0, -10, -5, 5,
    5, 10, 10, -20, -20, 10, 10, 5,
    0, 0, 0, 0, 0, 0, 0, 0,
]
KNIGHT_TABLE = [
    -50, -40, -30, -30, -30, -30, -40, -50,
    -40, -20, 0, 0, 0, 0, -20, -40,
    -30, 0, 10, 15, 15, 10, 0, -30,
    -30, 5, 15, 20, 20, 15, 5, -30,
    -30, 0, 15, 20, 20, 15, 0, -30,
    -30, 5, 10, 15, 15, 10, 5, -30,
    -40, -20, 0, 5, 5, 0, -20, -40,
    -50, -40, -30, -30, -30, -30, -40, -50,
]
BISHOP_TABLE = [
    -20, -10, -10, -10, -10, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 5, 10, 10, 5, 0, -10,
    -10, 5, 5, 10, 10, 5, 5, -10,
    -10, 0, 10, 10, 10, 10, 0, -10,
    -10, 10, 10, 10, 10, 10, 10, -10,
    -10, 5, 0, 0, 0, 0, 5, -10,
    -20, -10, -10, -10, -10, -10, -10, -20,
]
ROOK_TABLE = [
    0, 0, 0, 0, 0, 0, 0, 0,
    5, 10, 10, 10, 10, 10, 10, 5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    -5, 0, 0, 0, 0, 0, 0, -5,
    0, 0, 0, 5, 5, 0, 0, 0,
]
QUEEN_TABLE = [
    -20, -10, -10, -5, -5, -10, -10, -20,
    -10, 0, 0, 0, 0, 0, 0, -10,
    -10, 0, 5, 5, 5, 5, 0, -10,
    -5, 0, 5, 5, 5, 5, 0, -5,
    0, 0, 5, 5, 5, 5, 0, -5,
    -10, 5, 5, 5, 5, 5, 0, -10,
    -10, 0, 5, 0, 0, 0, 0, -10,
    -20, -10, -10, -5, -5, -10, -10, -20,
]
KING_TABLE = [
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -30, -40, -40, -50, -50, -40, -40, -30,
    -20, -30, -30, -40, -40, -30, -30, -20,
    -10, -20, -20, -20, -20, -20, -20, -10,
    20, 20, 0, 0, 0, 0, 20, 20,
    20, 30, 10, 0, 0, 10, 30, 20,
]

TABLES = {
    chess.PAWN: PAWN_TABLE,
    chess.KNIGHT: KNIGHT_TABLE,
    chess.BISHOP: BISHOP_TABLE,
    chess.ROOK: ROOK_TABLE,
    chess.QUEEN: QUEEN_TABLE,
    chess.KING: KING_TABLE,
}

# A forced mate is worth far more than any material, and the search prefers
# faster mates (the bonus shrinks by one pawn per ply away from the mate).
MATE_SCORE = 100000
INF = float("inf")

# Repetition: shuffling the same pieces back and forth wins nothing. A move
# that repeats a position already seen in this game is penalised -- a little
# for the second visit, a lot for the third (which would let either side
# claim a draw and end the game). A mating move is exempt from the penalty
# entirely, so the AI never delays a checkmate to avoid a repeat.
REPETITION_PENALTY_ONCE = 30
REPETITION_PENALTY_THRICE = 500


def position_key(board):
    """The key python-chess uses to spot a repeated position: the pieces,
    the side to move, castling rights and the en-passant square."""
    return board._transposition_key()


def repetition_penalty(times_seen):
    """How much a move is docked for returning to a position already seen
    `times_seen` times in this game (centipawns)."""
    if times_seen >= 2:
        return REPETITION_PENALTY_THRICE
    if times_seen == 1:
        return REPETITION_PENALTY_ONCE
    return 0


def game_over_reason(board):
    """Why the game is over, for the GAME OVER banner. Returns None while
    the game can still continue. Threefold repetition and the fifty-move
    rule are claims in chess, not automatic -- here the game claims them
    at once, so a game can never shuffle the same pieces forever."""
    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        return {"headline": f"Checkmate — {winner} wins!",
                "detail": "The king is in check and has no legal move.",
                "result": board.result()}
    if board.is_stalemate():
        return {"headline": "Stalemate — draw",
                "detail": "No legal moves, but the king is not in check.",
                "result": board.result()}
    if board.is_insufficient_material():
        return {"headline": "Draw — not enough pieces left",
                "detail": "Neither side has enough material to checkmate.",
                "result": board.result()}
    if board.is_repetition(3) or board.is_fivefold_repetition():
        return {"headline": "Draw — same position three times",
                "detail": "Repeating the same moves cannot win; the game is a draw.",
                "result": board.result()}
    if board.is_fifty_moves() or board.is_seventyfive_moves():
        return {"headline": "Draw — 50 moves, no progress",
                "detail": "Fifty moves with no capture and no pawn move is a draw.",
                "result": board.result()}
    if board.is_game_over():
        return {"headline": "Game over",
                "detail": "The game has ended.",
                "result": board.result()}
    return None


def evaluate(board):
    """Score a position in centipawns, from White's point of view.

    Positive = good for White, negative = good for Black.
    Material + where each piece stands. No randomness: the same
    position always scores the same.
    """
    score = 0
    for square, piece in board.piece_map().items():
        # Tables are written from White's point of view, rank 8 first,
        # so a white piece reads the table at the rank-mirrored square
        # (a1 -> the a8 entry) while a black piece reads it directly.
        index = square ^ 56 if piece.color == chess.WHITE else square
        value = PIECE_VALUES[piece.piece_type] + TABLES[piece.piece_type][index]
        score += value if piece.color == chess.WHITE else -value
    return score


def format_score(cp):
    """Centipawns -> a short human score: '+1.2', '-0.3', or 'M4' for mate."""
    if cp is None:
        return "?"
    if abs(cp) >= MATE_SCORE - 1000:
        plies = MATE_SCORE - abs(cp)
        mate_in = (plies + 1) // 2
        return f"M{mate_in}" if cp > 0 else f"-M{mate_in}"
    sign = "+" if cp >= 0 else "-"
    return f"{sign}{abs(cp) / 100:.1f}"


class TreeNode:
    """One position in the recorded search tree."""

    def __init__(self, san, depth, maximizing, alpha, beta, fen):
        self.san = san                # move that reached this node ("start" for root)
        self.depth = depth            # plies remaining below this node
        self.maximizing = maximizing  # True: White to move (MAX), False: Black (MIN)
        self.alpha = alpha            # best score White can already guarantee
        self.beta = beta              # best score Black can already guarantee
        self.fen = fen                # position, so the UI can show this board
        self.value = None             # minimax value once known
        self.children = []
        self.pruned = False           # True: this branch was cut off, never explored
        self.order = 0                # visit order (for step-through replay)

    @property
    def kind(self):
        return "MAX" if self.maximizing else "MIN"


class SearchStats:
    def __init__(self):
        self.nodes = 0       # positions the search actually evaluated
        self.pruned = 0      # branches skipped by alpha-beta pruning
        self.time = 0.0      # seconds


def _order_moves(board):
    """Best-first move order: captures first, biggest victim first.

    Good ordering is what makes alpha-beta pruning work -- the sooner the
    search finds a strong move, the sooner it can skip the weak ones.
    """
    def key(move):
        if board.is_capture(move):
            victim = board.piece_at(move.to_square)
            attacker = board.piece_at(move.from_square)
            victim_value = PIECE_VALUES[victim.piece_type] if victim else 0
            attacker_value = PIECE_VALUES[attacker.piece_type] if attacker else 0
            return -victim_value * 10 + attacker_value
        return 0
    return sorted(board.legal_moves, key=key)


def _minimax(board, depth, alpha, beta, maximizing, node, stats, use_pruning, ply):
    """Classic minimax with optional alpha-beta pruning. Returns the score
    of this position (centipawns, White's point of view) and fills in the
    recorded tree under `node`."""
    stats.nodes += 1
    node.order = stats.nodes

    if board.is_checkmate():
        # Side to move has no legal move and is in check: it lost.
        node.value = (-MATE_SCORE + ply) if maximizing else (MATE_SCORE - ply)
        return node.value
    if board.is_stalemate() or board.is_insufficient_material():
        node.value = 0
        return 0
    if depth == 0:
        node.value = evaluate(board)
        return node.value

    if maximizing:
        best = -INF
        for move in _order_moves(board):
            san = board.san(move)
            board.push(move)
            child = TreeNode(san, depth - 1, False, alpha, beta, board.fen())
            node.children.append(child)
            value = _minimax(board, depth - 1, alpha, beta, False, child,
                             stats, use_pruning, ply + 1)
            board.pop()
            if value > best:
                best = value
            if use_pruning:
                alpha = max(alpha, best)
                if beta <= alpha:
                    # Beta cutoff: Black already has a reply at least this
                    # good somewhere else, so White will never choose this
                    # branch. The remaining moves are skipped, not searched.
                    _mark_remaining_pruned(board, node, alpha, beta, stats)
                    break
        node.value = best
        return best
    else:
        best = INF
        for move in _order_moves(board):
            san = board.san(move)
            board.push(move)
            child = TreeNode(san, depth - 1, True, alpha, beta, board.fen())
            node.children.append(child)
            value = _minimax(board, depth - 1, alpha, beta, True, child,
                             stats, use_pruning, ply + 1)
            board.pop()
            if value < best:
                best = value
            if use_pruning:
                beta = min(beta, best)
                if beta <= alpha:
                    # Alpha cutoff: White already has a move at least this
                    # good somewhere else, so Black will never allow this
                    # branch. The remaining moves are skipped, not searched.
                    _mark_remaining_pruned(board, node, alpha, beta, stats)
                    break
        node.value = best
        return best


def _mark_remaining_pruned(board, node, alpha, beta, stats):
    """Record the moves alpha-beta skipped as red pruned nodes, so the
    tree shows what was cut off instead of silently dropping it."""
    seen = {child.san for child in node.children}
    for move in board.legal_moves:
        san = board.san(move)
        if san not in seen:
            pruned = TreeNode(san, node.depth - 1, not node.maximizing,
                              alpha, beta, board.fen())
            pruned.pruned = True
            pruned.value = None
            stats.pruned += 1
            node.children.append(pruned)


def best_move(board, depth, use_pruning=True, history_keys=None):
    """Search from `board` and return the AI's move plus everything the
    search saw: the tree, the stats, and each root move's score.

    `history_keys` maps position keys seen so far in this game to how many
    times each occurred. A move that repeats a position is docked by
    `repetition_penalty`, so the AI prefers to make progress instead of
    shuffling pieces back and forth. The docked (effective) score is what
    the candidate table shows, because that is what the AI decided on.
    `avoided_repetition` is True when the penalty changed the AI's pick.
    """
    stats = SearchStats()
    root = TreeNode("start", depth, board.turn == chess.WHITE, -INF, INF,
                    board.fen())
    start = time.time()
    value = _minimax(board, depth, -INF, INF, board.turn == chess.WHITE,
                     root, stats, use_pruning, 0)
    stats.time = time.time() - start

    # Root children hold one score per legal move: the candidate table.
    raw = sorted(
        ((child.san, child.value) for child in root.children
         if child.value is not None),
        key=lambda item: item[1],
        reverse=(board.turn == chess.WHITE),
    )
    if not raw:
        # Game already over (mate / stalemate): no move to return.
        return {"move": None, "san": None, "value": value, "tree": root,
                "stats": stats, "candidates": [], "pv": [],
                "avoided_repetition": False}

    # Dock moves that would repeat a position already seen in this game.
    # Scores are White's point of view, so a penalty lowers the score for
    # White and raises it for Black -- worse for whoever is about to move.
    history_keys = history_keys or {}
    effective = {}
    for san, score in raw:
        move = next((m for m in board.legal_moves
                     if board.san(m) == san), None)
        penalty = 0
        if move is not None and abs(score) < MATE_SCORE - 1000:
            # Never let a repetition worry delay a forced mate: a mating
            # move is exempt from the penalty entirely.
            board.push(move)
            penalty = repetition_penalty(
                history_keys.get(position_key(board), 0))
            board.pop()
        if board.turn == chess.WHITE:
            effective[san] = score - penalty
        else:
            effective[san] = score + penalty
    candidates = sorted(raw, key=lambda item: effective[item[0]],
                        reverse=(board.turn == chess.WHITE))
    candidates = [(san, effective[san]) for san, _ in candidates]
    avoided = candidates[0][0] != raw[0][0]

    # The best move is the first candidate. The principal variation is the
    # best line from that move: follow the chosen child's best children.
    chosen_san = candidates[0][0]
    move = None
    chosen_child = None
    for legal in board.legal_moves:
        if board.san(legal) == chosen_san:
            move = legal
            break
    for child in root.children:
        if child.san == chosen_san:
            chosen_child = child
            break
    pv = [chosen_san] + _principal_variation(chosen_child) \
        if chosen_child is not None else [chosen_san]
    return {
        "move": move,
        "san": chosen_san,
        "value": effective[chosen_san],
        "tree": root,
        "stats": stats,
        "candidates": candidates,
        "pv": pv,
        "avoided_repetition": avoided,
    }


def _principal_variation(node):
    """Best line from this node: at each step follow the child whose value
    matches the node's value (the move the search would actually pick)."""
    line = []
    current = node
    while current.children:
        scored = [c for c in current.children if c.value is not None]
        if not scored:
            break
        if current.maximizing:
            nxt = max(scored, key=lambda c: c.value)
        else:
            nxt = min(scored, key=lambda c: c.value)
        if nxt.value != current.value:
            break
        line.append(nxt.san)
        current = nxt
    return line


def compare(board, depth, history_keys=None):
    """Run the same position twice, once plain minimax and once with
    alpha-beta pruning. Both must pick the same move and score -- pruning
    only skips work, it never changes the answer. Returns both reports."""
    plain = best_move(board, depth, use_pruning=False,
                      history_keys=history_keys)
    pruned = best_move(board, depth, use_pruning=True,
                       history_keys=history_keys)
    return {"plain": plain, "pruned": pruned}
