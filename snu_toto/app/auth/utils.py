import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from snu_toto.app.auth.exceptions import EmailSendFailedException
from snu_toto.app.core.config import EMAIL_SETTINGS

class EmailSender:
    @staticmethod
    async def send_verification_email(to_email: str, code: str):
        """인증 코드를 포함한 메일을 발송"""
        msg = MIMEMultipart()
        msg["From"] = EMAIL_SETTINGS.USER
        msg["To"] = to_email
        msg["Subject"] = "[SNU-TOTO] 스누메일 인증 번호입니다."

        body = f"SNU-TOTO 인증 번호는 [{code}] 입니다. 5분 이내에 입력해 주세요."
        msg.attach(MIMEText(body, "plain"))

        try:
            await aiosmtplib.send(
                msg,
                hostname=EMAIL_SETTINGS.HOST,
                port=EMAIL_SETTINGS.PORT,
                username=EMAIL_SETTINGS.USER,
                password=EMAIL_SETTINGS.PASSWORD,
                use_tls=False,
                start_tls=True
            )
        
        except Exception as e:
            import logging
            logging.error(f"SMTP Error: {str(e)}") # 디버깅을 위한 로그

            raise EmailSendFailedException()