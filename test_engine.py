"""Headless checks for engine.py. Run:  python test_engine.py"""

import chess

import engine

FAILURES = []


def check(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name} {detail}")
    if not condition:
        FAILURES.append(name)


# 1. Start position is exactly even (symmetric material + tables).
board = chess.Board()
check("start position evaluates to 0", engine.evaluate(board) == 0,
      f"got {engine.evaluate(board)}")

# 2. Being a queen up is good for the side that has it.
board = chess.Board("4k3/8/8/8/8/8/8/3QK3 w - - 0 1")
check("queen up is positive", engine.evaluate(board) > 800,
      f"got {engine.evaluate(board)}")

# 3. Pruning never changes the answer: same move and value, fewer nodes.
positions = {
    "start": chess.Board(),
    "middlegame": chess.Board(
        "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1"),
    "endgame": chess.Board("8/5k2/3p4/1p1Pp2p/pP2Pp1P/P4P1K/8/8 b - - 0 1"),
}
for name, pos in positions.items():
    result = engine.compare(pos, 3)
    plain, pruned = result["plain"], result["pruned"]
    check(f"{name}: pruning keeps best move",
          plain["san"] == pruned["san"],
          f"plain={plain['san']} pruned={pruned['san']}")
    check(f"{name}: pruning keeps value",
          plain["value"] == pruned["value"],
          f"plain={plain['value']} pruned={pruned['value']}")
    check(f"{name}: pruning searches fewer nodes",
          pruned["stats"].nodes < plain["stats"].nodes,
          f"plain={plain['stats'].nodes} pruned={pruned['stats'].nodes}")
    check(f"{name}: pruning records pruned branches",
          pruned["stats"].pruned > 0,
          f"pruned={pruned['stats'].pruned}")
    check(f"{name}: best move is legal",
          pruned["move"] in pos.legal_moves)
    check(f"{name}: principal variation is non-empty",
          len(pruned["pv"]) > 0, f"pv={pruned['pv']}")

# 4. Mate in 1: Scholar's mate Qxf7#.
board = chess.Board(
    "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
report = engine.best_move(board, 3, use_pruning=True)
check("mate in 1 found", report["san"] == "Qxf7#", f"got {report['san']}")
board.push(report["move"])
check("mate in 1 is checkmate", board.is_checkmate())

# 5. A short AI-vs-AI game runs cleanly and the tree is recorded.
board = chess.Board()
for _ in range(10):
    if board.is_game_over():
        break
    report = engine.best_move(board, 2, use_pruning=True)
    assert report["move"] is not None
    assert report["tree"].children, "tree has no children"
    board.push(report["move"])
check("10-ply AI game completes", len(board.move_stack) == 10,
      f"plies={len(board.move_stack)}")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURES: {FAILURES}")
    raise SystemExit(1)
print("All engine checks passed.")
