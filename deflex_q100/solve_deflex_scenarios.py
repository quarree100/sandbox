
from deflex import main
from oemof.tools import logger
import os
import logging


def all_scenarios_from_dir(path, csv=True, xls=False):
    xls_scenarios = []
    csv_scenarios = []
    log = {}
    for name in os.listdir(path):
        if (name[-4:] == '.xls' or name[-5:] == "xlsx") and xls is True:
            xls_scenarios.append(os.path.join(path, name))
        if name[-4:] == "_csv" and csv is True:
            csv_scenarios.append(os.path.join(path, name))
    logging.info(str(xls_scenarios))
    logging.info(str(csv_scenarios))
    for c in csv_scenarios:
        name = os.path.basename(c)
        logging.info("Next scenario: {0}".format(name))
        try:
            main.model_scenario(csv_path=c, name=name)
        except Exception as e:
            log[c] = e
    for x in xls_scenarios:
        name = os.path.basename(x).replace(".", "_")
        logging.info("Next scenario: {0}".format(name))
        try:
            main.model_scenario(xls_file=x, name=name)
        except Exception as e:
            log[x] = e

    logging.info(log)


logger.define_logging()
base_path = "/home/uwe/reegis/scenarios/deflex/2014"
all_scenarios_from_dir(path=base_path)
