# 参数用途与使用边界

## 向用户解释

- 内参 `fx, fy, cx, cy`：描述像素与相机观察方向的关系，单位为像素；通常组成 3×3 矩阵 `K`。
- 畸变 `D`：修正镜头导致的径向／切向变形。五项模型顺序为 `k1, k2, p1, p2, k3`；OpenCV rational 八项为 `k1, k2, p1, p2, k3, k4, k5, k6`。按实际模型完整读取，不能截断八项，也不能把 rational 当成 fisheye 模型。
- 外参 `R, t`：描述相机与另一个坐标系的位置和朝向，常写成 4×4 齐次变换。腕部相机相对安装 link 的变换通常固定，相对底座的变换随关节姿态改变；桌边相机固定时相对底座的变换通常固定。
- 电机标定文件：把编码器读数映射为正确关节状态，影响运动学和外参，但不是镜头参数。

可举例“点选桌面位置，让机械臂移动到那里”。单个 RGB 像素只能确定一条观察射线；还需已知桌面平面、深度或有几何约束的多视角信息，才能获得空间点。仅标定两台普通 USB 相机，不会自动得到任意物体的准确三维位置。

## LeRobot 是否必须使用

常见 ACT 图像模仿学习直接输入相机图像和关节状态，通常不要求把 `K/D/外参` 填入策略配置。保存这些参数不会自动提高已有模型表现。

参数主要用于几何定位、点选抓取、视觉伺服、相机／机械臂坐标转换及多视角空间融合。先查目标策略和处理器是否实际消费标定信息，再决定如何接入；避免凭空添加策略不支持的字段。

对已训练模型，增加去畸变、裁剪或图像旋转会改变输入分布；不要擅自只修改推理端。采集、训练和推理的图像处理需要一致。

## 保存和读取

- 每路内参同时保存相机标识、实际 `width/height`、`K` 或四项内参、`D` 和模型、采集时镜头设置及重投影误差。
- 使用 `T_parent_child` 表示把 child 中的点变到 parent：`p_parent = T_parent_child @ p_child`。不要仅写含糊的“从 A 到 B”。
- 位移为米；矩阵中的旋转为 3×3 正交旋转。若另存四元数，要写清 `wxyz` 或 `xyzw`；不得混用。
- 当前上游 `solve.json` 的 `gripper_to_camera_optical` 表示相机在选定末端 link 坐标系中的位姿，等价于 `T_link_camera`。字段名不代表可以忽略 `--fk-frame` 的实际选择。
- 末端相机在底座中的位姿：`T_base_camera(q) = T_base_link(q) @ T_link_camera`。
- link 由实际刚性安装决定。若相机跟随腕部俯仰但不跟随滚转，应核对俯仰之后、滚转之前的 link；不能因安装在夹爪附近就默认选 gripper。
- FK 使用图像时刻的实测关节角，不用目标角替代。若沿用某项目的 `q=(Present_Position-(range_min+range_max)/2)*2π/4095`，先确认与该项目 LeRobot/URDF 的约定一致；读数已包含硬件 homing offset 时不能重复扣除。寄存器匹配不等于已独立验证物理零位。

## 误差口径

内参重投影误差用像素；手眼的新姿态一致性通常用毫米／度；绝对定位或抓取误差需要独立物理基准。三者不能互相换算后宣称达标。RMS 门槛也不是最大误差门槛。

固定肩肘与改变肩肘的验证应分别报告，连同样本数、范围、最大误差、模型是否冻结。桌边板面反投影的一致性可能抵消共同的基座变换误差，不测量尺量和方向对齐的绝对误差。详见 [validation-and-delivery.md](validation-and-delivery.md)。

## 原始资料

- [OpenCV 相机标定模型与坐标变换](https://docs.opencv.org/5.0/main_modules/calib.html)
- [OpenCV 镜头畸变和去畸变](https://docs.opencv.org/5.0/py_tutorials/py_calib3d/py_calibration/py_calibration.html)
- [LeRobot 官方 ACT 使用示例](https://github.com/huggingface/lerobot/blob/main/examples/tutorial/act/act_using_example.py)

版本相关的 API 和策略要求以当前代码或官方资料为准。
