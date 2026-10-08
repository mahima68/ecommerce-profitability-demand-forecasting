"""Download the official public dataset without manually handling the ZIP."""
from pathlib import Path
from urllib.request import urlopen, Request
from zipfile import ZipFile
import tempfile
import shutil
import json
from ecommerce.data import ROOT, sha256

URL = 'https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip'
target = ROOT / 'data/raw/online_retail_II.xlsx'
target.parent.mkdir(exist_ok=True, parents=True)
if target.exists():
    print('Dataset already exists. Delete it explicitly if you want to download a fresh copy.')
else:
    with tempfile.TemporaryDirectory() as temp:
        archive = Path(temp) / 'data.zip'
        with urlopen(Request(URL, headers={'User-Agent': 'RetailPortfolio/1.0'}), timeout=120) as response:
            with archive.open('wb') as f:
                shutil.copyfileobj(response, f)
        with ZipFile(archive) as z:
            # Extract only the known workbook, not arbitrary paths in a ZIP.
            with z.open('online_retail_II.xlsx') as source, target.open('wb') as dest:
                shutil.copyfileobj(source, dest)
    print(f'Downloaded {target.name}.')
(target.parent / 'source_manifest.json').write_text(json.dumps({'url': URL, 'sha256': sha256(target)}, indent=2))
