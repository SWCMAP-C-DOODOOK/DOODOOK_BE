from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

from apps.ledger.views_stats import AccumulatedStatsView, CategoryShareStatsView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.budget.urls')),
    path('api/', include('apps.openbanking.urls')),
    path('api/', include('apps.ocr.urls')),
    path('api/', include('apps.dues.urls')),
    path('api/stats/category', CategoryShareStatsView.as_view()),
    path('api/stats/accumulated', AccumulatedStatsView.as_view()),
    path('api/', include('apps.common.urls')),
    path('api/', include('apps.users.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
