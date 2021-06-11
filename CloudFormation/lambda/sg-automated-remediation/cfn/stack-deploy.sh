#!/bin/bash
set -e
cfn-cli -s "install.*" stack sync
