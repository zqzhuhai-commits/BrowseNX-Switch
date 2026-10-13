# 夸克 Android APK 到 Switch 的可行性检查

检查日期：2026-10-13。仅做静态检查，未在 Switch 或 Android 设备上运行。

## 结论

用户提供的 APK 是完整 Android 应用。仅有这个 APK，不能直接重打包为
在 Horizon / Atmosphère 下运行的独立 NSP。
真正保留夸克原版界面及网页内核的可行路线是：在 Switch 上启动 Switchroot Android，
然后安装原 APK。这改变了“从大气层 HOME 菜单直接运行 NSP”的使用方式。

在同为 ARM64 的 CPU 上，操作系统运行接口仍不同。移植这里的 Android 应用至少涉及
DEX / ART、Java Framework、JNI、Android 原生库、窗口、输入和图形接口。
NSP 封装不会提供这些运行环境。此项目没有可直接使用的完整 Android 兼容运行层。
仅替换扩展名、加入壳程序或提取 `libwebviewuc.so`，不能解决上述依赖。

## 对提供 APK 的实测静态信息

| 项目 | 值 |
|---|---|
| 应用名称 | 夸克 |
| 包名 | `com.quark.browser` |
| 版本 | `10.18.6.1161` |
| versionCode | `1161` |
| 最低 Android API | `23`（Android 6.0） |
| 目标 Android API | `30` |
| 主 Activity | `com.ucpro.MainActivity` |
| 文件大小 | `186706541` 字节，约 178.1 MiB |
| DEX 文件数量 | 17 |
| 原生 `.so` 数量 | 65 |
| 原生 ABI | 仅 `arm64-v8a` |
| SHA-256 | `34f8c619a429562a9f54628d913c231cbcc3e1e45d09af26f5eed0c68509db70` |

下载来源为用户提供的 `umcdn.uc.cn` APK 链接。没有将 APK 或提取出的商业库上传至此仓库。
这些数据反映包结构；**APK 体积不等于运行内存，不能据此声称夸克更省内存。**

### 大型原生组件

| 文件 | 解压后大小（字节） |
|---|---:|
| `libapp.so` | 67967240 |
| `libwebviewuc.so` | 64023192 |
| `libflutter.so` | 11233672 |
| `libunet.so` | 8618360 |

`libwebviewuc.so` 的 ELF 动态依赖包含：
`libandroid.so`、`libdl.so`、`libm.so`、`liblog.so`、`libjnigraphics.so`、`libc.so`。
其导入和导出还包含 `ANativeWindow_fromSurface`、Android 日志接口以及
`Java_com_uc_webview_*` JNI 方法，证明内核的现有二进制依赖 Android。

`libflutter.so` 依赖 Android 原生库及 `libEGL.so` / `libGLESv2.so`。
APK 中的 Flutter 组件不能仅提取后当作 Switch 原生界面运行。
此 APK 不提供完整应用、UC 内核和 Android Flutter 引擎的对应可重编译源码。

## 两条路线的区别

| 要求 | Switchroot Android + 原夸克 APK | 原生 Switch NSP |
|---|---|---|
| 保留原夸克界面和实现 | 使用原应用；仍需实机兼容测试 | 无法靠此 APK 直接实现 |
| 从大气层 HOME 菜单直接启动浏览器 | 需要切换 / 重启进入 Android | 可以 |
| Android 运行依赖 | 由 Android 系统提供 | 需要移植或替代 |
| 现有 APK 是否足够 | 足够安装，但不保证实机运行正常 | 不足以完成原生移植 |
| 可能的替代方案 | 用 Android 平板模式运行 APK | 独立原生 UI + 可移植开源内核 |

Switchroot 官方列出 Android 14 / 15、平板模式和 Android TV 模式，覆盖 V1、V2、Lite、OLED。
对手机浏览器界面，平板模式更接近其目标环境；这是基于输入方式作出的选择建议，
不是本 APK 已通过 Switch 实测的结论。
具体安装仍需核对设备型号、启动方式和 SD 卡情况，不应为了测试 APK 擅自分区或刷机。

## 原 NetSurf 版本的百度闪退

用户报告：内存占用高，打开百度闪退。
静态检查发现 libnx 默认堆会预留几乎全部可用应用内存；上游默认启用 JavaScript，
并发资源加载和内存缓存也可以进一步压低。
**没有异常报告或实机调试，尚不能把百度闪退确认为 OOM，也不能确认换夸克会修复。**
轻量修订工作在用户转向优先检查夸克 APK 后暂停；未发布未经完成验证的新 NetSurf 包。

## 官方资料

- Android 平台结构：<https://developer.android.com/guide/platform>
- Switchroot Android 14 / 15：<https://wiki.switchroot.org/wiki/android/android-14-15>
- 官方平板设备入口：<https://wiki.lineageos.org/devices/nx_tab/>
- libnx 默认堆实现：<https://github.com/switchbrew/libnx/blob/master/nx/source/runtime/init.c>

下一步需要确定是否接受切换到 Android 系统。
若继续坚持独立 NSP，则实现范围应为原生浏览器与 UI 的开发，不能将本 APK 的封装称为完成移植。
