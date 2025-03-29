import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.patches import Patch
import numpy as np
import csv
import json
from pathlib import Path


def get_total_window_number(instance):
    
    window_number = 0

    for patient in instance['patients'].values():
        for protocol in patient['protocols'].values():

            initial_shift = protocol['initial_shift']
            
            for protocol_service in protocol['protocol_services']:

                start = protocol_service['start'] + initial_shift
                tolerance = protocol_service['tolerance']
                frequency = protocol_service['frequency']
                times = protocol_service['times']

                for central_day_index in range(start, start + frequency * times, frequency):

                    is_window_inside = False

                    for day_index in range(central_day_index - tolerance, central_day_index + tolerance):

                        day_name = str(day_index)

                        if day_name in instance['days']:
                            is_window_inside = True
                            break
                    
                    if is_window_inside:
                        window_number += 1
        
    return window_number


def get_normalized_disponibility_vs_requests(instance):

    days_disponibility = {}

    for day_name, day in instance['days'].items():

        days_disponibility[day_name] = 0
        
        for care_unit in day.values():
            for operator in care_unit.values():
                days_disponibility[day_name] += operator['duration']

    worst_case_request_scenario = {day_name: 0 for day_name in instance['days'].keys()}
    tolerance_sum = 0
    window_number = 0

    for patient in instance['patients'].values():
        for protocol in patient['protocols'].values():

            initial_shift = protocol['initial_shift']
            
            for protocol_service in protocol['protocol_services']:

                service_name = protocol_service['service']
                service_duration = instance['services'][service_name]['duration']

                start = protocol_service['start'] + initial_shift
                tolerance = protocol_service['tolerance']
                frequency = protocol_service['frequency']
                times = protocol_service['times']

                for central_day_index in range(start, start + frequency * times, frequency):

                    is_window_inside = False

                    for day_index in range(central_day_index - tolerance, central_day_index + tolerance):

                        day_name = str(day_index)

                        if day_name in instance['days']:
                            worst_case_request_scenario[day_name] += service_duration
                            is_window_inside = True

                    if is_window_inside:
                        window_number += 1
                        tolerance_sum += tolerance

    disponibility_vs_requests = sum([days_disponibility[day_name] / worst_case_request_scenario[day_name] for day_name in instance['days'].keys() if worst_case_request_scenario[day_name] > 0])
    average_tolerance = tolerance_sum / window_number

    return disponibility_vs_requests / average_tolerance


def get_average_time_slots_per_care_unit(instance):

    time_slots_global_sum = 0
    care_unit_number = 0

    for day in instance['days'].values():
        for care_unit in day.values():

            care_unit_number += 1
            
            for operator in care_unit.values():
                time_slots_global_sum += operator['duration']
    
    return time_slots_global_sum / care_unit_number


def get_max_request_in_same_day_per_patient(instance):

    day_number = len(instance['days'].keys())
    min_day = min([int(day_name) for day_name in instance['days'].keys()])

    overlap_window_day_number = 0

    for patient in instance['patients'].values():

        windows = []

        for protocol in patient['protocols'].values():
            
            initial_shift = protocol['initial_shift']
            
            for protocol_service in protocol['protocol_services']:

                start = protocol_service['start'] + initial_shift
                tolerance = protocol_service['tolerance']
                frequency = protocol_service['frequency']
                times = protocol_service['times']

                for central_day_index in range(start, start + frequency * times, frequency):

                    window = {
                        'start': central_day_index - tolerance,
                        'end': central_day_index + tolerance
                    }

                    if window['start'] < min_day:
                        window['start'] = min_day
                    if window['end'] > min_day + day_number - 1:
                        window['end'] = min_day + day_number - 1
                    
                    if window['end'] >= window['start']:
                        windows.append(window)
        
        for index in range(len(windows) - 1):
            for other_index in range(index + 1, len(windows)):

                if (windows[index]['start'] <= windows[other_index]['start'] and windows[index]['end'] >= windows[other_index]['start']):
                    min_end = min(windows[index]['end'], windows[other_index]['end'])
                    overlap_window_day_number += min_end - windows[other_index]['start']
                    continue

                if (windows[other_index]['start'] <= windows[index]['start'] and windows[other_index]['end'] >= windows[index]['start']):
                    min_end = min(windows[index]['end'], windows[other_index]['end'])
                    overlap_window_day_number += min_end - windows[index]['start']

    return overlap_window_day_number


def generate_csv_instances_file(input_folder_path, group_prefix=None):
    
    results_data = []

    # iterate every directory
    for group_path in input_folder_path.iterdir():
        
        if not group_path.is_dir():
            continue

        if group_prefix is not None and not group_path.name.startswith(group_prefix):
            continue

        # iterate every instance
        for instance_path in group_path.iterdir():

            # only valid JSON files that starts with 'SOL_'
            if instance_path.suffix != '.json':
                continue
            if instance_path.name == 'info.json':
                continue
            if instance_path.name.startswith('SOL_'):
                continue

            with open(instance_path, 'r') as file:
                instance = json.load(file)
            
            # compute request number
            window_number = get_total_window_number(instance)

            # add results to the result object
            results_info = {}
            results_info['group'] = instance_path.parent.name
            results_info['instance'] = instance_path.name
            results_info['window_number'] = window_number
            results_info['average_windows_per_patient'] = window_number / len(instance['patients'].keys())
            results_info['normalized_disponibility_vs_requests'] = get_normalized_disponibility_vs_requests(instance)
            results_info['average_time_slots_per_care_unit'] = get_average_time_slots_per_care_unit(instance)
            results_info['max_request_in_same_day_per_patient'] = get_max_request_in_same_day_per_patient(instance)

            results_data.append(results_info)

    field_names = [
        'group',
        'instance',
        'window_number',
        'average_windows_per_patient',
        'normalized_disponibility_vs_requests',
        'average_time_slots_per_care_unit',
        'max_request_in_same_day_per_patient'
    ]

    # write results to csv file
    with open(input_folder_path.joinpath('instances.csv'), 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=field_names, dialect='excel-tab')
        writer.writeheader()
        writer.writerows(results_data)


def generate_csv_results_file(input_folder_path, group_prefix=None):
    
    results_data = []

    # iterate every directory
    for group_path in input_folder_path.iterdir():
        
        if not group_path.is_dir():
            continue

        if group_prefix is not None and not group_path.name.startswith(group_prefix):
            continue

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
            
            # compute request numbers
            rejected_request_number = len(results['rejected'])
            request_number = rejected_request_number
            for day in results['scheduled'].values():
                request_number += len(day)

            # add those results to the result object
            results_info = results['info']
            results_info['group'] = results_path.parent.name
            results_info['instance'] = results_path.name
            results_info['request_number'] = request_number
            results_info['rejected_request_number'] = rejected_request_number

            results_data.append(results_info)

    field_names = [
        'group',
        'instance',
        'request_number',
        'rejected_request_number',
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


def plot_averages(group_names, averages, save_path):

    x = np.arange(len(group_names))
    width = 0.25
    multiplier = 0

    fig, ax = plt.subplots()

    for attribute, measurement in averages.items():

        offset = width * multiplier
        rects = ax.bar(x + offset, measurement, width, label=attribute)
        multiplier += 1
        
        if attribute == 'model_solving_time':
            ax.bar_label(rects, padding=3, fontsize=5)

    ax.set_ylabel('Time (s)')
    ax.set_title('Average group solving times')
    ax.set_xticks(x + width, group_names, fontsize=5)
    ax.legend(loc='upper right')

    plt.savefig(save_path)
    plt.close('all')


def generate_averages_plot(input_folder_path, group_prefix=None):

    group_names = []

    averages = {
        'model_creation_time': [],
        'model_solving_time': [],
        'solver_internal_time': []
    }

    # iterate every directory
    for group_path in input_folder_path.iterdir():
        
        if not group_path.is_dir():
            continue

        if group_prefix is not None and not group_path.name.startswith(group_prefix):
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

            # keep track of the time sums for this group
            results_info = results['info']
            model_creation_time_sum += results_info['model_creation_time']
            model_solving_time_sum += results_info['model_solving_time']
            solver_internal_time_sum += results_info['solver_internal_time']

            # the istance number is used in the average computation
            instance_number += 1
        
        # if there is at least one valid instance in this group
        if instance_number > 0:

            # add the group name in a list
            group_name = group_path.name
            group_name = group_name.removeprefix('equal_resources_')
            group_name = group_name.removeprefix('operator_overlap_')
            group_name = group_name.removeprefix('requests_')
            group_name = group_name.removeprefix('var_patients_')
            group_names.append(group_name)
            
            # add averages in their respective lists
            averages['model_creation_time'].append(model_creation_time_sum / instance_number)
            averages['model_solving_time'].append(model_solving_time_sum / instance_number)
            averages['solver_internal_time'].append(solver_internal_time_sum / instance_number)

    # plot the averages for each group
    plot_averages(group_names, averages, input_folder_path.joinpath('time_averages.png'))


def plot_master_instance(instance, results, save_path):

    fig, (ax1, ax2) = plt.subplots(2, 1)
    fig.set_size_inches(16, 8)

    slot_width = 2.0
    space_between_days = 0.2 * slot_width
    colors = 'rgbcmy'

    day_number = len(instance['days'])

    # tracks care_unit bar position
    care_unit_x_position = 0
    care_unit_x_positions = {}
    day_x_positions = {}

    max_total_care_unit_duration = 0
    care_unit_names = set()

    # draw upper graphic (total care unit requests per each day)
    plt.sca(ax1)

    for day_name, day in instance['days'].items():

        care_unit_x_positions[day_name] = {}
        day_x_positions[day_name] = care_unit_x_position + len(day) * slot_width * 0.5
        
        for care_unit_name, care_unit in day.items():

            care_unit_names.add(care_unit_name)
            care_unit_x_positions[day_name][care_unit_name] = care_unit_x_position

            total_care_unit_duration = 0
            for operator in care_unit.values():
                total_care_unit_duration += operator['duration']
            
            if total_care_unit_duration > max_total_care_unit_duration:
                max_total_care_unit_duration = total_care_unit_duration

            # each care unit has an horizontal bold line indicating its own total duration
            plt.hlines(xmin=care_unit_x_position, xmax=care_unit_x_position + slot_width, y=total_care_unit_duration, colors='black', lw=2, zorder=0)
            
            care_unit_x_position += slot_width

        care_unit_x_position += space_between_days

    last_care_unit_x_position = care_unit_x_position
    day_x_positions[str(day_number)] = last_care_unit_x_position + space_between_days * 0.5

    # draw thin vertical lines between each day
    for positions in care_unit_x_positions.values():

        if len(positions) == 0:
            continue

        # find the first bar x position
        min_care_unit_x_position = 100000
        for care_unit_x_position in positions.values():
            if care_unit_x_position < min_care_unit_x_position:
                min_care_unit_x_position = care_unit_x_position

        plt.vlines(x=(min_care_unit_x_position - space_between_days * 0.5), ymin = 0, ymax=max_total_care_unit_duration, colors='grey', lw=0.5, ls=':', zorder=0)
    # last day right vertical line
    plt.vlines(x=(last_care_unit_x_position + space_between_days * 0.5), ymin = 0, ymax=max_total_care_unit_duration, colors='grey', lw=0.5, ls=':', zorder=0)

    # assign a color to each care unit encountered
    care_unit_colors = {}
    for care_unit_index, care_unit_name in enumerate(care_unit_names):
        care_unit_colors[care_unit_name] = colors[int(care_unit_index % len(colors))]

    # draw boxes
    care_unit_heights = {}
    for day_name, day_requests in results['scheduled'].items():
        for request in day_requests:
            patient_name = request['patient']
            service_name = request['service']
                
            care_unit_name = instance['services'][service_name]['care_unit']
            duration = instance['services'][service_name]['duration']

            if day_name not in care_unit_heights:
                care_unit_heights[day_name] = {}
            if care_unit_name not in care_unit_heights[day_name]:
                care_unit_heights[day_name][care_unit_name] = 0

            ax1.add_patch(Rectangle(
                (care_unit_x_positions[day_name][care_unit_name] + space_between_days, care_unit_heights[day_name][care_unit_name]),
                slot_width - space_between_days,
                duration,
                linewidth=1, edgecolor='k', lw=1.5,
                facecolor=care_unit_colors[care_unit_name], zorder=1))
            
            care_unit_heights[day_name][care_unit_name] += duration

    # creation of the legend with all care unit colors
    patch_list = []
    for care_unit_name, care_unit_color in care_unit_colors.items():
        patch_list.append(Patch(facecolor=care_unit_color, label=care_unit_name))
    ax1.legend(handles=patch_list)

    ax1.set_title('Care unit total occupation')
    ax1.set_ylabel('Total request slots', weight='bold', labelpad=8)

    # draw lower graphic (patient protocol requests)
    plt.sca(ax2)

    # vertical position of the boxes
    request_y_position = 0

    slot_height = 1.0
    space_between_rows = slot_height * 0.2

    request_labels = {}
    request_y_positions = {}

    # draw request intervals
    for patient_name, patient in instance['patients'].items():
        for protocol in patient['protocols'].values():
            initial_shift = protocol['initial_shift']
            for service_protocol in protocol['protocol_services']:

                service_start = service_protocol['start']
                frequency = service_protocol['frequency']
                tolerance = service_protocol['tolerance']
                care_unit_name = instance['services'][service_protocol['service']]['care_unit']
                
                request_labels[request_y_position + 0.5 * slot_height] = f'{patient_name} - {service_protocol["service"]}'
                request_y_positions[(patient_name, service_protocol['service'])] = request_y_position + 0.5 * slot_height

                for index in range(service_protocol['times']):

                    start = initial_shift + service_start + frequency * index - tolerance
                    end = initial_shift + service_start + frequency * index + tolerance + 1

                    # clamp the window to [0; day_number] and discard fully-outside windows
                    if start >= day_number:
                        continue
                    if start < 0:
                        start = 0
                        if end < 0:
                            continue
                    if end < 0:
                        continue
                    if end > day_number:
                        end = day_number
                        if start > day_number:
                            continue
                    
                    start_day_len = len(instance['days'][str(start)])
                    if end == day_number:
                        end_day_len = 0
                    else:
                        end_day_len = len(instance['days'][str(end)])

                    start = day_x_positions[str(start)] - start_day_len * slot_width * 0.5
                    end = day_x_positions[str(end)] - end_day_len * slot_width * 0.5

                    plt.hlines(
                        xmin=start, xmax=end,
                        y=request_y_position + space_between_rows + (slot_height - space_between_rows) * 0.5,
                        lw=2, colors=care_unit_colors[care_unit_name], zorder=2)
                    plt.vlines(
                        x=start,
                        ymin=request_y_position + space_between_rows + space_between_rows,
                        ymax=request_y_position + space_between_rows + (slot_height - space_between_rows * 2),
                        lw=1.5, colors=care_unit_colors[care_unit_name], zorder=2)
                    plt.vlines(
                        x=end,
                        ymin=request_y_position + space_between_rows + space_between_rows,
                        ymax=request_y_position + space_between_rows + (slot_height - space_between_rows * 2),
                        lw=1.5, colors=care_unit_colors[care_unit_name], zorder=2)

                request_y_position += slot_height

    # draw black marks where services are scheduled
    for day_name, day_requests in results['scheduled'].items():
        for request in day_requests:
            patient_name = request['patient']
            service_name = request['service']
            care_unit_name = instance['services'][service_name]['care_unit']
            day_len = len(instance['days'][day_name])
            pos = day_x_positions[day_name]
            plt.plot(pos, request_y_positions[(patient_name, service_name)] + space_between_rows * 0.5, 'x', color='k')

    # draw thin vertical lines between each day
    for day_name, day in instance['days'].items():
        plt.vlines(x=(day_x_positions[day_name] - len(day) * slot_width * 0.5), ymin = 0, ymax=request_y_position, colors='grey', lw=0.5, ls=':', zorder=0)
    # last day right vertical line
    plt.vlines(x=(last_care_unit_x_position + space_between_days * 0.5), ymin = 0, ymax=request_y_position, colors='grey', lw=0.5, ls=':', zorder=0)

    # add axis ticks
    ax2.set_xticks(list(day_x_positions.values())[:-1], labels=list(care_unit_x_positions.keys()))
    ax2.set_yticks(list(request_labels.keys()), labels=list(request_labels.values()))

    ax2.set_title('Patient request windows')
    ax2.set_xlabel('Days', weight='bold', labelpad=6)
    ax2.set_ylabel('Requests', weight='bold', labelpad=8)

    fig.suptitle(f'Solution of instance {save_path.name.removesuffix(".png")}', weight='bold')

    plt.savefig(save_path, dpi=500)
    plt.close('all')


def plot_all_instances(input_folder_path, group_prefix=None):

    # iterate every directory
    for group_path in input_folder_path.iterdir():

        if not group_path.is_dir():
            continue

        if group_prefix is not None and not group_path.name.startswith(group_prefix):
            continue

        # iterate every instance
        for instance_path in group_path.iterdir():

            # only valid JSON files that starts with 'SOL_'
            if instance_path.suffix != '.json':
                continue
            if instance_path.name == 'info.json':
                continue
            if instance_path.name.startswith('SOL_'):
                continue

            with open(instance_path, 'r') as file:
                instance = json.load(file)
            
            group_path.joinpath('plots').mkdir(exist_ok=True)
            plot_instance_care_unit_fullness(instance, instance_path.parent.joinpath('plots').joinpath(Path(f'fullness_cu_{instance_path.name.removesuffix(".json")}.png')))
            plot_instance_patients_fullness(instance, instance_path.parent.joinpath('plots').joinpath(Path(f'fullness_pat_{instance_path.name.removesuffix(".json")}.png')))
            
            results_path = instance_path.parent.joinpath(f'SOL_{instance_path.name}')
            if results_path.exists():
                with open(results_path) as file:
                    results = json.load(file)
                
                plot_master_instance(instance, results, instance_path.parent.joinpath(instance_path.name.removesuffix('.json') + '.png'))


def plot_instance_care_unit_fullness(instance, save_path):

    day_names = sorted(instance['days'].keys(), key=lambda v: int(v))
    
    care_unit_names = set()
    for day in instance['days'].values():
        care_unit_names.update(day.keys())
    care_unit_names = sorted(care_unit_names)
    
    day_care_unit_capacity = []
    for care_unit_name in care_unit_names:
        row = []
        for day_name in day_names:
            row.append(sum(operator['duration'] for operator in instance['days'][day_name][care_unit_name].values()))
        day_care_unit_capacity.append(row)

    requests_per_day_care_unit = []
    spread_requests_per_day_care_unit = []
    for _ in range(len(care_unit_names)):
        requests_per_day_care_unit.append([0 for _ in range(len(day_names))])
        spread_requests_per_day_care_unit.append([0 for _ in range(len(day_names))])

    for patient in instance['patients'].values():
        for protocol in patient['protocols'].values():

            initial_shift = protocol['initial_shift']
            
            for protocol_service in protocol['protocol_services']:

                service_name = protocol_service['service']
                care_unit_name = instance['services'][service_name]['care_unit']
                service_duration = instance['services'][service_name]['duration']

                start = protocol_service['start'] + initial_shift
                tolerance = protocol_service['tolerance']
                frequency = protocol_service['frequency']
                times = protocol_service['times']

                for central_day_index in range(start, start + frequency * times, frequency):
                    for day_index in range(central_day_index - tolerance, central_day_index + tolerance):
                        day_name = str(day_index)
                        if day_name not in day_names or care_unit_name not in care_unit_names:
                            continue

                        coordinate = (day_names.index(day_name), care_unit_names.index(care_unit_name))
                        requests_per_day_care_unit[coordinate[1]][coordinate[0]] += service_duration
                        spread_requests_per_day_care_unit[coordinate[1]][coordinate[0]] += service_duration / (2 * tolerance + 1)

    fig, (ax1, ax2) = plt.subplots(2, 1)
    
    plt.sca(ax1)

    ax1.imshow(requests_per_day_care_unit)

    ax1.set_xticks(range(len(day_names)), labels=day_names, rotation=45, ha="right", rotation_mode="anchor")
    ax1.set_yticks(range(len(care_unit_names)), labels=care_unit_names)

    for j in range(len(day_names)):
        for i in range(len(care_unit_names)):
            ax1.text(j, i, round(requests_per_day_care_unit[i][j] / day_care_unit_capacity[i][j], 3), ha="center", va="center", color="w", fontsize=3)

    plt.sca(ax2)

    ax2.imshow(spread_requests_per_day_care_unit)

    ax2.set_xticks(range(len(day_names)), labels=day_names, rotation=45, ha="right", rotation_mode="anchor")
    ax2.set_yticks(range(len(care_unit_names)), labels=care_unit_names)

    for j in range(len(day_names)):
        for i in range(len(care_unit_names)):
            ax2.text(j, i, round(spread_requests_per_day_care_unit[i][j] / day_care_unit_capacity[i][j], 3), ha="center", va="center", color="w", fontsize=3)
    
    ax1.set_title("Care units occupation percentages")
    ax2.set_title("Spreaded occupation percentages")
    fig.suptitle(f'Instance {save_path.name.removesuffix(".png")}', weight='bold')
    fig.tight_layout()

    plt.savefig(save_path, dpi=500)
    plt.close('all')


def plot_instance_patients_fullness(instance, save_path):

    day_names = sorted(instance['days'].keys(), key=lambda v: int(v))
    
    patient_names = sorted(instance['patients'].keys())

    requests_per_day_patient = []
    spread_requests_per_day_patient = []
    for _ in range(len(patient_names)):
        requests_per_day_patient.append([0 for _ in range(len(day_names))])
        spread_requests_per_day_patient.append([0 for _ in range(len(day_names))])

    for patient_name, patient in instance['patients'].items():
        for protocol in patient['protocols'].values():

            initial_shift = protocol['initial_shift']
            
            for protocol_service in protocol['protocol_services']:

                start = protocol_service['start'] + initial_shift
                tolerance = protocol_service['tolerance']
                frequency = protocol_service['frequency']
                times = protocol_service['times']

                for central_day_index in range(start, start + frequency * times, frequency):
                    for day_index in range(central_day_index - tolerance, central_day_index + tolerance):
                        day_name = str(day_index)
                        if day_name not in day_names:
                            continue

                        coordinate = (day_names.index(day_name), patient_names.index(patient_name))
                        requests_per_day_patient[coordinate[1]][coordinate[0]] += 1
                        spread_requests_per_day_patient[coordinate[1]][coordinate[0]] += 1 / (2 * tolerance + 1)

    fig, (ax1, ax2) = plt.subplots(2, 1)
    
    plt.sca(ax1)

    ax1.imshow(requests_per_day_patient)

    ax1.set_xticks(range(len(day_names)), labels=day_names, rotation=45, ha="right", rotation_mode="anchor", fontsize=3)
    ax1.set_yticks(range(len(patient_names)), labels=patient_names, fontsize=3)

    for j in range(len(day_names)):
        for i in range(len(patient_names)):
            ax1.text(j, i, requests_per_day_patient[i][j], ha="center", va="center", color="w", fontsize=3)

    plt.sca(ax2)

    ax2.imshow(spread_requests_per_day_patient)

    ax2.set_xticks(range(len(day_names)), labels=day_names, rotation=45, ha="right", rotation_mode="anchor", fontsize=3)
    ax2.set_yticks(range(len(patient_names)), labels=patient_names, fontsize=3)

    for j in range(len(day_names)):
        for i in range(len(patient_names)):
            ax2.text(j, i, round(spread_requests_per_day_patient[i][j], 3), ha="center", va="center", color="w", fontsize=3)
    
    ax1.set_title("Patient occupation percentages")
    ax2.set_title("Spreaded occupation percentages")
    fig.suptitle(f'Instance {save_path.name.removesuffix(".png")}', weight='bold')
    fig.tight_layout()

    plt.savefig(save_path, dpi=500)
    plt.close('all')