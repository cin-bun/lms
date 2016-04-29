from django.conf.urls import include, url

from learning.admission.views import InterviewListView, InterviewDetailView

urlpatterns = [
    url(r'^admission', include([
        url(r'^/interviews/$', InterviewListView.as_view(), name='admission_dashboard'),
        url(r'^/interviews/(?P<pk>\d+)$', InterviewDetailView.as_view(), name='admission_interview_detail'),
    ])),
]