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
        try:
            cat_name = self.category.name if self.category_id else ''
        except Exception:
            cat_name = ''
        if cat_name == 'Berlin Bezirk':
            return f"Berlin - {self.name}"
        return f"{cat_name}: {self.name}" if cat_name else self.name


class UserAudienceOption(models.Model):
    """Selected audience option for a user (e.g., the user's State or City)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='audience_options')
    option = models.ForeignKey(AudienceOption, on_delete=models.CASCADE, related_name='users')

    class Meta:
        unique_together = ('user', 'option')

    def __str__(self):
        return f"{self.user} -> {self.option}"


class BerlinPostalCode(models.Model):
    """Mapping of Berlin postal code to its Bezirk (district)."""
    code = models.CharField(max_length=10, unique=True)
    # The Bezirk is modeled as an AudienceOption under the category "Berlin Bezirk"
    bezirk = models.ForeignKey(AudienceOption, on_delete=models.CASCADE, related_name='postal_codes')

    class Meta:
        verbose_name = "Berlin postal code"
        verbose_name_plural = "Berlin postal codes"

    def __str__(self):
        return f"{self.code} -> {self.bezirk.name}"


class UserProfile(models.Model):
    """Extension of the built-in User storing the postal code used for automatic restriction assignment."""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    postal_code = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"Profile({self.user.username}) postal={self.postal_code or '-'}"

    class Meta:
        verbose_name = "User profile"
        verbose_name_plural = "User profiles"

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_user_profile(sender, instance, created, **kwargs):
    """Create a profile automatically when a new user is created."""
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=UserProfile)
def sync_postal_restriction(sender, instance, **kwargs):
    """Whenever a profile's postal code changes, (re)assign the Berlin Bezirk restriction if applicable."""
    code = (instance.postal_code or '').strip()
    if not code:
        return
    mapping = BerlinPostalCode.objects.select_related('bezirk__category').filter(code=code).first()
    if not mapping:
        return
    bezirk_option = mapping.bezirk
    # Guarantee category integrity
    if bezirk_option.category.name != 'Berlin Bezirk':
        cat, _ = AudienceCategory.objects.get_or_create(name='Berlin Bezirk')
        if bezirk_option.category_id != cat.id:
            bezirk_option, _ = AudienceOption.objects.get_or_create(category=cat, name=mapping.bezirk.name)
    # Replace any existing selection for this category
    UserAudienceOption.objects.filter(user=instance.user, option__category=bezirk_option.category).delete()
    UserAudienceOption.objects.get_or_create(user=instance.user, option=bezirk_option)


class EmailVerification(models.Model):
    """Stores a short numeric verification code sent to an email address.

    Used during registration: a code is created for an email and expires after a short period.
    """
    email = models.EmailField()
    code = models.CharField(max_length=12)
    created = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["email"]), models.Index(fields=["code"])]

    def __str__(self):
        return f"EmailVerification({self.email}) code={self.code} used={self.used}"