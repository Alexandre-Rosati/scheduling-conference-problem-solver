import json, argparse, pathlib

parser = argparse.ArgumentParser()

parser.add_argument("-rd", "--rd", help='raw data', default="%s\\..\\data\\light.json" % pathlib.Path().resolve(), type=str)
parser.add_argument("-d", "--d", help='result of mip', default="%s\\..\\pyomo\\output\\mip_3_1.json" % pathlib.Path().resolve(), type=str)
args = parser.parse_args()

f = open("%s" % args.rd, "r")
data = json.loads(f.read())
f.close()

print(args.d)

f = open("%s" % args.d, "r")
result = json.loads(f.read())
f.close()

out = {}
for x in data["daysXtimeslots"]:
    out[(x["day"], x["timeslot"])] = {}
    for r in data["rooms"]:
        if int(r["buildingId"]) != int(result["buildingId"]): continue
        out[(x["day"], x["timeslot"])][int(r["id"])] = None

for x in result["X"]:
    if int(x["state"]) == 0: continue
    out[(x["tuple"][4], x["tuple"][5])][(int(x["tuple"][3]))] = (int(x["tuple"][0]), int(x["tuple"][1]))

print("-------", end ="")
for r in data["rooms"]:
    if int(r["buildingId"]) != int(result["buildingId"]): continue
    print(" |  room %2d " % r["id"], end ="")
print(" |")
for x in data["daysXtimeslots"]:
    print(" %s - %s " % (x["day"], x["timeslot"]), end ="")
    for r in data["rooms"]:
        if int(r["buildingId"]) != int(result["buildingId"]): continue
        if out[(x["day"], x["timeslot"])][int(r["id"])] is None:
            print(" |   empty  ", end ="")
        else:
            print(" | A%3d S%3d" % (int(out[(x["day"], x["timeslot"])][int(r["id"])][0]), int(out[(x["day"], x["timeslot"])][int(r["id"])][1])), end ="")
    print(" |")