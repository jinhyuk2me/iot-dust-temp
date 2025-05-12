import requests
import json
from typing import Dict, Any, Optional, List, Union

class APIClient:
    """REST API 클라이언트 클래스
    
    설정에서 서버 주소와 포트를 가져와 API 요청을 처리합니다.
    """
    
    _instance = None
    
    def __new__(cls):
        """싱글톤 패턴 구현"""
        if cls._instance is None:
            cls._instance = super(APIClient, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """초기화 (한 번만 실행)"""
        if self._initialized:
            return
            
        # 기본 설정
        self.server_address = "localhost"
        self.api_port = 5001
        self.base_url = f"http://{self.server_address}:{self.api_port}/api"
        self.timeout = 1.0  # 요청 타임아웃 (초)
        self._initialized = True
        
    def update_config(self, server_address=None, api_port=None):
        """API 설정 업데이트"""
        if server_address:
            self.server_address = server_address
        if api_port:
            self.api_port = int(api_port)
            
        # 베이스 URL 업데이트
        self.base_url = f"http://{self.server_address}:{self.api_port}/api"
        
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """GET 요청 수행
        
        Args:
            endpoint: API 엔드포인트 경로 (/api/ 이후 부분)
            params: URL 파라미터 (옵션)
            
        Returns:
            응답 데이터 (JSON)
            
        Raises:
            ConnectionError: 연결 실패
            TimeoutError: 요청 시간 초과
            ValueError: 잘못된 응답
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()  # HTTP 에러 체크
            return response.json()
        except requests.exceptions.Timeout:
            print(f"[ERROR] API 요청 시간 초과: {url}")
            raise TimeoutError(f"API 요청 시간 초과: {url}")
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] API 서버 연결 실패: {url}")
            raise ConnectionError(f"API 서버 연결 실패: {url}")
        except requests.exceptions.HTTPError as e:
            print(f"[ERROR] API 요청 실패 (HTTP {response.status_code}): {url}")
            raise ValueError(f"API 요청 실패: {e}")
        except json.JSONDecodeError:
            print(f"[ERROR] API 응답 JSON 파싱 실패: {url}")
            raise ValueError("API 응답 JSON 파싱 실패")
    
    def post(self, endpoint: str, data: Dict) -> Dict:
        """POST 요청 수행
        
        Args:
            endpoint: API 엔드포인트 경로 (/api/ 이후 부분)
            data: 요청 바디 데이터
            
        Returns:
            응답 데이터 (JSON)
            
        Raises:
            ConnectionError: 연결 실패
            TimeoutError: 요청 시간 초과
            ValueError: 잘못된 응답
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        # 디버그 출력 추가
        print(f"[DEBUG] API 요청 URL: {url}")
        print(f"[DEBUG] API 요청 데이터: {data}")
        
        try:
            response = requests.post(url, json=data, timeout=self.timeout)
            # 디버그 출력 추가
            print(f"[DEBUG] API 응답 상태 코드: {response.status_code}")
            
            # 응답 내용 확인 (가능한 경우)
            try:
                print(f"[DEBUG] API 응답 내용: {response.text[:200]}...")
            except:
                print("[DEBUG] API 응답 내용을 표시할 수 없습니다.")
            
            # HTTP 에러 처리 개선
            if response.status_code >= 400:
                print(f"[ERROR] API 요청 실패 (HTTP {response.status_code}): {url}")
                error_message = f"HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict) and "message" in error_data:
                        error_message = f"{error_message} - {error_data['message']}"
                except:
                    if response.text:
                        error_message = f"{error_message} - {response.text[:100]}"
                
                raise ValueError(error_message)
            
            response.raise_for_status()  # 혹시 모를 다른 HTTP 에러 체크
            return response.json()
        except requests.exceptions.Timeout:
            print(f"[ERROR] API 요청 시간 초과: {url}")
            raise TimeoutError(f"API 요청 시간 초과: {url}")
        except requests.exceptions.ConnectionError:
            print(f"[ERROR] API 서버 연결 실패: {url}")
            raise ConnectionError(f"API 서버 연결 실패: {url}")
        except requests.exceptions.HTTPError as e:
            print(f"[ERROR] API 요청 실패 (HTTP {response.status_code}): {url}")
            raise ValueError(f"API 요청 실패: {e}")
        except json.JSONDecodeError:
            print(f"[ERROR] API 응답 JSON 파싱 실패: {url}")
            raise ValueError("API 응답 JSON 파싱 실패")
    
    # 트럭 관련 API 메서드
    def get_all_trucks(self) -> Dict:
        """모든 트럭 정보 조회"""
        return self.get("trucks")
    
    def get_truck(self, truck_id: str) -> Dict:
        """특정 트럭 정보 조회"""
        return self.get(f"trucks/{truck_id}")
    
    def get_all_truck_positions(self) -> Dict:
        """모든 트럭 위치 정보 조회"""
        return self.get("trucks/positions")
    
    def get_truck_position(self, truck_id: str) -> Dict:
        """특정 트럭 위치 정보 조회"""
        return self.get(f"trucks/{truck_id}/position")
    
    def get_all_truck_batteries(self) -> Dict:
        """모든 트럭 배터리 정보 조회"""
        return self.get("trucks/batteries")
    
    def get_truck_battery(self, truck_id: str) -> Dict:
        """특정 트럭 배터리 정보 조회"""
        return self.get(f"trucks/{truck_id}/battery")
    
    def update_truck_battery(self, truck_id: str, level: float, is_charging: bool) -> Dict:
        """특정 트럭 배터리 정보 업데이트"""
        data = {"level": level, "is_charging": is_charging}
        return self.post(f"trucks/{truck_id}/battery", data)
    
    # 미션 관련 API 메서드
    def get_all_missions(self) -> List[Dict]:
        """모든 미션 조회"""
        return self.get("missions")
    
    def get_mission(self, mission_id: str) -> Dict:
        """특정 미션 조회"""
        return self.get(f"missions/{mission_id}")
    
    def create_mission(self, mission_data: Dict) -> Dict:
        """미션 생성"""
        return self.post("missions", mission_data)
    
    def complete_mission(self, mission_id: str) -> Dict:
        """미션 완료 처리"""
        return self.post(f"missions/{mission_id}/complete", {})
    
    def cancel_mission(self, mission_id: str) -> Dict:
        """미션 취소 처리"""
        return self.post(f"missions/{mission_id}/cancel", {})
    
    # 시설 관련 API 메서드
    def get_all_facilities(self) -> Dict:
        """모든 시설 정보 조회"""
        return self.get("facilities")
    
    def get_all_gates(self) -> Dict:
        """모든 게이트 정보 조회"""
        return self.get("facilities/gates")
    
    def get_gate(self, gate_id: str) -> Dict:
        """특정 게이트 정보 조회"""
        return self.get(f"facilities/gates/{gate_id}")
    
    def get_all_belts(self) -> Dict:
        """모든 벨트 정보 조회"""
        return self.get("facilities/belts")
    
    def get_belt(self, belt_id: str) -> Dict:
        """특정 벨트 정보 조회"""
        return self.get(f"facilities/belt/{belt_id}")
        
    def control_gate(self, gate_id: str, command: str) -> Dict:
        """게이트 제어
        
        Args:
            gate_id: 게이트 ID (예: "GATE_A")
            command: 제어 명령 ("open" 또는 "close")
        """
        data = {"command": command}
        return self.post(f"facilities/gates/{gate_id}/control", data)
    
    def control_belt(self, belt_id: str, command: str, speed: int = None) -> Dict:
        """벨트 제어
        
        Args:
            belt_id: 벨트 ID (예: "BELT")
            command: 제어 명령 ("start", "stop", "emergency_stop")
            speed: 벨트 속도 (0-100)
        """
        data = {"command": command}
        if speed is not None:
            data["speed"] = speed
        return self.post(f"facilities/belt/{belt_id}/control", data)
    
    # 시스템 관련 API 메서드
    def restart_tcp_server(self) -> Dict:
        """TCP 서버 재시작
        
        Returns:
            응답 데이터 (JSON)
        """
        return self.post("system/tcp/restart", {})
        
    def get_tcp_server_status(self) -> Dict:
        """TCP 서버 상태 조회
        
        Returns:
            TCP 서버 상태 정보 (JSON)
        """
        return self.get("system/tcp/status")

# 싱글톤 인스턴스 사용을 위한 전역 변수
api_client = APIClient() 