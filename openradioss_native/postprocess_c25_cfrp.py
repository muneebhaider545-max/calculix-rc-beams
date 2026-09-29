#!/usr/bin/env python3
import csv, os, math

fn='C25_CFRP_NATIVET01.csv'
if not os.path.exists(fn):
    raise SystemExit("CSV not found")

with open(fn,newline='') as f:
    rows=list(csv.reader(f))
hdr=rows[0]
load_cols=[(i,h) for i,h in enumerate(hdr) if 'Load line nodes' in h]
print('LOAD_HISTORY_COLUMNS')
for i,h in load_cols:
    print(i,h)

numeric=[]
for row in rows[1:]:
    try:
        vals=[float(x) for x in row]
    except Exception:
        continue
    numeric.append(vals)

if len(load_cols) < 6:
    raise SystemExit("Expected 6 load-history columns (DZ and REACZ for 3 nodes), got %d" % len(load_cols))

idx=[i for i,h in load_cols]
dz_idx=idx[0::2][:3]
rz_idx=idx[1::2][:3]

out=[]
for vals in numeric:
    t=vals[0]
    dz=sum(vals[i] for i in dz_idx)/len(dz_idx)
    reac=sum(vals[i] for i in rz_idx)
    out.append((t,dz,reac,abs(reac)/1000.0))

with open('C25_CFRP_load_deflection.csv','w',newline='') as f:
    w=csv.writer(f)
    w.writerow(['time_s','midspan_DZ_mm','sum_REACZ_N','load_kN'])
    w.writerows(out)

peak=max(out,key=lambda r:r[3])

iei=hdr.index('INTERNAL ENERGY') if 'INTERNAL ENERGY' in hdr else None
kei=hdr.index('KINETIC ENERGY') if 'KINETIC ENERGY' in hdr else None
ratios=[]
if iei is not None and kei is not None:
    for vals in numeric:
        ie=abs(vals[iei]); ke=abs(vals[kei])
        if ie>1e-12:
            ratios.append(ke/ie)
ratio_max=max(ratios) if ratios else float('nan')

with open('C25_CFRP_solver_summary.txt','w') as f:
    f.write('GENUINE OPENRADIOSS 3D SOLVER RESULT\n')
    f.write('Peak reaction load = %.6f kN\n' % peak[3])
    f.write('Midspan displacement at peak = %.6f mm\n' % peak[1])
    f.write('Peak time = %.6f s\n' % peak[0])
    f.write('Experimental Pu = 99.5 kN\n')
    f.write('Experimental delta_u = 20.058 mm\n')
    f.write('Peak-load error = %.3f %%\n' % ((peak[3]-99.5)/99.5*100.0))
    f.write('Max KE/IE ratio = %.6f\n' % ratio_max)

print(open('C25_CFRP_solver_summary.txt').read())
