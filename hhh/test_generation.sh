#!/usr/bin/env bash
# Compare a small new 4b2tau sample to an existing EventProd sample.

if [ "$#" -lt 6 ] || [ "$#" -gt 7 ]; then
    echo "Usage: $0 OLD_LHE MG5_ROOT LHAPDF_CONFIG OUTPUT_DIRECTORY MG5_SETUP KEY4HEP_SETUP [DELPHES_BINARY]" >&2
    exit 2
fi

old_lhe=$1
mg5_root=$2
lhapdf_config=$3
outdir=$4
mg5_setup=$5
key4hep_setup=$6
delphes_args=()
if [ "$#" -eq 7 ]; then
    delphes_args=(--delphes "$7")
fi
script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
mkdir -p "$outdir" || exit 1

echo "Generating ten events; MG5 log: $outdir/mg5.log"
(
    source "$mg5_setup" || exit 1
    python3 "$script_dir/produce.py" lhe \
        --mg5-root "$mg5_root" --lhapdf-config "$lhapdf_config" \
        --workdir "$outdir/mg5_work" --outdir "$outdir" --seed 910582 --events 10
) > "$outdir/mg5.log" 2>&1 || exit 1
new_lhe="$outdir/events_000910582.lhe.gz"
python3 "$script_dir/produce.py" compare --old "$old_lhe" --new "$new_lhe" \
    --events 10 > "$outdir/lhe_comparison.json" || exit 1
echo "Reconstructing old and new events; Delphes logs: $outdir/old_delphes.log and $outdir/new_delphes.log"
(
    source "$key4hep_setup" -r 2026-04-08 || exit 1
    python3 "$script_dir/produce.py" delphes "${delphes_args[@]}" \
        --lhe "$old_lhe" --output "$outdir/old.root" --seed 910581 --events 10 \
        > "$outdir/old_delphes.log" 2>&1 || exit 1
    python3 "$script_dir/produce.py" delphes "${delphes_args[@]}" \
        --lhe "$new_lhe" --output "$outdir/new.root" --seed 910582 --events 10 \
        > "$outdir/new_delphes.log" 2>&1 || exit 1
    python3 "$script_dir/check_root.py" "$outdir/old.root" "$outdir/new.root" \
        --old-lhe "$old_lhe" --new-lhe "$new_lhe" \
        > "$outdir/root_comparison.json" || exit 1
) || exit 1
echo "Comparison reports: $outdir/lhe_comparison.json and $outdir/root_comparison.json"
