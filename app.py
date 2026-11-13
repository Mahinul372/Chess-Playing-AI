"""Chess AI you can play against -- and watch think.

Play real chess against an AI that searches with Minimax and Alpha-Beta
pruning. After every AI move, open the search tree to see the actual moves
the AI considered, the score of each, and the branches it pruned -- with
plain-language explanations of what the algorithm is doing.

The "How the AI thinks" panel under the board is a 2-minute lesson in four
cards: look ahead, score the board, expect the worst (Minimax), skip the
hopeless (Alpha-Beta pruning). The line under it always shows what the AI
just did in your game.

The AI never loops: a move that repeats a position already seen in this
game is penalised, and the game ends in a draw at once on threefold
repetition, fifty moves without progress, or too few pieces to mate.

Run:  python app.py
"""

import collections
import os
import sys
import time

import chess
import pygame

import engine

# ---------------------------------------------------------------- window
WIDTH, HEIGHT = 1280, 860
BOARD = 560
SQ = BOARD // 8
BOARD_X, BOARD_Y = 24, 24
PANEL_X = 608
PANEL_W = 648
LESSON_Y = 600

LIGHT_SQ = (240, 217, 181)
DARK_SQ = (181, 136, 99)
BG_TOP = (30, 41, 59)
BG_BOTTOM = (15, 23, 42)
CARD = (30, 41, 59)
CARD_BORDER = (71, 85, 105)
BTN = (51, 65, 85)
BTN_HOVER = (71, 85, 105)
INK = (241, 245, 249)
MUTED = (148, 163, 184)
ACCENT = (212, 175, 55)      # gold: buttons, best line, highlights
GOLD = (212, 175, 55)
GOLD_LIGHT = (253, 230, 138)
GREEN = (46, 200, 90)        # MAX node / explored
BLUE = (96, 165, 250)        # MIN node
RED = (248, 113, 113)        # pruned node
GREY = (148, 163, 184)       # not yet revealed
LAST_MOVE = (205, 210, 110)
CHECK = (220, 80, 80)

WHITE_GLYPHS = {chess.KING: "♔", chess.QUEEN: "♕", chess.ROOK: "♖",
                chess.BISHOP: "♗", chess.KNIGHT: "♘", chess.PAWN: "♙"}
BLACK_GLYPHS = {chess.KING: "♚", chess.QUEEN: "♛", chess.ROOK: "♜",
                chess.BISHOP: "♝", chess.KNIGHT: "♞", chess.PAWN: "♟"}
LETTERS = {chess.KING: "K", chess.QUEEN: "Q", chess.ROOK: "R",
           chess.BISHOP: "B", chess.KNIGHT: "N", chess.PAWN: "P"}

# The lesson: four cards that teach Minimax and Alpha-Beta pruning while
# you play. Each card is one idea, in plain words, no jargon up front.
LESSONS = [
    ("1", "Look ahead",
     "The AI tries every legal move, then every reply, down to the depth "
     "you set. Depth 3 means thousands of positions from a single move."),
    ("2", "Score the board",
     "Every position gets a number. Queen 9, rook 5, knight and bishop 3. "
     "Good squares add a little. White wants it high, Black wants it low."),
    ("3", "Expect the worst",
     "White picks the highest score, Black the lowest. Each side expects "
     "the other's best reply. That is Minimax."),
    ("4", "Skip the hopeless",
     "Alpha-Beta pruning: once a move is proven worse than one you already "
     "have, the AI stops there. Same answer, far less work."),
]


PIECE_NAMES = {chess.KING: "King", chess.QUEEN: "Queen", chess.ROOK: "Rook",
               chess.BISHOP: "Bishop", chess.KNIGHT: "Knight", chess.PAWN: "Pawn"}


def captured_piece(board, move):
    """The piece `move` captures, or None. En passant takes the pawn on
    the square behind, not the square the pawn lands on."""
    if not board.is_capture(move):
        return None
    if board.is_en_passant(move):
        square = chess.square(chess.square_file(move.to_square),
                              chess.square_rank(move.from_square))
        return board.piece_at(square)
    return board.piece_at(move.to_square)


def load_piece_sheet():
    """The Cburnett piece set as one sprite sheet (assets/pieces.png:
    6 columns K Q R B N P, row 0 white, row 1 black), or None if the
    file is missing -- then the game falls back to text glyphs."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "assets", "pieces.png")
    if not os.path.exists(path):
        return None
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        return None


SHEET_COLS = {chess.KING: 0, chess.QUEEN: 1, chess.ROOK: 2,
              chess.BISHOP: 3, chess.KNIGHT: 4, chess.PAWN: 5}


def load_piece_font(size):
    """A font with real chess glyphs, or None (fall back to letters)."""
    import os
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/seguisym.ttf",
        "C:/Windows/Fonts/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except Exception:
                pass
    for name in ("Segoe UI Symbol", "DejaVu Sans", "Noto Sans Symbols 2"):
        try:
            return pygame.font.SysFont(name, size)
        except Exception:
            pass
    return None


def pick_font(names, size, bold=False):
    """First available text font from `names`, else pygame's default."""
    for name in names:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            pass
    return pygame.font.Font(None, size)


def wrap_text(text, font, width):
    """Split text into lines that fit `width` pixels."""
    lines = []
    for paragraph in text.split("\n"):
        words = paragraph.split()
        line = ""
        for word in words:
            test = f"{line} {word}".strip()
            if font.size(test)[0] <= width:
                line = test
            else:
                if line:
                    lines.append(line)
                line = word
        if line:
            lines.append(line)
    return lines


class Button:
    def __init__(self, rect, label, action):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action

    def draw(self, surface, font, hover=False):
        pygame.draw.rect(surface, BTN_HOVER if hover else BTN, self.rect,
                         border_radius=8)
        pygame.draw.rect(surface, ACCENT, self.rect, 2, border_radius=8)
        text = font.render(self.label, True, INK)
        surface.blit(text, text.get_rect(center=self.rect.center))

    def click(self, pos):
        if self.rect.collidepoint(pos):
            self.action()
            return True
        return False


class App:
    def __init__(self):
        pygame.init()
        pygame.font.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Chess AI — Minimax & Alpha-Beta, shown live")
        self.clock = pygame.time.Clock()

        text_names = ["Segoe UI", "DejaVu Sans", "Liberation Sans", "Arial"]
        self.font = pick_font(text_names, 17)
        self.small = pick_font(text_names, 14)
        self.coord_font = pick_font(text_names, 13, bold=True)
        self.title_font = pick_font(text_names, 22, bold=True)
        self.card_head_font = pick_font(text_names, 18, bold=True)
        self.card_font = pick_font(text_names, 16)
        self.banner_font = pick_font(text_names, 54, bold=True)
        self.banner_title_font = pick_font(text_names, 30, bold=True)
        self.piece_font = load_piece_font(52)
        self.piece_font_med = load_piece_font(16)
        self.mini_piece_font = load_piece_font(13)
        self.use_glyphs = self.piece_font is not None
        if not self.use_glyphs:
            self.piece_font = pick_font(text_names, 40, bold=True)
            self.piece_font_med = pick_font(text_names, 14, bold=True)
            self.mini_piece_font = pick_font(text_names, 11, bold=True)
        self.piece_sheet = load_piece_sheet()
        self.piece_big = self.build_piece_surfaces(self.piece_font, SQ)
        self.piece_med = self.build_piece_surfaces(self.piece_font_med, 22)
        self.piece_small = self.build_piece_surfaces(self.mini_piece_font, 14)
        self.tile_light = self.build_tile(LIGHT_SQ)
        self.tile_dark = self.build_tile(DARK_SQ)
        self.last_move_tint = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
        self.last_move_tint.fill((205, 210, 110, 120))
        self.board_shadow = pygame.Surface((BOARD + 28, BOARD + 28),
                                           pygame.SRCALPHA)
        pygame.draw.rect(self.board_shadow, (0, 0, 0, 110),
                         self.board_shadow.get_rect(), border_radius=12)

        # One-time vertical gradient for the window background.
        self.bg = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            t = y / max(1, HEIGHT - 1)
            color = tuple(int(BG_TOP[i] + (BG_BOTTOM[i] - BG_TOP[i]) * t)
                          for i in range(3))
            pygame.draw.line(self.bg, color, (0, y), (WIDTH, y))

        self.new_game()

    def build_piece_surfaces(self, font, size):
        """Render each piece once, so drawing the board is just blitting.
        Real artwork from the sprite sheet when it loaded, else text
        glyphs with an outline and a soft shadow underneath."""
        if self.piece_sheet is not None:
            return self.build_sheet_surfaces(size)
        surfaces = {}
        edge_px = 2 if size >= 50 else 1
        for color in (chess.WHITE, chess.BLACK):
            for piece_type in range(1, 7):
                glyph = (WHITE_GLYPHS if self.use_glyphs else LETTERS)[piece_type] \
                    if color == chess.WHITE else \
                    (BLACK_GLYPHS if self.use_glyphs else LETTERS)[piece_type]
                surf = pygame.Surface((size, size), pygame.SRCALPHA)
                pygame.draw.ellipse(
                    surf, (0, 0, 0, 80),
                    (size * 0.16, size * 0.80, size * 0.68, size * 0.14))
                edge = (30, 30, 30) if color == chess.WHITE else (240, 240, 240)
                fill = (250, 250, 250) if color == chess.WHITE else (20, 20, 20)
                for dx in (-edge_px, 0, edge_px):
                    for dy in (-edge_px, 0, edge_px):
                        if dx == 0 and dy == 0:
                            continue
                        edge_surf = font.render(glyph, True, edge)
                        surf.blit(edge_surf, edge_surf.get_rect(
                            center=(size // 2 + dx, size // 2 + dy)))
                fill_surf = font.render(glyph, True, fill)
                surf.blit(fill_surf, fill_surf.get_rect(
                    center=(size // 2, size // 2)))
                surfaces[(color, piece_type)] = surf
        return surfaces

    def build_sheet_surfaces(self, size):
        """Cut the 12 pieces out of the sprite sheet and scale each to
        `size`. The artwork already has its own shading and base."""
        surfaces = {}
        cell = self.piece_sheet.get_width() // 6
        for color in (chess.WHITE, chess.BLACK):
            row = 0 if color == chess.WHITE else 1
            for piece_type in range(1, 7):
                col = SHEET_COLS[piece_type]
                region = self.piece_sheet.subsurface(
                    (col * cell, row * cell, cell, cell))
                surfaces[(color, piece_type)] = pygame.transform.smoothscale(
                    region, (size, size))
        return surfaces

    def build_tile(self, color):
        """One board square with a soft vertical gradient, so the board
        reads as a surface instead of flat colour."""
        tile = pygame.Surface((SQ, SQ))
        top = tuple(min(255, c + 14) for c in color)
        bottom = tuple(max(0, c - 14) for c in color)
        for y in range(SQ):
            t = y / max(1, SQ - 1)
            shade = tuple(int(top[i] + (bottom[i] - top[i]) * t)
                          for i in range(3))
            pygame.draw.line(tile, shade, (0, y), (SQ, y))
        return tile

    # ------------------------------------------------------------ state
    def new_game(self):
        self.board = chess.Board()
        self.human_color = chess.WHITE
        self.ai_depth = 3
        self.use_pruning = True
        self.ai_vs_ai = False
        self.handicap = "even"  # AI vs AI: "even", "white" or "black" deeper
        self.selected = None
        self.targets = []
        self.last_move = None
        self.ai_report = None
        self.compare_text = None
        self.ai_pending = False
        self.next_ai_time = 0
        self.live_example = (
            "Play a move — what the AI looks at, and what it skips, "
            "will appear here."
        )
        self.avoided_repetition = False
        self.game_over_info = None
        self.eliminated = []
        self.hover_square = None
        self.hover_pos = None
        self.rebuild_history()
        self.screen_name = "play"
        self.tree = None
        self.expanded = set()
        self.selected_node = None
        self.revealed = 0
        self.replay = False

    def rebuild_history(self):
        """Count how many times each position has occurred in this game,
        so the AI can avoid repeating one, and rebuild the list of
        captured pieces. Used after undo too."""
        self.history_keys = collections.Counter()
        self.eliminated = []
        replay = chess.Board()
        self.history_keys[engine.position_key(replay)] += 1
        for move in self.board.move_stack:
            piece = captured_piece(replay, move)
            if piece is not None:
                self.eliminated.append((piece.color, piece.piece_type))
            replay.push(move)
            self.history_keys[engine.position_key(replay)] += 1
        self.game_over_info = engine.game_over_reason(self.board)

    def record_capture(self, move):
        """Note a capture before the move is pushed, for the Eliminated
        list on the right panel."""
        piece = captured_piece(self.board, move)
        if piece is not None:
            self.eliminated.append((piece.color, piece.piece_type))

    def eliminated_text(self, color, piece_type):
        if self.ai_vs_ai:
            who = "White" if color == chess.WHITE else "Black"
        elif color == self.human_color:
            who = "Your"
        else:
            who = "AI's"
        return f"{who} {PIECE_NAMES[piece_type]} is eliminated"

    # ------------------------------------------------------------ game
    def human_move(self, move):
        self.record_capture(move)
        san = self.board.san(move)
        self.board.push(move)
        self.last_move = (move.from_square, move.to_square)
        self.selected = None
        self.targets = []
        self.after_move(san)

    def ai_move(self):
        self.ai_pending = False
        depth = self.ai_depth_for(self.board.turn)
        report = engine.best_move(self.board, depth, self.use_pruning,
                                  history_keys=self.history_keys,
                                  randomize=True)
        if report["move"] is None:
            return
        san = report["san"]
        self.record_capture(report["move"])
        self.board.push(report["move"])
        self.last_move = (report["move"].from_square, report["move"].to_square)
        self.ai_report = report
        self.tree = report["tree"]
        self.expanded = {id(self.tree)}
        self.selected_node = self.tree
        self.revealed = 10 ** 9  # tree screen reveals everything by default
        self.replay = False
        self.avoided_repetition = report.get("avoided_repetition", False)
        self.live_example = self.explain_after_search(report)
        self.after_move(san)

    def after_move(self, san):
        self.history_keys[engine.position_key(self.board)] += 1
        self.game_over_info = engine.game_over_reason(self.board)
        if self.game_over_info is not None:
            # Game over: nobody moves again, whatever was pending.
            self.ai_pending = False
            return
        if self.ai_vs_ai:
            self.next_ai_time = pygame.time.get_ticks() + 700
        elif self.board.turn != self.human_color:
            self.ai_pending = True
            # A short beat so your move lands before the AI answers.
            self.next_ai_time = pygame.time.get_ticks() + 350

    def explain_after_search(self, report):
        """One live line about what the AI just did in this game -- the
        concrete example for lesson card 4."""
        stats = report["stats"]
        best = report["san"]
        score = engine.format_score(report["value"])
        if self.use_pruning:
            text = (
                f"Just now: Alpha-Beta looked at {stats.nodes} positions and "
                f"skipped {stats.pruned} branches that could not change its "
                f"mind. Best move {best} ({score})."
            )
            example = self.cutoff_example(report["tree"])
            if example:
                text += f" {example}"
        else:
            text = (
                f"Just now: plain Minimax looked at every branch, "
                f"{stats.nodes} positions in {stats.time:.2f}s. Best move "
                f"{best} ({score}). Turn pruning on to see how much of this "
                f"work can be skipped."
            )
        if self.avoided_repetition:
            text += (" It also skipped a move that would have repeated a "
                     "position — repeating moves wins nothing.")
        return text

    def cutoff_example(self, tree):
        """One concrete pruned branch, in plain words. A cutoff means the
        branch could not change the AI's decision, so it was never searched."""
        for child in tree.children:
            for grand in child.children:
                if grand.pruned:
                    return (
                        f"For example, after {child.san} the move {grand.san} "
                        f"was never searched: the AI had already found a "
                        f"better option elsewhere."
                    )
        for child in tree.children:
            if child.pruned:
                return (
                    f"For example, the move {child.san} was never searched: "
                    f"the AI had already found a better option elsewhere."
                )
        return ""

    def run_compare(self):
        if self.board.is_game_over() or self.game_over_info is not None:
            return
        depth = min(self.ai_depth, 3)
        result = engine.compare(self.board, depth,
                                history_keys=self.history_keys)
        plain = result["plain"]
        pruned = result["pruned"]
        plain_nodes = plain["stats"].nodes
        pruned_nodes = pruned["stats"].nodes
        saved = 100 * (plain_nodes - pruned_nodes) / plain_nodes if plain_nodes else 0
        same = plain["san"] == pruned["san"]
        self.compare_text = (
            f"Same position, depth {depth}: plain Minimax searched "
            f"{plain_nodes} nodes in {plain['stats'].time:.2f}s; Alpha-Beta "
            f"searched {pruned_nodes} nodes in {pruned['stats'].time:.2f}s "
            f"({saved:.0f}% fewer). Same best move: {pruned['san']} "
            f"({'yes' if same else 'NO -- check the engine'})."
        )

    # ------------------------------------------------------------ input
    def square_at(self, pos):
        x, y = pos
        if BOARD_X <= x < BOARD_X + BOARD and BOARD_Y <= y < BOARD_Y + BOARD:
            return chess.square((x - BOARD_X) // SQ, 7 - (y - BOARD_Y) // SQ)
        return None

    def handle_play_click(self, pos):
        if self.ai_vs_ai or self.game_over_info is not None:
            return
        if self.board.turn != self.human_color:
            return
        square = self.square_at(pos)
        if square is None:
            return
        piece = self.board.piece_at(square)
        if self.selected is not None:
            for move in self.targets:
                if move.to_square == square:
                    self.human_move(move)
                    return
            self.selected = None
            self.targets = []
        if piece is not None and piece.color == self.board.turn:
            self.selected = square
            self.targets = [m for m in self.board.legal_moves
                            if m.from_square == square]

    # ------------------------------------------------------------ drawing
    def draw_piece(self, surface, piece, cx, cy, size):
        surfaces = self.piece_big if size >= 50 else self.piece_small
        surf = surfaces[(piece.color, piece.piece_type)]
        surface.blit(surf, surf.get_rect(center=(cx, cy)))

    def draw_board(self, surface, board, x, y, sq):
        is_main = board is self.board
        for rank in range(8):
            for file in range(8):
                square = chess.square(file, rank)
                px = x + file * sq
                py = y + (7 - rank) * sq
                if sq >= 50:
                    tile = self.tile_light if (file + rank) % 2 \
                        else self.tile_dark
                    surface.blit(tile, (px, py))
                else:
                    color = LIGHT_SQ if (file + rank) % 2 else DARK_SQ
                    pygame.draw.rect(surface, color, (px, py, sq, sq))
                if is_main and self.last_move and square in self.last_move:
                    surface.blit(self.last_move_tint, (px, py))
                piece = board.piece_at(square)
                if piece:
                    self.draw_piece(surface, piece, px + sq // 2,
                                    py + sq // 2, sq)
        # coordinates on the edge squares, in the opposite shade
        if sq >= 50:
            for file in range(8):
                square = chess.square(file, 0)
                dark = (file + 0) % 2 == 0
                label = self.coord_font.render(chess.FILE_NAMES[file], True,
                                               DARK_SQ if dark else LIGHT_SQ)
                surface.blit(label, (x + file * sq + sq - 13, y + BOARD - 16))
            for rank in range(8):
                square = chess.square(0, rank)
                dark = (0 + rank) % 2 == 0
                label = self.coord_font.render(str(rank + 1), True,
                                               DARK_SQ if dark else LIGHT_SQ)
                surface.blit(label, (x + 3, y + (7 - rank) * sq + 3))
        # hover tint on a square you could move from
        if is_main and self.hover_square is not None:
            piece = board.piece_at(self.hover_square)
            if piece is not None and piece.color == board.turn:
                hx = x + chess.square_file(self.hover_square) * sq
                hy = y + (7 - chess.square_rank(self.hover_square)) * sq
                tint = pygame.Surface((sq, sq), pygame.SRCALPHA)
                tint.fill((212, 175, 55, 60))
                surface.blit(tint, (hx, hy))
        # check highlight
        if board.is_check():
            king = board.king(board.turn)
            px = x + chess.square_file(king) * sq
            py = y + (7 - chess.square_rank(king)) * sq
            pygame.draw.rect(surface, CHECK, (px, py, sq, sq), 4)
        # selected square + legal-move dots (ring for captures)
        if is_main and self.selected is not None:
            px = x + chess.square_file(self.selected) * sq
            py = y + (7 - chess.square_rank(self.selected)) * sq
            pygame.draw.rect(surface, GOLD, (px, py, sq, sq), 3)
            for move in self.targets:
                tx = x + chess.square_file(move.to_square) * sq + sq // 2
                ty = y + (7 - chess.square_rank(move.to_square)) * sq + sq // 2
                if board.piece_at(move.to_square) is not None:
                    pygame.draw.circle(surface, GOLD, (tx, ty), 26, 4)
                else:
                    dot = pygame.Surface((sq, sq), pygame.SRCALPHA)
                    pygame.draw.circle(dot, (20, 20, 20, 110),
                                       (sq // 2, sq // 2), 10)
                    surface.blit(dot, (tx - sq // 2, ty - sq // 2))

    def draw_text_block(self, surface, text, font, x, y, width, color=INK):
        for line in wrap_text(text, font, width):
            surface.blit(font.render(line, True, color), (x, y))
            y += font.get_linesize()
        return y

    def status_text(self):
        if self.game_over_info is not None:
            return (f"{self.game_over_info['headline']} "
                    f"({self.game_over_info['result']})")
        if self.board.is_checkmate():
            winner = "Black" if self.board.turn == chess.WHITE else "White"
            return f"Checkmate — {winner} wins ({self.board.result()})"
        if self.board.is_stalemate():
            return "Stalemate — draw (1/2-1/2)"
        if self.board.is_insufficient_material():
            return "Draw — insufficient material (1/2-1/2)"
        if self.board.is_game_over():
            return f"Game over ({self.board.result()})"
        turn = "White" if self.board.turn == chess.WHITE else "Black"
        check = " — check!" if self.board.is_check() else ""
        if self.ai_pending:
            return f"{turn} to move — AI thinking…{check}"
        if self.board.turn == self.human_color and not self.ai_vs_ai:
            return f"Your move ({turn}){check}"
        return f"{turn} to move{check}"

    def draw_game_over(self):
        """A big GAME OVER banner across the board, so it is obvious the
        game has ended -- and why -- instead of the pieces just freezing."""
        if self.game_over_info is None:
            return
        overlay = pygame.Surface((BOARD, BOARD), pygame.SRCALPHA)
        overlay.fill((10, 15, 25, 190))
        self.screen.blit(overlay, (BOARD_X, BOARD_Y))
        pygame.draw.rect(self.screen, GOLD,
                         (BOARD_X, BOARD_Y, BOARD, BOARD), 4)
        cx = BOARD_X + BOARD // 2
        title = self.banner_font.render("GAME OVER!", True, GOLD)
        self.screen.blit(title, title.get_rect(center=(cx, BOARD_Y + 190)))
        info = self.game_over_info
        head = self.title_font.render(info["headline"], True, INK)
        self.screen.blit(head, head.get_rect(center=(cx, BOARD_Y + 260)))
        y = BOARD_Y + 300
        y = self.draw_text_block(self.screen, info["detail"], self.font,
                                 BOARD_X + 70, y, BOARD - 140, MUTED)
        hint = self.font.render("Press New game to play again",
                                True, GOLD_LIGHT)
        self.screen.blit(hint, hint.get_rect(center=(cx, BOARD_Y + 400)))

    def start_banner_text(self):
        """What the start banner says, or None once the game is under way."""
        if self.board.move_stack:
            return None
        if self.ai_vs_ai:
            if self.handicap == "even":
                return ("AI vs AI",
                        "Watch the two sides play each other.")
            favoured = "White" if self.handicap == "white" else "Black"
            return ("AI vs AI",
                    f"{favoured} searches one level deeper — expect a winner.")
        if self.human_color == chess.WHITE:
            return ("YOU are playing as White",
                    "You move first — click one of your pieces to begin.")
        return ("YOU are playing as Black",
                "White moves first — the AI will open the game.")

    def draw_start_banner(self):
        """Before the first move, a card over the board says plainly which
        side you are playing, so there is no guessing."""
        text = self.start_banner_text()
        if text is None:
            return
        title, sub = text
        overlay = pygame.Surface((BOARD, BOARD), pygame.SRCALPHA)
        overlay.fill((10, 15, 25, 110))
        self.screen.blit(overlay, (BOARD_X, BOARD_Y))
        card_w, card_h = 470, 150
        cx = BOARD_X + BOARD // 2
        cy = BOARD_Y + BOARD // 2
        rect = pygame.Rect(cx - card_w // 2, cy - card_h // 2,
                           card_w, card_h)
        pygame.draw.rect(self.screen, CARD, rect, border_radius=12)
        pygame.draw.rect(self.screen, GOLD, rect, 2, border_radius=12)
        title_surf = self.banner_title_font.render(title, True, GOLD)
        self.screen.blit(title_surf, title_surf.get_rect(
            center=(cx, cy - 28)))
        sub_surf = self.font.render(sub, True, INK)
        self.screen.blit(sub_surf, sub_surf.get_rect(center=(cx, cy + 12)))
        hint = self.small.render("Change sides, depth or mode with the "
                                 "buttons on the right", True, MUTED)
        self.screen.blit(hint, hint.get_rect(center=(cx, cy + 44)))

    def draw_lesson(self):
        """The 2-minute lesson: four roomy cards, then the live line about
        what the AI just did in this game."""
        x0, y0 = BOARD_X, LESSON_Y
        title = self.title_font.render("How the AI thinks", True, GOLD)
        self.screen.blit(title, (x0, y0))
        sub = self.font.render("— the 2-minute lesson, learned by playing",
                               True, MUTED)
        self.screen.blit(sub, (x0 + title.get_width() + 10, y0 + 4))
        card_w, card_h, gap = 296, 148, 12
        y = y0 + 32
        for i, (num, head, body) in enumerate(LESSONS):
            x = x0 + i * (card_w + gap)
            rect = pygame.Rect(x, y, card_w, card_h)
            pygame.draw.rect(self.screen, CARD, rect, border_radius=10)
            pygame.draw.rect(self.screen, CARD_BORDER, rect, 1,
                             border_radius=10)
            pygame.draw.circle(self.screen, GOLD, (x + 26, y + 28), 14)
            num_text = self.card_head_font.render(num, True, BG_BOTTOM)
            self.screen.blit(num_text, num_text.get_rect(
                center=(x + 26, y + 28)))
            head_text = self.card_head_font.render(head, True, INK)
            self.screen.blit(head_text, (x + 48, y + 15))
            self.draw_text_block(self.screen, body, self.card_font,
                                 x + 16, y + 52, card_w - 32, MUTED)
        live_y = y + card_h + 12
        live_lines = wrap_text(self.live_example, self.font,
                               WIDTH - 2 * BOARD_X)
        for line in live_lines:
            self.screen.blit(self.font.render(line, True, GOLD_LIGHT),
                             (x0, live_y))
            live_y += self.font.get_linesize()
        self.draw_text_block(
            self.screen,
            "Try it: press Compare both to race plain Minimax against "
            "Alpha-Beta on this exact position — same move, far fewer nodes.",
            self.small, x0, live_y + 6, WIDTH - 2 * BOARD_X, MUTED)

    # ------------------------------------------------------------ screens
    def draw_play(self):
        self.screen.blit(self.bg, (0, 0))
        # drop shadow + wooden frame around the board
        self.screen.blit(self.board_shadow, (BOARD_X - 8, BOARD_Y - 8))
        pygame.draw.rect(self.screen, (88, 60, 42),
                         (BOARD_X - 14, BOARD_Y - 14, BOARD + 28, BOARD + 28),
                         border_radius=10)
        pygame.draw.rect(self.screen, GOLD,
                         (BOARD_X - 4, BOARD_Y - 4, BOARD + 8, BOARD + 8), 2)
        self.draw_board(self.screen, self.board, BOARD_X, BOARD_Y, SQ)
        self.draw_start_banner()
        self.draw_game_over()

        # right panel: title, buttons, status, AI report, compare, moves
        x = PANEL_X
        self.screen.blit(self.title_font.render("Chess AI", True, GOLD),
                         (x, 24))
        for button in self.play_buttons():
            button.draw(self.screen, self.font,
                        hover=(self.hover_pos is not None
                               and button.rect.collidepoint(self.hover_pos)))
        y = 158
        y = self.draw_text_block(self.screen, self.status_text(), self.font,
                                 x, y, PANEL_W, INK) + 10
        # AI report card
        if self.ai_report:
            r = self.ai_report
            s = r["stats"]
            algo = "Alpha-Beta" if self.use_pruning else "Minimax"
            lines = [
                f"AI ({algo}, depth {r['depth']}): best move {r['san']} "
                f"({engine.format_score(r['value'])})",
                f"Positions searched: {s.nodes}   Pruned: {s.pruned}   "
                f"Time: {s.time:.2f}s",
                f"Best line: {' '.join(r['pv']) if r['pv'] else '—'}",
                "Top moves:  " + "   ".join(
                    f"{san}  {engine.format_score(val)}"
                    for san, val in r["candidates"][:5]),
            ]
            if r.get("random_pick"):
                lines.append(
                    f"Picked at random from {r['near_best']} moves within "
                    f"0.3 of the best — no two games play the same.")
            if self.avoided_repetition:
                lines.append("Skipped a move that would repeat a position.")
            card_h = len(lines) * self.font.get_linesize() + 16
            rect = pygame.Rect(x, y, PANEL_W, card_h)
            pygame.draw.rect(self.screen, CARD, rect, border_radius=10)
            pygame.draw.rect(self.screen, CARD_BORDER, rect, 1,
                             border_radius=10)
            ly = y + 8
            for line in lines:
                ly = self.draw_text_block(self.screen, line, self.font,
                                          x + 12, ly, PANEL_W - 24, INK)
            y += card_h + 10
        if self.compare_text:
            lines = wrap_text(self.compare_text, self.font, PANEL_W - 24)
            card_h = len(lines) * self.font.get_linesize() + 16
            rect = pygame.Rect(x, y, PANEL_W, card_h)
            pygame.draw.rect(self.screen, CARD, rect, border_radius=10)
            pygame.draw.rect(self.screen, (34, 197, 94), rect, 1,
                             border_radius=10)
            ly = y + 8
            for line in lines:
                self.screen.blit(self.font.render(line, True, (187, 247, 208)),
                                 (x + 12, ly))
                ly += self.font.get_linesize()
            y += card_h + 10
        y = self.draw_eliminated(x, y)
        # move history, clipped to its box, most recent lines only
        box_y = max(y + 4, 440)
        box_h = LESSON_Y - 12 - box_y
        if box_h > 30:
            label = self.small.render("Moves", True, MUTED)
            self.screen.blit(label, (x, box_y))
            history = " ".join(
                f"{i // 2 + 1}.{san}" if i % 2 == 0 else san
                for i, san in enumerate(self.move_history()))
            lines = wrap_text(history, self.font, PANEL_W)
            max_lines = max(1, (box_h - 20) // self.font.get_linesize())
            lines = lines[-max_lines:]
            clip = self.screen.get_clip()
            self.screen.set_clip(pygame.Rect(x, box_y, PANEL_W, box_h))
            ly = box_y + 20
            for line in lines:
                self.screen.blit(self.font.render(line, True, MUTED),
                                 (x, ly))
                ly += self.font.get_linesize()
            self.screen.set_clip(clip)

        self.draw_lesson()

    def draw_eliminated(self, x, y):
        """Captured pieces, latest few last: the piece in its own colour,
        with a line like 'Your Queen is eliminated' beside it."""
        if not self.eliminated:
            return y
        self.screen.blit(self.small.render("Eliminated", True, MUTED), (x, y))
        y += 20
        shown = self.eliminated[-5:]
        for color, piece_type in shown:
            surf = self.piece_med[(color, piece_type)]
            self.screen.blit(surf, (x, y - 2))
            text = self.font.render(
                self.eliminated_text(color, piece_type), True, INK)
            self.screen.blit(text, (x + 28, y))
            y += 24
        if len(self.eliminated) > len(shown):
            more = self.small.render(
                f"+{len(self.eliminated) - len(shown)} more eliminated",
                True, MUTED)
            self.screen.blit(more, (x + 28, y))
            y += 18
        return y + 6

    def move_history(self):
        history = []
        replay = chess.Board()
        for move in self.board.move_stack:
            history.append(replay.san(move))
            replay.push(move)
        return history

    def play_buttons(self):
        y = 62
        row1 = [
            Button((PANEL_X, y, 120, 36), "New game", self.new_game),
            Button((PANEL_X + 130, y, 120, 36), "Undo", self.undo),
            Button((PANEL_X + 260, y, 190, 36),
                   f"You: {'White' if self.human_color == chess.WHITE else 'Black'} (switch)",
                   self.toggle_side),
            Button((PANEL_X + 460, y, 180, 36),
                   ("AI vs AI: off" if not self.ai_vs_ai
                    else "AI vs AI: even" if self.handicap == "even"
                    else f"AI vs AI: {self.handicap.title()} +1"),
                   self.toggle_ai_vs_ai),
        ]
        y = 108
        row2 = [
            Button((PANEL_X, y, 120, 36), f"Depth: {self.ai_depth}",
                   self.cycle_depth),
            Button((PANEL_X + 130, y, 160, 36),
                   "Alpha-Beta" if self.use_pruning else "Minimax",
                   self.toggle_pruning),
            Button((PANEL_X + 300, y, 150, 36), "Compare both",
                   self.run_compare),
            Button((PANEL_X + 460, y, 170, 36), "See search tree →",
                   self.open_tree),
        ]
        return row1 + row2

    def undo(self):
        if self.ai_vs_ai:
            return
        pops = 0
        while self.board.move_stack and pops < 2:
            if self.board.turn == self.human_color and pops > 0:
                break
            self.board.pop()
            pops += 1
        self.last_move = None
        self.selected = None
        self.targets = []
        self.ai_pending = False
        # The last search belonged to the undone position.
        self.ai_report = None
        self.tree = None
        self.rebuild_history()

    def toggle_side(self):
        self.new_game()
        self.human_color = chess.BLACK
        self.ai_pending = True
        # Let the start banner be readable before the AI opens the game.
        self.next_ai_time = pygame.time.get_ticks() + 1500

    def ai_depth_for(self, color):
        """Search depth for the side to move. In AI vs AI with a handicap,
        the favoured side searches one level deeper and the other one
        level shallower, so the stronger side can actually win."""
        depth = self.ai_depth
        if not self.ai_vs_ai or self.handicap == "even":
            return depth
        favoured = chess.WHITE if self.handicap == "white" else chess.BLACK
        if color == favoured:
            return min(4, depth + 1)
        return max(2, depth - 1)

    def toggle_ai_vs_ai(self):
        """Cycle: off -> even -> White one level deeper -> Black one level
        deeper -> off. An even match between identical engines is a draw;
        the handicap is what makes a winner possible."""
        order = ["even", "white", "black", "off"]
        current = "off" if not self.ai_vs_ai else self.handicap
        nxt = order[(order.index(current) + 1) % len(order)]
        if nxt == "off":
            self.ai_vs_ai = False
            self.handicap = "even"
        else:
            self.ai_vs_ai = True
            self.handicap = nxt
            self.next_ai_time = pygame.time.get_ticks() + 400

    def cycle_depth(self):
        # Plain Minimax at depth 4 takes ~30s a move; cap it at depth 3.
        top = 4 if self.use_pruning else 3
        self.ai_depth = 2 if self.ai_depth >= top else self.ai_depth + 1

    def toggle_pruning(self):
        self.use_pruning = not self.use_pruning
        if not self.use_pruning and self.ai_depth > 3:
            self.ai_depth = 3

    def open_tree(self):
        if self.tree is None:
            return
        self.screen_name = "tree"

    # ------------------------------------------------------------ tree screen
    def visible_nodes(self):
        """Nodes reachable from the root through expanded nodes."""
        out = []

        def walk(node, depth):
            out.append((node, depth))
            if id(node) in self.expanded:
                for child in node.children:
                    walk(child, depth + 1)
        walk(self.tree, 0)
        return out

    def tree_coords(self):
        """Tidy layout: each visible leaf gets its own column and a parent
        sits centred over its visible children, so the shape of the search
        reads at a glance instead of names piling up on one row. Rows are
        spread down the screen, one per depth, with the left gutter saying
        whose turn that row is.

        Returns (visible, coords, levels, rooms): `rooms` maps a node id
        to the pixels to its nearest neighbour on the same row, which
        decides whether its label fits.
        """
        visible = self.visible_nodes()
        in_visible = {id(n) for n, _ in visible}
        levels = {}
        for node, depth in visible:
            levels.setdefault(depth, []).append(node)
        kids = {id(n): [c for c in n.children if id(c) in in_visible]
                for n, _ in visible}
        slots = {}
        counter = [0]

        def place(node):
            children = kids[id(node)]
            if not children:
                slots[id(node)] = counter[0]
                counter[0] += 1
            else:
                for child in children:
                    place(child)
                slots[id(node)] = (slots[id(children[0])]
                                   + slots[id(children[-1])]) / 2

        place(self.tree)
        total = max(counter[0], 1)
        max_depth = max(levels) if levels else 0
        left, right = 112, WIDTH - 40
        top, bottom = 118, HEIGHT - 210
        # Spread the rows down the screen, but never so far apart that a
        # barely-expanded tree looks empty -- 150px between rows is plenty.
        row_h = min(150, (bottom - top) / max(1, max_depth))
        coords = {}
        for node, depth in visible:
            x = left + (right - left) * (slots[id(node)] + 0.5) / total
            coords[id(node)] = (x, top + depth * row_h)
        rooms = {}
        for depth, nodes in levels.items():
            ordered = sorted(nodes, key=lambda n: coords[id(n)][0])
            xs = [coords[id(n)][0] for n in ordered]
            for i, node in enumerate(ordered):
                left_gap = xs[i] - xs[i - 1] if i > 0 else 999
                right_gap = xs[i + 1] - xs[i] if i < len(xs) - 1 else 999
                rooms[id(node)] = min(left_gap, right_gap)
        return visible, coords, levels, rooms

    def pv_nodes(self):
        """Nodes on the principal variation, by id."""
        ids = set()
        node = self.tree
        ids.add(id(node))
        for san in (self.ai_report["pv"] if self.ai_report else []):
            nxt = next((c for c in node.children if c.san == san), None)
            if nxt is None:
                break
            ids.add(id(nxt))
            node = nxt
        return ids

    def draw_tree(self):
        self.screen.blit(self.bg, (0, 0))
        self.screen.blit(self.title_font.render("Search tree — what the AI looked at",
                                                True, ACCENT), (190, 20))
        y = 52
        y = self.draw_text_block(
            self.screen,
            "Green = White's turn (MAX), blue = Black's turn (MIN), red = pruned: "
            "the AI skipped this branch. Gold ring = the best line. "
            "Click a node to expand it and see the board behind it. Labels "
            "appear only where they fit — click any node for its move and score.",
            self.font, 24, y, WIDTH - 48, MUTED) + 6
        if self.tree is None:
            self.draw_text_block(self.screen, "No search yet — play a move first.",
                                 self.font, 24, y + 20, 600)
            return
        visible, coords, levels, rooms = self.tree_coords()
        pv = self.pv_nodes()
        # Whose turn each row is, in the left gutter.
        for depth, nodes in levels.items():
            _, row_y = coords[id(nodes[0])]
            maxing = nodes[0].maximizing
            side = "White" if maxing else "Black"
            kind = "MAX" if maxing else "MIN"
            self.screen.blit(self.small.render(side, True, MUTED),
                             (16, row_y - 10))
            self.screen.blit(
                self.small.render(f"to move · {kind}", True, MUTED),
                (16, row_y + 6))
        # Node labels: always show them for the root's children (the
        # candidate moves). Deeper down, label only the best line, pruned
        # nodes and the selected node. A label appears only if its
        # neighbours leave room for it; on a crowded row, alternate
        # labels above and below the nodes so they stop piling up on one
        # line. A node shows its value when there is room for that too.
        # Anything unlabelled is one click away in the detail strip below.
        level_index = {}
        for depth, nodes in levels.items():
            ordered = sorted(nodes, key=lambda n: coords[id(n)][0])
            for i, node in enumerate(ordered):
                level_index[id(node)] = i
        # edges
        for node, depth in visible:
            for child in node.children:
                if id(child) in coords:
                    pygame.draw.line(self.screen, (150, 150, 150),
                                     coords[id(node)], coords[id(child)], 1)
        # nodes
        for node, depth in visible:
            cx, cy = coords[id(node)]
            revealed = node.pruned or node.order <= self.revealed
            if node.pruned:
                color = RED
            elif not revealed:
                color = GREY
            elif node.maximizing:
                color = GREEN
            else:
                color = BLUE
            pygame.draw.circle(self.screen, color, (int(cx), int(cy)), 14)
            if id(node) in pv:
                pygame.draw.circle(self.screen, GOLD, (int(cx), int(cy)), 18, 3)
            if self.selected_node is node:
                pygame.draw.circle(self.screen, (255, 255, 255),
                                   (int(cx), int(cy)), 18, 2)
            room = rooms[id(node)]
            show_value = revealed and node.value is not None and room >= 60
            label = None
            if room >= 22:
                if depth <= 1:
                    label = (f"{node.san} {engine.format_score(node.value)}"
                             if show_value else node.san)
                elif id(node) in pv or node.pruned or self.selected_node is node:
                    if node.pruned:
                        label = node.san
                    elif show_value:
                        label = (f"{node.san} "
                                 f"{engine.format_score(node.value)}")
                    else:
                        label = node.san
            if label:
                above = room < 46 and level_index[id(node)] % 2 == 1
                ly = cy - 26 if above else cy + 26
                text = self.small.render(label, True, INK)
                self.screen.blit(text, text.get_rect(center=(cx, ly)))
        # detail strip
        self.draw_node_detail()

    def draw_node_detail(self):
        node = self.selected_node or self.tree
        y = HEIGHT - 150
        pygame.draw.rect(self.screen, CARD, (24, y, WIDTH - 48, 126))
        pygame.draw.rect(self.screen, ACCENT, (24, y, WIDTH - 48, 126), 1)
        if node.pruned:
            status = "PRUNED — the AI never searched this branch."
        elif node.value is None:
            status = "No value recorded."
        else:
            status = (f"Value {engine.format_score(node.value)} — "
                      f"{'White' if node.value >= 0 else 'Black'} is ahead.")
        alpha = "−∞" if node.alpha == float("-inf") else engine.format_score(node.alpha)
        beta = "+∞" if node.beta == float("inf") else engine.format_score(node.beta)
        detail = (
            f"{node.san}   {node.kind} node   {status}\n"
            f"Alpha {alpha}  (best White can already guarantee)   "
            f"Beta {beta}  (best Black can already guarantee)\n"
            f"Children: {len(node.children)}   "
            f"{'Click again to collapse.' if id(node) in self.expanded and node.children else 'Click to expand.' if node.children else ''}"
        )
        self.draw_text_block(self.screen, detail, self.font, 40, y + 12,
                             WIDTH - 260, INK)
        # mini board of this position
        mini = chess.Board(node.fen)
        self.draw_board(self.screen, mini, WIDTH - 176, y + 8, 14)

    def tree_click(self, pos):
        if self.tree is None:
            return
        visible, coords, levels, rooms = self.tree_coords()
        for node, depth in visible:
            cx, cy = coords[id(node)]
            if (pos[0] - cx) ** 2 + (pos[1] - cy) ** 2 <= 20 ** 2:
                self.selected_node = node
                if node.children:
                    if id(node) in self.expanded:
                        self.expanded.discard(id(node))
                    else:
                        self.expanded.add(id(node))
                return

    def tree_buttons(self):
        return [
            Button((24, 16, 150, 30), "← Back to board",
                   lambda: setattr(self, "screen_name", "play")),
            Button((WIDTH - 340, 16, 150, 30), "▶ Replay search",
                   self.start_replay),
            Button((WIDTH - 180, 16, 150, 30), "Show all",
                   self.show_all_tree),
        ]

    def start_replay(self):
        self.revealed = 0
        self.replay = True
        self.expanded = {id(self.tree)}

    def show_all_tree(self):
        self.revealed = 10 ** 9
        self.replay = False

    def check_move_cap(self):
        """AI vs AI safety stop: after 200 moves with no result, call it
        a draw instead of letting the game sit there with no winner and
        no message."""
        if (self.ai_vs_ai and self.game_over_info is None
                and len(self.board.move_stack) >= 200):
            self.game_over_info = {
                "headline": "Draw — 200 moves, no winner",
                "detail": ("Neither side could force a win in 200 moves; "
                           "the game is a draw."),
                "result": "*"}
            self.ai_pending = False

    # ------------------------------------------------------------ main loop
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEMOTION:
                    self.hover_pos = event.pos
                    if self.screen_name == "play":
                        self.hover_square = self.square_at(event.pos)
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.screen_name == "play":
                        if not any(b.click(event.pos)
                                   for b in self.play_buttons()):
                            self.handle_play_click(event.pos)
                    else:
                        if not any(b.click(event.pos)
                                   for b in self.tree_buttons()):
                            self.tree_click(event.pos)

            if self.replay and self.tree is not None:
                total = max((n.order for n, _ in self.visible_nodes()),
                            default=0)
                self.revealed += max(1, total // 120)
                if self.revealed >= total:
                    self.replay = False

            if self.screen_name == "play":
                self.draw_play()
                self.check_move_cap()
                if (self.ai_pending and self.game_over_info is None
                        and pygame.time.get_ticks() >= self.next_ai_time):
                    # show "AI thinking…" before the blocking search runs
                    pygame.display.flip()
                    self.ai_move()
                elif (self.ai_vs_ai and self.game_over_info is None
                        and pygame.time.get_ticks() >= self.next_ai_time):
                    pygame.display.flip()
                    self.ai_move()
            else:
                self.draw_tree()
                for button in self.tree_buttons():
                    button.draw(self.screen, self.font,
                                hover=(self.hover_pos is not None
                                       and button.rect.collidepoint(
                                           self.hover_pos)))
            pygame.display.flip()
            self.clock.tick(30)


if __name__ == "__main__":
    App().run()
