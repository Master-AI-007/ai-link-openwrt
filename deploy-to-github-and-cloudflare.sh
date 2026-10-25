#!/usr/bin/env bash
set -e

echo "============================================================"
echo "  AI-LINK v1.0.0 官方网站 (Cloudflare) & GitHub 一键发布助手"
echo "============================================================"

if [ -n "$1" ]; then
  GH_REPO="$1"
  echo "[1/2] 正在初始化 Git 并推送到 GitHub: $GH_REPO ..."
  git init
  git branch -M main
  git add .
  git commit -m "release: AI-LINK v1.0.0 Official Release & Website" || true
  git remote remove origin 2>/dev/null || true
  git remote add origin "$GH_REPO"
  git push -u origin main
  echo "✅ GitHub 推送完成！"
else
  echo "💡 提示：如需自动推送到 GitHub，请传入您的仓库地址，例如："
  echo "   ./deploy-to-github-and-cloudflare.sh https://github.com/<用户名>/ai-link-openwrt.git"
fi

echo ""
echo "[2/2] 正在通过 Wrangler 部署官网至 Cloudflare Pages ..."
if command -v npx >/dev/null 2>&1; then
  npx wrangler pages deploy ./public --project-name=ai-link-official
  echo "✅ Cloudflare Pages 部署完成！"
else
  echo "⚠️ 未检测到 npx，您可直接将 public/ 目录上传至 Cloudflare Pages 控制台。"
fi
