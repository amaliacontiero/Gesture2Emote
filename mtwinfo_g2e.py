

class mtwinfoG2E:
    def __init__(self):
        self.experimental_sensors = {
        0: {"ID": "00B4F131", "tip_part": "HAND", "desc": "hand"},
        1: {"ID": "00B4F07B", "tip_part": "fArm", "desc": "wrist"},
        2: {"ID": "00B4EF3E", "tip_part": "uArm", "desc": "upper arm"},
        }

    def idtosegment(self,idvalue):
        for segment in self.experimental_sensors.values():
            if segment['ID'] == idvalue:
                bodysegment = segment['tip_part']
        return bodysegment  
    
    def segmentNumber(self,idvalue):
        for number, segment in self.experimental_sensors.items():
            if segment['ID'] == idvalue:
                return number
        return None
    
