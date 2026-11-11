# Source from any directory: source /path/to/EventProducer/init.sh
source /cvmfs/sw.hsf.org/key4hep/setup.sh -r 2026-04-08
export EVENTPRODUCER=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export PYTHONPATH="${EVENTPRODUCER}/..:${PYTHONPATH}"
