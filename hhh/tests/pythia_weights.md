# HHH LHE weights in Pythia 8.311

A small Pythia program read EventProd's `events_000910581.lhe` using the same
`Beams:frameType = 4` and `Beams:setProductionScalesFromLHEF = off` settings as
the HHH Pythia card. Immediately after `init()`, `Info::weightNameVector()`
contained only `Weight`. After the first successful `next()`, it contained
ten names: `Weight`, then `AUX_rwgt_1` through `AUX_rwgt_9`.

The first event's nominal value was `0.00027091258`. Its next nine values were
`0.00060440098`, `0.00038721921`, `0.0015880524`, `0.00032933119`,
`0.00060167072`, `0.001524054`, `0.00061574788`, `0.00041006328`, and
`0.00095766746`. These equal the nine `<wgt>` values in the input LHE event.

Michele Selvaggi's upstream k4SimDelphes PR #158 reads these vectors after
each event. Its resulting `EventHeader.weights` layout is therefore expected to
have ten entries for HHH, with the nominal value at index 0. The current HHH
ntuple code reads indices 0-8 as the nine coupling points, so it needs a
one-position offset for such files. An upstream Delphes binary still needs an
end-to-end output check before switching production.

To repeat the vector check after sourcing a Key4hep environment containing
Pythia8, compile `pythia_weight_probe.cc` with
`g++ pythia_weight_probe.cc -o pythia_weight_probe $(pythia8-config --cxxflags --libs)`
and pass an uncompressed HHH LHE file to the resulting executable.
