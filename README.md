# 中文语境嵌词 Anki 牌组

这个项目把常见外语词嵌进自然的中文或英文语境，并按计算机、生活、旅游三个领域生成中英、中日、英日、英中四套 Anki 牌组。每个词条会生成语境识别、双向翻译三张卡片。

## 文件说明

- `decks/computer.csv`：计算机领域，1000 个核心专业词条
- `decks/life.csv`：生活常用，1200 个核心词条
- `decks/travel.csv`：旅游场景，948 个核心词条
- `decks/computer_ja.csv`：计算机领域，1000 个中文语境嵌日文词条
- `decks/life_ja.csv`：生活常用，1200 个中文语境嵌日文词条
- `decks/travel_ja.csv`：旅游场景，948 个中文语境嵌日文词条
- `decks/computer_en_ja.csv`：计算机领域，1000 个英文语境嵌日文词条
- `decks/life_en_ja.csv`：生活常用，1200 个英文语境嵌日文词条
- `decks/travel_en_ja.csv`：旅游场景，948 个英文语境嵌日文词条
- `decks/computer_en_zh.csv`：计算机领域，1000 个英文语境嵌中文词条
- `decks/life_en_zh.csv`：生活常用，1200 个英文语境嵌中文词条
- `decks/travel_en_zh.csv`：旅游场景，948 个英文语境嵌中文词条
- `generate_apkg.py`：校验 CSV 并生成 Anki 牌组
- `output/computer.apkg`：脚本运行后生成
- `output/life.apkg`：脚本运行后生成
- `output/travel.apkg`：脚本运行后生成
- `output/computer_ja.apkg`：日语计算机牌组，脚本运行后生成
- `output/life_ja.apkg`：日语生活牌组，脚本运行后生成
- `output/travel_ja.apkg`：日语旅游牌组，脚本运行后生成
- `output/computer_en_ja.apkg`：英语语境日语计算机牌组，脚本运行后生成
- `output/life_en_ja.apkg`：英语语境日语生活牌组，脚本运行后生成
- `output/travel_en_ja.apkg`：英语语境日语旅游牌组，脚本运行后生成
- `output/computer_en_zh.apkg`：英语语境中文计算机牌组，脚本运行后生成
- `output/life_en_zh.apkg`：英语语境中文生活牌组，脚本运行后生成
- `output/travel_en_zh.apkg`：英语语境中文旅游牌组，脚本运行后生成

CSV 的列固定为：

```text
中文句,英文词,音标,中文释义,完整句
```

音标主要来自 [ECDICT](https://github.com/skywind3000/ECDICT) 词典，并使用 `/.../` 格式；固定短语的补充音标采用常见 IPA 标注。

日语牌组的列固定为：

```text
中文句,日文词,假名,罗马音,中文释义,完整句
```

日语词形、假名和罗马音主要参考 [JMdict](https://www.edrdg.org/jmdict/j_jmdict.html) 与 CC-CEDICT 数据，并结合领域术语和中文语境做了校正。

英日牌组的列固定为：

```text
英文句,日文词,假名,罗马音,英文释义,完整句
```

英中牌组的列固定为：

```text
英文句,中文词,拼音,英文释义,完整句
```

十二个牌组均使用人工整理并逐条校对的核心词表，优先保证用词准确、语境自然，不再追求被模板污染的大数量。

请使用 UTF-8 编码保存 CSV。字段中如果包含英文逗号，需要用双引号包裹。

## 安装依赖

需要 Python 3.8 或更高版本。建议在项目目录中创建虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install genanki
```

Windows PowerShell 的激活命令是：

```powershell
.venv\Scripts\Activate.ps1
```

## 生成牌组

在项目根目录运行：

```bash
python generate_apkg.py
```

脚本会读取 `decks/` 下的十二个 CSV 文件，校验字段、词条数量、重复目标词和例句长度，然后生成：

```text
output/computer.apkg
output/life.apkg
output/travel.apkg
output/computer_ja.apkg
output/life_ja.apkg
output/travel_ja.apkg
output/computer_en_ja.apkg
output/life_en_ja.apkg
output/travel_en_ja.apkg
output/computer_en_zh.apkg
output/life_en_zh.apkg
output/travel_en_zh.apkg
```

牌组 ID、模型 ID 和笔记 GUID 都是固定值。重新生成并导入时，Anki 会识别为同一批牌组和笔记，而不是持续创建重复内容。

## 导入 Anki

1. 打开 Anki，选择“文件”菜单中的“导入”。
2. 选择 `output/` 目录中的一个 `.apkg` 文件。
3. 确认导入目标，然后依次导入其余十一个文件。
4. 导入完成后，会在 `mixedlanguage` 牌组下看到中英、中日、英日、英中各三个领域的独立牌组。

每个词条包含以下三张卡片：

- 语境识别：正面显示嵌词中文句，背面显示英文词、音标、中文释义和完整句。
- 英译中：正面显示英文词和音标，背面显示中文释义和完整句。
- 中译英：正面显示中文释义，背面显示英文词、音标和完整句。

日语牌组同样包含三张卡片：

- 语境识别：正面显示嵌词中文句，背面显示日文词、假名、罗马音、中文释义和完整句。
- 日译中：正面显示日文词、假名和罗马音，背面显示中文释义和完整句。
- 中译日：正面显示中文释义，背面显示日文词、假名和罗马音。

英日牌组包含三张卡片：

- 语境识别：正面显示嵌词英文句，背面显示日文词、假名、罗马音、英文释义和完整句。
- 日译英：正面显示日文词、假名和罗马音，背面显示英文释义和完整句。
- 英译日：正面显示英文释义，背面显示日文词、假名、罗马音和完整句。

英中牌组包含三张卡片：

- 语境识别：正面显示嵌词英文句，背面显示中文词、拼音、英文释义和完整句。
- 中译英：正面显示中文词和拼音，背面显示英文释义和完整句。
- 英译中：正面显示英文释义，背面显示中文词、拼音和完整句。

## 修改词表

直接编辑 `decks/` 中的 CSV 后重新运行脚本即可。中英、中日、英日、英中四套计算机、生活、旅游牌组应分别保留 1000、1200、948 行词条，第一行表头不要修改。脚本会对常见数据问题给出具体行号，修正后再重新生成即可。
