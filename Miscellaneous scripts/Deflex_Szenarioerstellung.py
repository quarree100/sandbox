from deflex import basic_scenario, main
from oemof.tools import logger
import logging

logger.define_logging(logfile='oemof.log',
                      screen_level=logging.INFO,
                      file_level=logging.DEBUG)

# Erstelle Szenarien für alle Geometrien und Jahre
years = [2012, 2013, 2014]
rmaps = ['de02','de17','de21','de22']

for year in years:
     for rmap in rmaps:
         basic_scenario.create_basic_scenario(year, rmap)

# print('Alles gerechnet')

# Rechne alle Szenarien

main.main(2014, 'de02')
print('Klappt für 2014 und de02, jetzt alle rechnen')

# for year in years:
#     for rmap in rmaps:
#         main.main(year, rmap)



#main.main(year=2012,rmap='de02')
#main.basic_scenario()
#demand.get_heat_profiles_deflex()



#deflex.main.main(year=20 12, rmap = 'de02')