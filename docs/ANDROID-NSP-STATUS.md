# Android 浏览器原生 NSP：当前状态

更新：2026-10-13。

## 已确认需求

用户要求同时满足：
- 移植 Android 浏览器，优先考虑已提供的夸克 APK。
- 保留在 Horizon / Atmosphère 中直接安装 NSP 并启动的方式。
- 改善界面与网页稳定性。
- 不以 Switchroot Android、远程串流或新的 NetSurf 修订版替代。

## 交付状态

**尚未实现 Android 浏览器的原生 Switch NSP。**
仓库既有 Release 是 NetSurf 原生封装，不是夸克或 Android 应用移植。
NetSurf 的内存与百度闪退修订已暂停；没有发布该修订版。

已完成夸克 APK 静态检查，详见 QUARK-APK-FEASIBILITY.md。
它包含 17 个 DEX 和 65 个 ARM64 原生库，内核和界面依赖 Android API。
只打包 NSP 或映射 ELF，不能执行主 Activity 的 Java/Dex 逻辑，
也不能提供 Android 的窗口、图形、生命周期、网络服务和运行时接口。

## 额外核查的现有方案

### Viridite

来源：https://github.com/Viridite/Viridite

该项目适配部分 Android NDK 游戏；其实现用假的 JavaVM/JNI 回调替代少量 Java 辅助接口。
项目说明明确表示不运行 Dalvik 字节码，当前兼容目标主要是特定原生游戏。
这不是可以执行夸克 17 个 DEX 的 Android 运行环境。
没有将其声称为支持夸克，也未生成名为夸克但实际不能运行应用的安装包。

### Chromium NX

来源：https://github.com/shodowlo/chromium-nx

源码 README 描述它通过 LKL 和 Linux 系统接口适配运行 Debian ARM64 的 chromium-shell。
这是一条原生系统中运行现代浏览器的实验路线，但它不是 Android APK 的移植，
也不包含夸克 Android 的应用框架和原界面，因此不作为用户指定路线的交付。

## 尚缺的核心实现

继续原生 Android 浏览器路线，需要：
1. 可执行相关 DEX 的运行时，或从可重编译应用源码重写这些逻辑。
2. Java Framework、JNI、Android 原生库和图形/输入服务的实际适配。
3. 浏览器内核线程、网络、缓存、内存回收及进程模型适配。
4. 针对该应用进行 Switch 实机启动、网页加载与内存测试。
5. 前述运行能力完成后，再进行 NSP 封装与安装验证。

以上不由扩展名转换或 NSP 打包自动完成。目前这些实现尚未完成，
所以当前不能交付满足两项要求的可运行夸克 NSP。
