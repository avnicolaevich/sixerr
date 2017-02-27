from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect

from django.views.generic import ListView, DetailView, CreateView

import braintree

from .models import Gig, Profile, Purchase, Review
from .forms import GigForm

braintree.Configuration.configure(braintree.Environment.Sandbox,
                                  merchant_id='8ykhmn7wsdn2xqm7',
                                  public_key='43t9nrz7gk33r482',
                                  private_key='b9ae0d74068c14ef1ba6a073ad5dd5cb')


class HomeListView(ListView):
    model = Gig
    template_name = 'home.html'
    context_object_name = 'gigs'


class GigDetailView(DetailView):
    model = Gig
    template_name = 'gig_detail.html'
    pk_url_kwarg = 'id'

    def get_context_data(self, **kwargs):
        if self.request.method == 'POST' and not self.request.user.is_anonymous() \
                and Purchase.objects.filter(gig_id=id, buyer=self.request.user).count() > 0 \
                and 'content' in self.request.POST and self.request.POST['content'] != '':
            Review.objects.create(content=self.request.POST['content'], gig_id=id, user=self.request.user)

        gig = self.get_object()

        if self.request.user.is_anonymous() or Purchase.objects.filter(gig=gig, buyer=self.request.user).count() > 0 \
                or Review.objects.filter(gig=gig, user=self.request.user).count() > 0:
            show_post_review = False
        else:
            show_post_review = Purchase.objects.filter(gig=gig, buyer=self.request.user).count() > 0
        reviews = Review.objects.filter(gig=gig)

        client_token = braintree.ClientToken.generate()
        context = {
            'show_post_review': show_post_review,
            'reviews': reviews,
            'client_token': client_token,
            'gig': gig,
        }
        return super(GigDetailView, self).get_context_data(**context)


@login_required(login_url='/')
def create_gig(request):
    if request.method == 'POST':
        gig_form = GigForm(request.POST, request.FILES)
        if gig_form.is_valid():
            gig = gig_form.save(commit=False)
            gig.user = request.user
            gig.save()
            return redirect('my_gigs')
        else:
            messages.success(request, 'Data is not valid')

    context = {
    }
    return render(request, 'create_gig.html', context)


@login_required(login_url='/')
def edit_gig(request, id):
    try:
        gig = Gig.objects.get(id=id, user=request.user)
        if request.method == 'POST':
            gig_form = GigForm(request.POST, request.FILES, instance=gig)
            if gig_form.is_valid():
                gig.save()
                return redirect('my_gigs')
            else:
                messages.success(request, 'Data is not valid')
        context = {
            'gig': gig,
        }
        return render(request, 'edit_gig.html', context)
    except Gig.DoesNotExist:
        return redirect('/')


@login_required(login_url='/')
def my_gigs(request):
    gigs = Gig.objects.filter(user=request.user)

    context = {
        'gigs': gigs
    }
    return render(request, 'my_gigs.html', context)


@login_required(login_url='/')
def profile(request, username):
    if request.method == 'POST':
        profile = Profile.objects.get(user=request.user)
        profile.about = request.POST['about']
        profile.slogan = request.POST['slogan']
        profile.save()
    else:
        try:
            profile = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            return redirect('/')

    gigs = Gig.objects.filter(user=profile.user, status=True)
    context = {
        'profile': profile,
        'gigs': gigs,
    }
    return render(request, 'profile.html', context)


@login_required(login_url="/")
def create_purchase(request):
    if request.method == 'POST':
        try:
            gig = Gig.objects.get(id=request.POST['gig_id'])
        except Gig.DoesNotExist:
            return redirect('/')

        nonce = request.POST["payment_method_nonce"]
        result = braintree.Transaction.sale({
            "amount": gig.price,
            "payment_method_nonce": nonce
        })

        if result.is_success:
            Purchase.objects.create(gig=gig, buyer=request.user)
    return redirect('/')


@login_required(login_url="/")
def my_sellings(request):
    purchases = Purchase.objects.filter(gig__user=request.user)

    context = {
        'purchases': purchases,
    }
    return render(request, 'my_sellings.html', context)


@login_required(login_url="/")
def my_buyings(request):
    purchases = Purchase.objects.filter(buyer=request.user)

    context = {
        'purchases': purchases,
    }
    return render(request, 'my_buyings.html', context)


def category(request, link):
    categories = {
        'graphic-design': 'GD',
        'digital-marketing': 'DM',
        'video-animation': 'VA',
        'music-audio': 'MA',
        'programming-tech': 'PT',
    }
    try:
        gigs = Gig.objects.filter(category=categories[link])
        context = {
            'gigs': gigs,
        }
        return render(request, 'home.html', context)
    except KeyError:
        return redirect('home')


def search(request):
    gigs = Gig.objects.filter(title__contains=request.GET['title'])
    context = {
        'gigs': gigs,
    }
    return render(request, 'home.html', context)