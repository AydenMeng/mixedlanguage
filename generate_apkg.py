#!/usr/bin/env python3
"""Generate three themed Anki decks from the CSV files in decks/."""

from __future__ import annotations

import csv
import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

try:
    import genanki
except ImportError as exc:  # pragma: no cover - depends on the local environment
    raise SystemExit(
        "缺少 genanki。请先运行：python -m pip install genanki"
    ) from exc


ROOT_DIR = Path(__file__).resolve().parent
DECKS_DIR = ROOT_DIR / "decks"
OUTPUT_DIR = ROOT_DIR / "output"

EXPECTED_HEADER = ["中文句", "英文词", "音标", "中文释义", "完整句"]

# These IDs must stay fixed so Anki can update the same decks and notes.
MODEL_ID = 1735689700


@dataclass(frozen=True)
class DeckConfig:
    key: str
    deck_id: int
    deck_name: str
    row_count: int


DECK_CONFIGS: Tuple[DeckConfig, ...] = (
    DeckConfig(
        key="computer",
        deck_id=1735689601,
        deck_name="mixedlanguage::计算机领域用词",
        row_count=479,
    ),
    DeckConfig(
        key="life",
        deck_id=1735689602,
        deck_name="mixedlanguage::生活常用词",
        row_count=344,
    ),
    DeckConfig(
        key="travel",
        deck_id=1735689603,
        deck_name="mixedlanguage::旅游常用词",
        row_count=948,
    ),
)


CARD_CSS = """
.card {
  box-sizing: border-box;
  max-width: 760px;
  margin: 0 auto;
  padding: 32px 22px;
  color: #20242a;
  background: #ffffff;
  font-family: "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei",
    "Helvetica Neue", Arial, sans-serif;
  font-size: 22px;
  line-height: 1.65;
  text-align: center;
}

.prompt {
  font-size: 30px;
  font-weight: 600;
  line-height: 1.55;
}

.answer {
  margin: 0 0 24px;
  font-size: 28px;
  line-height: 1.5;
}

.word,
.english {
  color: #b54708;
  font-weight: 700;
}

.meaning {
  color: #087f5b;
  font-weight: 700;
}

.phonetic {
  color: #7048a8;
  font-family: "Charis SIL", "Doulos SIL", "Times New Roman", serif;
  font-size: 0.68em;
  font-weight: 500;
  white-space: nowrap;
}

.answer .phonetic {
  margin-left: 10px;
}

.prompt + .phonetic {
  margin-top: 8px;
}

.full-sentence {
  margin-top: 10px;
  color: #666b73;
  font-size: 19px;
  line-height: 1.7;
}

.divider {
  width: 68%;
  height: 1px;
  margin: 24px auto;
  border: 0;
  background: #e5e7eb;
}

@media (prefers-color-scheme: dark) {
  .card {
    color: #f1f3f5;
    background: #25272b;
  }

  .full-sentence {
    color: #b8bdc5;
  }

  .word,
  .english {
    color: #ffb86b;
  }

  .meaning {
    color: #63e6be;
  }

  .phonetic {
    color: #cbb6ff;
  }

  .divider {
    background: #4b4e54;
  }
}
"""


CARD_TEMPLATES = [
    {
        "name": "1 语境识别",
        "qfmt": '<div class="prompt">{{中文句}}</div>',
        "afmt": (
            '<div class="answer">'
            '<span class="word">{{英文词}}</span>'
            '<span class="phonetic">{{音标}}</span>'
            '<span> — </span>'
            '<span class="meaning">{{中文释义}}</span>'
            "</div>"
            '<hr class="divider">'
            '<div class="full-sentence">{{完整句}}</div>'
        ),
    },
    {
        "name": "2 英译中",
        "qfmt": (
            '<div class="prompt english">{{英文词}}</div>'
            '<div class="phonetic">{{音标}}</div>'
        ),
        "afmt": (
            '<div class="answer">'
            '<span class="meaning">{{中文释义}}</span>'
            "</div>"
            '<hr class="divider">'
            '<div class="full-sentence">{{完整句}}</div>'
        ),
    },
    {
        "name": "3 中译英",
        "qfmt": '<div class="prompt meaning">{{中文释义}}</div>',
        "afmt": (
            '<div class="answer">'
            '<span class="word">{{英文词}}</span>'
            '<span class="phonetic">{{音标}}</span>'
            "</div>"
            '<hr class="divider">'
            '<div class="full-sentence">{{完整句}}</div>'
        ),
    },
]


class DeckDataError(ValueError):
    """Raised when one of the input CSV files is invalid."""


def target_pattern(word: str) -> re.Pattern[str]:
    return re.compile(
        r"(?<![A-Za-z])" + re.escape(word) + r"(?![A-Za-z])",
        flags=re.IGNORECASE,
    )


def highlight_target(sentence: str, word: str) -> str:
    """Escape an Anki field, then wrap the target English in a style span."""
    escaped_sentence = html.escape(sentence, quote=False)
    pattern = target_pattern(word)
    if not pattern.search(escaped_sentence):
        raise DeckDataError("完整句中未找到目标英文词：{}".format(word))
    return pattern.sub(
        lambda match: '<span class="english">{}</span>'.format(match.group(0)),
        escaped_sentence,
        count=1,
    )


def read_deck_csv(config: DeckConfig) -> List[Dict[str, str]]:
    csv_path = DECKS_DIR / "{}.csv".format(config.key)
    if not csv_path.is_file():
        raise DeckDataError("找不到文件：{}".format(csv_path))

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != EXPECTED_HEADER:
            raise DeckDataError(
                "{} 的表头必须是：{}".format(
                    csv_path.name, ",".join(EXPECTED_HEADER)
                )
            )

        rows = list(reader)

    errors: List[str] = []
    if len(rows) != config.row_count:
        errors.append(
            "{} 应有 {} 行词条，实际为 {} 行".format(
                csv_path.name, config.row_count, len(rows)
            )
        )

    seen_words = set()
    for line_number, row in enumerate(rows, start=2):
        if None in row:
            errors.append("{} 第 {} 行有额外列".format(csv_path.name, line_number))
            continue

        missing_fields = [
            field
            for field in EXPECTED_HEADER
            if not (row.get(field) or "").strip()
        ]
        if missing_fields:
            errors.append(
                "{} 第 {} 行字段为空：{}".format(
                    csv_path.name,
                    line_number,
                    "、".join(missing_fields),
                )
            )
            continue

        sentence = row["中文句"].strip()
        word = row["英文词"].strip()
        phonetic = row["音标"].strip()
        meaning = row["中文释义"].strip()
        full_sentence = row["完整句"].strip()
        word_key = word.casefold()

        if any("\t" in value for value in row.values()):
            errors.append("{} 第 {} 行包含制表符".format(csv_path.name, line_number))

        if word_key in seen_words:
            errors.append(
                "{} 第 {} 行英文词重复：{}".format(
                    csv_path.name, line_number, word
                )
            )
        seen_words.add(word_key)

        if not target_pattern(word).search(sentence):
            errors.append(
                "{} 第 {} 行的中文句未包含 {}：{}".format(
                    csv_path.name, line_number, word, sentence
                )
            )

        if not target_pattern(word).search(full_sentence):
            errors.append(
                "{} 第 {} 行的完整句未包含 {}：{}".format(
                    csv_path.name, line_number, word, full_sentence
                )
            )

        if not (phonetic.startswith("/") and phonetic.endswith("/")):
            errors.append(
                "{} 第 {} 行的音标需要用斜杠包裹：{}".format(
                    csv_path.name, line_number, phonetic
                )
            )

        han_count = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", sentence))
        if not 15 <= han_count <= 40:
            errors.append(
                "{} 第 {} 行中文句含 {} 个汉字，应在 15 到 40 个之间".format(
                    csv_path.name, line_number, han_count
                )
            )

        meaning_han_count = len(
            re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", meaning)
        )
        if not 2 <= meaning_han_count <= 6:
            errors.append(
                "{} 第 {} 行中文释义含 {} 个汉字，应在 2 到 6 个之间".format(
                    csv_path.name, line_number, meaning_han_count
                )
            )

    if errors:
        raise DeckDataError("\n".join(errors))

    return rows


def build_model() -> genanki.Model:
    return genanki.Model(
        MODEL_ID,
        "中文语境嵌词",
        fields=[
            {"name": "中文句"},
            {"name": "英文词"},
            {"name": "音标"},
            {"name": "中文释义"},
            {"name": "完整句"},
        ],
        templates=CARD_TEMPLATES,
        css=CARD_CSS,
    )


def build_deck(
    config: DeckConfig,
    rows: Sequence[Dict[str, str]],
    model: genanki.Model,
) -> genanki.Deck:
    deck = genanki.Deck(config.deck_id, config.deck_name)

    for row in rows:
        word = row["英文词"].strip()
        phonetic = row["音标"].strip()
        sentence = row["中文句"].strip()
        meaning = row["中文释义"].strip()
        full_sentence = row["完整句"].strip()
        fields = [
            highlight_target(sentence, word),
            html.escape(word, quote=False),
            html.escape(phonetic, quote=False),
            html.escape(meaning, quote=False),
            highlight_target(full_sentence, word),
        ]

        deck.add_note(
            genanki.Note(
                model=model,
                fields=fields,
                guid=genanki.guid_for("mixedlanguage-v1", config.key, word.casefold()),
                tags=["中文语境嵌词", config.key],
            )
        )

    return deck


def main() -> int:
    try:
        deck_rows = [
            (config, read_deck_csv(config)) for config in DECK_CONFIGS
        ]
        model = build_model()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        for config, rows in deck_rows:
            deck = build_deck(config, rows, model)
            output_path = OUTPUT_DIR / "{}.apkg".format(config.key)
            genanki.Package(deck).write_to_file(str(output_path))
            print(
                "已生成 {}：{} 个词条，{} 张卡片".format(
                    output_path.relative_to(ROOT_DIR),
                    len(rows),
                    len(rows) * len(CARD_TEMPLATES),
                )
            )
    except DeckDataError as exc:
        print("数据校验失败：\n{}".format(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
