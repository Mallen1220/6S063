import argparse
import math
import time
import threading

from pythonosc import dispatcher
from pythonosc import osc_server

is_callibrated = False
startTime = 0
cycle = 0
totalCycles = 6
duration = 2.0
movingAverage = [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
movingTotal = [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
movingCount = [0,0,0,0]
fConfidence = []
rConfidence = []
rollingAverage = [[[],[],[],[],[]], [[],[],[],[],[]], [[],[],[],[],[]], [[],[],[],[],[]]]
rollingAverageVal = [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
rollingCount = [0,0,0,0]
rollingMax = 3

maxF = 0
maxR = 0

maxF_i = None
maxR_i = None


def print_volume_handler(unused_addr, args, volume):
  print("[{0}] ~ {1}".format(args[0], volume))

def print_compute_handler(unused_addr, args, volume):
  try:
    print("[{0}] ~ {1}".format(args[0], args[1](volume)))
  except ValueError: pass

def parseFFT(addr, *args):
    # args is a tuple of 126 values
    # First value is channel #
    # Next 125 values are the amplitude values of the ith frequency

    # print(len(args))
    pass

def parseTimeSeries(addr, *args):
    print("TS: ",args)

def parseBandPower(addr, *args):
    #print("BP: ",args)
    if is_callibrated:
        node = args[0] - 1
        count = rollingCount[node]
        for band in range(5):
            oldValue = rollingAverage[node][band][count]
            newValue = args[band + 1]
            rollingAverageVal[node][band] = ((rollingAverageVal[node][band]*rollingMax) - oldValue + newValue)/float(rollingMax)
            rollingAverage[node][band][count] = newValue
        rollingCount[node] = (count + 1) % rollingMax
        """
        if node == 0:
            print(rollingAverage[node][4])
        """
        
    else:
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
        multiplier *= 0.8
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
        multiplier *= 0.8
    if beta > delta:
        multiplier *= 0.4
    # TODO: calibrate confidence calculator
    return multiplier


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip",
        default="127.0.0.1", help="The ip to listen on")
    parser.add_argument("--port",
        type=int, default=12345, help="The port to listen on")
    args = parser.parse_args()

    dispatcher = dispatcher.Dispatcher()
    dispatcher.map("/openbciFFT", parseFFT)
    dispatcher.map("/openbciTS", parseTimeSeries)
    dispatcher.map("/openbciBP", parseBandPower)

    

    server = osc_server.ThreadingOSCUDPServer(
        (args.ip, args.port), dispatcher)
    print("Serving on {}".format(server.server_address))
    #server.serve_forever()
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()
    
    print("LOOP STARTING")
    
    inp = None

    while (True):
        if inp == "calibrate":
            # Run calibration
            # Use data generated by parseBandPower over 1 minute
            #   Running average or time-weighted average
            # Change to next state combination by sending a request to 
            #   http://localhost:3000/i
            # where i is the index of the state combination
            # REST in Python: http://docs.python-requests.org/en/latest/
            #
            # Store most focused state combination and most relaxed state combination

            if cycle == 0:
                startTime = time.time()
                cycle += 1
                print("Cycle: " + str(cycle))
            if cycle <= totalCycles:
                if startTime + duration < time.time():
                    # Calculate final average number
                    f_c = 0
                    r_c = 0
                    for node in range(4):
                        f_c += confidenceFocus(movingAverage[node])
                        r_c += confidenceRelax(movingAverage[node])
                    f_c /= 5.0
                    r_c /= 5.0
                    fConfidence.append(f_c)
                    rConfidence.append(r_c)

                    print(f_c)
                    print(r_c)
                    #print(movingTotal)
                    #print(movingCount)

                    # Move to next cycle
                    # Reset values
                    movingAverage = [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
                    movingTotal = [[0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0], [0,0,0,0,0]]
                    movingCount = [0,0,0,0]


                    # TODO: Change to next state combination by sending a request to 
                    #   http://localhost:3000/i


                    startTime = time.time()
                    cycle += 1
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

                print(maxF_i)
                print(maxR_i)

                # Generate rolling average data structure
                for node in range(4):
                    for band in range(5):
                        rollingAverage[node][band] = [0 for i in range(rollingMax)]

                is_callibrated = True
                cycle = 0
                inp = None

        elif inp == "relax":
            # Use the calibrated settings to make user relaxed
            print(confidenceRelax(rollingAverageVal[0]))
            pass
        elif inp == "focus":
            # Use the calibrated settings to make user focused
            print(confidenceFocus(rollingAverageVal[0]))
            pass
        elif inp == "q" or inp == "quit":
            print("Quitting application...")
            break
        else:
            print("Enter input:")
            inp = input()











