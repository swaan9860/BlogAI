# blog/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden, JsonResponse
from django.utils.text import slugify
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth import get_user_model
from .models import Post, UserPreference, PostInteraction
from .forms import PostForm, CommentForm, UserPreferenceForm
import numpy as np
from scipy.sparse import coo_matrix
from sklearn.metrics.pairwise import cosine_similarity

User = get_user_model()

def post_list(request):
    query = request.GET.get('q', '')
    posts = Post.objects.exclude(slug__exact='').order_by('-created_at')
    recommended_posts = None
    if request.user.is_authenticated:
        try:
            # Collaborative filtering recommendations
            recommended_posts = get_collaborative_recommendations(request.user)
            if not recommended_posts:
                # Fallback to tag-based recommendations
                user_prefs = request.user.userpreference
                preferred_tags = user_prefs.preferred_tags.names()
                if preferred_tags:
                    recommended_posts = Post.objects.filter(
                        tags__name__in=preferred_tags
                    ).exclude(author=request.user).distinct()[:3]
        except UserPreference.DoesNotExist:
            pass
    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__name__in=[query])
        ).distinct()
    return render(request, 'blog/post_list.html', {
        'posts': posts,
        'query': query,
        'recommended_posts': recommended_posts
    })

def search_suggestions(request):
    query = request.GET.get('term', '').strip()
    if query:
        tags = Post.objects.filter(
            tags__name__istartswith=query
        ).values_list('tags__name', flat=True).distinct()[:10]
        suggestions = list(set(tags))  # Remove duplicates
    else:
        suggestions = []
    return JsonResponse(suggestions, safe=False)

def ajax_search(request):
    query = request.GET.get('q', '').strip()
    posts = Post.objects.exclude(slug__exact='')
    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__name__in=[query])
        ).distinct()[:10]
    results = [{
        'title': post.title,
        'slug': post.slug,
        'content': post.content[:100],
        'author': post.author.username,
        'created_at': post.created_at.strftime('%b %d, %Y'),
        'picture': post.picture.url if post.picture else None
    } for post in posts]
    return JsonResponse({'results': results})

def get_collaborative_recommendations(user, num_recommendations=3):
    # Get all users and posts
    users = User.objects.all()
    posts = Post.objects.filter(is_published=True)
    if not users or not posts:
        return None

    # Create user-post interaction matrix (1 for viewed, 0 otherwise)
    user_ids = {user.id: idx for idx, user in enumerate(users)}
    post_ids = {post.id: idx for idx, post in enumerate(posts)}
    rows, cols, data = [], [], []
    
    interactions = PostInteraction.objects.filter(viewed=True)
    for interaction in interactions:
        if interaction.user.id in user_ids and interaction.post.id in post_ids:
            rows.append(user_ids[interaction.user.id])
            cols.append(post_ids[interaction.post.id])
            data.append(1)

    # Create sparse matrix
    interaction_matrix = coo_matrix((data, (rows, cols)), shape=(len(users), len(posts)))
    interaction_matrix = interaction_matrix.tocsr()

    # Compute cosine similarity between users
    similarity = cosine_similarity(interaction_matrix)
    user_idx = user_ids.get(user.id)
    if user_idx is None:
        return None

    # Get similar users
    similar_users = np.argsort(similarity[user_idx])[::-1][1:11]  # Top 10 similar users
    similar_user_ids = [list(user_ids.keys())[idx] for idx in similar_users]

    # Recommend posts viewed by similar users but not by the current user
    viewed_posts = set(PostInteraction.objects.filter(user=user, viewed=True).values_list('post__id', flat=True))
    recommended_posts = Post.objects.filter(
        postinteraction__user__id__in=similar_user_ids,
        postinteraction__viewed=True
    ).exclude(id__in=viewed_posts).distinct()[:num_recommendations]

    return recommended_posts

def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if request.user.is_authenticated:
        PostInteraction.objects.get_or_create(user=request.user, post=post, defaults={'viewed': True})
    return render(request, 'blog/post_detail.html', {'post': post})

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            base_slug = slugify(post.title)
            slug = base_slug
            counter = 1
            while Post.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            post.slug = slug
            post.save()
            form.save_m2m()
            messages.success(request, 'Post created!')
            return redirect(post.get_absolute_url())
    else:
        form = PostForm()
    return render(request, 'blog/post_create.html', {'form': form})

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('post_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

@login_required
def edit_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if post.author.username != request.user.username:
        return HttpResponseForbidden("You can only edit your own posts.")
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated!')
            return redirect(post.get_absolute_url())
    else:
        form = PostForm(instance=post)
    return render(request, 'blog/post_edit.html', {'form': form, 'post': post})

@login_required
def delete_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if post.author.username != request.user.username:
        return HttpResponseForbidden("You can only delete your own posts.")
    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post deleted!')
        return redirect('post_list')
    return render(request, 'blog/post_delete.html', {'post': post})

@login_required
def user_preferences(request):
    try:
        preference = request.user.userpreference
    except UserPreference.DoesNotExist:
        preference = UserPreference(user=request.user)
        preference.save()
    if request.method == 'POST':
        form = UserPreferenceForm(request.POST, instance=preference)
        if form.is_valid():
            form.save()
            messages.success(request, 'Preferences updated!')
            return redirect('post_list')
    else:
        form = UserPreferenceForm(instance=preference)
    return render(request, 'blog/preferences.html', {'form': form})