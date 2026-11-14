#!/bin/sh
# Regenerate and compile the IEEE version; prints page count and layout warnings.
set -e
cd "$(dirname "$0")"
python3 make_ieee.py >/dev/null
"${TECTONIC:-tectonic}" -X compile --keep-logs leaklens_ieee.tex 2>&1 | grep -i "error\|Overfull\|Font Warning" | sort -u || true
python3 -c "import re;s=open('leaklens_ieee.log').read();print('pages', re.findall(r'Output written.*?\((\d+) page',s))"
