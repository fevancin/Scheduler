from argparse import ArgumentParser
from time import perf_counter
from json import load, dump
from pathlib import Path
import pyomo.environ as pyo

from pyomo.environ import ConcreteModel, maximize
from pyomo.environ import Set, Var, Objective, Constraint, ConstraintList
from pyomo.environ import Boolean, NonNegativeReals, NonNegativeIntegers
from pyomo.environ import SolverFactory

def get_milp_basic_model(instance):
    
    # find the maximum end time for each care unit (reduces domain in t variables)
    max_times = dict()
    for care_unit_name, care_unit in instance['operators'].items():

        max_time = 0
        for operator in care_unit.values():
            end_time = operator["start"] + operator["duration"]
            if end_time > max_time:
                max_time = end_time

        # adds one because the special value 0 is reserved for the non-execution
        max_times[care_unit_name] = max_time + 1

    # x_indexes are (patient, service)
    x_indexes = []
    # chi_indexes are (patient, service, operator, care_unit)
    chi_indexes = []
    for patient_name, services_requested in instance['requests'].items():
        for service_name in services_requested:

            care_unit_name = instance['services'][service_name]['care_unit']
            duration = instance['services'][service_name]['duration']

            is_service_satisfiable = False
            for operator_name, operator in instance['operators'][care_unit_name].items():
                if operator['duration'] >= duration:
                    chi_indexes.append((patient_name, service_name, operator_name, care_unit_name))
                    is_service_satisfiable = True

            if is_service_satisfiable:
                x_indexes.append((patient_name, service_name))

    # aux1_indexes are (patient, service1, service2)
    aux1_indexes = []
    for index1 in range(len(x_indexes) - 1):
        for index2 in range(index1 + 1, len(x_indexes)):
            if x_indexes[index1][0] == x_indexes[index2][0]:
                aux1_indexes.append((x_indexes[index1][0], x_indexes[index1][1], x_indexes[index2][1]))
    
    model = ConcreteModel()

    model.x_indexes = Set(initialize=x_indexes)
    model.chi_indexes = Set(initialize=chi_indexes)
    model.aux1_indexes = Set(initialize=aux1_indexes)

    # if a service requested from a patient is satisfied
    model.x = Var(model.x_indexes, domain=Boolean)

    # the time when a service is done
    model.t = Var(model.x_indexes, domain=NonNegativeIntegers)

    # what operator satisfy a service requested by a patient
    model.chi = Var(model.chi_indexes, domain=Boolean)

    model.aux1 = Var(model.aux1_indexes, domain=Boolean)

    # maximize the total duration of services done (maximize operator uptime)
    def objective_function(model):
        return sum(model.x[p, s] * instance['services'][s]['duration'] for p, s in model.x_indexes)
    model.objective = Objective(rule=objective_function, sense=maximize)

    # keep toghether x and t variables:
    # - when x = 0 then t = 0
    def f1(model, p, s):
        care_unit_name = instance["services"][s]["care_unit"]
        return model.t[p, s] <= model.x[p, s] * max_times[care_unit_name]
    model.t_and_x = Constraint(model.x_indexes, rule=f1)

    # - when x = 1 then t > 0
    def f2(model, p, s):
        return model.t[p, s] >= model.x[p, s]
    model.x_and_t = Constraint(model.x_indexes, rule=f2)

    # links toghether x and chi variables
    # when x = 1 then exactly one chi variable of that care unit must be 1
    def f3(model, p, s):
        return sum(model.chi[p, s, o, c] for pp, ss, o, c in model.chi_indexes if p == pp and s == ss) == model.x[p, s]
    model.x_and_chi = Constraint(model.x_indexes, rule=f3)

    # operator start and end times must be respected
    def f4(model, p, s, o, c):
        start = instance['operators'][c][o]["start"] + 1
        return start * model.chi[p, s, o, c] <= model.t[p, s]
    model.respect_start = Constraint(model.chi_indexes, rule=f4)

    def f5(model, p, s, o, c):
        start = instance['operators'][c][o]["start"] + 1
        end = start + instance['operators'][c][o]["duration"]
        service_duration = instance["services"][s]["duration"]
        return model.t[p, s] + service_duration <= end + (1 - model.chi[p, s, o, c]) * max_times[c]
    model.respect_end = Constraint(model.chi_indexes, rule=f5)

    # services of the same patient must not overlap
    def f6(model, p, s, ss):
        service_duration = instance["services"][s]["duration"]
        care_unit_name = instance["services"][s]["care_unit"]
        return (model.t[p, s] + service_duration * model.x[p, s] <= model.t[p, ss] + (1 - model.aux1[p, s, ss]) * max_times[care_unit_name])
    model.patient_not_overlaps1 = Constraint(model.aux1_indexes, rule=f6)

    def f7(model, p, s, ss):
        service_duration = instance["services"][ss]["duration"]
        care_unit_name = instance["services"][ss]["care_unit"]
        return (model.t[p, ss] + service_duration * model.x[p, ss] <= model.t[p, s] + model.aux1[p, s, ss] * max_times[care_unit_name])
    model.patient_not_overlaps2 = Constraint(model.aux1_indexes, rule=f7)

    def f8(model, p, s, ss):
        return (model.aux1[p, s, ss] <= model.x[p, ss])
    model.patient_not_overlaps3 = Constraint(model.aux1_indexes, rule=f8)

    def f9(model, p, s, ss):
        return (model.x[p, ss] - model.x[p, s] <= model.aux1[p, s, ss])
    model.patient_not_overlaps4 = Constraint(model.aux1_indexes, rule=f9)

    return (model, max_times)

def get_milp_std_model(instance):

    model, max_times = get_milp_basic_model(instance)

    chi_indexes = list(model.chi_indexes)

    # aux2_indexes are (patient1, service1, patient2, service2, operator, care_unit, i)
    aux2_indexes = []
    for index1 in range(len(chi_indexes) - 1):
        for index2 in range(index1 + 1, len(chi_indexes)):
            if chi_indexes[index1][2] == chi_indexes[index2][2] and chi_indexes[index1][3] == chi_indexes[index2][3]:
                aux2_indexes.append((chi_indexes[index1][0], chi_indexes[index1][1], chi_indexes[index2][0], chi_indexes[index2][1], chi_indexes[index1][2], chi_indexes[index1][3], 0))
                aux2_indexes.append((chi_indexes[index1][0], chi_indexes[index1][1], chi_indexes[index2][0], chi_indexes[index2][1], chi_indexes[index1][2], chi_indexes[index1][3], 1))

    model.aux2_indexes = Set(initialize=aux2_indexes)
    model.aux2 = Var(model.aux2_indexes, domain=Boolean)

    # services satisfied by the same operator must not overlap
    def f1(model, p, s, pp, ss, o, c, n):
        if n == 0:
            s_duration = instance["services"][s]["duration"]
            return (model.t[p, s] + s_duration * model.chi[p, s, o, c] <= model.t[pp, ss] + (1 - model.aux2[p, s, pp, ss, o, c, n]) * max_times[c])
        else:
            ss_duration = instance["services"][ss]["duration"]
            return (model.t[pp, ss] + ss_duration * model.chi[pp, ss, o, c] <= model.t[p, s] + (1 - model.aux2[p, s, pp, ss, o, c, n]) * max_times[c])
    model.operator_not_overlaps1 = Constraint(model.aux2_indexes, rule=f1)

    def f2(model, p, s, pp, ss, o, c, n):
        if n == 0: return Constraint.Skip
        return (model.chi[p, s, o, c] + model.chi[pp, ss, o, c] - 1 <= model.aux2[p, s, pp, ss, o, c, 0] + model.aux2[p, s, pp, ss, o, c, 1])
    model.operator_not_overlaps2 = Constraint(model.aux2_indexes, rule=f2)

    def f3(model, p, s, pp, ss, o, c, n):
        if n == 0:
            return (model.chi[p, s, o, c] >= model.aux2[p, s, pp, ss, o, c, 0] + model.aux2[p, s, pp, ss, o, c, 1])
        return (model.chi[pp, ss, o, c] >= model.aux2[p, s, pp, ss, o, c, 0] + model.aux2[p, s, pp, ss, o, c, 1])
    model.operator_not_overlaps3 = Constraint(model.aux2_indexes, rule=f3)

    return model

def get_milp_master_model(instance):

    max_day = len(list(instance['days'].keys())) - 1

    # x_indexes are of type (patient, service, day) for each triplet that is a valid schedule
    x_indexes = []

    # window_constraint_indexes are of type (patient, service, start_day, end_day) for each request window
    window_constraint_indexes = []

    for patient_name, patient in instance['patients'].items():
        for protocol_name, protocol in patient['protocols'].items():
            initial_shift = protocol['initial_shift']
            for protocol_service in protocol['protocol_services']:
                service_name = protocol_service['service']
                for window_index in range(protocol_service['times']):

                    start_day = protocol_service['start'] + window_index * protocol_service['frequency'] - protocol_service['tolerance'] + initial_shift
                    end_day = start_day + protocol_service['tolerance'] * 2
                    
                    # ammissibility checks
                    if start_day > end_day:
                        continue
                    if start_day > max_day or end_day < 0:
                        continue
                    
                    # clamp to valid day values
                    if start_day < 0:
                        start_day = 0
                    if end_day > max_day:
                        end_day = max_day
                    
                    for day_index in range(start_day, end_day + 1):
                        x_indexes.append((patient_name, service_name, day_index))
                    
                    # only windows of size > 1
                    if start_day != end_day:
                        window_constraint_indexes.append((patient_name, service_name, start_day, end_day))

    # day_care_unit_indexes are of type (day_index, care_unit_name)
    day_care_unit_indexes = []
    day_care_unit_total_capacity = {}

    for day_name, day in instance['days'].items():
        for care_unit_name, care_unit in day.items():

            key = (int(day_name), care_unit_name)

            # check if exists at least one patient that requests a service of this care unit
            exists_at_least_one_x = False
            for patient_name, service_name, day_index in x_indexes:
                if day_index == key[0] and instance['services'][service_name]['care_unit'] == care_unit_name:
                    exists_at_least_one_x = True
                    break

            # it's useless to generate empty constraints
            if not exists_at_least_one_x:
                continue

            day_care_unit_indexes.append(key)

            total_capacity = 0
            for operator in care_unit.values():
                total_capacity += operator['duration']

            day_care_unit_total_capacity[key] = total_capacity

    model = ConcreteModel()

    model.x_indexes = Set(initialize=list(set(x_indexes)))
    model.window_constraint_indexes = Set(initialize=list(set(window_constraint_indexes)))
    model.day_care_unit_indexes = Set(initialize=day_care_unit_indexes)

    # x[patient, service, day]
    # the variable x is true when a service requested from a patient is done in a specific day
    model.x = Var(model.x_indexes, domain=Boolean)

    # maximize service durations
    model.objective_function_value = Var(domain=NonNegativeReals)
    model.objective_constraint = Constraint(expr=sum(model.x[p, s, d] * instance['services'][s]['duration'] * instance['patients'][p]['priority'] for p, s, d in model.x_indexes) <= model.objective_function_value)
    model.objective_constraint2 = Constraint(expr=sum(model.x[p, s, d] * instance['services'][s]['duration'] * instance['patients'][p]['priority'] for p, s, d in model.x_indexes) >= model.objective_function_value)

    # def objective_function(model):
    #     return sum(model.x[p, s, d] * instance['services'][s]['duration'] for p, s, d in model.x_indexes)
    # model.objective = Objective(rule=objective_function, sense=maximize)
    def objective_function(model):
        return model.objective_function_value
    model.objective = Objective(rule=objective_function, sense=maximize)

    # it'impossible to satisfy a service more than once in its request window
    def window_constraint_function(model, p, s, d1, d2):
        return sum([model.x[p, s, d] for d in range(d1, d2 + 1)]) <= 1
    model.window_constraints = Constraint(model.window_constraint_indexes, rule=window_constraint_function)

    def total_capacity_constraint_function(model, d, c):
        return sum([model.x[p, s, d] * instance['services'][s]['duration'] for p, s, dd in model.x_indexes if d == dd and instance['services'][s]['care_unit'] == c]) <= day_care_unit_total_capacity[(d, c)]
    model.total_capacity_constraint = Constraint(model.day_care_unit_indexes, rule=total_capacity_constraint_function)

    model.cores = ConstraintList()

    model.objective_function_constraints = ConstraintList()

    return model

def add_rejected_services_to_results(instance, results):
        
    # store all couples (patient, service) for every request not satisfied
    results['rejected'] = {}
    for patient_name, service_requests in instance['requests'].items():
        for service_name in service_requests:
            is_service_satisfied = False
            for scheduled_service in results['scheduled']:
                if patient_name == scheduled_service['patient'] and service_name == scheduled_service['service']:
                    is_service_satisfied = True
                    break
            if not is_service_satisfied:
                if patient_name not in results['rejected']:
                    results['rejected'][patient_name] = []
                results['rejected'][patient_name].append(service_name)

def get_master_model_solution(model):

    results = {}

    solution_values = model.x.extract_values()
    for (patient_name, service_name, day_index), solution_value in solution_values.items():
        if solution_value > 0.01:
            day_name = str(day_index)
            if day_name not in results:
                results[day_name] = {}
            if patient_name not in results[day_name]:
                results[day_name][patient_name] = []
            results[day_name][patient_name].append(service_name)

    # order the result dictionary by keys
    return dict(sorted(results.items(), key=lambda v: int(v[0])))

def get_subproblem_model_solution(model):

    results = {'scheduled': []}

    solution_values = model.chi.extract_values()
    solution_times = model.t.extract_values()
    for (patient_name, service_name, operator_name, care_unit_name), solution_value in solution_values.items():
        if solution_value is not None and solution_value > 0.01:
            results['scheduled'].append({
                'patient': patient_name,
                'service': service_name,
                'operator': operator_name,
                'care_unit': care_unit_name,
                'time': int(solution_times[(patient_name, service_name)]) - 1
            })

    return results

def extract_solution_from_milp_result(model, result, problem_type):

    model.solutions.load_from(result)

    # result decoding to an object format
    if result.solver.termination_condition == pyo.TerminationCondition.infeasible:
        results = {}
    else:
        if problem_type == 'master':
            results = get_master_model_solution(model)
        elif problem_type == 'subproblem':
            results = get_subproblem_model_solution(model)
    
    return results

def get_milp_model(instance, problem_type):

    model = None

    if problem_type == 'master':
        model = get_milp_master_model(instance)
        # add_opt_to_master_model(instance, model)
    else:
        model = get_milp_std_model(instance)
        # add_opt_to_subproblem_model(instance, model)
    
    return model

def solve_problem(instance, output_folder_path: Path, time_limit: int):

    creation_start_time = perf_counter()
    model = get_milp_model(instance, 'subproblem')
    creation_elapsed_time = perf_counter() - creation_start_time

    opt = pyo.SolverFactory('gurobi')

    if time_limit is not None:
        opt.options['TimeLimit'] = time_limit
    opt.options['SoftMemLimit'] = 8
    # model.setParam('MIPGap', 0.05)

    solving_start_time = perf_counter()
    result = opt.solve(model, logfile=output_folder_path.joinpath('milp_logfile.log'), tee=True)
    # result = opt.solve(model, tee=True)

    solving_elapsed_time = perf_counter() - solving_start_time

    model.solutions.store_to(result)
    solution = result.solution[0]
    lower_bound = float(result['problem'][0]['Lower bound'])
    upper_bound = float(result['problem'][0]['Upper bound'])
    gap = float(solution['gap'])
    if gap <= 1e-5 and lower_bound != upper_bound:
        gap = (upper_bound - lower_bound) / upper_bound
    value = float(solution['objective']['objective']['Value'])

    solver_info = {
        'method': 'milp',
        'model_creation_time': creation_elapsed_time,
        'model_solving_time': solving_elapsed_time,
        'solver_internal_time': float(result.solver.time),
        'status': str(result.solver.status),
        'termination_condition': str(result.solver.termination_condition),
        'lower_bound': lower_bound,
        'upper_bound': upper_bound if upper_bound <= 1e9 else 'infinity',
        'gap': gap,
        'objective_function_value': value
    }

    results = extract_solution_from_milp_result(model, result, 'subproblem')

    add_rejected_services_to_results(instance, results)
    
    return (results, solver_info)

################################################################################
#                                   /main.py                                   #
################################################################################

# read the command line arguments
parser = ArgumentParser(prog='main.py', description='Main script for the instances solving process.')

parser.add_argument('-i', '--input', type=Path, required=True, help='Master input instance of the problem.')
parser.add_argument('-o', '--output', type=Path, help='Destination folder for all the output (defaults to an automatic generated name).')
parser.add_argument('-t', '--time-limit', type=int, default=3600, help='Time limit in seconds for the solving process.')
parser.add_argument('-v', '--verbose', action='store_true')
args = parser.parse_args()

if args.output:
    solution_folder_path = args.output
else:
    solution_folder_path = args.input.parent.joinpath(f'SOL_{args.input.stem}')

solution_folder_path.mkdir(exist_ok=True)

if args.verbose:
    start_time = perf_counter()

# load master instance data
with open(args.input, 'r') as file:
    instance = load(file)

# copy instance data to solution folder
with open(solution_folder_path.joinpath('instance.json'), 'w') as file:
    dump(instance, file, indent=4)

patient_priorities = {}
for patient_name, patient_protocols in instance['patients'].items():
    patient_priorities[patient_name] = patient_protocols['priority']

# results of all subproblems (last iteration schedule)
all_subproblem_results = {}

# if method is milp, get the master model only once here
if args.verbose:
    creation_start_time = perf_counter()
    print('start master creation')

master_model = get_milp_master_model(instance)

if args.verbose:
    creation_elapsed_time = perf_counter() - creation_start_time
    print(f'end master creation: {creation_elapsed_time} seconds.')

opt = SolverFactory('gurobi')
opt.options['TimeLimit'] = args.time_limit

if args.verbose:
    print('Starting master solving')
    solving_start_time = perf_counter()

result = opt.solve(master_model, logfile=solution_folder_path.joinpath('milp_logfile.log'), tee=True)
# result = opt.solve(model, tee=True)

if args.verbose:
    solving_elapsed_time = perf_counter() - solving_start_time
    print(f'Ending master problem. Took {solving_elapsed_time}')

master_model.solutions.store_to(result)
solution = result.solution[0]
lower_bound = float(result['problem'][0]['Lower bound'])
upper_bound = float(result['problem'][0]['Upper bound'])
gap = float(solution['gap'])
if gap <= 1e-5 and lower_bound != upper_bound:
    gap = (upper_bound - lower_bound) / upper_bound
value = float(solution['objective']['objective']['Value'])

solver_info = {
    'method': 'milp',
    'model_creation_time': creation_elapsed_time,
    'model_solving_time': solving_elapsed_time,
    'solver_internal_time': float(result.solver.time),
    'status': str(result.solver.status),
    'termination_condition': str(result.solver.termination_condition),
    'lower_bound': lower_bound,
    'upper_bound': upper_bound if upper_bound <= 1e9 else 'infinity',
    'gap': gap,
    'objective_function_value': value
}

master_results = extract_solution_from_milp_result(master_model, result, 'master')

# write master results to file
with open(solution_folder_path.joinpath(f'master_results.json'), 'w') as file:
    dump(master_results, file, indent=4)
with open(solution_folder_path.joinpath(f'master_solver_info.json'), 'w') as file:
    dump(solver_info, file, indent=4)

all_subproblem_results = {}

# solve the subproblem for each day
for day_name, day_requests in master_results.items():

    # build the subproblem input for this day
    subproblem_input = {
        'operators': instance['days'][day_name],
        'services': instance['services'],
        'requests': master_results[day_name],
        'priorities': patient_priorities
    }

    if args.verbose:
        print(f'Starting subproblem for day {day_name}.')

    # solve the subproblem for this day
    subproblem_results, solver_info = solve_problem(
        instance=subproblem_input,
        output_folder_path=solution_folder_path,
        time_limit=str(args.time_limit)
    )

    if args.verbose:
        print(f'Ending subproblem for day {day_name}.')

    # put toghether all day results in a single object, indexed by day name
    all_subproblem_results[day_name] = subproblem_results

    # check if exists at least one request not satisfied
    if len(subproblem_results['rejected']) > 0:
        if args.verbose:
            print(f'Day {day_name} is not completely satisfied.')
    
    # write the subproblem data to file
    with open(solution_folder_path.joinpath(f'day{day_name}_subproblem_input.json'), 'w') as file:
        dump(subproblem_input, file, indent=4)
    with open(solution_folder_path.joinpath(f'day{day_name}_subproblem_results.json'), 'w') as file:
        dump(subproblem_results, file, indent=4)
    with open(solution_folder_path.joinpath(f'day{day_name}_subproblem_solver_info.json'), 'w') as file:
        dump(solver_info, file, indent=4)

# write aggregate subproblem results to file
with open(solution_folder_path.joinpath(f'master_results.json'), 'w') as file:
    dump(master_results, file, indent=4)
with open(solution_folder_path.joinpath(f'all_subproblem_results.json'), 'w') as file:
    dump(all_subproblem_results, file, indent=4)

# write last iteration schedule results to file
with open(solution_folder_path.joinpath('all_subproblem_results.json'), 'w') as file:
    dump(all_subproblem_results, file, indent=4)

if args.verbose:
    print(f'Total time taken: {perf_counter() - start_time} seconds.')