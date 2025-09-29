#REQUEST RESPONSE LOGIC
from django.http import HttpResponse


def index(request):
    return HttpResponse("Hello, world. You're at the main index.")
def vote(request):
    return HttpResponse("Where Polls are voted on.")
def results(request):
    return HttpResponse("Where Poll results are shown.")
def login(request):
    return HttpResponse("This is the login page.")
