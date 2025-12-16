import json
import sys
import datetime
from score_function import getSolutionScore
from optimized_solution import greedy_random_solution as greedy_random_solution_peaceful
from optimized_solution_small_town import greedy_random_solution as greedy_random_solution_small_town
from optimized_solution_suburbia import greedy_random_solution as greedy_random_solution_suburbia
from optimized_solution_epitech import greedy_random_solution as greedy_random_solution_epitech


def naive_solution(dataset):
    """
    Solution naïve : place une antenne Density sur chaque bâtiment.
    
    Avantages :
    - Garantit la couverture de tous les bâtiments
    - Garantit que la capacité n'est jamais dépassée
    
    Inconvénients :
    - Très coûteux !
    - Beaucoup d'antennes inutiles
    
    À VOUS D'AMÉLIORER CETTE SOLUTION !
    """
    antennas = []
    
    for building in dataset['buildings']:
        antenna = {
            "type": "Density",
            "x": building['x'],
            "y": building['y'],
            "buildings": [building['id']]
        }
        antennas.append(antenna)
    
    solution = {
        "antennas": antennas
    }
    
    return solution


def main():
    datasets = [
        "1_peaceful_village",
        "2_small_town",
        "3_suburbia",
        "4_epitech",
        "5_isogrid",
        "6_manhattan"]
    
    selected_dataset = datasets[3]  # 4_epitech
    time_now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    input_file = './datasets/' + selected_dataset + '.json'    
    
    print(f"Chargement du dataset : {input_file}")
    dataset = json.load(open(input_file))
    
    print(f"Nombre de bâtiments : {len(dataset['buildings'])}")
    
    print("\nGénération de la solution...")
    
    # Sélectionner la bonne fonction selon le dataset
    if selected_dataset == "1_peaceful_village":
        solution_text = greedy_random_solution_peaceful(json.dumps(dataset))
    elif selected_dataset == "2_small_town":
        solution_text = greedy_random_solution_small_town(json.dumps(dataset))
    elif selected_dataset == "3_suburbia":
        solution_text = greedy_random_solution_suburbia(json.dumps(dataset))
    elif selected_dataset == "4_epitech":
        solution_text = greedy_random_solution_epitech(json.dumps(dataset))
    else:
        solution_text = greedy_random_solution_peaceful(json.dumps(dataset))  # fallback
    
    solution = json.loads(solution_text)
    
    print(f"Solution générée avec {len(solution)} antennes")
    
    # Calcul du coût (optionnel, pour information)
    cost, isValid, message = getSolutionScore(json.dumps({"antennas": solution}), json.dumps(dataset) )
    print(message)
    
    if isValid:
        output_file = f'./solutions/solution_{selected_dataset}_{cost}_{time_now}.json'
        with open(output_file, 'w') as f:
            json.dump({"antennas": solution}, f, indent=2)
            print(f"Solution sauvegardée dans {output_file}")


if __name__ == "__main__":
    main()