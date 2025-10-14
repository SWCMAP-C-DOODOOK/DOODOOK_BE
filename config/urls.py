from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.http import HttpResponse

from apps.ledger.views_stats import AccumulatedStatsView, CategoryShareStatsView

def healthz(_request):
    return HttpResponse("ok", content_type="text/plain")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("healthz/", healthz),
    path("api/", include("apps.budget.urls")),
    path("api/", include("apps.openbanking.urls")),
    path("api/", include("apps.ocr.urls")),
    path("api/", include("apps.dues.urls")),
    path("api/stats/category", CategoryShareStatsView.as_view()),
    path("api/stats/accumulated", AccumulatedStatsView.as_view()),
    path("api/", include("apps.common.urls")),
    path("api/", include("apps.users.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)