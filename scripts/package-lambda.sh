#!/usr/bin/env bash
set -euo pipefail

python_version="${1:?Usage: bash scripts/package-lambda.sh PYTHON_VERSION ARCHITECTURE}"
architecture="${2:?Specify arm64 or x86_64}"

case "$architecture" in
  arm64) platform_arch=aarch64 ;;
  x86_64) platform_arch=x86_64 ;;
  *) printf 'Unsupported architecture: %s\n' "$architecture" >&2; exit 1 ;;
esac

cd "$(dirname "${BASH_SOURCE[0]}")/.."
mkdir -p out
archive="$PWD/out/image-uploader.zip"
package_dir=$(mktemp -d)
trap 'rm -rf "$package_dir"' EXIT
mkdir "$package_dir/files"

python -m pip install \
  --requirement requirements.txt \
  --target "$package_dir/files" \
  --platform "manylinux_2_28_$platform_arch" \
  --platform "manylinux2014_$platform_arch" \
  --implementation cp \
  --python-version "$python_version" \
  --only-binary=:all: \
  --no-compile

cp -R src/image_uploader "$package_dir/files/"
(
  cd "$package_dir/files"
  zip -qr ../image-uploader.zip . -x '*/__pycache__/*' '*.pyc'
)
mv "$package_dir/image-uploader.zip" "$archive"
