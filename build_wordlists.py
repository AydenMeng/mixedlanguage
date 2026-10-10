#!/usr/bin/env python3
"""Build the themed word CSV files from the ECDICT dictionary database."""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


ROOT_DIR = Path(__file__).resolve().parent
DECKS_DIR = ROOT_DIR / "decks"

VALID_WORD_RE = re.compile(r"^[A-Za-z][A-Za-z' -]{0,40}$")
HAN_SEQUENCE_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]+")
POS_PREFIX_RE = re.compile(r"^(vt|vi|v|n|a|adj|adv)\.\s*", re.IGNORECASE)
BRACKET_RE = re.compile(r"[\[【(（][^\]】)）]*[\]】)）]")

LIFE_STOP_WORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "if",
    "because",
    "although",
    "though",
    "while",
    "when",
    "where",
    "why",
    "how",
    "who",
    "whom",
    "whose",
    "which",
    "what",
    "this",
    "that",
    "these",
    "those",
    "i",
    "me",
    "my",
    "mine",
    "we",
    "us",
    "our",
    "ours",
    "you",
    "your",
    "yours",
    "he",
    "him",
    "his",
    "she",
    "her",
    "hers",
    "it",
    "its",
    "they",
    "them",
    "their",
    "theirs",
    "am",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "do",
    "does",
    "did",
    "have",
    "has",
    "had",
    "can",
    "could",
    "may",
    "might",
    "must",
    "shall",
    "should",
    "will",
    "would",
    "at",
    "by",
    "for",
    "from",
    "in",
    "into",
    "of",
    "on",
    "onto",
    "to",
    "with",
    "about",
    "as",
    "than",
    "so",
    "not",
    "no",
    "yes",
}

BAD_MEANINGS = {
    "主英",
    "变形",
    "的变形",
    "复数",
    "过去式",
    "过去分词",
    "现在分词",
}

SPECIAL_LIFE_WORDS = {
    "all",
    "also",
    "another",
    "any",
    "ask",
    "back",
    "begin",
    "big",
    "call",
    "child",
    "company",
    "country",
    "day",
    "down",
    "even",
    "family",
    "feel",
    "find",
    "first",
    "get",
    "give",
    "go",
    "good",
    "government",
    "great",
    "group",
    "hand",
    "help",
    "here",
    "high",
    "house",
    "however",
    "just",
    "keep",
    "know",
    "last",
    "leave",
    "life",
    "like",
    "look",
    "make",
    "man",
    "many",
    "mean",
    "more",
    "most",
    "much",
    "need",
    "never",
    "new",
    "now",
    "old",
    "one",
    "only",
    "other",
    "out",
    "over",
    "own",
    "part",
    "party",
    "people",
    "place",
    "problem",
    "really",
    "same",
    "say",
    "school",
    "see",
    "seem",
    "service",
    "show",
    "small",
    "state",
    "still",
    "student",
    "such",
    "system",
    "take",
    "tell",
    "there",
    "thing",
    "think",
    "through",
    "time",
    "too",
    "try",
    "use",
    "very",
    "want",
    "way",
    "well",
    "woman",
    "work",
    "world",
    "year",
}

SPECIAL_LIFE_TEMPLATES = (
    "在生活英语里，{word} 很常用，但具体意思要结合整句话来判断。",
    "日常交流时经常会遇到 {word}，记住常见搭配比只背中文更重要。",
    "学习 {word} 时不要只看一个中文解释，还要留意它在语境里的用法。",
)

MEANING_OVERRIDES: Dict[Tuple[str, str], str] = {
    ("computer", "memory"): "内存",
    ("computer", "program"): "程序",
    ("computer", "server"): "服务器",
    ("computer", "protocol"): "协议",
    ("computer", "file"): "文件",
    ("computer", "monitor"): "显示器",
    ("computer", "printer"): "打印机",
    ("computer", "cache"): "缓存",
    ("computer", "cyberpunk"): "赛博朋克",
    ("computer", "compiler"): "编译器",
    ("computer", "mouse"): "鼠标",
    ("computer", "backup"): "备份",
    ("computer", "source"): "源码",
    ("computer", "argument"): "参数",
    ("computer", "object"): "对象",
    ("computer", "address"): "地址",
    ("computer", "link"): "链接",
    ("computer", "switch"): "交换机",
    ("computer", "cookie"): "网站凭证",
    ("computer", "binary"): "二进制",
    ("computer", "debug"): "调试",
    ("computer", "browser"): "浏览器",
    ("computer", "table"): "数据表",
    ("computer", "field"): "字段",
    ("computer", "drive"): "驱动器",
    ("computer", "screen"): "屏幕",
    ("computer", "patch"): "补丁",
    ("computer", "packet"): "数据包",
    ("computer", "parameter"): "参数",
    ("computer", "loop"): "循环",
    ("computer", "upgrade"): "升级",
    ("computer", "deploy"): "部署",
    ("computer", "token"): "令牌",
    ("computer", "cursor"): "光标",
    ("computer", "bandwidth"): "带宽",
    ("computer", "library"): "程序库",
    ("computer", "bug"): "程序错误",
    ("computer", "digital"): "数字化",
    ("computer", "interface"): "接口",
    ("computer", "buffer"): "缓冲区",
    ("computer", "module"): "模块",
    ("computer", "terminal"): "终端",
    ("computer", "console"): "控制台",
    ("computer", "script"): "脚本",
    ("computer", "response"): "响应",
    ("computer", "key"): "按键",
    ("computer", "video"): "视频",
    ("computer", "component"): "组件",
    ("computer", "socket"): "套接字",
    ("computer", "syntax"): "语法",
    ("computer", "decimal"): "十进制",
    ("computer", "driver"): "驱动程序",
    ("computer", "interpreter"): "解释器",
    ("computer", "assembler"): "汇编器",
    ("computer", "scheduler"): "调度器",
    ("computer", "frame"): "数据帧",
    ("computer", "adapter"): "适配器",
    ("life", "honestly"): "老实说",
    ("life", "leg"): "腿部",
    ("life", "argue"): "争吵",
    ("life", "borrow"): "借用",
    ("life", "route"): "路线",
    ("life", "transfer"): "转移",
    ("life", "reservation"): "预订",
    ("travel", "reservation"): "预订",
    ("travel", "transfer"): "换乘",
    ("travel", "itinerary"): "行程",
    ("travel", "checkout"): "退房",
    ("travel", "route"): "路线",
    ("travel", "hostel"): "青年旅舍",
    ("travel", "tour"): "旅游",
}

SENTENCE_OVERRIDES: Dict[Tuple[str, str], str] = {
    (
        "computer",
        "cyberpunk",
    ): "这部 cyberpunk 作品对未来城市的想象很有科技感。",
    (
        "computer",
        "argument",
    ): "调用这个方法前别忘了检查 argument 的类型和顺序。",
    (
        "computer",
        "upgrade",
    ): "这次 upgrade 涉及数据库和中间件，必须安排维护窗口。",
    (
        "computer",
        "electronic",
    ): "这块 electronic 元件出现故障，导致设备无法正常启动。",
    (
        "computer",
        "directory",
    ): "这个 directory 里保存了所有构建产物，清理前要先确认。",
    (
        "computer",
        "binary",
    ): "接口传输大批量数据时，更适合使用 binary 格式。",
    (
        "computer",
        "decimal",
    ): "金额计算最好使用 decimal 类型，避免浮点数带来精度误差。",
    (
        "computer",
        "script",
    ): "部署脚本时要把 script 的路径和权限一起检查清楚。",
    (
        "computer",
        "console",
    ): "程序卡住以后，我在 console 里输入命令才恢复了服务。",
    (
        "travel",
        "transfer",
    ): "在机场 transfer 时要注意广播，登机口有时会临时变更。",
    (
        "life",
        "honestly",
    ): "说句 honestly，我实在不想参加这种没有意义的应酬。",
    (
        "life",
        "leg",
    ): "锻炼完以后我的 leg 特别酸，连楼梯都不想爬。",
    (
        "life",
        "argue",
    ): "他们为周末去哪里 argue 了很久，最后还是没有达成一致。",
    (
        "life",
        "borrow",
    ): "能先 borrow 你的充电器吗，我的手机快没电了。",
    (
        "life",
        "hesitate",
    ): "别再 hesitate 了，错过这次机会你会后悔很久。",
}

SENTENCE_OPENERS: Dict[str, Tuple[str, ...]] = {
    "computer": (
        "排查问题时，",
        "做项目维护时，",
        "处理线上告警时，",
        "准备上线前，",
        "代码评审时，",
        "结合监控数据，",
        "复盘故障时，",
        "部署新版本时，",
        "检查配置时，",
        "讨论技术方案时，",
        "更新系统文档时，",
        "安排测试计划时，",
    ),
    "life": (
        "回想起来，",
        "最近这段时间，",
        "和朋友聊天时，",
        "独自在家时，",
        "处理日常琐事时，",
        "经历那件事以后，",
        "忙完工作以后，",
        "周末休息时，",
        "走在路上时，",
        "面对家人时，",
        "做决定以前，",
        "整理房间时，",
    ),
    "travel": (
        "出发以后，",
        "到达当地时，",
        "办理手续时，",
        "自由行过程中，",
        "在景点游玩时，",
        "遇到行程变化时，",
        "入住酒店以后，",
        "准备返程时，",
        "等待登机时，",
        "咨询工作人员时，",
        "查看旅行攻略时，",
        "安排第二天计划时，",
    ),
}

SENTENCE_CLOSERS: Dict[str, Tuple[str, ...]] = {
    "computer": (
        "相关风险已经记录",
        "团队会继续跟进",
        "目前运行基本稳定",
        "后面还要补充验证",
        "这次处理很有参考价值",
        "问题已进入跟踪列表",
        "后续测试会覆盖该场景",
        "处理结果已经同步",
        "线上指标没有异常",
        "维护流程会更加清晰",
        "这项检查不能省略",
        "经验已经写入文档",
    ),
    "life": (
        "这让我多了一点体会",
        "后来我慢慢想明白了",
        "现在回想仍然很有感触",
        "生活也因此轻松了一些",
        "这件事提醒我要多留心",
        "我心里终于踏实了",
        "以后再遇到会更从容",
        "家人也很认可这个做法",
        "这成了我的一点经验",
        "之后我打算继续坚持",
        "这个变化让人很舒服",
        "我也学会了换位思考",
    ),
    "travel": (
        "后面的行程顺利多了",
        "这次经历很有帮助",
        "大家终于松了一口气",
        "问题很快就解决了",
        "我们对当地也更熟悉了",
        "这条路线值得推荐",
        "旅途因此少了很多麻烦",
        "工作人员的态度很不错",
        "后面的安排没有受影响",
        "这次体验让人印象深刻",
        "同行的人都觉得很方便",
        "下次来还会这样安排",
    ),
}


@dataclass(frozen=True)
class DomainConfig:
    key: str
    target_count: int
    seeds: Tuple[str, ...]
    chinese_markers: Tuple[str, ...]


DOMAINS: Tuple[DomainConfig, ...] = (
    DomainConfig(
        key="computer",
        target_count=1800,
        seeds=(
            "computer",
            "software",
            "hardware",
            "program",
            "programming",
            "database",
            "network",
            "server",
            "system",
            "algorithm",
            "data",
            "internet",
            "web",
            "file",
            "code",
            "coding",
            "memory",
            "storage",
            "computerized",
            "digital",
            "machine",
            "processor",
            "computing",
            "application",
            "security",
            "protocol",
            "device",
            "electronic",
            "cyber",
            "cloud",
            "operating",
        ),
        chinese_markers=("计算机", "电脑", "程序", "数据库", "网络", "软件", "硬件"),
    ),
    DomainConfig(
        key="life",
        target_count=3000,
        seeds=(),
        chinese_markers=(),
    ),
    DomainConfig(
        key="travel",
        target_count=1500,
        seeds=(
            "travel",
            "traveler",
            "traveller",
            "tour",
            "tourist",
            "tourism",
            "hotel",
            "airport",
            "flight",
            "plane",
            "airplane",
            "train",
            "railway",
            "ticket",
            "journey",
            "trip",
            "luggage",
            "baggage",
            "passport",
            "visa",
            "destination",
            "vacation",
            "holiday",
            "resort",
            "sightseeing",
            "customs",
            "boarding",
            "departure",
            "arrival",
            "booking",
            "reservation",
            "itinerary",
            "cruise",
            "caravan",
            "camping",
        ),
        chinese_markers=(
            "旅行",
            "旅游",
            "游客",
            "酒店",
            "机场",
            "航班",
            "车票",
            "行李",
            "护照",
            "签证",
            "景点",
        ),
    ),
)


FALLBACK_ENTRIES: Dict[str, Tuple[Tuple[str, str, str, str], ...]] = {
    "computer": (
        ("command line", "/kəˈmænd laɪn/", "命令行", "n"),
        ("operating system", "/ˈɑːpəreɪtɪŋ ˌsɪstəm/", "操作系统", "n"),
        ("source code", "/sɔːrs koʊd/", "源代码", "n"),
        ("machine learning", "/məˈʃiːn ˌlɝːnɪŋ/", "机器学习", "n"),
        (
            "artificial intelligence",
            "/ˌɑːrtɪˈfɪʃəl ɪnˈtelɪdʒəns/",
            "人工智能",
            "n",
        ),
        ("data structure", "/ˈdeɪtə ˌstrʌktʃər/", "数据结构", "n"),
        ("network security", "/ˈnetwɝːk sɪˈkjʊrəti/", "网络安全", "n"),
        ("access control", "/ˈækses kənˈtroʊl/", "访问控制", "n"),
        ("user interface", "/ˈjuːzər ˈɪntərfeɪs/", "用户界面", "n"),
        ("computer network", "/kəmˈpjuːtər ˈnetwɝːk/", "计算机网络", "n"),
        ("computer science", "/kəmˈpjuːtər ˈsaɪəns/", "计算机科学", "n"),
        ("computer program", "/kəmˈpjuːtər ˈproʊɡræm/", "计算机程序", "n"),
        (
            "information technology",
            "/ˌɪnfərˈmeɪʃən tekˈnɑːlədʒi/",
            "信息技术",
            "n",
        ),
        ("cloud computing", "/klaʊd kəmˈpjuːtɪŋ/", "云计算", "n"),
        ("big data", "/bɪɡ ˈdeɪtə/", "大数据", "n"),
        ("open source", "/ˈoʊpən sɔːrs/", "开源", "n"),
        ("pull request", "/pʊl rɪˈkwest/", "拉取请求", "n"),
        ("version control", "/ˈvɝːʒən kənˈtroʊl/", "版本控制", "n"),
        ("load balancer", "/loʊd ˈbælənsər/", "负载均衡器", "n"),
        ("virtual machine", "/ˈvɝːtʃuəl məˈʃiːn/", "虚拟机", "n"),
        ("file system", "/faɪl ˈsɪstəm/", "文件系统", "n"),
        (
            "application programming interface",
            "/ˌæplɪˈkeɪʃən ˈproʊɡræmɪŋ ˈɪntərfeɪs/",
            "应用接口",
            "n",
        ),
        (
            "random access memory",
            "/ˈrændəm ˈækses ˈmeməri/",
            "随机存储器",
            "n",
        ),
        ("read only memory", "/riːd ˈoʊnli ˈmeməri/", "只读存储器", "n"),
        (
            "central processing unit",
            "/ˈsentrəl ˈprɑːsesɪŋ ˈjuːnɪt/",
            "中央处理器",
            "n",
        ),
        (
            "graphical user interface",
            "/ˈɡræfɪkəl ˈjuːzər ˈɪntərfeɪs/",
            "图形界面",
            "n",
        ),
        ("local area network", "/ˈloʊkəl ˈeriə ˈnetwɝːk/", "局域网", "n"),
        ("wide area network", "/waɪd ˈeriə ˈnetwɝːk/", "广域网", "n"),
        ("internet protocol", "/ˈɪntərnet ˈproʊtəkɔːl/", "互联网协议", "n"),
        ("domain name", "/doʊˈmeɪn neɪm/", "域名", "n"),
        ("web server", "/web ˈsɝːvər/", "网络服务器", "n"),
        ("database server", "/ˈdeɪtəbeɪs ˈsɝːvər/", "数据库服务器", "n"),
        ("storage device", "/ˈstɔːrɪdʒ dɪˈvaɪs/", "存储设备", "n"),
        ("input device", "/ˈɪnpʊt dɪˈvaɪs/", "输入设备", "n"),
        ("output device", "/ˈaʊtpʊt dɪˈvaɪs/", "输出设备", "n"),
        ("security policy", "/sɪˈkjʊrəti ˈpɑːləsi/", "安全策略", "n"),
        ("data processing", "/ˈdeɪtə ˈprɑːsesɪŋ/", "数据处理", "n"),
        (
            "software engineering",
            "/ˈsɔːftwer ˌendʒɪˈnɪrɪŋ/",
            "软件工程",
            "n",
        ),
        (
            "system administrator",
            "/ˈsɪstəm ədˈmɪnɪstreɪtər/",
            "系统管理员",
            "n",
        ),
        (
            "network administrator",
            "/ˈnetwɝːk ədˈmɪnɪstreɪtər/",
            "网络管理员",
            "n",
        ),
        ("information system", "/ˌɪnfərˈmeɪʃən ˈsɪstəm/", "信息系统", "n"),
        ("control panel", "/kənˈtroʊl ˈpænəl/", "控制面板", "n"),
        ("task manager", "/tæsk ˈmænɪdʒər/", "任务管理器", "n"),
        ("search engine", "/sɝːtʃ ˈendʒɪn/", "搜索引擎", "n"),
        ("web browser", "/web ˈbraʊzər/", "网页浏览器", "n"),
        ("mobile application", "/ˈmoʊbəl ˌæplɪˈkeɪʃən/", "移动应用", "n"),
        (
            "software development",
            "/ˈsɔːftwer dɪˈveləpmənt/",
            "软件开发",
            "n",
        ),
        ("computer virus", "/kəmˈpjuːtər ˈvaɪrəs/", "计算机病毒", "n"),
        ("data security", "/ˈdeɪtə sɪˈkjʊrəti/", "数据安全", "n"),
        ("network protocol", "/ˈnetwɝːk ˈproʊtəkɔːl/", "网络协议", "n"),
        ("data center", "/ˈdeɪtə ˈsentər/", "数据中心", "n"),
        ("source file", "/sɔːrs faɪl/", "源文件", "n"),
        ("binary file", "/ˈbaɪnəri faɪl/", "二进制文件", "n"),
        ("text file", "/tekst faɪl/", "文本文件", "n"),
        ("web page", "/web peɪdʒ/", "网页", "n"),
        ("user account", "/ˈjuːzər əˈkaʊnt/", "用户账户", "n"),
        ("file format", "/faɪl ˈfɔːrmæt/", "文件格式", "n"),
        ("error message", "/ˈerər ˈmesɪdʒ/", "错误信息", "n"),
        ("system update", "/ˈsɪstəm ˈʌpdeɪt/", "系统更新", "n"),
        ("software update", "/ˈsɔːftwer ˈʌpdeɪt/", "软件更新", "n"),
        (
            "programming language",
            "/ˈproʊɡræmɪŋ ˈlæŋɡwɪdʒ/",
            "编程语言",
            "n",
        ),
        ("machine code", "/məˈʃiːn koʊd/", "机器码", "n"),
        ("network device", "/ˈnetwɝːk dɪˈvaɪs/", "网络设备", "n"),
        ("file transfer", "/faɪl ˈtrænsfɝː/", "文件传输", "n"),
        ("web service", "/web ˈsɝːvɪs/", "网络服务", "n"),
        ("front end", "/frʌnt end/", "前端", "n"),
        ("back end", "/bæk end/", "后端", "n"),
        ("software bug", "/ˈsɔːftwer bʌɡ/", "软件缺陷", "n"),
        ("program crash", "/ˈproʊɡræm kræʃ/", "程序崩溃", "n"),
        ("computer memory", "/kəmˈpjuːtər ˈmeməri/", "计算机内存", "n"),
        ("access permission", "/ˈækses pərˈmɪʃən/", "访问权限", "n"),
        ("file extension", "/faɪl ɪkˈstenʃən/", "文件扩展名", "n"),
        ("data model", "/ˈdeɪtə ˈmɑːdəl/", "数据模型", "n"),
        ("database table", "/ˈdeɪtəbeɪs ˈteɪbəl/", "数据库表", "n"),
        ("object code", "/ˈɑːbdʒekt koʊd/", "目标代码", "n"),
        ("command prompt", "/kəˈmænd prɑːmpt/", "命令提示符", "n"),
        ("terminal window", "/ˈtɝːmɪnəl ˈwɪndoʊ/", "终端窗口", "n"),
        ("program code", "/ˈproʊɡræm koʊd/", "程序代码", "n"),
        ("network packet", "/ˈnetwɝːk ˈpækɪt/", "网络数据包", "n"),
        ("security patch", "/sɪˈkjʊrəti pætʃ/", "安全补丁", "n"),
    ),
    "life": (),
    "travel": (
        ("travel agency", "/ˈtrævəl ˈeɪdʒənsi/", "旅行社", "n"),
        ("travel insurance", "/ˈtrævəl ɪnˈʃʊrəns/", "旅行保险", "n"),
        ("boarding pass", "/ˈbɔːrdɪŋ pæs/", "登机牌", "n"),
        ("baggage claim", "/ˈbæɡɪdʒ kleɪm/", "行李提取", "n"),
        ("round trip", "/raʊnd trɪp/", "往返行程", "n"),
        ("one way", "/wʌn weɪ/", "单程", "n"),
        ("departure time", "/dɪˈpɑːrtʃər taɪm/", "出发时间", "n"),
        ("arrival time", "/əˈraɪvəl taɪm/", "到达时间", "n"),
        ("passport control", "/ˈpæspɔːrt kənˈtroʊl/", "护照检查", "n"),
        (
            "customs declaration",
            "/ˈkʌstəmz ˌdekləˈreɪʃən/",
            "海关申报",
            "n",
        ),
        ("checked luggage", "/tʃekt ˈlʌɡɪdʒ/", "托运行李", "n"),
        ("carry on", "/ˈkæri ɑːn/", "随身行李", "n"),
        ("window seat", "/ˈwɪndoʊ siːt/", "靠窗座位", "n"),
        ("aisle seat", "/aɪl siːt/", "靠过道座位", "n"),
        ("one way ticket", "/wʌn weɪ ˈtɪkɪt/", "单程票", "n"),
        ("round trip ticket", "/raʊnd trɪp ˈtɪkɪt/", "往返票", "n"),
        ("train station", "/treɪn ˈsteɪʃən/", "火车站", "n"),
        ("bus station", "/bʌs ˈsteɪʃən/", "公交车站", "n"),
        ("subway station", "/ˈsʌbweɪ ˈsteɪʃən/", "地铁站", "n"),
        ("taxi stand", "/ˈtæksi stænd/", "出租车候车点", "n"),
        ("rental car", "/ˈrentəl kɑːr/", "租用车", "n"),
        ("tourist attraction", "/ˈtʊrɪst əˈtrækʃən/", "旅游景点", "n"),
        ("scenic spot", "/ˈsiːnɪk spɑːt/", "风景名胜", "n"),
        ("local cuisine", "/ˈloʊkəl kwɪˈziːn/", "当地美食", "n"),
        ("street food", "/striːt fuːd/", "街头小吃", "n"),
        ("travel guide", "/ˈtrævəl ɡaɪd/", "旅行指南", "n"),
        ("guided tour", "/ˈɡaɪdɪd tʊr/", "导览游览", "n"),
        ("souvenir shop", "/ˌsuːvəˈnɪr ʃɑːp/", "纪念品店", "n"),
        ("duty free", "/ˈduːti friː/", "免税的", "j"),
        ("room service", "/ruːm ˈsɝːvɪs/", "客房服务", "n"),
        ("front desk", "/frʌnt desk/", "前台", "n"),
        ("double room", "/ˈdʌbəl ruːm/", "双人房", "n"),
        ("single room", "/ˈsɪŋɡəl ruːm/", "单人房", "n"),
        ("wake up call", "/weɪk ʌp kɔːl/", "叫醒服务", "n"),
        ("travel document", "/ˈtrævəl ˈdɑːkjəmənt/", "旅行证件", "n"),
        ("visa application", "/ˈviːzə ˌæplɪˈkeɪʃən/", "签证申请", "n"),
        (
            "currency exchange",
            "/ˈkɝːənsi ɪksˈtʃeɪndʒ/",
            "货币兑换",
            "n",
        ),
        ("credit card", "/ˈkredɪt kɑːrd/", "信用卡", "n"),
        ("debit card", "/ˈdebɪt kɑːrd/", "借记卡", "n"),
        ("room key", "/ruːm kiː/", "房间钥匙", "n"),
        (
            "tourist information",
            "/ˈtʊrɪst ˌɪnfərˈmeɪʃən/",
            "游客信息",
            "n",
        ),
        ("travel route", "/ˈtrævəl ruːt/", "旅行路线", "n"),
        ("departure lounge", "/dɪˈpɑːrtʃər laʊndʒ/", "候机室", "n"),
        (
            "baggage allowance",
            "/ˈbæɡɪdʒ əˈlaʊəns/",
            "行李限额",
            "n",
        ),
        ("travel expense", "/ˈtrævəl ɪkˈspens/", "旅行费用", "n"),
        ("airport shuttle", "/ˈerpɔːrt ˈʃʌtəl/", "机场班车", "n"),
        (
            "hotel reservation",
            "/hoʊˈtel ˌrezərˈveɪʃən/",
            "酒店预订",
            "n",
        ),
        ("travel plan", "/ˈtrævəl plæn/", "旅行计划", "n"),
        ("travel agent", "/ˈtrævəl ˈeɪdʒənt/", "旅行代理", "n"),
        ("tourist visa", "/ˈtʊrɪst ˈviːzə/", "旅游签证", "n"),
        ("return ticket", "/rɪˈtɝːn ˈtɪkɪt/", "返程票", "n"),
        ("boarding gate", "/ˈbɔːrdɪŋ ɡeɪt/", "登机口", "n"),
        ("baggage cart", "/ˈbæɡɪdʒ kɑːrt/", "行李车", "n"),
        ("train ticket", "/treɪn ˈtɪkɪt/", "火车票", "n"),
        ("bus ticket", "/bʌs ˈtɪkɪt/", "公交车票", "n"),
        ("travel budget", "/ˈtrævəl ˈbʌdʒɪt/", "旅行预算", "n"),
        ("travel companion", "/ˈtrævəl kəmˈpænjən/", "旅伴", "n"),
        ("local guide", "/ˈloʊkəl ɡaɪd/", "当地导游", "n"),
        ("hotel lobby", "/hoʊˈtel ˈlɑːbi/", "酒店大堂", "n"),
        ("hotel room", "/hoʊˈtel ruːm/", "酒店客房", "n"),
    ),
}


SENTENCE_TEMPLATES: Dict[str, Dict[str, Sequence[str]]] = {
    "computer": {
        "n": (
            "这次系统升级重点处理了 {word} 相关的问题，团队已经记录在案。",
            "接口联调出现异常时，我们会逐项确认 {word} 的配置是否正确。",
            "新项目里会用到 {word}，文档里已经给出了具体说明。",
            "开发流程中如果忽略 {word}，后面很容易出现难以定位的问题。",
            "这套方案把 {word} 单独抽了出来，维护起来会更方便。",
            "版本发布前要再次核对 {word} 的配置，确认不会影响现有业务。",
            "准备上线时别忘了检查 {word}，很多故障都出在这个环节。",
            "发布窗口开始前，值班同事需要确认 {word} 已经达到预期状态。",
            "发布前检查清单里，必须包含 {word} 的状态确认，减少上线风险。",
            "培训新同事时，我会专门讲一下 {word} 的常见用法。",
            "日志里提到了 {word}，但还需要结合代码进一步分析。",
            "旧系统的 {word} 一直不稳定，我们准备在下个版本里统一整改。",
            "如果 {word} 设计得不合理，后期扩展和维护都会变得很麻烦。",
            "运维同事正在核对 {word} 的参数，确认没有遗漏关键配置。",
            "上线前先把 {word} 的影响范围评估清楚，再决定何时发布。",
            "客户反馈的问题最终定位到了 {word}，现在已经开始修复。",
            "文档里对 {word} 的说明不够详细，新人看半天也抓不住重点。",
            "迁移过程中要特别留意 {word}，否则可能造成数据不一致。",
            "这次故障复盘的重点之一，就是 {word} 为什么没有被提前发现。",
        ),
        "v": (
            "遇到这个报错时，我们先 {word} 一下，再继续排查系统问题。",
            "这个脚本会在任务开始前自动 {word}，减少人工操作。",
            "如果部署失败，可以重新 {word} 一次，看看错误是否复现。",
            "开发人员需要在提交代码前 {word}，确保改动符合规范。",
            "为了提升稳定性，服务会定期 {word} 并清理过期数据。",
            "测试环境里可以放心 {word}，正式环境必须提前审批。",
            "我发现程序卡住以后，手动 {word} 就能恢复正常。",
            "新人先学会怎么 {word}，再参与线上问题的处理。",
            "开发环境里可以先手动 {word}，确认结果符合预期再写进脚本。",
            "为了减少重复劳动，我们让流水线自动 {word} 每一步结果。",
            "交接文档里写清楚了怎么 {word}，新人照着做基本不会出错。",
            "系统异常时不要急着 {word}，先把现场日志完整保存下来。",
            "这个操作需要管理员权限，普通账号无法直接 {word}。",
            "上线之后如果指标异常，可以立即回滚，再重新 {word} 一次。",
            "我在本地反复 {word}，终于复现了客户反馈的那个问题。",
            "代码合并前需要自动 {word}，通过以后才能进入发布流程。",
        ),
        "j": (
            "这个模块的表现还不够 {word}，需要继续调整和测试。",
            "新版本在性能上更加 {word}，用户反馈也明显变好了。",
            "当系统处于 {word} 状态时，后台会触发对应的告警。",
            "代码评审时要重点看实现是否 {word}，不能只看功能。",
            "这套架构设计得很 {word}，后续扩展会轻松很多。",
            "接口返回的数据结构不够 {word}，前端处理起来很麻烦。",
            "监控面板显示系统整体比较 {word}，暂时不用处理。",
            "选择工具时要优先考虑 {word} 的方案，减少维护成本。",
            "旧版本响应很慢，新版本明显更加 {word}，值得尽快升级。",
            "这个错误信息不够 {word}，值班人员很难判断问题出在哪里。",
            "测试用例覆盖得比较 {word}，大部分边界情况都考虑到了。",
            "当前配置看起来不太 {word}，建议让熟悉系统的同事再看一遍。",
            "如果接口设计足够 {word}，前端和客户端就不用各写一套逻辑。",
            "性能压测结果显示服务比较 {word}，暂时没有明显瓶颈。",
            "日志格式保持 {word}，排查问题时能节省很多时间。",
            "数据量增长以后，原来的方案已经不够 {word}，必须重新设计。",
        ),
        "r": (
            "程序运行得很 {word}，暂时没有出现新的异常。",
            "任务已经 {word} 完成，监控指标也恢复了正常。",
            "数据同步完成后，页面会 {word} 展示最新结果。",
            "系统会自动 {word} 检测异常，并通知值班人员。",
            "这个服务 {word} 运行了半年，期间没有发生重大故障。",
            "请求量增加以后，接口仍然能 {word} 返回结果。",
            "日志被 {word} 写入磁盘，方便后续排查问题。",
            "部署脚本会 {word} 检查环境，避免配置遗漏。",
            "任务在后台 {word} 执行，不会影响用户当前的操作。",
            "收到告警后，值班人员 {word} 登录服务器开始排查。",
            "这个命令会 {word} 扫描目录，并输出所有异常文件。",
            "缓存失效以后，请求会 {word} 回源到数据库。",
            "升级过程中服务仍然 {word} 提供访问，没有出现中断。",
            "配置修改完成后，系统会 {word} 重新加载相关参数。",
            "日志被 {word} 上传到集中平台，方便团队统一分析。",
            "遇到高危漏洞时，补丁会 {word} 推送到所有生产机器。",
        ),
    },
    "life": {
        "n": (
            "最近我在生活里经常接触到 {word}，慢慢就弄懂了它的用法。",
            "说到日常生活，{word} 是很多人都绕不开的话题。",
            "这件事让我重新认识到 {word} 对生活的重要性。",
            "我和朋友聊了很久，话题最后又回到了 {word}。",
            "平时多留意 {word}，遇到问题时会从容很多。",
            "家里人一直提醒我要重视 {word}，以前我总不当回事。",
            "在普通的一天里，{word} 也可能带来意想不到的变化。",
            "如果要改善生活质量，可以从 {word} 开始慢慢调整。",
            "买菜的时候我才发现，{word} 对家庭开支的影响其实不小。",
            "邻居之间聊起 {word}，每个人都有自己的一套解决办法。",
            "学会安排 {word} 以后，我每天的时间不再那么混乱。",
            "这件事让我意识到，{word} 不能等到出问题才去重视。",
            "同事们午休时经常讨论 {word}，大家的看法差别很大。",
            "旅行回来以后，我对 {word} 有了和以前完全不同的理解。",
            "把 {word} 处理好，生活里很多烦心事都会少一大半。",
            "父母那一代对 {word} 很看重，我们却常常忽略它。",
        ),
        "v": (
            "遇到这种情况时，我通常会先 {word} 一下，再决定接下来的安排。",
            "这件事拖了很久，我决定今天就把它 {word} 掉。",
            "如果不知道怎么处理，不妨先试着 {word} 看看。",
            "他每次遇到麻烦都会主动 {word}，而不是一味抱怨。",
            "妈妈提醒我出门前别忘了 {word}，不然会耽误事情。",
            "只要愿意 {word}，很多生活里的小问题都能解决。",
            "朋友建议我先 {word}，等情绪稳定后再继续沟通。",
            "与其一直犹豫，不如现在就开始 {word}，边做边调整。",
            "我准备这周末把这件事 {word} 完，免得一直惦记。",
            "如果你愿意耐心 {word}，结果可能会比现在好很多。",
            "遇到矛盾时先别急着发火，试着 {word} 对方的感受。",
            "他忙了一整天，终于把拖了很久的事情 {word} 好了。",
            "我可以陪你一起 {word}，这样遇到问题也方便商量。",
            "与其抱怨现状，不如马上动手 {word}，先改变一点点。",
            "老师建议我们每天 {word} 几分钟，久而久之会有明显变化。",
            "这件事不能只靠一个人，需要大家一起 {word} 才能完成。",
        ),
        "j": (
            "今天发生这件事以后，我心里一直有点 {word}，说不清为什么。",
            "他最近的状态看起来比较 {word}，可能需要好好休息。",
            "大家都觉得这个结果很 {word}，讨论时也特别有共鸣。",
            "面对突如其来的变化，保持 {word} 其实并不容易。",
            "事情虽然没有想象中顺利，但整体还算 {word}。",
            "一个人的时候，我更容易察觉到自己是 {word} 的。",
            "朋友安慰我说，偶尔感到 {word} 其实也很正常。",
            "经历得越多，越能理解为什么有人会显得那么 {word}。",
            "收到那封邮件以后，我一整天都觉得很 {word}，做什么都提不起劲。",
            "虽然结果不理想，但大家的心态还算 {word}，没有互相埋怨。",
            "听到别人这样评价自己，他心里多少有些 {word}。",
            "这段时间过得比较 {word}，我需要找机会放松一下。",
            "站在陌生城市的街头，我突然有种很 {word} 的感觉。",
            "她对未来一直保持 {word} 的态度，很少被困难吓退。",
            "面对家人的期待，他感到既 {word} 又不知道该怎么表达。",
            "连续遇到几件麻烦事以后，我难免有点 {word}。",
        ),
        "r": (
            "他处理这件事时显得很 {word}，大家都看在眼里。",
            "我最近 {word} 调整了作息，感觉精神状态好多了。",
            "做完决定以后，心里反而 {word} 平静了下来。",
            "遇到分歧时，如果能 {word} 沟通，结果通常会更好。",
            "她 {word} 完成了每天的计划，生活也变得更有规律。",
            "面对压力，他仍然能 {word} 保持自己的节奏。",
            "这件事我 {word} 想明白了，不再像之前那样纠结。",
            "养成习惯以后，生活中很多好的改变会 {word} 发生。",
            "做完运动以后，我整个人 {word} 放松了下来。",
            "遇到不懂的问题，他会 {word} 向有经验的同事请教。",
            "我们 {word} 聊了两个小时，很多误会终于解开了。",
            "她每天 {word} 记录开销，月底一看就知道钱花在哪里。",
            "只要提前计划好，很多事情都能 {word} 完成。",
            "听到这个好消息，家里人 {word} 高兴了好几天。",
            "他 {word} 接受了批评，并表示以后会认真注意。",
            "把心里的话说出来以后，我 {word} 觉得轻松多了。",
        ),
    },
    "travel": {
        "n": (
            "这次旅途中，{word} 给我留下了很深的印象。",
            "出发前我们专门查了 {word}，想提前做好准备。",
            "当地工作人员耐心解释了 {word} 的相关规定。",
            "如果遇到和 {word} 有关的问题，可以找服务台帮忙。",
            "这次行程的预算里已经包含了 {word} 的费用。",
            "很多游客都会关心 {word}，所以网上攻略写得特别详细。",
            "导游提醒我们注意 {word}，避免在旅途中遇到麻烦。",
            "我在旅途中第一次真正体会到 {word} 的重要性。",
            "在机场排队时，我第一次注意到 {word} 原来有这么多规定。",
            "这次出门时间比较紧，{word} 成了大家最关心的问题。",
            "服务台的工作人员详细介绍了 {word} 的办理流程。",
            "如果提前了解 {word}，旅途中能少走很多弯路。",
            "同团游客正在讨论 {word}，有人赞成也有人反对。",
            "我拍下 {word} 的照片，准备回去给家人看看。",
            "这次意外让我意识到，{word} 在旅行中有多重要。",
            "飞机晚点以后，{word} 的安排全部需要重新调整。",
        ),
        "v": (
            "旅途中如果遇到特殊情况，可以先 {word} 再联系工作人员。",
            "出发前记得 {word}，免得到了现场才发现准备不足。",
            "到达当地以后，我们打算先 {word}，然后再开始游玩。",
            "如果需要调整计划，最好提前 {word}，不要等到最后一刻。",
            "导游建议我们在这里 {word}，稍作休息再继续赶路。",
            "遇到航班变化时，可以主动 {word}，争取更合适的安排。",
            "游客通常会在出发前 {word}，以免耽误后面的行程。",
            "只要按规定 {word}，大多数问题都能顺利解决。",
            "到了景区门口，我们决定先 {word} 再买票进去。",
            "酒店前台提醒客人必须提前 {word}，否则房间可能被取消。",
            "如果语言不通，可以请工作人员帮忙 {word}。",
            "为了节省时间，我们在出发前就把这些事情 {word} 好了。",
            "遇到突发状况时，保持冷静再 {word} 往往更有效。",
            "他第一次独自出国，很多事情都要自己 {word}。",
            "导游让我们在原地稍等，他去帮大家 {word}。",
            "行程发生变化以后，我们只能临时 {word} 后面的安排。",
        ),
        "j": (
            "这次行程让我觉得当地的服务非常 {word}，印象很不错。",
            "酒店的住宿条件比较 {word}，住起来还挺舒服。",
            "这个景点在旺季会显得特别 {word}，最好早点过去。",
            "网友说当地交通很 {word}，自由行基本没有压力。",
            "那家餐厅的价格不算便宜，但味道确实很 {word}。",
            "如果天气条件比较 {word}，户外活动可能会临时取消。",
            "导游推荐的路线非常 {word}，老人和孩子也能走下来。",
            "出门旅行时选一个 {word} 的时间，体验会好很多。",
            "一路上的指示牌比较 {word}，第一次来的人也能看懂。",
            "这家民宿的房间虽然不大，但布置得很 {word}。",
            "旺季的时候景点特别 {word}，拍照很难找到空位。",
            "当地司机开车比较 {word}，坐久了会有点不舒服。",
            "这家餐厅服务很 {word}，等位的时候还提供茶水。",
            "雨天的山路有些 {word}，司机开得格外小心。",
            "景区门票价格不算 {word}，一家人都能接受。",
            "出发前查到的交通信息很 {word}，帮了我们大忙。",
        ),
        "r": (
            "我们按照计划 {word} 前进，沿途风景也特别漂亮。",
            "这趟旅程安排得 {word}，几乎每件事都很顺利。",
            "到达酒店以后，大家 {word} 办理了入住手续。",
            "如果时间允许，我希望能 {word} 体验当地生活。",
            "工作人员 {word} 解答了我们的问题，态度也很友好。",
            "出发前我们一定要 {word} 检查证件和行李，免得遗漏东西。",
            "天气变化得很快，最好 {word} 调整后面的行程。",
            "这次自由行虽然有点累，但整体过得很 {word}。",
            "我们比预定时间 {word} 到达，刚好赶上第一班车。",
            "需要办理手续时，工作人员会 {word} 提供帮助。",
            "行李准备好以后，我们 {word} 出发去机场办理手续。",
            "遇到天气突然变化，导游会 {word} 调整后面的行程。",
            "这趟旅行安排得 {word}，大家几乎没有浪费等待时间。",
            "如果时间允许，我希望能 {word} 体验当地人的日常生活。",
            "登机口变更以后，广播 {word} 通知了所有乘客。",
            "回酒店的路上，我们 {word} 聊起白天的见闻。",
        ),
    },
}


@dataclass(frozen=True)
class Candidate:
    word: str
    phonetic: str
    meaning: str
    pos: str
    rank: int
    oxford: bool
    definition: str
    translation: str
    exchange: str


class BuildError(ValueError):
    """Raised when source data cannot satisfy a requested deck size."""


def parse_meaning(translation: str) -> Optional[str]:
    lines = (translation or "").splitlines()
    for line in lines:
        candidate_line = BRACKET_RE.sub(" ", line.strip())
        candidate_line = POS_PREFIX_RE.sub("", candidate_line)

        for part in re.split(r"[；;，,]", candidate_line):
            part = BRACKET_RE.sub("", part)
            sequences = HAN_SEQUENCE_RE.findall(part)
            for sequence in sequences:
                if len(sequence) < 2:
                    continue
                meaning = sequence[:6]
                if (
                    meaning in BAD_MEANINGS
                    or meaning.startswith("的")
                    or meaning.endswith("的变形")
                ):
                    continue
                return meaning
    return None


def parse_pos(translation: str) -> Optional[str]:
    lines = (translation or "").splitlines()
    if not lines:
        return None
    first_line = lines[0].strip().lower()
    if re.match(r"^(vt|vi|v)\.", first_line):
        return "v"
    if re.match(r"^(a|adj)\.", first_line):
        return "j"
    if re.match(r"^adv\.", first_line):
        return "r"
    if re.match(r"^n\.", first_line):
        return "n"
    return None


def normalize_phonetic(phonetic: str) -> Optional[str]:
    phonetic = (phonetic or "").strip().strip('"')
    phonetic = re.split(r"[,;，；]", phonetic, maxsplit=1)[0].strip()
    phonetic = phonetic.strip("/")
    phonetic = re.sub(r"\s+", " ", phonetic)
    if not phonetic or len(phonetic) > 60:
        return None
    return "/{}/".format(phonetic)


def frequency_rank(bnc: str, frq: str) -> int:
    ranks: List[int] = []
    for value in (bnc, frq):
        if value and value.isdigit() and int(value) > 0:
            ranks.append(int(value))
    return min(ranks) if ranks else 10**9


def load_candidates(path: Path) -> List[Candidate]:
    candidates: List[Candidate] = []
    seen = set()

    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            word = " ".join((row.get("word") or "").split())
            word_key = word.casefold()
            if not word or word_key in seen:
                continue
            if not VALID_WORD_RE.fullmatch(word):
                continue

            phonetic = normalize_phonetic(row.get("phonetic") or "")
            meaning = parse_meaning(row.get("translation") or "")
            pos = parse_pos(row.get("translation") or "")
            if not phonetic or not meaning or not pos:
                continue

            seen.add(word_key)
            candidates.append(
                Candidate(
                    word=word,
                    phonetic=phonetic,
                    meaning=meaning,
                    pos=pos,
                    rank=frequency_rank(row.get("bnc") or "", row.get("frq") or ""),
                    oxford=row.get("oxford") == "1",
                    definition=(row.get("definition") or "").lower(),
                    translation=row.get("translation") or "",
                    exchange=row.get("exchange") or "",
                )
            )

    return candidates


def is_base_form(candidate: Candidate) -> bool:
    return "0:" not in candidate.exchange and "1:" not in candidate.exchange


def relevance_score(candidate: Candidate, domain: DomainConfig) -> int:
    word = candidate.word.lower()
    text = candidate.definition + "\n" + candidate.translation.lower()
    word_hit = 20 if word in domain.seeds else 0
    seed_hits = sum(1 for seed in domain.seeds if seed in text)
    marker_hits = sum(
        1 for marker in domain.chinese_markers if marker in candidate.translation
    )
    return (
        word_hit
        + min(seed_hits, 6) * 3
        + min(marker_hits, 3) * 4
        + (3 if candidate.oxford else 0)
    )


def select_candidates(
    candidates: Sequence[Candidate],
    domain: DomainConfig,
) -> List[Candidate]:
    if domain.key == "life":
        pool = [
            candidate
            for candidate in candidates
            if candidate.oxford
            and is_base_form(candidate)
            and candidate.word.casefold() not in LIFE_STOP_WORDS
        ]
        pool.sort(key=lambda item: (item.rank, item.word.casefold()))

        if len(pool) < domain.target_count:
            selected_words = {candidate.word.casefold() for candidate in pool}
            supplements = [
                candidate
                for candidate in candidates
                if is_base_form(candidate)
                and candidate.word.casefold() not in LIFE_STOP_WORDS
                and candidate.word.casefold() not in selected_words
            ]
            supplements.sort(key=lambda item: (item.rank, item.word.casefold()))
            pool.extend(
                supplements[: domain.target_count - len(pool)]
            )
    else:
        pool = [
            candidate
            for candidate in candidates
            if is_base_form(candidate)
            and any(
                seed in candidate.definition
                or seed in candidate.translation.lower()
                for seed in domain.seeds
            )
        ]
        pool.sort(
            key=lambda item: (
                -relevance_score(item, domain),
                item.rank,
                len(item.word),
                item.word.casefold(),
            )
        )

    selected = pool[: domain.target_count]
    selected_words = {candidate.word.casefold() for candidate in selected}

    for word, phonetic, meaning, pos in FALLBACK_ENTRIES[domain.key]:
        if len(selected) >= domain.target_count:
            break
        word_key = word.casefold()
        if word_key in selected_words:
            continue
        selected.append(
            Candidate(
                word=word,
                phonetic=phonetic,
                meaning=meaning,
                pos=pos,
                rank=0,
                oxford=False,
                definition="",
                translation=meaning,
                exchange="",
            )
        )
        selected_words.add(word_key)

    if len(selected) < domain.target_count:
        raise BuildError(
            "{} 领域只有 {} 个候选词，无法生成 {} 个词条".format(
                domain.key, len(selected), domain.target_count
            )
        )

    return selected


def sentence_for(
    candidate: Candidate,
    domain_key: str,
    used_patterns: set,
) -> str:
    is_special = (
        domain_key == "life"
        and candidate.word.casefold() in SPECIAL_LIFE_WORDS
    )
    if is_special:
        templates = SPECIAL_LIFE_TEMPLATES
    else:
        templates = SENTENCE_TEMPLATES[domain_key][candidate.pos]

    pattern_group = "special" if is_special else candidate.pos
    openers = SENTENCE_OPENERS[domain_key]
    closers = SENTENCE_CLOSERS[domain_key]
    total_patterns = len(templates) * len(openers) * len(closers)
    start = zlib.crc32(candidate.word.casefold().encode("utf-8")) % total_patterns

    pattern_index = start
    for _ in range(total_patterns):
        pattern_key = (pattern_group, pattern_index)
        if pattern_key in used_patterns:
            pattern_index = (pattern_index + 1) % total_patterns
            continue

        template_index = pattern_index % len(templates)
        opener_index = (pattern_index // len(templates)) % len(openers)
        closer_index = (
            pattern_index // (len(templates) * len(openers))
        ) % len(closers)

        core = templates[template_index].format(word=candidate.word).rstrip("。")
        sentence = "{}{}，{}。".format(
            openers[opener_index],
            core,
            closers[closer_index],
        )
        han_count = sum(
            len(sequence)
            for sequence in HAN_SEQUENCE_RE.findall(sentence)
        )
        if 15 <= han_count <= 40:
            used_patterns.add(pattern_key)
            return sentence

        pattern_index = (pattern_index + 1) % total_patterns
    else:
        raise BuildError(
            "{} 的 {} 类例句组合已经用完".format(domain_key, candidate.pos)
        )


def write_deck(domain: DomainConfig, candidates: Sequence[Candidate]) -> None:
    output_path = DECKS_DIR / "{}.csv".format(domain.key)
    used_patterns: set = set()
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["中文句", "英文词", "音标", "中文释义", "完整句"])

        for candidate in candidates:
            sentence = SENTENCE_OVERRIDES.get(
                (domain.key, candidate.word.casefold()),
                sentence_for(
                    candidate,
                    domain.key,
                    used_patterns,
                ),
            )
            meaning = MEANING_OVERRIDES.get(
                (domain.key, candidate.word.casefold()),
                candidate.meaning,
            )
            writer.writerow(
                [
                    sentence,
                    candidate.word,
                    candidate.phonetic,
                    meaning,
                    sentence,
                ]
            )

    print("已生成 {}：{} 个词条".format(output_path, len(candidates)))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="从 ECDICT CSV 生成三个领域的 Anki 词表"
    )
    parser.add_argument(
        "--ecdict",
        type=Path,
        default=Path(os.environ.get("ECDICT_CSV", "/tmp/ecdict.csv")),
        help="ECDICT CSV 文件路径，默认读取 ECDICT_CSV 环境变量或 /tmp/ecdict.csv",
    )
    args = parser.parse_args(argv)

    if not args.ecdict.is_file():
        print("找不到 ECDICT 文件：{}".format(args.ecdict), file=sys.stderr)
        return 1

    try:
        all_candidates = load_candidates(args.ecdict)
        DECKS_DIR.mkdir(parents=True, exist_ok=True)

        for domain in DOMAINS:
            selected = select_candidates(all_candidates, domain)
            write_deck(domain, selected)
    except BuildError as exc:
        print("词表生成失败：{}".format(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
