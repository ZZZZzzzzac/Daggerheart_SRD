/* 内置 GitHub Token（可选）
 * 复制本文件为 config.token.js，填入你的 fine-grained PAT
 * Fine-grained PAT 设置：https://github.com/settings/tokens?type=beta
 * 权限：只勾选 Daggerheart_SRD 仓库，选 contents:write + pull_requests:write
 *
 * 安全提醒：
 * - 此文件不入 git（已在 .gitignore），但构建后会包含在 public/ 中
 * - 如果你设置了此 token，编辑器会优先用它直接调 GitHub API
 * - 如果不设置，编辑器走服务端代理（无需前端暴露 token）
 * - 服务端代理地址：https://daggerheart.cn/SRD/api/submit-pr
 */
const BUILTIN_TOKEN = '';  // 填入你的 token，或留空走服务端代理
