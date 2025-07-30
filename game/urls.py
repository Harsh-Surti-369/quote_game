from django.urls import path
from .views import DiaryEntryView,GroupPointsView, get_quote_part,get_active_flips,VerifyQuotePairView

urlpatterns = [
    path('diary-entry', DiaryEntryView.as_view(), name='diary-entry'),
    path('get-quote-part', get_quote_part, name='get-quote-part'),
    path('verify-quote-pair', VerifyQuotePairView.as_view(), name='verify-quote-pair'),
    path('active-flips', get_active_flips, name='active-flips'),
    path('group-points', GroupPointsView.as_view(), name='group-points'),
]