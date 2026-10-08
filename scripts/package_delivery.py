"""Create a portable submission archive without machine-specific dependencies."""
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'Association-Lab-Faculty-Edition.zip'
exclude={'.venv','node_modules','__pycache__','.pytest_cache','tmp','.git','.codex','.agents'}
files=[p for p in ROOT.rglob('*') if p.is_file() and not exclude.intersection(p.relative_to(ROOT).parts) and p!=OUT and p.suffix not in {'.log','.pyc','.new','.zip'}]
with ZipFile(OUT,'w',ZIP_DEFLATED) as archive:
    for p in sorted(files): archive.write(p,Path('DMDW6')/p.relative_to(ROOT))
with ZipFile(OUT) as archive:
    assert archive.testzip() is None
    print(f'Archive verified: {len(archive.namelist())} files, {OUT.stat().st_size:,} bytes')
print(OUT)
