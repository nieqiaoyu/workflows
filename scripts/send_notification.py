import base64
import hashlib
import hmac
import json
import os
import sys
import time

import requests


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
        text += "\n\n---\n\n"

    repo_url = os.environ.get("REPO_URL", "")
    if repo_url:
        text += f"[查看完整变更日志](https://github.com/{repo_url}/blob/main/CHANGELOG.md)"

    return text


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
