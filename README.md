# Chess-Playing-AI

Play real chess against an AI — and watch it think. Every AI move comes
with the actual search behind it: the moves it considered, their scores,
and the branches it pruned. Built to make Minimax and Alpha-Beta pruning
understandable, not just to win games.

## Run

```bash
pip install -r requirements.txt
python app.py
```

## Play

- Click one of your pieces, then click a highlighted square to move.
  All chess rules apply: castling, en passant, check, checkmate, stalemate.
  Pawn promotion is auto-queen.
- **New game** restarts. **Undo** takes back your last move and the AI's reply.
- **Play as** switches sides. **AI vs AI** lets the two sides play each other.
- **Depth** (2–4) sets how many moves ahead the AI searches. Deeper is
  stronger but slower. Plain Minimax is capped at depth 3 — depth 4
  without pruning takes about 30 seconds a move. **Alpha-Beta / Minimax**
  switches the search mode.

## What the AI shows you

After each AI move, the right panel shows its best move, the position
score, search depth, positions searched, branches pruned, time taken, the
best line it expects, and its top 5 candidate moves.

**See search tree** opens the real tree from that move:

- Green node — White to move (MAX). Blue node — Black to move (MIN).
- Red node — pruned: the AI skipped this branch.
- Gold ring — the best line (principal variation).
- Click a node to expand it and see the board behind it. **Replay search**
  shows the nodes in the order the AI visited them.

**Compare both** runs the same position twice — plain Minimax, then
Alpha-Beta — and reports nodes searched and time for each.

## How Minimax works

The AI tries every legal move, then assumes the opponent answers with
their best move, and so on to the search depth. Each end position gets a
score (see below). White picks the move with the highest score, Black the
lowest. That is the whole idea: maximise your own outcome while the
opponent minimises it.

## How Alpha-Beta pruning works

While searching, the AI tracks two numbers. **Alpha** is the best score
White can already guarantee; **beta** is the best score Black can already
guarantee. If a branch cannot beat the best move already found, the rest
of that branch is skipped — it cannot change the decision. Pruning finds
the exact same best move as plain Minimax while searching far fewer
positions. The tree shows the skipped branches in red.

## How positions are scored

Material plus piece placement, in centipawns (100 = one pawn), from
White's point of view. Positive favours White, negative favours Black.

| Piece  | Pawn | Knight | Bishop | Rook | Queen |
| ------ | ---- | ------ | ------ | ---- | ----- |
| Value  | 100  | 320    | 330    | 500  | 900   |

Piece-square tables add small bonuses for good squares (advanced pawns,
central knights, a safe king). Checkmate scores as a forced win or loss,
with faster mates preferred. The score is an estimate, not a guarantee.

## Files

| File              | What it is                                              |
| ----------------- | ------------------------------------------------------- |
| `app.py`          | The game: board, controls, tree view, explanations      |
| `engine.py`       | Evaluation, Minimax, Alpha-Beta, and the recorded tree  |
| `requirements.txt`| `python-chess` (rules) and `pygame` (interface)         |

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).
