# NetSurf Switch 浏览器 — 独立 NSP 测试版

此项目把 etonedemid 的 **NetSurf Switch v0.2.0 移植版**打包为完整的 NSP 应用。
浏览器内核来自上游；本次新增的是独立应用封装、NSO 转换和验证流程。
它不是调用系统 Web Applet 的 BrowseNX，也不是桌面 Chromium 的移植。

## 下载

[下载完整 NSP 测试版](https://github.com/zqzhuhai-commits/BrowseNX-Switch/releases/tag/v0.2.0-nsp1)。
发布工作流将仓库的三个传输分段合并为 **一个 NSP**。
如果 Release 尚在生成，可以下载仓库并运行 `python3 scripts/assemble_nsp.py`；
输出在 `dist/NetSurf-Switch-0.2.0-experimental.nsp`。传输分段本身不能安装。

## 安装与使用

1. 将 `NetSurf-Switch-0.2.0-experimental.nsp` 复制到 Switch SD 卡或通过 USB 传给安装器。
2. 在支持自制 NSP 的 Atmosphère 环境中，使用 DBI 等安装器安装。
3. 从 HOME 菜单启动“NetSurf 浏览器”。**无需另外放置 NRO，也无需 hbmenu。**
4. 点地址栏输入网址。确保 Switch 已联网、日期时间正确。

这是未经过实机测试的版本。制作目标为用户现有的大气层 Switch；
**没有验证系统 22.5.0 的安装、启动或网页兼容性。**
自制 NSP 不具备任天堂签名，运行环境需支持安装及启动此类应用。
这不是零售原版系统可运行的官方软件。

## 操作

| 操作 | 输入 |
|---|---|
| 指针 | 左摇杆或触屏 |
| 点击 | A / ZR |
| 滚动 | 右摇杆 |
| 翻页 | L / R |
| 返回 / 取消 | B（具体行为取决于当前界面） |
| 输入网址或表单 | 点地址栏或输入框，弹出系统键盘 |
| 退出 | + |

上游支持书签、HTTPS、JavaScript、图片和部分音视频。
现代网站支持不等同于 Chrome：MSE / HLS / DASH、WebGL 等仍有上游限制；
不能保证 YouTube、复杂登录网页或 DRM 视频运行。
界面沿用上游英文，HOME 图标名称为中文；CJK 字形覆盖需实机检查。

## 数据与排错

浏览器会创建 `sdmc:/switch/netsurf/`，保存设置、书签和日志；
这些是运行时生成的数据，安装前无需复制资源文件。

- 设置：`sdmc:/switch/netsurf/Choices`
- 书签：`sdmc:/switch/netsurf/Hotlist`
- 日志：`sdmc:/switch/netsurf/stderr.log`

若启动或打开网站失败，请保留错误码、触发网址、日志和实际系统 / Atmosphère 版本。
若图标启动前就失败，优先检查自制 NSP 运行环境；若出现浏览器日志，再检查应用运行问题。

## 打包原理与验证边界

程序来自固定的上游 NRO。libnx 的同一启动代码支持 NSO 和 NRO 入口。
本项目保持三个段的虚拟地址、MOD0、动态重定位和 BSS 布局，重建一个段级 ELF，
使用 switch-tools `elf2nso` 转为 NSO。原 NRO 的 RomFS 被提取并装入 Program NCA；
libnx 在 NSO 模式下会从当前已安装应用挂载 RomFS。

NPDM 使用 Application 模式、39 位地址空间、4 MiB 主线程栈；
从上游模板保留自制程序所需的服务和系统调用权限。
Title ID：`01f0b05e20261000`。如果已有同 ID 软件，不应覆盖安装。

已完成：NSO 三段哈希检查、解压段字节与原 NRO 一致检查、
NCA 文件哈希 / 内容哈希检查、77 个 RomFS 资源逐个比对、控制信息和 CNMT 关联检查。
完整性验证不能替代安装、网络、触屏、软键盘、视频和退出的实机测试。
安装器中显示自制软件签名状态属于此包的预期属性。

## 重打包

Linux 依赖：`gcc`、`make`、`git`、`curl`、`python3`。

```bash
bash build.sh /absolute/path/to/prod.keys
```

只读取 `header_key` 和 `key_area_key_application_00`，不使用 `title.keys`。
密钥文件不属于源码或发布包。不要提交密钥或原始打包日志。
`scripts/stage_nsp.py` 会拒绝与固定 SHA-256 不符的 NRO。
`build.sh` 是重打包流程，不重新编译整个浏览器内核。
重编译浏览器请参见附带上游源码中的 `tools-switch/Dockerfile` 和构建脚本。

## 来源与许可

- NetSurf Switch：[etonedemid/netsurf-switch](https://github.com/etonedemid/netsurf-switch)，
  `v0.2.0` / `29d910fc28e6e0c816eea4a86bae4e40f2ac699d`。
- 浏览器原始 NRO SHA-256：`adc407ceab4e17347230f71d13c87969767e65015fd163021d548ce9f35456a9`。
- 打包工具：[rlaphoenix/hacBrewPack](https://github.com/rlaphoenix/hacBrewPack)，GPL v2。
- 转换工具：[switchbrew/switch-tools](https://github.com/switchbrew/switch-tools)。
- 压缩库：[lz4/lz4](https://github.com/lz4/lz4)，BSD 2-Clause。
- 校验工具：[SciresM/hactool](https://github.com/SciresM/hactool)。
- 运行时机制参考：[switchbrew/libnx](https://github.com/switchbrew/libnx)。

本项目新增脚本按 GPL v2 分发。`vendor/netsurf-switch` 子模块固定浏览器源码的对应提交，
使用 `git clone --recurse-submodules` 获取。各组件、字体及第三方依赖保留原许可；
依赖构建脚本和上游来源见子模块。
本项目不包含任天堂 SDK、系统浏览器二进制或用户密钥。
