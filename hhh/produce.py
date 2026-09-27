#!/usr/bin/env python3
"""Local, reproducible gg -> hhh -> 4b2tau LHE and Delphes production."""

import argparse
import gzip
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path


CARDS = Path(__file__).resolve().parent / "cards"
DEFAULT_DELPHES = Path(os.environ.get(
    "HHH_DELPHES_BINARY",
    "/data/atlas02/users/dingleyt/FCChh/key4/k4SimDelphes/build2/standalone/DelphesPythia8_EDM4HEP",
))
WEIGHT_POINTS = [
    (-1.0, -1.0), (0.0, -2.0), (-2.0, 0.0),
    (0.0, -1.0), (-1.0, 0.0), (-2.0, -1.0),
    (-1.0, -2.0), (-0.5, -1.0), (-1.5, -1.0),
]


def run(command, cwd):
    print("Running:", " ".join(map(str, command)), flush=True)
    subprocess.run([str(item) for item in command], cwd=cwd, check=True)


def unpack_model(archive, destination):
    with tarfile.open(archive) as source:
        members = source.getmembers()
        for member in members:
            target = (destination / member.name).resolve()
            if not target.is_relative_to(destination.resolve()) or member.issym() or member.islnk():
                raise ValueError(f"Unsafe model archive entry: {member.name}")
        source.extractall(destination)
    model = destination / "mg5/models/loop_sm_c3d4"
    if not (model / "particles.py").is_file():
        raise FileNotFoundError(f"Missing model files in {archive}")
    return model


def generate_lhe(args):
    if args.seed <= 0 or args.events <= 0:
        raise ValueError("Seed and event count must be positive")
    mg5 = args.mg5_root.resolve() / "bin/mg5_aMC"
    if not mg5.is_file():
        raise FileNotFoundError(mg5)
    lhapdf = args.lhapdf_config.resolve()
    if not lhapdf.is_file():
        raise FileNotFoundError(lhapdf)
    workdir = args.workdir.resolve()
    output = args.outdir.resolve() / f"events_{args.seed:09d}.lhe.gz"
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    workdir.mkdir(parents=True, exist_ok=True)
    process = workdir / "hhh_process"
    if process.exists():
        raise FileExistsError(f"Refusing to overwrite {process}; use a fresh workdir")

    model = unpack_model(CARDS / "loop_sm_c3d4.tar", workdir)
    template = (CARDS / "mg_pp_hhh_84TeV.mg5").read_text()
    process_card, launch_card = template.split("######## DELIMITER", 1)
    # The card archive contains mg5/models/...; import its extracted model by path.
    process_card = process_card.replace("import model loop_sm_c3d4", f"import model {model}")
    process_card = process_card.replace("output DUMMYPROCESS", f"output {process}")
    launch_card = launch_card.split("\n", 1)[1]
    launch_card = launch_card.replace("launch DUMMYPROCESS", f"launch {process}")
    launch_card = re.sub(r"^set lhapdf .*$", f"set lhapdf {lhapdf}", launch_card, flags=re.MULTILINE)
    launch_card = launch_card.replace("DUMMYSEED", str(args.seed)).replace("DUMMYNEVENTS", str(args.events))
    (workdir / "process.mg5").write_text(process_card)
    (workdir / "launch.mg5").write_text(launch_card)

    run([mg5, "process.mg5"], workdir)
    if not (process / "Cards").is_dir():
        raise RuntimeError("MG5 did not create the process directory; check its output above")
    shutil.copy2(CARDS / "reweight_card.dat", process / "Cards/reweight_card.dat")
    shutil.copy2(CARDS / "madspin_card.dat", process / "Cards/madspin_card.dat")
    run([mg5, "launch.mg5"], workdir)

    candidates = sorted((process / "Events").glob("run_*_decayed_*/unweighted_events.lhe.gz"))
    if not candidates:
        raise FileNotFoundError("No MadSpin-decayed LHE output was produced")
    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(candidates[-1], output)
    print(f"Wrote {output}")
    return output


def simulate(args):
    binary = args.delphes.resolve()
    if not binary.is_file():
        raise FileNotFoundError(binary)
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="hhh_delphes_") as name:
        workdir = Path(name)
        for card in ("FCChh_II.tcl", "electronMomentumResolution_II.tcl",
                     "muonMomentumResolution_II.tcl", "trackMomentumResolution_II.tcl",
                     "edm4hep_output_config.tcl"):
            shutil.copy2(CARDS / card, workdir / card)
        with (gzip.open(args.lhe, "rb") if args.lhe.suffix == ".gz" else open(args.lhe, "rb")) as source:
            with (workdir / "events.lhe").open("wb") as target:
                shutil.copyfileobj(source, target)
        pythia = (CARDS / "mgp8_hhh_84TeV_btau.cmd").read_text()
        pythia += f"\nBeams:LHEF = events.lhe\nRandom:seed = {args.seed}\nMain:numberOfEvents = {args.events}\n"
        (workdir / "card.cmd").write_text(pythia)
        run([binary, "FCChh_II.tcl", "edm4hep_output_config.tcl", "card.cmd", output], workdir)
    print(f"Wrote {output}")


def inspect_lhe(path, limit):
    opener = gzip.open if path.suffix == ".gz" else open
    ids, points, events, checked, bad_decays, bad_weights = [], [], 0, 0, 0, 0
    in_header = in_event = in_init = False
    beam = None
    weight_definition = ""
    event_lines = []
    with opener(path, "rt") as stream:
        for line in stream:
            if "<initrwgt>" in line:
                in_header = True
            elif "</initrwgt>" in line:
                in_header = False
            elif in_header:
                if "<weight id=" in line:
                    weight_definition = line
                elif weight_definition:
                    weight_definition += line
                if weight_definition and "</weight>" in weight_definition:
                    match = re.search(r"<weight id=['\"]([^'\"]+)['\"]>(.*?)</weight>",
                                      weight_definition, flags=re.DOTALL)
                    weight_definition = ""
                    if match:
                        ids.append(match.group(1))
                        trip = re.search(r"tripcoup(?:\s+\d+\s+|=)([-\d.]+)", match.group(2))
                        quart = re.search(r"quartcoup(?:\s+\d+\s+|=)([-\d.]+)", match.group(2))
                        points.append((float(trip.group(1)), float(quart.group(1))))
            if line.strip() == "<init>":
                in_init = True
            elif line.strip() == "</init>":
                in_init = False
            elif in_init and beam is None and re.match(r"^\s*2212\s+2212\s+", line):
                fields = line.split()
                beam = {"energy_1_GeV": float(fields[2]), "energy_2_GeV": float(fields[3]),
                        "pdf_1": int(fields[6]), "pdf_2": int(fields[7])}
            if line.strip() == "<event>":
                in_event, event_lines = True, []
            elif line.strip() == "</event>" and in_event:
                events += 1
                if checked < limit:
                    particles = [row.split() for row in event_lines if re.match(r"^\s*-?\d+\s+-?\d+\s+", row)]
                    stable = [int(row[0]) for row in particles if len(row) >= 3 and row[1] == "1"]
                    higgs = [row for row in particles if row[0] == "25" and row[1] == "2"]
                    if len(higgs) != 3 or sum(abs(p) == 5 for p in stable) != 4 or sum(abs(p) == 15 for p in stable) != 2:
                        bad_decays += 1
                    event_ids = re.findall(r"<wgt id=['\"]([^'\"]+)['\"]>", "".join(event_lines))
                    if event_ids != ids:
                        bad_weights += 1
                    checked += 1
                in_event = False
            elif in_event and checked < limit:
                event_lines.append(line)
    report = {"file": str(path), "events": events, "checked": checked,
              "beam": beam, "weight_ids": ids, "weight_points": points,
              "wrong_decay_events": bad_decays, "wrong_weight_events": bad_weights}
    if points != WEIGHT_POINTS or ids != [f"rwgt_{n}" for n in range(1, 10)]:
        raise ValueError(f"Unexpected weight map in {path}: {report}")
    if beam != {"energy_1_GeV": 42000.0, "energy_2_GeV": 42000.0,
                "pdf_1": 260000, "pdf_2": 260000}:
        raise ValueError(f"Unexpected beam or PDF in {path}: {report}")
    if checked == 0 or bad_decays or bad_weights:
        raise ValueError(f"Invalid HHH events in {path}: {report}")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    lhe = sub.add_parser("lhe", help="Generate reweighted and MadSpin-decayed LHE events")
    lhe.add_argument("--mg5-root", type=Path, required=True)
    lhe.add_argument("--lhapdf-config", type=Path, required=True)
    lhe.add_argument("--workdir", type=Path, required=True)
    lhe.add_argument("--outdir", type=Path, required=True)
    lhe.add_argument("--seed", type=int, required=True)
    lhe.add_argument("--events", type=int, default=10)
    delphes = sub.add_parser("delphes", help="Shower and reconstruct an LHE sample")
    delphes.add_argument("--delphes", type=Path, default=DEFAULT_DELPHES,
                         help=f"Delphes executable (default: {DEFAULT_DELPHES})")
    delphes.add_argument("--lhe", type=Path, required=True)
    delphes.add_argument("--output", type=Path, required=True)
    delphes.add_argument("--seed", type=int, required=True)
    delphes.add_argument("--events", type=int, default=10)
    compare = sub.add_parser("compare", help="Check old and new HHH LHE samples")
    compare.add_argument("--old", type=Path, required=True)
    compare.add_argument("--new", type=Path, required=True)
    compare.add_argument("--events", type=int, default=10)
    args = parser.parse_args()
    if args.command == "lhe":
        report = inspect_lhe(generate_lhe(args), args.events)
        if report["events"] != args.events:
            raise ValueError(f"MG5 wrote {report['events']} events, expected {args.events}")
    elif args.command == "delphes":
        simulate(args)
    else:
        old = inspect_lhe(args.old, args.events)
        new = inspect_lhe(args.new, args.events)
        print(json.dumps({"old": old, "new": new}, indent=2))


if __name__ == "__main__":
    main()
