# Event production

FCChh production uses EventProducer's normal `bin/run.py` interface. Data paths
in `config/param_FCChh.py` default to this checkout; `--output-dir` selects a
different shared production root. Edit that configuration for the site's MG5,
LHAPDF and Delphes installations. Source `EventProducer/init.sh` before checking
ROOT files or running reconstruction jobs directly.

From the top-level repository, generate one HHH file of 100 events:

```bash
python3 EventProducer/bin/run.py --FCChh --LHE --send --condor \
  --typelhe mg --process mg_pp_hhh_84TeV -N 1 -n 100
```

Add `--dry-run` to preview without writing or submitting, or `--prepare-only`
to write the Condor description without submitting. The latter prints the
`condor_submit` command for the prepared jobs. Neither option starts production.
HHH automatically uses the bundled model, MG5 card, MadSpin card and reweight
card. `--mg5card`, `--model`, `--madspin-card` and `--reweight-card` override
those files. Nominal couplings are edited manually in the MG5 card.

After the LHE jobs finish, check them to populate the existing YAML records:

```bash
source EventProducer/init.sh
python3 EventProducer/bin/run.py --FCChh --LHE --check --force \
  --process mg_pp_hhh_84TeV
```

Then submit the separate Pythia/Delphes jobs:

```bash
python3 EventProducer/bin/run.py --FCChh --reco --send --condor \
  --type lhep8 --process mg_pp_hhh_84TeV --prodtag fcc_v07 --detector II \
  -N 1 -n 100
```

Use the same `--output-dir` on every command when overriding the default.
Reconstruction reads only LHE records marked `DONE`. Existing reconstruction
records/files are skipped; use a fresh output directory for another production.
For a ROOT-file check after reconstruction finishes:

```bash
python3 EventProducer/bin/run.py --FCChh --reco --check --force \
  --process mg_pp_hhh_84TeV --prodtag fcc_v07 --detector II
```

`-N` is the number of jobs and `-n` is the number of events **per job**.
Each job is limited to 10,000 events. Five million events therefore use
`-N 500 -n 10000` for each submission stage. To request a total not divisible
by 10,000, submit the full jobs and one additional smaller LHE job.

For all six processes, edit the settings at the top of `hhh/submit_all.sh` and
run it from any directory:

```bash
bash EventProducer/hhh/submit_all.sh
```

The Bash file explicitly lists HHH, ttbb, ttZ, ttH, tttt and ZZZ process names.
It calls the same original submission interface for each process and starts in
`dry-run` mode. Submit `stage="lhe"` first. When those jobs finish, check the
LHE files (omit `--process` on the check command to check every process), then
change to `stage="reco"`. `jobs` and `events` are set manually in the script.
Backgrounds use their MG5 example cards and bundled Pythia cards, with no HHH
MadSpin/reweight options added.

## Files and software

Under the production root:

* `LHE/mg_pp_hhh_84TeV/events_<id>.lhe.gz`: compressed signal LHE files.
* `DelphesEvents/fcc_v07/II/mgp8_pp_hhh_84TeV/events_<id>.root`: reconstructed signal files.
* `yaml/lhe/` and `yaml/fcc_v07/II/`: existing LHE/reconstruction bookkeeping.
* `BatchOutputs/`: generated scripts, Condor descriptions and logs.
* `statistics/` and `dicts/`: local status and process-dictionary outputs.

These data directories are ignored by Git. The process names and versioned
reconstruction layout follow the original EventProducer conventions.
The earlier `LHE/HHH_samples` and `HHH_recoSamples` layout belongs to the older
standalone test submitter; existing productions were not moved.

Software environments remain on CVMFS. The HHH generator uses MG5 2.9.24 and
LCG 107; `fcc_v07` reconstruction uses Key4hep 2026-04-08 and the locally
installed upstream k4SimDelphes binary. The supplied detector cards cover
`fcc_v07/II`. Other detector cards must be supplied before requesting them.
HHH's process-dictionary cross section is deliberately `nan`: determine the
normalization from the generated sample before producing analysis yields.

After reconstruction, set the process, input/output directories and batch
settings in the FCCAnalyses ntuple configuration, then run:

```bash
source FCCAnalyses/setup.sh
fccanalysis submit /path/to/HHH_ntuples.py
```

`hhh/submit_signal.py` is only a shorthand for the normal HHH command and takes
the same `--LHE`/`--reco`, `-N`, `-n` and submission flags. The older
`hhh/submit_condor_smoke.py` remains a standalone test utility; the normal
EventProducer submission path does not call it.

## Small standalone generation checks

`produce.py` generates the FCC-hh 84 TeV `gg > hhh > 4b2tau` signal using
MadGraph5_aMC 2.9.24, the bundled `loop_sm_c3d4` model, the nine reweight
points in `cards/reweight_card.dat`, and MadSpin. It then supports Pythia8 plus
Delphes simulation with the bundled `fcc_v07/II` detector card. The LHE step
writes `events_<seed>.lhe.gz`; the Delphes step decompresses it in a temporary
directory, so no manual format conversion is needed.

Set the nominal couplings manually in `cards/mg_pp_hhh_84TeV.mg5`.
The card sets the SM point with `set tripcoup 4 0` and `set quartcoup 6 0`,
overriding the bundled UFO defaults of `c3=2, d4=3`. The nine reweight points
remain in `cards/reweight_card.dat`. Use `--reweight-card` and `--madspin-card`
to select alternative cards. Check the resulting LHE header to confirm the
nominal settings.

Source the environment containing MG5's dependencies and LHAPDF before running
the LHE stage. Source the appropriate key4hep environment before running the
Delphes stage. The Delphes stage defaults to the locally installed upstream
`k4SimDelphes` v00-08 binary at
`/data/atlas02/users/dingleyt/FCChh/key4/k4SimDelphes_upstream_v00_08/install/bin/DelphesPythia8_EDM4HEP`.
Source `/cvmfs/sw.hsf.org/key4hep/setup.sh -r 2026-04-08` for this binary.
Override it with `--delphes` or `HHH_DELPHES_BINARY`. All other
tool and output paths are passed explicitly. The MG5 work directory is retained
for logs and provenance.

The installed binary was built from upstream `key4hep/k4SimDelphes` tag
`v00-08` (commit `96ef2eddb90ed6e81eee63dc6ca076ba73ac7bb6`), which includes
Michele Selvaggi's [PR #158](https://github.com/key4hep/k4SimDelphes/pull/158).
No local Delphes source patch is needed. The previous
`k4SimDelphes-weightNames.patch` is retained only to document the old build.
The submodule does not contain a Delphes binary. Keep the binary's source
revision and key4hep release recorded with each production.
To rebuild the same executable on this host, use:

```bash
source /cvmfs/sw.hsf.org/key4hep/setup.sh -r 2026-04-08
git clone --branch v00-08 --depth 1 https://github.com/key4hep/k4SimDelphes.git k4SimDelphes-v00-08
cmake -S k4SimDelphes-v00-08 -B k4SimDelphes-v00-08/build \
  -DCMAKE_INSTALL_PREFIX=/data/atlas02/users/dingleyt/FCChh/key4/k4SimDelphes_upstream_v00_08/install \
  -DCMAKE_INSTALL_LIBDIR=lib -DBUILD_TESTING=OFF
cmake --build k4SimDelphes-v00-08/build -j 4
cmake --install k4SimDelphes-v00-08/build
```

For a ten-event old/new smoke test, run `test_generation.sh` with six arguments:
an existing EventProd `4b2tau` LHE file, the MG5 2.9.24 directory, the
`lhapdf-config` executable, a fresh output directory, and the LCG and key4hep
setup scripts. The test script uses Key4hep release `2026-04-08`; an optional
seventh argument overrides the Delphes executable.
It creates both LHE and ROOT comparison reports, with generator logs alongside.
Use a fresh output directory for a repeat run. The samples have different seeds,
so the comparison checks process content, decay, weight IDs/order, and retention
of nine HHH reweights, rather than demanding identical kinematics. The checker
accepts both old nine-entry files and upstream ten-entry files, where the first
entry is the nominal `Weight` and the names are in the file-level metadata.

The HHH cross section and k-factor are deliberately not copied from EventProd's
`param_FCChh.py`, where the HHH entry duplicates `ttbb`. Determine those values
from the generator output and the intended normalization calculation before
using the samples for yields.

The first ten-event run is recorded in `tests/smoke_2026-09-27.md`. For MG5,
use a clean 2.9.24 extraction or a complete installation with CutTools built
using the active compiler; the old unpacked EventProd directory is missing a
Python module, and another local installation had an incompatible CutTools build.

For this HHH input, upstream stores `Weight` followed by `rwgt_1` through
`rwgt_9`. `FCCAnalyses/hhh/HHH_ntuples.py` reads the nine reweights at indices
1–9 in these files and at indices 0–8 in the old locally patched files. The
ten-event comparison against the same LHE input is recorded in
`tests/upstream_weights_2026-09-27.md`. See also `tests/pythia_weights.md`.
