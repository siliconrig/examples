#!/usr/bin/env bash
set -euo pipefail

if [ -z "${IDF_PATH:-}" ]; then
    echo "IDF_PATH not set. Source your ESP-IDF export.sh first."
    exit 1
fi

cd "$(dirname "$0")"

for project in sender receiver; do
    echo "Building $project..."
    cd "$project"
    if [ ! -f build/CMakeCache.txt ]; then
        idf.py set-target esp32s3
    fi
    idf.py build
    esptool.py --chip esp32s3 merge_bin -o "build/${project}-merged.bin" \
        --flash_mode dio --flash_size 16MB \
        0x0 build/bootloader/bootloader.bin \
        0x8000 build/partition_table/partition-table.bin \
        0x10000 "build/${project}.bin"
    cd ..
done

echo "Done. Merged binaries:"
echo "  sender/build/sender-merged.bin"
echo "  receiver/build/receiver-merged.bin"
