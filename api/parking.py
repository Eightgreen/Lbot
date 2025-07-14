import os
import requests
import logging
import json
import time
import re
from itertools import chain
from datetime import datetime, timezone

# 設置日誌記錄，方便除錯
logger = logging.getLogger(__name__)

class Auth:
    def __init__(self, app_id, app_key):
        # 初始化認證物件，儲存 TDX API 的 Client ID 和 Client Secret
        self.app_id = app_id
        self.app_key = app_key

    def get_auth_header(self):
        # 生成取得 Access Token 所需的請求標頭
        return {
            'content-type': 'application/x-www-form-urlencoded',
            'grant_type': 'client_credentials',
            'client_id': self.app_id,
            'client_secret': self.app_key
        }

class ParkingFinder:
    def __init__(self):
        # 初始化 ParkingFinder，設定預設城市、地址映射、群組配置和自訂集合
        # 從環境變數獲取 TDX API 金鑰
        self.app_id = os.getenv("TDX_APP_ID")
        self.app_key = os.getenv("TDX_APP_KEY")
        if not self.app_id or not self.app_key:
            raise ValueError("TDX_APP_ID 和 TDX_APP_KEY 必須在環境變數中設定")

        # 初始化認證物件
        self.auth = Auth(self.app_id, self.app_key)
        # Access Token 相關變數
        self.access_token = None
        self.token_expiry = 0  # Token 過期時間戳記
        self.auth_url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
        # 快取路段的最高車格號
        self.max_spot_cache = {}  # 格式為 {segment_id: max_spot_number}
        # 快取路段名稱
        self.segment_name_cache = {}  # 格式為 {segment_id: segment_name}

        # 從環境變數獲取預設地址，預設為台北市中正區
        self.home_address = os.getenv("HOME_ADDRESS", "臺北市中正區")
        # 根據預設地址映射城市
        self.home_city = self._map_city(self.home_address)[0]
        # 地址到路段代碼和名稱的映射表，支援模糊查詢並減少 API 呼叫
        self.address_to_segment = {
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
                {"id": "1131198", "name": "榮華二路19巷8弄"},
                {"id": "40730A0", "name": "水源路A"},
                {"id": "4091000", "name": "青年路"},
                {"id": "4023000", "name": "中華路2段"},
                {"id": "4117000", "name": "國興路"},
                {"id": "4023416", "name": "中華路2段416巷"},
                {"id": "4023364", "name": "中華路二段364巷17弄及24弄"},
                {"id": "5300000", "name": "雙和街"},
                {"id": "4023300", "name": "中華路2段300巷13弄"}
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
        # 分組配置：每個路段包含自定義群組名稱和車格號範圍
        self.group_config = {
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

    def _get_access_token(self):
        # 取得或刷新 Access Token
        current_time = time.time()
        # 檢查 Token 是否有效（留 60 秒緩衝）
        if self.access_token and current_time < self.token_expiry - 60:
            return self.access_token

        try:
            # 發送 POST 請求取得 Token
            auth_response = requests.post(self.auth_url, data=self.auth.get_auth_header())
            auth_response.raise_for_status()
            auth_json = auth_response.json()
            self.access_token = auth_json.get('access_token')
            # 設定 Token 過期時間（預設 86400 秒，減去 60 秒緩衝）
            self.token_expiry = current_time + auth_json.get('expires_in', 86400) - 60
            return self.access_token
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("取得 Access Token 失敗: API 速率限制 (429 Too Many Requests)")
                raise Exception("API 速率限制，請稍後再試")
            logger.error("取得 Access Token 失敗: {}".format(str(e)))
            raise
        except requests.exceptions.RequestException as e:
            logger.error("取得 Access Token 失敗: {}".format(str(e)))
            raise

    def _get_data_header(self):
        # 生成 API 請求的標頭，包含 Access Token
        return {
            'authorization': 'Bearer {}'.format(self._get_access_token()),
            'Accept-Encoding': 'gzip'
        }

    def _map_city(self, address):
        # 將地址解析為 TDX API 的城市代碼和剩餘地址，若無匹配城市則預設為 Taipei
        if not isinstance(address, str):
            logger.error("地址輸入無效: 必須是字串，收到 {}".format(type(address)))
            return "Taipei", ""
        city_mapping = {
            "NewTaipei": "新北市",
            "YilanCounty": "宜蘭縣",
            "PingtungCounty": "屏東縣",
            "HsinchuCounty": "新竹縣",
            "Taoyuan": "桃園市",
            "Taipei": "臺北市",
            "Hsinchu": "新竹市",
            "YunlinCounty": "雲林縣",
            "MiaoliCounty": "苗栗縣",
            "Chiayi": "嘉義市",
            "TaitungCounty": "臺東縣",
            "Kaohsiung": "高雄市",
            "HualienCounty": "花蓮縣",
            "LienchiangCounty": "連江縣",
            "ChiayiCounty": "嘉義縣",
            "Keelung": "基隆市",
            "Taichung": "臺中市",
            "PenghuCounty": "澎湖縣",
            "ChanghuaCounty": "彰化縣",
            "KinmenCounty": "金門縣",
            "NantouCounty": "南投縣",
            "Tainan": "臺南市"
        }
        # 檢查地址是否包含城市名稱
        for city_code, city_name in city_mapping.items():
            if city_name in address:
                # 移除城市名稱，取得剩餘地址
                remaining_address = address.replace(city_name, "").strip()
                return city_code, remaining_address
        # 若無匹配，預設為 Taipei
        return "Taipei", address

    def _get_parking_segments(self, city, address):
        # 通過模糊查詢獲取路段代碼和名稱
        url = "https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSegment/City/{}".format(city)
        params = {"$format": "JSON", "$top": 100, "$select": "ParkingSegmentID,ParkingSegmentName"}
        filter_keys = [address]
        if "巷" in address:
            filter_keys.append(address.split("巷")[0])
        if len(address) > 1:
            filter_keys.append(address[:2])

        for filter_key in filter_keys:
            params["$filter"] = "contains(ParkingSegmentName/Zh_tw,'{}')".format(filter_key)
            for attempt in range(3):  # 最多重試 3 次
                try:
                    response = requests.get(url, headers=self._get_data_header(), params=params)
                    response.raise_for_status()
                    data = response.json()
                    if data.get("ParkingSegments"):
                        # 快取路段名稱
                        for segment in data.get("ParkingSegments", []):
                            seg_id = segment.get("ParkingSegmentID")
                            seg_name = segment.get("ParkingSegmentName", {}).get("Zh_tw", "未知路段")
                            self.segment_name_cache[seg_id] = seg_name
                        return data
                    return {"error": "無匹配路段", "api_response": data}
                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        logger.error("模糊查詢路段失敗 (關鍵字: {}): API 速率限制 (429 Too Many Requests)，嘗試 {}/3".format(filter_key, attempt + 1))
                        if attempt < 2:
                            time.sleep(2)  # 延遲 2 秒後重試
                            continue
                        return {"error": "API 速率限制，請稍後再試", "api_response": {}}
                    elif e.response.status_code == 500:
                        logger.error("模糊查詢路段失敗 (關鍵字: {}): 伺服器錯誤 (500 Internal Server Error)，嘗試 {}/3".format(filter_key, attempt + 1))
                        if attempt < 2:
                            time.sleep(2)
                            continue
                        try:
                            return {"error": "伺服器錯誤，請稍後再試", "api_response": e.response.json()}
                        except ValueError:
                            return {"error": "伺服器錯誤，請稍後再試", "api_response": {"error": e.response.text}}
                    logger.error("模糊查詢路段失敗 (關鍵字: {}): {}".format(filter_key, str(e)))
                    try:
                        return {"error": "查詢路段失敗，請檢查網路或稍後再試", "api_response": e.response.json()}
                    except ValueError:
                        return {"error": "查詢路段失敗，請檢查網路或稍後再試", "api_response": {"error": e.response.text}}
                except requests.exceptions.RequestException as e:
                    logger.error("模糊查詢路段失敗 (關鍵字: {}): {}".format(filter_key, str(e)))
                    if attempt < 2:
                        time.sleep(2)
                        continue
                    return {"error": "查詢路段失敗，請檢查網路或稍後再試", "api_response": {"error": str(e)}}
        return {"error": "無匹配路段", "api_response": {"error": "無關鍵字匹配"}}

    def _get_segment_name(self, city, segment_id):
        # 查詢指定路段的名稱，先檢查快取
        if segment_id in self.segment_name_cache:
            return self.segment_name_cache[segment_id]

        url = "https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSegment/City/{}".format(city)
        params = {
            "$format": "JSON",
            "$top": 1,
            "$select": "ParkingSegmentName",
            "$filter": "ParkingSegmentID eq '{}'".format(segment_id)
        }
        for attempt in range(3):  # 最多重試 3 次
            try:
                response = requests.get(url, headers=self._get_data_header(), params=params)
                response.raise_for_status()
                data = response.json()
                if data.get("ParkingSegments"):
                    segment_name = data["ParkingSegments"][0]["ParkingSegmentName"]["Zh_tw"]
                    # 儲存到快取
                    self.segment_name_cache[segment_id] = segment_name
                    return segment_name
                return {"error": "未知路段", "api_response": data}
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.error("查詢路段名稱失敗: API 速率限制 (429 Too Many Requests)，嘗試 {}/3".format(attempt + 1))
                    if attempt < 2:
                        time.sleep(2)
                        continue
                    return {"error": "未知路段 (API 速率限制)", "api_response": {}}
                elif e.response.status_code == 500:
                    logger.error("查詢路段名稱失敗: 伺服器錯誤 (500 Internal Server Error)，嘗試 {}/3".format(attempt + 1))
                    if attempt < 2:
                        time.sleep(2)
                        continue
                    try:
                        return {"error": "未知路段 (伺服器錯誤)", "api_response": e.response.json()}
                    except ValueError:
                        return {"error": "未知路段 (伺服器錯誤)", "api_response": {"error": e.response.text}}
                logger.error("查詢路段名稱失敗: {}".format(str(e)))
                try:
                    return {"error": "未知路段 (查詢失敗)", "api_response": e.response.json()}
                except ValueError:
                    return {"error": "未知路段 (查詢失敗)", "api_response": {"error": e.response.text}}
            except requests.exceptions.RequestException as e:
                logger.error("查詢路段名稱失敗: {}".format(str(e)))
                if attempt < 2:
                    time.sleep(2)
                    continue
                return {"error": "未知路段 (查詢失敗)", "api_response": {"error": str(e)}}

    def get_max_spot_number(self, city, segment_id):
        # 檢查 group_config 是否定義了車格範圍
        if segment_id in self.group_config:
            all_spots = list(chain(*[group["spots"] for group in self.group_config[segment_id]]))
            if all_spots:
                # 轉換車格號為可比較格式，僅提取數字部分進行比較
                max_spot = max(all_spots, key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
                logger.info("路段 {} 使用 group_config 定義的最高車格號: {}".format(segment_id, max_spot))
                self.max_spot_cache[segment_id] = max_spot
                return max_spot

        # 若無 group_config 定義，分批查詢最高車格號（1-50，51-100 等）
        if segment_id in self.max_spot_cache:
            logger.info("從快取取得路段 {} 的最高車格號: {}".format(segment_id, self.max_spot_cache[segment_id]))
            return self.max_spot_cache[segment_id]

        max_spot_number = ""
        batch_size = 50  # 每次查詢 50 個車格，減少 URL 長度
        start_number = 1
        api_call_count = 0  # 記錄 API 請求次數

        while True:
            end_number = start_number + batch_size - 1
            # 構建車格號範圍的過濾條件，支援 2 位或 3 位數字及字母
            filter_conditions = []
            for i in range(start_number, end_number + 1):
                spot_suffix_2 = "{:02d}".format(i)  # 2 位格式，如 01
                spot_suffix_3 = "{:03d}".format(i)  # 3 位格式，如 001
                filter_conditions.append(
                    "(substring(ParkingSpotID, length(ParkingSpotID)-3, 3) eq '{}' or substring(ParkingSpotID, length(ParkingSpotID)-2, 2) eq '{}')".format(
                        spot_suffix_3, spot_suffix_2)
                )

            # 構建 API 查詢
            url = "https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSpotAvailability/City/{}".format(city)
            params = {
                "$format": "JSON",
                "$top": batch_size,
                "$select": "ParkingSpotID,ParkingSegmentID",
                "$filter": "ParkingSegmentID eq '{}' and ({})".format(segment_id, ' or '.join(filter_conditions))
            }

            for attempt in range(3):  # 最多重試 3 次
                try:
                    api_call_count += 1
                    response = requests.get(url, headers=self._get_data_header(), params=params)
                    response.raise_for_status()
                    data = response.json()
                    spots = data.get("CurbSpotParkingAvailabilities", [])
                    logger.info("API 請求次數: {}, 路段: {}, 範圍: {}-{}, 回應車格數: {}".format(
                        api_call_count, segment_id, start_number, end_number, len(spots)))

                    if not spots:
                        # 無車格資料，終止查詢
                        logger.info("路段 {} 在 {}-{} 範圍無車格資料".format(segment_id, start_number, end_number))
                        break

                    # 解析車格號，更新最大值
                    for spot in spots:
                        spot_id = spot.get("ParkingSpotID", "")
                        match = re.search(r'(\d+[A-Z]?)$', spot_id)
                        if match:
                            spot_number = match.group(1)
                            if not max_spot_number or (spot_number and int(re.search(r'\d+', spot_number).group()) > int(re.search(r'\d+', max_spot_number).group()) if re.search(r'\d+', max_spot_number) else 0):
                                max_spot_number = spot_number

                    # 若回應包含接近批次上限的車格號，繼續查下一批
                    if max_spot_number and int(re.search(r'\d+', max_spot_number).group()) >= end_number - 5:
                        start_number += batch_size
                        break
                    else:
                        # 無更高車格號，終止查詢
                        return max_spot_number if max_spot_number else ""

                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        logger.error("查詢路段 {} 車格（{}-{}）失敗: API 速率限制 (429 Too Many Requests)，嘗試 {}/3".format(
                            segment_id, start_number, end_number, attempt + 1))
                        if attempt < 2:
                            time.sleep(2)
                            continue
                        return max_spot_number if max_spot_number else ""
                    elif e.response.status_code == 500:
                        logger.error("查詢路段 {} 車格（{}-{}）失敗: 伺服器錯誤 (500 Internal Server Error)，嘗試 {}/3".format(
                            segment_id, start_number, end_number, attempt + 1))
                        if attempt < 2:
                            time.sleep(2)
                            continue
                        return max_spot_number if max_spot_number else ""
                    logger.error("查詢路段 {} 車格（{}-{}）失敗: {}".format(segment_id, start_number, end_number, str(e)))
                    return max_spot_number if max_spot_number else ""
                except requests.exceptions.RequestException as e:
                    logger.error("查詢路段 {} 車格（{}-{}）失敗: {}".format(segment_id, start_number, end_number, str(e)))
                    if attempt < 2:
                        time.sleep(2)
                        continue
                    return max_spot_number if max_spot_number else ""
            else:
                continue  # 若 break 跳出內層迴圈，繼續外層迴圈

        if not max_spot_number:
            logger.warning("路段 {} 無車格資料".format(segment_id))
        else:
            # 儲存到快取
            self.max_spot_cache[segment_id] = max_spot_number
            logger.info("路段 {} 的最高車格號 {} 已快取".format(segment_id, max_spot_number))
        return max_spot_number

    def get_max_spot_numbers(self, city, segment_ids):
        # 分批查詢多個路段的最高車格號，若 group_config 已定義則直接使用
        if not segment_ids:
            return {}
        max_spot_numbers = {}
        remaining_segments = []

        for seg_id in segment_ids:
            if seg_id in self.group_config:
                # 使用 group_config 定義的車格號
                all_spots = list(chain(*[group["spots"] for group in self.group_config[seg_id]]))
                if all_spots:
                    max_spot = max(all_spots, key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)
                    max_spot_numbers[seg_id] = max_spot
                    self.max_spot_cache[seg_id] = max_spot
                    logger.info("路段 {} 使用 group_config 定義的最高車格號: {}".format(seg_id, max_spot))
                    continue
            # 若無 group_config 定義或快取，加入 API 查詢
            if seg_id in self.max_spot_cache:
                max_spot_numbers[seg_id] = self.max_spot_cache[seg_id]
                logger.info("從快取取得路段 {} 的最高車格號: {}".format(seg_id, self.max_spot_cache[seg_id]))
            else:
                remaining_segments.append(seg_id)

        if not remaining_segments:
            return max_spot_numbers

        batch_size = 50  # 每次查詢 50 個車格，減少 URL 長度
        start_number = 1
        api_call_count = 0  # 記錄 API 請求次數

        while remaining_segments:
            end_number = start_number + batch_size - 1
            # 構建車格號範圍的過濾條件，支援 2 位或 3 位數字及字母
            filter_conditions = []
            for i in range(start_number, end_number + 1):
                spot_suffix_2 = "{:02d}".format(i)  # 2 位格式，如 01
                spot_suffix_3 = "{:03d}".format(i)  # 3 位格式，如 001
                filter_conditions.append(
                    "(substring(ParkingSpotID, length(ParkingSpotID)-3, 3) eq '{}' or substring(ParkingSpotID, length(ParkingSpotID)-2, 2) eq '{}')".format(
                        spot_suffix_3, spot_suffix_2)
                )

            # 構建 API 查詢
            url = "https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSpotAvailability/City/{}".format(city)
            params = {
                "$format": "JSON",
                "$top": batch_size * len(remaining_segments),  # 根據路段數調整上限
                "$select": "ParkingSpotID,ParkingSegmentID",
                "$filter": "ParkingSegmentID in ({}) and ({})".format(
                    ','.join(["'{}'".format(id) for id in remaining_segments]), ' or '.join(filter_conditions))
            }

            for attempt in range(3):  # 最多重試 3 次
                try:
                    api_call_count += 1
                    response = requests.get(url, headers=self._get_data_header(), params=params)
                    response.raise_for_status()
                    data = response.json()
                    spots = data.get("CurbSpotParkingAvailabilities", [])
                    logger.info("API 請求次數: {}, 路段: {}, 範圍: {}-{}, 回應車格數: {}".format(
                        api_call_count, remaining_segments, start_number, end_number, len(spots)))

                    if not spots:
                        # 無車格資料，終止查詢
                        logger.info("路段 {} 在 {}-{} 範圍無車格資料".format(remaining_segments, start_number, end_number))
                        break

                    # 按路段解析車格號，更新最大值
                    for spot in spots:
                        segment_id = spot.get("ParkingSegmentID")
                        spot_id = spot.get("ParkingSpotID", "")
                        if not segment_id or not spot_id:
                            logger.warning("路段 {} 的車格資料不完整，缺少 ParkingSegmentID 或 ParkingSpotID".format(segment_id))
                            continue
                        match = re.search(r'(\d+[A-Z]?)$', spot_id)
                        if match:
                            spot_number = match.group(1)
                            current_max = max_spot_numbers.get(segment_id, "")
                            if not current_max or (spot_number and int(re.search(r'\d+', spot_number).group()) > int(re.search(r'\d+', current_max).group()) if re.search(r'\d+', current_max) else 0):
                                max_spot_numbers[segment_id] = spot_number

                    # 更新剩餘路段
                    remaining_segments = [seg_id for seg_id in remaining_segments
                                         if max_spot_numbers.get(seg_id, "") and int(re.search(r'\d+', max_spot_numbers[seg_id]).group()) >= end_number - 5]
                    if not remaining_segments:
                        break
                    start_number += batch_size
                    break

                except requests.exceptions.HTTPError as e:
                    if e.response.status_code == 429:
                        logger.error("查詢多路段 {} 車格（{}-{}）失敗: API 速率限制 (429 Too Many Requests)，嘗試 {}/3".format(
                            remaining_segments, start_number, end_number, attempt + 1))
                        if attempt < 2:
                            time.sleep(2)
                            continue
                        return max_spot_numbers
                    elif e.response.status_code == 500:
                        logger.error("查詢多路段 {} 車格（{}-{}）失敗: 伺服器錯誤 (500 Internal Server Error)，嘗試 {}/3".format(
                            remaining_segments, start_number, end_number, attempt + 1))
                        if attempt < 2:
                            time.sleep(2)
                            continue
                        return max_spot_numbers
                    logger.error("查詢多路段 {} 車格（{}-{}）失敗: {}".format(remaining_segments, start_number, end_number, str(e)))
                    return max_spot_numbers
                except requests.exceptions.RequestException as e:
                    logger.error("查詢多路段 {} 車格（{}-{}）失敗: {}".format(remaining_segments, start_number, end_number, str(e)))
                    if attempt < 2:
                        time.sleep(2)
                        continue
                    return max_spot_numbers

        # 儲存到快取並記錄結果
        for seg_id, max_num in max_spot_numbers.items():
            if max_num:
                self.max_spot_cache[seg_id] = max_num
                logger.info("路段 {} 的最高車格號 {} 已快取".format(seg_id, max_num))
            else:
                logger.warning("路段 {} 無車格資料".format(seg_id))
        return max_spot_numbers

    def find_grouped_parking_spots(self, address):
        # 查詢指定地址或自訂集合的空車位，按空車位數量排序，包含路段、自定義群組名稱和更新時間
        # 確保輸入為字串
        if not isinstance(address, str):
            logger.error("地址輸入無效: 必須是字串，收到 {}".format(type(address)))
            return "地址輸入無效，請提供有效的地址字串（例如：停車 明德路337巷）"
        # 先解析城市代碼和剩餘地址
        city, remaining_address = self._map_city(address)
        if not remaining_address:
            return "地址輸入無效，請提供具體的路段或集合名稱（例如：明德路337巷 或 回家）"

        segment_ids = []
        segment_groups = {}  # 儲存路段和指定群組 {segment_id: [group_name]}

        # 檢查是否為自訂集合或單一地址
        if remaining_address in self.address_to_segment:
            for item in self.address_to_segment[remaining_address]:
                if ":" in item["id"]:
                    # 自訂集合中的特定群組，例如 "1335000:後段右側"
                    seg_id, group_name = item["id"].split(":")
                    segment_ids.append(seg_id)
                    segment_groups[seg_id] = [group_name]
                else:
                    # 完整路段
                    segment_ids.append(item["id"])
                    segment_groups[item["id"]] = [g["name"] for g in self.group_config.get(item["id"], [])]
        else:
            # 模糊查詢未知地址
            segment_data = self._get_parking_segments(city, remaining_address)
            if isinstance(segment_data, dict) and "error" in segment_data:
                return "找不到 {} 的路段資料：{}。\nAPI 回應：{}".format(remaining_address, segment_data["error"], json.dumps(segment_data["api_response"], ensure_ascii=False, indent=2))
            if not segment_data or "ParkingSegments" not in segment_data:
                supported_addresses = ", ".join(self.address_to_segment.keys())
                return "找不到 {} 的路段資料，請嘗試以下地址：{}。\nAPI 回應：{}".format(remaining_address, supported_addresses, json.dumps(segment_data, ensure_ascii=False, indent=2))
            segment_ids = [s["ParkingSegmentID"] for s in segment_data["ParkingSegments"]]
            for seg_id in segment_ids:
                segment_groups[seg_id] = [g["name"] for g in self.group_config.get(seg_id, [])]
                # 若無群組定義，假設全段
                if not segment_groups[seg_id]:
                    segment_groups[seg_id] = ["全段"]

        # 查詢空車位資料
        spot_data = self._get_parking_spots(city, segment_ids)
        if isinstance(spot_data, dict) and "error" in spot_data:
            return "無法查詢 {} 的空車位資料：{}。\nAPI 回應：{}".format(remaining_address, spot_data["error"], json.dumps(spot_data["api_response"], ensure_ascii=False, indent=2))
        if isinstance(spot_data, dict) and spot_data.get("status") == "no_available_spots":
            return "目前 {} 真的沒有空車位，請稍後再試。\nAPI 回應：{}".format(remaining_address, json.dumps(spot_data["api_response"], ensure_ascii=False, indent=2))

        # 初始化路段結果，計算每個群組的空車位數量和車格資訊
        segment_spots = {}
        current_time = datetime.now(timezone.utc)
        for spot in spot_data.get("CurbSpotParkingAvailabilities", []):
            segment_id = spot.get("ParkingSegmentID")
            spot_id = spot.get("ParkingSpotID")
            collect_time = spot.get("DataCollectTime")
            # 驗證資料完整性
            if not segment_id or not spot_id or not collect_time:
                logger.warning("車格資料不完整，缺少 ParkingSegmentID、ParkingSpotID 或 DataCollectTime")
                continue
            # 解析車格號，支援數字或數字+字母
            match = re.search(r'(\d+[A-Z]?)$', spot_id)
            spot_number = match.group(1) if match else None
            if not spot_number:
                logger.warning("車格 {} 的 ParkingSpotID 格式無效".format(spot_id))
                continue

            # 計算更新時間（分鐘前）
            try:
                collect_dt = datetime.fromisoformat(collect_time.replace('Z', '+00:00'))
                time_diff = (current_time - collect_dt).total_seconds() / 60
                minutes_ago = int(round(time_diff))
            except ValueError:
                logger.warning("車格 {} 的 DataCollectTime 格式無效: {}".format(spot_id, collect_time))
                minutes_ago = 0

            # 查找對應群組名稱
            group_name = "全段"  # 預設為全段，適用於模糊查詢的路段
            for group in self.group_config.get(segment_id, []):
                if spot_number in group["spots"]:
                    group_name = group["name"]
                    break

            # 僅處理指定群組（若為自訂集合或有群組定義）
            if segment_id in segment_groups and group_name not in segment_groups[segment_id]:
                continue

            # 初始化路段資料結構
            if segment_id not in segment_spots:
                # 使用 address_to_segment 中的名稱，若不存在則查詢 API
                segment_name = None
                for addr, segments in self.address_to_segment.items():
                    for seg in segments:
                        if seg["id"] == segment_id:
                            segment_name = seg["name"]
                            break
                    if segment_name:
                        break
                if not segment_name:
                    segment_name = self._get_segment_name(city, segment_id)
                    if isinstance(segment_name, dict) and "error" in segment_name:
                        return "無法查詢 {} 的空車位資料：{}。\nAPI 回應：{}".format(remaining_address, segment_name["error"], json.dumps(segment_name.get("api_response", {}), ensure_ascii=False, indent=2))
                segment_spots[segment_id] = {
                    "name": segment_name,
                    "groups": {},
                    "total_count": 0
                }

            # 添加空車位到群組
            if spot.get("SpotStatus") == 2:
                if group_name not in segment_spots[segment_id]["groups"]:
                    segment_spots[segment_id]["groups"][group_name] = {
                        "spots": [],
                        "count": 0
                    }
                segment_spots[segment_id]["groups"][group_name]["spots"].append({
                    "number": spot_number,
                    "minutes_ago": minutes_ago
                })
                segment_spots[segment_id]["groups"][group_name]["count"] += 1
                segment_spots[segment_id]["total_count"] += 1

        # 若無空車位，返回提示
        if not segment_spots or all(info["total_count"] == 0 for info in segment_spots.values()):
            return "目前 {} 真的沒有空車位，請稍後再試。\nAPI 回應：{}".format(remaining_address, json.dumps(spot_data["api_response"], ensure_ascii=False, indent=2))

        # 按路段的總空車位數量排序
        sorted_segments = sorted(segment_spots.items(), key=lambda x: x[1]["total_count"], reverse=True)

        # 格式化回應文字
        response_text = " {} 的空車位資訊：\n".format(remaining_address)
        for segment_id, segment_info in sorted_segments:
            if segment_info["total_count"] > 0:  # 只顯示有空車位的路段
                response_text += "路段: {}\n".format(segment_info["name"])
                # 按群組的空車位數量排序
                sorted_groups = sorted(segment_info["groups"].items(), key=lambda x: x[1]["count"], reverse=True)
                for group_name, group_info in sorted_groups:
                    if group_info["count"] > 0:  # 只顯示有空車位的群組
                        # 按車格號排序，僅比較數字部分
                        sorted_spots = sorted(group_info["spots"], key=lambda x: int(re.search(r'\d+', x["number"]).group()) if re.search(r'\d+', x["number"]) else 0)
                        spot_texts = []
                        for spot in sorted_spots:
                            spot_texts.append("{}(更新於{}分鐘前)".format(spot["number"], spot["minutes_ago"]))
                        response_text += "  {}，空車位數量: {}，車格號: {}\n".format(
                            group_name, group_info["count"], ", ".join(spot_texts))

        return response_text