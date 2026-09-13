def no_index_middleware(get_response):
    """Tells crawlers to stay out -- this deploy is reachable at a bare IP,
    not a domain meant for public discovery. See also urls.py robots.txt."""
    def middleware(request):
        response = get_response(request)
        response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        return response
    return middleware
