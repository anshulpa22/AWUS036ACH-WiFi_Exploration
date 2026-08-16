#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage:
  wifi-scan-summary.sh INTERFACE [OUTPUT_FILE]

Example:
  ./wifi-scan-summary.sh wlx00c0caXXXXXX

The script performs a Wi-Fi scan and creates an anonymized Markdown report.
Raw SSIDs and BSSIDs are held only in a temporary file and are not copied into
the report.
EOF
}

fail() {
    echo "Error: $*" >&2
    exit 1
}

if [[ $# -lt 1 || $# -gt 2 ]]; then
    usage
    exit 1
fi

INTERFACE=$1

for command in cat iw rfkill awk grep date mktemp dirname mkdir mv rm sudo; do
done

iw dev "$INTERFACE" info >/dev/null 2>&1 ||
    fail "'$INTERFACE' is not a wireless interface"

PHY=$(
    iw dev "$INTERFACE" info |
        awk '/wiphy/ {print "phy" $2; exit}'
)

[[ -n "$PHY" ]] ||
    fail "could not determine PHY for '$INTERFACE'"

RF_STATE=$(
    rfkill --noheadings --output DEVICE,SOFT,HARD |
        awk -v phy="$PHY" '$1 == phy {print $2, $3; exit}'
)

[[ -n "$RF_STATE" ]] ||
    fail "could not map '$PHY' to an RF-kill entry"

read -r SOFT_STATE HARD_STATE <<< "$RF_STATE"

if [[ "$SOFT_STATE" != "unblocked" ]]; then
    fail "radio '$PHY' is soft-blocked: $SOFT_STATE"
fi

if [[ "$HARD_STATE" != "unblocked" ]]; then
    fail "radio '$PHY' is hard-blocked: $HARD_STATE"
fi

COUNTRY=$(
    iw reg get |
        awk '
            /^global$/ {
                global_section=1
                next
            }
            global_section && /^country / {
                country=$2
                sub(/:$/, "", country)
                print country
                exit
            }
        '
)

COUNTRY=${COUNTRY:-unknown}
TIMESTAMP=$(date --iso-8601=seconds)
FILE_TIMESTAMP=$(date +%Y%m%d-%H%M%S)

SCRIPT_DIR=$(
    CDPATH= cd -- "$(dirname -- "$0")" && pwd
)
LAB_DIR=$(dirname "$SCRIPT_DIR")

OUTPUT_FILE=${2:-"$LAB_DIR/results/scan-summary-$FILE_TIMESTAMP.md"}
OUTPUT_DIR=$(dirname -- "$OUTPUT_FILE")

mkdir -p "$OUTPUT_DIR"

RAW_SCAN=$(mktemp)
REPORT_TMP=$(mktemp "$OUTPUT_DIR/.scan-report.XXXXXX")

cleanup() {
    rm -f "$RAW_SCAN" "$REPORT_TMP"
}

trap cleanup EXIT

echo "Scanning with interface '$INTERFACE'..."
echo "The scan may request sudo authentication."

sudo iw dev "$INTERFACE" scan > "$RAW_SCAN"

BSS_COUNT=$(grep -c '^BSS ' "$RAW_SCAN" || true)

{
    echo "# Anonymized Wi-Fi Scan Summary"
    echo
    echo "- Timestamp: \`$TIMESTAMP\`"
    echo "- Interface: \`<anonymized-wireless-interface>\`"
    echo "- PHY at scan time: \`$PHY\`"
    echo "- Regulatory country: \`$COUNTRY\`"
    echo "- BSS entries: \`$BSS_COUNT\`"
    echo
    echo "SSIDs and BSSIDs are intentionally excluded."
    echo
    echo "| AP | Band | Channel | Frequency | Signal | Width | Secondary | Center segment | Security | SSID status |"
    echo "|---|---|---:|---:|---:|---|---|---:|---|---|"

    awk '
        function reset_record() {
            freq=""
            signal=""
            channel=""
            secondary=""
            width=""
            center=""
            security="No RSN observed"
            ssid_status="Not advertised"
        }

        function print_record(    band, inferred_width) {
            if (ap == 0) {
                return
            }

            if (freq == "") {
                freq="unknown"
            }

            if (signal == "") {
                signal="unknown"
            } else {
                signal=signal " dBm"
            }

            if (channel == "") {
                channel="unknown"
            }

            if (freq != "unknown" && (freq + 0) < 3000) {
                band="2.4 GHz"
            } else if (freq != "unknown" && (freq + 0) < 5925) {
                band="5 GHz"
            } else if (freq != "unknown") {
                band="6 GHz"
            } else {
                band="unknown"
            }

            inferred_width=width

            if (inferred_width == "") {
                if (secondary == "above" || secondary == "below") {
                    inferred_width="40 MHz"
                } else if (secondary == "no secondary") {
                    inferred_width="20 MHz"
                } else {
                    inferred_width="unknown"
                }
            }

            if (secondary == "") {
                secondary="unknown"
            }

            if (inferred_width == "20 MHz" ||
                inferred_width == "40 MHz") {
                center="—"
            } else if (center == "") {
                center="—"
            }

            printf "| AP-%02d | %s | %s | %s MHz | %s | %s | %s | %s | %s | %s |\n", ap, band, channel, freq, signal, inferred_width, secondary, center, security, ssid_status
        }

        BEGIN {
            ap=0
            reset_record()
        }

        /^BSS / {
            print_record()
            ap++
            reset_record()
            next
        }

        /^[[:space:]]+freq:/ {
            freq=$2
            next
        }

        /^[[:space:]]+signal:/ {
            signal=$2
            next
        }

        /DS Parameter set: channel/ {
            channel=$NF
            next
        }

        /\* primary channel:/ {
            channel=$NF
            next
        }

        /\* secondary channel offset:/ {
            secondary=$0
            sub(/^.*secondary channel offset:[[:space:]]*/, "", secondary)
            next
        }

        /\* STA channel width: 20 MHz/ {
            if (width == "") {
                width="20 MHz"
            }
            next
        }

        /\* channel width:/ {
            if ($0 ~ /\(80 MHz\)/) {
                width="80 MHz"
            } else if ($0 ~ /\(160 MHz\)/) {
                width="160 MHz"
            } else if ($0 ~ /\(80\+80 MHz\)/) {
                width="80+80 MHz"
            }
            next
        }

        /\* center freq segment 1:/ {
            center=$NF
            next
        }

        /^[[:space:]]+SSID:/ {
            ssid=$0
            sub(/^[[:space:]]+SSID:[[:space:]]*/, "", ssid)

            if (length(ssid) > 0) {
                ssid_status="Redacted"
            } else {
                ssid_status="Empty"
            }
            next
        }

        /^[[:space:]]+RSN:/ {
            security="RSN present"
            next
        }

        END {
            print_record()
        }
    ' "$RAW_SCAN"

    echo
    echo "## Notes"
    echo
    echo "- Signal values come from the driver through \`iw\`."
    echo "- Advertised PHY rate is not application throughput."
    echo "- Width is inferred from HT/VHT operation information."
    echo "- A missing SSID line is recorded as \`Not advertised\`."
    echo "- The report does not determine whether a non-advertised SSID is intentionally hidden."
}  > "$REPORT_TMP"

mv -- "$REPORT_TMP" "$OUTPUT_FILE"

echo "Created anonymized report:"
echo "  $OUTPUT_FILE"
echo
echo "Raw scan data was stored temporarily and will now be deleted."
