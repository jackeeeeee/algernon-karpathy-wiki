#!/bin/bash
# qmd 索引重建脚本
# 用法: ./qmd-reindex.sh [wiki目录路径]

WIKI_DIR="${1:-$(dirname "$0")/../wiki}"
WIKI_DIR=$(cd "$WIKI_DIR" && pwd)

echo "重建 qmd 索引: $WIKI_DIR"

# 删除旧索引（如果存在）
rm -rf "$WIKI_DIR/../.qmd"

# 重建索引
qmd collection add "$WIKI_DIR" --name wiki

echo "索引重建完成"
