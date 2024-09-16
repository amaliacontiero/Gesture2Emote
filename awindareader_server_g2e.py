import sys
import time
from collections import deque
from threading import Lock
import xsensdeviceapi as xda
import keyboard
import socket
from datetime import datetime, timezone
from mtwinfo_g2e import mtwinfoG2E
import paho.mqtt.client as mqtt

HOST = '127.0.0.1'
PORT = 27215


class XsPortInfoStr:
    def __str__(self, p):
        return f"Port: {p.portNumber():>2} ({p.portName()}) @ {p.baudrate():>7} Bd, ID: {p.deviceId().toString()}"

class XsDeviceStr:
    def __str__(self, d):
        return f"ID: {d.deviceId().toString()} ({d.productCode()})"

def find_closest_update_rate(supported_update_rates, desired_update_rate):
    if not supported_update_rates:
        return 0

    if len(supported_update_rates) == 1:
        return supported_update_rates[0]

    closest_update_rate = min(supported_update_rates, key=lambda x: abs(x - desired_update_rate))
    return closest_update_rate

class WirelessMasterCallback(xda.XsCallback):
    def __init__(self):
        super().__init__()
        self.m_connectedMTWs = set()
        self.m_mutex = Lock()

    def getWirelessMTWs(self):
        with self.m_mutex:
            return self.m_connectedMTWs.copy()

    def onConnectivityChanged(self, dev, newState):
        with self.m_mutex:
            if newState == xda.XCS_Disconnected:
                print(f"\nEVENT: MTW Disconnected -> {dev.deviceId()}")
                self.m_connectedMTWs.discard(dev)
            elif newState == xda.XCS_Rejected:
                print(f"\nEVENT: MTW Rejected -> {dev.deviceId()}")
                self.m_connectedMTWs.discard(dev)
            elif newState == xda.XCS_PluggedIn:
                print(f"\nEVENT: MTW PluggedIn -> {dev.deviceId()}")
                self.m_connectedMTWs.discard(dev)
            elif newState == xda.XCS_Wireless:
                print(f"\nEVENT: MTW Connected -> {dev.deviceId()}")
                self.m_connectedMTWs.add(dev)
            elif newState == xda.XCS_File:
                print(f"\nEVENT: MTW File -> {dev.deviceId()}")
                self.m_connectedMTWs.discard(dev)
            elif newState == xda.XCS_Unknown:
                print(f"\nEVENT: MTW Unknown -> {dev.deviceId()}")
                self.m_connectedMTWs.discard(dev)
            else:
                print(f"\nEVENT: MTW Error -> {dev.deviceId()}")
                self.m_connectedMTWs.discard(dev)

class MtwCallback(xda.XsCallback):
    def __init__(self, mtwIndex, device):
        super().__init__()
        self.m_packetBuffer = deque(maxlen=300)
        self.m_mutex = Lock()
        self.m_mtwIndex = mtwIndex
        self.m_device = device

    def dataAvailable(self):
        with self.m_mutex:
            return bool(self.m_packetBuffer)

    def getOldestPacket(self):
        with self.m_mutex:
            packet = self.m_packetBuffer[0]
            return packet

    def deleteOldestPacket(self):
        with self.m_mutex:
            self.m_packetBuffer.popleft()

    def getMtwIndex(self):
        return self.m_mtwIndex

    def device(self):
        assert self.m_device is not None
        return self.m_device

    def onLiveDataAvailable(self, _, packet):
        with self.m_mutex:
            # NOTE: Processing of packets should not be done in this thread.
            self.m_packetBuffer.append(packet)
            if len(self.m_packetBuffer) > 300:
                self.deleteOldestPacket()
                

# ------------------------------------------------------------------------- #

# MQTT

broker_ip = 'localhost'

def connect_to_broker(broker_ip):
    client = mqtt.Client("Gesture2Emote")
    client.username_pw_set("thin","genious")
    if client.connect(broker_ip) != 0:
        print("Could not connect to MQTT broker.")
    else: 
        print(f"Connected to MQTT broker {broker_ip}")
    return client
        
def send_message(client, message):
    client.publish("Gesture2Emote", message)



if __name__ == '__main__':
    
    def devCleanupQuit():
        control.close()
        print("Control object closed")
        print("Quitting...")
        quit()
    
    desired_update_rate = 60
    desired_radio_channel = 11

    wireless_master_callback = WirelessMasterCallback()
    mtw_callbacks = []

    print("Constructing XsControl...")
    control = xda.XsControl.construct()
    if control is None:
        print("Failed to construct XsControl instance.")
        sys.exit(1)

    try:
        print("Scanning ports...")

        detected_devices = xda.XsScanner_scanPorts()

        print("Finding wireless master...")
        wireless_master_port = next((port for port in detected_devices if port.deviceId().isWirelessMaster()), None)
        if wireless_master_port is None:
            print("No wireless masters found")
            devCleanupQuit()

        print(f"Wireless master found @ {wireless_master_port}")

        print("Opening port...")
        if not control.openPort(wireless_master_port.portName(), wireless_master_port.baudrate()):
            print(f"Failed to open port {wireless_master_port}")
            devCleanupQuit()

        print("Getting XsDevice instance for wireless master...")
        wireless_master_device = control.device(wireless_master_port.deviceId())
        if wireless_master_device is None:
            print(f"Failed to construct XsDevice instance: {wireless_master_port}")
            devCleanupQuit()

        print(f"XsDevice instance created @ {wireless_master_device}")

        print("Setting config mode...")
        if not wireless_master_device.gotoConfig():
            print(f"Failed to go to config mode: {wireless_master_device}")
            devCleanupQuit()

        print("Attaching callback handler...")
        wireless_master_device.addCallbackHandler(wireless_master_callback)

        print("Getting the list of the supported update rates...")
        supportUpdateRates = xda.XsDevice.supportedUpdateRates(wireless_master_device, xda.XDI_None)

        print("Supported update rates: ", end="")
        for rate in supportUpdateRates:
            print(rate, end=" ")
        print()

        new_update_rate = find_closest_update_rate(supportUpdateRates, desired_update_rate)

        print(f"Setting update rate to {new_update_rate} Hz...")

        if not wireless_master_device.setUpdateRate(new_update_rate):
            print(f"Failed to set update rate: {wireless_master_device}")
            devCleanupQuit()

        print("Disabling radio channel if previously enabled...")

        if wireless_master_device.isRadioEnabled():
            if not wireless_master_device.disableRadio():
                print(f"Failed to disable radio channel: {wireless_master_device}")
                devCleanupQuit()

        print(f"Setting radio channel to {desired_radio_channel} and enabling radio...")
        if not wireless_master_device.enableRadio(desired_radio_channel):
            print(f"Failed to set radio channel: {wireless_master_device}")
            devCleanupQuit()

        print("Waiting for MTW to wirelessly connect...\n")


        # This function checks for user input to break the loop
        def user_input_ready():
            return False  # Replace this with your method to detect user input


        wait_for_connections = True
        connected_mtw_count = len(wireless_master_callback.getWirelessMTWs())
        while wait_for_connections:
            time.sleep(0.1)
            next_count = len(wireless_master_callback.getWirelessMTWs())
            if next_count != connected_mtw_count:
                print(f"Number of connected MTWs: {next_count}. Press 'Y' to start measurement.")
                connected_mtw_count = next_count

            wait_for_connections = not keyboard.is_pressed('y')



        print("Starting measurement...")
        if not wireless_master_device.gotoMeasurement():
            print(f"Failed to goto measurement mode: {wireless_master_device}")
            devCleanupQuit()
        

        print("Getting XsDevice instances for all MTWs...")
        all_device_ids = control.deviceIds()
        mtw_device_ids_scan = [device_id for device_id in all_device_ids if device_id.isMtw()]
        mtw_device_ids = [None] * 3
        mtw_devices = []
        
        
        
        for i in range(len(mtw_device_ids_scan)):
            priority = mtwinfoG2E().segmentNumber(mtw_device_ids_scan[i].toXsString())
            mtw_device_ids[priority] = mtw_device_ids_scan[i]
        
        for device_id in mtw_device_ids:
            mtw_device = control.device(device_id)
            if mtw_device is not None:
                mtw_devices.append(mtw_device)
            else:
                print("Failed to create an MTW XsDevice instance")
                devCleanupQuit()
            
            

        print("Attaching callback handlers to MTWs...")
        mtw_callbacks = [MtwCallback(i, mtw_devices[i]) for i in range(len(mtw_devices))]
        for i in range(len(mtw_devices)):
            mtw_devices[i].addCallbackHandler(mtw_callbacks[i])
        
        ready_to_record = False
            # Connect to MQTT Broker
        mqttclient = connect_to_broker(broker_ip)

        while not ready_to_record:
            ready_to_record = all([mtw_callbacks[i].dataAvailable() for i in range(len(mtw_callbacks))])
            if not ready_to_record:
                print("Waiting for data available...")
                time.sleep(0.5)
            #     optional, enable heading reset before recording data, make sure all sensors have aligned physically the same heading!!
            # else:
            #     print("Do heading reset before recording data, make sure all sensors have aligned physically the same heading!!")
            #     all([mtw_devices[i].resetOrientation(xda.XRM_Heading) for i in range(len(mtw_callbacks))])
            # TIP does heading reset before Tpose calibration, not needed for now

        if not wireless_master_device.startRecording():
            print("Failed to start recording. Aborting.")
            devCleanupQuit()

        print("\nMain loop. Press any key to quit\n")
        print("Waiting for data available...")

            
        quatData = [xda.XsEuler()] * len(mtw_callbacks)
        accData = [xda.XsEuler()] * len(mtw_callbacks)
        
        
        print_counter = 0
        while not user_input_ready():
            time.sleep(0.02)

            new_data_available = False
            for i in range(len(mtw_callbacks)):
                if mtw_callbacks[i].dataAvailable():
                    new_data_available = True
                    packet = mtw_callbacks[i].getOldestPacket()
                    quatData[i] = packet.orientationQuaternion()
                    accData[i] = packet.calibratedAcceleration()
                    
                    current_datetime = datetime.now(timezone.utc)
                    packettime = current_datetime.strftime('%T.%f')[:-3]
                    
                    mtw_callbacks[i].deleteOldestPacket()
                    
            send_str = ""        

            if new_data_available:
                '''
                for i in range(len(mtw_callbacks)):
                    send_str += f"{quatData[i][0]:.2f} {quatData[i][1]:.2f} {quatData[i][2]:.2f} {quatData[i][3]:.2f} "
                    send_str += f"{accData[i][0]:.2f} {accData[i][1]:.2f} {accData[i][2]:.2f} "
                '''
                for i in range(len(mtw_callbacks)):
                    send_str += f"{quatData[i][0]:.2f} {quatData[i][1]:.2f} {quatData[i][2]:.2f} {quatData[i][3]:.2f} "
                    send_str += f"{accData[i][0]:.2f} {accData[i][1]:.2f} {accData[i][2]:.2f} "
                
                try:
                    #send_result = client_socket.send(send_str.encode())
                    send_message(mqttclient, send_str)
                    
                        
                except:
                    print("Send failed with error")
                    devCleanupQuit()
                
                if print_counter % 30 == 0:
                    for i in range(len(mtw_callbacks)):
                        
                        print(f"[{i}]: {quatData[i][0]:.2f} {quatData[i][1]:.2f} {quatData[i][2]:.2f}  {quatData[i][3]:.2f}  ",
                              f"{accData[i][0]:.2f} {accData[i][1]:.2f} {accData[i][2]:.2f} \n {packettime}" )

                print_counter += 1

        print("Setting config mode...")
        if not wireless_master_device.gotoConfig():
            print(f"Failed to goto config mode: {wireless_master_device}")
            devCleanupQuit()

        print("Disabling radio...")
        if not wireless_master_device.disableRadio():
            print(f"Failed to disable radio: {wireless_master_device}")
            devCleanupQuit()

    except Exception as ex:
        print(ex)
        print("****ABORT****")
    except:
        print("An unknown fatal error has occurred. Aborting.")
        print("****ABORT****")

    print("Closing XsControl...")
    control.close()

    print("Deleting mtw callbacks...")

    print("Successful exit.")
    print("Press [ENTER] to continue.")
    input()

