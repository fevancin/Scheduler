import csv
import json
from pathlib import Path
import argparse

from tools import generate_csv_results_file, generate_averages_plot, plot_all_instances

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

generate_csv_results_file(input_folder_path)

generate_averages_plot(input_folder_path)

if plot_instances:
    plot_all_instances(input_folder_path)