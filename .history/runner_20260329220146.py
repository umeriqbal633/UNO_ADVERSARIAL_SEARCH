import sys
import os
from uno_game import UNOGame, print_tree

def generate_simulation_output():
    game = UNOGame(p3_mode='simulation')
    
    with open('simulation_output.txt', 'w', encoding='utf-8') as f:
        sys.stdout = f
        print("UNO GAME SIMULATION & SEARCH TREES")
        print("="*60)
        
        # Print initial game state logged in game.log
        for line in game.log:
            print(line)
        
        # We will simulate 6 turns (2 full rounds) to demonstrate all players and trees
        for _ in range(6):
            if game.game_over:
                break
                
            log_start_idx = len(game.log)
            game.step()
            
            # Write turn logs
            for line in game.log[log_start_idx:]:
                print(line)
                
            # Write generated tree for this turn
            turn = game.turn_number
            player_idx = (turn - 1) % 3
            print("\n----- GENERATED SEARCH TREE -----")
            if player_idx == 0:
                print("Strategy: Defensive Minimax (Player 1)")
                tree = game.tree_logs.get(f"Turn {turn} P1")
                if tree: print_tree(tree, max_children=4)
            elif player_idx == 1:
                print("Strategy: Offensive Expectimax (Player 2)")
                tree = game.tree_logs.get(f"Turn {turn} P2")
                if tree: print_tree(tree, max_children=4)
            elif player_idx == 2:
                print("Strategy: Balanced Minimax (Player 3)")
                tree = game.tree_logs.get(f"Turn {turn} P3")
                if tree: print_tree(tree, max_children=4)
            print("\n")
            
        sys.stdout = sys.__stdout__

if __name__ == '__main__':
    generate_simulation_output()