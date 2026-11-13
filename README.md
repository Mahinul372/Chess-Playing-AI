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
- **You: White (switch)** shows the side you play now; click it to switch.
  **AI vs AI** cycles off → even → White +1 → Black +1. Even games
  between identical engines end in draws, so the +1 handicap makes one
  side search a level deeper (and the other a level shallower) — that is
  what makes a winner possible. A game that reaches 200 moves with no
  result ends in a draw.
- The AI does not play the same game twice: at each turn it picks at
  random from the moves within 0.3 of the best, so openings vary from
  game to game. A forced mate is always played at once, never varied away.
- **Depth** (2–4) sets how many moves ahead the AI searches. Deeper is
  stronger but slower. Plain Minimax is capped at depth 3 — depth 4
  without pruning takes about 30 seconds a move. **Alpha-Beta / Minimax**
  switches the search mode.
- When a game starts, a card over the board says which side you are
  playing — "YOU are playing as White" (you move first) or "YOU are
  playing as Black" (the AI opens the game). It disappears once the game
  is under way.
- Captured pieces show on the right as they fall — the piece in its own
  colour, with a line like "Your Queen is eliminated" (or "AI's Queen is
  eliminated" when you take one). En passant counts as a capture too.
- When the game ends, a **GAME OVER!** banner says why — checkmate,
  stalemate, too few pieces to mate, the same position three times, 50
  moves with no capture and no pawn move, or 200 moves with no result.
  The AI never shuffles the same pieces forever: a move that repeats a
  position is penalised, and a mating move is never delayed by that penalty.

## What the AI shows you

After each AI move, the right panel shows its best move, the position
score, search depth, positions searched, branches pruned, time taken, the
best line it expects, and its top 5 candidate moves.

**How the AI thinks** — the four cards under the board — is a 2-minute
lesson in plain words: 1) look ahead, 2) score the board, 3) expect the
worst (Minimax), 4) skip the hopeless (Alpha-Beta pruning). The line
under the cards always shows what the AI just did in your game — how many
positions it looked at, how many branches it skipped, and one branch it
skipped as an example.

**See search tree** opens the real tree from that move, laid out so it
reads: each parent sits centred over its children, rows are spread down
the screen, and the left gutter says whose turn each row is. Labels
appear only where they fit — on a crowded row they alternate above and
below the nodes — and clicking any node shows its move, score, alpha and
beta in the strip below, with the board behind it:

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
| `app.py`          | The game: board, controls, tree view, lesson, GAME OVER |
| `engine.py`       | Evaluation, Minimax, Alpha-Beta, and the recorded tree  |
| `test_engine.py`  | Headless checks: pruning, mate in 1, repetition, draws  |
| `assets/pieces.png`| Piece artwork (one sprite sheet, 12 pieces)            |
| `requirements.txt`| `python-chess` (rules) and `pygame` (interface)         |
| `LICENSE`         | GNU GPLv3 licence text                                  |

Piece artwork: the Cburnett chess set (Wikimedia Commons, GFDL / BSD /
GPL). If `assets/pieces.png` is missing, the game falls back to text
glyphs for the pieces.

## License

GNU General Public License v3.0 — see [LICENSE](LICENSE).
