from rest_framework.pagination import PageNumberPagination
"""
From the prompt: "how do you allow customization of page size in query params Django ex url/someth?page=5&page_size =3"
ChatGPT 4.5, OpenAI, 2025/10/16,https://chatgpt.com/c/68f281b5-b4a0-8330-856d-c05eac523956

Class to allow for custom page_size params from API endpoints
"""
class CustomPageNumberPagination(PageNumberPagination):
    page_size = 10  # default
    page_size_query_param = 'size'  # customizable page size
    max_page_size = 100  # page size limit
    page_query_param = 'page'  # page number param