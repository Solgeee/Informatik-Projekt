#REQUEST RESPONSE LOGIC
from django.http import HttpResponse
from django.shortcuts import render


def index(request):
    return HttpResponse("Hello, world. You're at the main index.")

def vote(request):
    return render(request, "main/vote.html")

def results(request):
    return render(request, "main/results.html")

def login(request):
    return render(request, "main/login.html")