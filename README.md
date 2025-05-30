# Chess-Playing-AI
a chess-playing AI using Minimax with Alpha-Beta Pruning that simulates strategic gameplay between two agents. The project involved optimizing search trees and implementing decision-making under constraints. Which will help to understand game theory, heuristics, and evaluation functions in real-world scenarios.
  1. Minimax Algorithm Demonstration:
  
  Visually illustrates the minimax algorithm, a fundamental decision-making technique in game AI
  
  Shows alpha-beta pruning optimization in action (with pruned nodes displayed differently)
  
  2. Game Theory Concepts:
  
  Models adversarial decision-making between two players
  
  Demonstrates how AI evaluates future game states to make optimal moves
  
  3. Educational Value:
  
  Makes abstract algorithms concrete through visualization
  
  Shows the tree structure of possible moves and evaluations
  
  Helps students understand recursive algorithms visually
  
  4. AI Strength Modeling:
  
  Implements a mathematical model (logarithmic + linear components) to simulate player strengths
  
  Includes randomness to simulate real-world uncertainty in game outcomes
  
  5. Interactive Learning:
  
  Allows users to input different parameters (starting player, strength values)
  
  Shows how these parameters affect the game tree and outcomes
  
  6. Tournament Simulation:
  
  Runs multiple games with alternating starting players
  
  Tracks and displays overall tournament results
  
  7. Software Engineering Aspects:
  
  Demonstrates good OOP principles with classes for nodes, input boxes, and the visualizer
  
  Shows clean state management between different application phases
  
  Includes robust input validation
  
  8. Visual Design:
  
  Color-codes different node types (max, min, pruned)
  
  Provides clear legends and instructions
  
  Animates the game tree construction

***This project serves as an excellent bridge between theoretical CS concepts and practical implementation, making it valuable for:

Computer science students learning about game AI

Educators looking for teaching tools

Anyone interested in understanding how chess AIs evaluate positions

Developers learning about algorithm visualization techniques

***Now let us discuss how this actually works: 
1. Input Phase:
You collect 3 inputs:

Starting player (0 = Cristiano, 1 = Lionel)

Cristiano’s strength (base value for AI evaluation)

Lionel’s strength (base value for AI evaluation)
#Strength Calculation
Each AI’s strength is converted into a numerical score using:
                    strength(x)=log2​(x+1)+10x​
Why log? Diminishing returns (a 10-strength AI isn’t 10× better than a 1-strength one).
Why x/10? Adds a linear scaling effect.
#Utility (Evaluation) Function
At the end of each branch (depth=5), the AI evaluates the position using:
utility=strength(maxV)−strength(minV)+random noise
Random noise (±0.1-0.2) simulates slight uncertainty in AI evaluations.

If utility > 0, the maximizing player (e.g., Cristiano) is winning.

If utility < 0, the minimizing player (e.g., Lionel) is winning.

2. Minimax Algorithm with Alpha-Beta Pruning
(A) How Minimax Works:
Maximizing player (Cristiano) picks moves that increase utility.

Minimizing player (Lionel) picks moves that decrease utility.

The AI recursively explores possible moves up to depth 5.

(B) Alpha-Beta Pruning
Optimization: Skips evaluating branches that won’t change the final decision.

Pruned nodes appear in red in your visualization.

(C) Final Decision
The root node (top of the tree) picks the best move based on Minimax.

3. Tournament Simulation
Four games are played (alternating starting players).

Each game generates a new Minimax tree and computes a winner.

Final results show total wins for Cristiano vs. Lionel.

