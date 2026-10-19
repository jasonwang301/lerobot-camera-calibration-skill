#!/usr/bin/env bash
set -euo pipefail

task_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
python_bin="$task_dir/.venv/bin/python"
if [[ ! -x "$python_bin" ]]; then
  printf '请先运行 bash setup_handeye.sh 创建独立环境。\n' >&2
  exit 1
fi

# Upstream documents a console command that is absent from its entry points.
# Running the module also works when this directory is copied to another PC.
cd "$task_dir"
export PYTHONPATH="$task_dir/cyberwave-edge-so101${PYTHONPATH:+:$PYTHONPATH}"
exec "$python_bin" -m scripts.cw_handeye_debug "$@"
