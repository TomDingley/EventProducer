#!/bin/bash
# MG5 worker used by send_mglhe; paths are supplied by param_FCChh.py.
SCRIPTFILE=$1
PROCESSNAME=$2
OUTPUTDIR=$3
JOBID=$4
NEVENTS=$5
CUTFILE=$6
MODELFILE=$7
PLUGINFILE=${8:-}
REWEIGHTCARD=${9:-}
MADSPINCARD=${10:-}
MG5ROOT=${11}
LHAPDFCONFIG=${12}
GENERATORSETUP=${13}

unset LD_LIBRARY_PATH
unset PYTHONHOME
unset PYTHONPATH
source "$GENERATORSETUP" || exit 1
MG5="$MG5ROOT/bin/mg5_aMC"
if [ ! -f "$MG5" ] || [ "$NEVENTS" -lt 1 ] || [ "$NEVENTS" -gt 10000 ]; then
    echo "Invalid MG5 installation or event count" >&2
    exit 1
fi
OUTDIR="$OUTPUTDIR/$PROCESSNAME"
OUTFILE="$OUTDIR/events_$JOBID.lhe.gz"
if [ -e "$OUTFILE" ]; then
    echo "Output already exists: $OUTFILE" >&2
    exit 1
fi

mkdir job || exit 1
cd job || exit 1
cp "$SCRIPTFILE" card.mg5 || exit 1
SEED=$((10#$JOBID))
sed -i -e "s/DUMMYSEED/$SEED/g" -e "s/DUMMYNEVENTS/$NEVENTS/g" card.mg5 || exit 1
csplit --digits=2 --quiet --prefix=config card.mg5 '/DELIMITER/+1' '{*}' || exit 1
sed -i "s|^set lhapdf .*|set lhapdf $LHAPDFCONFIG|" config01 || exit 1

# Extract custom models in this job, without changing the MG5 installation.
if [ -f "$MODELFILE" ]; then
    tar -xf "$MODELFILE" || exit 1
    MODELNAME=$(awk '$1 == "import" && $2 == "model" {print $3; exit}' config00)
    MODELPATH=$(find "$PWD" -type d -name "$MODELNAME" -print -quit)
    if [ -z "$MODELPATH" ]; then
        echo "Model $MODELNAME was not found in $MODELFILE" >&2
        exit 1
    fi
    sed -i "s|import model $MODELNAME|import model $MODELPATH|" config00 || exit 1
fi
if [ -n "$PLUGINFILE" ]; then
    mkdir -p PLUGIN || exit 1
    cp "$PLUGINFILE" PLUGIN/ || exit 1
fi

"$MG5" config00 || exit 1
if [ -f "$CUTFILE" ]; then
    cp "$CUTFILE" DUMMYPROCESS/SubProcesses/cuts.f || exit 1
fi
if [ -n "$REWEIGHTCARD" ]; then
    cp "$REWEIGHTCARD" DUMMYPROCESS/Cards/reweight_card.dat || exit 1
fi
if [ -n "$MADSPINCARD" ]; then
    cp "$MADSPINCARD" DUMMYPROCESS/Cards/madspin_card.dat || exit 1
fi
"$MG5" config01 || exit 1

INFILE=$(find DUMMYPROCESS/Events -path '*/run_*_decayed_*/unweighted_events.lhe.gz' | sort | tail -n 1)
if [ -z "$INFILE" ]; then
    if [ -n "$MADSPINCARD" ]; then
        echo "MadSpin did not produce a decayed LHE file" >&2
        exit 1
    fi
    INFILE="DUMMYPROCESS/Events/run_01/unweighted_events.lhe.gz"
fi
if [ ! -s "$INFILE" ]; then
    echo "Missing MG5 output: $INFILE" >&2
    exit 1
fi
mkdir -p "$OUTDIR" || exit 1
cp "$INFILE" "$OUTFILE" || exit 1
printf 'Wrote %s\n' "$OUTFILE"
