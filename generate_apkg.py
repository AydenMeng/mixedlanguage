#!/usr/bin/env python3
"""Generate themed Chinese-English, Chinese-Japanese, and English-Japanese decks."""

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
JA_EXPECTED_HEADER = ["中文句", "日文词", "假名", "罗马音", "中文释义", "完整句"]
EN_JA_EXPECTED_HEADER = ["英文句", "日文词", "假名", "罗马音", "英文释义", "完整句"]
EN_ZH_EXPECTED_HEADER = ["英文句", "中文词", "拼音", "英文释义", "完整句"]

# These IDs must stay fixed so Anki can update the same decks and notes.
MODEL_ID = 1735689700
JA_MODEL_ID = 1735689701
EN_JA_MODEL_ID = 1735689702
EN_ZH_MODEL_ID = 1735689703


@dataclass(frozen=True)
class DeckConfig:
    key: str
    deck_id: int
    deck_name: str
    row_count: int
    language: str


DECK_CONFIGS: Tuple[DeckConfig, ...] = (
    DeckConfig(
        key="computer",
        deck_id=1735689601,
        deck_name="mixedlanguage::计算机领域用词",
        row_count=1000,
        language="en",
    ),
    DeckConfig(
        key="life",
        deck_id=1735689602,
        deck_name="mixedlanguage::生活常用词",
        row_count=1200,
        language="en",
    ),
    DeckConfig(
        key="travel",
        deck_id=1735689603,
        deck_name="mixedlanguage::旅游常用词",
        row_count=948,
        language="en",
    ),
)

JA_DECK_CONFIGS: Tuple[DeckConfig, ...] = (
    DeckConfig(
        key="computer_ja",
        deck_id=1735689611,
        deck_name="mixedlanguage::日语计算机领域用词",
        row_count=1000,
        language="ja",
    ),
    DeckConfig(
        key="life_ja",
        deck_id=1735689612,
        deck_name="mixedlanguage::日语生活常用词",
        row_count=1200,
        language="ja",
    ),
    DeckConfig(
        key="travel_ja",
        deck_id=1735689613,
        deck_name="mixedlanguage::日语旅游常用词",
        row_count=948,
        language="ja",
    ),
)

EN_JA_DECK_CONFIGS: Tuple[DeckConfig, ...] = (
    DeckConfig(
        key="computer_en_ja",
        deck_id=1735689621,
        deck_name="mixedlanguage::英语语境日语计算机用词",
        row_count=1000,
        language="en_ja",
    ),
    DeckConfig(
        key="life_en_ja",
        deck_id=1735689622,
        deck_name="mixedlanguage::英语语境日语生活用词",
        row_count=1200,
        language="en_ja",
    ),
    DeckConfig(
        key="travel_en_ja",
        deck_id=1735689623,
        deck_name="mixedlanguage::英语语境日语旅游用词",
        row_count=948,
        language="en_ja",
    ),
)

EN_ZH_DECK_CONFIGS: Tuple[DeckConfig, ...] = (
    DeckConfig(
        key="computer_en_zh",
        deck_id=1735689631,
        deck_name="mixedlanguage::英语语境中文计算机用词",
        row_count=1000,
        language="en_zh",
    ),
    DeckConfig(
        key="life_en_zh",
        deck_id=1735689632,
        deck_name="mixedlanguage::英语语境中文生活用词",
        row_count=1200,
        language="en_zh",
    ),
    DeckConfig(
        key="travel_en_zh",
        deck_id=1735689633,
        deck_name="mixedlanguage::英语语境中文旅游用词",
        row_count=948,
        language="en_zh",
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


JA_CARD_TEMPLATES = [
    {
        "name": "1 语境识别",
        "qfmt": '<div class="prompt">{{中文句}}</div>',
        "afmt": (
            '<div class="answer">'
            '<span class="word">{{日文词}}</span>'
            '<span class="phonetic">{{假名}} · {{罗马音}}</span>'
            '<span> — </span>'
            '<span class="meaning">{{中文释义}}</span>'
            "</div>"
            '<hr class="divider">'
            '<div class="full-sentence">{{完整句}}</div>'
        ),
    },
    {
        "name": "2 日译中",
        "qfmt": (
            '<div class="prompt english">{{日文词}}</div>'
            '<div class="phonetic">{{假名}} · {{罗马音}}</div>'
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
        "name": "3 中译日",
        "qfmt": '<div class="prompt meaning">{{中文释义}}</div>',
        "afmt": (
            '<div class="answer">'
            '<span class="word">{{日文词}}</span>'
            '<span class="phonetic">{{假名}} · {{罗马音}}</span>'
            "</div>"
            '<hr class="divider">'
            '<div class="full-sentence">{{完整句}}</div>'
        ),
    },
]


EN_JA_CARD_TEMPLATES = [
    {
        "name": "1 语境识别",
        "qfmt": '<div class="prompt">{{英文句}}</div>',
        "afmt": (
            '<div class="answer">'
            '<span class="word">{{日文词}}</span>'
            '<span class="phonetic">{{假名}} · {{罗马音}}</span>'
            '<span> — </span>'
            '<span class="meaning">{{英文释义}}</span>'
            "</div>"
            '<hr class="divider">'
            '<div class="full-sentence">{{完整句}}</div>'
        ),
    },
    {
        "name": "2 日译英",
        "qfmt": (
            '<div class="prompt english">{{日文词}}</div>'
            '<div class="phonetic">{{假名}} · {{罗马音}}</div>'
        ),
        "afmt": (
            '<div class="answer">'
            '<span class="meaning">{{英文释义}}</span>'
            "</div>"
            '<hr class="divider">'
            '<div class="full-sentence">{{完整句}}</div>'
        ),
    },
    {
        "name": "3 英译日",
        "qfmt": '<div class="prompt meaning">{{英文释义}}</div>',
        "afmt": (
            '<div class="answer">'
            '<span class="word">{{日文词}}</span>'
            '<span class="phonetic">{{假名}} · {{罗马音}}</span>'
            "</div>"
            '<hr class="divider">'
            '<div class="full-sentence">{{完整句}}</div>'
        ),
    },
]


EN_ZH_CARD_TEMPLATES = [
    {
        "name": "1 语境识别",
        "qfmt": '<div class="prompt">{{英文句}}</div>',
        "afmt": (
            '<div class="answer">'
            '<span class="word">{{中文词}}</span>'
            '<span class="phonetic">{{拼音}}</span>'
            '<span> — </span>'
            '<span class="meaning">{{英文释义}}</span>'
            "</div>"
            '<hr class="divider">'
            '<div class="full-sentence">{{完整句}}</div>'
        ),
    },
    {
        "name": "2 中译英",
        "qfmt": (
            '<div class="prompt english">{{中文词}}</div>'
            '<div class="phonetic">{{拼音}}</div>'
        ),
        "afmt": (
            '<div class="answer">'
            '<span class="meaning">{{英文释义}}</span>'
            "</div>"
            '<hr class="divider">'
            '<div class="full-sentence">{{完整句}}</div>'
        ),
    },
    {
        "name": "3 英译中",
        "qfmt": '<div class="prompt meaning">{{英文释义}}</div>',
        "afmt": (
            '<div class="answer">'
            '<span class="word">{{中文词}}</span>'
            '<span class="phonetic">{{拼音}}</span>'
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
    """Escape an Anki field, then wrap the target term in a style span."""
    escaped_sentence = html.escape(sentence, quote=False)
    pattern = target_pattern(html.escape(word, quote=False))
    if not pattern.search(escaped_sentence):
        raise DeckDataError("完整句中未找到目标词：{}".format(word))
    return pattern.sub(
        lambda match: '<span class="english">{}</span>'.format(match.group(0)),
        escaped_sentence,
        count=1,
    )


def read_deck_csv(config: DeckConfig) -> List[Dict[str, str]]:
    csv_path = DECKS_DIR / "{}.csv".format(config.key)
    if not csv_path.is_file():
        raise DeckDataError("找不到文件：{}".format(csv_path))

    if config.language == "en":
        expected_header = EXPECTED_HEADER
        target_field = "英文词"
        reading_field = "音标"
        sentence_field = "中文句"
        meaning_field = "中文释义"
    elif config.language == "ja":
        expected_header = JA_EXPECTED_HEADER
        target_field = "日文词"
        reading_field = "假名"
        sentence_field = "中文句"
        meaning_field = "中文释义"
    elif config.language == "en_ja":
        expected_header = EN_JA_EXPECTED_HEADER
        target_field = "日文词"
        reading_field = "假名"
        sentence_field = "英文句"
        meaning_field = "英文释义"
    else:
        expected_header = EN_ZH_EXPECTED_HEADER
        target_field = "中文词"
        reading_field = "拼音"
        sentence_field = "英文句"
        meaning_field = "英文释义"

    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != expected_header:
            raise DeckDataError(
                "{} 的表头必须是：{}".format(
                    csv_path.name, ",".join(expected_header)
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
            for field in expected_header
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

        sentence = row[sentence_field].strip()
        word = row[target_field].strip()
        reading = row[reading_field].strip()
        meaning = row[meaning_field].strip()
        full_sentence = row["完整句"].strip()
        word_key = word.casefold()

        if any("\t" in value for value in row.values()):
            errors.append("{} 第 {} 行包含制表符".format(csv_path.name, line_number))

        if config.language == "en" and word_key in seen_words:
            errors.append(
                "{} 第 {} 行英文词重复：{}".format(
                    csv_path.name, line_number, word
                )
            )
        seen_words.add(word_key)

        if not target_pattern(word).search(sentence):
            errors.append(
                "{} 第 {} 行的中文句未包含目标词 {}：{}".format(
                    csv_path.name, line_number, word, sentence
                )
            )

        if not target_pattern(word).search(full_sentence):
            errors.append(
                "{} 第 {} 行的完整句未包含目标词 {}：{}".format(
                    csv_path.name, line_number, word, full_sentence
                )
            )

        if config.language == "en" and not (
            reading.startswith("/") and reading.endswith("/")
        ):
            errors.append(
                "{} 第 {} 行的音标需要用斜杠包裹：{}".format(
                    csv_path.name, line_number, reading
                )
            )

        if config.language in {"en", "ja"}:
            han_count = len(
                re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", sentence)
            )
            min_han_count = 15 if config.language == "en" else 10
            if not min_han_count <= han_count <= 40:
                errors.append(
                    "{} 第 {} 行中文句含 {} 个汉字，应在 {} 到 40 个之间".format(
                        csv_path.name, line_number, han_count, min_han_count
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
        else:
            word_count = len(re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", sentence))
            if not 5 <= word_count <= 45:
                errors.append(
                    "{} 第 {} 行英文句含 {} 个英文单词，应在 5 到 45 个之间".format(
                        csv_path.name, line_number, word_count
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


def build_ja_model() -> genanki.Model:
    return genanki.Model(
        JA_MODEL_ID,
        "中文语境嵌日文词",
        fields=[
            {"name": "中文句"},
            {"name": "日文词"},
            {"name": "假名"},
            {"name": "罗马音"},
            {"name": "中文释义"},
            {"name": "完整句"},
        ],
        templates=JA_CARD_TEMPLATES,
        css=CARD_CSS,
    )


def build_en_ja_model() -> genanki.Model:
    return genanki.Model(
        EN_JA_MODEL_ID,
        "英语语境嵌日文词",
        fields=[
            {"name": "英文句"},
            {"name": "日文词"},
            {"name": "假名"},
            {"name": "罗马音"},
            {"name": "英文释义"},
            {"name": "完整句"},
        ],
        templates=EN_JA_CARD_TEMPLATES,
        css=CARD_CSS,
    )


def build_en_zh_model() -> genanki.Model:
    return genanki.Model(
        EN_ZH_MODEL_ID,
        "英语语境嵌中文词",
        fields=[
            {"name": "英文句"},
            {"name": "中文词"},
            {"name": "拼音"},
            {"name": "英文释义"},
            {"name": "完整句"},
        ],
        templates=EN_ZH_CARD_TEMPLATES,
        css=CARD_CSS,
    )


def build_deck(
    config: DeckConfig,
    rows: Sequence[Dict[str, str]],
    model: genanki.Model,
) -> genanki.Deck:
    deck = genanki.Deck(config.deck_id, config.deck_name)

    if config.language == "en":
        target_field = "英文词"
        reading_field = "音标"
        sentence_field = "中文句"
        meaning_field = "中文释义"
    elif config.language == "en_ja":
        target_field = "日文词"
        reading_field = "假名"
        sentence_field = "英文句"
        meaning_field = "英文释义"
    elif config.language == "ja":
        target_field = "日文词"
        reading_field = "假名"
        sentence_field = "中文句"
        meaning_field = "中文释义"
    else:
        target_field = "中文词"
        reading_field = "拼音"
        sentence_field = "英文句"
        meaning_field = "英文释义"

    for row_number, row in enumerate(rows):
        word = row[target_field].strip()
        reading = row[reading_field].strip()
        sentence = row[sentence_field].strip()
        meaning = row[meaning_field].strip()
        full_sentence = row["完整句"].strip()
        fields = [
            highlight_target(sentence, word),
            html.escape(word, quote=False),
            html.escape(reading, quote=False),
        ]
        if config.language in {"ja", "en_ja"}:
            fields.append(html.escape(row["罗马音"].strip(), quote=False))
        fields.extend(
            [
                html.escape(meaning, quote=False),
                highlight_target(full_sentence, word),
            ]
        )

        deck.add_note(
            genanki.Note(
                model=model,
                fields=fields,
                guid=genanki.guid_for(
                    "mixedlanguage-v1",
                    config.key,
                    word.casefold(),
                    "" if config.language == "en" else str(row_number),
                ),
                tags=["中文语境嵌词", config.key],
            )
        )

    return deck


def main() -> int:
    try:
        deck_rows = [
            (config, read_deck_csv(config))
            for config in (
                DECK_CONFIGS
                + JA_DECK_CONFIGS
                + EN_JA_DECK_CONFIGS
                + EN_ZH_DECK_CONFIGS
            )
        ]
        models = {
            "en": build_model(),
            "ja": build_ja_model(),
            "en_ja": build_en_ja_model(),
            "en_zh": build_en_zh_model(),
        }
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        for config, rows in deck_rows:
            deck = build_deck(config, rows, models[config.language])
            output_path = OUTPUT_DIR / "{}.apkg".format(config.key)
            genanki.Package(deck).write_to_file(str(output_path))
            template_count = {
                "en": len(CARD_TEMPLATES),
                "ja": len(JA_CARD_TEMPLATES),
                "en_ja": len(EN_JA_CARD_TEMPLATES),
                "en_zh": len(EN_ZH_CARD_TEMPLATES),
            }[config.language]
            print(
                "已生成 {}：{} 个词条，{} 张卡片".format(
                    output_path.relative_to(ROOT_DIR),
                    len(rows),
                    len(rows) * template_count,
                )
            )
    except DeckDataError as exc:
        print("数据校验失败：\n{}".format(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
