---
name: git-proxy
description: "Git 网络代理管理工具。触发词：'git代理'、'切换代理'、'设置git代理'、'git network'、'取消代理'、'socks代理'。用于设置、取消、查看 Git HTTP/HTTPS/SOCKS5 代理，自动检测系统代理配置。"
argument-hint: "[on|off|status|toggle|socks]"
---

# Git 代理管理

管理 Git 的 HTTP/HTTPS/SOCKS5 网络代理设置，自动检测系统代理配置。

## 参数说明

| 参数 | 行为 |
|------|------|
| `on` | 设置代理（自动检测 HTTP/SOCKS） |
| `off` | 取消代理 |
| `status` | 查看当前代理状态 |
| `toggle` | 切换代理状态（开↔关） |
| `socks` | 强制使用 SOCKS5 代理 |
| 无参数 | 显示当前状态并询问操作 |

## 使用示例

```
/git-proxy on      # 开启代理（自动检测）
/git-proxy off     # 关闭代理
/git-proxy status  # 查看状态
/git-proxy toggle  # 切换状态
/git-proxy socks   # 强制使用 SOCKS5
/git-proxy         # 交互式操作
```

## 执行流程

### 1. 检测系统代理（按优先级）

**检测顺序：**

1. **环境变量**（最优先）
   - `http_proxy` / `https_proxy` → HTTP 代理
   - `ALL_PROXY` / `all_proxy` → SOCKS 代理

2. **macOS 网络设置**
   - HTTP: `networksetup -getwebproxy Wi-Fi`
   - HTTPS: `networksetup -getsecurewebproxy Wi-Fi`
   - SOCKS: `networksetup -getsocksfirewallproxy Wi-Fi`

3. **常见代理端口**（默认回退）
   - ClashX: HTTP 7890 / SOCKS 7891
   - Surge: HTTP 6152 / SOCKS 6153
   - Charles: HTTP 8888
   - 通用: HTTP 8001 / SOCKS 1081

### 2. 代理类型选择逻辑

```
如果指定 socks 参数 → 使用 SOCKS5
如果环境变量有 ALL_PROXY → 使用 SOCKS5
如果检测到 SOCKS 代理且无 HTTP → 使用 SOCKS5
否则 → 使用 HTTP
```

### 3. 执行操作

#### 设置代理 (on / socks)

```bash
# HTTP 代理
git config --global http.proxy http://127.0.0.1:8001
git config --global https.proxy http://127.0.0.1:8001

# SOCKS5 代理（更快，推荐）
git config --global http.proxy socks5://127.0.0.1:1081
git config --global https.proxy socks5://127.0.0.1:1081
```

#### 取消代理 (off)

```bash
git config --global --unset http.proxy
git config --global --unset https.proxy
```

#### 查看状态 (status)

```bash
git config --global --get http.proxy
git config --global --get https.proxy
```

## 输出格式

```
🔍 Git 代理状态
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
当前状态: ✅ 已开启 (SOCKS5)
HTTP 代理: socks5://127.0.0.1:1081
HTTPS 代理: socks5://127.0.0.1:1081
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

检测到的系统代理:
  • HTTP: 127.0.0.1:8001
  • SOCKS: 127.0.0.1:1081
  • 来源: macOS 网络设置
```

## SOCKS5 vs HTTP 代理

| 特性 | HTTP 代理 | SOCKS5 代理 |
|------|-----------|-------------|
| 性能 | 较慢 | 更快 |
| 兼容性 | 最好 | 好 |
| 适用场景 | 通用 | 推荐用于 Git |

**推荐**: 如果系统同时有 HTTP 和 SOCKS 代理，优先使用 SOCKS5（速度更快）。

## 注意事项

1. **认证代理**: 如需用户名密码，格式为 `socks5://user:pass@host:port`
2. **仅影响 Git**: 此设置仅影响 Git 的 HTTP/HTTPS 请求
3. **SSH 协议**: SSH 方式的 remote 不受影响，需配置 `~/.ssh/config`
4. **临时使用**: 单次命令可加 `-c` 参数，如 `git -c http.proxy=socks5://host:port clone ...`
