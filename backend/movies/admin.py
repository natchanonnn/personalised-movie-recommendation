from django.contrib import admin

from .models import CastCredit, CrewCredit, Genre, Movie, Person


admin.site.register(CastCredit)
admin.site.register(CrewCredit)
admin.site.register(Genre)
admin.site.register(Movie)
admin.site.register(Person)
