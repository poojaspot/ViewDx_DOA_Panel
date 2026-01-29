#!/bin/bash
set -e

TOKEN="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"

pip install --no-deps git+https://$TOKEN@github.com/SpotSensein/meril_doa/commits/viewdx_doa
