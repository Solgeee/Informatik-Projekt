#THIS FILE IS FOR TESTS
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Poll, Option, Vote
from .models import AudienceCategory, AudienceOption, UserAudienceOption


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

class RestrictionEnforcementTest(TestCase):
	def setUp(self):
		self.User = get_user_model()
		# Create categories and options
		cat1 = AudienceCategory.objects.create(name='State')
		cat2 = AudienceCategory.objects.create(name='City')
		self.o1 = AudienceOption.objects.create(category=cat1, name='CA')
		self.o2 = AudienceOption.objects.create(category=cat2, name='SF')
		self.poll = Poll.objects.create(question='Q?', is_visible=True)

	def test_user_cannot_vote_without_restrictions(self):
		user = self.User.objects.create_user(username='u3', email='u3@example.com', password='pw')
		# Add poll option to vote on
		opt = Option.objects.create(poll=self.poll, text='A', order=0)
		self.client.login(username='u3', password='pw')
		vote_url = reverse('vote', args=[self.poll.id])
		resp = self.client.get(vote_url)
		# Should redirect to restrictions page
		self.assertEqual(resp.status_code, 302)
		self.assertIn('restrictions', resp['Location'])

	def test_user_can_vote_after_restrictions(self):
		user = self.User.objects.create_user(username='u4', email='u4@example.com', password='pw')
		Option.objects.create(poll=self.poll, text='A', order=0)
		self.client.login(username='u4', password='pw')
		# Assign restrictions
		UserAudienceOption.objects.create(user=user, option=self.o1)
		UserAudienceOption.objects.create(user=user, option=self.o2)
		vote_url = reverse('vote', args=[self.poll.id])
		resp = self.client.get(vote_url)
		self.assertEqual(resp.status_code, 200)

	def test_incomplete_restrictions_block_vote(self):
		user = self.User.objects.create_user(username='u5', email='u5@example.com', password='pw')
		Option.objects.create(poll=self.poll, text='A', order=0)
		self.client.login(username='u5', password='pw')
		# Assign only one category restriction (incomplete)
		UserAudienceOption.objects.create(user=user, option=self.o1)
		vote_url = reverse('vote', args=[self.poll.id])
		resp = self.client.get(vote_url)
		self.assertEqual(resp.status_code, 302)
		self.assertIn('restrictions', resp['Location'])

	def test_excess_restrictions_block_vote(self):
		user = self.User.objects.create_user(username='u6', email='u6@example.com', password='pw')
		Option.objects.create(poll=self.poll, text='A', order=0)
		self.client.login(username='u6', password='pw')
		# Add two selections for same category (simulate corruption)
		UserAudienceOption.objects.create(user=user, option=self.o1)
		# create another option in first category
		alt = AudienceOption.objects.create(category=self.o1.category, name='NV')
		UserAudienceOption.objects.create(user=user, option=alt)
		# Also add second category restriction to satisfy count but with duplication
		UserAudienceOption.objects.create(user=user, option=self.o2)
		vote_url = reverse('vote', args=[self.poll.id])
		resp = self.client.get(vote_url)
		self.assertEqual(resp.status_code, 302)
		self.assertIn('restrictions', resp['Location'])

# Create your tests here.
