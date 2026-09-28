from __future__ import print_function
import sys, os, csv
from odbAccess import openOdb

if len(sys.argv) < 2:
    raise SystemExit("Usage: abaqus python extract_odb_results.py job.odb")

odb_path = sys.argv[-1]
odb = openOdb(path=odb_path, readOnly=True)

step = odb.steps['FLEXURE']
asm = odb.rootAssembly

# Abaqus may uppercase set names
def get_nset(name):
    for k,v in asm.nodeSets.items():
        if k.upper() == name.upper():
            return v
    raise KeyError("Node set not found: "+name)

load_set = get_nset('RP_LOAD') if any(k.upper()=='RP_LOAD' for k in asm.nodeSets) else get_nset('LOAD_LINE')

rows = []
peak_load = -1.0
peak_disp = None

for frame in step.frames:
    disp = frame.fieldOutputs['U'].getSubset(region=load_set)
    rf = frame.fieldOutputs['RF'].getSubset(region=load_set)
    if not disp.values or not rf.values:
        continue
    # If RP_LOAD exists this is one value; if LOAD_LINE, sum reactions and average U3.
    u3 = sum(v.data[2] for v in disp.values)/float(len(disp.values))
    rf3 = sum(v.data[2] for v in rf.values)
    load_kn = abs(rf3)/1000.0
    rows.append((frame.frameValue, u3, rf3, load_kn))
    if load_kn > peak_load:
        peak_load = load_kn
        peak_disp = abs(u3)

base = os.path.splitext(os.path.basename(odb_path))[0]
csv_path = base + "_history.csv"
with open(csv_path, "w") as f:
    w = csv.writer(f)
    w.writerow(["step_time","U3_mm","RF3_N","load_kN"])
    for r in rows:
        w.writerow(r)

# Final-frame field maxima
final = step.frames[-1]
summary = []
summary.append("ODB: %s" % odb_path)
summary.append("Frames: %d" % len(step.frames))
summary.append("Peak reaction load: %.6f kN" % peak_load)
summary.append("Displacement at peak reaction: %.6f mm" % peak_disp)

for field_name in ['DAMAGET','DAMAGEC','S']:
    if field_name in final.fieldOutputs:
        vals = final.fieldOutputs[field_name].values
        if field_name in ('DAMAGET','DAMAGEC'):
            m = max(float(v.data) for v in vals) if vals else float('nan')
            summary.append("Final max %s: %.6f" % (field_name,m))
        elif field_name == 'S' and vals:
            mises=[getattr(v,'mises',None) for v in vals]
            mises=[x for x in mises if x is not None]
            if mises:
                summary.append("Final max Mises stress: %.6f MPa" % max(mises))

# Contact damage may be unavailable until damage activates.
if 'CSDMG' in final.fieldOutputs:
    vals=final.fieldOutputs['CSDMG'].values
    if vals:
        summary.append("Final max CSDMG: %.6f" % max(float(v.data) for v in vals))

summary_path = base + "_summary.txt"
with open(summary_path,"w") as f:
    f.write("\n".join(summary)+"\n")

print("\n".join(summary))
odb.close()
