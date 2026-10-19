# LeRobot 相机标定技能

面向 Codex 的中文技能，用于 LeRobot／SO-ARM101 腕部和固定 USB 相机的标定准备、参数解释、AprilGrid 检测及结果验证。

## 包含内容

- 相机内参、镜头畸变、手眼外参的含义与使用边界。
- SO101 试用环境安装、AprilGrid 适配、腕部手眼求解和离线检查。
- 一块实测 AprilGrid 的示例配置与参考照片：黑框 49 mm、白间隙 12 mm。
- 安装与启动脚本、固定版本依赖列表、两份兼容补丁和 FK 用 URDF。
- 当前基线尚缺环节的接入说明，以及真实采集与验证要求。
- 冻结后独立验证、肩肘覆盖、桌边从臂尺量基准、完整参数包及误差口径。
- 项目已有通电采集器的有限试动、跟随失败、正常释放与用户要求断电时的处理。

技能入口：[SKILL.md](skills/lerobot-camera-calibration/SKILL.md)。

## 安装技能

将 `skills/lerobot-camera-calibration` 整个文件夹放入 `${CODEX_HOME:-$HOME/.codex}/skills/`。已有同名技能时先比较内容，保留自己的项目记录。

调用示例：

```text
用 $lerobot-camera-calibration 解释内外参用途
用 $lerobot-camera-calibration 为我的 SO-ARM101 准备双相机标定
```

技能支持自动按相关任务匹配。具体安装目录与发现机制以所用 Codex 环境为准。

## 运行试用基线

把技能中的 `assets/trial/` 内容复制到独立工作目录后运行 `bash setup_handeye.sh`。不要把相机采集数据写入已安装技能目录。

基线已在 Linux x86_64、Python 3.12 上验证。首次安装会下载固定提交的上游源码和依赖；仓库未包含虚拟环境、上游完整仓库或大型离线依赖包。详细操作与 API 限制见 [workflow.md](skills/lerobot-camera-calibration/references/workflow.md)。

安装后可运行不访问相机或串口的检查，每次使用新的输出目录：

```bash
mkdir -p artifacts
.venv/bin/python verify_aprilgrid.py
bash handeye.sh selftest --board-config configs/user-aprilgrid.json \
  --pixels-per-square 196 --distance 1.4 --out runs/offline-check-001
bash handeye.sh intrinsics --run runs/offline-check-001
bash handeye.sh solve --run runs/offline-check-001 --intrinsics-from-fit --use-fitted-distortion
```

## 实现状态

AprilGrid 检测、SDK 报告接口兼容及合成图像上的内参／腕部手眼流程已验证。**未附带真实相机的标定参数**；合成误差不代表真机精度。

当前上游采集器要求预先提供内参、同时连接机械臂，并硬编码请求 1280×720。初始内参所需的纯相机采集入口、分辨率选择及桌边外参流程仍需按文档补充接入，或使用项目现有的可靠工具。

真实使用前核对相机模式、关节标定和安装 link。上游 `capture` 会关闭电机力矩，启动前须确保机械臂得到支撑。示例板参数不能直接用于其他实物板。

本次补充的 [验证与交付说明](skills/lerobot-camera-calibration/references/validation-and-delivery.md) 包含匿名实测案例：同一手眼模型在固定肩肘新姿态上 RMS 约 3.07 mm，另拍改变肩肘的新姿态后约 8.66 mm。这说明必须写清验证范围，不能将局部一致性视作全工作区绝对抓取精度；这些数值不是可复用的设备参数。

[通电采集参考](skills/lerobot-camera-calibration/references/motor-held-capture.md) 用于评估和使用项目已有实现。本仓库仍未附带完整自动运动控制器；一次低速回程诊断成功不代表随后往返轨迹能通过跟随检查，也不应把未完成的运动诊断作为新标定结果。

## 来源

- [Cyberwave SO101](https://github.com/cyberwave-os/cyberwave-edge-so101)，基线提交 `66687450bce0fb4b742526e18294d33a53485175`。相关补丁包含上游代码上下文，保留其 [MIT 声明](third-party/Cyberwave-MIT.txt)。
- URDF 来源及校验值见 [urdf-source.json](skills/lerobot-camera-calibration/assets/trial/assets/urdf-source.json)。
- 相机几何及 LeRobot 官方资料见技能的 [参数说明](skills/lerobot-camera-calibration/references/parameters.md)。

上传版本不包含个人设备连接记录；参考照片已去除 EXIF／XMP 等元数据，保留原始像素。
