# coding: utf-8

"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase
from datetime import date
from currencies import Currency


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

class CurrencyTest(TestCase):
    def test_remote_service(self):
        """
        Invoke web page with currency rates and calculate value
        """
        c = Currency()
        v = round(c.convert(date(2012,4,10), 'EUR', 'USD', 2.0),2)
        self.assertEqual(v, 2.62)
