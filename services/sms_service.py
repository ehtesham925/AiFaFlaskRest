from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()



class SmsService:
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "your_auth_token")
        self.verify_service_sid = os.getenv("TWILIO_VERIFY_SID", "VAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
        self.client = Client(self.account_sid, self.auth_token)


    
    def send_otp(self,phone_number):
        verification = self.client.verify.v2.services(self.verify_service_sid).verifications.create(
            to=phone_number,
            channel='sms'  # or 'call' for voice OTP
      )
        print(f"OTP sent to {phone_number}, status: {verification.status}")

    
    
    def check_otp(self,phone_number, code):
        verification_check = self.client.verify.v2.services(self.verify_service_sid).verification_checks.create(
            to=phone_number,
            code=code
        )
        print(f"Verification status: {verification_check.status}")



if __name__ == "__main__":
    sms = SmsService()
    phone = "+919700404029"  # Must match the number used in send_otp
    # sms.send_otp(phone)
    # otp_code = input("Enter the OTP you received: ")
    # sms.check_otp(phone, otp_code)
