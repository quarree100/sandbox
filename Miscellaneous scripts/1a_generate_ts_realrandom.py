# RUN THIS FILE FROM THE TERMINAL OR COMMAND LINE

# THIS IS AN EXAMPLE TO CREATE MULTIPLE TIME SERIES

# BELOW YOU WILL FIND THE CONFIGURATION SECTION

# THIS EXAMPLE CONSIDERS PARALLEL PROCESSING TO SPEED UP THE DRIVING PROFILE GENERATION


from emobpy import Mobility, Availability, Charging, Export, DataBase
import pandas as pd
import numpy as np
import random
import psutil
from multiprocessing import Lock, Process, Queue

nr_workers = min(20, psutil.cpu_count()-1)


try:
    import ray
    is_ray = True
    deco = ray.remote
    ray.init(num_cpus=nr_workers, ignore_reinit_error=True, include_webui=False)
except ImportError:
    deco = None
    is_ray = False

def raydecorator(condition, decorator):
    return decorator if condition else lambda x: x

@raydecorator(is_ray, deco)
def evsteps(odir, s1, s2, s3, p, r, seed):
    print('evsteps seed:', seed)
    np.random.seed(seed)
    m = Mobility()
    m.setParams(p)
    m.setStats(s1, s2, s3)
    m.setRules(r)
    m.run()
    m.save_profile(odir)
    del m
    return None


def drive_iter(odir,s1,s2,s3,p,r,from_,to_):
    prequeue = []
    for i in range(from_, to_):
        prequeue.append([odir, s1, s2, s3, p, r])
    return prequeue


@raydecorator(is_ray, deco)
def gridsteps(whenAtHome,
               whenAtWork,
               obs,
               code,
               battery_capacity,
               charging_eff,
               soc_init,
               soc_min,
               db,
               fold,
               battopt):
    prob = whenAtHome[obs['whenathome']]
    if obs['g_type'] == 'commuter':
        prob['prob_charging_point']['workplace'] = whenAtWork[obs['whenatwork']]
    a = Availability(code)
    a.setScenario(prob)
    a.setVehicleFeature(battery_capacity, charging_eff)
    a.setBatteryRules(soc_init, soc_min, battopt)
    a.loadSettingDriving(db)
    a.run()
    a.save_profile(fold, obs)
    return None


def scen_solve_mov(func, queue, queue_lock, io_lock):
    while True:
        queue_lock.acquire()
        if queue.empty():
            queue_lock.release()
            return
        lsconf, seed = queue.get()
        queue_lock.release()
        func(*lsconf,seed)
    return None

def scen_solve(func, queue, queue_lock, io_lock):
    while True:
        queue_lock.acquire()
        if queue.empty():
            queue_lock.release()
            return
        lsconf = queue.get()
        queue_lock.release()
        func(*lsconf)
    return None


if __name__ == '__main__':

### EDIT THIS SECTION TO CREATE YOUR OWN SCENARIO ###

####################################################
########### Initial configuration parameters #######
####################################################

    dbdir = '/home/dbeier/git-projects/emobpy_examples/casestudy/test123' # directory to store the profiles
    run_driving = True
    run_availability = False
    run_charging = False
    run_export = False

####################################################
############# Configuration for driving ############
####################################################
    if run_driving:

        bev_n = 25  # number of driving time series
        dist = {'fulltime': 0.485, 'parttime': 0.135, 'freetime': 0.380}  # share of profiles
        hours = 24*14  # Total hours for each time series
        timestep = 0.5 # in hours. e.g. 0.5 means half hour
        consumption = 0.18  # kWh/km
        refdate = '31/12/2018'  # time series starting date. Starting time always 00:00

        seeds = list(range(bev_n))


        stat1 = pd.read_csv('vehiclestats/1_group_trips_weekdays.csv')  # importing statistics
        stat2 = pd.read_csv('vehiclestats/2_time_purpose_group_weeks_hrs.csv') # importing statistics. Time steps in the file must match the timestep variable. e.g. If the variable is 0.5 then in the file the time steps should be 0.5 as well
        stat3 = pd.read_csv('vehiclestats/3_km_range_purpose_car.csv') # importing statistics

        # param dictionary. Person key must match with the stat1 column "group" and with the stat2. Open the csv file and compare
        param_comm_fulltime = {'person':'fulltime',
                               'group':'commuter',
                               'refdate':refdate,
                               'energy_consumption':consumption,
                               'hours':hours,
                               'timestep_in_hrs':timestep}

        param_comm_parttime = {'person':'parttime',
                               'group':'commuter',
                               'refdate':refdate,
                               'energy_consumption':consumption,
                               'hours':hours,
                               'timestep_in_hrs':timestep}

        param_free = {'person':'freetime',
                      'group':'freetime',
                      'refdate':refdate,
                      'energy_consumption':consumption,
                      'hours':hours,
                      'timestep_in_hrs':timestep}

        rules_comm_fulltime={'weekday':
                                {'n_trip_out': [1],
                                 'last_trip_to':{'home':True},
                                 'at_least_one_trip':{'workplace':True},
                                 'overall_min_time_at':{'home':9,'workplace':7.0},
                                 'overall_max_time_at':{'workplace':8.0},
                                 'min_state_duration':{'workplace':3.5}
                                },
                            'weekend':
                                {'n_trip_out': [1],
                                 'last_trip_to':{'home':True},
                                 'overall_min_time_at':{'home':6,'workplace':3},
                                 'overall_max_time_at':{'workplace':4},
                                 'min_state_duration':{'workplace':3}
                                }
                            }

        rules_comm_parttime={'weekday':
                                {'n_trip_out': [1],
                                 'last_trip_to':{'home':True},
                                 'at_least_one_trip':{'workplace':True},
                                 'overall_min_time_at':{'home':9,'workplace':3.5},
                                 'overall_max_time_at':{'workplace':4},
                                 'min_state_duration':{'workplace':3.5}
                                },
                            'weekend':
                                {'n_trip_out': [1],
                                 'last_trip_to':{'home':True},
                                 'overall_min_time_at':{'home':6,'workplace':3},
                                 'overall_max_time_at':{'workplace':4},
                                 'min_state_duration':{'workplace':3}
                                }
                            }

        rules_freetime={'weekday':
                            {'n_trip_out': [1],
                             'last_trip_to':{'home':True},
                             'overall_min_time_at':{'home':9}
                            },
                        'weekend':
                            {'n_trip_out': [1],
                             'last_trip_to':{'home':True},
                             'overall_min_time_at':{'home':6}
                            }
                       }

####################################################
######## Configuration for grid availability #######
####################################################

    if run_availability:

        soc_init = 0.5   # initial state of charge. soc_init*100 = %
        soc_min = 0.01    # profile can not have hours with state of charge lower than this value. soc_min*100 = %
        battery_capacity = 40  # kWh
        battopt = list(range(battery_capacity + 5, battery_capacity*4, 5))  # in case the motor electricity demand is high (long distance trips).
                                                                            # The battery_capacity may be not enough.
                                                                            # Then this list has several battery sizes that are tested until a size is good enough to fullfil demand requirements.
                                                                            # However, it may happend that this list values are still not enough.
                                                                            # Then it creates a file whose name indicate "FAIL".
                                                                            # This has been done so to avoid stopping the creation of the rest of the profiles.
                                                                            # There is a Notebook that can be use after this run to help to identify the FAIL files,
                                                                            # to test more options to create a success profile.
        charging_eff = 0.90

        parkingathome = {'street': 0.19, 'garage': 0.81}  # from the total amount of driving profiles, this share represents the ones who have a garage or not.
        commuters_atworkplace = {'workpark': 0.5, 'publicpark': 0.25, 'none': 0.25}  # This share applies only for commuters type driving profiles

        # This configuration applies for all profiles
        whenAtHome ={'street': {'prob_charging_point' :
                                         {'errands':  {'public':0.5,'none':0.5},
                                          'escort':   {'public':0.5,'none':0.5},
                                          'leisure':  {'public':0.5,'none':0.5},
                                          'shopping': {'public':0.5,'none':0.5},
                                          'home':     {'public':0.5,'none':0.5},
                                          'workplace':{'public':0.0,'workplace':1.0,'none':0.0},
                                          'driving':  {'none':1.0}
                                          },
                                    'capacity_charging_point' :
                                          {'public':22,'home':3.7,'workplace':11,'none':0}
                                    },
                     'garage': {'prob_charging_point' :
                                         {'errands':  {'public':0.5,'none':0.5},
                                          'escort':   {'public':0.5,'none':0.5},
                                          'leisure':  {'public':0.5,'none':0.5},
                                          'shopping': {'public':0.5,'none':0.5},
                                          'home':     {'public':0.0,'home':1.0,'none':0.0},
                                          'workplace':{'public':0.0,'workplace':1.0,'none':0.0},
                                          'driving':  {'none':1.0}
                                          },
                                    'capacity_charging_point' :
                                          {'public':22,'home':3.7,'workplace':11,'none':0}
                                    }
                        }
        # this configuration applies only for commuters type and depends on the case ('workpark', 'publicpark', 'none') the above configuration gets replaced the 'workplace' key with the indicated below
        whenAtWork = {'workpark':{'public':0.0,'workplace':1.0,'none':0.0},
                      'publicpark':{'public':0.5,'workplace':0.0,'none':0.5},
                      'none':{'public':0.0,'workplace':0.0,'none':1.0}}


####################################################
########### Configuration for grid demand ##########
####################################################

    if run_charging:

        options_list = ['immediate',
                        'balanced',
                        'from_0_to_24_at_home',
                        'from_23_to_8_at_home'
                        ]

####################################################
######### Configuration for csv report file ########
####################################################

    if run_export:

        report_folder = 'csv'


####################################################
################# END CONFIGURATION ################
####################################################









############# DO NOT MODIFY THIS SECTION ###########
####################################################

    if run_driving:

        inventory = [[dbdir,stat1,stat2,stat3,param_comm_fulltime,rules_comm_fulltime,0,round(bev_n*dist['fulltime'])],
                     [dbdir,stat1,stat2,stat3,param_comm_parttime,rules_comm_parttime,0,round(bev_n*dist['parttime'])],
                     [dbdir,stat1,stat2,stat3,param_free,rules_freetime,0,round(bev_n*dist['freetime'])]]

        lista = []
        for l in inventory:
            for p in drive_iter(*l):
                lista.append(p)

        if is_ray:
            queue = []
        else:
            queue = Queue()

        for q,seed in zip(lista, seeds):
            if is_ray:
                queue.append(evsteps.remote(*q,seed))
            else:
                queue.put((q,seed))

        if is_ray:
            ray.get(queue)
        else:
            io_lock = Lock()
            queue_lock = Lock()
            processes = {}
            for i in range(nr_workers):
                processes[i] = Process(target=scen_solve_mov, args=(evsteps, queue, queue_lock, io_lock))
                processes[i].start()
            for i in range(nr_workers):
                processes[i].join()
        print('=:=:=:=:=:=:=:=:=:=:= Driving done! =:=:=:=:=:=:=:=:=:=:')


    db = DataBase(dbdir)

    if run_availability:
        db.update()
        iddrivingp = [k for k, v in db.db.items() if v['kind'] == 'driving']
        random.shuffle(iddrivingp)
        groups = {}
        init = 0
        for key, val in parkingathome.items():
            idx = init + int(round(len(iddrivingp)*val+0.01, 0))
            try:
                print('When_at_home slice:', init, ':', idx)
                for code in iddrivingp[init:idx]:
                    groups[code] = {'g_type': db.db[code]['g_type'],
                                    'per_str': db.db[code]['per_str'],
                                    'whenathome': key,
                                    'whenatwork': False}
            except:
                print('When_at_home slice:', init, ':', idx, 'out of range. Total profiles:',len(iddrivingp))
                for code in iddrivingp[init:]:
                    groups[code] = {'g_type': db.db[code]['g_type'],
                                    'per_str': db.db[code]['per_str'],
                                    'whenathome': key,
                                    'whenatwork': False}
            init = idx
        commuters = []
        for code, dict_ in groups.items():
            if 'commuter' == dict_['g_type']:
                commuters.append(code)
        random.shuffle(commuters)
        init = 0
        for key, val in commuters_atworkplace.items():
            idx = init + int(round(len(commuters)*val+0.01, 0))
            try:
                print('Commuter_at_work slice:', init, ':', idx)
                for code in commuters[init:idx]:
                    groups[code]['whenatwork'] = key
            except:
                print('Commuter_at_work slice:', init, ':', idx, 'out of range. Total profiles:',len(commuters))
                for code in commuters[init:]:
                    groups[code]['whenatwork'] = key
            init = idx
        for cod, dic in groups.items():
            print(cod, dic)
        if is_ray:
            queue = []
        else:
            queue = Queue()
        for code, obs in groups.items():
            q = [whenAtHome, whenAtWork, obs, code, battery_capacity, charging_eff, soc_init, soc_min, db, dbdir, battopt]
            if is_ray:
                queue.append(gridsteps.remote(*q))
            else:
                queue.put(q)
        if is_ray:
            ray.get(queue)
        else:
            io_lock = Lock()
            queue_lock = Lock()
            processes = {}
            for i in range(nr_workers):
                processes[i] = Process(target=scen_solve, args=(gridsteps, queue, queue_lock, io_lock))
                processes[i].start()
            for i in range(nr_workers):
                processes[i].join()
        print('=:=:=:=:=:=:=:=:=:=:= Grid availability done! =:=:=:=:=:=:=:=:=:=:')

    if run_charging:
        db.update()
        for code, v in db.db.items():
            if v['kind'] == 'availability':
                print('   Success?  Availability Profile: ', code, ' : ', v['success'])

        for option in options_list:
            db.update()
            for ids in db.db.keys():
                if db.db[ids]['kind'] == 'availability':
                    c = Charging(ids)
                    c.loadScenario(db)
                    c.setSubScenario(option)
                    c.run()
                    c.save_profile(dbdir)
        print('=:=:=:=:=:=:=:=:=:=:= Charging options done! =:=:=:=:=:=:=:=:=:=:')

    if run_export:
        db.update()
        export = Export()
        export.loaddata(db)
        print("Creating report... \nIf there is a failed availability file in the database, this process may hang up. \nIn which case check your database folder")
        export.to_csv()
        export.save_files(report_folder)
        print('=:=:=:=:=:=:=:=:=:=:= Export done! =:=:=:=:=:=:=:=:=:=:')

    print('==== Program finished ====')
