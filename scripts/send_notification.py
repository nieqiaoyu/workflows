import json
import os
import sys
from pathlib import Path

import requests


OWNERS_FILE = Path(os.environ.get("MODULE_OWNERS_FILE", "docs/module_owners.json"))


def main():
    with open("docs/changes.json", "r", encoding="utf-8") as f:
        changes = json.load(f)

    matched_owners = collect_matched_owners(changes)
    message = format_markdown_message(changes, matched_owners)
    send_wecom_markdown(message)

    mention_payload = build_mention_payload(changes, matched_owners)
    if mention_payload:
        send_wecom_text(**mention_payload)


def format_markdown_message(changes: dict, matched_owners: dict) -> str:
    version = changes.get("version", "unknown")
    text = f"## 技术文档更新通知 v{version}\n"
    text += f"> 更新时间：{changes['last_updated']}\n\n"

    for item in changes["changes"]:
        text += f"**文件：** `{item['file']}`\n\n"
        text += item["summary"]
        owner_lines = format_owner_lines(item, matched_owners)
        if owner_lines:
            text += f"\n\n{owner_lines}"
        text += "\n\n---\n\n"

    repo_url = os.environ.get("REPO_URL", "")
    if repo_url:
        text += f"[查看完整变更日志](https://github.com/{repo_url}/blob/main/CHANGELOG.md)"

    return text


def load_module_owners() -> list[dict]:
    owners_json = os.environ.get("MODULE_OWNERS_JSON", "").strip()
    if owners_json:
        try:
            data = json.loads(owners_json)
        except json.JSONDecodeError as exc:
            print(f"Invalid MODULE_OWNERS_JSON: {exc}")
            return []

        if isinstance(data, int):
            return default_mobile_owner(str(data))
        if isinstance(data, str):
            value = data.strip()
            if value.isdigit():
                return default_mobile_owner(value)
            print("Invalid MODULE_OWNERS_JSON: expected object with modules, got string.")
            return []
        if not isinstance(data, dict):
            print("Invalid MODULE_OWNERS_JSON: expected object with modules.")
            return []

        modules = data.get("modules", [])
        return modules if isinstance(modules, list) else []

    if not OWNERS_FILE.exists():
        return []

    try:
        data = json.loads(OWNERS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Invalid module owners file: {OWNERS_FILE}: {exc}")
        return []

    modules = data.get("modules", [])
    return modules if isinstance(modules, list) else []


def default_mobile_owner(mobile: str) -> list[dict]:
    return [
        {
            "module": "默认负责人",
            "keywords": ["docs/demo.md"],
            "owners": [
                {
                    "name": "默认负责人",
                    "role": "负责人",
                    "mobile": mobile,
                }
            ],
        }
    ]


def collect_matched_owners(changes: dict) -> dict[str, dict]:
    result = {}
    for item in changes.get("changes", []):
        result[item.get("file", "")] = find_matching_owners(item)
    return result


def format_owner_lines(change: dict, matched_owners: dict) -> str:
    owners = matched_owners.get(change.get("file", ""), {})
    people = dedupe_people(owners.get("owners", []))

    grouped = group_people_by_role(people)
    lines = [
        f"**{role}：** " + "、".join(render_person_name(person) for person in role_people)
        for role, role_people in grouped.items()
    ]

    if not lines:
        return ""
    return "**相关负责人：**\n" + "\n".join(lines)


def find_matching_owners(change: dict) -> dict[str, list[dict]]:
    haystack_parts = [
        change.get("file", ""),
        change.get("summary", ""),
        " ".join(change.get("affected_modules", [])),
    ]
    haystack = "\n".join(haystack_parts).lower()

    matched = {"owners": []}
    for module in load_module_owners():
        keywords = [module.get("module", ""), *module.get("keywords", [])]
        keywords = [keyword.lower() for keyword in keywords if keyword]
        if not keywords:
            continue
        if "*" not in keywords and not any(keyword in haystack for keyword in keywords):
            continue

        matched["owners"].extend(normalize_module_people(module))

    return matched


def normalize_module_people(module: dict) -> list[dict]:
    people = []

    for person in module.get("owners", []):
        normalized = dict(person)
        normalized.setdefault("role", "负责人")
        people.append(normalized)

    legacy_roles = {
        "frontend": "前端",
        "backend": "后端",
        "test": "测试",
        "testing": "测试",
        "qa": "测试",
    }
    for field, role in legacy_roles.items():
        for person in module.get(field, []):
            normalized = dict(person)
            normalized.setdefault("role", role)
            people.append(normalized)

    return people


def dedupe_people(people: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for person in people:
        key = person.get("mobile") or person.get("user_id") or person.get("name")
        if not key or key in seen:
            continue
        seen.add(key)
        result.append(person)
    return result


def render_person_name(person: dict) -> str:
    return person.get("name") or person.get("user_id") or person.get("mobile") or "未命名负责人"


def group_people_by_role(people: list[dict]) -> dict[str, list[dict]]:
    grouped = {}
    for person in people:
        role = person.get("role") or "负责人"
        grouped.setdefault(role, []).append(person)
    return grouped


def build_mention_payload(changes: dict, matched_owners: dict) -> dict | None:
    user_ids = []
    mobiles = []
    people = []

    for owners in matched_owners.values():
        for person in owners.get("owners", []):
            people.append(person)
            if person.get("user_id"):
                user_ids.append(person["user_id"])
            if person.get("mobile"):
                mobiles.append(person["mobile"])

    user_ids = dedupe_values(user_ids)
    mobiles = dedupe_values(mobiles)
    people = dedupe_people(people)
    if not user_ids and not mobiles:
        return None

    version = changes.get("version", "unknown")
    content = f"请相关负责人关注技术文档更新 v{version}，详情见上方通知。"
    owner_lines = format_text_owner_lines(people)
    if owner_lines:
        content += f"\n{owner_lines}"

    print(
        "WeCom mention targets: "
        f"user_ids={len(user_ids)}, "
        f"mobiles={','.join(mask_mobile(mobile) for mobile in mobiles)}"
    )

    return {
        "content": content,
        "mentioned_list": user_ids,
        "mentioned_mobile_list": mobiles,
    }


def render_person_for_text(person: dict) -> str:
    name = person.get("name")
    user_id = person.get("user_id")
    if name and user_id:
        return f"@{name}{user_id}"
    if user_id:
        return f"@{user_id}"
    return name or "未命名负责人"


def format_text_owner_lines(people: list[dict]) -> str:
    grouped = group_people_by_role(people)
    role_order = ["前端", "后端", "测试"]
    lines = []

    for role in role_order:
        role_people = grouped.pop(role, [])
        if role_people:
            lines.append(f"{role}：" + "、".join(render_person_for_text(person) for person in role_people))

    for role, role_people in grouped.items():
        if role_people:
            lines.append(f"{role}：" + "、".join(render_person_for_text(person) for person in role_people))

    return "\n".join(lines)


def mask_mobile(mobile: str) -> str:
    if len(mobile) < 4:
        return "****"
    return f"***{mobile[-4:]}"


def dedupe_values(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def send_wecom_markdown(content: str) -> None:
    send_wecom_payload(
        {
            "msgtype": "markdown",
            "markdown": {
                "content": content,
            },
        }
    )


def send_wecom_text(
    content: str,
    mentioned_list: list[str],
    mentioned_mobile_list: list[str],
) -> None:
    payload = {
        "msgtype": "text",
        "text": {
            "content": content,
        },
    }
    if mentioned_list:
        payload["text"]["mentioned_list"] = mentioned_list
    if mentioned_mobile_list:
        payload["text"]["mentioned_mobile_list"] = mentioned_mobile_list

    send_wecom_payload(payload)


def send_wecom_payload(payload: dict) -> None:
    webhook_url = os.environ["WECOM_WEBHOOK_URL"]

    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
    except requests.RequestException as exc:
        print(f"WeCom notification failed: {exc}")
        sys.exit(1)

    if response.status_code != 200:
        print(f"WeCom HTTP error: {response.status_code} {response.text}")
        sys.exit(1)

    result = response.json()
    if result.get("errcode") != 0:
        print(f"WeCom returned error: {result}")
        sys.exit(1)

    print("WeCom notification sent.")


if __name__ == "__main__":
    main()
