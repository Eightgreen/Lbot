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
        self.app_id = app_id
        self.app_key = app_key

    def get_auth_header(self):
        return {
            'content-type': 'application/x-www-form-urlencoded',
            'grant_type': 'client_credentials',
            'client_id': self.app_id,
            'client_secret': self.app_key
        }

class ParkingFinder:
    def __init__(self):
        """初始化 ParkingFinder，設定預設城市、地址映射和車格分組配置"""
        # 從環境變數獲取 TDX API 金鑰
        self.app_id = os.getenv("TDX_APP_ID")
        self.app_key = os.getenv("TDX_APP_KEY")
        if not self.app_id or not self.app_key:
            raise ValueError("TDX_APP_ID and TDX_APP_KEY must be set in environment variables")

        # 初始化認證物件
        self.auth = Auth(self.app_id, self.app_key)
        # Access Token 相關變數
        self.access_token = None
        self.token_expiry = 0  # Token 過期時間戳記
        self.auth_url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
        # 快取路段的最高車格號
        self.max_spot_cache = {}  # {segment_id: max_spot_number}

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
            "明德": ["1124337", "1124000", "112400A"]
        }
        # 分組配置：每個路段包含自定義分組名稱和逐一列舉的車格號碼
        self.group_config = {
            "1124337": [  # 明德路337巷
                {"name": "前段",
                 "spots": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]},
                {"name": "中段",
                 "spots": [26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48,
                           49, 50]},
                {"name": "後段", "spots": [51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67]}
            ],
            "1124000": [  # 明德路
                {"name": "中段",
                 "spots": [67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89,
                           90, 91, 92, 93]},
                {"name": "後段", "spots": [110, 111, 112, 113, 114, 115, 116, 117, 118, 119]}
            ],
            "112400A": [  # 明德路A
                {"name": "中段", "spots": [62, 63, 64, 65]},
                {"name": "後段", "spots": [119, 120, 121, 122, 123, 124]}
            ],
            "1335000": [  # 裕民六路
                {"name": "前段左側", "spots": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]},
                {"name": "後段右側", "spots": [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]}
            ],
            "1335114": [  # 裕民六路114巷
                {"name": "前段", "spots": [6, 7, 8, 9, 10, 11, 12, 13, 14]},
                {"name": "後段", "spots": [15, 16, 17, 18, 19, 20, 21, 22, 23]}
            ],
            "114100A": [  # 裕民二路
                {"name": "前段", "spots": [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]},
                {"name": "後段", "spots": [22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38]}
            ],
            "1141049": [  # 裕民二路49巷
                {"name": "全段", "spots": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]}
            ],
            "1131000": [  # 奎山國小周邊
                {"name": "前段", "spots": [10, 11, 12, 13, 14, 15, 16, 17, 18]},
                {"name": "後段", "spots": [19, 20, 21, 22, 23, 24, 25, 26, 27]}
            ],
            "1131198": [  # 榮華二路19巷8弄
                {"name": "全段", "spots": [1, 2]}
            ]
        }

    def _get_access_token(self):
        """取得或刷新 Access Token"""
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
            logger.error(f"取得 Access Token 失敗: {str(e)}")
            raise

    def _get_data_header(self):
        """生成 API 請求的標頭，包含 Access Token"""
        return {
            'authorization': f'Bearer {self._get_access_token()}',
            'Accept-Encoding': 'gzip'
        }

    def _map_city(self, address):
        """將中文地址映射為 TDX API 的城市代碼，若無匹配則預設為臺北市"""
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
        """通過模糊查詢獲取路段代碼和名稱"""
        url = f"https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSegment/City/{city}"
        params = {"$format": "JSON", "$top": 100, "$select": "ParkingSegmentID,ParkingSegmentName"}
        filter_keys = [address]
        if "巷" in address:
            filter_keys.append(address.split("巷")[0])
        if len(address) > 1:
            filter_keys.append(address[:2])

        for filter_key in filter_keys:
            params["$filter"] = f"contains(ParkingSegmentName/Zh_tw,'{filter_key}')"
            try:
                response = requests.get(url, headers=self._get_data_header(), params=params)
                response.raise_for_status()
                data = response.json()
                if data.get("ParkingSegments"):
                    return data
            except requests.exceptions.RequestException as e:
                logger.error(f"模糊查詢路段失敗 (關鍵字: {filter_key}): {str(e)}")
        return None

    def _get_segment_name(self, city, segment_id):
        """查詢指定路段的名稱"""
        url = f"https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSegment/City/{city}"
        params = {
            "$format": "JSON",
            "$top": 1,
            "$select": "ParkingSegmentName",
            "$filter": f"ParkingSegmentID eq '{segment_id}'"
        }
        try:
            response = requests.get(url, headers=self._get_data_header(), params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("ParkingSegments"):
                return data["ParkingSegments"][0]["ParkingSegmentName"]["Zh_tw"]
            return "未知路段"
        except requests.exceptions.RequestException as e:
            logger.error(f"查詢路段名稱失敗: {str(e)}")
            return "未知路段"

    def _get_parking_spots(self, city, segment_ids):
        """查詢指定路段的空車位編號"""
        url = f"https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSpotAvailability/City/{city}"
        params = {
            "$format": "JSON",
            "$top": 100,
            "$select": "ParkingSpotID,ParkingSegmentID,SpotStatus,DataCollectTime",
            "$filter": f"ParkingSegmentID in ({','.join([f'\'{id}\'' for id in segment_ids])}) and SpotStatus eq 2"
        }
        try:
            response = requests.get(url, headers=self._get_data_header(), params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"查詢車位失敗: {str(e)}")
            return None

    def get_max_spot_number(self, city, segment_id):
        """分批查詢指定路段的最高車格號，先查 1-100，若有更高則查 101-200，以此類推"""
        # 檢查快取
        if segment_id in self.max_spot_cache:
            logger.info(f"從快取取得路段 {segment_id} 的最高車格號: {self.max_spot_cache[segment_id]}")
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
                spot_suffix_2 = f"{i:02d}"  # 2 位格式，如 01
                spot_suffix_3 = f"{i:03d}"  # 3 位格式，如 001
                filter_conditions.append(
                    f"(substring(ParkingSpotID, length(ParkingSpotID)-2, 2) eq '{spot_suffix_2}' or "
                    f"substring(ParkingSpotID, length(ParkingSpotID)-3, 3) eq '{spot_suffix_3}')"
                )

            # 構建 API 查詢
            url = f"https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSpotAvailability/City/{city}"
            params = {
                "$format": "JSON",
                "$top": batch_size,
                "$select": "ParkingSpotID,ParkingSegmentID",
                "$filter": f"ParkingSegmentID eq '{segment_id}' and ({' or '.join(filter_conditions)})"
            }

            try:
                api_call_count += 1
                response = requests.get(url, headers=self._get_data_header(), params=params)
                response.raise_for_status()
                data = response.json()
                spots = data.get("CurbSpotParkingAvailabilities", [])
                logger.info(f"API 請求次數: {api_call_count}, 路段: {segment_id}, 範圍: {start_number}-{end_number}, 回應車格數: {len(spots)}")

                if not spots:
                    # 無車格資料，終止查詢
                    logger.info(f"路段 {segment_id} 在 {start_number}-{end_number} 範圍無車格資料")
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
                logger.error(f"查詢路段 {segment_id} 車格（{start_number}-{end_number}）失敗: {str(e)}")
                return max_spot_number if max_spot_number > 0 else 0

        if max_spot_number == 0:
            logger.warning(f"路段 {segment_id} 無車格資料")
        else:
            # 儲存到快取
            self.max_spot_cache[segment_id] = max_spot_number
            logger.info(f"路段 {segment_id} 的最高車格號 {max_spot_number} 已快取")
        return max_spot_number

    def find_grouped_parking_spots(self, address):
        """查詢指定地址的空車位並按分組顯示，包含最高車格號"""
        city = self._map_city(address)
        segment_ids = self.address_to_segment.get(address)
        segment_names = {}

        if not segment_ids:
            segment_data = self._get_parking_segments(city, address)
            if not segment_data or "ParkingSegments" not in segment_data:
                supported_addresses = ", ".join(self.address_to_segment.keys())
                return f"找不到 {address} 的路段資料，請嘗試以下地址：{supported_addresses}。"
            segment_ids = [s["ParkingSegmentID"] for s in segment_data["ParkingSegments"]]
            segment_names = {s["ParkingSegmentID"]: s["ParkingSegmentName"]["Zh_tw"] for s in
                             segment_data["ParkingSegments"]}

        spot_data = self._get_parking_spots(city, segment_ids)

        if not spot_data or "CurbSpotParkingAvailabilities" not in spot_data:
            return f"目前 {address} 無空車位資料，請稍後再試。"

        grouped_spots = {}
        for spot in spot_data.get("CurbSpotParkingAvailabilities", []):
            segment_id = spot.get("ParkingSegmentID")
            spot_id = spot.get("ParkingSpotID")
            # 解析車格號，支援 2 位或 3 位數字
            match = re.search(r'(\d{2,3})$', spot_id)
            spot_number = int(match.group(1)) if match else 0

            group_name = "未知分組"
            for group in self.group_config.get(segment_id, []):
                if spot_number in group["spots"]:
                    group_name = group["name"]
                    break

            if segment_id not in grouped_spots:
                if segment_id not in segment_names:
                    segment_names[segment_id] = self._get_segment_name(city, segment_id)
                grouped_spots[segment_id] = {"name": segment_names[segment_id], "groups": {}}

            if spot.get("SpotStatus") == 2:
                if group_name not in grouped_spots[segment_id]["groups"]:
                    grouped_spots[segment_id]["groups"][group_name] = []
                grouped_spots[segment_id]["groups"][group_name].append({
                    "spot_id": spot_id,
                    "number": spot_number,
                    "status": "空位",
                    "collect_time": spot.get("DataCollectTime")
                })

        if not grouped_spots or all(len(info["groups"]) == 0 for info in grouped_spots.values()):
            return f"目前 {address} 無空車位資料，請稍後再試。"

        response_text = f" {address} 的空車位資訊：\n"
        for segment_id, segment_info in grouped_spots.items():
            # 查詢該路段的最高車格號
            max_spot_number = self.get_max_spot_number(city, segment_id)
            if segment_info["groups"]:
                response_text += f"路段: {segment_info['name']} (代碼: {segment_id}，最高車格號: {max_spot_number})\n"
                for group_name, spots in segment_info["groups"].items():
                    response_text += f"  分組: {group_name}\n"
                    for idx, spot in enumerate(spots[:5], 1):
                        response_text += f"    {idx}. 車格: {spot['number']} (ID: {spot['spot_id']})，狀態: {spot['status']}，更新時間: {spot['collect_time']}\n"

        return response_text
```