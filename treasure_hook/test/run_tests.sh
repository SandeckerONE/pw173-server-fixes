#!/bin/bash
# run_tests.sh - builds the 64-bit test copy of treasure_hook plus fake_gs in three
# shapes (PIE -O0, non-PIE -O0, PIE -O2) and runs run_tests.py against each.
# This is Claude's sandbox test. It is NOT needed on the server.
set -e
cd "$(dirname "$0")"
OUT=${1:-out}
rm -rf "$OUT"
mkdir -p "$OUT/pie_O0" "$OUT/nopie_O0" "$OUT/pie_O2"
gcc -std=gnu11 -O2 -fPIC -shared -Wall -Wextra -o "$OUT/libtreasure64.so" ../src/treasure_hook.c -lpthread
g++ -std=c++11 -Wno-invalid-offsetof -O0 -fno-devirtualize -o "$OUT/pie_O0/gs" fake_gs.cpp
g++ -std=c++11 -Wno-invalid-offsetof -O0 -fno-devirtualize -no-pie -fno-pie -o "$OUT/nopie_O0/gs" fake_gs.cpp
g++ -std=c++11 -Wno-invalid-offsetof -O2 -o "$OUT/pie_O2/gs" fake_gs.cpp
python3 run_tests.py "$OUT"
