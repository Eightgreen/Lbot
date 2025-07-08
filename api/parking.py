import os
import requests
import logging

logger = logging.getLogger(__name__)


class ParkingFinder:
    def __init__(self):
        """初始化 ParkingFinder，設定預設城市和車格分組配置"""
        # 預設家鄉地址，影響城市映射
        self.home_address = os.getenv("HOME_ADDRESS", "回家")
        self.home_city = self._map_city(self.home_address)
        # 分組配置：每個路段的分組包含自定義名稱和逐一列舉的車格號碼
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
                {"name": "前段左側", "spots": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19]},
                {"name": "後段右側",
                 "spots": [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39]}
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
        """將中文地址映射為 TDX API 的城市代碼"""
        # 定義城市映射表，僅包含必要城市以精簡程式碼
        city_mapping = {"台北": "Taipei", "新北": "NewTaipei", "桃園": "Taoyuan", "台中": "Taichung"}
        # 返回匹配的城市代碼，預設為 Taipei
        return next((value for key, value in city_mapping.items() if key in address), "Taipei")

    def _get_parking_segments(self, city, address):
        """查詢指定城市的路段代碼和名稱，支援模糊查詢"""
        # 構建 TDX API URL，查詢路段資料
        url = f"https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSegment/City/{city}"
        # 設定查詢參數：JSON 格式，最多 100 筆，僅選代碼和名稱
        params = {"$format": "JSON", "$top": 100, "$select": "ParkingSegmentID,ParkingSegmentName"}
        # 若提供地址，添加過濾條件，支援模糊查詢（去除「巷」後的內容）
        if address:
            filter_key = address.split("巷")[0] if "巷" in address else address
            params["$filter"] = f"contains(ParkingSegmentName/Zh_tw,'{filter_key}')"
        try:
            # 發送 GET 請求並解析 JSON 回應
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # 記錄錯誤並返回 None
            logger.error(f"Failed to fetch parking segments: {str(e)}")
            return None

    def _get_parking_spots(self, city, segment_ids):
        """查詢指定路段的空車位編號"""
        # 構建 TDX API URL，查詢車位動態資料
        url = f"https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSpotAvailability/City/{city}"
        # 設定查詢參數：JSON 格式，最多 100 筆，僅選必要欄位，過濾空車位
        params = {
            "$format": "JSON",
            "$top": 100,
            "$select": "ParkingSpotID,ParkingSegmentID,SpotStatus,DataCollectTime",
            "$filter": f"ParkingSegmentID in ({','.join(f"'{id}'" for id in segment_ids)}) and SpotStatus eq 2"
        }
        try:
            # 發送 GET 請求並解析 JSON 回應
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            # 記錄錯誤並返回 None
            logger.error(f"Failed to fetch parking spots: {str(e)}")
            return None

    def find_grouped_parking_spots(self, address):
        """查詢指定地址的空車位並按分組顯示"""
        # 映射地址到城市代碼
        city = self._map_city(address)
        # 查詢路段代碼
        segment_data = self._get_parking_segments(city, address)

        # 檢查是否成功獲取路段資料，若失敗嘗試模糊查詢
        if not segment_data or "ParkingSegments" not in segment_data:
            return f"找不到 {address} 的路段資料，請嘗試更廣泛的地址（如 '{address.split('巷')[0]}'）。"

        # 提取路段代碼列表
        segment_ids = [s["ParkingSegmentID"] for s in segment_data["ParkingSegments"]]
        # 查詢空車位資料
        spot_data = self._get_parking_spots(city, segment_ids)

        # 檢查是否成功獲取車位資料
        if not spot_data or "CurbSpotParkingAvailabilities" not in spot_data:
            return f"目前 {address} 無空車位資料，請稍後再試。"

        # 初始化分組結果
        grouped_spots = {}
        for spot in spot_data.get("CurbSpotParkingAvailabilities", []):
            segment_id = spot.get("ParkingSegmentID")
            spot_id = spot.get("ParkingSpotID")
            # 提取車格號碼，假設 ParkingSpotID 後三位為車格號碼
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
                segment_name = next((s["ParkingSegmentName"]["Zh_tw"] for s in segment_data["ParkingSegments"] if
                                     s["ParkingSegmentID"] == segment_id), "未知路段")
                grouped_spots[segment_id] = {"name": segment_name, "groups": {}}

            # 添加車位到對應分組
            if group_name not in grouped_spots[segment_id]["groups"]:
                grouped_spots[segment_id]["groups"][group_name] = []
            grouped_spots[segment_id]["groups"][group_name].append({
                "spot_id": spot_id,
                "number": spot_number,
                "status": "空位",
                "collect_time": spot.get("DataCollectTime")
            })

        # 若無空車位，返回提示
        if not grouped_spots:
            return f"目前 {address} 無空車位資料，請稍後再試。"

        # 格式化回應文字
        response_text = f"{address} 的分組車位資訊：\n"
        for segment_id, segment_info in grouped_spots.items():
            response_text += f"路段: {segment_info['name']} (代碼: {segment_id})\n"
            for group_name, spots in segment_info["groups"].items():
                response_text += f"  分組: {group_name}\n"
                for idx, spot in enumerate(spots[:5], 1):  # 每組最多顯示 5 個車位
                    response_text += f"    {idx}. 車格: {spot['number']} (ID: {spot['spot_id']})，狀態: {spot['status']}，更新時間: {spot['collect_time']}\n"

        return response_text