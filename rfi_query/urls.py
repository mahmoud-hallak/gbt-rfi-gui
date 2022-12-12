from django.urls import include, path

from rfi import views

# router = routers.DefaultRouter()
# router.register(r'rfi', views.MasterRfiCatalogViewSet)

# Wire up our API using automatic URL routing.
# Additionally, we include login URLs for the browsable API.
urlpatterns = [
    # path('', include(router.urls)),
    # path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('', views.landing_page, name="rfi_webpage"),
    path('__debug__/', include('debug_toolbar.urls')),
]
