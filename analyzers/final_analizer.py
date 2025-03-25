import csv
import json
from pathlib import Path
import argparse

from tools import plot_master_instance, plot_averages

parser = argparse.ArgumentParser(prog='Results analizer', description='This program is used to analize results')
parser.add_argument('-i', '--input', type=Path, help='Folder with instance groups results', required=True)
parser.add_argument('-p', '--plot-instances', action='store_true', help='If every instance will have its own plot')
parser.add_argument('-v', '--verbose', action='store_true')
args = parser.parse_args()

input_folder_path = Path(args.input).resolve()
verbose = bool(args.verbose)
plot_instances = bool(args.plot_instances)

# checks for file existance and validity
if not input_folder_path.exists():
    print('Input path not found')
    exit(1)

if not input_folder_path.is_dir():
    print('Input is not a directory')

results_data = []

group_names = []

model_creation_time_averages = []
model_solving_time_averages = []
solver_internal_time_averages = []

averages = {
    'model_creation_time': [],
    'model_solving_time': [],
    'solver_internal_time': []
}

# iterate every directory
for group_path in input_folder_path.iterdir():
    
    if not group_path.is_dir():
        continue

    model_creation_time_sum = 0.0
    model_solving_time_sum = 0.0
    solver_internal_time_sum = 0.0

    instance_number = 0

    # iterate every instance
    for results_path in group_path.iterdir():

        # only valid JSON files that starts with 'SOL_'
        if results_path.suffix != '.json':
            continue
        if results_path.name == 'info.json':
            continue
        if not results_path.name.startswith('SOL_'):
            continue

        with open(results_path, 'r') as file:
            results = json.load(file)

        # add those results to the result list
        results_info = results['info']
        results_info['group'] = results_path.parent.name
        results_info['instance'] = results_path.name

        results_data.append(results['info'])

        # keep track of the time sums for this group
        model_creation_time_sum += results_info['model_creation_time']
        model_solving_time_sum += results_info['model_solving_time']
        solver_internal_time_sum += results_info['solver_internal_time']

        # plot the instance
        if plot_instances:

            instance_path = results_path.parent.joinpath(results_path.name.removeprefix('SOL_'))
            with open(instance_path) as file:
                instance = json.load(file)
            
            plot_master_instance(instance, results, instance_path.parent.joinpath(instance_path.name.removesuffix('.json') + '.png'))

        # the istance number is used in the average computation
        instance_number += 1
    
    # if there is at least one valid instance in this group
    if instance_number > 0:

        # add the group name in a list
        group_name = group_path.name
        group_name = group_name.removeprefix('equal_resources_')
        group_names.append(group_name)
        
        # add averages in their respective lists
        averages['model_creation_time'].append(model_creation_time_sum / instance_number)
        averages['model_solving_time'].append(model_solving_time_sum / instance_number)
        averages['solver_internal_time'].append(solver_internal_time_sum / instance_number)

# plot the averages for each group
plot_averages(group_names, averages, input_folder_path.joinpath('time_averages.png'))

field_names = [
    'group',
    'instance',
    'method',
    'model_creation_time',
    'model_solving_time',
    'solver_internal_time',
    'status',
    'termination_condition',
    'lower_bound',
    'upper_bound',
    'gap',
    'objective_function_value'
]

# write results to csv file
with open(input_folder_path.joinpath('results.csv'), 'w', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=field_names, dialect='excel-tab')
    writer.writeheader()
    writer.writerows(results_data)