import base64
import hashlib
import hmac
import json
import os
import sys
import time
from pathlib import Path

import requests


OWNERS_FILE = Path(os.environ.get("MODULE_OWNERS_FILE", "docs/module_owners.json"))


def main():
    with open("docs/changes.json", "r", encoding="utf-8") as f:
        changes = json.load(f)

    message = format_feishu_message(changes)
    send_to_feishu(message)


def format_feishu_message(changes: dict) -> str:
    version = changes.get("version", "unknown")
    text = f"文档变更版本：v{version}\n"
    text += f"更新时间：{changes['last_updated']}\n\n"

    for item in changes["changes"]:
        text += f"**文件：`{item['file']}`**\n\n"
        text += item["summary"]
        owner_mentions = format_owner_mentions(item)
        if owner_mentions:
            text += f"\n\n{owner_mentions}"
        text += "\n\n---\n\n"

    repo_url = os.environ.get("REPO_URL", "")
    if repo_url:
        text += f"[查看完整变更日志](https://github.com/{repo_url}/blob/main/CHANGELOG.md)"

    return text


def load_module_owners() -> list[dict]:
    if not OWNERS_FILE.exists():
        return []

    try:
        data = json.loads(OWNERS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid module owners file: {OWNERS_FILE}: {exc}")
        return []

    modules = data.get("modules", [])
    return modules if isinstance(modules, list) else []


def format_owner_mentions(change: dict) -> str:
    matched = find_matching_owners(change)
    frontend = dedupe_people(matched.get("frontend", []))
    backend = dedupe_people(matched.get("backend", []))

    lines = []
    if frontend:
        lines.append("前端负责人：" + "、".join(render_person(person) for person in frontend))
    if backend:
        lines.append("后端负责人：" + "、".join(render_person(person) for person in backend))

    if not lines:
        return ""
    return "相关负责人：\n" + "\n".join(lines)


def find_matching_owners(change: dict) -> dict[str, list[dict]]:
    haystack_parts = [
        change.get("file", ""),
        change.get("summary", ""),
        " ".join(change.get("affected_modules", [])),
    ]
    haystack = "\n".join(haystack_parts).lower()

    matched = {"frontend": [], "backend": []}
    for module in load_module_owners():
        keywords = [module.get("module", ""), *module.get("keywords", [])]
        keywords = [keyword.lower() for keyword in keywords if keyword]
        if not keywords or not any(keyword in haystack for keyword in keywords):
            continue

        matched["frontend"].extend(module.get("frontend", []))
        matched["backend"].extend(module.get("backend", []))

    return matched


def dedupe_people(people: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for person in people:
        key = person.get("mention") or person.get("feishu_id") or person.get("name")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(person)
    return result


def render_person(person: dict) -> str:
    if person.get("mention"):
        return person["mention"]
    if person.get("feishu_id"):
        return f"<at id={person['feishu_id']}></at>"
    return person.get("name", "未命名负责人")


def send_to_feishu(message: str) -> None:
    webhook_url = os.environ["FEISHU_WEBHOOK_URL"]
    sign_secret = os.environ.get("FEISHU_SIGN_SECRET", "")

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "技术文档更新通知",
                },
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": message,
                }
            ],
        },
    }

    if sign_secret:
        timestamp, sign = make_feishu_sign(sign_secret)
        payload["timestamp"] = timestamp
        payload["sign"] = sign

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
    except requests.RequestException as exc:
        print(f"Feishu notification failed: {exc}")
        sys.exit(1)

    if response.status_code != 200:
        print(f"Feishu HTTP error: {response.status_code} {response.text}")
        sys.exit(1)

    result = response.json()
    if result.get("code") != 0:
        print(f"Feishu returned error: {result}")
        sys.exit(1)

    print("Feishu notification sent.")


def make_feishu_sign(secret: str) -> tuple[str, str]:
    timestamp = str(int(time.time()))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        string_to_sign.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    sign = base64.b64encode(hmac_code).decode("utf-8")
    return timestamp, sign


if __name__ == "__main__":
    main()
