# SO101 双相机标定流程

## 复用已有项目或建立试用目录

先检查已有仓库、虚拟环境、图像和参数，避免覆盖。已有项目可直接运行自身工具；新 SO101 试用可将本技能的 `assets/trial/` 内容复制到一个独立工作目录，再在该目录运行 `bash setup_handeye.sh`。

附带基线在 Linux x86_64 / Python 3.12 上验证，来源为 [cyberwave-edge-so101](https://github.com/cyberwave-os/cyberwave-edge-so101)，提交 `66687450bce0fb4b742526e18294d33a53485175`。首次安装需要取得上游源码和依赖；不包含虚拟环境、整个上游仓库或大型 wheelhouse。其他系统需重新验证依赖兼容性。

- Cyberwave SDK `0.7.3` 包含所需标定模块；试用过的 `0.7.1` 不含该模块。
- 使用一个 OpenCV 安装，基线为 `opencv-python-headless==4.14.0.94`，避免多个包同时占用 `cv2`。
- `handeye.sh` 用 `python -m scripts.cw_handeye_debug` 启动，上游这一提交未注册 README 中的调试 console script。
- `setup_handeye.sh` 会核对上游提交并幂等应用两份补丁，不重置其他版本的已有仓库。补丁分别修复 SDK 报告接口，以及增加 AprilGrid、`--board-config` 和离线渲染支持。
- 安装脚本在有 `wheelhouse/` 时用离线包，否则默认阿里云 PyPI 镜像；可用 `HANDEYE_INDEX_URL=https://pypi.org/simple` 改用官方源。附带 `verify_pypi_report.py` 可将安装报告中的归档 SHA256 与官方 PyPI 比对。
- `assets/so101_new_calib.urdf` 及来源校验信息已附带。该 URDF 用于 FK，没有网格文件，不能作为渲染素材包。

## 板识别和离线检查

区分普通棋盘格、ChArUco、纯 AprilGrid。对现有板先检测字典、完整 ID 排列及各标签的 canonical 角点顺序，再确认实测尺寸。打印字样或手写修改不能替代用户的实测确认。

`configs/user-aprilgrid.json` 仅适用于附带参考照片对应的这块板：36h11，8 列 11 行，ID 3–90，列优先，标签图案逆时针旋转 90°，黑框 0.049 m、白色间隙 0.012 m。其他板需要新建配置。

在试用工作目录中执行以下命令；每次自检使用未存在的新输出目录：

```bash
mkdir -p artifacts
.venv/bin/python verify_aprilgrid.py
bash handeye.sh selftest --board-config configs/user-aprilgrid.json \
  --pixels-per-square 196 --distance 1.4 --out runs/offline-check-001
bash handeye.sh intrinsics --run runs/offline-check-001
bash handeye.sh solve --run runs/offline-check-001 --intrinsics-from-fit --use-fitted-distortion
```

这些命令只使用参考照片／合成图像，不打开摄像头或串口。`196` 像素标签在这个特定板尺寸下对应 48 像素间隙，避免渲染取整改变比例。`1.4` 是合成图像距离，不是对真机采集距离的要求。

## 真机输入与尚缺的采集入口

核对每台相机的物理安装与稳定设备路径。同型号且无唯一序列号的 USB 相机可能共享 by-id；优先核对 `/dev/v4l/by-path/`。不要根据 `/dev/video0` 等编号猜腕部／桌边；区分实际图像节点与 metadata 节点。

区分权限问题和占用问题：检查节点权限、用户组以及 EBUSY。`fuser` 查不到其他用户的 PID 不能证明空闲。不要为修复 EBUSY 盲目改路径解析，也不要自行停止其他任务。

附带上游基线有两个具体限制，采集前必须处理：

1. `Camera` 硬编码请求 1280×720，未暴露分辨率 CLI 参数。先按真实 LeRobot 相机模式补充分辨率选择，并记录实际获得的图像尺寸，或换用项目已有的匹配采集器。不要将 720p 结果直接套到 VGA。
2. `capture` 同时连接机械臂，而且要求已知 `fx/fy/cx/cy`。它不适合从零采集初始内参。先提供**只打开相机、不打开串口**的图像采集／导入入口，保存多角度、不同距离及覆盖画面不同区域的清晰图像。可使用 SDK `solve_intrinsics(images, board)`，或经过检查的现有离线拟合入口。当前基线 SDK 要求至少 5 个有效视角。

每台相机独立拟合 `K/D`；图像尺寸要一致。检查覆盖范围、重投影误差及异常视角，再用未参与拟合的图像验证。低误差本身不能证明板尺寸、实际尺度或焦距一定正确。

## 腕部外参

固定板相对机械臂底座，保持采集期间不动；移动机械臂获取绕不同轴旋转的姿态，在静止时同步记录图像与关节读数。相机固定在同一个安装 link 上。

确认 follower 串口、robot ID、有效关节标定 JSON、URDF 关节映射及 `--fk-frame`。基线缺少关节文件时仍允许使用近似角度；不要将这种 run 用于正式外参。`capture` 会关闭力矩，启动前告知并确保有支撑。

用已拟合内参及畸变构造实际命令，并在运行前检查 `capture --help`；不要执行包含未核对默认串口／link 的示例。腕部求解后的离线命令为：

```bash
bash handeye.sh solve --run runs/wrist-001 --intrinsics-from-fit --use-fitted-distortion
```

这里假设该真实 run 已有与当前模式匹配的 `intrinsics.json`。如果复用预先拟合文件，需要核对相机标识与分辨率；也可按 CLI 传入四项内参及 `--dist-coeffs`。

采用 `T_parent_child` 记法，固定板满足：

`T_base_board = T_base_link(i) @ T_link_wrist_camera @ T_wrist_camera_board(i)`。

检查这个量在各姿态间的稳定性、留一法稳定性及独立姿态。沿用基线阈值只作诊断，不把 `good` verdict 等同于毫米级真机精度保证。

## 桌边外参：需要补充实现

附带基线没有桌边 eye-to-hand 求解命令，不能宣称已完成。对当前双相机布局，可优先复用同一块固定板，避免让 SO101 夹持这块大板：

1. 腕部外参已验证后，用 FK 和腕部看到的板估计 `T_base_board`，用多个静止姿态核对一致性。
2. 桌边相机以自身 `K/D` 估计 `T_desk_camera_board`。
3. 求 `T_base_desk_camera = T_base_board @ inverse(T_desk_camera_board)`。

两路观察期间板与底座关系保持不变。先用已知真值的合成变换验证这个新增流程，再用独立真实点／姿态检验。误差会继承腕部外参和 FK 的误差，需要一起报告。

若板在底座系中的位姿已经独立测量，可直接使用该已知位姿代替腕部估计；若改用板固定末端的 eye-to-hand 数据，要按对应方程和 API 坐标方向重新验证，不能仅反转腕部输出矩阵就作为桌边外参。

## 输出和当前状态

保留原图、检测角点／覆盖图、板配置、相机模式、时间戳与关节／FK、版本和求解输出。基线内参在 `intrinsics.json`，腕部结果在 `solve.json`；桌边结果应显式标注 `T_base_desk_camera` 的含义。

保留 `synthetic` 来源标记。用户询问进度时先查当前 artifacts 和新 run，报告证据及尚缺步骤；不要把本技能创建时的记录说成实时硬件状态。
