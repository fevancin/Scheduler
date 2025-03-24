def check_services_validity(services, care_unit_names) -> tuple[int, str]:
    
    if type(services) is not dict:
        return (2, '"services" is not an object')
    
    for service_name, service in services.items():
    
        # check for service object validity
        if type(service_name) is not str or len(service_name) <= 0:
            return (3, f'service "{str(service_name)}" has an invalid name')
        if type(service) is not dict:
            return (3, f'service "{service_name}" is not an object')
    
        if len(service) != 2:
            return (4, f'service "{service_name}" has not the right attribute number')
    
        # care_unit checks
        if 'care_unit' not in service:
            return (5, f'"care_unit" attribute not found in service "{service_name}"')
        care_unit_name = service['care_unit']
        if type(care_unit_name) is not str:
            return (6, f'"care_unit" attribute name in service "{service_name}" is not a string')
        if len(care_unit_name) <= 0:
            return (7, f'"care_unit" attribute in service "{service_name}" is not valid')
        if care_unit_name not in care_unit_names:
            return (8, f'care unit "{service["care_unit"]} is not offered anywhere')
    
        # duration checks
        if 'duration' not in service:
            return (9, f'"duration" attribute not found in service "{service_name}"')
        duration = service['duration']
        if type(duration) is not int:
            return (10, f'"duration" attribute in service "{service_name}" is not an integer')
        if duration <= 0:
            return (11, f'"duration" attribute in service "{service_name}" is not a positive value')
    
    return (0, 'all ok')


def check_day_validity(day) -> tuple[int, str]:

    # check for day object validity
    if type(day) is not dict:
        return (1, 'day is not an object')
    
    for care_unit_name, care_unit in day.items():
        
        # check for care unit validity
        if type(care_unit_name) is not str:
            return (2, f'care unit name "{str(care_unit_name)}" is not a string')
        if len(care_unit_name) <= 0:
            return (3, f'care unit "{care_unit_name}" has not a valid name')
        if type(care_unit) is not dict:
            return (4, f'care unit "{care_unit_name}" is not an object')
        
        for operator_name, operator in care_unit.items():

            # operator checks
            if type(operator_name) is not str:
                return (5, f'operator name "{str(operator_name)}" in care unit "{care_unit_name}" is not a string')
            if len(operator_name) <= 0:
                return (6, f'operator name "{str(operator_name)}" in care unit "{care_unit_name}" has not a valid name')
            if type(operator) is not dict:
                return (7, f'operator "{str(operator_name)}" in care unit "{care_unit_name}" is not an object')
            if len(operator) != 2:
                return (8, f'operator object "{str(operator_name)}" in care unit "{care_unit_name}" has not the right attribute number')

            # operator start checks
            if 'start' not in operator:
                return (9, f'"start" attribute not found in operator "{operator_name}" of care unit "{care_unit_name}"')
            start = operator['start']
            if type(start) is not int:
                return (10, f'"start" attribute in operator "{operator_name}" of care unit "{care_unit_name}" is not an integer')
            if start < 0:
                return (11, f'"start" attribute in operator "{operator_name}" of care unit "{care_unit_name}" is not a non-negative value')
            
            # operator duration checks
            if 'duration' not in operator:
                return (12, f'"duration" attribute not found in operator "{operator_name}" of care unit "{care_unit_name}"')
            duration = operator['duration']
            if type(duration) is not int:
                return (13, f'"duration" attribute in operator "{operator_name}" of care unit "{care_unit_name}" is not an integer')
            if duration <= 0:
                return (14, f'"duration" attribute in operator "{operator_name}" of care unit "{care_unit_name}" is not a positive value')

    return (0, 'all ok')


def check_days_validity(days) -> tuple[int, str]:

    if type(days) is not dict:
        return (1, 'days is not an object')
    
    for day_name, day in days.items():
    
        # check for day validity
        if type(day_name) is not str:
            return (2, f'day name "{str(day_name)}" is not a string')
        if len(day_name) <= 0:
            return (3, f'day "{day_name}" has not a valid name')
        if type(day) is not dict:
            return (4, f'day "{day_name}" is not an object')
    
        error_code, error_message = check_day_validity(day)
        if error_code != 0:
            return (error_code, error_message)
    
    return (0, 'all ok')


def check_patients_validity(patients, service_names, min_day, max_day) -> tuple[int, str]:

    if type(patients) is not dict:
        return (1, f'patients is not an object')

    for patient_name, patient in patients.items():

        if type(patient_name) is not str:
            return (2, f'patient name "{str(patient_name)}" is not a string')
        if len(patient_name) <= 0:
            return (3, f'patient "{patient_name}" has not a valid name')
        if type(patient) is not dict:
            return (4, f'patient {patient_name} is not an object')
        
        if 'priority' in patient:
            if type(patient['priority']) is not int or patient['priority'] <= 0:
                return (5, f'patient {patient_name} has invalid priority')
        
        if 'protocols' not in patient or type(patient['protocols']) is not dict:
            return (6, f'patient {patient_name} has invalid protocols')
        
        for protocol_name, protocol in patient['protocols'].items():

            if 'initial_shift' not in protocol or type(protocol['initial_shift']) is not int:
                return (7, f'protocol {protocol_name} of patient {patient_name} has invalid initial_shift')
            if 'protocol_services' not in protocol or type(protocol['protocol_services']) is not list:
                return (8, f'protocol {protocol_name} of patient {patient_name} has invalid protocol_services')
            
            for protocol_service in protocol['protocol_services']:
            
                if type(protocol_service) is not dict:
                    return (9, f'protocol {protocol_name} of patient {patient_name} has an invalid protocol service')
            
                for key in ['service', 'start', 'tolerance', 'frequency', 'times']:
                    if key not in protocol_service:
                        return (10, f'{key} not in protocol {protocol_name} of patient {patient_name}')
                    if key != 'service' and type(protocol_service[key]) is not int:
                        return (11, f'{key} is not an int')
            
                if type(protocol_service['service']) is not str or len(protocol_service['service']) <= 0 or protocol_service['service'] not in service_names:
                    return (12, f'service name {protocol_service["service"]} is not valid in protocol {protocol_name} of patient {patient_name}')
                
                if protocol_service['tolerance'] < 0:
                    return (13, f'tolerance {protocol_service["tolerance"]} is not valid in service {protocol_service["service"]} protocol {protocol_name} of patient {patient_name}')
                if protocol_service['frequency'] < 0:
                    return (14, f'frequency {protocol_service["frequency"]} is not valid in service {protocol_service["service"]} protocol {protocol_name} of patient {patient_name}')
                if protocol_service['times'] < 1:
                    return (15, f'times {protocol_service["times"]} is not valid in service {protocol_service["service"]} protocol {protocol_name} of patient {patient_name}')
                
                if protocol_service['start'] + protocol['initial_shift'] + protocol_service['tolerance'] < min_day:
                    return (16, f'service {protocol_service["service"]} in protocol {protocol_name} of patient {patient_name} starts too early')
                if protocol_service['start'] + protocol['initial_shift'] + (protocol_service['times'] - 1) * protocol_service['frequency'] - protocol_service['tolerance'] > max_day:
                    return (17, f'service {protocol_service["service"]} in protocol {protocol_name} of patient {patient_name} ends too late')

    return (0, 'all ok')


def check_results_types(results, days) -> tuple[int, str]:

    for day_name, schedule in results['scheduled'].items():
        
        if day_name not in days.keys():
            return (5, f'day {day_name} does not exist')
        if type(schedule) is not list:
            return (1, f'schedule {schedule} is not a list')
        
        for schedule_item in schedule:
            for key in ['patient', 'service', 'care_unit', 'operator', 'time']:
                if key not in schedule_item:
                    return (2, f'{key} not in results schedule')
                if key != 'time' and type(schedule_item[key]) is not str:
                    return (3, f'{key} is not a string in results schedule')
            
            if type(schedule_item['time']) is not int:
                return (4, f'time is not an int in results schedule of patient{schedule_item["patient"]} of service {schedule_item["service"]}')
            
            if schedule_item['care_unit'] not in days[day_name].keys():
                return (6, f'care unit {schedule_item["care_unit"]} of schedule of patient{schedule_item["patient"]} of service {schedule_item["service"]} does not exist')
            if schedule_item['operator'] not in days[day_name][schedule_item['care_unit']].keys():
                return (7, f'operator {schedule_item["operator"]} of schedule of patient{schedule_item["patient"]} of service {schedule_item["service"]} does not exist')

    return (0, 'all ok')


def check_results_overlapping(results, services) -> tuple[int, str]:

    for day_name, day_schedule in results['scheduled'].items():

        for index in range(len(day_schedule) - 1):
            schedule = day_schedule[index]

            for other_index in range(index + 1, len(day_schedule)):
                other_schedule = day_schedule[other_index]
                
                is_same_patient = (schedule['patient'] == other_schedule['patient'])
                is_same_operator = (schedule['care_unit'] == other_schedule['care_unit'] and
                                    schedule['operator'] == other_schedule['operator'])
                
                if not is_same_patient and not is_same_operator:
                    continue

                start = schedule['time']
                end = schedule['time'] + services[schedule['service']]['duration']

                other_start = other_schedule['time']
                other_end = other_schedule['time'] + services[other_schedule['service']]['duration']

                if (start <= other_start and end > other_start) or (other_start <= start and other_end > start):
                    return (1, f'schedules ({schedule["service"]}, {schedule["patient"]}, {day_name}, {schedule["care_unit"]}, {schedule["operator"]}) and ({other_schedule["service"]}, {other_schedule["patient"]}, {day_name}, {other_schedule["care_unit"]}, {other_schedule["operator"]}) overlaps')

    return (0, 'all ok')


def check_results_operator_range(results, services, days) -> tuple[int, str]:
    
    for day_name, day in results['scheduled'].items():
        for schedule in day:

            patient_name = schedule['patient']
            service_name = schedule['service']
            service = services[service_name]
            care_unit_name = service['care_unit']
            service_duration = service['duration']
            
            operator_name = schedule['operator']
            operator = days[day_name][care_unit_name][operator_name]
            operator_start = operator['start']
            operator_duration = operator['duration']
            operator_end = operator_start + operator_duration

            service_start = schedule['time']
            service_end = service_start + service_duration
            
            if service_start < operator_start or service_end > operator_end:
                return (1, f'service {service_name} of patient {patient_name} satisfied in day {day_name} is done outside operator range.')

    return (0, 'all ok')


def check_results_windows_existance(results, patients) -> tuple[int, str]:
    
    for day_name, day in results['scheduled'].items():
        day_index = int(day_name)

        for schedule in day:

            patient_name = schedule['patient']
            service_name = schedule['service']

            is_inside_a_window = False

            for protocol in patients[patient_name]['protocols'].values():
                initial_shift = protocol['initial_shift']
                for protocol_service in protocol['protocol_services']:
                    if protocol_service['service'] != service_name:
                        continue

                    window_start = protocol_service['start'] + initial_shift - protocol_service['tolerance']

                    for _ in range(protocol_service['times']):
                        if day_index >= window_start and day_index <= window_start + 2 * protocol_service['tolerance']:
                            is_inside_a_window = True
                            break

                        window_start += protocol_service['frequency']

                    if is_inside_a_window:
                        break
                if is_inside_a_window:
                    break

            if not is_inside_a_window:
                return (1, f'service {service_name} of patient {patient_name} requested in day {day_name} is done outside any request window')

    return (0, 'all ok')


def check_results_validity(results, instance) -> tuple[int, str]:
    
    for key in ['scheduled', 'rejected']:
        if key not in results:
            return (1, f'{key} not in results')
    if type(results['scheduled']) is not dict:
        return (2, f'result\'s {key} is not an object')
    if type(results['rejected']) is not list:
        return (2, f'result\'s {key} is not a list')
    
    error_code, error_message = check_results_types(results, instance['days'])
    if error_code != 0:
        return (error_code, error_message)
    
    error_code, error_message = check_results_overlapping(results, instance['services'])
    if error_code != 0:
        return (error_code, error_message)
    
    error_code, error_message = check_results_operator_range(results, instance['services'], instance['days'])
    if error_code != 0:
        return (error_code, error_message)
    
    error_code, error_message = check_results_windows_existance(results, instance['patients'])
    if error_code != 0:
        return (error_code, error_message)
    
    return (0, 'all ok')


def check_master_validity(instance, results=None) -> tuple[int, str]:

    # check for key presence
    for key in ['services', 'days', 'patients']:
        if key not in instance:
            return (1, f'{key} not in instance')
    
    error_code, error_message = check_days_validity(instance['days'])
    if error_code != 0:
        return (2, error_message)

    # get all care unit names offered at least once in a day
    care_unit_names = set()
    for day in instance['days'].values():
        care_unit_names.update(day.keys())
    
    error_code, error_message = check_services_validity(instance['services'], care_unit_names)
    if error_code != 0:
        return (3, error_message)
    
    # get all service names offered at least once in a day
    service_names = set(instance['services'].keys())

    day_indexes = [int(day_name) for day_name in instance['days'].keys()]
    min_day = min(day_indexes)
    max_day = max(day_indexes)
        
    error_code, error_message = check_patients_validity(instance['patients'], service_names, min_day, max_day)
    if error_code != 0:
        return (4, error_message)

    if results is not None:
        error_code, error_message = check_results_validity(results, instance)
        if error_code != 0:
            return (5, error_message)
    
    return (0, 'all ok')


def check_requests_validity(requests, service_names) -> tuple[int, str]:

    if type(requests) is not list:
        return (1, 'requests is not a list')
    
    for request in requests:

        if type(request) is not dict:
            return (2, 'request item is not an object')
        
        for key in ['patient', 'service']:
            
            if key not in request:
                return (3, f'{key} not in request object')
            if type(request[key]) is not str:
                return (4, f'{key} value is not a string')
            
        if request['service'] not in service_names:
            return (5, f'service {request["service"]} is not in services')
    
    return (0, 'all ok')


def check_subproblem_validity(instance, results=None) -> tuple[int, str]:
    
    # check for key presence
    for key in ['services', 'day', 'requests']:
        if key not in instance:
            return (1, f'{key} not in instance')
    
    error_code, error_message = check_day_validity(instance['day'])
    if error_code != 0:
        return (2, error_message)

    # get all care unit names offered
    care_unit_names = set(instance['day'].keys())
    
    error_code, error_message = check_services_validity(instance['services'], care_unit_names)
    if error_code != 0:
        return (3, error_message)
    
    # get all service names offered at least once in a day
    service_names = set(instance['services'].keys())

    error_code, error_message = check_requests_validity(instance['requests'], service_names)
    if error_code != 0:
        return (4, error_message)
    
    return (0, 'all ok')