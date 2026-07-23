---
id: Q077
source: mianshiya
category: MCP 与协议
title: 什么是 Google ADK？
generated: 2026-07-23T15:41:19.805711
---

# 什么是 Google ADK？

> 来源: 面试鸭题库 | 分类: MCP 与协议

Google ADK（Android Debug Bridge）这个说法其实是个常⻅的误解。你可能想问的是 ADB，也就是 Android
Debug Bridge。
ADB 是 Android 开发⾥最基础的调试⼯具，它让你能在电脑上通过命令⾏跟⼿机通信。开发或者测试时，装应⽤、看
⽇志、执⾏ shell 命令都靠它。
它由三部分组成： 1）运⾏在电脑上的 adb 客户端 2）运⾏在⼿机上的 adbd 服务 3）中间通过 USB 或⽹络连接
⽐如你想把⼀个 APK 安装到设备，直接敲：
adb install app-debug.apk
或者进 shell 看⽂件：
adb shell
ls /sdcard/
还有⼀种情况是 ADK，全称是 Android Open Accessory Development Kit，这是 Google 提供的⼀套让 Android 设备
与外部硬件配件通信的⽅案，基于 USB 主机模式。像⼀些⼯业设备、外接传感器通过 USB 连⼿机，会⽤到它。不过
实际项⽬中⽤得不多，⼤部分场景被蓝⽛或 Wi-Fi 取代了。
简单说，⽇常开发提到的“ADK”九成都是⼝误，真正要⽤的是 ADB。遇到真配件通信需求，才会碰得到 ADK 那套协
议和权限声明。

---