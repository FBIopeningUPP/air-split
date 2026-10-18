"""Re-import every STEP file and confirm it is a valid solid whose volume matches the STL."""
import os, trimesh
from OCP.STEPControl import STEPControl_Reader
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.GProp import GProp_GProps
from OCP.BRepGProp import BRepGProp
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
bad = 0
for f in sorted(os.listdir(os.path.join(OUT, "step"))):
    r = STEPControl_Reader(); r.ReadFile(os.path.join(OUT, "step", f)); r.TransferRoots(); s = r.OneShape()
    p = GProp_GProps(); BRepGProp.VolumeProperties_s(s, p)
    stl = trimesh.load(os.path.join(OUT, "stl", f.replace(".step", ".stl")))
    ok = BRepCheck_Analyzer(s).IsValid() and abs(p.Mass() - stl.volume) / stl.volume < 0.002
    bad += not ok
    print(f"{f:22s} valid={ok}  STEP {p.Mass()/1000:6.2f} cm3  STL {stl.volume/1000:6.2f} cm3")
print("STEP files failing:", bad)
