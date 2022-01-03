import os, json, pathlib

try:
    path = os.getcwd()

    f = open("%s\\..\\data\\light.json" % pathlib.Path().resolve(), "r")
    data = json.loads(f.read())
    f.close()

    def permutation(prmnt, max):
        return 0 if prmnt + 1 >= max else (prmnt + 1)

    out = []
    data["streams"].sort(key=lambda x: (x.get('att'), x.get('sessions')), reverse=True)
    streams = data["streams"]
    data["rooms"].sort(key=lambda x: x.get('max'), reverse=True)
    rooms = data["rooms"]
    dxt = data["daysXtimeslots"]
    buildings = data["buildings"]

    slotsUsed = []
    for building in data["buildings"]:
        out.append({"id": building["id"], "slots": []})
        slotsUsed.append(0)

    for room in rooms:
        for ts in dxt:
            out[(room["buildingId"] - 1)]["slots"].append({
                "roomId": room["id"],
                "time": "%s%s" % (ts["day"], ts["timeslot"]),
                "stream": None,
                "sessionNo": None,
                "max": room["max"],
                "att": None,
                "areaId": None
            })

    prmnt = 1
    for stream in streams:
        maxTry = len(buildings)
        while 0 < maxTry:
            cpos = slotsUsed[prmnt] + stream["sessions"] - 1
            if len(out[prmnt]["slots"]) - slotsUsed[prmnt]\
                    - stream["sessions"] < 0:
                prmnt = permutation(prmnt, len(buildings))
            elif out[prmnt]["slots"][cpos]["max"] < stream['att']:
                prmnt = permutation(prmnt, len(buildings))
            else:
                break
            maxTry -= 1

        if maxTry == 0:
            raise Exception("Le stream %d ne peut pas être alloué" % stream["id"])

        for i in range(stream["sessions"]):
            out[prmnt]["slots"][slotsUsed[prmnt]]["stream"] \
                = stream["id"]
            out[prmnt]["slots"][slotsUsed[prmnt]]["att"] \
                = stream["att"]
            out[prmnt]["slots"][slotsUsed[prmnt]]["areaId"] \
                = stream["areaId"]
            out[prmnt]["slots"][slotsUsed[prmnt]]["sessionNo"] \
                = i + 1
            slotsUsed[prmnt] += 1
        prmnt = permutation(prmnt, len(buildings))

    print("La solution est réalisable")

    areasMatrix = []
    for area in data["areasMatrix"]:
        areasMatrix.append({"a": area[0], "a_": area[1], "ok": False})
        areasMatrix.append({"a": area[1], "a_": area[0], "ok": False})

    for building in out:
        for slot in building["slots"]:
            for slots_ in building["slots"]:
                for aXa in areasMatrix:
                    if aXa["a"] == slot["areaId"] and aXa["a_"] == slots_["areaId"]:
                        aXa["ok"] = True

    for aXa in areasMatrix:
        if not aXa["ok"]:
            print("La colocalisation des areas %d et %d n'as pas été validée" % (aXa["a"], aXa["a_"]))

    result = {}
    for building in buildings:
        result[building["id"]] = {"buildingId": building["id"],"X": []}

    for building in out:
        for slot in building["slots"]:
            if slot["stream"] is None: continue
            result[building['id']]["X"].append({"tuple": (int(slot["areaId"]), int(slot["stream"]), int(building['id']), int(slot["roomId"]), slot["time"][:1], slot["time"][1:]), "state": 1.0})

    for building in buildings:
        with open('output/result_%s.json' % (int(building['id'])), 'w') as outfile:
            json.dump(result[int(building['id'])], outfile)
        os.system("python \"%s\\..\\pyomo\\visualizer.py\" "
                  "-rd \"%s\\..\\data\\light.json\" "
                  "-d \"%s\\output\\result_%d.json\"" %(pathlib.Path().resolve(),pathlib.Path().resolve(),pathlib.Path().resolve(), int(building['id'])))

except Exception as e:
    print(e)
