#!/usr/bin/env python3

import re
import subprocess
import sys
from pathlib import Path

def main():
    commit_msg_path = Path(sys.argv[1])
    commit_msg = commit_msg_path.read_text()

    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            text=True
        ).strip()
    except subprocess.CalledProcessError:
        return

    # 영어 대문자 + 숫자 패턴만 추출
    match = re.search(r'\b([A-Z]+-\d+)\b', branch)
    if not match:
        return

    ticket_id = match.group(1)

    # 중복 방지
    if f"[{ticket_id}]" in commit_msg:
        return

    # "Feat: 메시지" → "Feat: [EVER-25] 메시지" 형태로 변환
    if ':' in commit_msg:
        type_part, rest = commit_msg.split(':', 1)
        new_msg = f"{type_part.strip()}: [{ticket_id}] {rest.strip()}\n"
    else:
        new_msg = f"[{ticket_id}] {commit_msg.strip()}\n"

    commit_msg_path.write_text(new_msg)

if __name__ == "__main__":
    main()
