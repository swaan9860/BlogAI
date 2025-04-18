# blog/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('post/create/', views.create_post, name='create_post'),
    path('post/<slug:slug>/', views.post_detail, name='post_detail'),
    path('post/<slug:slug>/edit/', views.edit_post, name='edit_post'),
    path('post/<slug:slug>/delete/', views.delete_post, name='delete_post'),
    path('signup/', views.signup, name='signup'),
    path('preferences/', views.user_preferences, name='preferences'),
    path('search/suggestions/', views.search_suggestions, name='search_suggestions'),
    path('search/ajax/', views.ajax_search, name='ajax_search'),
]