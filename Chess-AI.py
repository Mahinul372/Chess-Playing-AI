import pygame
import sys
import math
import random
from pygame.locals import *

# Initialize pygame
pygame.init()
pygame.font.init()

# Constants
WIDTH, HEIGHT = 1000, 700
NODE_RADIUS = 15
LEVEL_HEIGHT = 90
FONT = pygame.font.SysFont('Arial', 18)
LARGE_FONT = pygame.font.SysFont('Arial', 32)
INPUT_FONT = pygame.font.SysFont('Arial', 24)
COLORS = {
    'background': (245, 245, 245),
    'node': (70, 130, 180),
    'pruned': (220, 20, 60),
    'max': (50, 205, 50),
    'min': (255, 69, 0),
    'text': (50, 50, 50),
    'line': (100, 100, 100),
    'input_box': (255, 255, 255),
    'active_input': (220, 240, 255),
    'prompt': (70, 70, 70),
    'cursor': (0, 0, 0),
    'title': (30, 80, 120),
    'error': (200, 0, 0)
}

class InputBox:
    def __init__(self, x, y, w, h, prompt):
        self.rect = pygame.Rect(x, y, w, h)
        self.color = COLORS['input_box']
        self.prompt = prompt
        self.text = ""
        self.txt_surface = INPUT_FONT.render(self.text, True, COLORS['text'])
        self.active = False
        self.cursor_visible = False
        self.cursor_timer = 0
        self.cursor_pos = 0

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos):
                self.active = True
                self.cursor_visible = True
                self.cursor_timer = pygame.time.get_ticks()
            else:
                self.active = False
            self.color = COLORS['active_input'] if self.active else COLORS['input_box']
        
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return True
            elif event.key == pygame.K_BACKSPACE:
                if self.cursor_pos > 0:
                    self.text = self.text[:self.cursor_pos-1] + self.text[self.cursor_pos:]
                    self.cursor_pos -= 1
            elif event.key == pygame.K_LEFT:
                self.cursor_pos = max(0, self.cursor_pos-1)
            elif event.key == pygame.K_RIGHT:
                self.cursor_pos = min(len(self.text), self.cursor_pos+1)
            else:
                self.text = self.text[:self.cursor_pos] + event.unicode + self.text[self.cursor_pos:]
                self.cursor_pos += 1
            
            self.txt_surface = INPUT_FONT.render(self.text, True, COLORS['text'])
            self.cursor_visible = True
            self.cursor_timer = pygame.time.get_ticks()
        
        return False

    def draw(self, screen):
        # Draw prompt text
        prompt_surface = FONT.render(self.prompt, True, COLORS['prompt'])
        screen.blit(prompt_surface, (self.rect.x, self.rect.y - 30))
        
        # Draw input box
        pygame.draw.rect(screen, self.color, self.rect, 0, border_radius=5)
        pygame.draw.rect(screen, COLORS['text'], self.rect, 2, border_radius=5)
        
        # Draw text
        text_x = self.rect.x + 15
        text_y = self.rect.y + (self.rect.h - self.txt_surface.get_height()) // 2
        screen.blit(self.txt_surface, (text_x, text_y))
        
        # Draw cursor if active
        if self.active and self.cursor_visible:
            cursor_x = text_x + INPUT_FONT.size(self.text[:self.cursor_pos])[0]
            pygame.draw.line(
                screen, COLORS['cursor'], 
                (cursor_x, text_y + 5), 
                (cursor_x, text_y + self.txt_surface.get_height() - 5), 
                2
            )
        
        # Blink cursor
        if self.active and pygame.time.get_ticks() - self.cursor_timer > 500:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = pygame.time.get_ticks()

class VisualNode:
    def __init__(self, value, x, y, depth, is_maximizing, pruned=False):
        self.value = value
        self.x = x
        self.y = y
        self.depth = depth
        self.is_maximizing = is_maximizing
        self.pruned = pruned
        self.children = []
    
    def add_child(self, child):
        self.children.append(child)

class ChessAIVisualizer:
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Chess AI Tournament Visualizer")
        self.clock = pygame.time.Clock()
        self.nodes = []
        self.current_game = 0
        self.results = []
        self.carlsen_wins = 0
        self.caruana_wins = 0
        self.draws = 0
        self.state = "input"
        self.input_boxes = []
        self.current_input = 0
        self.start_player = None
        self.carlsen_strength = None
        self.caruana_strength = None
        self.error_message = ""
        self.error_timer = 0

    def run(self):
        while True:
            if self.state == "input":
                self.handle_input_screen()
            elif self.state == "visualization":
                self.play_game_visual()
                self.state = "results"
            elif self.state == "results":
                self.show_final_results()
                break  # Exit after showing results
            
            pygame.display.flip()
            self.clock.tick(30)

    def handle_input_screen(self):
        if not self.input_boxes:
            # Initialize input boxes only once
            input_y_start = HEIGHT // 3
            self.input_boxes = [
                InputBox(WIDTH//2 - 150, input_y_start, 300, 40, 
                        "Starting player (0=Carlsen, 1=Caruana):"),
                InputBox(WIDTH//2 - 150, input_y_start + 100, 300, 40, 
                        "Carlsen's base strength:"),
                InputBox(WIDTH//2 - 150, input_y_start + 200, 300, 40, 
                        "Caruana's base strength:")
            ]
            self.input_boxes[0].active = True

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            
            # Handle input boxes
            for i, box in enumerate(self.input_boxes):
                done = box.handle_event(event)
                if done:
                    if i < len(self.input_boxes) - 1:
                        # Move to next input box
                        self.input_boxes[i].active = False
                        self.input_boxes[i+1].active = True
                    else:
                        # Try to process all inputs
                        try:
                            self.start_player = int(self.input_boxes[0].text)
                            if self.start_player not in (0, 1):
                                raise ValueError("Player must be 0 or 1")
                            self.carlsen_strength = float(self.input_boxes[1].text)
                            self.caruana_strength = float(self.input_boxes[2].text)
                            self.state = "visualization"
                            return
                        except ValueError as e:
                            self.error_message = f"Invalid input: {str(e)}"
                            self.error_timer = pygame.time.get_ticks()
                            # Reset all inputs
                            for box in self.input_boxes:
                                box.text = ""
                                box.active = False
                            self.input_boxes[0].active = True

        # Draw input screen
        self.screen.fill(COLORS['background'])
        
        # Draw title
        title = LARGE_FONT.render("Chess AI Tournament", True, COLORS['title'])
        title_rect = title.get_rect(center=(WIDTH//2, HEIGHT//6))
        self.screen.blit(title, title_rect)
        
        # Draw input boxes
        for box in self.input_boxes:
            box.draw(self.screen)
        
        # Draw instructions
        instructions = FONT.render("Press Enter after each input", True, COLORS['prompt'])
        self.screen.blit(instructions, (WIDTH//2 - instructions.get_width()//2, HEIGHT - 50))
        
        # Draw error message if any
        if self.error_message and pygame.time.get_ticks() - self.error_timer < 3000:
            error_surface = FONT.render(self.error_message, True, COLORS['error'])
            self.screen.blit(error_surface, (WIDTH//2 - error_surface.get_width()//2, HEIGHT - 100))

    def strength(self, x):
        return math.log2(x + 1) + x / 10

    def utility(self, maxV, minV):
        t = random.randint(0, 1)
        rand_val = random.uniform(0.1, 0.2)
        return (self.strength(maxV) - self.strength(minV)) + ((-1) ** t) * rand_val

    def minimax_visual(self, depth, is_maximizing, alpha, beta, maxV, minV, parent_x, parent_y, tree_width, level_width):
        if depth == 5:
            value = self.utility(maxV, minV)
            x = max(NODE_RADIUS, min(WIDTH-NODE_RADIUS, parent_x + (random.random() - 0.5) * level_width))
            y = max(NODE_RADIUS, min(HEIGHT-NODE_RADIUS, parent_y + LEVEL_HEIGHT))
            node = VisualNode(value, x, y, depth, is_maximizing)
            self.nodes.append(node)
            return node, value

        best_node = None
        best_value = -float('inf') if is_maximizing else float('inf')
        nodes_at_level = 2 ** depth
        spacing = min(150, tree_width / (nodes_at_level + 1))
        
        for i in range(2):
            x = max(NODE_RADIUS, min(WIDTH-NODE_RADIUS, 
                  parent_x - tree_width/2 + (i+1) * spacing if depth > 0 else WIDTH/2))
            y = max(NODE_RADIUS, min(HEIGHT-NODE_RADIUS, 
                  parent_y + LEVEL_HEIGHT if depth > 0 else 50))
            
            node, value = self.minimax_visual(
                depth + 1, not is_maximizing, alpha, beta, maxV, minV, 
                x, y, tree_width/1.8, level_width
            )
            
            if depth > 0:
                VisualNode(None, x, y, depth, is_maximizing).add_child(node)
            
            if is_maximizing:
                if value > best_value:
                    best_value = value
                    best_node = node
                alpha = max(alpha, best_value)
            else:
                if value < best_value:
                    best_value = value
                    best_node = node
                beta = min(beta, best_value)
                
            if beta <= alpha:
                for j in range(i+1, 2):
                    x_pruned = max(NODE_RADIUS, min(WIDTH-NODE_RADIUS, 
                                  parent_x - tree_width/2 + (j+1) * spacing))
                    y_pruned = max(NODE_RADIUS, min(HEIGHT-NODE_RADIUS, 
                                  parent_y + LEVEL_HEIGHT))
                    pruned_node = VisualNode(None, x_pruned, y_pruned, depth, is_maximizing, pruned=True)
                    self.nodes.append(pruned_node)
                break
        
        if depth == 0:
            root = VisualNode(best_value, WIDTH/2, 50, 0, True)
            root.add_child(best_node)
            self.nodes.append(root)
            return root, best_value
        
        return best_node, best_value

    def play_game_visual(self):
        self.results = []
        for game in range(4):
            self.nodes = []
            if (self.start_player + game) % 2 == 0:
                maxV, minV = self.carlsen_strength, self.caruana_strength
                max_player = "Magnus Carlsen"
                min_player = "Fabiano Caruana"
            else:
                maxV, minV = self.caruana_strength, self.carlsen_strength
                max_player = "Fabiano Caruana"
                min_player = "Magnus Carlsen"

            root, utility_value = self.minimax_visual(
                0, True, -float('inf'), float('inf'), 
                maxV, minV, WIDTH/2, 50, WIDTH-150, 80
            )
            
            winner = max_player if utility_value > 0 else min_player if utility_value < 0 else "Draw"
            self.results.append((winner, utility_value, self.nodes.copy()))
            
            if winner == "Magnus Carlsen":
                self.carlsen_wins += 1
            elif winner == "Fabiano Caruana":
                self.caruana_wins += 1
            else:
                self.draws += 1
            
            self.visualize_game(game)

    def visualize_game(self, game_idx):
        running = True
        nodes = self.results[game_idx][2]
        
        while running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        running = False
            
            self.screen.fill(COLORS['background'])
            
            title = LARGE_FONT.render(
                f"Game {game_idx+1}: {self.results[game_idx][0]} wins (Utility: {self.results[game_idx][1]:.2f})", 
                True, COLORS['text']
            )
            self.screen.blit(title, (20, 10))
            
            for node in nodes:
                color = COLORS['pruned'] if node.pruned else COLORS['max'] if node.is_maximizing else COLORS['min']
                
                for child in node.children:
                    pygame.draw.line(
                        self.screen, COLORS['line'], 
                        (node.x, node.y), (child.x, child.y), 2
                    )
                
                pygame.draw.circle(self.screen, color, (int(node.x), int(node.y)), NODE_RADIUS)
                
                if node.value is not None:
                    value_text = FONT.render(f"{node.value:.2f}", True, COLORS['text'])
                    text_rect = value_text.get_rect(center=(node.x, node.y))
                    self.screen.blit(value_text, text_rect)
            
            # Draw legend
            pygame.draw.rect(self.screen, COLORS['max'], (20, HEIGHT-100, 20, 20), border_radius=3)
            self.screen.blit(FONT.render("Max Node", True, COLORS['text']), (50, HEIGHT-100))
            
            pygame.draw.rect(self.screen, COLORS['min'], (20, HEIGHT-70, 20, 20), border_radius=3)
            self.screen.blit(FONT.render("Min Node", True, COLORS['text']), (50, HEIGHT-70))
            
            pygame.draw.rect(self.screen, COLORS['pruned'], (20, HEIGHT-40, 20, 20), border_radius=3)
            self.screen.blit(FONT.render("Pruned Node", True, COLORS['text']), (50, HEIGHT-40))
            
            # Draw navigation instructions
            instructions = FONT.render("Press ESC to continue", True, COLORS['prompt'])
            self.screen.blit(instructions, (WIDTH - instructions.get_width() - 20, HEIGHT - 30))
            
            pygame.display.flip()
            self.clock.tick(30)
    
    def show_final_results(self):
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == KEYDOWN:
                    if event.key == K_ESCAPE:
                        running = False
            
            self.screen.fill(COLORS['background'])
            
            title = LARGE_FONT.render("Tournament Results", True, COLORS['title'])
            title_rect = title.get_rect(center=(WIDTH//2, 50))
            self.screen.blit(title, title_rect)
            
            # Draw game results
            for i, (winner, utility, _) in enumerate(self.results):
                result_text = FONT.render(
                    f"Game {i+1}: {winner} (Utility: {utility:.2f})", 
                    True, COLORS['text']
                )
                self.screen.blit(result_text, (WIDTH//4, 120 + i*35))
            
            # Draw overall results
            overall_y = 120 + len(self.results)*35 + 30
            self.screen.blit(
                LARGE_FONT.render("Overall Results:", True, COLORS['title']), 
                (WIDTH//4, overall_y)
            )
            
            self.screen.blit(
                FONT.render(f"Magnus Carlsen Wins: {self.carlsen_wins}", True, COLORS['text']), 
                (WIDTH//4, overall_y + 50)
            )
            self.screen.blit(
                FONT.render(f"Fabiano Caruana Wins: {self.caruana_wins}", True, COLORS['text']), 
                (WIDTH//4, overall_y + 85)
            )
            self.screen.blit(
                FONT.render(f"Draws: {self.draws}", True, COLORS['text']), 
                (WIDTH//4, overall_y + 120)
            )
            
            # Determine and draw overall winner
            if self.carlsen_wins > self.caruana_wins:
                winner_text = "Overall Winner: Magnus Carlsen"
                winner_color = COLORS['max']
            elif self.caruana_wins > self.carlsen_wins:
                winner_text = "Overall Winner: Fabiano Caruana"
                winner_color = COLORS['min']
            else:
                winner_text = "Overall Winner: Draw"
                winner_color = COLORS['text']
            
            winner_surface = LARGE_FONT.render(winner_text, True, winner_color)
            winner_rect = winner_surface.get_rect(center=(WIDTH//2, overall_y + 180))
            self.screen.blit(winner_surface, winner_rect)
            
            # Draw instructions
            instructions = FONT.render("Press ESC to exit", True, COLORS['prompt'])
            self.screen.blit(instructions, (WIDTH//2 - instructions.get_width()//2, HEIGHT - 40))
            
            pygame.display.flip()
            self.clock.tick(30)

if __name__ == "__main__":
    visualizer = ChessAIVisualizer()
    visualizer.run()
    pygame.quit()
    sys.exit()