import argparse
from pathlib import Path
import json
from time import perf_counter
import pyomo.environ as pyo

from tools import get_monolitic_model, get_results_from_monolitic_model

parser = argparse.ArgumentParser(prog='monolitic.py', description='Solve monolitic model')
parser.add_argument('-i', '--input', type=Path, help='Folder with the instances', required=True)
parser.add_argument('--inefficient-operators', action='store_true', help='Use inefficient operator constraints')
parser.add_argument('-v', '--verbose', action='store_true')
args = parser.parse_args()

input_folder_path = Path(args.input).resolve()
verbose = bool(args.verbose)
use_inefficient_operators = bool(args.inefficient_operators)

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
        print(f'Start model {instance_path} creation')
    creation_start_time = perf_counter()
    model = get_monolitic_model(instance, use_inefficient_operators)
    creation_elapsed_time = perf_counter() - creation_start_time
    if verbose:
        print(f'End model  {instance_path} creation. Took {creation_elapsed_time} seconds.')

    opt = pyo.SolverFactory('gurobi')
    opt.options['TimeLimit'] = 60

    if verbose:
        print(f'Start  {instance_path} solving process')
    solving_start_time = perf_counter()
    model_results = opt.solve(model, tee=verbose)
    solving_elapsed_time = perf_counter() - solving_start_time
    if verbose:
        print(f'End  {instance_path} solving process. Took {solving_elapsed_time} seconds.')

    results = get_results_from_monolitic_model(model)

    model.solutions.store_to(model_results)
    solution = model_results.solution[0]
    lower_bound = float(model_results['problem'][0]['Lower bound'])
    upper_bound = float(model_results['problem'][0]['Upper bound'])
    gap = float(solution['gap'])
    value = float(solution['objective']['total_satisfied_service_durations_scaled_by_priority']['Value'])

    results['info'] = {
        'method': 'milp_monolitic',
        'model_creation_time': creation_elapsed_time,
        'model_solving_time': solving_elapsed_time,
        'solver_internal_time': float(model_results.solver.time),
        'status': str(model_results.solver.status),
        'termination_condition': str(model_results.solver.termination_condition),
        'lower_bound': lower_bound,
        'upper_bound': upper_bound,
        'gap': gap,
        'objective_function_value': value
    }

    # write results to file
    result_path = instance_path.parent.joinpath(f'SOL_{instance_path.name}')
    with open(result_path, 'w') as f:
        json.dump(results, f, indent=4)