import requests
# http://docs.python-requests.org/en/latest/user/quickstart/#make-a-request
light = True

with open('OpenBCI-Ganglion-RAW-eyes open_closed.csv') as f:
    time = 0
    for line in f:
        time += 1
        lineSplit = line.split(',')
        if len(lineSplit) == 9:
            for i, num in enumerate(lineSplit[1:5]):
                if abs(float(num)) > 1000:
                    # Trigger
                    print(time/200)
                    if light:
                        r = requests.get('localhost:3000/test/off')
                        light = False
                    else:
                        r = requests.get('localhost:3000/test/on')
                        light = True

