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

USB 重插后重新核对物理身份、稳定路径和真实画面。相同相机、镜头和模式未变时，不能仅因 videoN 编号改变就宣告内参失效；安装位置变化则需复核相应外参。预览页返回 HTTP 成功或显示旧照片不等于实时相机已恢复。

附带上游基线有两个具体限制，采集前必须处理：

1. `Camera` 硬编码请求 1280×720，未暴露分辨率 CLI 参数。先按真实 LeRobot 相机模式补充分辨率选择，并记录实际获得的图像尺寸，或换用项目已有的匹配采集器。不要将 720p 结果直接套到 VGA。
2. `capture` 同时连接机械臂，而且要求已知 `fx/fy/cx/cy`。它不适合从零采集初始内参。先提供**只打开相机、不打开串口**的图像采集／导入入口，保存多角度、不同距离及覆盖画面不同区域的清晰图像。可使用 SDK `solve_intrinsics(images, board)`，或经过检查的现有离线拟合入口。当前基线 SDK 要求至少 5 个有效视角。

每台相机独立拟合 `K/D`；图像尺寸要一致。检查覆盖范围、重投影误差及异常视角，再用未参与拟合的图像验证。低误差本身不能证明板尺寸、实际尺度或焦距一定正确。

项目若已有纯相机采集器及内参细化工具，优先检查并复用，不能将本节的上游基线限制误报成项目当前未完成。记录它们的实际源文件与版本；本技能未附带这些项目扩展。细化时检测器也可能使用初始去畸变模型，应同时冻结检测设置和 K/D，在全新图像上验证，避免用验证结果反复调模型。

## 腕部外参

固定板相对机械臂底座，保持采集期间不动；移动机械臂获取绕不同轴旋转的姿态，在静止时同步记录图像与关节读数。相机固定在同一个安装 link 上。

先按真实机械运动确认安装 link：分别观察俯仰、滚转和夹爪张合时，相机本体是否跟随。SO101 不能只按“六轴”名称推断相机 FK 需要的关节数；夹爪开合也不一定是相机位姿链的一部分。

确认 follower 串口、robot ID、有效关节标定 JSON、URDF 关节映射及 `--fk-frame`。基线缺少关节文件时仍允许使用近似角度；不要将这种 run 用于正式外参。`capture` 会关闭力矩，启动前告知并确保有支撑。

用已拟合内参及畸变构造实际命令，并在运行前检查 `capture --help`；不要执行包含未核对默认串口／link 的示例。腕部求解后的离线命令为：

```bash
bash handeye.sh solve --run runs/wrist-001 --intrinsics-from-fit --use-fitted-distortion
```

这里假设该真实 run 已有与当前模式匹配的 `intrinsics.json`。如果复用预先拟合文件，需要核对相机标识与分辨率；也可按 CLI 传入四项内参及 `--dist-coeffs`。

采用 `T_parent_child` 记法，固定板满足：

`T_base_board = T_base_link(i) @ T_link_wrist_camera @ T_wrist_camera_board(i)`。

检查这个量在各姿态间的稳定性、留一法稳定性及独立姿态。沿用基线阈值只作诊断，不把 `good` verdict 等同于毫米级真机精度保证。

求解方法的主次应在独立验证前确定。冻结 `X=T_link_camera` 和训练得到的 `Y=T_base_board`，再记录未参与拟合的新姿态；验证时不重新估计 Y 来吸收偏差。若拍视频，需同步记录关节与帧时间戳，并只从停稳窗口选择清晰且姿态有区别的帧；相邻视频帧数不能当作独立姿态数。完整验收见 [validation-and-delivery.md](validation-and-delivery.md)。

通电自动采集与上述上游被动采集是不同入口。使用项目已有自动控制器前，按 [motor-held-capture.md](motor-held-capture.md) 核对原位保持、有限试动、异常停止和单独释放；不因上游示例的默认行为而改变现场力矩状态。

## 桌边外参：优先复用项目实现

附带基线没有桌边 eye-to-hand 求解命令，不能宣称已完成。对当前双相机布局，可优先复用同一块固定板，避免让 SO101 夹持这块大板：

1. 腕部外参已验证后，用 FK 和腕部看到的板估计 `T_base_board`，用多个静止姿态核对一致性。
2. 桌边相机以自身 `K/D` 估计 `T_desk_camera_board`。
3. 求 `T_base_desk_camera = T_base_board @ inverse(T_desk_camera_board)`。

两路观察期间板与底座关系保持不变。先用已知真值的合成变换验证这个新增流程，再用独立真实点／姿态检验。误差会继承腕部外参和 FK 的误差，需要一起报告。

若板在底座系中的位姿已经独立测量，可直接使用该已知位姿代替腕部估计；若改用板固定末端的 eye-to-hand 数据，要按对应方程和 API 坐标方向重新验证，不能仅反转腕部输出矩阵就作为桌边外参。

使用尺量建立独立基准时：

- 确认量的是目标 follower 的底座；在照片／模型上定义具体孔心和有方向的坐标轴，不能混用 leader 的坐标。
- 记录板原点、X/Y 正方向、带符号读数、毫米／厘米及高度基准。高度量底座指定参考面到板印刷面，不凭“同一张桌子”设为零。
- CAD 中的孔距或 Q→R 等偏移定义在底座局部坐标系。先求底座相对板坐标的旋转，再将偏移旋转后相加；不能直接当作板坐标 X/Y。一个锚点加现场方向只给出带尺量／对齐不确定度的基准。
- 模型推算的其他孔位不是独立测量点。像素到基座三维点还需要实际参考平面或物体高度，不能把印刷面自动当成裸桌面。

记录测量订正历史，但只把最终已确认、对应目标从臂的数据导出为当前参数。桌边绝对精度需另测未参与设定的物理点。

## 输出和当前状态

保留原图、检测角点／覆盖图、板配置、相机模式、时间戳与关节／FK、版本和求解输出。基线内参在 `intrinsics.json`，腕部结果在 `solve.json`；桌边结果应显式标注 `T_base_desk_camera` 的含义。

保留 `synthetic` 来源标记。用户询问进度时先查当前 artifacts 和新 run，报告证据及尚缺步骤；不要把本技能创建时的记录说成实时硬件状态。

整理轻量参数包时按 [validation-and-delivery.md](validation-and-delivery.md) 保存配置、模型、验证和哈希清单；历史 ZIP 保留原样。最后一次电机状态必须带时间，软件关闭力矩与物理断电分别记录。
