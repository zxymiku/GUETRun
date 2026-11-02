#!/usr/bin/env bash
# 生成 GitHub Release 说明：
#   1. 距离上一次 Release 的提交记录（按提交人分组）
#   2. 提交人 / 贡献者统计
#   3. 变更统计与 GitHub compare 链接
#
# 仅依赖 bash（兼容 Bash 3.2 / BusyBox ash）+ git + 常见 coreutils，
# 可直接在 GitHub Actions 的 ubuntu runner 上运行。
set -eu

FROM=""
TO="HEAD"
VERSION=""
TAG=""
REPO="${GITHUB_REPOSITORY:-}"
OUTPUT=""

usage() {
  cat <<'EOF'
用法：
  generate-release-notes.sh --version <版本> --tag <标签> --repo <owner/repo> \
      --output <输出文件> [--from <上次发布标签>] [--to <提交或分支>]

参数：
  --from     上一次 Release 的标签；为空或不存在时按首次发布处理
  --to       本次发布的提交引用，默认 HEAD
  --version  版本号，例如 2.0.1
  --tag      本次 Release 标签，默认 v<版本号>
  --repo     GitHub 仓库，例如 owner/repo；默认读取 GITHUB_REPOSITORY
  --output   生成的 Markdown 文件路径，必填
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --from) FROM="${2:-}"; shift 2 ;;
    --to) TO="${2:-}"; shift 2 ;;
    --version) VERSION="${2:-}"; shift 2 ;;
    --tag) TAG="${2:-}"; shift 2 ;;
    --repo) REPO="${2:-}"; shift 2 ;;
    --output) OUTPUT="${2:-}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "未知参数：$1" >&2; usage >&2; exit 2 ;;
  esac
done

if [ -z "$VERSION" ]; then
  echo "缺少 --version" >&2
  exit 2
fi
if [ -z "$TAG" ]; then
  TAG="v${VERSION}"
fi
if [ -z "$REPO" ]; then
  echo "缺少 --repo（或环境变量 GITHUB_REPOSITORY）" >&2
  exit 2
fi
if [ -z "$OUTPUT" ]; then
  echo "缺少 --output" >&2
  exit 2
fi

SERVER_URL="${GITHUB_SERVER_URL:-https://github.com}"
REPO_URL="${SERVER_URL}/${REPO}"

git rev-parse -q --verify "${TO}^{commit}" >/dev/null || {
  echo "找不到提交引用：$TO" >&2
  exit 1
}

# 校验上次发布标签：不存在或不在当前历史中时退化为“首次发布”。
if [ -n "$FROM" ]; then
  if ! git rev-parse -q --verify "${FROM}^{commit}" >/dev/null; then
    echo "warning: 找不到上次发布标签 '$FROM'，按首次发布处理" >&2
    FROM=""
  elif ! git merge-base --is-ancestor "$FROM" "$TO" 2>/dev/null; then
    echo "warning: 标签 '$FROM' 不是 '$TO' 的祖先，按首次发布处理" >&2
    FROM=""
  fi
fi

if [ -n "$FROM" ]; then
  LOG_RANGE="${FROM}..${TO}"
  RANGE_TEXT="\`${FROM}\` → \`${TAG}\`"
  COMPARE_URL="${REPO_URL}/compare/${FROM}...${TAG}"
else
  LOG_RANGE="${TO}"
  RANGE_TEXT="首次发布 · 全部历史"
  COMPARE_URL=""
fi

COMMIT_COUNT=$(git rev-list --count --no-merges "$LOG_RANGE")

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT
COMMITS_FILE="$TMP_DIR/commits.tsv"
AUTHORS_FILE="$TMP_DIR/authors.txt"
: > "$COMMITS_FILE"

US=$(printf '\037')
TAB=$(printf '\t')

# 每条提交一行；字段以 US（0x1f）分隔。提交标题取 %s（单行），
# Co-authored-by 通过 trailers 提取，避免解析多行 body。
git log --no-merges --pretty=format:'%H%x1f%h%x1f%an%x1f%aI%x1f%s%x1f%(trailers:key=Co-authored-by,valueonly,separator=%x3B)%x0a' "$LOG_RANGE" |
while IFS="$US" read -r sha short author iso subject coauthors; do
  [ -n "${sha:-}" ] || continue
  [ -z "${author:-}" ] && author="未知提交人"

  subject=$(printf '%s' "$subject" | tr -d '\r' | tr '\t' ' ')
  date_text="${iso%%T*}"

  coauthor_text=""
  if [ -n "${coauthors:-}" ]; then
    old_ifs="$IFS"
    IFS=';'
    for person in $coauthors; do
      co_name="${person%%<*}"
      co_name=$(printf '%s' "$co_name" | sed 's/^[[:space:]]*//; s/[[:space:]]*$//')
      if [ -n "$co_name" ]; then
        case "、${coauthor_text}、" in
          *"、${co_name}、"*) ;;
          *)
            if [ -z "$coauthor_text" ]; then
              coauthor_text="$co_name"
            else
              coauthor_text="${coauthor_text}、${co_name}"
            fi
            ;;
        esac
      fi
    done
    IFS="$old_ifs"
  fi

  line="- ${subject} ([\`${short}\`](${REPO_URL}/commit/${sha})) · ${date_text}"
  if [ -n "$coauthor_text" ]; then
    line="${line} · 协作：${coauthor_text}"
  fi
  printf '%s\t%s\n' "$author" "$line" >> "$COMMITS_FILE"
done

# 按提交数降序排列提交人；数量相同时按姓名排序，保证输出稳定。
cut -f1 "$COMMITS_FILE" | LC_ALL=C sort | uniq -c | sed "s/^ *//; s/ /${TAB}/" |
  LC_ALL=C sort -t "$TAB" -k1,1nr -k2,2 > "$AUTHORS_FILE"
AUTHOR_COUNT=$(wc -l < "$AUTHORS_FILE" | tr -d ' ')

{
  echo "# 运动数据生成器 v${VERSION}"
  echo
  echo "> **范围**：${RANGE_TEXT} · **提交**：${COMMIT_COUNT} 个（不含合并提交） · **提交人**：${AUTHOR_COUNT} 人"
  echo
  echo "## 自上次发布以来的提交"
  echo

  if [ "$COMMIT_COUNT" -eq 0 ]; then
    echo "自上次发布以来没有新的提交。"
    echo
  else
    while IFS="$TAB" read -r count name; do
      [ -n "${name:-}" ] || continue
      safe_name=$(printf '%s' "$name" | sed 's/|/\\|/g')
      echo "### ${safe_name}（${count} 次提交）"
      echo
      while IFS="$TAB" read -r commit_author commit_line; do
        if [ "$commit_author" = "$name" ]; then
          echo "$commit_line"
        fi
      done < "$COMMITS_FILE"
      echo
    done < "$AUTHORS_FILE"

    echo "## 提交人统计"
    echo
    echo "| 提交人 | 提交数 |"
    echo "| --- | ---: |"
    while IFS="$TAB" read -r count name; do
      [ -n "${name:-}" ] || continue
      safe_name=$(printf '%s' "$name" | sed 's/|/\\|/g')
      echo "| ${safe_name} | ${count} |"
    done < "$AUTHORS_FILE"
    echo
  fi

  EMPTY_TREE=4b825dc642cb6eb9a060e54bf8d69288fbee4904
  DIFF_BASE="${FROM:-$EMPTY_TREE}"
  SHORTSTAT=$(git diff --shortstat "$DIFF_BASE" "$TO" || true)
  if [ -n "$SHORTSTAT" ]; then
    echo "## 变更统计"
    echo
    echo "- 代码变更：${SHORTSTAT}"
    echo "- 提交总数：${COMMIT_COUNT}（不含合并提交）"
    echo "- 参与提交人：${AUTHOR_COUNT} 人"
    echo
  fi

  if [ -n "$COMPARE_URL" ]; then
    echo "**完整对比**：[${FROM}...${TAG}](${COMPARE_URL})"
    echo
  fi

  echo "---"
  echo
  if [ -n "${GITHUB_RUN_ID:-}" ] && [ -n "${GITHUB_REPOSITORY:-}" ]; then
    echo "<sub>由 GitHub Actions 手动发布 · [运行详情](${SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID})</sub>"
  else
    echo "<sub>由 GitHub Actions 生成</sub>"
  fi
} > "$OUTPUT"

echo "Release notes written to $OUTPUT"
