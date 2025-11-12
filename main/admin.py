from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django import forms
from .models import Poll, Option, Vote

class OptionInline(admin.TabularInline):
	model = Option
	extra = 3
	max_num = 10
	fields = ('text', 'order', 'votes')
	readonly_fields = ('votes',)

@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
	list_display = ('id', 'question')
	exclude = (
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


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
