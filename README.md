# Patient scheduler project

1. [Quick command examples](#commands)
1. [Project file structure](#project-file-structure)
2. Generator configuration examples
    1. [Master instance](#master-instance-configuration-example)
    2. [Subproblem instance](#subproblem-instance-configuration-example)
3. Instance examples
    1. [Master instance](#master-instance-structure): what the main pipeline will recieve (infos about protocols and all days)
    2. [Master results](#master-results-structure): schedule attempt by the relaxed master solving process
    3. [Subproblem instance](#subproblem-instance-structure): what the subproblem will recieve (infos about a single day and requests)
    4. [Subproblem results](#subproblem-results-structure): what the subproblem solving process will produce (daily scheduled time slots)
    5. [Final results](#final-results-structure): final loop aggregate of all subproblem results (or monolithic single-pass results)
4. [Solver configuration example](#solver-configuration-example)
5. [Analyzer configuration example](#analyzer-configuration-examples)

## Commands

```
python ...
```

## Project file structure

> [!NOTE]
> Every code directory has a file `tools.py` containing common functions used in
> more than one file.

> [!NOTE]
> Generators, solvers and analyzers need a `config.yaml` file that specify all
> parameters needed. Examples of those are provided below.

```yaml
.gitignore
README.md

# specify one of ['master', 'subproblem', 'monolithic'] and run tests on
# those pipelines
run_tests.py

# run the main instance loop with master and subproblem decomposition
main.py

# generate groups of JSON instances in the 'input' subdirectory
generators:
- tools.py
- master_instance_generator.py
- subproblem_instance_generator.py

# check if the data in JSON files are correct, giving errors and warnings
checkers:
- tools.py
- master_instance_checker.py
- subproblem_instance_checker.py
- master_results_checker.py
- subproblem_results_checker.py
- final_results_checker.py
- cores_checker.py

# extract informations about JSON data and put them in a csv file
analyzers:
- tools.py
- master_instance_analyzer.py
- subproblem_instance_analyzer.py
- master_results_analyzer.py
- subproblem_results_analyzer.py
- final_results_analyzer.py
- cores_analyzer.py

# create png plots of instance results, saved in the 'plots' subdirectory
plotters:
- tools.py
- master_results_plotter.py
- subproblem_results_plotter.py
- final_results_plotter.py

# solve MILP problems, saving JSON results in the 'results' subdirectory and
# logs in the 'logs' subdirectory
solvers:
- tools.py
- master_solver.py
- subproblem_solver.py
- monolithic_solver.py

# used only in the main loop decomposition as feedback information
cores:
- tools.py
- compute_cores.py
- expand_core_days.py
- expand_core_patients.py
- expand_core_services.py

# directory with JSON instance data, results, analysis and png plots organized
# in groups, each with its own generator configuration
instances:

  # the group name is indicative of the characteristic of the instances inside
  group_name:

    info.yaml # reminder of the generator configuration used
    instances.csv # analyzer data about instance input
    results.csv # analyzer data about instance results
    cores.csv # analyzer data about instance cores, if main loop

    input:
    - instance_0.json
    - instance_1.json
    - instance_2.json
    - instance_3.json
    plots:
    - instance_0_results.png
    - instance_1_results.png
    - instance_2_results.png
    - instance_3_results.png
    logs:
    - instance_0_log.txt
    - instance_1_log.txt
    - instance_2_log.txt
    - instance_3_log.txt
    results:
    - instance_0_results.json
    - instance_1_results.json
    - instance_2_results.json
    - instance_3_results.json
    cores:
    - instance_0_iter_0_cores.json
    - instance_1_iter_0_cores.json
    - instance_2_iter_0_cores.json
    - instance_3_iter_0_cores.json
```

## Generator configuration examples

### Master instance configuration example

```yaml
include_info_in_instances: true # if active, every JSON file will be provided with all the generator info
include_info_in_group_folder: true # if active, a single copy of this file will be added in the group folder

# add an entry for each instance group
groups:
- seed: 42
  instance_number: 10
  instance_group_folder_name: "master_group"

  day:
    # define the day generator strategy (comment away other strategies):
    # - all_same: generate a single day and repeat it for 'number' days
    # - all_random: every day is potentially different from each other
    # - repeat_week: 'week_size' days are created and cyclically repeated
    strategy: "all_same"
    # day_strategy: "all_random"
    # day_strategy: "repeat_week"

    # week_size: 5 # use only if 'strategy' is "repeat_week"
    number: 30 # how many days are generated
    time_slots: 32 # how many time slot are present in each day
    care_unit_number: 4 # how many care units are present in each day
    operators_per_care_unit: 4 # how many operators are present in each care unit

  operator:
    # define the operator generator strategy (comment away other strategies):
    # - fill: every operator starts at 0 and end at 'time_slots'
    # - random: every operator is potentially different from each other
    # - overlap: the first half of operators will overlap the second half
    # strategy: "fill"
    # strategy: "random"
    strategy: "overlap"
  
    duration: 16 # use only if 'strategy' is "random" or "overlap"

    # use only if 'strategy' is "overlap". The first half of operators will
    # span [0, duration], the second half [y, duration]... The interval of
    # overlapping operators will be 'duration' * 'overlap_percentage'.
    overlap_percentage: 1.0

  service:
    # define the service generator strategy (comment away other strategies):
    # - pool: a fixed set of service are generated and then chosen for every request
    # - all_different: every request will generate a new service
    strategy: "pool"
    # strategy: "all_different"

    # define the care_unit choice strategy (comment away other strategies):
    # - random: every service will choose a random care unit
    # - balanced: service will choose care units in a cyclical way, ensuring an equal demand distribution
    # care_unit_strategy: "random"
    care_unit_strategy: "balanced"

    pool_size: 30 # use only if 'strategy' is "pool"
    duration: {min: 1, max: 8} # how many time slots every service will require
  
  patient:
    number: 20
    use_priority: true # every patient can be assigned with a certain priority (less is more urgent)
    priority: {min: 1, max: 3}
    protocols_per_patient: {min: 1, max: 3, average: 1, standard_deviation: 0.1}
  
  protocol:
    # define the protocol generator strategy (comment away other strategies):
    # - pool: a fixed set of protocols are generated and potentially reused
    # - all_different: every request will generate a new protocol
    # strategy: "pool"
    strategy: "all_different"

    services_per_protocol: 3 # protocol size
    # pool_size: 10 # use only if 'strategy' is "pool"
    initial_shift_spread_percentage: 0.5 # how much each protocol could be shifted (forward or backward) in relation to the number of days

    service:
    start_spread_percentage: 1.0 # how much each service could be shifted (forward or backward) in relation to the number of days
    tolerance: {max: 3} # how big could be the tolerance window [-tol, tol]
    frequency: {average: 6, standard_deviation: 3.0} # how many days will pass between each service request
    times: {max: 6} # how many time each service could be requested, advancing each time by 'frequency'
  
  ### NOT YET IMPLEMENTED ###
  # necessities express the constraint: "if A is done then B must also be done in a certain window"
  # necessity:
  #   active: true
  #   probability: 0.1
  #   max_chain: 1 # maximum necessity chain possible A -> B -> C...
  #   max_size: 2 # how many services will be forced to be present at maximum

  # interdictions express the constraint: "if A is done then B cannot be done in a certain window"
  # interdiction:
  #   active: false
  #   probability: 0.1
  #   service_number: {min: 1, max: 3} # how many services will be forced to *not* be present

  #   # define the interdiction window
  #   start: {min: 1, max: 5}
  #   window_size: {min: 1, max: 7}
```

### Subproblem instance configuration example

```yaml
include_info_in_instances: true # if active, every JSON file will be provided with all the generator info
include_info_in_group_folder: true # if active, a single copy of this file will be added in the group folder

# add an entry for each instance group
groups:
- seed: 42
  instance_number: 10
  instance_group_folder_name: "group_sub"

  day:
    time_slots: 32 # how many time slot are present in each day
    care_unit_number: 2 # how many care units are present in each day
    operators_per_care_unit: 4 # how many operators are present in each care unit

  operator:
    # define the operator generator strategy (comment away other strategies):
    # - fill: every operator starts at 0 and end at 'time_slots'
    # - random: every operator is potentially different from each other
    # - overlap: the first half of operators will overlap the second half
    strategy: "fill"
    # strategy: "random"
    # strategy: "overlap"

    # duration: {min: 6, max: 32} # use only if 'strategy' is "random" or "overlap"

    # use only if 'strategy' is "overlap". The first half of operators will
    # span [0, x] and the second half [y, time_slots]. The interval [y, x]
    # will be 'time_slots' * 'overlap_percentage'.
    # overlap_percentage: 0.5

  service:
    # define the service generator strategy (comment away other strategies):
    # - pool: a fixed set of service are generated and then chosen for every request
    # - all_different: every request will generate a new service
    strategy: "pool"
    # strategy: "all_different"

    # define the care_unit choice strategy (comment away other strategies):
    # - random: every service will choose a random care unit
    # - balanced: service will choose care units in a cyclical way, ensuring an equal demand distribution
    # care_unit_strategy: "random"
    care_unit_strategy: "balanced"

    pool_size: 20 # use only if 'strategy' is "pool"
    duration: {average: 6, standard_deviation: 2.0} # how many time slots every service will require

  patient:
    number: 10
    use_priority: true # every patient can be assigned with a certain priority (less is more urgent)
    priority: {min: 1, max: 3}
    requests_per_patient: {min: 1, max: 3} # how many services are requested by every patient
```

## Instance examples

### Master instance structure

```yaml
services:
  srv00:
    care_unit: 'cu00'
    duration: 4
  srv01:
    care_unit: 'cu01'
    duration: 4

days:
  day00:
    cu00:
      op00:
        start: 0
        duration: 8
      op01:
        start: 0
        duration: 8
    cu01:
      op00:
        start: 0
        duration: 8
      op01:
        start: 0
        duration: 8

patients:
  pat00:
    priority: 1
    protocols:
      prot00:
        initial_shift: 3
        protocol_services:
          - service: 'srv00'
            start: 3
            tolerance: 1
            frequency: 7
            times: 4
          - service: 'srv01'
            start: 3
            tolerance: 1
            frequency: 7
            times: 4
```

### Master results structure

```yaml
scheduled:
  day00:
  - patient: 'pat00'
    service: 'srv00'
  - patient: 'pat01'
    service: 'srv01'
  day01:
  - patient: 'pat00'
    service: 'srv00'
  - patient: 'pat01'
    service: 'srv01'
```

### Subproblem instance structure

```yaml
services:
  srv00:
    care_unit: 'cu00'
    duration: 4
  srv01:
    care_unit: 'cu00'
    duration: 4

day:
  cu00:
    op00:
      start: 0
      duration: 8
    op01:
      start: 0
      duration: 8
  cu01:
    op00:
      start: 0
      duration: 8
    op01:
      start: 0
      duration: 8

patients:
  pat00:
    priority: 1
    requests:
    - 'srv00'
    - 'srv01'
  pat01:
    priority: 1
    requests:
    - 'srv00'
    - 'srv01'
```

### Subproblem results structure

```yaml
scheduled:
- patient: 'pat00'
  service: 'srv00'
  care_unit: 'cu00'
  operator: 'op00'
  time: 3
- patient: 'pat01'
  service: 'srv01'
  care_unit: 'cu01'
  operator: 'op01'
  time: 3
rejected:
- patient: 'pat02'
  service: 'srv02'
- patient: 'pat03'
  service: 'srv03'
```

### Final results structure

```yaml
scheduled:
  day00:
  - patient: 'pat00'
    service: 'srv00'
    care_unit: 'cu00'
    operator: 'op00'
    time: 3
  - patient: 'pat01'
    service: 'srv01'
    care_unit: 'cu01'
    operator: 'op01'
    time: 3
  day01:
  - patient: 'pat00'
    service: 'srv00'
    care_unit: 'cu00'
    operator: 'op00'
    time: 3
rejected:
- patient: 'pat02'
  service: 'srv02'
  window: [3, 6]
- patient: 'pat03'
  service: 'srv03'
  window: [2, 4]
```

## Solver configuration example

```yaml
# if monolitic tests are performed:
#   one of ['monolithic', 'monolithic_inefficient']
method: 'monolithic'

solver: 'gurobi' # one of ['gurobi', 'glpk']
time_limit: 3600 # solver time limit in seconds
keep_logs: true
use_patient_priority: true
max_memory: 8 # solver mamory in GB
```

## Analyzer configuration examples

```yaml
# what data is pulled out of master JSON instances:
window_number: true
average_windows_per_patient: true
normalized_disponibility_vs_requests: true
average_window_size: true
average_time_slots_per_care_unit: true
average_overlapping_requests_per_patient: true
max_requests_in_same_day_per_patient: true

# what data is pulled out of final JSON results:
window_number: true
rejected_window_number: true
method: true
model_creation_time: true
model_solving_time: true
solver_internal_time: true
status: true
termination_condition: true
lower_bound: true
upper_bound: true
gap: true
objective_function_value: true
```