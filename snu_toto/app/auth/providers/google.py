import httpx
from snu_toto.app.core.config import GOOGLE_SETTINGS

class GoogleAuthClient:
    def __init__(self):
        self.client_id = GOOGLE_SETTINGS.CLIENT_ID
        self.client_secret = GOOGLE_SETTINGS.CLIENT_SECRET
        self.redirect_uri = GOOGLE_SETTINGS.REDIRECT_URI
        self.token_url = "https://oauth2.googleapis.com/token"
        self.userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"

    def get_auth_url(self) -> str:
        """유저를 리다이렉트시킬 구글 인증 페이지 주소 생성"""
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "offline",
            "prompt": "select_account"
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"https://accounts.google.com/o/oauth2/v2/auth?{query_string}"

    async def get_user_info(self, code: str) -> dict:
        """인가 코드로 토큰을 받고 유저 정보를 가져옴"""
        async with httpx.AsyncClient() as client:
            try:
                # 1. Access Token 요청
                token_data = {
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                }
                token_res = await client.post(self.token_url, data=token_data)
                token_res.raise_for_status()
                access_token = token_res.json().get("access_token")

                # 2. 유저 정보(Email, Social ID) 요청
                headers = {"Authorization": f"Bearer {access_token}"}
                user_res = await client.get(self.userinfo_url, headers=headers)
                user_res.raise_for_status()
                return user_res.json()
            
            except httpx.HTTPStatusError as e:
                # 구글 서버에서 4xx, 5xx 에러를 보낸 경우
                raise ValueError(f"Google API error: {e.response.text}")