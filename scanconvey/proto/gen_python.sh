#!/usr/bin/env bash
# Run from project root: bash proto/gen_python.sh
set -e
cd "$(dirname "$0")/.."

python -m grpc_tools.protoc \
  -I proto \
  --python_out=backend \
  --grpc_python_out=backend \
  proto/conveyor.proto

echo "Python gRPC stubs generated in backend/"
