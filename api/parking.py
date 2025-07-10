import os
import requests
import logging
import json
import time
import re

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

        # 從環境變數獲取預設地址，預設為台北市中正區
        self.home_address = os.getenv("HOME_ADDRESS", "臺北市中正區")
        # 根據地址映射城市
        self.home_city = self._map_city(self.home_address)
        # 地址到路段代碼的硬編碼映射表，支援模糊查詢並減少 API 呼叫
        self.address_to_segment = {
            "明德路337巷": ["1124337"],
            "明德路": ["1124000"],
            "明德路A": ["112400A"],
            "裕民六路": ["1335000"],
            "裕民六路114巷": ["1335114"],
            "裕民二路": ["114100A"],
            "裕民二路49巷": ["1141049"],
            "奎山國小周邊": ["1131000"],
            "榮華二路19巷8弄": ["1131198"],
            "裕民": ["1335000", "1335114", "114100A", "1141049"],
            "明德": ["1124337", "1124000", "112400A"],
            "回家": ["1124337", "112400A", "1335000:後段右側"]  # 自訂集合：明德路337巷全段 + 明德路A全段 + 裕民六路後段右側
        }
        # 分組配置：每個路段包含自定義群組名稱和車格號範圍
        self.group_config = {
            "1124337": [  # 明德路337巷
                {"name": "前段", "spots": list(range(1, 26))},
                {"name": "中段", "spots": list(range(26, 51))},
                {"name": "後段", "spots": list(range(51, 68))},
                {"name": "國小旁邊", "spots": [10, 11, 12, 13, 14, 15]}  # 自訂別稱
            ],
            "1124000": [  # 明德路
                {"name": "中段", "spots": list(range(67, 94))},
                {"name": "後段", "spots": list(range(110, 120))}
            ],
            "112400A": [  # 明德路A
                {"name": "中段", "spots": list(range(62, 66))},
                {"name": "後段", "spots": list(range(119, 125))}
            ],
            "1335000": [  # 裕民六路
                {"name": "前段左側", "spots": list(range(1, 19))},
                {"name": "後段右側", "spots": list(range(19, 37))}
            ],
            "1335114": [  # 裕民六路114巷
                {"name": "前段", "spots": list(range(6, 15))},
                {"name": "後段", "spots": list(range(15, 24))}
            ],
            "114100A": [  # 裕民二路
                {"name": "前段", "spots": list(range(5, 22))},
                {"name": "後段", "spots": list(range(22, 39))}
            ],
            "1141049": [  # 裕民二路49巷
                {"name": "全段", "spots": list(range(1, 12))}
            ],
            "1131000": [  # 奎山國小周邊
                {"name": "前段", "spots": list(range(10, 19))},
                {"name": "後段", "spots": list(range(19, 28))}
            ],
            "1131198": [  # 榮華二路19巷8弄
                {"name": "全段", "spots": [1, 2]}
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
        # 將中文地址映射為 TDX API 的城市代碼，若無匹配則預設為臺北市
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
        for city_code, city_name in city_mapping.items():
            if city_name in address:
                return city_code
        return "Taipei"

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
            try:
                response = requests.get(url, headers=self._get_data_header(), params=params)
                response.raise_for_status()
                data = response.json()
                if data.get("ParkingSegments"):
                    return data
            except requests.exceptions.RequestException as e:
                logger.error("模糊查詢路段失敗 (關鍵字: {}): {}".format(filter_key, address))
        return None

    def _get_segment_name(self, city, segment_id):
        # 查詢指定路段的名稱
        url = "https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSegment/City/{}".format(city)
        params = {
            "$format": "JSON",
            "$top": 1,
            "$select": "ParkingSegmentName",
            "$filter": "ParkingSegmentID eq '{}'".format(segment_id)
        }
        try:
            response = requests.get(url, headers=self._get_data_header(), params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("ParkingSegments"):
                return data["ParkingSegments"][0]["ParkingSegmentName"]["Zh_tw"]
            return "未知路段"
        except requests.exceptions.RequestException as e:
            logger.error("查詢路段名稱失敗: {}".format(str(e)))
            return "未知路段"

    def _get_parking_spots(self, city, segment_ids):
        # 查詢指定路段的空車位編號
        url = "https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSpotAvailability/City/{}".format(city)
        params = {
            "$format": "JSON",
            "$top": 100,
            "$select": "ParkingSpotID,ParkingSegmentID,SpotStatus,DataCollectTime",
            "$filter": "ParkingSegmentID in ({}) and SpotStatus eq 2".format(
                ','.join(["'{}'".format(id) for id in segment_ids]))
        }
        try:
            response = requests.get(url, headers=self._get_data_header(), params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("查詢車位失敗: {}".format(str(e)))
            return None

    def get_max_spot_number(self, city, segment_id):
        # 分批查詢指定路段的最高車格號，先查 1-100，若有更高則查 101-200，以此類推
        # 檢查快取
        if segment_id in self.max_spot_cache:
            logger.info("從快取取得路段 {} 的最高車格號: {}".format(segment_id, self.max_spot_cache[segment_id]))
            return self.max_spot_cache[segment_id]

        max_spot_number = 0
        batch_size = 100  # 每次查詢 100 個車格
        start_number = 1
        api_call_count = 0  # 記錄 API 請求次數

        while True:
            end_number = start_number + batch_size - 1
            # 構建車格號範圍的過濾條件，支援 2 位或 3 位數字
            filter_conditions = []
            for i in range(start_number, end_number + 1):
                spot_suffix_2 = "{:02d}".format(i)  # 2 位格式，如 01
                spot_suffix_3 = "{:03d}".format(i)  # 3 位格式，如 001
                # 使用單行格式化，避免語法錯誤
                filter_conditions.append(
                    "(substring(ParkingSpotID, length(ParkingSpotID)-2, 2) eq '{}' or substring(ParkingSpotID, length(ParkingSpotID)-3, 3) eq '{}')".format(
                        spot_suffix_2, spot_suffix_3)
                )

            # 構建 API 查詢
            url = "https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSpotAvailability/City/{}".format(city)
            params = {
                "$format": "JSON",
                "$top": batch_size,
                "$select": "ParkingSpotID,ParkingSegmentID",
                "$filter": "ParkingSegmentID eq '{}' and ({})".format(segment_id, ' or '.join(filter_conditions))
            }

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
                    match = re.search(r'(\d{2,3})$', spot_id)
                    if match:
                        try:
                            spot_number = int(match.group(1))
                            max_spot_number = max(max_spot_number, spot_number)
                        except ValueError:
                            continue

                # 若回應包含接近批次上限的車格號，繼續查下一批
                if max_spot_number >= end_number - 10:  # 接近上限（留 10 個緩衝）
                    start_number += batch_size
                    continue
                else:
                    # 無更高車格號，終止查詢
                    break

            except requests.exceptions.RequestException as e:
                logger.error("查詢路段 {} 車格（{}-{}）失敗: {}".format(segment_id, start_number, end_number, str(e)))
                return max_spot_number if max_spot_number > 0 else 0

        if max_spot_number == 0:
            logger.warning("路段 {} 無車格資料".format(segment_id))
        else:
            # 儲存到快取
            self.max_spot_cache[segment_id] = max_spot_number
            logger.info("路段 {} 的最高車格號 {} 已快取".format(segment_id, max_spot_number))
        return max_spot_number

    def find_grouped_parking_spots(self, address):
        # 查詢指定地址或自訂集合的空車位並按分組顯示，包含最高車格號
        city = self._map_city(address)
        segment_ids = []
        segment_groups = {}  # 儲存路段和指定群組 {segment_id: [group_name]}

        # 檢查是否為自訂集合或單一地址
        if address in self.address_to_segment:
            for item in self.address_to_segment[address]:
                if ":" in item:
                    # 自訂集合中的特定群組，例如 "1335000:後段右側"
                    seg_id, group_name = item.split(":")
                    segment_ids.append(seg_id)
                    segment_groups[seg_id] = [group_name]
                else:
                    # 完整路段
                    segment_ids.append(item)
                    segment_groups[item] = [g["name"] for g in self.group_config.get(item, [])]
        else:
            # 模糊查詢未知地址
            segment_data = self._get_parking_segments(city, address)
            if not segment_data or "ParkingSegments" not in segment_data:
                supported_addresses = ", ".join(self.address_to_segment.keys())
                return "找不到 {} 的路段資料，請嘗試以下地址：{}。".format(address, supported_addresses)
            segment_ids = [s["ParkingSegmentID"] for s in segment_data["ParkingSegments"]]
            segment_names = {s["ParkingSegmentID"]: s["ParkingSegmentName"]["Zh_tw"] for s in
                             segment_data["ParkingSegments"]}
            for seg_id in segment_ids:
                segment_groups[seg_id] = [g["name"] for g in self.group_config.get(seg_id, [])]

        # 查詢空車位資料
        spot_data = self._get_parking_spots(city, segment_ids)

        if not spot_data or "CurbSpotParkingAvailabilities" not in spot_data:
            return "目前 {} 無空車位資料，請稍後再試。".format(address)

        # 初始化分組結果
        grouped_spots = {}
        for spot in spot_data.get("CurbSpotParkingAvailabilities", []):
            segment_id = spot.get("ParkingSegmentID")
            spot_id = spot.get("ParkingSpotID")
            # 解析車格號，支援 2 位或 3 位數字
            match = re.search(r'(\d{2,3})$', spot_id)
            spot_number = int(match.group(1)) if match else 0

            # 查找對應群組名稱
            group_name = "未知分組"
            for group in self.group_config.get(segment_id, []):
                if spot_number in group["spots"]:
                    group_name = group["name"]
                    break

            # 僅處理指定群組（若為自訂集合）
            if segment_id in segment_groups and group_name not in segment_groups[segment_id]:
                continue

            # 初始化路段資料結構
            if segment_id not in grouped_spots:
                segment_name = self._get_segment_name(city, segment_id)
                grouped_spots[segment_id] = {"name": segment_name, "groups": {}}

            # 僅添加空車位到分組
            if spot.get("SpotStatus") == 2:
                if group_name not in grouped_spots[segment_id]["groups"]:
                    grouped_spots[segment_id]["groups"][group_name] = []
                grouped_spots[segment_id]["groups"][group_name].append({
                    "spot_id": spot_id,
                    "number": spot_number,
                    "status": "空位",
                    "collect_time": spot.get("DataCollectTime")
                })

        # 若無空車位，返回提示
        if not grouped_spots or all(len(info["groups"]) == 0 for info in grouped_spots.values()):
            return "目前 {} 無空車位資料，請稍後再試。".format(address)

        # 格式化回應文字
        response_text = " {} 的空車位資訊：\n".format(address)
        for segment_id, segment_info in grouped_spots.items():
            # 查詢該路段的最高車格號
            max_spot_number = self.get_max_spot_number(city, segment_id)
            if segment_info["groups"]:
                response_text += "路段: {} (代碼: {}，最高車格號: {})\n".format(
                    segment_info["name"], segment_id, max_spot_number)
                for group_name, spots in segment_info["groups"].items():
                    response_text += "  分組: {}\n".format(group_name)
                    for idx, spot in enumerate(spots[:5], 1):  # 每組最多顯示 5 個車位
                        response_text += "    {}. 車格: {} (ID: {}), 狀態: {}, 更新時間: {}\n".format(
                            idx, spot["number"], spot["spot_id"], spot["status"], spot["collect_time"])

        return response_text