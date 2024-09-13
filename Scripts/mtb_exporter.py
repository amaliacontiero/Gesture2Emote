#import xsensdeviceapi as xda
from xsensdeviceapi import xsensdeviceapi_py38_64 as xda
import time
from threading import Lock
import glob
import re
import os
import gc

import argparse

# Create the parser
parser = argparse.ArgumentParser(description="Process some variables.")

# Add arguments
parser.add_argument('--recording_subject', type=int, required=True, help='Description for recording_subject')
parser.add_argument('--recording_type', type=int, required=True, help='Description for recording_type')
parser.add_argument('--recording_class', type=int, required=True, help='Description for recording_class')

# Parse the arguments
args = parser.parse_args()

# Access the arguments
sub = args.recording_subject
typ = args.recording_type
cla = args.recording_class

class XdaCallback(xda.XsCallback):
    def __init__(self):
        xda.XsCallback.__init__(self)
        self.m_progress = 0
        self.m_lock = Lock()

class_rename = {'1. Wave': 'Wave', '2. Thumbs up': 'ThumbsUp', '3. Come': 'Come', '4. Point': 'Point', '5. Salute': 'Salute', '6. Angry fist': 'Angry', '7. Facepalm': 'Facepalm', '8. Crazy': 'Crazy', '9. Clapping': 'Clap', '10. Cheer': 'Cheer' }
sensor_segment = {'00B4EF3E':'uARM', '00B4F07B':'fARM', '00B4F131':'HAND',}

def main(inpath,outpath, subject, rectype, classname=None):
    
    #renamedclass = class_rename[classname]
    if rectype != "Idle":
        renamedclass = class_rename[classname]
        savename = f"Sub{subject}_{rectype}_{renamedclass}"
    else:
        savename = f"Sub{subject}_{rectype}"
    
    try: 
        print("Creating XsControl object...")
        control = xda.XsControl_construct()
        assert(control != 0)
        
        path = inpath

        print("Opening Awinda log file...")
        mtwlogfiles = []
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.startswith("MT_"):
                    mtwlogfiles.append(file)
                    print(file)
        print(len(mtwlogfiles), 'MTw logfiles found.')
        
        for logfile in mtwlogfiles:
            logfilepath = f'{path}{logfile}'
            print(logfilepath)
            try:
                if not control.openLogFile(logfilepath):
                    print(f"Failed to open log file: {logfilepath}. Skipping this file.")
                    continue
                print("Opened log file: %s" % logfilepath)

                deviceIdArray = control.mainDeviceIds()
                mtDeviceIdsArray = control.mtDeviceIds()
                
                print(mtDeviceIdsArray)
                callback = XdaCallback()
                
                for mtw in mtDeviceIdsArray:
                    
                    control = xda.XsControl_construct()
                    assert(control != 0)
                    if not control.openLogFile(logfilepath):
                        raise RuntimeError("Failed to open log file. Aborting.")

                    device = control.device(mtw)
                    assert(device != 0)
                    print("Processing device: %s, with ID: %s, found in file" % (device.productCode(), device.deviceId().toXsString()))
                    
                    device.addCallbackHandler(callback)
                    device.setOptions(xda.XSO_RetainBufferedData, xda.XSO_None) # Important! Because by default it doesn't retain buffered data.
                    
                    device.loadLogFile()
                    while device.isLoadLogFileInProgress(): # wait to load log file, otherwise 0 packets are returned
                        time.sleep(0)
                        
                    packetCount = device.getDataPacketCount()
                    print('Packet Count:', packetCount)
                    
                    mtwdeviceId = device.deviceId().toXsString()
                    #mtwproductcode = device.productCode().toXsString()
                    
                    # Export
                    # Initialize a string with header
                    output_string = "// General information:\n"
                    output_string += "//  MT Manager version: 2022.0.0\n"
                    output_string += "//  XDA version: 2022.0.0 build 7085 rev 119802 built on 2022-11-08\n"
                    output_string += "// Device information:\n"
                    output_string += f"//  DeviceId:{mtwdeviceId}\n" 
                    output_string += "//  ProductCode: MTW2-3A7G6\n" 
                    output_string += "//  Firmware Version: 4.6.0\n" 
                    output_string += "//  Hardware Version: 2.0.0\n" 
                    output_string += "// Device settings:\n" 
                    output_string += f"//  Filter Profile: human(46.1)\n"
                    output_string += f"//  Option Flags: Orientation Smoother Disabled, Position/Velocity Smoother Disabled, Continuous Zero Rotation Update Disabled, AHS Disabled, ICC Disabled\n"
                    output_string += f"// Coordinate system: ENU\n" # coordinateSystemOrientation()
                    #output_string += "PacketCounter\tAcc_X\tAcc_Y\tAcc_Z\tMat[1][1]\tMat[2][1]\tMat[3][1]\tMat[1][2]\tMat[2][2]\tMat[3][2]\tMat[1][3]\tMat[2][3]\tMat[3][3]\n"
                    output_string += "PacketCounter\tq0\tq1\tq2\tq3\tAcc_X\tAcc_Y\tAcc_Z\n"


                    index = 0
                    while index < packetCount:
                        packet = device.getDataPacketByIndex(index)

                        if packet.containsCalibratedData():
                            acc = packet.calibratedAcceleration()
                            #gyro = packet.calibratedGyroscopeData()
                            #mag = packet.calibratedMagneticField()
                            quaternion = packet.orientationQuaternion()
                            #euler = packet.orientationEuler()
                            #mat = packet.orientationMatrix()
                            #print(quaternion)

                            #output_string += f"{index+20000}\t\t\t\t\t\t{acc[0]}\t{acc[1]}\t{acc[2]}\t{gyro[0]}\t{gyro[1]}\t{gyro[2]}\t{mag[0]}\t{mag[1]}\t{mag[2]}\t{quaternion[0]}\t{quaternion[1]}\t{quaternion[2]}\t{quaternion[3]}\t{euler.x()}\t{euler.y()}\t{euler.z()}\n"
                            #output_string += f"{index+20000}\t{acc[0]}\t{acc[1]}\t{acc[2]}\t{mat[0,0]}\t{mat[1,0]}\t{mat[2,0]}\t{mat[0,1]}\t{mat[1,1]}\t{mat[2,1]}\t{mat[0,2]}\t{mat[1,2]}\t{mat[2,2]}\n"
                            output_string += f"{index}\t{quaternion[0]}\t{quaternion[1]}\t{quaternion[2]}\t{quaternion[3]}\t{acc[0]}\t{acc[1]}\t{acc[2]}\n"
                            
        
                        index += 1
                        
                    '''
                    #logpattern = r"^(MT_\d{4}-\d{2}-\d{2}_\w+-\d{3})+.*$"
                    logpattern = r"MT_\d{4}-\d{2}-\d{2}_(\w+)-(\d{3})\.mtb"

                    
                    match = re.search(logpattern, logfile)
                    if match:
                        #prefix = match.group(1)         # date and masterID
                        trial_number = match.group(2)   # trial number
                    '''
                        

                    logpattern = r"MT_\d{4}-(\d{2}-\d{2})_.*-(\d{3})\.mtb"

                    # Use re.search to find matches
                    match = re.search(logpattern, logfile)

                    if match:
                        date = match.group(1)  # This captures '09-03'
                        trial_number = match.group(2)  # This captures '000'

                        
                    else:
                        print("No match found.")

                    segment = sensor_segment[mtw.toXsString()]

                    os.makedirs(outpath, exist_ok=True)
                    file_path = f"{outpath}{savename}_{date}-{trial_number}_{segment}.txt" # help!
                    with open(file_path, "w") as file:
                        file.write(output_string)

                    print(f"Data saved to {file_path}")
                    
                
            except Exception as e:
                print(f"An error occurred while processing log file {logfilepath}: {e}. Skipping this file.")
                        
    except RuntimeError as error:
        print(error)
    except:
        print("An unknown fatal error has occured. Aborting.")
    else:
        print("Successful exit.")



subject_list = ['001','002','003','004','005']
rec_type_list = ['Continuous','Segmented','Idle']
class_name_list = ['1. Wave', '2. Thumbs up', '3. Come', '4. Point', '5. Salute', '6. Angry fist', '7. Facepalm', '8. Crazy', '9. Clapping', '10. Cheer']
   
subject = []
rec_type = []
class_name = [] 

# UNFORTUNATELY IT CANT EXPORT MORE THAN ONE *SEGMENTED* CLASS FOLDER AT A TIME......

subject.append(subject_list[sub])
rec_type.append(rec_type_list[typ])
class_name.append(class_name_list[cla])
#class_name = class_name_list

main_logfile_path = './Data/mtb_recordings/'
output_path = './Data/ASCII_Data/'
           

for i in subject:
    for j in rec_type:
        if j != 'Idle':
            for h in class_name:
                spec_path = f"{i}/{j}/{h}/"
                import_path = main_logfile_path + spec_path
                export_path = output_path + spec_path
                print(main_logfile_path+spec_path)
                main(import_path, export_path, i, j, h)
                
        else:
                spec_path = f"{i}/{j}/"
                import_path = main_logfile_path + spec_path
                export_path = output_path + spec_path
                print(main_logfile_path+spec_path)
                main(import_path, export_path, i, j)


    