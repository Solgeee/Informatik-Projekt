from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from .models import EmailVerification


class EmailVerificationModelTests(TestCase):
    def test_create_and_expire(self):
        now = timezone.now()
        ev = EmailVerification.objects.create(email='test@example.com', code='123456', expires_at=now + timedelta(minutes=1))
        self.assertFalse(ev.used)
        # should be retrievable while not expired
        found = EmailVerification.objects.filter(email__iexact='test@example.com', code='123456', used=False, expires_at__gte=timezone.now()).first()
        self.assertIsNotNone(found)
        # mark used
        ev.used = True
        ev.save()
        found2 = EmailVerification.objects.filter(email__iexact='test@example.com', code='123456', used=False).first()
        self.assertIsNone(found2)
