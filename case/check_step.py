"""Re-import every STEP file and confirm it is a valid solid whose shape matches the STL.

The STEP is meshed after import and its mesh volume compared with the STL: that is what a CAD program shows. (OpenCascade's
own volume integral is not used, as it misreads some faces of the chamfered key covers.)"""
import os, tempfile, trimesh
from OCP.STEPControl import STEPControl_Reader
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "out")
bad = 0
tmp = os.path.join(tempfile.gettempdir(), "air75_step_check.stl")
for f in sorted(os.listdir(os.path.join(OUT, "step"))):
    r = STEPControl_Reader(); r.ReadFile(os.path.join(OUT, "step", f)); r.TransferRoots(); s = r.OneShape()
    BRepMesh_IncrementalMesh(s, 0.01, False, 0.15, True)
    StlAPI_Writer().Write(s, tmp)
    sm = trimesh.load(tmp)
    stl = trimesh.load(os.path.join(OUT, "stl", f.replace(".step", ".stl")))
    ok = BRepCheck_Analyzer(s).IsValid() and sm.is_watertight and abs(sm.volume - stl.volume) / stl.volume < 0.002
    bad += not ok
    print(f"{f:22s} valid={ok}  STEP {sm.volume/1000:6.2f} cm3  STL {stl.volume/1000:6.2f} cm3")
print("STEP files failing:", bad)
