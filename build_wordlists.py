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
            "排查线上故障时，我们首先检查 {word} 的配置是否正确。",
            "新项目里会用到 {word}，文档里已经给出了具体说明。",
            "开发流程中如果忽略 {word}，后面很容易出现难以定位的问题。",
            "这套方案把 {word} 单独抽了出来，维护起来会更方便。",
            "部署之前要确认 {word} 的状态，避免影响正常业务。",
            "培训新同事时，我会专门讲一下 {word} 的常见用法。",
            "日志里提到了 {word}，但还需要结合代码进一步分析。",
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


def sentence_for(candidate: Candidate, domain_key: str) -> str:
    if (
        domain_key == "life"
        and candidate.word.casefold() in SPECIAL_LIFE_WORDS
    ):
        index = zlib.crc32(candidate.word.casefold().encode("utf-8"))
        return SPECIAL_LIFE_TEMPLATES[index % len(SPECIAL_LIFE_TEMPLATES)].format(
            word=candidate.word
        )

    templates = SENTENCE_TEMPLATES[domain_key][candidate.pos]
    index = zlib.crc32(candidate.word.casefold().encode("utf-8")) % len(templates)
    return templates[index].format(word=candidate.word)


def write_deck(domain: DomainConfig, candidates: Sequence[Candidate]) -> None:
    output_path = DECKS_DIR / "{}.csv".format(domain.key)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["中文句", "英文词", "音标", "中文释义", "完整句"])

        for candidate in candidates:
            sentence = sentence_for(candidate, domain.key)
            writer.writerow(
                [
                    sentence,
                    candidate.word,
                    candidate.phonetic,
                    candidate.meaning,
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
