#!/usr/bin/env bash
set -euo pipefail

task_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$task_dir"
upstream_commit=66687450bce0fb4b742526e18294d33a53485175
upstream_dir="$task_dir/cyberwave-edge-so101"

if [[ ! -d "$upstream_dir/.git" ]]; then
  git -c 'url.https://github.com/cyberwave-os/.insteadOf=https://github.com/cyberwave-os/' \
    clone https://github.com/cyberwave-os/cyberwave-edge-so101.git "$upstream_dir"
  git -C "$upstream_dir" checkout --detach "$upstream_commit"
fi
if [[ "$(git -C "$upstream_dir" rev-parse HEAD)" != "$upstream_commit" ]]; then
  printf '仓库不是已验证版本 %s；请使用单独目录，脚本不会重置已有代码。\n' "$upstream_commit" >&2
  exit 1
fi

for trial_patch in "$task_dir/patches/offline-report-sdk-073.patch" "$task_dir/patches/aprilgrid-board.patch"; do
  if git -C "$upstream_dir" apply --reverse --check "$trial_patch" >/dev/null 2>&1; then
    : # This patch is already present.
  elif git -C "$upstream_dir" apply --check "$trial_patch"; then
    git -C "$upstream_dir" apply "$trial_patch"
  else
    printf '无法应用补丁 %s；保留现有代码，请检查仓库改动。\n' "$trial_patch" >&2
    exit 1
  fi
done

if ! "$task_dir/.venv/bin/python" -m pip --version >/dev/null 2>&1; then
  task_python="${HANDEYE_PYTHON:-python3.12}"
  "$task_python" -c 'import sys; assert sys.version_info[:2] == (3, 12), "此安装脚本使用 Python 3.12"'
  if "$task_python" -c 'import ensurepip' >/dev/null 2>&1; then
    "$task_python" -m venv "$task_dir/.venv"
  elif python3 -c 'import virtualenv' >/dev/null 2>&1; then
    python3 -m virtualenv --app-data "$task_dir/.bootstrap-cache" \
      --no-periodic-update --no-download --python "$task_python" "$task_dir/.venv"
  else
    printf '缺少 Python 3.12 venv 支持；Ubuntu 可安装 python3.12-venv 后重试。\n' >&2
    exit 1
  fi
fi

export PIP_CACHE_DIR="$task_dir/.cache/pip"
package_index="${HANDEYE_INDEX_URL:-https://mirrors.aliyun.com/pypi/simple}"
if [[ -d "$task_dir/wheelhouse" ]]; then
  package_source=(--no-index --find-links "$task_dir/wheelhouse")
else
  package_source=(--index-url "$package_index")
fi
if [[ -f "$task_dir/requirements-handeye.lock.txt" ]]; then
  "$task_dir/.venv/bin/python" -m pip install "${package_source[@]}" \
    --report "$task_dir/install-report.json" -r "$task_dir/requirements-handeye.lock.txt"
else
  "$task_dir/.venv/bin/python" -m pip install "${package_source[@]}" \
    --report "$task_dir/install-report.json" \
    -e "$upstream_dir" 'cyberwave[camera]==0.7.3' 'opencv-python-headless>=4.10,<5'
fi

"$task_dir/.venv/bin/python" -m pip check
"$task_dir/.venv/bin/python" -c \
  'import cv2; import cyberwave.calibration; import pinocchio; print("标定依赖导入成功，OpenCV", cv2.__version__)'
printf '安装完成。离线自检：bash handeye.sh selftest\n'
