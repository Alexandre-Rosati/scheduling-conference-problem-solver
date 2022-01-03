import json, numpy, pathlib, logging, argparse
import pyomo.environ as pyo
from datetime import datetime

logging.getLogger().setLevel(logging.INFO)

parser = argparse.ArgumentParser()

parser.add_argument("-rd", "--rd", help='raw data', default="%s\\..\\data\\light.json" % pathlib.Path().resolve(), type=str)
parser.add_argument("-wd", "--wd", help='working directory', default="%s\\output" % pathlib.Path().resolve(), type=str)
parser.add_argument("-b", "--b", help='building id', default=2, type=int)
parser.add_argument("-mt", "--mt", help='maximum thread', default=4, type=int)
args = parser.parse_args()

buildingInput = int(args.b)
maximumThread = int(args.mt)

f = open("%s" % args.rd, "r")
data = json.loads(f.read())
f.close()

f = open("%s/mip_3_%d.json" % (args.wd, buildingInput), "r")
warmup = json.loads(f.read())
f.close()

model = pyo.ConcreteModel(doc="MIP model[4/5]: Gaps in stream minimizing")

logging.info("[%s] start mip4 (b=%d)" % (datetime.now(), buildingInput))

# =================================================
#   Warmup data
# =================================================

def warmupData():
    buildings = []
    for building in data["areas"]:
        if building["id"] == warmup["buildingId"]:
            buildings.append(building)
    data["buildings"] = buildings
    rooms = []
    for room in data["rooms"]:
        if room["buildingId"] == warmup["buildingId"]:
            rooms.append(room)
    data["rooms"] = rooms
    areas = []
    for area in data["areas"]:
        if area["id"] in warmup["areas"]:
            areas.append(area)
    data["areas"] = areas
    streams = []
    for stream in data["streams"]:
        if stream["id"] in warmup["streams"]:
            streams.append(stream)
    data["streams"] = streams

warmupData()

# =================================================
#   Data set
# =================================================

def streamsAreas(model, node):
    out = []
    for stream in data["streams"]:
        if stream["areaId"] == node:
            out.append(stream["id"])
    return out

def roomsBuildings(model, node):
    out = []
    for room in data["rooms"]:
        if room["buildingId"] == node:
            out.append(room["id"])
    return out

def aXsRule(model):
    return [(a,s) for a in model.A for s in model.AS[a]]

def bXrRule(model):
    return [(b,r) for b in model.B for r in model.BR[b]]

def smallRooms(model):
    out = []
    for s in data["streams"]:
        for r in data["rooms"]:
            if int(r["max"]) < int(s["att"]):
                out.append((s["areaId"], s["id"], r["buildingId"], r["id"]))
    return out

areas = [i["id"] for i in data["areas"]]
streams = [i["id"] for i in data["streams"]]
areasXstreams = [(i["areaId"], i["id"]) for i in data["streams"]]
buildings = [i["id"] for i in data["buildings"]]
rooms = [i["id"] for i in data["rooms"]]
days = [i["code"] for i in data["days"]]
timeslots = [i for i in data["timeslots"]]
dxt = [(i["day"], i["timeslot"]) for i in data["daysXtimeslots"]]

model.A = pyo.Set(initialize=areas, domain=pyo.NonNegativeIntegers)
model.S = pyo.Set(initialize=streams, domain=pyo.NonNegativeIntegers)
model.AS = pyo.Set(model.A, initialize=streamsAreas, domain=model.S)

model.B = pyo.Set(initialize=buildings, domain=pyo.NonNegativeIntegers)
model.R = pyo.Set(initialize=rooms, domain=pyo.NonNegativeIntegers)
model.BR = pyo.Set(model.B, initialize=roomsBuildings, domain=model.R)
model.D = pyo.Set(initialize=days)
model.T = pyo.Set(initialize=timeslots)

model.AxS = pyo.Set(initialize=aXsRule, domain=model.A * model.S)
model.BxR = pyo.Set(initialize=bXrRule, domain=model.B * model.R)
model.DxT = pyo.Set(initialize=dxt, domain=model.D * model.T)

model.SR = pyo.Set(initialize=smallRooms, domain=model.A * model.S * model.B * model.R)

# =================================================
#   Params
# =================================================

def sessions(model):
    dict = {}
    for s in data["streams"]:
        dict[s["id"]] = s["sessions"]
    return dict

def attendants(model):
    dict = {}
    for s in data["streams"]:
        dict[s["id"]] = s["att"]
    return dict

def areasMatrix(model):
    dict = {}
    for a in areas:
        for a_ in areas:
            dict[(a, a_)] = 1 if [a, a_] in data["areasMatrix"] or [a_, a] in data["areasMatrix"] else 0
    return dict

def maxRooms(model):
    dict = {}
    for r in data["rooms"]:
        dict[(r["buildingId"], r["id"])] = r["max"]
    return dict

def shifts(model):
    dict = {}
    for x in data["daysXtimeslots"]:
        dict[(x["day"], x["timeslot"])] = x["id"]
    return dict

def utility(model):
    utility = {}
    for i in data["streams"]:
        for j in data["rooms"]:
            relativeError = (((int(j["max"]) - int(i["att"])) / int(i["att"])) + 1)
            utility[(i["id"], j["id"])] = numpy.around(numpy.log(relativeError), decimals=6)
    return utility

model.N = pyo.Param(sessions, initialize=sessions, domain=pyo.NonNegativeIntegers)
model.P = pyo.Param(attendants, initialize=attendants, domain=pyo.NonNegativeIntegers)
model.I = pyo.Param(areasMatrix, initialize=areasMatrix, domain=pyo.NonNegativeIntegers)
model.RS = pyo.Param(maxRooms, initialize=maxRooms, domain=pyo.NonNegativeIntegers)
model.VAL = pyo.Param(shifts, initialize=shifts, domain=pyo.NonNegativeIntegers)
model.ISUM = pyo.Param(default=int(sum([pyo.value(model.I[i]) for i in model.I])/2), domain=pyo.NonNegativeIntegers)
model.M = pyo.Param(default=len(dxt), domain=pyo.NonNegativeIntegers)
model.UTIL = pyo.Param(utility, initialize=utility, domain=pyo.Reals)

# =================================================
#   Decision variables
# =================================================

model.X = pyo.Var(model.AxS, model.BxR, model.DxT, domain=pyo.NonNegativeIntegers, bounds=(0, 1))
model.Y = pyo.Var(model.AxS, model.B, domain=pyo.NonNegativeIntegers, bounds=(0, 1))
model.Q = pyo.Var(model.A, model.B, domain=pyo.NonNegativeIntegers, bounds=(0, 1))
model.V = pyo.Var(model.A, model.A, model.B, domain=pyo.NonNegativeIntegers, bounds=(0, 1))
model.U = pyo.Var(model.AxS, model.BxR, domain=pyo.NonNegativeIntegers, bounds=(0, 1))
model.FIRST = pyo.Var(model.AxS, domain=pyo.NonNegativeIntegers, bounds=(1, len(dxt)))
model.LAST = pyo.Var(model.AxS, domain=pyo.NonNegativeIntegers, bounds=(1, len(dxt)))

# =================================================
#   Constraints
# =================================================

def const1(model, a, s, b, r, d, t):
    return model.X[(a, s, b, r, d, t)] == 0

model.const1 = pyo.Constraint(model.SR, model.DxT, rule=const1)

def const2(model, a, s):
    return sum(model.Y[(a, s, b)] for b in model.B) == 1

model.const2 = pyo.Constraint(model.AxS, rule=const2)

def const3(model, b, r, d, t):
    return sum(model.X[(a, s, b, r, d, t)] for a, s in model.AxS) <= 1

model.const3 = pyo.Constraint(model.BxR, model.DxT, rule=const3)

def const4(model, a, s):
    return sum(model.X[(a, s, b, r, d, t)] for d,t in model.DxT for b, r in model.BxR) == model.N[s]

model.const4 = pyo.Constraint(model.AxS, rule=const4)

def const5(model, a, s, d, t):
    return sum(model.X[(a, s, b, r, d, t)] for b, r in model.BxR) <= 1

model.const5 = pyo.Constraint(model.AxS, model.DxT, rule=const5)

def const6(model, a, b):
    return sum(model.X[(a, s, b, r, d, t)] for d,t in model.DxT for r in model.BR[b] for s in model.AS[a]) \
           <= len(model.DxT) * len(model.R) * model.Q[(a, b)]

model.const6 = pyo.Constraint(model.A, model.B, rule=const6)

def const7(model, a, s, b):
    return sum(model.X[(a, s, b, r, d, t)] for d,t in model.DxT for r in model.BR[b]) \
           <= model.N[s] * model.Y[(a, s, b)]

model.const7 = pyo.Constraint(model.AxS, model.B, rule=const7)

def const8(model, a, a_, b):
    return model.V[(a, a_, b)] <= model.Q[(a, b)]

model.const8 = pyo.Constraint(model.A, model.A, model.B, rule=const8)

def const9(model, a, a_, b):
    return model.V[(a, a_, b)] <= model.Q[(a_, b)]

model.const9 = pyo.Constraint(model.A, model.A, model.B, rule=const9)

def const10(model, a, s, b, r):
    return sum(model.X[(a, s, b, r, d, t)] for d,t in model.DxT) <= model.N[s] * model.U[a,s,b,r]

model.const10 = pyo.Constraint(model.AxS, model.BxR, rule=const10)

def const11(model, a, s, d, t):
    return model.FIRST[(a,s)] <= ((model.VAL[(d,t)] * sum(model.X[(a, s, b, r, d, t)] for b,r in model.BxR)) + (pyo.value(model.M) * ( 1 - sum(model.X[(a, s, b, r, d, t)] for b,r in model.BxR))))

model.const11 = pyo.Constraint(model.AxS, model.DxT, rule=const11)

def const12(model, a, s, d, t):
    return model.LAST[(a,s)] >= model.VAL[(d,t)] * sum(model.X[(a, s, b, r, d, t)] for b,r in model.BxR)

model.const12 = pyo.Constraint(model.AxS, model.DxT, rule=const12)

def const13(model):
    return sum([(sum([ model.U[a,s,b,r] for b,r in model.BxR ]) - 1) for a,s in model.AxS]) <= float(warmup["objective"]["value"])

model.const13 = pyo.Constraint(rule=const13)

# =================================================
#   Warmup model
# =================================================

def warmupModel():
    for i in warmup["X"]:
        model.X[(int(i["tuple"][0]), int(i["tuple"][1]), int(i["tuple"][2]), int(i["tuple"][3]), i["tuple"][4], i["tuple"][5])] = int(i["state"])
    for i in warmup["Y"]:
        model.Y[(int(i["tuple"][0]), int(i["tuple"][1]), int(i["tuple"][2]))] = int(i["state"])
    for i in warmup["Q"]:
        model.Q[(int(i["tuple"][0]), int(i["tuple"][1]))] = int(i["state"])
    for i in warmup["U"]:
        model.U[(int(i["tuple"][0]), int(i["tuple"][1]), int(i["tuple"][2]), int(i["tuple"][3]))] = int(i["state"])

warmupModel()

# =================================================
#   Objectives
# =================================================

def objective(model):
    return sum(
        model.LAST[(a,s)] - model.FIRST[(a,s)]
        - model.N[s] + 1 for a,s in model.AxS)

model.objective = pyo.Objective(rule=objective, sense=pyo.minimize)

logging.info("[%s] solve" % datetime.now())

opt = pyo.SolverFactory('cplex')
opt.options['threads'] = maximumThread
opt.options['timelimit'] = 60*15
opt.options['mip tolerances mipgap'] = 0.05

results = opt.solve(model, warmstart=True, keepfiles=True, logfile="obj_4_%d.log" % buildingInput)

logging.info("[%s] save result to %s/cplex/obj_4_%d.log" % (datetime.now(), args.wd, buildingInput))

f = open('%s/cplex/obj_4_%d.log' % (args.wd, buildingInput), "w")
f.write(str(results))
f.close()

logging.info("[%s] export result" % datetime.now())

master = {"buildingId": buildingInput, "objective": { "value": round(pyo.value(model.objective))},
          "X": [], "Y": [], "Q": [], "U": [], "FIRST": [], "LAST": [], "areas": [], "streams": []}

logging.info("[%s] model Y" % datetime.now())

for i in model.Y:
    areaId = int(i[0])
    streamId = int(i[1])
    if areaId not in master["areas"] and round(pyo.value(model.Y[i])) == 1:
        master["areas"].append(areaId)
    if streamId not in master["streams"] and round(pyo.value(model.Y[i])) == 1:
        master["streams"].append(streamId)
    master["Y"].append({"tuple": i, "state": round(pyo.value(model.Y[i]))})

logging.info("[%s] model Q" % datetime.now())

for i in model.Q:
    master["Q"].append({"tuple": i, "state": round(pyo.value(model.Q[i]))})

logging.info("[%s] model U" % datetime.now())

for i in model.U:
    master["U"].append({"tuple": i, "state": round(pyo.value(model.U[i]))})

logging.info("[%s] model FIRST" % datetime.now())

for i in model.FIRST:
    master["FIRST"].append({"tuple": i, "state": round(pyo.value(model.FIRST[i]))})

logging.info("[%s] model LAST" % datetime.now())

for i in model.LAST:
    master["LAST"].append({"tuple": i, "state": round(pyo.value(model.LAST[i]))})

logging.info("[%s] model X" % datetime.now())

for i in model.X:
    master["X"].append({"tuple": i, "state": round(pyo.value(model.X[i]))})

logging.info("[%s] export building result to %s/mip_4_%d.json" % (datetime.now(), args.wd, buildingInput))

with open('%s/mip_4_%d.json' % (args.wd, buildingInput), 'w') as outfile:
    for chunk in json.JSONEncoder().iterencode(master):
        outfile.write(chunk)

logging.info("[%s] stop mip4 (b=%d)" % (datetime.now(), buildingInput))