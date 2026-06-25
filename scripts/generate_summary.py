import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


IGNORED_FILES = {"CHANGELOG.md", "docs/changes.json"}
CHANGES_JSON = Path("docs/changes.json")


def main():
    before_sha = os.environ.get("BEFORE_SHA", "").strip()
    after_sha = os.environ.get("AFTER_SHA", "HEAD").strip()
    version = get_next_version()

    changed_files = get_changed_markdown_files(before_sha, after_sha)
    if not changed_files:
        print("No markdown document changes found.")
        set_github_output("has_changes", "false")
        return

    summaries = []
    for file in changed_files:
        diff_content = get_file_diff(file, before_sha, after_sha)
        if not diff_content.strip():
            continue

        if len(diff_content) > 12000:
            diff_content = diff_content[:12000] + "\n...[truncated because diff is too long]"

        summary_text = generate_ai_summary(file, diff_content)
        summaries.append(
            {
                "file": file,
                "summary": summary_text,
                "timestamp": now_iso(),
                "version": version,
                "affected_modules": extract_modules(summary_text),
            }
        )

    if not summaries:
        print("All document changes were ignored.")
        set_github_output("has_changes", "false")
        return

    save_changelog(summaries, version)
    save_changes_json(summaries, version)
    set_github_output("has_changes", "true")


def set_github_output(name: str, value: str) -> None:
    output_file = os.environ.get("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as f:
            f.write(f"{name}={value}\n")


def run_git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def is_zero_sha(value: str) -> bool:
    return bool(value) and set(value) == {"0"}


def get_changed_markdown_files(before_sha: str, after_sha: str) -> list[str]:
    if before_sha and not is_zero_sha(before_sha):
        result = run_git(["diff", "--name-only", before_sha, after_sha])
    else:
        result = run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", after_sha])

    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)

    return [
        f.strip()
        for f in result.stdout.strip().split("\n")
        if f.strip()
        and f.strip().endswith(".md")
        and f.strip() not in IGNORED_FILES
    ]


def get_file_diff(file: str, before_sha: str, after_sha: str) -> str:
    if before_sha and not is_zero_sha(before_sha):
        diff_result = run_git(["diff", before_sha, after_sha, "--", file])
        if diff_result.stdout.strip():
            return diff_result.stdout

    path = Path(file)
    if path.exists():
        return f"[new or initial file]\n{path.read_text(encoding='utf-8')}"
    return f"[deleted file]\n{file}"


def now_iso() -> str:
    timezone_name = os.environ.get("DOC_TIMEZONE", "Asia/Shanghai")
    return datetime.now(ZoneInfo(timezone_name)).strftime("%Y-%m-%d %H:%M:%S")


def get_next_version() -> int:
    if not CHANGES_JSON.exists():
        return 1

    try:
        data = json.loads(CHANGES_JSON.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return 1

    current_version = data.get("version", 0)
    try:
        return int(current_version) + 1
    except (TypeError, ValueError):
        return 1


def generate_ai_summary(file_name: str, diff_content: str) -> str:
    prompt = f"""你是技术文档变更分析助手。请分析以下文档变更，生成简洁的结构化摘要。

文件：{file_name}

变更内容：
{diff_content}

请严格按以下格式输出：

变更内容：
（列出具体的新增/删除/修改项，包括参数、接口、流程变更）

需要关注：
（哪些变更可能导致代码需要适配）

影响模块：
（列出受影响的模块/接口/功能）

无影响：
（哪些变更只是文档描述优化，不影响代码）

摘要要简洁，开发者1分钟内能看完。"""

    provider = (os.environ.get("LLM_PROVIDER") or "openai-compatible").strip().lower()
    if provider == "anthropic":
        return call_anthropic(prompt)
    return call_openai_compatible(prompt)


def call_openai_compatible(prompt: str) -> str:
    api_base = (os.environ.get("LLM_API_BASE") or "https://api.openai.com").rstrip("/")
    response = requests.post(
        f"{api_base}/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {os.environ['LLM_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": os.environ["LLM_MODEL"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def call_anthropic(prompt: str) -> str:
    api_base = (os.environ.get("LLM_API_BASE") or "https://api.anthropic.com").rstrip("/")
    response = requests.post(
        f"{api_base}/v1/messages",
        headers={
            "x-api-key": os.environ["LLM_API_KEY"],
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        },
        json={
            "model": os.environ["LLM_MODEL"],
            "max_tokens": 1500,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["content"][0]["text"]


def extract_modules(summary: str) -> list[str]:
    modules = []
    in_section = False
    for line in summary.split("\n"):
        if "影响模块" in line:
            in_section = True
            continue
        if in_section and line.strip() and not line.startswith("无影响"):
            modules.append(line.strip().lstrip("- ").lstrip("* "))
        if "无影响" in line:
            break
    return modules


def save_changelog(summaries: list[dict], version: int) -> None:
    header = "# 文档变更日志\n\n"
    changelog = Path("CHANGELOG.md")
    existing = changelog.read_text(encoding="utf-8") if changelog.exists() else header

    new_entries = ""
    for item in summaries:
        new_entries += f"## v{version} - {item['timestamp']} - `{item['file']}`\n\n"
        new_entries += f"{item['summary']}\n\n---\n\n"

    old_content = existing.replace(header, "")
    changelog.write_text(header + new_entries + old_content, encoding="utf-8")


def save_changes_json(summaries: list[dict], version: int) -> None:
    CHANGES_JSON.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": version,
        "last_updated": now_iso(),
        "changes": summaries,
    }
    CHANGES_JSON.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
