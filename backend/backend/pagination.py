from rest_framework.pagination import PageNumberPagination


class StandardPagination(PageNumberPagination):
    """Default list pagination.

    Keeps responses bounded so a large transaction history cannot be pulled in a
    single request. Clients can raise the page size up to `max_page_size`.
    """

    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 500
