import os
import requests
import logging
import json
import time
import re
from datetime import datetime, timezone
from api.config import address_to_segment, group_config

# 設置日誌記錄，方便除錯
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 車格狀態映射
SPOT_STATUS_MAP = {
    0: "占用",
    1: "禁用",
    2: "空位",
}

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
        self.app_id = os.getenv("TDX_APP_ID")
        self.app_key = os.getenv("TDX_APP_KEY")
        if not self.app_id or not self.app_key:
            raise ValueError("TDX_APP_ID 和 TDX_APP_KEY 必須在環境變數中設定")

        self.auth = Auth(self.app_id, self.app_key)
        self.access_token = None
        self.token_expiry = 0
        self.auth_url = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
        self.segment_name_cache = {}
        self.home_address = os.getenv("HOME_ADDRESS", "臺北市中正區")
        self.home_city = self._map_city(self.home_address)[0]
        self.api_call_count = 0
        self.last_call_time = time.time()

    def _get_access_token(self):
        current_time = time.time()
        if self.access_token and current_time < self.token_expiry - 60:
            return self.access_token

        if current_time - self.last_call_time < 60 and self.api_call_count >= 20:
            logger.warning("接近 Access Token 每分鐘 20 次限制，等待 5 秒")
            time.sleep(5)

        try:
            logger.info("開始取得 Access Token")
            start_time = time.time()
            auth_response = requests.post(self.auth_url, data=self.auth.get_auth_header(), timeout=5)
            auth_response.raise_for_status()
            auth_json = auth_response.json()
            self.access_token = auth_json.get('access_token')
            self.token_expiry = current_time + auth_json.get('expires_in', 86400) - 60
            self.api_call_count += 1
            self.last_call_time = current_time
            logger.info(f"取得 Access Token 成功，耗時 {time.time() - start_time:.2f} 秒")
            return self.access_token
        except requests.exceptions.Timeout:
            logger.error("取得 Access Token 失敗: 請求超時 (504 Gateway Timeout)")
            raise Exception("取得 Access Token 失敗：請求超時，請稍後再試")
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
        return {
            'authorization': 'Bearer {}'.format(self._get_access_token()),
            'Accept-Encoding': 'gzip'
        }

    def _map_city(self, address):
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
        for city_code, city_name in city_mapping.items():
            if city_name in address:
                remaining_address = address.replace(city_name, "").strip()
                return city_code, remaining_address
        return "Taipei", address

    def _get_parking_segments(self, city, address):
        url = "https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSegment/City/{}".format(city)
        params = {"$format": "JSON", "$top": 100, "$select": "ParkingSegmentID,ParkingSegmentName"}
        params["$filter"] = "contains(ParkingSegmentName/Zh_tw,'{}')".format(address)
        try:
            logger.info(f"開始路段查詢，地址: {address}")
            start_time = time.time()
            response = requests.get(url, headers=self._get_data_header(), params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            self.api_call_count += 1
            logger.info(f"路段查詢成功，耗時 {time.time() - start_time:.2f} 秒")
            if data.get("ParkingSegments"):
                for segment in data.get("ParkingSegments", []):
                    seg_id = segment.get("ParkingSegmentID")
                    seg_name = segment.get("ParkingSegmentName", {}).get("Zh_tw", "未知路段")
                    self.segment_name_cache[seg_id] = seg_name
                return data
            return {"error": "路段查詢錯誤：無匹配路段", "api_response": data}
        except requests.exceptions.Timeout:
            logger.error("路段查詢錯誤 (地址: {}): 請求超時 (504 Gateway Timeout)".format(address))
            return {"error": "路段查詢錯誤：請求超時，請稍後再試", "api_response": {}}
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("路段查詢錯誤 (地址: {}): API 速率限制 (429 Too Many Requests)".format(address))
                return {"error": "路段查詢錯誤：API 速率限制，請稍後再試", "api_response": {}}
            elif e.response.status_code == 500:
                logger.error("路段查詢錯誤 (地址: {}): 伺服器錯誤 (500 Internal Server Error)".format(address))
                try:
                    return {"error": "路段查詢錯誤：伺服器錯誤，請稍後再試", "api_response": e.response.json()}
                except ValueError:
                    return {"error": "路段查詢錯誤：伺服器錯誤，請稍後再試", "api_response": {"error": e.response.text}}
            logger.error("路段查詢錯誤 (地址: {}): {}".format(address, str(e)))
            try:
                return {"error": "路段查詢錯誤：查詢失敗，請檢查網路或稍後再試", "api_response": e.response.json()}
            except ValueError:
                return {"error": "路段查詢錯誤：查詢失敗，請檢查網路或稍後再試", "api_response": {"error": e.response.text}}
        except requests.exceptions.RequestException as e:
            logger.error("路段查詢錯誤 (地址: {}): {}".format(address, str(e)))
            return {"error": "路段查詢錯誤：查詢失敗，請檢查網路或稍後再試", "api_response": {"error": str(e)}}

    def _get_segment_names(self, city, segment_ids):
        if not segment_ids:
            return {}
        result = {}
        uncached_ids = [seg_id for seg_id in segment_ids if seg_id not in self.segment_name_cache]
        if not uncached_ids:
            return {seg_id: self.segment_name_cache[seg_id] for seg_id in segment_ids}

        # 分批處理，最多 20 個路段 ID
        MAX_SEGMENT_IDS = 20
        for i in range(0, len(uncached_ids), MAX_SEGMENT_IDS):
            batch_ids = uncached_ids[i:i + MAX_SEGMENT_IDS]
            url = "https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSegment/City/{}".format(city)
            params = {
                "$format": "JSON",
                "$top": 100,
                "$select": "ParkingSegmentID,ParkingSegmentName",
                "$filter": "ParkingSegmentID in ({})".format(','.join(["'{}'".format(id) for id in batch_ids]))
            }
            try:
                logger.info(f"開始路段名稱查詢，路段 ID: {batch_ids}")
                start_time = time.time()
                response = requests.get(url, headers=self._get_data_header(), params=params, timeout=5)
                response.raise_for_status()
                data = response.json()
                self.api_call_count += 1
                logger.info(f"路段名稱查詢成功，耗時 {time.time() - start_time:.2f} 秒")
                for segment in data.get("ParkingSegments", []):
                    seg_id = segment.get("ParkingSegmentID")
                    seg_name = segment.get("ParkingSegmentName", {}).get("Zh_tw", "未知路段")
                    self.segment_name_cache[seg_id] = seg_name
                    result[seg_id] = seg_name
                for seg_id in batch_ids:
                    if seg_id not in result:
                        result[seg_id] = {"error": "路段名稱查詢錯誤：未知路段", "api_response": data}
            except requests.exceptions.Timeout:
                logger.error("路段名稱查詢錯誤: 請求超時 (504 Gateway Timeout)")
                for seg_id in batch_ids:
                    result[seg_id] = {"error": "路段名稱查詢錯誤：請求超時", "api_response": {}}
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.error("路段名稱查詢錯誤: API 速率限制 (429 Too Many Requests)")
                    for seg_id in batch_ids:
                        result[seg_id] = {"error": "路段名稱查詢錯誤：API 速率限制", "api_response": {}}
                elif e.response.status_code == 500:
                    logger.error("路段名稱查詢錯誤: 伺服器錯誤 (500 Internal Server Error)")
                    try:
                        for seg_id in batch_ids:
                            result[seg_id] = {"error": "路段名稱查詢錯誤：伺服器錯誤", "api_response": e.response.json()}
                    except ValueError:
                        for seg_id in batch_ids:
                            result[seg_id] = {"error": "路段名稱查詢錯誤：伺服器錯誤", "api_response": {"error": e.response.text}}
                else:
                    logger.error("路段名稱查詢錯誤: {}".format(str(e)))
                    try:
                        for seg_id in batch_ids:
                            result[seg_id] = {"error": "路段名稱查詢錯誤：查詢失敗", "api_response": e.response.json()}
                    except ValueError:
                        for seg_id in batch_ids:
                            result[seg_id] = {"error": "路段名稱查詢錯誤：查詢失敗", "api_response": {"error": e.response.text}}
            except requests.exceptions.RequestException as e:
                logger.error("路段名稱查詢錯誤: {}".format(str(e)))
                for seg_id in batch_ids:
                    result[seg_id] = {"error": "路段名稱查詢錯誤：查詢失敗", "api_response": {"error": str(e)}}

        for seg_id in segment_ids:
            if seg_id not in result and seg_id in self.segment_name_cache:
                result[seg_id] = self.segment_name_cache[seg_id]
        return result

    def _get_parking_spots(self, city, segment_ids):
        if not segment_ids:
            return {"error": "動態車格查詢錯誤：無有效的路段 ID", "api_response": {}}

        # 分批處理，最多 20 個路段 ID
        MAX_SEGMENT_IDS = 20
        all_spots = []
        api_responses = {seg_id: {"CurbSpotParkingAvailabilities": []} for seg_id in segment_ids}
        for i in range(0, len(segment_ids), MAX_SEGMENT_IDS):
            batch_ids = segment_ids[i:i + MAX_SEGMENT_IDS]
            url = "https://tdx.transportdata.tw/api/basic/v1/Parking/OnStreet/ParkingSpotAvailability/City/{}".format(city)
            params = {
                "$format": "JSON",
                "$top": 100,
                "$select": "ParkingSpotID,ParkingSegmentID,SpotStatus,DataCollectTime",
                "$filter": "ParkingSegmentID in ({})".format(','.join(["'{}'".format(id) for id in batch_ids]))
            }
            try:
                logger.info(f"開始動態車格查詢，路段 ID: {batch_ids}")
                start_time = time.time()
                response = requests.get(url, headers=self._get_data_header(), params=params, timeout=5)
                response.raise_for_status()
                data = response.json()
                self.api_call_count += 1
                logger.info(f"動態車格查詢成功，耗時 {time.time() - start_time:.2f} 秒")
                for spot in data.get("CurbSpotParkingAvailabilities", []):
                    seg_id = spot.get("ParkingSegmentID")
                    if seg_id in api_responses:
                        api_responses[seg_id]["CurbSpotParkingAvailabilities"].append(spot)
                    all_spots.append(spot)
                if not data.get("CurbSpotParkingAvailabilities"):
                    continue
                if not all("ParkingSpotID" in spot and "ParkingSegmentID" in spot and "DataCollectTime" in spot for spot in data["CurbSpotParkingAvailabilities"]):
                    return {"error": "動態車格查詢錯誤：API 回應資料不完整，缺少必要欄位", "api_response": data, "api_responses": api_responses}
            except requests.exceptions.Timeout:
                logger.error("動態車格查詢錯誤: 請求超時 (504 Gateway Timeout)")
                return {"error": "動態車格查詢錯誤：請求超時，請稍後再試", "api_response": {}, "api_responses": {seg_id: {"error": "請求超時"} for seg_id in batch_ids}}
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    logger.error("動態車格查詢錯誤: API 速率限制 (429 Too Many Requests)")
                    return {"error": "動態車格查詢錯誤：API 速率限制，請稍後再試", "api_response": {}, "api_responses": {seg_id: {"error": "API 速率限制"} for seg_id in batch_ids}}
                elif e.response.status_code == 500:
                    logger.error("動態車格查詢錯誤: 伺服器錯誤 (500 Internal Server Error)")
                    try:
                        return {"error": "動態車格查詢錯誤：伺服器錯誤，請稍後再試", "api_response": e.response.json(), "api_responses": {seg_id: {"error": "伺服器錯誤"} for seg_id in batch_ids}}
                    except ValueError:
                        return {"error": "動態車格查詢錯誤：伺服器錯誤，請稍後再試", "api_response": {"error": e.response.text}, "api_responses": {seg_id: {"error": "伺服器錯誤"} for seg_id in batch_ids}}
                elif e.response.status_code == 401:
                    logger.error("動態車格查詢錯誤: 未授權 (401 Unauthorized)")
                    return {"error": "動態車格查詢錯誤：API 認證失敗，請檢查 TDX 金鑰", "api_response": {}, "api_responses": {seg_id: {"error": "API 認證失敗"} for seg_id in batch_ids}}
                logger.error("動態車格查詢錯誤: {}".format(str(e)))
                try:
                    return {"error": "動態車格查詢錯誤：查詢失敗，請檢查網路或稍後再試", "api_response": e.response.json(), "api_responses": {seg_id: {"error": "查詢失敗"} for seg_id in batch_ids}}
                except ValueError:
                    return {"error": "動態車格查詢錯誤：查詢失敗，請檢查網路或稍後再試", "api_response": {"error": e.response.text}, "api_responses": {seg_id: {"error": "查詢失敗"} for seg_id in batch_ids}}
            except requests.exceptions.RequestException as e:
                logger.error("動態車格查詢錯誤: {}".format(str(e)))
                return {"error": "動態車格查詢錯誤：查詢失敗，請檢查網路或稍後再試", "api_response": {"error": str(e)}, "api_responses": {seg_id: {"error": "查詢失敗"} for seg_id in batch_ids}}

        return {"CurbSpotParkingAvailabilities": all_spots, "api_response": {"batched": True}, "api_responses": api_responses}

    def find_grouped_parking_spots(self, address):
        # 重置 API 呼叫計數
        self.api_call_count = 0
        error_msgs = []
        api_responses = []
        response_text = ""

        if not isinstance(address, str):
            logger.error("地址輸入無效: 必須是字串，收到 {}".format(type(address)))
            error_msgs.append("地址輸入無效，請提供有效的地址字串（例如：停車 明德路337巷）")
            response_text += f"此次查詢共呼叫 {self.api_call_count} 次 API\n"
            return response_text, error_msgs, api_responses

        city, remaining_address = self._map_city(address)
        if not remaining_address:
            error_msgs.append("地址輸入無效，請提供具體的路段或集合名稱（例如：明德路337巷 或 回家）")
            response_text += f"此次查詢共呼叫 {self.api_call_count} 次 API\n"
            return response_text, error_msgs, api_responses

        segment_ids = []
        segment_groups = {}

        if remaining_address in address_to_segment:
            for item in address_to_segment[remaining_address]:
                if ":" in item["id"]:
                    seg_id, group_name = item["id"].split(":")
                    segment_ids.append(seg_id)
                    segment_groups[seg_id] = [group_name]
                else:
                    segment_ids.append(item["id"])
                    segment_groups[item["id"]] = [g["name"] for g in group_config.get(item["id"], [])]
            # 優先使用 address_to_segment 的名稱
            segment_names = {}
            for item in address_to_segment[remaining_address]:
                seg_id = item["id"].split(":")[0] if ":" in item["id"] else item["id"]
                segment_names[seg_id] = item["name"]
        else:
            segment_data = self._get_parking_segments(city, remaining_address)
            if isinstance(segment_data, dict) and "error" in segment_data:
                error_msgs.append("找不到 {} 的路段資料：{}。\n請嘗試以下地址：{}".format(
                    remaining_address, segment_data["error"], ", ".join(address_to_segment.keys())))
                api_responses.append(segment_data["api_response"])
                response_text += f"此次查詢共呼叫 {self.api_call_count} 次 API\n"
                return response_text, error_msgs, api_responses
            if not isinstance(segment_data, dict) or "ParkingSegments" not in segment_data:
                error_msgs.append("找不到 {} 的路段資料，請嘗試以下地址：{}。".format(
                    remaining_address, ", ".join(address_to_segment.keys())))
                api_responses.append(segment_data)
                response_text += f"此次查詢共呼叫 {self.api_call_count} 次 API\n"
                return response_text, error_msgs, api_responses
            segment_ids = [s["ParkingSegmentID"] for s in segment_data["ParkingSegments"] if "ParkingSegmentID" in s]
            for seg_id in segment_ids:
                segment_groups[seg_id] = [g["name"] for g in group_config.get(seg_id, [])]
                if not segment_groups[seg_id]:
                    segment_groups[seg_id] = ["全段"]
            segment_names = self._get_segment_names(city, segment_ids)
            for seg_id, name_info in segment_names.items():
                if isinstance(name_info, dict) and "error" in name_info:
                    error_msgs.append(f"無法查詢路段 {seg_id} 的名稱：{name_info['error']}。")
                    api_responses.append(name_info["api_response"])

        spot_data = self._get_parking_spots(city, segment_ids)
        if isinstance(spot_data, dict) and "error" in spot_data:
            error_msgs.append("無法查詢 {} 的車位資料：{}。".format(
                remaining_address, spot_data["error"]))
            api_responses.append(spot_data["api_response"])
            response_text += f"此次查詢共呼叫 {self.api_call_count} 次 API\n"
            return response_text, error_msgs, api_responses

        segment_spots = {}
        current_time = datetime.now(timezone.utc)
        for spot in spot_data.get("CurbSpotParkingAvailabilities", []):
            segment_id = spot.get("ParkingSegmentID")
            spot_id = spot.get("ParkingSpotID")
            collect_time = spot.get("DataCollectTime")
            if not segment_id or not spot_id or not collect_time:
                logger.warning("車格資料不完整，缺少 ParkingSegmentID、ParkingSpotID 或 DataCollectTime")
                continue
            match = re.search(r'(\d+[A-Z]?)$', spot_id)
            spot_number = match.group(1) if match else None
            if not spot_number:
                logger.warning("車格 {} 的 ParkingSpotID 格式無效".format(spot_id))
                continue

            try:
                collect_dt = datetime.fromisoformat(collect_time.replace('Z', '+00:00'))
                time_diff = (current_time - collect_dt).total_seconds() / 60
                minutes_ago = int(round(time_diff))
            except ValueError:
                logger.warning("車格 {} 的 DataCollectTime 格式無效: {}".format(spot_id, collect_time))
                minutes_ago = 0

            spot_status = spot.get("SpotStatus")
            if not isinstance(spot_status, int):
                try:
                    spot_status = int(spot_status)
                except (TypeError, ValueError):
                    logger.warning("車格 {} 的 SpotStatus 格式無效: {}".format(spot_id, spot_status))
                    continue

            # 僅處理空車格和其他異常狀態（排除占用和禁用）
            if spot_status == 0 or spot_status == 1:
                continue

            group_name = "全段"
            for group in group_config.get(segment_id, []):
                if spot_number in group["spots"]:
                    group_name = group["name"]
                    break

            if segment_id in segment_groups and group_name not in segment_groups[segment_id]:
                continue

            if segment_id not in segment_spots:
                segment_name = segment_names.get(segment_id, "未知路段")
                if isinstance(segment_name, dict):
                    segment_name = "未知路段"
                segment_spots[segment_id] = {
                    "name": segment_name,
                    "groups": {},
                    "total_count": 0
                }

            status_name = SPOT_STATUS_MAP.get(spot_status, f"未知（狀態碼 {spot_status}）")
            if group_name not in segment_spots[segment_id]["groups"]:
                segment_spots[segment_id]["groups"][group_name] = {
                    "spots": [],
                    "count": 0
                }
            segment_spots[segment_id]["groups"][group_name]["spots"].append({
                "number": spot_number,
                "status": status_name,
                "minutes_ago": minutes_ago
            })
            if spot_status == 2:
                segment_spots[segment_id]["groups"][group_name]["count"] += 1
                segment_spots[segment_id]["total_count"] += 1

        # 僅在 API 錯誤時包含 api_responses
        if error_msgs:
            for seg_id in segment_ids:
                if seg_id in spot_data.get("api_responses", {}):
                    api_responses.append({seg_id: spot_data["api_responses"][seg_id]})
        else:
            api_responses = []  # 正常情況下不返回 API 回應

        if not segment_spots or all(info["total_count"] == 0 for info in segment_spots.values()):
            error_msgs.append("目前 {} 真的沒有空車位，請稍後再試。".format(remaining_address))
            response_text += f"此次查詢共呼叫 {self.api_call_count} 次 API\n"
            return response_text, error_msgs, api_responses

        response_text = " {} 的車位狀態資訊：\n".format(remaining_address)
        sorted_segments = sorted(segment_spots.items(), key=lambda x: x[1]["total_count"], reverse=True)
        for segment_id, segment_info in sorted_segments:
            response_text += "路段: {}\n".format(segment_info["name"])
            sorted_groups = sorted(segment_info["groups"].items(), key=lambda x: x[1]["count"], reverse=True)
            for group_name, group_info in sorted_groups:
                if group_info["spots"]:
                    sorted_spots = sorted(group_info["spots"], key=lambda x: int(re.search(r'\d+', x["number"]).group()) if re.search(r'\d+', x["number"]) else 0)
                    spot_texts = []
                    for spot in sorted_spots:
                        spot_texts.append(f"{spot['number']}（{spot['status']}，更新於{spot['minutes_ago']}分鐘前）")
                    response_text += f"  {group_name}，空車位數量: {group_info['count']}，車格狀態: {', '.join(spot_texts)}\n"

        response_text += f"此次查詢共呼叫 {self.api_call_count} 次 API\n"
        return response_text, error_msgs, api_responses