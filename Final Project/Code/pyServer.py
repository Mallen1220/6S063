import argparse
import math
import time
import threading
import requests

from pythonosc import dispatcher
from pythonosc import osc_server

# Nodejs Control Server
host = 'http://localhost:3000'
state_address = '/state/'
reset_address = '/reset'

# Calibration Variables
is_callibrated = False
startTime = 0
cycle = 0
totalCycles = 12 # 2 * number of different music and light states
duration = 30.0 # seconds per cycle
movingAverage = [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
movingTotal = [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
movingCount = [0,0,0,0]
fConfidence = []
rConfidence = []
rollingMax = 100
rollingAverage = [[[],[],[],[],[]], [[],[],[],[],[]], [[],[],[],[],[]], [[],[],[],[],[]]]
# Generate rolling average data structure
for node in range(4):
    for band in range(5):
        rollingAverage[node][band] = [0 for i in range(rollingMax)]
rollingAverageVal = [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
rollingCount = [0,0,0,0]


maxF = 0
maxR = 0

maxF_i = 3
maxR_i = 1


def parseBandPower(addr, *args):
    # args = args[:5]
    #print("BP: ",args)
    node = args[0] - 1
    if node > 3:
        return
    count = rollingCount[node]
    for band in range(5):
        oldValue = rollingAverage[node][band][count]
        newValue = args[band + 1]
        rollingAverageVal[node][band] = ((rollingAverageVal[node][band]*rollingMax) - oldValue + newValue)/float(rollingMax)
        rollingAverage[node][band][count] = newValue
    rollingCount[node] = (count + 1) % rollingMax
    if not is_callibrated:
        if cycle == 0 or cycle > totalCycles:
            return
        node = args[0] - 1
        for band in range(5):
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
        #multiplier *= 0.8
        multiplier *= beta/float(theta)
    if beta < delta:
        multiplier *= 0.4
    # TODO: calibrate confidence calculator
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
        #multiplier *= 0.8
        multiplier *= theta/float(beta)
    if beta > delta:
        multiplier *= 0.4
    # TODO: calibrate confidence calculator
    return multiplier

def resetState():
    request = requests.get(host + reset_address)
    return

if __name__ == "__main__":
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

    inp = None
    while (True):
        if inp == "calibrate" or inp == "c":
            # Run calibration
            if cycle == 0:
                # Set first cycles light and music state
                cycle += 1
                print("Start focused activity")
                print("(press any button to continue)")
                input()
                request = requests.get(host + state_address + str(cycle))
                is_callibrated = False
                startTime = time.time()
                print("Cycle: " + str(cycle))
            if cycle <= totalCycles/2:
                if startTime + duration < time.time():
                    # Calculate final average number
                    f_c = 0
                    for node in range(4):
                        f_c += confidenceFocus(movingAverage[node])
                    f_c /= 4.0
                    fConfidence.append(f_c)

                    # Change to the next cycle and adapt light and music state
                    cycle += 1
                    if cycle == int(totalCycles/2) + 1:
                        # Reset lights and music before next set of cyles
                        requests.get(host + reset_address)
                        print("Switch to relaxed activity")
                        print("(press anything to continue)")
                        input()
                    
                    # Move to next cycle
                    # Reset values
                    movingAverage = [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
                    movingTotal = [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
                    movingCount = [0,0,0,0]

                    request = requests.get(host + state_address + str(cycle%int(totalCycles/2)))
                    startTime = time.time()
                    print("Cycle: " + str(cycle))
                else:
                    # Calculate moving average using server
                    continue
            elif cycle <= totalCycles:
                if startTime + duration < time.time():
                    # Calculate final average number
                    r_c = 0
                    for node in range(4):
                        r_c += confidenceRelax(movingAverage[node])
                    r_c /= 4.0
                    rConfidence.append(r_c)

                    # Change to the next cycle and adapt light and music state
                    cycle += 1
                    
                    # Move to next cycle
                    # Reset values
                    movingAverage = [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
                    movingTotal = [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
                    movingCount = [0,0,0,0]

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

            #print(confidenceRelax(rollingAverageVal[0]))
            pass
        elif inp == "focus" or inp == "f":
            # Use the calibrated settings to make user focused
            request = requests.get(host + state_address + str(maxF_i))
            print(request.text)
            inp = None
        elif inp == "q" or inp == "quit":
            print("Quitting application...")
            break
        else:
            print("Enter input:")
            inp = input()











