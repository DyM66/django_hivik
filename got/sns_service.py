import boto3
from django.conf import settings
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

class SNSService:
    def _init_(self):
        # Inicializar el cliente SNS
        self.sns_client = boto3.client(
            'sns',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

    def send_sms(self, phone_number, message):
        try:
            # Enviar un mensaje SMS
            response = self.sns_client.publish(
                PhoneNumber=phone_number,  # Número de teléfono en formato internacional
                Message=message,           # El mensaje SMS
            )
            return response
        except NoCredentialsError:
            raise Exception("Credenciales de AWS no encontradas.")
        except PartialCredentialsError:
            raise Exception("Credenciales de AWS incompletas.")
        except Exception as e:
            raise Exception(f"Ocurrió un error al enviar el SMS: {str(e)}")