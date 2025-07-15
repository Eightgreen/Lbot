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
        {"name": "前段北護側", "spots": [str(i) for i in range(1, 27)]},
        {"name": "中段北護側", "spots": [str(i) for i in range(29, 44)]},
        {"name": "後段北護側", "spots": [str(i) for i in range(45, 49)]},
        {"name": "前段住戶側", "spots": [str(i) for i in range(69, 76)]},
        {"name": "中段住戶側", "spots": [str(i) for i in range(61, 68)]},
        {"name": "後段住戶側", "spots": [str(i) for i in range(50, 57)]}
    ],
    "1124000": [  # 明德路
        {"name": "振興一側", "spots": [str(i) for i in range(67, 93)]},
        {"name": "住戶側貨車停車格", "spots": ["119"]},
        {"name": "北護一側", "spots": [str(i) for i in range(110, 117)]}
    ],
    "112400A": [  # 明德路A
        {"name": "前段振興側", "spots": [str(i) for i in range(62, 65)]},
        {"name": "前段住戶側", "spots": [str(i) for i in range(119, 125)]},
        {"name": "後段振興側", "spots": ["60"]},
        {"name": "後段住戶側", "spots": [str(i) for i in range(125, 128)]}
    ],
    "1335000": [  # 裕民六路
        {"name": "萊爾富", "spots": ["18", "19", "20", "25", "26", "27", "39"]},
        {"name": "捷運那段", "spots": [str(i) for i in range(28, 38)] + ["1", "2"]}
    ],
    "1335114": [  # 裕民六路114巷
        {"name": "50元萊爾富", "spots": ["1", "2"]},
        {"name": "50元7-11側", "spots": [str(i) for i in range(6, 14)]},
        {"name": "50元停車場側", "spots": [str(i) for i in range(15, 24)]}
    ],
    "114100A": [  # 裕民二路
        {"name": "50元停車場段", "spots": [str(i) for i in chain(range(5, 11), range(34, 38), range(44, 49))] + ["51"]},
        {"name": "50元熱炒店對面", "spots": [str(i) for i in range(25, 33)]},
        {"name": "50元熱炒店", "spots": ["12"] + [str(i) for i in range(14, 22)]},
        {"name": "全聯一側", "spots": ["58", "61", "62A"]}
    ],
    "1141049": [  # 裕民二路49巷
        {"name": "全段", "spots": [str(i) for i in range(1, 12)]}
    ],
    "1131000": [  # 奎山國小周邊
        {"name": "50元國小後面", "spots": [str(i) for i in range(10, 19)]},
        {"name": "50元小巷", "spots": [str(i) for i in range(21, 26)]},
        {"name": "50元國小後面左轉", "spots": [str(i) for i in range(27, 29)]}
    ],
    "1131198": [  # 榮華二路19巷8弄
        {"name": "50元國小後面住戶", "spots": ["1", "2"]}
    ],
    "40730A0": [  # 水源路A
        {"name": "國興國宅段", "spots": [str(i) for i in chain(range(4, 11), range(13, 21), range(25, 33))] + ["10A"]},
        {"name": "公園管理處", "spots": [str(i) for i in chain(range(39, 45), range(47, 55))]},
        {"name": "青年公園後段", "spots": [str(i) for i in chain(range(56, 74), range(77, 81))]}
    ],
    "4091000": [  # 青年路
        {"name": "公園一側", "spots": [str(i) for i in chain(range(63, 66), range(68, 78), range(80, 98), range(99, 103))]},
        {"name": "公園對面", "spots": ["1"] + [str(i) for i in range(3, 11)]},
        {"name": "中間穿過到棒球段", "spots": ["25"] + [str(i) for i in chain(range(41, 44), range(49, 50))]},
        {"name": "最遠的網球段", "spots": [str(i) for i in chain(range(56, 74), range(77, 81))]}
    ],
    "4023000": [  # 中華路2段
        {"name": "全聯對面", "spots": [str(i) for i in chain(range(65, 70), range(75, 76))]},
        {"name": "全聯一側", "spots": ["58", "61", "62A"]},
        {"name": "四海遊龍對面", "spots": [str(i) for i in chain(range(77, 80), range(82, 83), range(85, 87))]},
        {"name": "四海遊龍一側", "spots": [str(i) for i in chain(range(42, 45), range(48, 54))]},
        {"name": "夜市對面前段", "spots": [str(i) for i in chain(range(21, 30))]},
        {"name": "夜市一側", "spots": ["95", "96"]},
        {"name": "夜市對面中段", "spots": [str(i) for i in chain(range(12, 13), range(15, 16), range(19, 20))]},
        {"name": "夜市一側尾", "spots": ["11"]},
        {"name": "夜市對面後段", "spots": ["1"] + [str(i) for i in chain(range(4, 5), range(7, 10))]}
    ],
    "4117000": [  # 國興路
        {"name": "高爾夫段", "spots": [str(i) for i in chain(range(30, 43))]},
        {"name": "幼兒園段", "spots": [str(i) for i in chain(range(3, 8), range(10, 18))]},
        {"name": "幼兒園對面", "spots": [str(i) for i in chain(range(19, 28))]}
    ],
    "4023416": [  # 中華路2段416巷
        {"name": "美聯社右轉", "spots": [str(i) for i in chain(range(24, 30))]},
        {"name": "美聯社左轉", "spots": [str(i) for i in chain(range(1, 5), [11, 13], range(15, 18), range(21, 22))]}
    ],
    "4023364": [  # 中華路二段364巷17弄及24弄
        {"name": "美聯社直走", "spots": [str(i) for i in chain([12, 14], range(20, 23))]},
        {"name": "美聯社直走左轉", "spots": [str(i) for i in chain(range(7, 8))]}
    ],
    "5300000": [  # 雙和街
        {"name": "美聯社直走左轉", "spots": [str(i) for i in chain([12, 13, 17, 18, 19, 24])]}
    ],
    "4023300": [  # 中華路2段300巷13弄
        {"name": "美聯社直走到底", "spots": [str(i) for i in chain([2, 6], range(43, 46), [48])]}
    ]
}