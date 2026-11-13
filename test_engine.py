"""Headless checks for engine.py. Run:  python test_engine.py"""

from collections import Counter

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

# 6. The AI does not loop: repeating a position is penalised, and a
# forced mate still beats the penalty.
check("repetition penalty: unseen = 0", engine.repetition_penalty(0) == 0)
check("repetition penalty: seen once = 30",
      engine.repetition_penalty(1) == 30)
check("repetition penalty: seen twice = 500",
      engine.repetition_penalty(2) == 500)

board = chess.Board()
raw = engine.best_move(board, 2, use_pruning=True)
raw_san = raw["san"]
move = board.parse_san(raw_san)
board.push(move)
seen_key = engine.position_key(board)
board.pop()
report = engine.best_move(board, 2, use_pruning=True,
                          history_keys=Counter({seen_key: 2}))
check("AI avoids a move that would repeat a position twice",
      report["san"] != raw_san,
      f"raw best {raw_san}, with history chose {report['san']}")
check("avoided_repetition is reported",
      report["avoided_repetition"] is True)
check("choice with history is still legal",
      report["move"] in board.legal_moves)
check("choice with history still has a best line",
      len(report["pv"]) > 0 and report["pv"][0] == report["san"],
      f"pv={report['pv']}")

# A mate in 1 still wins even if the mating move repeats a position:
# the mate score (100000) dwarfs the repetition penalty (500).
board = chess.Board(
    "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
mate_move = board.parse_san("Qxf7#")
board.push(mate_move)
mate_key = engine.position_key(board)
board.pop()
report = engine.best_move(board, 3, use_pruning=True,
                          history_keys=Counter({mate_key: 2}))
check("mate still beats the repetition penalty",
      report["san"] == "Qxf7#", f"got {report['san']}")

# 7. Game-over reasons: the banner always knows why the game ended.
check("reason: start position is not over",
      engine.game_over_reason(chess.Board()) is None)
board = chess.Board(
    "rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
reason = engine.game_over_reason(board)
check("reason: fool's mate is checkmate",
      reason is not None and "Checkmate" in reason["headline"],
      f"got {reason}")
board = chess.Board("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
reason = engine.game_over_reason(board)
check("reason: stalemate is a draw",
      reason is not None and "Stalemate" in reason["headline"],
      f"got {reason}")
board = chess.Board("8/8/4k3/8/8/4K3/8/8 w - - 0 1")
reason = engine.game_over_reason(board)
check("reason: king vs king is insufficient material",
      reason is not None and "not enough pieces" in reason["headline"],
      f"got {reason}")
board = chess.Board()
for san in ["Nf3", "Nf6", "Ng1", "Ng8", "Nf3", "Nf6", "Ng1", "Ng8"]:
    board.push_san(san)
check("knight shuffle really repeats the start three times",
      board.is_repetition(3))
reason = engine.game_over_reason(board)
check("reason: threefold repetition is a draw",
      reason is not None and "three times" in reason["headline"],
      f"got {reason}")
board = chess.Board("4k3/8/8/8/8/8/8/4K2R w K - 100 60")
reason = engine.game_over_reason(board)
check("reason: 50 moves without progress is a draw",
      reason is not None and "50 moves" in reason["headline"],
      f"got {reason}")

# 8. Random play: the AI varies its moves instead of repeating the same
# game every time, but a forced mate is always played at once, and the
# plain-vs-pruned comparison stays deterministic.
import random

board = chess.Board()
first = engine.best_move(board, 2, randomize=False)
check("no randomisation by default is deterministic",
      engine.best_move(board, 2, randomize=False)["san"] == first["san"])
picks = set()
for seed in range(12):
    random.seed(seed)
    report = engine.best_move(board, 2, randomize=True)
    picks.add(report["san"])
    best_score = max(score for _, score in report["candidates"])
    chosen = next(sc for san, sc in report["candidates"]
                  if san == report["san"])
    check(f"random pick within 0.3 of best (seed {seed})",
          abs(chosen - best_score) <= engine.RANDOM_THRESHOLD,
          f"chose {report['san']} {chosen} vs best {best_score}")
check("random play varies the opening", len(picks) > 1, f"picks: {picks}")
# Mate in 1 is never randomised away.
board = chess.Board(
    "r1bqkbnr/pppp1ppp/2n5/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 0 1")
for seed in range(6):
    random.seed(seed)
    report = engine.best_move(board, 2, randomize=True)
    check(f"mate in 1 still played (seed {seed})",
          report["san"] == "Qxf7#", f"got {report['san']}")
# Compare stays deterministic and the two searches agree.
board = chess.Board()
result = engine.compare(board, 2)
check("compare: plain and pruned pick the same move",
      result["plain"]["san"] == result["pruned"]["san"],
      f"{result['plain']['san']} vs {result['pruned']['san']}")

print()
if FAILURES:
    print(f"{len(FAILURES)} FAILURES: {FAILURES}")
    raise SystemExit(1)
print("All engine checks passed.")
