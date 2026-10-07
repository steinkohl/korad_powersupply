#!/bin/sh
# Copy the KC3405P driver, the UDP adapter, tests and docs into a pymeasure checkout.
# Usage: scripts/add_to_pymeasure.sh /path/to/pymeasure
set -e
[ -d "$1/pymeasure/instruments" ] || { echo "usage: $0 /path/to/pymeasure" >&2; exit 1; }
src="$(cd "$(dirname "$0")/.." && pwd)"
for d in pymeasure tests docs; do
    cp -r "$src/$d" "$1/"
done
init="$1/pymeasure/adapters/__init__.py"
grep -q "udp import UDPAdapter" "$init" || \
    sed -i 's/^from .protocol import ProtocolAdapter$/&\nfrom .udp import UDPAdapter/' "$init"
echo "Done. Still to do by hand: add 'korad/index' to docs/api/instruments/index.rst,"
echo "'udp' to docs/api/adapters/index.rst (if present) and an entry to CHANGES.rst."
