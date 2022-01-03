import json, numpy, pathlib, logging, argparse
import pyomo.environ as pyo
from datetime import datetime

logging.getLogger().setLevel(logging.INFO)

parser = argparse.ArgumentParser()

parser.add_argument("-rd", "--rd", help='raw data', default="%s\\..\\data\\light.json" % pathlib.Path().resolve(), type=str)
parser.add_argument("-wd", "--wd", help='working directory', default="%s\\output" % pathlib.Path().resolve(), type=str)
parser.add_argument("-mt", "--mt", help='maximum thread', default=4, type=int)
args = parser.parse_args()

maximumThread = int(args.mt)

f = open("%s" % args.rd, "r")
data = json.loads(f.read())
f.close()

model = pyo.ConcreteModel(doc="MIP model[1/5]: Unique buildings to streams and areas")

logging.info("[%s] start mip1" % datetime.now())


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
    return [(a, s) for a in model.A for s in model.AS[a]]


def bXrRule(model):
    return [(b, r) for b in model.B for r in model.BR[b]]


def smallRooms(model):
    out = []
    for s in data["streams"]:
        for r in data["rooms"]:
            if int(r["max"]) < int(s["att"]):
                out.append((s["areaId"], s["id"], r["buildingId"], r["id"]))
    return out


areas = [i["id"] for i in data["areas"]]
streams = [i["id"] for i in data["streams"]]
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
model.ISUM = pyo.Param(default=int(sum([pyo.value(model.I[i]) for i in model.I]) / 2), domain=pyo.NonNegativeIntegers)
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
    return sum(model.X[(a, s, b, r, d, t)] for d, t in model.DxT for b, r in model.BxR) \
           == model.N[s]


model.const4 = pyo.Constraint(model.AxS, rule=const4)


def const5(model, a, s, d, t):
    return sum(model.X[(a, s, b, r, d, t)] for b, r in model.BxR) <= 1


model.const5 = pyo.Constraint(model.AxS, model.DxT, rule=const5)


def const6(model, a, b):
    return sum(model.X[(a, s, b, r, d, t)] for d, t in model.DxT for r in model.BR[b] for s in model.AS[a]) \
           <= len(model.DxT) * len(model.R) * model.Q[(a, b)]


model.const6 = pyo.Constraint(model.A, model.B, rule=const6)


def const7(model, a, s, b):
    return sum(model.X[(a, s, b, r, d, t)] for d, t in model.DxT for r in model.BR[b]) \
           <= model.N[s] * model.Y[(a, s, b)]


model.const7 = pyo.Constraint(model.AxS, model.B, rule=const7)


# =================================================
#   Objectives
# =================================================

def objective(model):
    return sum([
        (sum([
            model.Q[(a, b)]
            for b in model.B
        ]) - 1)
        for a in model.A
    ])


model.objective = pyo.Objective(rule=objective, sense=pyo.minimize)

logging.info("[%s] solve" % datetime.now())

opt = pyo.SolverFactory('cplex')
opt.options['threads'] = maximumThread

results = opt.solve(model, keepfiles=True, logfile="obj_1.log")

logging.info("[%s] save result to %s/cplex/obj_1.log" % (datetime.now(), args.wd))

f = open('%s/cplex/obj_1.log' % args.wd, "w")
f.write(str(results))
f.close()

logging.info("[%s] export result" % datetime.now())

master = {}

out = {"objective": {"value": pyo.value(model.objective)},
       "X": [], "Y": [], "Q": []}

logging.info("[%s] master building" % datetime.now())

for i in model.B:
    master[i] = {"buildingId": int(i), "objective": {"value": round(pyo.value(model.objective))},
                 "X": [], "Y": [], "Q": [], "areas": [], "streams": []}

logging.info("[%s] model Y" % datetime.now())

for i in model.Y:
    out["Y"].append({"tuple": i, "state": round(pyo.value(model.Y[i]))})
    areaId = int(i[0])
    streamId = int(i[1])
    buildingId = int(i[2])
    if areaId not in master[buildingId]["areas"] and round(pyo.value(model.Y[i])) == 1:
        master[buildingId]["areas"].append(areaId)
    if streamId not in master[buildingId]["streams"] and round(pyo.value(model.Y[i])) == 1:
        master[buildingId]["streams"].append(streamId)
    if areaId in master[buildingId]["areas"]:
        master[buildingId]["Y"].append({"tuple": i, "state": round(pyo.value(model.Y[i]))})

logging.info("[%s] model Q" % datetime.now())

for i in model.Q:
    areaId = int(i[0])
    buildingId = int(i[1])
    out["Q"].append({"tuple": i, "state": round(pyo.value(model.Q[i]))})
    if areaId in master[buildingId]["areas"]:
        master[buildingId]["Q"].append({"tuple": i, "state": round(pyo.value(model.Q[i]))})

logging.info("[%s] model X" % (datetime.now()))

for i in model.X:
    areaId = int(i[0])
    streamId = int(i[1])
    buildingId = int(i[2])
    out["X"].append({"tuple": i, "state": round(pyo.value(model.X[i]))})
    if areaId in master[buildingId]["areas"] and streamId in master[buildingId]["streams"]:
        master[buildingId]["X"].append({"tuple": i, "state": round(pyo.value(model.X[i]))})

logging.info("[%s] export complete result to %s/mip_1.json" % (datetime.now(), args.wd))

with open('%s/mip_1.json' % args.wd, 'w') as outfile:
    for chunk in json.JSONEncoder().iterencode(out):
        outfile.write(chunk)

for i in model.B:
    if len(master[i]["streams"]) > 0:
        logging.info(
            "[%s] export building result to %s/mip_1_%d.json" % (datetime.now(), args.wd, int(master[i]["buildingId"])))
        with open('%s/mip_1_%d.json' % (args.wd, int(master[i]["buildingId"])), 'w') as outfile:
            for chunk in json.JSONEncoder().iterencode(master[i]):
                outfile.write(chunk)

logging.info("[%s] stop mip1" % (datetime.now()))
