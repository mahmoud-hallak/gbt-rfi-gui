from datetime import datetime

from django.test import TestCase

from .forms import QueryForm


# Create your tests here.
class FreqTestCases(TestCase):
	def test_FreqHighLow(self):
		form = QueryForm(data = {"freq_low":1301, "freq_high":1300})
		self.assertEquals(form.errors["freq_low"], ["Low Frequency must be less than High Frequency"])
	def test_HighEqLow(self):
		form = QueryForm(data = {"freq_low":1300, "freq_high":1300})
		self.assertEquals(form.errors["freq_low"], ['Frequencies cannot be the same'])
	def test_NotFloat1(self):
		form = QueryForm(data = {"freq_low":"hi", "freq_high":1300})
		self.assertEquals(form.errors["freq_low"], ['Enter a number.'])
	def test_NotFloat2(self):
		form = QueryForm(data = {"freq_high":1300, "freq_high":"hello"})
		self.assertEquals(form.errors["freq_high"], ['Enter a number.'])
	def test_NotFloat3(self):
		form = QueryForm(data = {"freq_low":"some", "freq_high":"thing"})
		self.assertEquals(form.errors["freq_low"], ['Enter a number.'])
		self.assertEquals(form.errors["freq_high"], ['Enter a number.'])

class DateTestCases(TestCase):
	def test_noEndbutStart(self):
		form = QueryForm(data = {"start":datetime(2022, 10, 1, 17, 30, 29, 431717)})
		self.assertEquals(form.errors["start"], ['Specify a start and end date'])
	def test_noStartbutEnd(self):
		form = QueryForm(data = {"end":datetime(2022, 10, 1, 17, 30, 29, 431717)})
		self.assertEquals(form.errors["end"], ['Specify a start and end date'])
	def test_DateEndStart(self):
		form = QueryForm(data = {"end":datetime(2022, 10, 1, 17, 30, 29, 431717), "start":datetime(2022, 10, 3, 17, 30, 29, 431717)})
		self.assertEquals(form.errors["end"], ['End date must be later than start date'])
		self.assertEquals(form.errors["start"], ['End date must be later than start date'])
	def test_MoreThanAYear(self):
		form = QueryForm(data = {"end":datetime(2020, 10, 1, 17, 30, 29, 431717), "start":datetime(2022, 10, 1, 17, 30, 29, 431717)})
		self.assertEquals(form.errors["end"], ['End date must be later than start date'])
	def test_DateAndStartEnd(self):
		form = QueryForm(data = {"end":datetime(2020, 10, 1, 17, 30, 29, 431717), "date":datetime(2022, 10, 1, 17, 30, 29, 431717)})
		self.assertEquals(form.errors["end"], ['Specify a start and end date', 'Specify a date of interest OR date range'])
		self.assertEquals(form.errors["start"], ['Specify a start and end date', 'Specify a date of interest OR date range'])
		self.assertEquals(form.errors["date"], ['Specify a date of interest OR date range'])
		form = QueryForm(data = {"start":datetime(2020, 10, 1, 17, 30, 29, 431717), "date":datetime(2022, 10, 1, 17, 30, 29, 431717)})
		self.assertEquals(form.errors["end"], ['Specify a start and end date', 'Specify a date of interest OR date range'])
		self.assertEquals(form.errors["start"], ['Specify a start and end date', 'Specify a date of interest OR date range'])
		self.assertEquals(form.errors["date"], ['Specify a date of interest OR date range'])
	def test_NoDateGiven(self):
		form = QueryForm(data = {})
		self.assertEquals(form.errors["end"], ['Specify a date of interest OR date range'])
		self.assertEquals(form.errors["start"], ['Specify a date of interest OR date range'])
		self.assertEquals(form.errors["date"], ['Specify a date of interest OR date range'])
