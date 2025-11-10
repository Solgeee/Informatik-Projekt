from django.contrib import admin
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
