import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.patches import Patch
import numpy as np

def plot_averages(group_names, averages, save_path):
    x = np.arange(len(group_names))
    width = 0.25
    multiplier = 0

    fig, ax = plt.subplots(layout='constrained')

    for attribute, measurement in averages.items():

        offset = width * multiplier
        rects = ax.bar(x + offset, measurement, width, label=attribute)
        multiplier += 1
        
        if attribute == 'model_solving_time':
            ax.bar_label(rects, padding=3)

    ax.set_ylabel('Time (s)')
    ax.set_title('Average group solving times')
    ax.set_xticks(x + width, group_names)
    ax.legend(loc='upper right')

    plt.savefig(save_path)
    plt.close('all')


def plot_master_instance(instance, results, save_path):

    fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)
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

    fig.suptitle(f'Solution of instance', weight='bold')

    # plt.show()
    plt.savefig(save_path, dpi=500)
    plt.close('all')