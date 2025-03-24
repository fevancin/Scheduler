import argparse
from pathlib import Path
import json

from tools import check_master_validity, check_subproblem_validity

parser = argparse.ArgumentParser(prog='Instance checker', description='This program is used to validate instance and results for correctness')
parser.add_argument('-i', '--input', type=Path, help='Folder with instances and/or results', required=True)
parser.add_argument('--ignore-results', action='store_true', help='If results are present, ignore them')
parser.add_argument('-v', '--verbose', action='store_true')
args = parser.parse_args()

input_folder_path = Path(args.input).resolve()
verbose = bool(args.verbose)
ignore_results = bool(args.ignore_results)

# checks for file existance and validity
if not input_folder_path.exists():
    print('Input path not found')
    exit(1)

if not input_folder_path.is_dir():
    print('Input is not a directory')

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
        print(f'Read instance {instance_path}')

    if ignore_results:
        if 'days' in instance:
            error_code, error_message = check_master_validity(instance)
        else:
            error_code, error_message = check_subproblem_validity(instance)

    # if it exists and is considered, read results file
    else:
        
        results_path = instance_path.parent.joinpath(f'SOL_{instance_path.name}')
        if results_path.exists():
            with open(results_path, 'r') as file:
                results = json.load(file)
            
            if verbose:
                print(f'Read results {results_path}')

            if 'days' in instance:
                error_code, error_message = check_master_validity(instance, results)
            else:
                error_code, error_message = check_subproblem_validity(instance, results)
    
        # if results are not found
        else:
            if verbose:
                print(f'Results {results_path} not found')
            
            if 'days' in instance:
                error_code, error_message = check_master_validity(instance)
            else:
                error_code, error_message = check_subproblem_validity(instance)
    
    # print the error message if is necessary
    if verbose or error_code != 0:
        print(f'[{error_code}] Instance {instance_path} has error: "{error_message}"')

if verbose:
    print('All tests done')