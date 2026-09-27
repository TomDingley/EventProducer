# HHH signal production

`produce.py` generates the FCC-hh 84 TeV `gg > hhh > 4b2tau` signal using
MadGraph5_aMC 2.9.24, the bundled `loop_sm_c3d4` model, the nine reweight
points in `cards/reweight_card.dat`, and MadSpin. It then supports Pythia8 plus
Delphes simulation with the bundled `fcc_v07/II` detector card. The LHE step
writes `events_<seed>.lhe.gz`; the Delphes step decompresses it in a temporary
directory, so no manual format conversion is needed.

Source the environment containing MG5's dependencies and LHAPDF before running
the LHE stage. Source the appropriate key4hep environment before running the
Delphes stage. Pass paths explicitly; no production output directory is fixed
in the scripts. The MG5 work directory is retained for logs and provenance.

The Delphes executable must be built from `TomDingley/k4SimDelphes` branch
`weightNamesPythia`, commit `be648e4`. That revision preserves LHE weight IDs
as EDM4hep metadata; the converter places their values in `EventHeader.weights`.
`k4SimDelphes-weightNames.patch` records the exact source difference from its
base commit `e2ade58`, so the change can also be reviewed or applied locally.
The submodule does not contain a Delphes binary. Keep the binary's build and
key4hep release recorded with each production.

For a ten-event old/new smoke test, run `test_generation.sh` with seven arguments:
an existing EventProd `4b2tau` LHE file, the MG5 2.9.24 directory, the
`lhapdf-config` executable, the patched `DelphesPythia8_EDM4HEP` executable,
and a fresh output directory, followed by the LCG and key4hep setup scripts.
It creates both LHE and ROOT comparison reports, with generator logs alongside.
Use a fresh output directory for a repeat run. The samples have different seeds,
so the comparison checks process content, decay, weight IDs/order, and retention
of nine event weights, rather than demanding identical kinematics.

The HHH cross section and k-factor are deliberately not copied from EventProd's
`param_FCChh.py`, where the HHH entry duplicates `ttbb`. Determine those values
from the generator output and the intended normalization calculation before
using the samples for yields.

The first ten-event run is recorded in `tests/smoke_2026-09-27.md`. For MG5,
use a clean 2.9.24 extraction or a complete installation with CutTools built
using the active compiler; the old unpacked EventProd directory is missing a
Python module, and another local installation had an incompatible CutTools build.
