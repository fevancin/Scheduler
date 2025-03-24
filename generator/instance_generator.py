import argparse
from pathlib import Path
import yaml
import shutil
import random
import json
from datetime import datetime
import time

from tools import generate_master_instance, generate_subproblem_instance

try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

parser = argparse.ArgumentParser(prog='Instances generator', description='This program is used to generate random intances for the master or subproblem')
parser.add_argument('-c', '--config', type=Path, help='Configuration file path', required=True)
parser.add_argument('-o', '--output', type=Path, help='Output path', required=True)
parser.add_argument('-d', '--delete-prev', help='Remove previous instance data in the output location', action='store_true')
parser.add_argument('-v', '--verbose', action='store_true')
args = parser.parse_args()

config_path = Path(args.config).resolve()
output_folder_path = Path(args.output).resolve()

delete_prev = bool(args.delete_prev)
is_verbose = bool(args.verbose)

# checks for configuration file existance and validity
if not config_path.exists():
    print('Configuration file not found')
    exit(1)

if config_path.is_dir() or not config_path.is_file():
    print('Configuration must be a file')
    exit(1)

if config_path.suffix != '.yaml':
    print('Configuration file must be YAML')
    exit(1)

if output_folder_path.exists() and not output_folder_path.is_dir():
    print('The output must be a folder name')
    exit(1)

# read configuration file
with open(config_path, 'r') as file:
    config = yaml.load(file, Loader)

if is_verbose:
    print(f'Read config file in {config_path}')

# eventual default setting of missing parameters
if 'include_info_in_instances' not in config:
    config['include_info_in_instances'] = False

if 'include_info_in_group_folder' not in config:
    config['include_info_in_group_folder'] = False

random.seed(42)
group_index = 0
for group_config in config['groups']:

    if 'seed' not in group_config:
        group_config['seed'] = random.randint(1, 1000)
    
    if 'instance_number' not in group_config:
        group_config['instance_number'] = 1
    
    if 'instance_group_folder_name' not in group_config:
        group_config['instance_group_folder_name'] = f'group_{group_index}'
        group_index += 1

# eventual deletion of previous data
if delete_prev:

    shutil.rmtree(output_folder_path)

    if is_verbose:
        print(f'Deleted stuff, if present, in {output_folder_path}')

# if not present, create the output directory
if not output_folder_path.exists():

    output_folder_path.mkdir()

    if is_verbose:
        print(f'Created new folder {output_folder_path}')

timestamp = datetime.now().strftime('%a_%d_%m_%Y_%H_%M_%S')

if is_verbose:
    print(f'{timestamp} will be used as timestamp in those instances')
    total_instance_number = 0
    start_time = time.perf_counter()

# generate each group
for group_config in config['groups']:

    group_config['timestamp'] = timestamp

    # creation of the group directory
    group_path = output_folder_path.joinpath(group_config['instance_group_folder_name'])
    if not group_path.exists():
        group_path.mkdir()
        if is_verbose:
            print(f'Created new folder {group_path}')
    
    # if specified, add the configuration file in the group directory
    if config['include_info_in_group_folder'] is True:
        with open(group_path.joinpath('info.json'), 'w') as file:
            json.dump(group_config, file, indent=4)
    
    # each group instance will use the same seed
    random.seed(group_config['seed'])

    # generate each instance
    for instance_index in range(group_config['instance_number']):

        # if protocol info is provided then it's a master instance
        if 'protocol' in group_config:
            instance = generate_master_instance(group_config)
        else:
            instance = generate_subproblem_instance(group_config)
        
        # if specified, add the configuration infos in the instance file
        if config['include_info_in_instances'] is True:
            instance['info'] = group_config
        
        # write to file the current instance
        instance_path = group_path.joinpath(f'instance_{instance_index}.json')
        with open(instance_path, 'w') as file:
            json.dump(instance, file, indent=4)
    
    if is_verbose:
        print(f'Created {group_config["instance_number"]} instances in group {group_path}')
        total_instance_number += group_config['instance_number']

if is_verbose:
    print(f'Created {total_instance_number} instances in total. Took {time.perf_counter() - start_time} seconds.\nDone.')