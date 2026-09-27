#!/usr/bin/env python3
"""Check that old and new EDM4hep files retain LHE weights and names."""

import argparse
import gzip
import json
import math
import re
from pathlib import Path

import ROOT

ROOT.gErrorIgnoreLevel = ROOT.kError


def lhe_weights(path, count):
    opener = gzip.open if Path(path).suffix == ".gz" else open
    result, event = [], None
    with opener(path, "rt") as source:
        for line in source:
            if line.strip() == "<event>":
                event = []
            elif line.strip() == "</event>" and event is not None:
                values = re.findall(r"<wgt id=['\"]rwgt_\d+['\"]>\s*([^<]+)</wgt>",
                                    "".join(event))
                result.append([float(value) for value in values])
                if len(result) == count:
                    break
                event = None
            elif event is not None:
                event.append(line)
    if len(result) != count or any(len(weights) != 9 for weights in result):
        raise ValueError(f"{path}: expected {count} LHE events with nine weights each")
    return result


def inspect(path, lhe=None):
    source = ROOT.TFile.Open(path)
    if not source or source.IsZombie():
        raise ValueError(f"Cannot open {path}")
    events = source.Get("events")
    if not events or not events.GetBranch("_EventHeader_weights"):
        raise ValueError(f"{path}: no EventHeader weight branch")
    count = events.GetEntries()
    if count != 10:
        raise ValueError(f"{path}: expected ten reconstructed events, found {count}")
    expected_weights = lhe_weights(lhe, count) if lhe else None
    for index in range(count):
        events.GetEntry(index)
        weights = events._EventHeader_weights
        if len(weights) != 9 or not all(math.isfinite(value) for value in weights):
            raise ValueError(f"{path}: event {index} has invalid HHH weights")
        if expected_weights is not None and any(
            not math.isclose(value, original, rel_tol=1e-5, abs_tol=1e-12)
            for value, original in zip(weights, expected_weights[index])
        ):
            raise ValueError(f"{path}: event {index} weights differ from LHE")
        if index == 0:
            keys = [key.decode() if isinstance(key, bytes) else str(key)
                    for key in events.GPStringKeys]
            if "EventWeightNames" not in keys:
                raise ValueError(f"{path}: no EventWeightNames metadata")
            names = [str(name) for name in events.GPStringValues[keys.index("EventWeightNames")]]
            if names != [f"rwgt_{number}" for number in range(1, 10)]:
                raise ValueError(f"{path}: incorrect weight names: {names}")
    source.Close()
    return {"file": path, "events": count,
            "weight_branch": "_EventHeader_weights", "weights_per_event": 9,
            "weight_names": names, "weights_match_lhe": lhe is not None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("old_root")
    parser.add_argument("new_root")
    parser.add_argument("--old-lhe")
    parser.add_argument("--new-lhe")
    args = parser.parse_args()
    print(json.dumps({"old": inspect(args.old_root, args.old_lhe),
                      "new": inspect(args.new_root, args.new_lhe)}, indent=2))
