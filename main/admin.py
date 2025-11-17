from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from .models import Poll, Option, Vote, AudienceCategory, AudienceOption, UserAudienceOption, BerlinPostalCode, UserProfile
from django.contrib.admin.widgets import FilteredSelectMultiple

class OptionInline(admin.TabularInline):
	model = Option
	extra = 3
	max_num = 10
	fields = ('text', 'order', 'votes')
	readonly_fields = ('votes',)


class PollAdminForm(forms.ModelForm):
	district_options = forms.ModelMultipleChoiceField(
		queryset=AudienceOption.objects.filter(category__name='Berlin Bezirk').order_by('name'),
		required=False,
		widget=FilteredSelectMultiple('Districts', is_stacked=False),
		label='Districts (Bezirke)'
	)

	class Meta:
		model = Poll
		fields = '__all__'
		widgets = {}

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		if self.instance and self.instance.pk:
			self.fields['district_options'].initial = list(
				self.instance.groups.filter(category__name='Berlin Bezirk').values_list('id', flat=True)
			)

	def save(self, commit=True):
		obj = super().save(commit)
		if obj.pk:
			selected_districts = list(self.cleaned_data.get('district_options') or [])
			# Preserve all non-Berlin-Bezirk groups and replace only Berlin-Bezirk
			others = obj.groups.exclude(category__name='Berlin Bezirk')
			obj.groups.set(list(others) + selected_districts)
		return obj


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
	form = PollAdminForm
	list_display = ('id', 'question', 'is_visible')
	list_editable = ('is_visible',)
	list_filter = ('is_visible', 'groups',)
	exclude = (
		'groups',
		'option_one', 'option_two', 'option_three',
		'option_one_count', 'option_two_count', 'option_three_count'
	)
	inlines = [OptionInline]

@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
	list_display = ('id', 'poll', 'text', 'order', 'votes')
	list_filter = ('poll',)

@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'poll', 'option', 'created')
	list_filter = ('poll', 'option')
@admin.register(AudienceCategory)
class AudienceCategoryAdmin(admin.ModelAdmin):
	list_display = ('id', 'name')
	search_fields = ('name',)


@admin.register(AudienceOption)
class AudienceOptionAdmin(admin.ModelAdmin):
	list_display = ('id', 'category', 'name')
	list_filter = ('category',)
	search_fields = ('name',)


class CustomUserCreationForm(forms.ModelForm):
	password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
	password2 = forms.CharField(label='Password confirmation', widget=forms.PasswordInput)

	class Meta:
		model = User
		fields = ('username', 'first_name', 'last_name', 'email')

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['first_name'].required = True
		self.fields['last_name'].required = True
		self.fields['email'].required = True

	def clean_email(self):
		email = self.cleaned_data.get('email', '').strip()
		if '@' not in email or '.' not in email.split('@')[-1]:
			raise forms.ValidationError('Please provide a valid email address.')
		return email

	def clean_password2(self):
		p1 = self.cleaned_data.get("password1")
		p2 = self.cleaned_data.get("password2")
		if p1 and p2 and p1 != p2:
			raise forms.ValidationError("Passwords don't match")
		return p2

	def save(self, commit=True):
		user = super().save(commit=False)
		user.set_password(self.cleaned_data["password1"])
		if commit:
			user.save()
		return user


class CustomUserAdmin(BaseUserAdmin):
	add_form = CustomUserCreationForm
	add_fieldsets = (
		(None, {
			'classes': ('wide',),
			'fields': ('username', 'first_name', 'last_name', 'email', 'password1', 'password2'),
		}),
	)

class UserProfileInline(admin.StackedInline):
	model = UserProfile
	can_delete = False
	extra = 0
	fields = ('postal_code',)

class UserAudienceOptionInline(admin.TabularInline):
	model = UserAudienceOption
	extra = 0
	fields = ('option',)

CustomUserAdmin.inlines = [UserProfileInline, UserAudienceOptionInline]

@admin.register(UserAudienceOption)
class UserAudienceOptionAdmin(admin.ModelAdmin):
	list_display = ('id', 'user', 'option')
	list_filter = ('option__category',)
	search_fields = ('user__username', 'option__name')

@admin.register(BerlinPostalCode)
class BerlinPostalCodeAdmin(admin.ModelAdmin):
	list_display = ('code', 'bezirk')
	search_fields = ('code', 'bezirk__name')
	list_filter = ('bezirk__category',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
	list_display = ('user', 'postal_code')
	search_fields = ('user__username', 'postal_code')


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
