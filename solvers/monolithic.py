import argparse
from pathlib import Path
import json
from time import perf_counter
import pyomo.environ as pyo

from tools import get_monolitic_model, get_results_from_monolitic_model

parser = argparse.ArgumentParser(prog='monolitic.py', description='Solve monolitic model')
parser.add_argument('-i', '--input', type=Path, help='Folder with the instances', required=True)
parser.add_argument('--inefficient-operators', action='store_true', help='Use inefficient operator constraints')
parser.add_argument('-s', '--solver', type=str, default='gurobi', choices=['gurobi', 'glpk'], help='The solver used')
parser.add_argument('-t', '--time-limit', type=int, help='Optional solver time limit')
parser.add_argument('-v', '--verbose', action='store_true')
args = parser.parse_args()

input_folder_path = Path(args.input).resolve()
use_inefficient_operators = bool(args.inefficient_operators)
solver = str(args.solver)
time_limit = args.time_limit
verbose = bool(args.verbose)

for instance_path in input_folder_path.iterdir():

    # the only valid files are JSON that don't start with 'SOL_'
    if not instance_path.is_file() or instance_path.is_dir():
        continue

    if instance_path.suffix != '.json':
        continue

    if str(instance_path.name).startswith('SOL_'):
        continue

    if instance_path.name == 'info.json':
        continue

    # read instance file
    with open(instance_path, 'r') as file:
        instance = json.load(file)

    if verbose:
        print(f'Start model creation of instance {instance_path}')
    creation_start_time = perf_counter()
    model = get_monolitic_model(instance, use_inefficient_operators)
    creation_elapsed_time = perf_counter() - creation_start_time
    if verbose:
        print(f'End model creation of instance {instance_path}. Took {creation_elapsed_time} seconds.')

    opt = pyo.SolverFactory(solver)

    if time_limit is not None:
        opt.options['TimeLimit'] = time_limit

    if verbose:
        print(f'Start solving process of instance {instance_path}')
    solving_start_time = perf_counter()
    if verbose:
        model_results = opt.solve(model, tee=True, logfile=f'{instance_path.removesuffix(".json")}.log')
    else:
        model_results = opt.solve(model)
    solving_elapsed_time = perf_counter() - solving_start_time
    if verbose:
        print(f'End solving process of instance {instance_path}. Took {solving_elapsed_time} seconds.')

    model.solutions.store_to(model_results)
    solution = model_results.solution[0]
    lower_bound = float(model_results['problem'][0]['Lower bound'])
    upper_bound = float(model_results['problem'][0]['Upper bound'])
    gap = float(solution['gap'])
    value = float(solution['objective']['total_satisfied_service_durations_scaled_by_priority']['Value'])

    results = {'info': {
        'method': 'milp_monolitic',
        'model_creation_time': creation_elapsed_time,
        'model_solving_time': solving_elapsed_time,
        'solver_internal_time': float(model_results.solver.time),
        'status': str(model_results.solver.status),
        'termination_condition': str(model_results.solver.termination_condition),
        'lower_bound': lower_bound,
        'upper_bound': upper_bound if upper_bound <= 1e9 else 'infinity',
        'gap': gap,
        'objective_function_value': value
    }}
    
    results.update(get_results_from_monolitic_model(model))

    # write results to file
    result_path = instance_path.parent.joinpath(f'SOL_{instance_path.name}')
    with open(result_path, 'w') as f:
        json.dump(results, f, indent=4)