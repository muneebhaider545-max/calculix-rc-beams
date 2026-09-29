#!/usr/bin/env python3
import csv, glob, math, os
fn=glob.glob('C25_CFRP_COHESIVET01.csv')
if not fn:
    print('No cohesive CSV time-history found')
    raise SystemExit(0)
with open(fn[0],newline='') as f:
    rows=list(csv.reader(f))
h=rows[0]; num=[]
for r in rows[1:]:
    try:num.append([float(x) for x in r])
    except:pass
cols=[i for i,x in enumerate(h) if 'Load line nodes' in x]
if len(cols)<6 or not num:
    print('Insufficient load-line history columns')
    raise SystemExit(0)
dz=cols[0::2][:3]; rz=cols[1::2][:3]
data=[]
for v in num:
    d=sum(v[i] for i in dz)/3.0
    R=sum(v[i] for i in rz)
    data.append((v[0],d,abs(R)/1000.0))
peak=max(data,key=lambda q:q[2])
iei=h.index('INTERNAL ENERGY') if 'INTERNAL ENERGY' in h else None
kei=h.index('KINETIC ENERGY') if 'KINETIC ENERGY' in h else None
ratios=[]
if iei is not None and kei is not None:
    for v in num:
        if abs(v[iei])>1e-12:
            ratios.append(abs(v[kei])/abs(v[iei]))
with open('C25_CFRP_COHESIVE_load_deflection.csv','w',newline='') as f:
    w=csv.writer(f); w.writerow(['time_s','midspan_DZ_mm','load_kN']); w.writerows(data)
with open('cohesive_solver_summary.txt','w') as f:
    f.write(f'Peak reaction load = {peak[2]:.6f} kN\n')
    f.write(f'Displacement at peak = {peak[1]:.6f} mm\n')
    f.write(f'Peak time = {peak[0]:.6f} s\n')
    f.write(f'Peak load error vs 99.5 kN = {(peak[2]-99.5)/99.5*100:.3f}%\n')
    f.write(f'Max KE/IE = {max(ratios) if ratios else float("nan"):.6f}\n')
print(open('cohesive_solver_summary.txt').read())
