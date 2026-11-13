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


def best_move(board, depth, use_pruning=True):
    """Search from `board` and return the AI's move plus everything the
    search saw: the tree, the stats, and each root move's score."""
    stats = SearchStats()
    root = TreeNode("start", depth, board.turn == chess.WHITE, -INF, INF,
                    board.fen())
    start = time.time()
    value = _minimax(board, depth, -INF, INF, board.turn == chess.WHITE,
                     root, stats, use_pruning, 0)
    stats.time = time.time() - start

    # Root children hold one score per legal move: the candidate table.
    candidates = sorted(
        ((child.san, child.value) for child in root.children
         if child.value is not None),
        key=lambda item: item[1],
        reverse=(board.turn == chess.WHITE),
    )
    if not candidates:
        # Game already over (mate / stalemate): no move to return.
        return {"move": None, "san": None, "value": value, "tree": root,
                "stats": stats, "candidates": [], "pv": []}
    # The best move is the first candidate; the principal variation is the
    # best line: follow each node's best child down to a leaf.
    move = None
    for legal in board.legal_moves:
        if board.san(legal) == candidates[0][0]:
            move = legal
            break
    pv = _principal_variation(root)
    return {
        "move": move,
        "san": candidates[0][0] if candidates else None,
        "value": value,
        "tree": root,
        "stats": stats,
        "candidates": candidates,
        "pv": pv,
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


def compare(board, depth):
    """Run the same position twice, once plain minimax and once with
    alpha-beta pruning. Both must pick the same move and score -- pruning
    only skips work, it never changes the answer. Returns both reports."""
    plain = best_move(board, depth, use_pruning=False)
    pruned = best_move(board, depth, use_pruning=True)
    return {"plain": plain, "pruned": pruned}
