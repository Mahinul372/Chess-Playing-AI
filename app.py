"""Chess AI you can play against -- and watch think.

Play real chess against an AI that searches with Minimax and Alpha-Beta
pruning. After every AI move, open the search tree to see the actual moves
the AI considered, the score of each, and the branches it pruned -- with
plain-language explanations of what the algorithm is doing.

Run:  python app.py
"""

import sys
import time

import chess
import pygame

import engine

# ---------------------------------------------------------------- window
WIDTH, HEIGHT = 1280, 760
BOARD = 560
SQ = BOARD // 8
BOARD_X, BOARD_Y = 24, 24
PANEL_X = 608
PANEL_W = 648

LIGHT_SQ = (240, 217, 181)
DARK_SQ = (181, 136, 99)
BG = (245, 245, 245)
PANEL_BG = (255, 255, 255)
INK = (40, 40, 40)
MUTED = (110, 110, 110)
ACCENT = (30, 80, 120)
GREEN = (46, 160, 67)      # MAX node / explored
BLUE = (70, 130, 180)      # MIN node
RED = (220, 60, 60)        # pruned node
GOLD = (212, 175, 55)      # best path
GREY = (180, 180, 180)     # not yet revealed
LAST_MOVE = (205, 210, 110)
CHECK = (220, 80, 80)

WHITE_GLYPHS = {chess.KING: "♔", chess.QUEEN: "♕", chess.ROOK: "♖",
                chess.BISHOP: "♗", chess.KNIGHT: "♘", chess.PAWN: "♙"}
BLACK_GLYPHS = {chess.KING: "♚", chess.QUEEN: "♛", chess.ROOK: "♜",
                chess.BISHOP: "♝", chess.KNIGHT: "♞", chess.PAWN: "♟"}


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
    return None


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

    def draw(self, surface, font):
        pygame.draw.rect(surface, PANEL_BG, self.rect, border_radius=6)
        pygame.draw.rect(surface, ACCENT, self.rect, 2, border_radius=6)
        text = font.render(self.label, True, ACCENT)
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

        self.font = pygame.font.SysFont("arial", 17)
        self.small = pygame.font.SysFont("arial", 14)
        self.title_font = pygame.font.SysFont("arial", 22, bold=True)
        self.piece_font = load_piece_font(52)
        self.mini_piece_font = load_piece_font(13)
        self.use_glyphs = self.piece_font is not None
        if not self.use_glyphs:
            self.piece_font = pygame.font.SysFont("arial", 40, bold=True)
            self.mini_piece_font = pygame.font.SysFont("arial", 11, bold=True)

        self.new_game()

    # ------------------------------------------------------------ state
    def new_game(self):
        self.board = chess.Board()
        self.human_color = chess.WHITE
        self.ai_depth = 3
        self.use_pruning = True
        self.ai_vs_ai = False
        self.selected = None
        self.targets = []
        self.last_move = None
        self.ai_report = None
        self.compare_text = None
        self.ai_pending = False
        self.next_ai_time = 0
        self.explain = (
            "Minimax: the AI tries every legal move, then assumes you answer "
            "with your best move, and so on. White picks the highest score, "
            "Black the lowest. The score comes from material plus where each "
            "piece stands."
        )
        self.screen_name = "play"
        self.tree = None
        self.expanded = set()
        self.selected_node = None
        self.revealed = 0
        self.replay = False

    # ------------------------------------------------------------ game
    def human_move(self, move):
        san = self.board.san(move)
        self.board.push(move)
        self.last_move = (move.from_square, move.to_square)
        self.selected = None
        self.targets = []
        self.after_move(san)

    def ai_move(self):
        self.ai_pending = False
        report = engine.best_move(self.board, self.ai_depth, self.use_pruning)
        if report["move"] is None:
            return
        san = report["san"]
        self.board.push(report["move"])
        self.last_move = (report["move"].from_square, report["move"].to_square)
        self.ai_report = report
        self.tree = report["tree"]
        self.expanded = {id(self.tree)}
        self.selected_node = self.tree
        self.revealed = 10 ** 9  # tree screen reveals everything by default
        self.replay = False
        self.explain = self.explain_after_search(report)
        self.after_move(san)

    def after_move(self, san):
        if self.board.is_game_over():
            return
        if self.ai_vs_ai:
            self.next_ai_time = pygame.time.get_ticks() + 700
        elif self.board.turn != self.human_color:
            self.ai_pending = True

    def explain_after_search(self, report):
        stats = report["stats"]
        best = report["san"]
        score = engine.format_score(report["value"])
        if self.use_pruning:
            example = self.cutoff_example(report["tree"])
            text = (
                f"Alpha-Beta pruning: the AI searched {stats.nodes} positions "
                f"and skipped {stats.pruned} branches it could prove were "
                f"useless. Best move {best} ({score}). It found the same best "
                f"move as plain Minimax would -- pruning only skips work, it "
                f"never changes the answer."
            )
            if example:
                text += f" Example: {example}"
            return text
        return (
            f"Plain Minimax, no pruning: the AI searched every branch, "
            f"{stats.nodes} positions in {stats.time:.2f}s. Best move {best} "
            f"({score}). Turn pruning on to see how much of this work can be "
            f"skipped."
        )

    def cutoff_example(self, tree):
        """One concrete pruned branch, in plain words. A cutoff means the
        branch could not change the AI's decision, so it was never searched."""
        for child in tree.children:
            for grand in child.children:
                if grand.pruned:
                    return (
                        f"for example, after {child.san} the move {grand.san} "
                        f"was never searched: the AI had already found a "
                        f"better option elsewhere, so this branch could not "
                        f"change its decision."
                    )
        for child in tree.children:
            if child.pruned:
                return (
                    f"for example, the move {child.san} was never searched: "
                    f"the AI had already found a better option elsewhere."
                )
        return ""

    def run_compare(self):
        if self.board.is_game_over():
            return
        depth = min(self.ai_depth, 3)
        result = engine.compare(self.board, depth)
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
        if self.ai_vs_ai or self.board.is_game_over():
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
    def draw_piece(self, surface, piece, cx, cy, font, size):
        if self.use_glyphs:
            glyph = (WHITE_GLYPHS if piece.color == chess.WHITE
                     else BLACK_GLYPHS)[piece.piece_type]
            edge = (30, 30, 30) if piece.color == chess.WHITE else (240, 240, 240)
            fill = (250, 250, 250) if piece.color == chess.WHITE else (20, 20, 20)
            for dx, dy in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
                edge_surf = font.render(glyph, True, edge)
                surface.blit(edge_surf, edge_surf.get_rect(center=(cx + dx, cy + dy)))
            surf = font.render(glyph, True, fill)
            surface.blit(surf, surf.get_rect(center=(cx, cy)))
        else:
            letter = {chess.KING: "K", chess.QUEEN: "Q", chess.ROOK: "R",
                      chess.BISHOP: "B", chess.KNIGHT: "N", chess.PAWN: "P"}[piece.piece_type]
            color = (250, 250, 250) if piece.color == chess.WHITE else (20, 20, 20)
            surf = font.render(letter, True, color)
            surface.blit(surf, surf.get_rect(center=(cx, cy)))

    def draw_board(self, surface, board, x, y, sq):
        for rank in range(8):
            for file in range(8):
                square = chess.square(file, rank)
                px = x + file * sq
                py = y + (7 - rank) * sq
                color = LIGHT_SQ if (file + rank) % 2 else DARK_SQ
                if self.last_move and square in self.last_move and board is self.board:
                    color = LAST_MOVE
                pygame.draw.rect(surface, color, (px, py, sq, sq))
                piece = board.piece_at(square)
                if piece:
                    font = self.piece_font if sq >= 50 else self.mini_piece_font
                    self.draw_piece(surface, piece, px + sq // 2, py + sq // 2,
                                    font, sq)
        # check highlight
        if board.is_check():
            king = board.king(board.turn)
            px = x + chess.square_file(king) * sq
            py = y + (7 - chess.square_rank(king)) * sq
            pygame.draw.rect(surface, CHECK, (px, py, sq, sq), 4)
        # legal-move dots
        if board is self.board and self.selected is not None:
            px = x + chess.square_file(self.selected) * sq
            py = y + (7 - chess.square_rank(self.selected)) * sq
            pygame.draw.rect(surface, ACCENT, (px, py, sq, sq), 3)
            for move in self.targets:
                tx = x + chess.square_file(move.to_square) * sq + sq // 2
                ty = y + (7 - chess.square_rank(move.to_square)) * sq + sq // 2
                pygame.draw.circle(surface, ACCENT, (tx, ty), 9)

    def draw_text_block(self, surface, text, font, x, y, width, color=INK):
        for line in wrap_text(text, font, width):
            surface.blit(font.render(line, True, color), (x, y))
            y += font.get_linesize()
        return y

    def status_text(self):
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

    # ------------------------------------------------------------ screens
    def draw_play(self):
        self.screen.fill(BG)
        self.draw_board(self.screen, self.board, BOARD_X, BOARD_Y, SQ)
        # coordinates
        for file in range(8):
            label = self.small.render(chess.FILE_NAMES[file], True, MUTED)
            self.screen.blit(label, (BOARD_X + file * SQ + 4, BOARD_Y + BOARD + 4))
        # explanation under the board
        y = BOARD_Y + BOARD + 26
        self.screen.blit(self.title_font.render("How the AI thinks",
                                                True, ACCENT), (BOARD_X, y))
        y += 30
        self.draw_text_block(self.screen, self.explain, self.font,
                             BOARD_X, y, BOARD - 10, INK)

        # right panel
        x = PANEL_X
        self.screen.blit(self.title_font.render("Chess AI", True, ACCENT), (x, 24))
        y = 60
        y = self.draw_text_block(self.screen, self.status_text(), self.font,
                                 x, y, PANEL_W, INK) + 8
        # AI report
        if self.ai_report:
            r = self.ai_report
            s = r["stats"]
            algo = "Alpha-Beta" if self.use_pruning else "Minimax"
            lines = [
                f"AI ({algo}, depth {self.ai_depth}): best move {r['san']} "
                f"({engine.format_score(r['value'])})",
                f"Positions searched: {s.nodes}   Pruned: {s.pruned}   "
                f"Time: {s.time:.2f}s",
                f"Best line: {' '.join(r['pv']) if r['pv'] else '—'}",
            ]
            top = [f"{san}  {engine.format_score(val)}"
                   for san, val in r["candidates"][:5]]
            lines.append("Top moves:  " + "   ".join(top))
            for line in lines:
                y = self.draw_text_block(self.screen, line, self.font, x, y,
                                         PANEL_W, INK) + 2
            y += 4
        if self.compare_text:
            y = self.draw_text_block(self.screen, self.compare_text, self.font,
                                     x, y, PANEL_W, (30, 90, 30)) + 8
        # move history
        y = self.draw_text_block(
            self.screen,
            "Moves: " + " ".join(
                f"{i // 2 + 1}.{san}" if i % 2 == 0 else san
                for i, san in enumerate(self.move_history())),
            self.font, x, y, PANEL_W, MUTED) + 12
        # buttons
        for button in self.play_buttons():
            button.draw(self.screen, self.font)

    def move_history(self):
        history = []
        replay = chess.Board()
        for move in self.board.move_stack:
            history.append(replay.san(move))
            replay.push(move)
        return history

    def play_buttons(self):
        y = 640
        row1 = [
            Button((PANEL_X, y, 120, 36), "New game", self.new_game),
            Button((PANEL_X + 130, y, 120, 36), "Undo", self.undo),
            Button((PANEL_X + 260, y, 190, 36),
                   f"You: {'White' if self.human_color == chess.WHITE else 'Black'} (switch)",
                   self.toggle_side),
            Button((PANEL_X + 460, y, 180, 36),
                   "AI vs AI: ON" if self.ai_vs_ai else "AI vs AI: off",
                   self.toggle_ai_vs_ai),
        ]
        y = 686
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

    def toggle_side(self):
        self.new_game()
        self.human_color = chess.BLACK
        self.ai_pending = True

    def toggle_ai_vs_ai(self):
        self.ai_vs_ai = not self.ai_vs_ai
        if self.ai_vs_ai:
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
        """One row per depth, nodes spaced evenly across the row.

        A tidy parent-centred layout spreads siblings apart whenever one
        branch is expanded; even spacing keeps the candidate moves readable
        no matter which branch is open.
        """
        visible = self.visible_nodes()
        levels = {}
        for node, depth in visible:
            levels.setdefault(depth, []).append(node)
        coords = {}
        for depth, nodes in levels.items():
            count = len(nodes)
            for i, node in enumerate(nodes):
                x = 40 + (WIDTH - 80) * (i + 0.5) / count
                y = 110 + depth * 74
                coords[id(node)] = (x, y)
        return visible, coords, levels

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
        self.screen.fill(BG)
        self.screen.blit(self.title_font.render("Search tree — what the AI looked at",
                                                True, ACCENT), (190, 20))
        y = 52
        y = self.draw_text_block(
            self.screen,
            "Green = White's turn (MAX), blue = Black's turn (MIN), red = pruned: "
            "the AI skipped this branch. Gold ring = the best line. "
            "Click a node to expand it and see the board behind it.",
            self.font, 24, y, WIDTH - 48, MUTED) + 6
        if self.tree is None:
            self.draw_text_block(self.screen, "No search yet — play a move first.",
                                 self.font, 24, y + 20, 600)
            return
        visible, coords, levels = self.tree_coords()
        pv = self.pv_nodes()
        # Node labels: always show them for the root's children (the
        # candidate moves). Deeper down, label only the best line, pruned
        # nodes and the selected node -- otherwise the labels overlap.
        # A row shows values when its nodes have room for them.
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
            space = (WIDTH - 80) / len(levels[depth])
            show_value = revealed and node.value is not None and space >= 55
            label = None
            if depth <= 1:
                label = (f"{node.san} {engine.format_score(node.value)}"
                         if show_value else node.san)
            elif id(node) in pv or node.pruned or self.selected_node is node:
                if node.pruned:
                    label = node.san
                elif show_value:
                    label = f"{node.san} {engine.format_score(node.value)}"
                else:
                    label = node.san
            if label:
                text = self.small.render(label, True, INK)
                self.screen.blit(text, text.get_rect(center=(cx, cy + 26)))
        # detail strip
        self.draw_node_detail()

    def draw_node_detail(self):
        node = self.selected_node or self.tree
        y = HEIGHT - 150
        pygame.draw.rect(self.screen, PANEL_BG, (24, y, WIDTH - 48, 126))
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
        visible, coords, levels = self.tree_coords()
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
        y = HEIGHT - 170
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

    # ------------------------------------------------------------ main loop
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
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
                if self.ai_pending:
                    # show "AI thinking…" before the blocking search runs
                    pygame.display.flip()
                    self.ai_move()
                elif (self.ai_vs_ai and not self.board.is_game_over()
                        and pygame.time.get_ticks() >= self.next_ai_time
                        and len(self.board.move_stack) < 200):
                    pygame.display.flip()
                    self.ai_move()
            else:
                self.draw_tree()
                for button in self.tree_buttons():
                    button.draw(self.screen, self.font)
            pygame.display.flip()
            self.clock.tick(30)


if __name__ == "__main__":
    App().run()
