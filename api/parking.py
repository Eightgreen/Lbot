import os
import requests
import logging

# 設置日誌記錄，方便除錯
logger = logging.getLogger(__name__)


class ParkingFinder:
    def __init__(self):
        """初始化 ParkingFinder，設定預設城市、地址映射和車格分組配置"""
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

    def _map_city(self, address):
        """將中文地址映射為 TDX API 的城市代碼，若無匹配則預設為臺北市"""
        # 城市映射表，鍵為 TDX API 城市代碼，值為中文城市名稱
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
        # 檢查地址是否包含任一城市名稱
        for city_code, city_name in city_mapping.items():
            if city_name in address:
                return city_code
        # 若無匹配，預設為 Taipei
        return "Taipei"

    def _get_parking_segments(self, city, address):
        """通過模糊查詢獲取路段代碼和名稱"""
        # 構建 TDX API URL，用於查詢路段資料
        url = "https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSegment/City/{}".format(city)
        # 設定查詢參數：JSON 格式，最多 100 筆，僅選代碼和名稱
        params = {"$format": "JSON", "$top": 100, "$select": "ParkingSegmentID,ParkingSegmentName"}
        # 嘗試多種模糊查詢關鍵字
        filter_keys = [address]
        if "巷" in address:
            filter_keys.append(address.split("巷")[0])
        if len(address) > 1:
            filter_keys.append(address[:2])
        for filter_key in filter_keys:
            params["$filter"] = "contains(ParkingSegmentName/Zh_tw,'{}')".format(filter_key)
            try:
                # 發送 GET 請求並解析 JSON 回應
                response = requests.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                if data.get("ParkingSegments"):
                    return data
            except Exception:
                logger.error("模糊查詢路段失敗 (關鍵字: {}): {}".format(filter_key, address))
        # 若所有查詢失敗，返回 None
        return None

    def _get_segment_name(self, city, segment_id):
        """查詢指定路段的名稱"""
        # 構建 TDX API URL，用於查詢路段資料
        url = "https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSegment/City/{}".format(city)
        # 設定查詢參數：JSON 格式，僅選名稱，過濾特定路段
        params = {
            "$format": "JSON",
            "$top": 1,
            "$select": "ParkingSegmentName",
            "$filter": "ParkingSegmentID eq '{}'".format(segment_id)
        }
        try:
            # 發送 GET 請求並解析 JSON 回應
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("ParkingSegments"):
                return data["ParkingSegments"][0]["ParkingSegmentName"]["Zh_tw"]
            return "未知路段"
        except Exception as e:
            # 記錄錯誤並返回預設名稱
            logger.error("查詢路段名稱失敗: {}".format(str(e)))
            return "未知路段"

    def _get_parking_spots(self, city, segment_ids):
        """查詢指定路段的空車位編號"""
        # 構建 TDX API URL，用於查詢車位動態資料
        url = "https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSpotAvailability/City/{}".format(city)
        # 設定查詢參數：JSON 格式，最多 100 筆，僅選必要欄位，過濾空車位
        params = {
            "$format": "JSON",
            "$top": 100,
            "$select": "ParkingSpotID,ParkingSegmentID,SpotStatus,DataCollectTime",
            "$filter": "ParkingSegmentID in ({}) and SpotStatus eq 2".format(
                ','.join(["'" + id + "'" for id in segment_ids]))
        }
        try:
            # 發送 GET 請求並解析 JSON 回應
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # 記錄錯誤並返回 None
            logger.error("查詢車位失敗: {}".format(str(e)))
            return None

    def find_grouped_parking_spots(self, address):
        """查詢指定地址的空車位並按分組顯示"""
        # 映射地址到城市代碼
        city = self._map_city(address)
        # 嘗試從硬編碼映射表獲取路段代碼
        segment_ids = self.address_to_segment.get(address)
        segment_names = {}

        # 若映射表無匹配，執行模糊查詢
        if not segment_ids:
            segment_data = self._get_parking_segments(city, address)
            if not segment_data or "ParkingSegments" not in segment_data:
                supported_addresses = ", ".join(self.address_to_segment.keys())
                return "找不到 {} 的路段資料，請嘗試以下地址：{}。".format(address, supported_addresses)
            segment_ids = [s["ParkingSegmentID"] for s in segment_data["ParkingSegments"]]
            segment_names = {s["ParkingSegmentID"]: s["ParkingSegmentName"]["Zh_tw"] for s in
                             segment_data["ParkingSegments"]}

        # 查詢空車位資料
        spot_data = self._get_parking_spots(city, segment_ids)

        # 檢查車位資料是否有效
        if not spot_data or "CurbSpotParkingAvailabilities" not in spot_data:
            return "目前 {} 無空車位資料，請稍後再試。".format(address)

        # 初始化分組結果
        grouped_spots = {}
        for spot in spot_data.get("CurbSpotParkingAvailabilities", []):
            segment_id = spot.get("ParkingSegmentID")
            spot_id = spot.get("ParkingSpotID")
            # 假設 ParkingSpotID 後三位為車格號碼
            try:
                spot_number = int(spot_id[-3:]) if spot_id[-3:].isdigit() else 0
            except ValueError:
                spot_number = 0

            # 查找對應分組名稱
            group_name = "未知分組"
            for group in self.group_config.get(segment_id, []):
                if spot_number in group["spots"]:
                    group_name = group["name"]
                    break

            # 初始化路段資料結構
            if segment_id not in grouped_spots:
                if segment_id not in segment_names:
                    segment_names[segment_id] = self._get_segment_name(city, segment_id)
                grouped_spots[segment_id] = {"name": segment_names[segment_id], "groups": {}}

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
            if segment_info["groups"]:  # 僅顯示有空車位的路段
                response_text += "路段: {} (代碼: {})\n".format(segment_info["name"], segment_id)
                for group_name, spots in segment_info["groups"].items():
                    response_text += "  分組: {}\n".format(group_name)
                    for idx, spot in enumerate(spots[:5], 1):  # 每組最多顯示 5 個車位
                        response_text += "    {}. 車格: {} (ID: {})，狀態: {}，更新時間: {}\n".format(
                            idx, spot["number"], spot["spot_id"], spot["status"], spot["collect_time"])

        return response_text