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
    # Audience targeting: assign poll to one or more audience options (e.g., State, City)
    # Empty = visible to all (subject to is_visible)
    # Note: User-side filtering will be implemented later.
    
    # ManyToMany declared after AudienceOption class definition below using a string reference
    groups = models.ManyToManyField('AudienceOption', blank=True, related_name='polls', help_text="Restrict visibility to selected audience options (leave empty for everyone).")

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


class AudienceCategory(models.Model):
    """A category for audience targeting (e.g., State, City)."""
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = "Audience categories"

    def __str__(self):
        return self.name


class AudienceOption(models.Model):
    """An option within a category (e.g., 'California' under 'State')."""
    category = models.ForeignKey(AudienceCategory, on_delete=models.CASCADE, related_name='options')
    name = models.CharField(max_length=100)

    class Meta:
        unique_together = ('category', 'name')
        ordering = ['category__name', 'name']

    def __str__(self):
        return f"{self.category.name}: {self.name}"


class UserAudienceOption(models.Model):
    """Selected audience option for a user (e.g., the user's State or City)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='audience_options')
    option = models.ForeignKey(AudienceOption, on_delete=models.CASCADE, related_name='users')

    class Meta:
        unique_together = ('user', 'option')

    def __str__(self):
        return f"{self.user} -> {self.option}"