#!/usr/bin/env python3
"""Simulate postal assignment logic without Django DB.
Checks Berlin mapping file and german-postcodes.csv and prints what would be assigned.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BERLIN = ROOT / 'data' / 'berlin_postal_codes.csv'
GERMAN = ROOT / 'data' / 'german-postcodes.csv'

def find_berlin(code):
    if not BERLIN.exists():
        return None
    with BERLIN.open(encoding='utf-8', newline='') as f:
        r=csv.DictReader(f)
        for row in r:
            if row.get('postal_code','').strip()==code:
                return row.get('bezirk_name')
    return None

def find_bundesland(code):
    if not GERMAN.exists():
        return None
    with GERMAN.open(encoding='utf-8', newline='') as f:
        r=csv.DictReader(f)
        for row in r:
            if row.get('Plz','').strip()==code:
                return row.get('Bundesland')
    return None

if __name__=='__main__':
    samples=['10115','13053','01067','80331','20095']
    for s in samples:
        b=find_berlin(s)
        if b:
            print(f"{s} -> Berlin Bezirk: {b}")
        else:
            bl=find_bundesland(s)
            print(f"{s} -> Bundesland: {bl}")
