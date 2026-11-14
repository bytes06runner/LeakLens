"""Compile paper/leaklens_paper.tex with TeX Live from Ubuntu's packages (pdflatex, two passes)."""

import glob
import os
import shutil
import subprocess
import zipfile

code_dir = os.path.dirname(glob.glob("/kaggle/input/**/CODE_VERSION.json", recursive=True)[0])
hits = glob.glob("/kaggle/input/**/paper/leaklens_paper.tex", recursive=True)
if hits:
    shutil.copytree(os.path.dirname(hits[0]), "/tmp/paper")
else:
    with zipfile.ZipFile(os.path.join(code_dir, "paper.zip")) as z:
        z.extractall("/tmp")
log = []
p = subprocess.run("apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq texlive-latex-base "
                   "texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended texlive-pictures "
                   "texlive-science lmodern", shell=True, capture_output=True, text=True)
log.append(f"apt rc={p.returncode}\n{p.stderr[-2000:]}")
for i in range(2):
    p = subprocess.run(["pdflatex", "-interaction=nonstopmode", "leaklens_paper.tex"], cwd="/tmp/paper",
                       capture_output=True, text=True)
    log.append(f"pass {i + 1} rc={p.returncode}")
for f in ("leaklens_paper.pdf", "leaklens_paper.log"):
    if os.path.exists(f"/tmp/paper/{f}"):
        shutil.copy(f"/tmp/paper/{f}", "/kaggle/working/")
open("/kaggle/working/build_log.txt", "w").write("\n".join(log))
print("\n".join(log))
