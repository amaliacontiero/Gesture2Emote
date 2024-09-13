import os
import re

class mtwprefix:
    def __init__(self, selected_sensors):
        self.experimental_sensors = {
        0: {"ID": "00B4EC22", "osim_name": "pelvis", "desc": "Pelvis"},
        1: {"ID": "00B4EF3D", "osim_name": "femur_l", "desc": "ULeg L"},
        2: {"ID": "00B4F1A5", "osim_name": "femur_r", "desc": "ULeg R"},
        3: {"ID": "00B4EECD", "osim_name": "tibia_l", "desc": "LLeg L"},
        4: {"ID": "00B4F0C0", "osim_name": "tibia_r", "desc": "LLeg R"},
        5: {"ID": "00B4F10D", "osim_name": "talus_l", "desc": "Foot L"},
        6: {"ID": "00B4F3A7", "osim_name": "talus_r", "desc": "Foot R"},
        7: {"ID": "00B4F3A9", "osim_name": "humerus_l", "desc": "UArm L"},
        8: {"ID": "00B4EF3E", "osim_name": "humerus_r", "desc": "UArm R"},
        9: {"ID": "00B4F3AA", "osim_name": "radius_l", "desc": "FArm L"},
        10: {"ID": "00B4F07B", "osim_name": "radius_r", "desc": "FArm R"},
        11: {"ID": "00B4F2DA", "osim_name": "hand_l", "desc": "Hand L"},
        12: {"ID": "00B4F131", "osim_name": "hand_r", "desc": "Hand R"},
        13: {"ID": "00B4F1A6", "osim_name": "torso", "desc": "Head"}
        }
        self.test_sensors = dict()
        for i in selected_sensors:
            self.test_sensors[i] = self.experimental_sensors[i]
        

    def idtosegment(self,idvalue):
        for segment in self.experimental_sensors.values():
            if segment['ID'] == idvalue:
                bodysegment = segment['desc']
        return bodysegment     
        
    def showsensormap(self):
        print('Sensor ID  || OpenSim name  || Description')
        print('=================================================')
        for sensor_id, sensor_info in self.test_sensors.items():
            print(sensor_info['ID'], '  ||', sensor_info['osim_name'], '      ||', sensor_info['desc'])
            print('=================================================')

    def getfilenames(self, datapath):
        MTw_filenames = []

        for root, dirs, files in os.walk(datapath):
            for file in files:
                if file.startswith("MT_"):
                    MTw_filenames.append(file)
        print(len(MTw_filenames),'MTw data files found')
        
        return MTw_filenames
    
    def getprefix(self, MTw_filenames):
        unique_mtwtrialprefixes = set()
        for filename in MTw_filenames:
            match = re.match(r'(\w+)_(\d{4}-\d{2}-\d{2})_(\w+)-(\d+)_(\w+).txt', filename) # regex on filenames
            
            if match: # extract filename data
                header, date, awinda_station_id, trial, sensor_id = match.groups()
                unique_mtwtrialprefixes.add(f'{header}_{date}_{awinda_station_id}-{trial}')    
            else:
                print('Invalid:', filename)

        mtwtrialprefix = sorted(list(unique_mtwtrialprefixes))
        print('There are',len(mtwtrialprefix),'trials available.')

        return mtwtrialprefix
    
    