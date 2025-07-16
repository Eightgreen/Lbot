from itertools import chain

address_to_segment = {
    "明德路337巷": [{"id": "1124337", "name": "明德路337巷"}],
    "明德路": [{"id": "1124000", "name": "明德路"}],
    "明德路A": [{"id": "112400A", "name": "明德路A"}],
    "裕民六路": [{"id": "1335000", "name": "裕民六路"}],
    "裕民六路114巷": [{"id": "1335114", "name": "裕民六路114巷"}],
    "裕民二路": [{"id": "114100A", "name": "裕民二路"}],
    "裕民二路49巷": [{"id": "1141049", "name": "裕民二路49巷"}],
    "奎山國小周邊": [{"id": "1131000", "name": "奎山國小周邊"}],
    "榮華二路19巷8弄": [{"id": "1131198", "name": "榮華二路19巷8弄"}],
    "水源路A": [{"id": "40730A0", "name": "水源路A"}],
    "青年路": [{"id": "4091000", "name": "青年路"}],
    "中華路2段": [{"id": "4023000", "name": "中華路2段"}],
    "國興路": [{"id": "4117000", "name": "國興路"}],
    "中華路2段416巷": [{"id": "4023416", "name": "中華路2段416巷"}],
    "中華路二段364巷17弄及24弄": [{"id": "4023364", "name": "中華路二段364巷17弄及24弄"}],
    "雙和街": [{"id": "5300000", "name": "雙和街"}],
    "中華路2段300巷13弄": [{"id": "4023300", "name": "中華路2段300巷13弄"}],
    "裕民": [
        {"id": "1335000", "name": "裕民六路"},
        {"id": "1335114", "name": "裕民六路114巷"},
        {"id": "114100A", "name": "裕民二路"},
        {"id": "1141049", "name": "裕民二路49巷"}
    ],
    "明德": [
        {"id": "1124337", "name": "明德路337巷"},
        {"id": "1124000", "name": "明德路"},
        {"id": "112400A", "name": "明德路A"}
    ],
    "回家": [
        {"id": "1124337", "name": "明德路337巷"},
        {"id": "1124000", "name": "明德路"},
        {"id": "112400A", "name": "明德路A"},
        {"id": "1335000", "name": "裕民六路"},
        {"id": "1335114", "name": "裕民六路114巷"},
        {"id": "114100A", "name": "裕民二路"},
        {"id": "1141049", "name": "裕民二路49巷"},
        {"id": "1131000", "name": "奎山國小周邊"},
        {"id": "1131198", "name": "榮華二路19巷8弄"}
    ],
    "回家計次": [
        {"id": "1335114", "name": "裕民六路114巷"},
        {"id": "114100A", "name": "裕民二路"},
        {"id": "1131000", "name": "奎山國小周邊"},
        {"id": "1131198", "name": "榮華二路19巷8弄"}
    ],
    "青年公園": [
        {"id": "40730A0", "name": "水源路A"},
        {"id": "4091000", "name": "青年路"},
        {"id": "4023000", "name": "中華路2段"},
        {"id": "4117000", "name": "國興路"},
        {"id": "4023416", "name": "中華路2段416巷"},
        {"id": "4023364", "name": "中華路二段364巷17弄及24弄"},
        {"id": "5300000", "name": "雙和街"},
        {"id": "4023300", "name": "中華路2段300巷13弄"}
    ]
}

group_config = {
    "1124337": [  # 明德路337巷
        {"name": "前段北護側", "spots": [str(i) for i in range(1, 28)]},
        {"name": "中段北護側", "spots": [str(i) for i in range(29, 45)]},
        {"name": "後段北護側", "spots": [str(i) for i in range(45, 50)]},
        {"name": "前段住戶側", "spots": [str(i) for i in range(69, 77)]},
        {"name": "中段住戶側", "spots": [str(i) for i in range(61, 69)]},
        {"name": "後段住戶側", "spots": [str(i) for i in range(50, 58)]}
    ],
    "1124000": [  # 明德路
        {"name": "振興一側", "spots": [str(i) for i in range(67, 94)]},
        {"name": "住戶側貨車停車格", "spots": ["119"]},
        {"name": "北護一側", "spots": [str(i) for i in range(110, 118)]}
    ],
    "112400A": [  # 明德路A
        {"name": "前段振興側", "spots": [str(i) for i in range(62, 66)]},
        {"name": "前段住戶側", "spots": [str(i) for i in range(119, 126)]},
        {"name": "後段振興側", "spots": ["60"]},
        {"name": "後段住戶側", "spots": [str(i) for i in range(125, 129)]}
    ],
    "1335000": [  # 裕民六路
        {"name": "萊爾富", "spots": ["18", "19", "20", "25", "26", "27", "39"]},
        {"name": "捷運那段", "spots": [str(i) for i in range(28, 39)] + ["1", "2"]}
    ],
    "1335114": [  # 裕民六路114巷
        {"name": "50元萊爾富", "spots": ["1", "2"]},
        {"name": "50元7-11側", "spots": [str(i) for i in range(6, 15)]},
        {"name": "50元停車場側", "spots": [str(i) for i in range(15, 25)]}
    ],
    "114100A": [  # 裕民二路
        {"name": "50元停車場段", "spots": [str(i) for i in chain(range(5, 12), range(34, 39), range(44, 50))] + ["51"]},
        {"name": "50元熱炒店對面", "spots": [str(i) for i in range(25, 34)]},
        {"name": "50元熱炒店", "spots": ["12"] + [str(i) for i in range(14, 23)]},
        {"name": "全聯一側", "spots": ["58", "61", "62A"]}
    ],
    "1141049": [  # 裕民二路49巷
        {"name": "全段", "spots": [str(i) for i in range(1, 13)]}
    ],
    "1131000": [  # 奎山國小周邊
        {"name": "50元國小後面", "spots": [str(i) for i in range(10, 20)]},
        {"name": "50元小巷", "spots": [str(i) for i in range(21, 27)]},
        {"name": "50元國小後面左轉", "spots": [str(i) for i in range(27, 30)]}
    ],
    "1131198": [  # 榮華二路19巷8弄
        {"name": "50元國小後面住戶", "spots": ["1", "2"]}
    ],
    "40730A0": [  # 水源路A
        {"name": "國興國宅段", "spots": [str(i) for i in chain(range(4, 12), range(13, 22), range(25, 34))] + ["10A"]},
        {"name": "公園管理處", "spots": [str(i) for i in chain(range(39, 46), range(47, 56))]},
        {"name": "青年公園後段", "spots": [str(i) for i in chain(range(56, 75), range(77, 82))]}
    ],
    "4091000": [  # 青年路
        {"name": "公園一側", "spots": [str(i) for i in chain(range(63, 67), range(68, 79), range(80, 99), range(99, 104))]},
        {"name": "公園對面", "spots": ["1"] + [str(i) for i in range(3, 12)]},
        {"name": "中間穿過到棒球段", "spots": ["25"] + [str(i) for i in chain(range(41, 45), range(49, 51))]},
        {"name": "最遠的網球段", "spots": [str(i) for i in chain(range(56, 75), range(77, 82))]}
    ],
    "4023000": [  # 中華路2段
        {"name": "全聯對面", "spots": [str(i) for i in chain(range(65, 71), range(75, 77))]},
        {"name": "全聯一側", "spots": ["58", "61", "62A"]},
        {"name": "四海遊龍對面", "spots": [str(i) for i in chain(range(77, 81), range(82, 84), range(85, 88))]},
        {"name": "四海遊龍一側", "spots": [str(i) for i in chain(range(42, 46), range(48, 55))]},
        {"name": "夜市對面前段", "spots": [str(i) for i in chain(range(21, 31))]},
        {"name": "夜市一側", "spots": ["95", "96"]},
        {"name": "夜市對面中段", "spots": [str(i) for i in chain(range(12, 14), range(15, 17), range(19, 21))]},
        {"name": "夜市一側尾", "spots": ["11"]},
        {"name": "夜市對面後段", "spots": ["1"] + [str(i) for i in chain(range(4, 6), range(7, 11))]}
    ],
    "4117000": [  # 國興路
        {"name": "高爾夫段", "spots": [str(i) for i in chain(range(30, 44))]},
        {"name": "幼兒園段", "spots": [str(i) for i in chain(range(3, 9), range(10, 19))]},
        {"name": "幼兒園對面", "spots": [str(i) for i in chain(range(19, 29))]}
    ],
    "4023416": [  # 中華路2段416巷
        {"name": "美聯社右轉", "spots": [str(i) for i in chain(range(24, 31))]},
        {"name": "美聯社左轉", "spots": [str(i) for i in chain(range(1, 6), [11, 13], range(15, 19), range(21, 23))]}
    ],
    "4023364": [  # 中華路二段364巷17弄及24弄
        {"name": "美聯社直走", "spots": [str(i) for i in chain([12, 14], range(20, 24))]},
        {"name": "美聯社直走左轉", "spots": [str(i) for i in chain(range(7, 9))]}
    ],
    "5300000": [  # 雙和街
        {"name": "美聯社直走左轉", "spots": [str(i) for i in chain([12, 13, 17, 18, 19, 24])]}
    ],
    "4023300": [  # 中華路2段300巷13弄
        {"name": "美聯社直走到底", "spots": [str(i) for i in chain([2, 6], range(43, 47), [48])]}
    ]
}