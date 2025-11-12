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
    is_visible = models.BooleanField(default=True, help_text="Controls whether this poll appears on the home page list.")

    def total(self):
        return self.option_one_count + self.option_two_count + self.option_three_count

    def dynamic_total(self):
        """Total based on related Option objects (new dynamic model)."""
        return sum(o.votes for o in self.options.all())


class Option(models.Model):
    """Dynamic poll option; supports arbitrary number of options per poll."""
    poll = models.ForeignKey(Poll, related_name='options', on_delete=models.CASCADE)
    text = models.CharField(max_length=100)
    votes = models.PositiveIntegerField(default=0)
    order = models.PositiveIntegerField(default=0, help_text="Display order (0-based; sequential).")

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f"Option({self.text}) for Poll {self.poll.id}"


class Vote(models.Model):
    """User's vote for a poll via a specific Option.

    Maintains uniqueness per (user, poll) preventing multi-voting.
    Legacy 'choice' retained for backward compatibility but deprecated.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name='votes')
    option = models.ForeignKey(Option, on_delete=models.CASCADE, null=True, blank=True)
    # Deprecated legacy field (will be phased out once data migrates)
    choice = models.CharField(max_length=10, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'poll')

    def __str__(self):
        return f"{self.user} -> {self.poll.id}: {self.option or self.choice}"