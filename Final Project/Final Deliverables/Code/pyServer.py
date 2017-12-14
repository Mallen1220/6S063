import argparse
import math
import time
import threading
import requests

from pythonosc import dispatcher
from pythonosc import osc_server

if __name__ == "__main__":

    # Nodejs Control Server
    host = 'http://localhost:3000'
    state_address = '/state/'
    reset_address = '/reset'

    # Calibration Variables
    is_callibrated = False
    startTime = 0
    cycle = 0
    totalCycles = 12                                                                # 2 * number of different music and light states
    duration = 30.0                                                                 # seconds per cycle

    # Number of Nodes (Ganglion Board = 4)
    num_nodes = 4
    # Number of Bands (Theta, Delta, Alpha, Beta, Gamma = 5)
    num_bands = 5
    # Number of data points stored for calculating rolling average
    num_rolling_dp = 100

    # Initialize Data Structures
    movingAverage = [[0 for i in range(num_bands)] for j in range(num_nodes)]       #[[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
    movingTotal = [[0 for i in range(num_bands)] for j in range(num_nodes)]         #[[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
    movingCount = [0 for i in range(num_nodes)]                                     #[0,0,0,0]
    fConfidence = []
    rConfidence = []
    rollingDataSet = [[[0 for i in range(num_rolling_dp)] for j in range(num_bands)] for k in range(num_nodes)]# [[[],[],[],[],[]], [[],[],[],[],[]], [[],[],[],[],[]], [[],[],[],[],[]]]
    rollingAverage = [[0 for i in range(num_bands)] for j in range(num_nodes)]   #[[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
    rollingCount = [0 for i in range(num_nodes)]                                    #[0,0,0,0]

    # MAX heuristic value for Focus & Relax
    maxF = 0
    maxR = 0
    # Index of cycle with MAX heuristic value for Focus & Relax
    maxF_i = 0
    maxR_i = 0

    #### Callback function for each incoming OSC packet containing Band Power data ####
    def parseBandPower(addr, *args):
        # args = args[:5]
        #print("BP: ",args)
        node = args[0] - 1
        if node > 3:
            return
        count = rollingCount[node]
        for band in range(num_bands):
            oldValue = rollingDataSet[node][band][count]
            newValue = args[band + 1]
            rollingAverage[node][band] = ((rollingAverage[node][band]*num_rolling_dp) - oldValue + newValue)/float(num_rolling_dp)
            rollingDataSet[node][band][count] = newValue
        rollingCount[node] = (count + 1) % num_rolling_dp
        if not is_callibrated:
            if cycle == 0 or cycle > totalCycles:
                return
            node = args[0] - 1
            for band in range(num_bands):
                movingAverage[node][band] = (movingAverage[node][band]*movingCount[node] + args[band + 1])/float(movingCount[node]+1)
                movingTotal[node][band] += args[band + 1]
            movingCount[node] += 1

    #### Calculates FOCUS confidence value from BP array ####
    # Input: bpArray = [delta, theta, alpha, beta, gamma]
    # Output: confidenceValue = (0-1)
    def confidenceFocus(bpArray):
        delta = bpArray[0]
        theta = bpArray[1]
        beta = bpArray[2]
        multiplier = 1.0
        if beta < theta:
            multiplier *= beta/float(theta)
        if beta < delta:
            multiplier *= 0.4
        return multiplier

    #### Calculates RELAX confidence value from BP array ####
    # Input: bpArray = [delta, theta, alpha, beta, gamma]
    # Output: confidenceValue = (0-1)
    def confidenceRelax(bpArray):
        delta = bpArray[0]
        theta = bpArray[1]
        beta = bpArray[2]
        multiplier = 1.0
        if beta > theta:
            multiplier *= theta/float(beta)
        if beta > delta:
            multiplier *= 0.4
        return multiplier

    def confidenceFromMovingAverage(confidenceFX):
        confidence_val = 0
        for node in range(num_nodes):
            confidence_val += confidenceFX(movingAverage[node])
        confidence_val /= float(num_nodes)
        return confidence_val

    def resetState():
        request = requests.get(host + reset_address)
        return

    def resetConfidence():
        global fConfidence
        global rConfidence
        fConfidence = []
        rConfidence = []

    def resetDataStructures():
        resetMovingAverage()
        resetRollingAverage()

    def resetMovingAverage():
        global movingAverage
        global movingTotal
        global movingCount
        movingAverage = [[0 for i in range(num_bands)] for j in range(num_nodes)]
        movingTotal = [[0 for i in range(num_bands)] for j in range(num_nodes)]
        movingCount = [0 for i in range(num_nodes)]

    def resetRollingAverage():
        global rollingDataSet
        global rollingAverage
        global rollingCount
        rollingDataSet = [[[0 for i in range(num_rolling_dp)] for j in range(num_bands)] for k in range(num_nodes)]
        rollingAverage = [[0 for i in range(num_bands)] for j in range(num_nodes)]
        rollingCount = [0 for i in range(num_nodes)]


    # Parse Arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip",
        default="127.0.0.1", help="The ip to listen on")
    parser.add_argument("--port",
        type=int, default=12345, help="The port to listen on")
    args = parser.parse_args()

    # Create OSC Server to listen for OSC messages and call parseBandPower callback function
    dispatcher = dispatcher.Dispatcher()
    dispatcher.map("/openbciBP", parseBandPower)    
    server = osc_server.ThreadingOSCUDPServer(
        (args.ip, args.port), dispatcher)
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    
    # Reset light and music
    resetState()

    # Main Loop State
    inp = None

    while (True):
        if inp == "calibrate" or inp == "c":
            # Run calibration
            if cycle == 0:
                # Set first cycles light and music state
                resetConfidence()
                cycle += 1
                print("Start focused activity")
                print("(press ENTER to continue)")
                input()
                request = requests.get(host + state_address + str(cycle))
                is_callibrated = False
                startTime = time.time()
                print("Cycle: " + str(cycle))
            if cycle <= totalCycles/2:
                if startTime + duration < time.time():
                    f_c = confidenceFromMovingAverage(confidenceFocus)
                    fConfidence.append(f_c)

                    # Move on to next Cycle: Reset Variables + Change light/music state
                    cycle += 1
                    if cycle == int(totalCycles/2) + 1:
                        # Reset lights and music before next set of cyles
                        requests.get(host + reset_address)
                        print("Switch to relaxed activity")
                        print("(press ENTER to continue)")
                        input()
                    
                    # Move to next cycle
                    resetMovingAverage()

                    request = requests.get(host + state_address + str(cycle%int(totalCycles/2)))
                    startTime = time.time()
                    print("Cycle: " + str(cycle))
                else:
                    # Calculate moving average using server
                    continue
            elif cycle <= totalCycles:
                if startTime + duration < time.time():
                    r_c = confidenceFromMovingAverage(confidenceRelax)
                    rConfidence.append(r_c)

                    # Move on to next Cycle: Reset Variables + Change light/music state
                    cycle += 1
                    
                    resetMovingAverage()

                    request = requests.get(host + state_address + str(cycle%int(totalCycles/2)))
                    startTime = time.time()
                    print("Cycle: " + str(cycle))
                else:
                    # Calculate moving average using server
                    continue
            else:
                print("Calibration Complete")

                for c in range(len(fConfidence)):
                    if fConfidence[c] > maxF:
                        maxF = fConfidence[c]
                        maxF_i = c
                    if rConfidence[c] > maxR:
                        maxR = rConfidence[c]
                        maxR_i = c

                print("Most Focused Setting: Setting #" + str(maxF_i))
                print("Most Relaxed Setting: Setting #" + str(maxR_i))
                resetState()
                is_callibrated = True
                cycle = 0
                inp = None

        elif inp == "relax" or inp == "r":
            # Use the calibrated settings to make user relaxed
            request = requests.get(host + state_address + str(maxR_i))
            print(request.text)
            inp = None
        elif inp == "focus" or inp == "f":
            # Use the calibrated settings to make user focused
            request = requests.get(host + state_address + str(maxF_i))
            print("State Changed")
            inp = None
        elif inp == "d" or inp == "debug":
            print("Focus Confidence – " + str(fConfidence))
            print("Relax Confidence – " + str(rConfidence))
            print("Max Focus Index – " + str(maxF_i))
            print("Max Relax Index – " + str(maxR_i))
            inp = None
        elif inp == "q" or inp == "quit":
            print("Quitting application...")
            break
        elif inp == "h" or inp == "help":
            print("Commands:")
            print("q or quit            : quit application")
            print("c or calibrate       : calibrate Trancendance system")
            print("r or relax           : enter relaxed state after calibration")
            print("f or focus           : enter focused state after calibration")
            print("h or help            : display help menu")
            inp = None
        else:
            print("Enter command or 'help' to see all commands:")
            inp = input()











