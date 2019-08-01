from os import listdir
from os.path import isfile, join
import json
import csv

test_n = str(5)

mypath = "/Users/Tim-Mac/msc/bm-control/dev/nrf5SDKforMeshv310src/scripts/interactive_pyaci/tester/"
mypath += "test_" + test_n + "/"
resultspath = mypath + "/results/"


files = [f for f in listdir(resultspath) if isfile(join(resultspath, f))]
files = [f for f in files if "test_" + test_n in f]
files.sort()

csv_file = open(mypath + "test_" + test_n + '_results.csv', 'w')
csvwriter = csv.writer(csv_file)

for ff in files:
    with open(resultspath + ff, 'r') as f:
        lines = f.readlines()
        lines = [json.loads(l) for l in lines]
        csvwriter.writerow([ff, len(lines)])