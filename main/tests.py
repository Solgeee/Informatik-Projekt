#THIS FILE IS FOR TESTS
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Poll, Option, Vote


class ResultsBootstrapTest(TestCase):
	def test_results_bootstrap_creates_options(self):
		# Create a poll with legacy fields but no dynamic options
		p = Poll.objects.create(
			question="Q?",
			option_one="A",
			option_two="B",
			option_three="C",
			option_one_count=2,
			option_two_count=3,
			option_three_count=4,
		)

		self.assertEqual(Option.objects.filter(poll=p).count(), 0)

		url = reverse('results', args=[p.id])
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)

		opts = list(Option.objects.filter(poll=p).order_by('order'))
		self.assertEqual(len(opts), 3)
		self.assertEqual([o.text for o in opts], ["A", "B", "C"])
		self.assertEqual([o.votes for o in opts], [2, 3, 4])


class VoteFlowTest(TestCase):
	def setUp(self):
		self.User = get_user_model()

	def test_vote_post_increments_and_redirects(self):
		user = self.User.objects.create_user(username='u', email='u@example.com', password='pw')
		p = Poll.objects.create(
			question="Pick",
			option_one="X",
			option_two="Y",
			option_three="Z",
		)
		# Ensure options exist (either via GET bootstrap or manual create); here manual for clarity
		x = Option.objects.create(poll=p, text="X", order=0)
		y = Option.objects.create(poll=p, text="Y", order=1)

		self.client.login(username='u', password='pw')

		url = reverse('vote', args=[p.id])
		resp = self.client.post(url, data={'option': str(x.id)})
		# Expect redirect to results
		self.assertEqual(resp.status_code, 302)
		self.assertIn('/results/', resp['Location'])

		x.refresh_from_db()
		y.refresh_from_db()
		self.assertEqual(x.votes, 1)
		self.assertEqual(y.votes, 0)

		# Change vote to Y; X should decrement, Y increment
		resp2 = self.client.post(url, data={'option': str(y.id)})
		self.assertEqual(resp2.status_code, 302)
		x.refresh_from_db(); y.refresh_from_db()
		self.assertEqual(x.votes, 0)
		self.assertEqual(y.votes, 1)


class HomeVisibilityTest(TestCase):
	def setUp(self):
		self.User = get_user_model()

	def test_home_shows_only_visible_polls(self):
		p1 = Poll.objects.create(question="Visible Poll", is_visible=True)
		p2 = Poll.objects.create(question="Hidden Poll", is_visible=False)

		url = reverse('home')
		resp = self.client.get(url)
		self.assertEqual(resp.status_code, 200)
		html = resp.content.decode('utf-8')
		self.assertIn("Visible Poll", html)
		self.assertNotIn("Hidden Poll", html)

	def test_missing_option_shows_error(self):
		user = self.User.objects.create_user(username='u2', email='u2@example.com', password='pw')
		p = Poll.objects.create(question="Pick", option_one="X")
		Option.objects.create(poll=p, text="X", order=0)
		self.client.login(username='u2', password='pw')
		url = reverse('vote', args=[p.id])
		resp = self.client.post(url, data={})
		self.assertEqual(resp.status_code, 200)
		self.assertContains(resp, 'Please select an option', status_code=200)

# Create your tests here.
