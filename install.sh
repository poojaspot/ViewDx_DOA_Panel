#!/bin/bash
set -e

TOKEN="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"

pip install --no-deps git+https://$TOKEN@github.com/SpotSensein/meril_doa/commits/viewdx_doa
