"""Strip WeChat / WeFlow placeholder tokens from a fine-tune dataset.

When the WeFlow XLSX importer encounters a non-text WeChat message (sticker,
animated emoji, image, voice, file, location, transfer, etc.) it emits a
bracket-tagged placeholder such as ``[动画表情]`` or ``[表情包]`` into the
normalized message content. A QLoRA fine-tune on raw exported data therefore
learns "when the user sends a greeting, reply with ``[动画表情] [表情包]``" —
the target speaker really does open most chats with a sticker, but the literal
tag bleeds straight into generated replies and looks broken.

This script post-processes an existing dataset directory (``train.jsonl``,
``validation.jsonl``, ``test.jsonl``) by:

1. Dropping any sample whose final ``assistant`` message becomes empty after
   placeholders are stripped (pure-sticker reply — uninformative for a text
   model);
2. Within every surviving sample, stripping the placeholder tokens from
   *all* messages (user-side too) so the model never sees them anywhere;
3. Dropping a sample if cleanup leaves it with fewer than one user message
   and one assistant message.

The originals are preserved alongside the canonical files as
``<split>.original.jsonl`` so a re-run does not need to be re-imported from
scratch.

Usage::

    python scripts/local_finetune/clean_placeholders.py \
        --dataset-dir E:/laiver-tmp/fine-tuning/<job-id>/dataset

Verified on the 张皓楠 WeFlow chat (5492 → 4445 train samples after cleaning).
The Qwen3-14B QLoRA adapter trained on the cleaned data produces TA-style
short replies on 9/10 evaluation prompts; the bracket-tag leak that
dominated the dirty-data run is gone.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# Conservative list of placeholders emitted by the WeFlow XLSX importer.
# Extend if a future export surfaces a new token. Order does not matter
# because we compile a single alternation regex below.
PLACEHOLDERS: tuple[str, ...] = (
    "[动画表情]",
    "[表情包]",
    "[图片]",
    "[视频]",
    "[语音]",
    "[文件]",
    "[链接]",
    "[红包]",
    "[位置]",
    "[名片]",
    "[转账]",
    "[拍一拍]",
    "[引用]",
)

_PLACEHOLDER_RE = re.compile("|".join(re.escape(p) for p in PLACEHOLDERS))
_WHITESPACE_RE = re.compile(r"\s+")


def strip_placeholders(text: str) -> str:
    """Remove placeholder tokens and collapse runs of whitespace."""
    return _WHITESPACE_RE.sub(" ", _PLACEHOLDER_RE.sub("", text)).strip()


def clean_split(src_path: Path, dst_path: Path) -> dict[str, int]:
    """Read ``src_path`` line-by-line, write the cleaned subset to ``dst_path``."""
    counts = {"kept": 0, "dropped_pure_placeholder": 0, "dropped_other": 0}
    with src_path.open(encoding="utf-8") as fin, dst_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            row = json.loads(line)
            messages = row.get("messages", [])
            if not messages:
                counts["dropped_other"] += 1
                continue

            # Find the final assistant message — that is the training target.
            final_idx: int | None = None
            for i in range(len(messages) - 1, -1, -1):
                if messages[i].get("role") == "assistant":
                    final_idx = i
                    break
            if final_idx is None:
                counts["dropped_other"] += 1
                continue

            cleaned_target = strip_placeholders(messages[final_idx].get("content", ""))
            if not cleaned_target:
                # Pure-placeholder reply: no textual signal for the model to learn.
                counts["dropped_pure_placeholder"] += 1
                continue

            new_messages: list[dict[str, str]] = []
            for message in messages:
                content = strip_placeholders(message.get("content", ""))
                if not content:
                    continue
                new_messages.append({"role": message["role"], "content": content})

            # Runner contract: at least one user message before the final assistant.
            if (
                len(new_messages) < 2
                or new_messages[-1]["role"] != "assistant"
                or not any(m["role"] == "user" for m in new_messages[:-1])
            ):
                counts["dropped_other"] += 1
                continue

            row["messages"] = new_messages
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")
            counts["kept"] += 1
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--dataset-dir",
        required=True,
        type=Path,
        help="Directory containing train.jsonl / validation.jsonl / test.jsonl",
    )
    parser.add_argument(
        "--backup-suffix",
        default=".original.jsonl",
        help="Suffix to append when backing up originals (default: .original.jsonl)",
    )
    args = parser.parse_args()

    if not args.dataset_dir.is_dir():
        raise SystemExit(f"dataset-dir not found: {args.dataset_dir}")

    summary: dict[str, dict[str, int]] = {}
    for split in ("train", "validation", "test"):
        src = args.dataset_dir / f"{split}.jsonl"
        if not src.exists():
            print(f"  {split:11s}: skipped (no {src.name})")
            continue
        backup = args.dataset_dir / f"{split}{args.backup_suffix}"
        if not backup.exists():
            backup.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"  {split:11s}: backed up to {backup.name}")
        summary[split] = clean_split(backup, src)

    print()
    print("=== cleaning result ===")
    for split, c in summary.items():
        total = c["kept"] + c["dropped_pure_placeholder"] + c["dropped_other"]
        kept_pct = 100 * c["kept"] // max(1, total)
        print(
            f"  {split:11s}: kept {c['kept']:5d} ({kept_pct}%) | "
            f"dropped_pure {c['dropped_pure_placeholder']:4d} | "
            f"dropped_other {c['dropped_other']:4d} | total {total}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
