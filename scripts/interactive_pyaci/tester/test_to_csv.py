from os import listdir
from os.path import isfile, join
import json
import csv

test_n = str(5)

mypath = "/Users/Tim-Mac/msc/bm-control/dev/nrf5SDKforMeshv310src/scripts/interactive_pyaci/tester/"
mypath += "test_" + test_n + "/"
setuppath = mypath + "/setup/"

files = [f for f in listdir(setuppath) if isfile(join(setuppath, f))]
files = [f for f in files if "test_" + test_n in f]
files.sort()

def get_header(d):
    arr = []

    for k, v in d.items():
        if(type(v) is dict):
            headers = get_header(v)
            arr += [k + "_" + h for h in headers]
        else:
            arr.append(k)

    return arr


def expand(d):
    arr = []

    for k, v in d.items():
        if(type(v) is dict):
            arr = arr + expand(v)
        else:
            arr.append(v)

    return arr


csv_file = open(mypath + 'test_'+ test_n + '_setup.csv', 'w')
csvwriter = csv.writer(csv_file)

with open(setuppath + files[0], 'r') as f:
    data = json.load(f)
    row = ["test_file"] + get_header(data)
    csvwriter.writerow(row)


for ff in files:
    with open(setuppath + ff, 'r') as f:
        data = json.load(f)
        row = [ff] + expand(data)
        csvwriter.writerow(row)


csv_file.close()