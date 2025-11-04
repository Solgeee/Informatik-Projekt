#DATABASES CREATED HERE; EACH CLASS IN MODELS REPRESENTS A TABLE
from django.db import models
from django.conf import settings

# Create your models here.
class Poll(models.Model):
    question = models.TextField(default="New Question")
    option_one = models.CharField(max_length=30, default="Option 1")
    option_two = models.CharField(max_length=30, default="Option 2")
    option_three = models.CharField(max_length=30, default="Option 3")
    option_one_count = models.IntegerField(default=0)
    option_two_count = models.IntegerField(default=0)
    option_three_count = models.IntegerField(default=0)

    def total(self):
        return self.option_one_count + self.option_two_count + self.option_three_count


class Vote(models.Model):
    """Record of a user's vote for a specific poll.

    This prevents double-counting by keeping one Vote per (user, poll).
    When a user changes their vote we update this record and adjust the
    Poll counters accordingly.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='votes')
    choice = models.CharField(max_length=10, choices=(
        ('option1', 'Option 1'),
        ('option2', 'Option 2'),
        ('option3', 'Option 3'),
    ))
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'poll')

    def __str__(self):
        return f"{self.user} -> {self.poll.id}: {self.choice}"