import os, re, sys, pathlib, socket, logging

logging.getLogger().setLevel(logging.INFO)

vpy = "python3" if socket.gethostname() != "DESKTOP-H4LHSCT" else "python"

try:
    maxThread = int(sys.argv[1])
    spath = sys.argv[2]
    wpath = sys.argv[3]
    wdata = sys.argv[4]
except:
    maxThread = 4
    spath = pathlib.Path().resolve()
    wpath = "%s/output" % pathlib.Path().resolve()
    wdata = "%s/../data/light.json" % pathlib.Path().resolve()

buildings = []

def getResult(step):
    out = []
    for root, dirs, files in os.walk(wpath):
        for file in files:
            if re.match(r'^mip_%d_' % step, file):
                out.append(file)
    return out

for root, dirs, files in os.walk(wpath):
    for file in files:
        if file in [".gitignore"]:
            continue
        os.remove(os.path.join(root, file))

if __name__ == '__main__':

    ##################
    # process step 1 #
    ##################
    os.system("%s -u \"%s/mip1.py\" -rd \"%s\" -wd \"%s\" -mt %d" % (vpy, spath, wdata, wpath, maxThread))
    for result in getResult(1):
        building = int(result.split("_")[2].split(".")[0])
        os.system("%s -u \"%s/visualizer.py\" -rd \"%s\" -d \"%s/%s\"" % (vpy, spath, wdata, wpath, result))
    
    ##################
    # process step 2 #
    ##################
    os.system("%s -u \"%s/mip2.py\" -rd \"%s\" -wd \"%s\" -mt %d" % (vpy, spath, wdata, wpath, maxThread))
    for result in getResult(2):
        building = int(result.split("_")[2].split(".")[0])
        buildings.append(building)
        os.system("%s -u \"%s/visualizer.py\" -rd \"%s\" -d \"%s/%s\"" % (vpy, spath, wdata, wpath, result))
    
    ##################
    # process step 3 #
    ##################
    for building in buildings:
        os.system("%s -u \"%s/mip3.py\" -rd \"%s\" -wd \"%s\" -b %d -mt %d" % (vpy, spath, wdata, wpath, building, maxThread))
    for result in getResult(3):
        building = int(result.split("_")[2].split(".")[0])
        os.system("%s -u \"%s/visualizer.py\" -rd \"%s\" -d \"%s/%s\"" % (vpy, spath, wdata, wpath, result))
    
    ##################
    # process step 4 #
    ##################
    for building in buildings:
        os.system("%s -u \"%s/mip4.py\" -rd \"%s\" -wd \"%s\" -b %d -mt %d" % (vpy, spath, wdata, wpath, building, maxThread))
    for result in getResult(4):
        building = int(result.split("_")[2].split(".")[0])
        os.system("%s -u \"%s/visualizer.py\" -rd \"%s\" -d \"%s/%s\"" % (vpy, spath, wdata, wpath, result))

    ##################
    # process step 5 #
    ##################
    for building in buildings:
        os.system("%s -u \"%s/mip5.py\" -rd \"%s\" -wd \"%s\" -b %d -mt %d" % (vpy, spath, wdata, wpath, building, maxThread))
    for result in getResult(5):
        building = int(result.split("_")[2].split(".")[0])
        os.system("%s -u \"%s/visualizer.py\" -rd \"%s\" -d \"%s/%s\"" % (vpy, spath, wdata, wpath, result))