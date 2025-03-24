import random


def generate_value(config):

    # if a fixed value is specified
    if type(config) is int or type(config) is float:
        return config
    
    # gaussian distribution
    if 'average' in config:
        
        # add the default standard deviation if not present
        if 'standard_deviation' not in config:
            config['standard_deviation'] = 1.0
    
        value = int(random.gauss(mu=config['average'], sigma=config['standard_deviation']))
    
        # clamp in order to respect eventual bounds
        if 'min' in config and value < config['min']:
            return config['min']
        if 'max' in config and value > config['max']:
            return config['max']
        return value
    
    # uniform distribution
    if 'min' in config:
        return random.randint(config['min'], config['max'])
    return random.randint(0, config['max'])


def generate_service(config, service_index=None):

    # get the maximum care unit number
    if type(config['day']['care_unit_number']) is int:
        care_unit_number = config['day']['care_unit_number']
    else:
        care_unit_number = config['day']['care_unit_number']['max']

    # select a care unit for the service
    if config['service']['care_unit_strategy'] == 'random':
        care_unit_index = random.randint(0, care_unit_number - 1)
    elif config['service']['care_unit_strategy'] == 'balanced':
        care_unit_index = service_index % care_unit_number

    # compute the service duration
    if (type(config['service']['duration']) is not int and
        ('min' not in config['service']['duration'] or config['service']['duration']['min'] < 1)):
        config['service']['duration']['min'] = 1
    duration = generate_value(config['service']['duration'])

    return {
        'care_unit': f'cu{care_unit_index:02}',
        'duration': duration
    }


def generate_operator(config, operator_index=None):
    
    # every operator occupy all time slots
    if config['operator']['strategy'] == 'fill':
        start = 0
        duration = config['day']['time_slots']
    
    # a random duration is computed
    elif config['operator']['strategy'] == 'random':

        duration = generate_value(config['operator']['duration'])
        start = random.randint(0, config['day']['time_slots'] - duration)
    
    # each operator overlaps with the next one by a certain percentage
    elif config['operator']['strategy'] == 'overlap':

        overlap_percentage = config['operator']['overlap_percentage']
        duration = generate_value(config['operator']['duration'])
        start = operator_index * int(duration * (1.0 - overlap_percentage))

    return {
        'start': start,
        'duration': duration
    }
    

def generate_care_unit(config):

    # compute the care unit size
    if (type(config['day']['operators_per_care_unit']) is not int and
        ('min' not in config['day']['operators_per_care_unit'] or config['day']['operators_per_care_unit']['min'] < 1)):
        config['day']['operators_per_care_unit']['min'] = 1
    operator_number = generate_value(config['day']['operators_per_care_unit'])
    
    care_unit = {}

    if config['operator']['strategy'] == 'overlap':
        for operator_index in range(operator_number):
            care_unit[f'op{operator_index:02}'] = generate_operator(config, operator_index)
    else:
        for operator_index in range(operator_number):
            care_unit[f'op{operator_index:02}'] = generate_operator(config)

    return care_unit


def generate_day(config):

    day = {}

    # the day has all care units
    if type(config['day']['care_unit_number']) is int:
        care_unit_indexes = range(config['day']['care_unit_number'])
    
    # choose only some care units
    else:
        if 'min' not in config['day']['care_unit_number'] or config['day']['care_unit_number']['min'] < 1:
            config['day']['care_unit_number']['min'] = 1
        care_unit_number = generate_value(config['day']['care_unit_number'])
        max_care_unit_number = config['day']['care_unit_number']['max']

        care_unit_indexes = sorted(random.sample(range(max_care_unit_number - 1), k=care_unit_number))
    
    for care_unit_index in care_unit_indexes:
        day[f'cu{care_unit_index:02}'] = generate_care_unit(config)

    return day


def generate_protocol(config, services=None):

    # shift the entire protocol in order to align it with first_day
    if 'first_day' in config['day']:
        first_day = int(config['day']['first_day'])
    else:
        first_day = 0

    # compute the initial shift
    day_number = config['day']['number']
    max_initial_shift = int(day_number * config['protocol']['initial_shift_spread_percentage'])
    initial_shift = random.randint(-max_initial_shift, max_initial_shift)

    # compute the protocol size
    if (type(config['protocol']['services_per_protocol']) is not int and
        ('min' not in config['protocol']['services_per_protocol'] or config['protocol']['services_per_protocol']['min'] < 1)):
        config['protocol']['services_per_protocol']['min'] = 1
    protocol_service_number = generate_value(config['protocol']['services_per_protocol'])

    # generate every protocol service
    protocol_services = []
    for _ in range(protocol_service_number):

        # if services are pooled, choose one
        if config['service']['strategy'] == 'pool':

            max_service_index = config['service']['pool_size'] - 1
            service_index = random.randint(0, max_service_index)
            service_name = f'srv{service_index:02}'

        # if services are all different, generate a new one
        elif config['service']['strategy'] == 'all_different':

            service_index = len(services)
            service_name = f'srv{service_index:02}'

            if config['service']['care_unit_strategy'] == 'balanced':
                services[service_name] = generate_service(config, service_index)
            else:
                services[service_name] = generate_service(config)

        # compute all the parameters necessary
        tolerance = generate_value(config['protocol']['service']['tolerance'])
        frequency = generate_value(config['protocol']['service']['frequency'])
        
        max_start_shift = int(day_number * config['protocol']['service']['start_spread_percentage'])
        start = random.randint(-max_start_shift, max_start_shift) + first_day

        # times must be at least 1
        if (type(config['protocol']['service']['times']) is not int and
            ('min' not in config['protocol']['service']['times'] or config['protocol']['service']['times']['min'] < 1)):
            config['protocol']['service']['times']['min'] = 1
        times = generate_value(config['protocol']['service']['times'])
        
        # different windows cannot overlap, adjust the frequency if needed
        if frequency < 2 * tolerance + 1:
            frequency = 2 * tolerance + 1
        
        # if the first window has its center before 'first_day', delete every
        # window completely outside
        if start + initial_shift + tolerance < first_day:

            # how many windows are completely or partially outside
            out_times = int((first_day  - start - initial_shift) / frequency)

            # center of the first window right before day 0
            first_out = start + out_times * frequency

            # if its tolerance window reach day 0, keep it
            if first_out + tolerance + initial_shift >= first_day:
                start = first_out
                times -= out_times

            # if not, delete even this window
            else:
                start = first_out + frequency
                times -= out_times + 1

        # if times is big enough that some window are completely over
        # 'day_number', trim the excess
        max_times = int((day_number - start - initial_shift) / frequency + 1)
        if times > max_times:
            times = max_times
        
        if times > 0:
            protocol_services.append({
                'service': service_name,
                'start': start,
                'tolerance': tolerance,
                'frequency': frequency,
                'times': times
            })
    
    return {
        'initial_shift': initial_shift,
        'protocol_services': protocol_services
    }


def generate_patient(config, protocol_pool=None, services=None):

    protocols = {}
    protocol_number = generate_value(config['patient']['protocols_per_patient'])

    # generate every protocol indipendently
    if config['protocol']['strategy'] == 'all_different':
        for protocol_index in range(protocol_number):
            protocols[f'prot{protocol_index:02}'] = generate_protocol(config, services)
    
    # choose from the protocol pool
    elif config['protocol']['strategy'] == 'pool':

        # cannot extract more than pool_size protocols
        protocol_pool_size = len(protocol_pool)
        if protocol_number > protocol_pool_size:
            protocol_number = protocol_pool_size
        
        # choose 'protocol_number' from the pool
        protocol_indexes = random.sample(range(protocol_pool_size), k=protocol_number)

        for protocol_index in range(protocol_number):
            protocols[f'prot{protocol_index:02}'] = protocol_pool[protocol_indexes[protocol_index]]
        
    # add priority if is used
    if config['patient']['use_priority'] is True:
        return {
            'priority': generate_value(config['patient']['priority']),
            'protocols': protocols
        }
    else:
        return {
            'protocols': protocols
        }


def generate_master_instance(config):

    instance = {
        'services': {},
        'days': {},
        'patients': {}
    }

    ### SERVICES GENERATION ###

    # generate the service pool if needed
    if config['service']['strategy'] == 'pool':
        for service_index in range(config['service']['pool_size']):
            if config['service']['care_unit_strategy'] == 'balanced':
                instance['services'][f'srv{service_index:02}'] = generate_service(config, service_index)
            else:
                instance['services'][f'srv{service_index:02}'] = generate_service(config)
    
    ### DAYS GENERATION ###

    # start indexes from first_day, if present
    if 'first_day' in config['day']:
        first_day = int(config['day']['first_day'])
    else:
        first_day = 0

    # every day is equal to eachother
    if config['day']['strategy'] == 'all_same':

        # generate a single day and repeat it up until the day number
        day = generate_day(config)

        for day_index in range(first_day, first_day + config['day']['number']):
            instance['days'][f'{day_index}'] = day
    
    # every day is independently generated
    elif config['day']['strategy'] == 'all_random':

        for day_index in range(first_day, first_day + config['day']['number']):
            instance['days'][f'{day_index}'] = generate_day(config)

    # repeat the same 'week' over and over up until the day number
    elif config['day']['strategy'] == 'repeat_week':

        # generate 'week_size' days
        week_size = config['day']['week_size']
        week = []
        for _ in range(week_size):
            week.append(generate_day(config))
        
        # repeat the week cyclically
        for day_index in range(first_day, first_day + config['day']['number']):
            instance['days'][f'{day_index}'] = week[day_index % week_size]

    ### PATIENTS GENERATION ###

    # every protocol is different
    if config['protocol']['strategy'] == 'all_different':
        for patient_index in range(config['patient']['number']):
            instance['patients'][f'pat{patient_index:02}'] = generate_patient(config, None, instance['services'])

    # there is a finite pool of protocol
    elif config['protocol']['strategy'] == 'pool':

        protocol_pool = []
        for _ in range(config['protocol']['pool_size']):
            if config['service']['strategy'] == 'all_different':
                protocol_pool.append(generate_protocol(config, instance['services']))
            else:
                protocol_pool.append(generate_protocol(config))

        # patients will choose from the pool
        for patient_index in range(config['patient']['number']):
            instance['patients'][f'pat{patient_index:02}'] = generate_patient(config, protocol_pool)

    ### INTERDICTION GENERATION ###

    if 'interdiction' in config and 'active' in config['interdiction'] and config['interdiction']['active'] is True:

        instance['interdictions'] = []
        service_names = list(instance['services'].keys())
        
        for service_name in service_names:
        
            # randomly select some services
            if random.random() >= config['interdiction']['probability']:
                continue
        
            # choose the interdict services (but not the causing one)
            interdiction_size = generate_value(config['interdiction']['service_number'])
            interdiction_service_names = random.sample(service_names, k=interdiction_size)
            if service_name in interdiction_service_names:
                interdiction_service_names.remove(service_name)
        
            start = generate_value(config['interdiction']['start'])
            duration = generate_value(config['interdiction']['window_size'])
        
            instance['interdictions'].append({
                'cause': service_name,
                'effect': interdiction_service_names,
                'window': {
                    'start': start,
                    'duration': duration
                }
            })

    return instance


def generate_subproblem_instance(config):

    instance = {
        'services': {},
        'day': {},
        'requests': []
    }

    # potential patient priority information, if used
    if 'use_priority' not in config['patient']:
        config['patient']['use_priority'] = False
    if config['patient']['use_priority'] is True:
        instance['patient_priorities'] = {}

    ### SERVICES GENERATION ###

    # generate the service pool if needed
    if config['service']['strategy'] == 'pool':
        for service_index in range(config['service']['pool_size']):
            if config['service']['care_unit_strategy'] == 'balanced':
                instance['services'][f'srv{service_index:02}'] = generate_service(config, service_index)
            else:
                instance['services'][f'srv{service_index:02}'] = generate_service(config)
    
    ### DAY GENERATION ###
    
    instance['day'] = generate_day(config)

    ### PATIENT GENERATION ###

    for patient_index in range(config['patient']['number']):

        patient_name = f'pat{patient_index:02}'
        
        # eventual priority generation
        if config['patient']['use_priority'] is True:
            instance['patient_priorities'][patient_name] = generate_value(config['patient']['priority'])
        
        # compute the request size, i.e. the number of services requested
        if (type(config['patient']['requests_per_patient']) is not int and
            ('min' not in config['patient']['requests_per_patient'] or config['patient']['requests_per_patient']['min'] < 1)):
            config['patient']['requests_per_patient']['min'] = 1
        request_size = generate_value(config['patient']['requests_per_patient'])
        service_number = config['service']['pool_size']
        if request_size > service_number:
            request_size = service_number

        # choose services from the pool
        if config['service']['strategy'] == 'pool':
            service_indexes = sorted(random.sample(range(service_number), k=request_size))
        
        # generate new services (with new indexes)
        elif config['service']['strategy'] == 'all_different':

            service_indexes = []
            services_number = len(instance['services'])
            
            for service_index in range(len(services_number, services_number + request_size)):
                service_indexes.append(service_index)
                instance['services'][f'srv{service_index}'] = generate_service(config)

        # create an entry for each request
        for service_index in service_indexes:
            instance['requests'].append({
                'patient': patient_name,
                'service': f'srv{service_index:02}'
            })

    return instance