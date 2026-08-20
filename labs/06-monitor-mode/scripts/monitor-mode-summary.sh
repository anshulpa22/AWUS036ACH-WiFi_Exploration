#!/usr/bin/env bash

set -Eeuo pipefail

usage() {
    cat <<'EOF'
Usage:
  monitor-mode-summary.sh INTERFACE [CHANNEL] [DURATION] [OUTPUT_FILE]

Arguments:
  INTERFACE    Disconnected wireless interface to use
  CHANNEL      Wi-Fi channel; default: 1
  DURATION     Capture duration in seconds; default: 20
  OUTPUT_FILE  Markdown report path; optional

Example:
  ./monitor-mode-summary.sh wlx00c0caXXXXXX 1 20

The script temporarily places a disconnected Wi-Fi interface in monitor mode,
captures privacy-safe management-frame metadata, creates a Markdown summary,
and restores the interface to managed mode.
EOF
}

die() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

set_monitor_channel() {
    local interface=$1
    local channel=$2
    local attempt

    for attempt in 1 2 3 4 5; do
        if sudo iw dev "$interface" set channel "$channel" HT20; then
            return 0
        fi

        if [[ "$attempt" -lt 5 ]]; then
            printf \
               'Channel configuration attempt %d failed; retrying...\n' \
               "$attempt" >&2
            sleep 1
        fi
    done

    die "could not configure channel $channel after 5 attempts"
}

[[ $# -ge 1 && $# -le 4 ]] || {
    usage
    exit 1
}

INTERFACE=$1
CHANNEL=${2:-1}
DURATION=${3:-20}
TIMESTAMP=$(date '+%Y%m%d-%H%M%S')

SCRIPT_DIR=$(
    cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &&
    pwd
)

RESULTS_DIR=$(dirname "$SCRIPT_DIR")/results
OUTPUT_FILE=${4:-"$RESULTS_DIR/monitor-summary-$TIMESTAMP.md"}

[[ "$CHANNEL" =~ ^[0-9]+$ ]] ||
    die "channel must be a positive integer"

[[ "$DURATION" =~ ^[1-9][0-9]*$ ]] ||
    die "duration must be a positive integer"

for command_name in iw ip nmcli tshark awk mktemp; do
    command -v "$command_name" >/dev/null 2>&1 ||
        die "required command '$command_name' was not found"
done

iw dev "$INTERFACE" info >/dev/null 2>&1 ||
    die "'$INTERFACE' is not a wireless interface"

PHY=$(
    iw dev "$INTERFACE" info |
    awk '/^[[:space:]]*wiphy / {print "phy"$2}'
)

iw phy "$PHY" info |
    sed -n '/Supported interface modes:/,/Band 1:/p' |
    grep -qE '^[[:space:]]+\*[[:space:]]+monitor$' ||
    die "'$INTERFACE' does not advertise monitor-mode support"


CURRENT_TYPE=$(
    iw dev "$INTERFACE" info |
    awk '/^[[:space:]]*type / {print $2}'
)

[[ "$CURRENT_TYPE" == "managed" ]] ||
    die "'$INTERFACE' must initially be in managed mode"

if ! iw dev "$INTERFACE" link | grep -q '^Not connected'; then
    die "'$INTERFACE' is connected; refusing to interrupt an active link"
fi

COUNTRY=$(
    iw reg get |
    awk '
        /^global$/ {
            global_section = 1
            next
        }
        global_section && /^country / {
            country = $2
            sub(/:.*/, "", country)
            print country
            exit
        }
    '
)

[[ -n "$COUNTRY" ]] ||
    die "could not determine the global regulatory country"

[[ "$COUNTRY" != "00" ]] ||
    die "global regulatory country is 00; configure the correct country first"

mkdir -p "$RESULTS_DIR"
mkdir -p "$(dirname "$OUTPUT_FILE")"

TEMP_CAPTURE=$(mktemp)
MONITOR_ACTIVE=0

ORIGINAL_MANAGED=$(
    nmcli -g GENERAL.NM-MANAGED device show "$INTERFACE"
)

if ip link show dev "$INTERFACE" |
    grep -q '<[^>]*UP[^>]*>'; then
    ORIGINAL_LINK_STATE=up
else
    ORIGINAL_LINK_STATE=down
fi

cleanup() {
    local exit_status=$?

    trap - EXIT INT TERM

    if [[ "$MONITOR_ACTIVE" -eq 1 ]]; then
        sudo ip link set dev "$INTERFACE" down || true
        sudo iw dev "$INTERFACE" set type managed || true

        if [[ "$ORIGINAL_LINK_STATE" == "up" ]]; then
            sudo ip link set dev "$INTERFACE" up || true
        fi
    fi

    if [[ "$ORIGINAL_MANAGED" == "yes" ]]; then
        sudo nmcli device set "$INTERFACE" managed yes || true
    fi

    rm -f -- "$TEMP_CAPTURE"

    exit "$exit_status"
}

trap cleanup EXIT INT TERM

sudo -v

printf "Using interface: %s\n" "$INTERFACE"
printf "Regulatory country: %s\n" "$COUNTRY"
printf "Channel: %s\n" "$CHANNEL"
printf "Capture duration: %s seconds\n" "$DURATION"

sudo nmcli device set "$INTERFACE" managed no
sudo ip link set dev "$INTERFACE" down
sudo iw dev "$INTERFACE" set type monitor
MONITOR_ACTIVE=1

# The rtw88_8812au driver requires the converted monitor interface to be
# administratively up before it accepts a channel configuration.
sleep 1
sudo ip link set dev "$INTERFACE" up
sleep 1

set_monitor_channel "$INTERFACE" "$CHANNEL"

printf "Capturing privacy-safe management-frame metadata...\n"

sudo tshark \
    -i "$INTERFACE" \
    -a "duration:$DURATION" \
    -Y 'wlan.fc.type == 0' \
    -T fields \
    -e frame.time_epoch \
    -e wlan.fc.type_subtype \
    -e radiotap.channel.freq \
    -e radiotap.dbm_antsignal \
    > "$TEMP_CAPTURE"

FRAME_COUNT=$(wc -l < "$TEMP_CAPTURE")

{
    printf '# Anonymized Monitor-Mode Summary\n\n'
    printf -- '- Timestamp: `%s`\n' "$(date --iso-8601=seconds)"
    printf -- '- Interface: `<anonymized-wireless-interface>`\n'
    printf -- '- Regulatory country: `%s`\n' "$COUNTRY"
    printf -- '- Channel: `%s`\n' "$CHANNEL"
    printf -- '- Duration: `%s seconds`\n' "$DURATION"
    printf -- '- Management frames: `%s`\n\n' "$FRAME_COUNT"

    printf 'SSIDs, BSSIDs, station addresses and payloads are excluded.\n\n'
    printf '| Subtype | Meaning | Frames |\n'
    printf '|---|---|---:|\n'

    awk -F '\t' '
    function name(value) {
        if (value == "0x0000") return "Association request"
        if (value == "0x0001") return "Association response"
        if (value == "0x0004") return "Probe request"
        if (value == "0x0005") return "Probe response"
        if (value == "0x0008") return "Beacon"
        if (value == "0x000a") return "Disassociation"
        if (value == "0x000b") return "Authentication"
        if (value == "0x000c") return "Deauthentication"
        return "Other management subtype"
    }
    NF >= 2 {
        count[$2]++
    }
    END {
        for (type in count)
            printf "| `%s` | %s | %d |\n",
                   type, name(type), count[type]
    }
    ' "$TEMP_CAPTURE" | sort

    printf '\n## Aggregate RSSI\n\n'

    awk -F '\t' '
    {
        values = split($4, chain, ",")

        for (i = 1; i <= values; i++) {
            if (chain[i] ~ /^-[0-9]+([.][0-9]+)?$/) {
                rssi = chain[i] + 0
                samples++
                sum += rssi

                if (samples == 1 || rssi < minimum)
                    minimum = rssi

                if (samples == 1 || rssi > maximum)
                    maximum = rssi

                break
            }
        }
    }
    END {
        if (samples == 0) {
            print "No valid negative RSSI measurements were reported."
            exit
        }

        printf "- Samples: `%d`\n", samples
        printf "- Mean: `%.2f dBm`\n", sum / samples
        printf "- Weakest: `%.2f dBm`\n", minimum
        printf "- Strongest: `%.2f dBm`\n", maximum
    }
    ' "$TEMP_CAPTURE"

    printf '\n## Interpretation Limits\n\n'
    printf '%s\n' \
        '- RSSI is aggregated across all captured management-frame sources.' \
        '- The mean does not represent one particular access point.' \
        '- Monitor mode does not guarantee reception of every transmitted frame.' \
        '- This report performs passive observation only.' \
        '- No raw packet capture is retained.'
} > "$OUTPUT_FILE"

printf "Created anonymized report:\n  %s\n" "$OUTPUT_FILE"
printf "The interface will now be restored to managed mode.\n"
