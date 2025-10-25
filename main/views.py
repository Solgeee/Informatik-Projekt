#REQUEST RESPONSE LOGIC
from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from .models import Poll  # Add this import


def home(request):
    polls = Poll.objects.all()  # Get all polls from database
    context = {
        'polls': polls
    }
    return render(request, "main/home.html", context)

def vote(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    
    if request.method == 'POST':
        selected_option = request.POST.get('poll_choice')
        if selected_option == 'option1':
            poll.option_one_count += 1
        elif selected_option == 'option2':
            poll.option_two_count += 1
        elif selected_option == 'option3':
            poll.option_three_count += 1
        else:
            return HttpResponse(400, 'Invalid form option')
            
        poll.save()
        return redirect('results', poll_id=poll_id)  # Updated this line
    
    context = {
        'poll': poll
    }
    return render(request, "main/vote.html", context)

def results(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id)
    context = {
        'poll': poll
    }
    return render(request, "main/results.html", context)

def login(request):
    return render(request, "main/login.html")