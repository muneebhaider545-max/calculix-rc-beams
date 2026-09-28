# fast-route validation workflow
import os, sys, math, re, csv, subprocess, pathlib, json

L_TOTAL = 1219.2
X_LEFT = 76.2
X_RIGHT = 1143.0
SPAN = X_RIGHT - X_LEFT
B = 101.6
H = 203.2
I = B*H**3/12.0
N_ELEMS = 48
DX = L_TOTAL/N_ELEMS

specimens = {
"C18-CONT": {"Pu":32.5, "d":11.686, "fc":19.55, "system":"Control"},
"C18-ST": {"Pu":40.0, "d":13.082, "fc":19.55, "system":"Steel"},
"C18-GFRP": {"Pu":54.5, "d":9.220, "fc":19.55, "system":"GFRP"},
"C18-CFRP": {"Pu":49.0, "d":6.368, "fc":19.55, "system":"CFRP"},
"C21-CONT": {"Pu":39.5, "d":9.364, "fc":26.90, "system":"Control"},
"C21-ST": {"Pu":50.0, "d":5.130, "fc":26.90, "system":"Steel"},
"C21-GFRP": {"Pu":66.0, "d":7.245, "fc":26.90, "system":"GFRP"},
"C21-CFRP": {"Pu":73.0, "d":9.756, "fc":26.90, "system":"CFRP"},
"C25-CONT": {"Pu":54.5, "d":9.290, "fc":28.70, "system":"Control"},
"C25-ST": {"Pu":62.5, "d":15.012, "fc":28.70, "system":"Steel"},
"C25-GFRP": {"Pu":85.5, "d":4.5733, "fc":28.70, "system":"GFRP"},
"C25-CFRP": {"Pu":99.5, "d":20.058, "fc":28.70, "system":"CFRP"},
}

def equivalent_E(P_kN, delta_mm):
    # Peak-state secant equivalent modulus for the tested simply supported span.
    P = P_kN*1000.0
    return 1.08633945*P*SPAN**3/(48.0*I*delta_mm)  # B31 shear-deformation correction calibrated once for this geometry

def write_deck(name, data, n_elems=N_ELEMS, outdir="models"):
    os.makedirs(outdir, exist_ok=True)
    # n_elems must be divisible by 16 so 3-in supports and midspan are nodes.
    dx=L_TOTAL/n_elems
    nodes=[(i+1,i*dx,0.0,0.0) for i in range(n_elems+1)]
    left_id=round(X_LEFT/dx)+1
    mid_id=round((L_TOTAL/2)/dx)+1
    right_id=round(X_RIGHT/dx)+1
    E=equivalent_E(data["Pu"],data["d"])
    path=os.path.join(outdir,name+".inp")
    with open(path,"w") as f:
        f.write("*HEADING\n")
        f.write(f"Peak-state equivalent CalculiX beam model: {name}\n")
        f.write("** Geometry mm, force N, stress MPa\n")
        f.write("*NODE\n")
        for nid,x,y,z in nodes:
            f.write(f"{nid},{x:.6f},{y:.6f},{z:.6f}\n")
        f.write("*ELEMENT,TYPE=B31,ELSET=EALL\n")
        for e in range(1,n_elems+1):
            f.write(f"{e},{e},{e+1}\n")
        f.write("*NSET,NSET=LEFT\n%d\n"%left_id)
        f.write("*NSET,NSET=RIGHT\n%d\n"%right_id)
        f.write("*NSET,NSET=MID\n%d\n"%mid_id)
        f.write("*NSET,NSET=SUPPORTS\n%d,%d\n"%(left_id,right_id))
        f.write("*MATERIAL,NAME=EQMAT\n")
        f.write("*ELASTIC\n")
        f.write(f"{E:.8f},0.20\n")
        f.write("*BEAM SECTION,ELSET=EALL,MATERIAL=EQMAT,SECTION=RECT\n")
        f.write(f"{H:.6f},{B:.6f}\n")
        f.write("0.,0.,1.\n")
        f.write("*BOUNDARY\n")
        # left pin: translations fixed; right roller: vertical/lateral fixed
        f.write("LEFT,1,3,0.\n")
        f.write("RIGHT,2,3,0.\n")
        # suppress rigid torsional rotation at left only
        f.write("LEFT,4,4,0.\n")
        f.write("*STEP\n")
        f.write("*STATIC\n")
        f.write("1.,1.\n")
        f.write("*CLOAD\n")
        f.write(f"MID,3,{-data['Pu']*1000.0:.6f}\n")
        f.write("*NODE PRINT,NSET=MID\n")
        f.write("U\n")
        f.write("*NODE PRINT,NSET=SUPPORTS\n")
        f.write("RF\n")
        f.write("*EL PRINT,ELSET=EALL\n")
        f.write("S\n")
        f.write("*NODE FILE,NSET=MID\n")
        f.write("U\n")
        f.write("*EL FILE,ELSET=EALL\n")
        f.write("S\n")
        f.write("*END STEP\n")
    return path,E,left_id,mid_id,right_id

def run_ccx(ccx, inp):
    stem=os.path.splitext(os.path.basename(inp))[0]
    cwd=os.path.dirname(inp) or "."
    proc=subprocess.run([ccx,stem],cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    open(os.path.join(cwd,stem+".log"),"w").write(proc.stdout)
    return proc.returncode, proc.stdout

def parse_mid_u3(dat_path, mid_id):
    if not os.path.exists(dat_path):
        return None
    lines=open(dat_path,errors="ignore").read().splitlines()
    # Search all rows starting with node id; for U print row columns are node,U1,U2,U3
    vals=[]
    patt=re.compile(r"^\s*"+str(mid_id)+r"\s+([-+0-9.Ee]+)\s+([-+0-9.Ee]+)\s+([-+0-9.Ee]+)")
    for line in lines:
        m=patt.match(line)
        if m:
            try:
                nums=[float(m.group(i)) for i in range(1,4)]
                vals.append(nums[2])
            except: pass
    if vals:
        # displacement entry has magnitude in mm; reaction blocks can also match but U3 at mid is largest negative displacement.
        return min(vals, key=lambda x:x)
    return None

def mesh_study(ccx):
    base=specimens["C25-CFRP"]
    rows=[]
    for ne in [16,32,48,96]:
        ddir=f"mesh_{ne}"
        inp,E,l,m,r=write_deck("C25-CFRP-MESH",base,ne,ddir)
        code,out=run_ccx(ccx,inp)
        u=parse_mid_u3(os.path.join(ddir,"C25-CFRP-MESH.dat"),m)
        rows.append({"elements":ne,"Eeq_MPa":E,"u3_mm":u,"returncode":code})
    return rows

def main():
    if len(sys.argv)<2:
        print("usage: python run_models.py /path/to/ccx")
        return 2
    ccx=os.path.abspath(sys.argv[1])
    os.makedirs("models",exist_ok=True)
    results=[]
    for name,data in specimens.items():
        inp,E,left,mid,right=write_deck(name,data)
        code,out=run_ccx(ccx,inp)
        dat=os.path.join("models",name+".dat")
        u=parse_mid_u3(dat,mid)
        dnum=abs(u) if u is not None else None
        err=(100.0*(dnum-data["d"])/data["d"]) if dnum is not None else None
        results.append({
            "Specimen":name,"System":data["system"],"fc_MPa":data["fc"],
            "Pu_exp_kN":data["Pu"],"delta_exp_mm":data["d"],
            "Eeq_peak_MPa":E,"delta_ccx_mm":dnum,
            "delta_error_pct":err,"ccx_returncode":code
        })
    with open("calculix_results.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=results[0].keys()); w.writeheader(); w.writerows(results)
    ms=mesh_study(ccx)
    with open("mesh_convergence.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=ms[0].keys()); w.writeheader(); w.writerows(ms)
    json.dump({"span_mm":SPAN,"total_length_mm":L_TOTAL,"width_mm":B,"depth_mm":H,
               "model_type":"B31 peak-state secant-equivalent elastic beam",
               "note":"Eeq calibrated from experimental Pu and peak deflection; this is a solver cross-check, not independent nonlinear prediction."},
              open("model_metadata.json","w"),indent=2)
    print(open("calculix_results.csv").read())
    print(open("mesh_convergence.csv").read())
    return 0

if __name__=="__main__":
    raise SystemExit(main())
